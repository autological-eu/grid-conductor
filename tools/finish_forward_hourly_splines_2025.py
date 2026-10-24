"""One-off completion watcher; never starts fits or recurring reviews."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/bidding-zone-network-2025/forward-hourly-splines-v1'


def main():
    execution=json.loads((OUT/'execution.json').read_text())
    pid=execution['fit_pid'];start=execution['fit_start']
    while not (OUT/'summary.json').exists():
        try:
            stat=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
            live=stat[0] not in ['Z','X'] and stat[19]==start
        except FileNotFoundError:live=False
        if not live:
            (OUT/'postprocessing.json').write_text(json.dumps(dict(status='fit_stopped_without_completion',failure_receipt_exists=(OUT/'failure.json').exists()),indent=2))
            return
        time.sleep(30)
    try:
        for script in ['audit_forward_hourly_splines_2025.py','report_forward_hourly_splines_2025.py']:
            subprocess.run([sys.executable,str(ROOT/'tools'/script)],cwd=ROOT,check=True)
        (OUT/'postprocessing.json').write_text(json.dumps(dict(status='audit_and_report_complete'),indent=2))
    except Exception as exc:
        (OUT/'postprocessing.json').write_text(json.dumps(dict(status='postprocessing_failed',reason=str(exc)),indent=2))
        raise


if __name__=='__main__':main()
