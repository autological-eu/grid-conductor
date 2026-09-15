"""Resumable ERA5 -> per-cell generation profiles, under a 10 GiB growth budget.

Use the pinned PyPSA-Eur environment. Parent supervises a single worker with all
temporary downloads inside the owned work directory. Raw files are removed only
after reopening and hashing the corresponding compact output.
"""
import argparse
import calendar
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT/'data/pypsa-eur/monthly-weather'
GIB = 1024**3


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            value.update(block)
    return value.hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')
    temp.replace(path)


def month_window(year, month):
    start = dt.datetime(year, month, 1)
    stop = start+dt.timedelta(days=calendar.monthrange(year, month)[1])
    return start, stop


def owned_remove(path, root=WORK):
    if Path(path).is_symlink():
        raise ValueError('Refusing cleanup through a symlink')
    path, root = Path(path).resolve(), Path(root).resolve()
    if path == root or root not in path.parents or path.is_symlink():
        raise ValueError('Cleanup target is not an owned weather batch')
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def tree_bytes(root):
    total = 0
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if not (Path(base)/d).is_symlink()]
        for name in files:
            try:
                total += (Path(base)/name).stat().st_size
            except FileNotFoundError:
                pass
    return total


def merge(a, b):
    for key, value in b.items():
        if isinstance(value, dict) and isinstance(a.get(key), dict):
            merge(a[key], value)
        else:
            a[key] = value
    return a


def configuration(path):
    import yaml
    upstream = ROOT/'data/pypsa-eur/upstream'
    base = yaml.safe_load((upstream/'config/config.default.yaml').read_text())
    return merge(base, yaml.safe_load(Path(path).read_text()))


def conversions(config):
    from compact_cutout import resource_key
    out = {}
    for technology in config['electricity']['renewable_carriers']:
        if technology == 'hydro':
            continue
        resource = dict(config['renewable'][technology]['resource'])
        method = resource.pop('method')
        model_key = 'panel' if method == 'pv' else 'turbine'
        models = resource[model_key]
        for model in models.values() if isinstance(models, dict) else [models]:
            opts = dict(resource, **{model_key: model})
            out[resource_key(method, opts)] = dict(method=method, resource=opts)
    return out


def verify(path, start, stop, keys):
    import pandas as pd
    import xarray as xr
    with xr.open_dataset(path, chunks={'time': 24}) as data:
        expected = pd.date_range(start, stop, freq='h', inclusive='left')
        if not data.indexes['time'].equals(expected):
            raise ValueError('Compact output does not contain every required hour')
        if set(data.data_vars) != set(keys):
            raise ValueError('Compact conversion inventory mismatch')
        for key in keys:
            if bool(data[key].isnull().any().compute()):
                raise ValueError(f'Missing converted data in {key}')
            if not bool((abs(data[key]) < float('inf')).all().compute()):
                raise ValueError('Nonfinite converted data')
    return sha(path)


