"""Install the tracked compact-cutout adapter into the pinned upstream checkout.

This changes only cutout loading; upstream regional resource classes, capacity
weighting, exclusions and aggregation remain intact. Fail closed on source drift.
"""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT/'data/pypsa-eur/upstream'


def install():
    helper = UPSTREAM/'scripts/_helpers.py'
    source = helper.read_text()
    anchor = '    if isinstance(cutout_files, str):\n        cutout = atlite.Cutout(cutout_files, chunks=chunks)'
    replacement = '    from scripts.gridfix_compact_cutout import open_cutout\n\n    if isinstance(cutout_files, str):\n        cutout = open_cutout(cutout_files, chunks=chunks)'
    if replacement not in source:
        if anchor not in source:
            raise ValueError('Upstream load_cutout changed; review adapter')
        helper.write_text(source.replace(anchor, replacement, 1))
    shutil.copyfile(ROOT/'tools/compact_cutout.py', UPSTREAM/'scripts/gridfix_compact_cutout.py')
    build = UPSTREAM/'scripts/build_cutout.py'
    source = build.read_text()
    anchor = '    cutout_params = snakemake.params.cutouts[snakemake.wildcards.cutout]'
    guard = '''    if snakemake.wildcards.cutout.endswith("-compact"):
        raise ValueError("Build and verify monthly weather profiles, then publish the compact cutout before running the model")

'''
    if guard not in source:
        if anchor not in source:
            raise ValueError('Upstream build_cutout changed; review guard')
        build.write_text(source.replace(anchor, guard+anchor, 1))


if __name__ == '__main__':
    install()
    print('Installed compact weather loader and missing-input guard')
