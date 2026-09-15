"""Apply a narrow upstream fix: validate requested demand hours, not unused years.

The upstream assertion precedes date selection and fails on unrelated historical
gaps. Reindex before asserting, so missing requested hours are also detected.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = '''    assert not load.isna().any().any(), (
        "Load data contains nans. Adjust the parameters "
        "`time_shift_for_large_gaps` or modify the `manual_adjustment` function "
        "for implementing the needed load data modifications."
    )

'''
ANCHOR = '    load = load.loc[years].reindex(index=snapshots)\n'
CHECK = '''
    # Grid Conductor: check the requested window after alignment, not unused years.
    missing = load.isna().sum()
    if missing.any():
        raise ValueError(f"Missing demand hours in requested window: {missing[missing > 0].to_dict()}")
'''


def patch(source):
    if CHECK in source:
        return source
    if OLD not in source or ANCHOR not in source:
        raise ValueError('Upstream demand source changed; review before patching')
    return source.replace(OLD, '', 1).replace(ANCHOR, ANCHOR+CHECK, 1)


if __name__ == '__main__':
    path = ROOT/'data/pypsa-eur/upstream/scripts/build_electricity_demand.py'
    source = path.read_text(encoding='utf-8')
    path.write_text(patch(source), encoding='utf-8')
    print('Applied requested-window demand validation patch')