def worker(config_path, month):
    import atlite
    import numpy as np
    import pandas as pd
    import xarray as xr
    config = configuration(config_path)
    year = int(config['snapshots']['start'][:4])
    specs = conversions(config)
    start, stop = month_window(year, month)
    batch = WORK/f'{year}-{month:02d}'
    batch.mkdir(parents=True, exist_ok=True)
    raw = batch/'raw'
    raw.mkdir(exist_ok=True)
    output = batch/'profiles.nc'
    receipt = batch/'verified.json'
    fingerprint = hashlib.sha256(json.dumps(dict(specs=specs, grid=config['atlite']['cutouts'][config['atlite']['default_cutout']]), sort_keys=True).encode()).hexdigest()
    if receipt.exists():
        previous = json.loads(receipt.read_text())
        if previous['fingerprint'] != fingerprint:
            raise ValueError('Existing batch uses different weather/conversion settings; choose a new work directory')
        if verify(output, start, stop, specs) != previous['sha256']:
            raise ValueError('Previously verified batch changed')
        owned_remove(raw)
        return
    params = config['atlite']['cutouts'][config['atlite']['default_cutout']]
    cutout = atlite.Cutout(raw/'weather.nc', module='era5',
        x=slice(*params['x']), y=slice(*params['y']), dx=params['dx'], dy=params['dy'],
        time=slice(start, stop-dt.timedelta(hours=1)), chunks={'time': 24})
    expected = pd.date_range(start, stop, freq='h', inclusive='left')
    if not cutout.data.indexes['time'].equals(expected):
        raise ValueError('Cached raw month has the wrong time range')
    cutout.prepare(features=['wind', 'influx', 'temperature'], tmpdir=raw,
        monthly_requests=True, concurrent_requests=False,
        compression={'zlib': True, 'complevel': 1, 'shuffle': True})
    variables = {}
    for key, spec in specs.items():
        field = getattr(cutout, spec['method'])(aggregate_time=None, **spec['resource'])
        variables[key] = field.astype(np.float32)
    data = xr.Dataset(variables, attrs=dict(cutout.data.attrs))
    data.attrs.update(gridfix_compact=1, gridfix_resources=json.dumps(specs, sort_keys=True),
                      gridfix_fingerprint=fingerprint)
    temp = output.with_suffix('.nc.tmp')
    encoding = {key: dict(zlib=True, complevel=3, shuffle=True, dtype='float32') for key in variables}
    data.to_netcdf(temp, encoding=encoding)
    checksum = verify(temp, start, stop, specs)
    # Compare a sampled converted series after storage to detect encoding changes.
    with xr.open_dataset(temp) as stored:
        for key, field in variables.items():
            np.testing.assert_allclose(stored[key].isel(time=[0, len(expected)-1]).values,
                field.isel(time=[0, len(expected)-1]).values, rtol=1e-6, atol=1e-7)
    temp.replace(output)
    raw_hash = sha(raw/'weather.nc')
    cutout.data.close()
    save(receipt, dict(sha256=checksum, raw_sha256=raw_hash, fingerprint=fingerprint,
        start=start.isoformat(), end_exclusive=stop.isoformat(), hours=len(expected),
        atlite_version=atlite.__version__, specs=specs, bytes=output.stat().st_size))
    owned_remove(raw)


def supervise(config, months, budget_gib, wait_lock=False, finish=False):
    if os.name != 'posix':
        raise ValueError('Run the supervised downloader in Linux/WSL')
    WORK.mkdir(parents=True, exist_ok=True)
    lock = WORK/'pipeline.lock'
    import fcntl
    with lock.open('a') as lockfile:
        fcntl.flock(lockfile, fcntl.LOCK_EX | (0 if wait_lock else fcntl.LOCK_NB))
        initial_free = shutil.disk_usage(ROOT).free
        initial_work = tree_bytes(WORK)
        limit = int(budget_gib*GIB)
        status = dict(status='running', budget_gib=budget_gib, months_completed=[], peak_bytes=initial_work,
                      note='Sampled guard stops at budget minus 1 GiB; not an OS filesystem quota.')
        for month in months:
            if shutil.disk_usage(ROOT).free < 4*GIB or tree_bytes(WORK) > limit-GIB:
                raise ValueError('Not enough disk headroom to start a month')
            log = (WORK/f'month-{month:02d}.log').open('a')
            command = [sys.executable, str(Path(__file__).resolve()), '--config', str(config), '--worker', str(month)]
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            stopped = False
            try:
                while process.poll() is None:
                    used = tree_bytes(WORK)
                    free = shutil.disk_usage(ROOT).free
                    growth = initial_free-free+initial_work
                    status.update(active_month=month, bytes=used, physical_free_bytes=free,
                                  peak_bytes=max(status['peak_bytes'], used))
                    if max(used, growth) >= limit-GIB or free < 3*GIB:
                        stopped = True
                        os.killpg(process.pid, signal.SIGTERM)
                        try:
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid, signal.SIGKILL)
                        break
                    save(WORK/'status.json', status)
                    time.sleep(2)
                process.wait()
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait()
                log.close()
            if stopped or process.returncode:
                status.update(status='paused_disk_budget' if stopped else 'failed', exit_code=process.returncode)
                save(WORK/'status.json', status)
                raise ValueError(f'Month {month} stopped; inspect monthly-weather/status.json and month log')
            status['months_completed'].append(month)
            save(WORK/'status.json', status)
        status['status'] = 'monthly_profiles_complete'
        save(WORK/'status.json', status)
        if finish:
            assemble(config)
            publish(config)
            status['status'] = 'annual_profiles_published'
            save(WORK/'status.json', status)


