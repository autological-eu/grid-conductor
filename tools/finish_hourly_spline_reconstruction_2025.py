"""One-off completion pipeline for the live fit; never launches another fit."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/bidding-zone-network-2025/hourly-spline-reconstruction-recovery-v1'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(value):
    path = OUT / 'postprocessing.json'
    temporary = path.with_suffix('.tmp.json')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    os.replace(temporary, path)


def run(pid):
    lock = (OUT / 'postprocessing.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    proc = Path(f'/proc/{pid}')
    started = (proc / 'stat').read_text().split()[21]
    if 'hourly_spline_numerical_recovery_2025.py' not in (proc / 'cmdline').read_text():
        raise ValueError('Specified process is not the live recovery runner')
    scripts = ['audit_hourly_spline_reconstruction_2025.py', 'report_hourly_spline_reconstruction_2025.py']
    expected = {name: digest(ROOT / 'tools' / name) for name in scripts}
    record = dict(status='waiting_for_completed_fit', runner_pid=pid, process_start=started,
        scripts_sha256=expected, controller_sha256=digest(Path(__file__)))
    save(record)
    while not (OUT / 'recovery-completion.json').exists():
        if (OUT / 'failure.json').exists():
            raise RuntimeError('Fit failed; no completed-fit/audit/report claim')
        if not proc.exists() or (proc / 'stat').read_text().split()[21] != started:
            raise RuntimeError('Runner exited without completion proof; verification incomplete')
        time.sleep(5)
    for name in scripts:
        if digest(ROOT / 'tools' / name) != expected[name]:
            raise ValueError('Postprocessing source changed: ' + name)
        record['status'] = 'independent_audit' if name.startswith('audit_') else 'report_generation'
        save(record)
        subprocess.run([sys.executable, str(ROOT / 'tools' / name), '--recovery'], cwd=ROOT, check=True)
    record['status'] = 'audit_and_report_complete'
    record['summary_sha256'] = digest(OUT / 'summary.json')
    record['audit_sha256'] = digest(OUT / 'audit.json')
    record['report_sha256'] = digest(ROOT / 'research/hourly-spline-reconstruction-2025.md')
    save(record)
    print(json.dumps(record, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runner-pid', type=int, required=True)
    args = parser.parse_args()
    try:
        run(args.runner_pid)
    except Exception as exc:
        save(dict(status='postprocessing_failed', error=str(exc)))
        raise
