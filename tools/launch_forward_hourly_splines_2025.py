"""Detach the authorized one-off study; inspect identity, reject duplicate jobs."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/bidding-zone-network-2025/forward-hourly-splines-v1'


def identity(pid):
    try:
        stat=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
        return stat[0],stat[19]
    except FileNotFoundError:return None,None


def main():
    OUT.mkdir(exist_ok=True)
    lock=(OUT/'launcher.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    path=OUT/'execution.json'
    if path.exists():
        old=json.loads(path.read_text())
        for role in ['fit','finish']:
            state,start=identity(old.get(role+'_pid',0))
            if state not in [None,'Z','X'] and start==old.get(role+'_start'):
                raise RuntimeError(f'Existing {role} process is live (including paused state)')
    if (OUT/'summary.json').exists():raise RuntimeError('Already completed; inspect results')
    env=os.environ.copy();env.update(PYTHONPATH=str(ROOT/'tools'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    with (OUT/'fit.log').open('ab') as log:
        fit=subprocess.Popen([sys.executable,str(ROOT/'tools/run_forward_hourly_splines_2025.py')],cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    state,start=identity(fit.pid)
    receipt=dict(utc=datetime.now(timezone.utc).isoformat(),fit_pid=fit.pid,fit_start=start,scope='one-off12month forward-validation study; no recurring review')
    path.write_text(json.dumps(receipt,indent=2))
    with (OUT/'finish.log').open('ab') as log:
        finish=subprocess.Popen([sys.executable,str(ROOT/'tools/finish_forward_hourly_splines_2025.py')],cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    _,start=identity(finish.pid)
    receipt.update(finish_pid=finish.pid,finish_start=start)
    path.write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt))


if __name__=='__main__':main()
