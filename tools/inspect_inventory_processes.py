"""Read-only inventory-process inspection; receipts never establish liveness."""
import argparse
import json
from pathlib import Path


def matches_process(folder, script, flag, target):
    try:
        state = next(line.split()[1] for line in (folder/'status').read_text().splitlines() if line.startswith('State:'))
        if state in ['Z', 'X', 'x']:
            return False
        args = [v for v in (folder/'cmdline').read_bytes().decode().split('\0') if v]
        if not any(Path(v).name == script for v in args) or args.count(flag) != 1:
            return False
        position = args.index(flag)
        if position+1 >= len(args):
            return False
        value = Path(args[position+1])
        if not value.is_absolute():
            value = (folder/'cwd').resolve()/value
        return value.resolve() == target.resolve()
    except (OSError, UnicodeError, StopIteration):
        return False


def inspect(root, continuation, proc=Path('/proc')):
    root, continuation = root.resolve(), continuation.resolve()
    roles = [('original_driver', 'submonthly_inventory_driver.py', '--root', root, root/'driver-status.json'),
             ('continuation_waiter', 'run_submonthly_continuation.py', '--output', continuation, continuation.with_suffix('.waiting.json')),
             ('continuation_driver', 'submonthly_inventory_driver.py', '--root', continuation, continuation/'driver-status.json')]
    rows = []
    for role, script, flag, target, status_path in roles:
        receipt = json.loads(status_path.read_text()) if status_path.exists() else None
        saved_pid = receipt.get('pid') if receipt else None
        live = sorted(int(folder.name) for folder in proc.iterdir() if folder.name.isdigit()
                      and matches_process(folder, script, flag, target))
        rows.append(dict(role=role, live_pids=live, receipt_present=receipt is not None,
                         saved_pid_matches_live_process=type(saved_pid) is int and saved_pid in live,
                         receipt_stage=receipt.get('status') if receipt else None,
                         interpretation='live_process_observed_not_checkpoint_validation' if live else 'no_matching_live_process_receipt_is_not_progress'))
    return dict(scope='Liveness inspection only; no witness, bound, empirical or investment acceptance.', processes=rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--continuation', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(inspect(args.root, args.continuation), indent=2))
