"""Repair upstream's intended last-year availability fallback; record the proxy."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
p = ROOT/'data/pypsa-eur/upstream/scripts/add_electricity.py'
source = p.read_text()
old = '''                except (ValueError, TypeError):
                    values = df.iloc[:, -1]  # take last column if year selection fails'''
new = '''                except (ValueError, TypeError, KeyError):
                    logger.warning("Availability year %s is unavailable for %s/%s; using last published column %s as an explicit proxy", n.snapshots[0].year, carrier, attr, df.columns[-1])
                    values = df.iloc[:, -1]  # intended upstream last-column fallback'''
if new not in source:
    if old not in source:
        raise ValueError('Upstream availability fallback changed; review before patching')
    p.write_text(source.replace(old, new, 1))
print('Patched intended availability fallback with explicit proxy warning')