def assemble(config_path):
    import xarray as xr
    config = configuration(config_path)
    year = int(config['snapshots']['start'][:4])
    specs = conversions(config)
    paths = []
    fingerprints = set()
    for month in range(1, 13):
        folder = WORK/f'{year}-{month:02d}'
        receipt = json.loads((folder/'verified.json').read_text())
        path = folder/'profiles.nc'
        if sha(path) != receipt['sha256']:
            raise ValueError('A verified monthly profile changed')
        fingerprints.add(receipt['fingerprint'])
        paths.append(path)
    if len(fingerprints) != 1:
        raise ValueError('Monthly resource/grid settings differ')
    # Allow room for both verified month files and the assembled result.
    expected_bytes = sum(path.stat().st_size for path in paths)*2 + GIB
    if tree_bytes(WORK)+expected_bytes > 9*GIB or shutil.disk_usage(ROOT).free < expected_bytes+3*GIB:
        raise ValueError('Not enough budget headroom to assemble the annual file')
    output = WORK/f'europe-{year}-compact.nc'
    temp = output.with_suffix('.nc.tmp')
    with xr.open_mfdataset(paths, combine='nested', concat_dim='time', join='exact',
                          chunks={'time': 24}, combine_attrs='override') as data:
        data.to_netcdf(temp, encoding={key: dict(zlib=True, complevel=3, shuffle=True,
                                                 dtype='float32') for key in specs})
    checksum = verify(temp, dt.datetime(year, 1, 1), dt.datetime(year+1, 1, 1), specs)
    temp.replace(output)
    save(WORK/'annual-verified.json', dict(sha256=checksum, monthly_sha256=[sha(p) for p in paths],
        fingerprint=next(iter(fingerprints)), year=year, bytes=output.stat().st_size))
    # Keep monthly compact files as restart checkpoints; only raw batches are purged.
    print(f'Annual compact cutout verified: {output}')


def publish(config_path):
    config = configuration(config_path)
    year = int(config['snapshots']['start'][:4])
    output = WORK/f'europe-{year}-compact.nc'
    receipt = json.loads((WORK/'annual-verified.json').read_text())
    if sha(output) != receipt['sha256']:
        raise ValueError('Annual output failed its recorded hash')
    name = config['atlite']['default_cutout']
    if name != f'europe-{year}-compact':
        raise ValueError('Select the compact production configuration before publishing')
    target = ROOT/f'data/pypsa-eur/upstream/data/cutout/build/unknown/{name}.nc'
    if target.exists() or target.is_symlink():
        if target.resolve() != output.resolve():
            raise ValueError('Publication target already belongs to another file')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(output.resolve())
    print(f'Published verified compact cutout without a second copy: {target}')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', type=Path, default=ROOT/'config/pypsa-eur/full-year.yaml')
    p.add_argument('--months', type=int, nargs='+', default=list(range(1, 13)))
    p.add_argument('--budget-gib', type=float, default=10)
    p.add_argument('--worker', type=int)
    p.add_argument('--assemble', action='store_true')
    p.add_argument('--publish', action='store_true')
    p.add_argument('--wait-lock', action='store_true')
    p.add_argument('--finish', action='store_true', help='After all monthly batches, assemble and publish verified annual profiles')
    args = p.parse_args()
    if not 0 < args.budget_gib <= 10 or any(m not in range(1, 13) for m in args.months):
        p.error('Budget must be within 10 GiB and months within 1..12')
    if args.publish:
        publish(args.config)
    elif args.assemble:
        assemble(args.config)
    elif args.worker:
        worker(args.config, args.worker)
    else:
        supervise(args.config.resolve(), args.months, args.budget_gib, args.wait_lock, args.finish)
