"""Apply a narrow upstream fix: fall back to the latest year column for p_max_pu.

The committed data/nuclear_p_max_pu.csv stops at 2024, so a 2025 planning
horizon makes df[year] raise KeyError, which upstream does not catch (only
ValueError/TypeError). Fall back to the last available year column instead.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = '''                try:
                    df.columns = df.columns.astype(int)
                    year = n.snapshots[0].year
                    values = df[year]
                except (ValueError, TypeError):
                    values = df.iloc[:, -1]  # take last column if year selection fails
'''
NEW = '''                try:
                    df.columns = df.columns.astype(int)
                    year = n.snapshots[0].year
                    values = df[year]
                except (ValueError, TypeError, KeyError):
                    # Grid Conductor: horizon may outrun committed data columns;
                    # reuse the latest available year instead of failing.
                    values = df.iloc[:, -1]  # take last column if year selection fails
'''


def patch(source):
    if 'except (ValueError, TypeError, KeyError):' in source:
        return source
    if OLD not in source:
        raise ValueError('Upstream conventional input source changed; review before patching')
    return source.replace(OLD, NEW, 1)


if __name__ == '__main__':
    path = ROOT/'data/pypsa-eur/upstream/scripts/add_electricity.py'
    source = path.read_text(encoding='utf-8')
    path.write_text(patch(source), encoding='utf-8')
    print('Applied latest-year fallback for conventional p_max_pu inputs')