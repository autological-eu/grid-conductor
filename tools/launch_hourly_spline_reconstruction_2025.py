"""Detach the authorized checkpointed fit and its one-off completion pipeline.

Separate sessions and redirected descriptors survive interactive tool cleanup.
The optimizer and scientific configuration are deliberately untouched.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/bidding-zone-network-2025/hourly-spline-reconstruction-recovery-v1'
PYTHON = ROOT / 'data/pypsa-eur/upstream/.pixi/envs/default/bin/python'
SCRIPTS = ['hourly_spline_numerical_recovery_2025.py', 'finish_hourly_spline_reconstruction_2025.py']


def identity(pid):
    try:
        proc = Path('/proc') / str(pid)
        fields = (proc / 'stat').read_text().split()
        return dict(pid=pid, state=fields[2], start=fields[21], group=fields[4], session=fields[5],
                    arguments=(proc / 'cmdline').read_bytes().split(b'\0'))
    except (FileNotFoundError, ProcessLookupError):
        return None


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    lock = (OUT / 'launch.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if (OUT / 'recovery-completion.json').exists():
        raise RuntimeError('Fit already completed; inspect results instead of relaunching')
    if (OUT / 'failure.json').exists():
        raise RuntimeError('Numerical failure requires diagnosis before relaunch')
    active = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        item = identity(int(proc.name))
        if item and item['state'] not in {'Z', 'X'} and any(
                Path(os.fsdecode(a)).name in SCRIPTS for a in item['arguments'] if a):
            active.append(item['pid'])
    if active:
        raise RuntimeError('Existing fit/completion process is live: ' + str(active))
    env = os.environ.copy()
    env.update(PYTHONPATH='tools', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
    utc = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    children = []
    for script, log in zip(SCRIPTS, ['run.log', 'postprocessing.log']):
        args = [str(PYTHON), '-u', str(ROOT / 'tools' / script)]
        if children:
            args += ['--runner-pid', str(children[0]['pid'])]
        with (OUT / log).open('ab', buffering=0) as f:
            f.write(('\nDETACHED_SESSION ' + utc + '\n').encode())
            child = subprocess.Popen(args, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                stdout=f, stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
        time.sleep(.2)
        item = identity(child.pid)
        if child.poll() is not None or not item or item['state'] in {'Z', 'X'}:
            raise RuntimeError('Detached process failed at startup: ' + script)
        if int(item['group']) != child.pid or int(item['session']) != child.pid:
            raise RuntimeError('Process did not start in its own session')
        children.append(dict(pid=child.pid, start=item['start'], process_group=item['group'],
            session=item['session'], script=script, script_sha256=digest(ROOT / 'tools' / script)))
    record = dict(launched_utc=utc, method='independent sessions; all descriptors redirected; no optimizer/configuration change',
        launcher_sha256=digest(Path(__file__)), processes=children)
    temporary = OUT / 'execution.tmp.json'
    temporary.write_text(json.dumps(record, indent=2) + '\n')
    os.replace(temporary, OUT / 'execution.json')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    run()
