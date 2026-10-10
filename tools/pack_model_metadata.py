"""Lossless Git storage for immutable model metadata; hydrate before model work.

Original JSON bytes/hashes remain the authoritative calculation inputs. The local
JSON files are ignored, and omitted from the static build; downloads use gzip.
"""
import argparse
import gzip
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    'irena-capacity-2025/summary.json',
    'european-reservoir-clearing-2025/summary.json',
    'fixed-reservoir-screening-2025/summary.json',
    'daily-fuel-annual-2025/summary.json',
]


def run(restore=False):
    for name in FILES:
        path = ROOT / 'public/research' / name
        archive = path.with_name(path.name + '.gz')
        if restore:
            raw = gzip.decompress(archive.read_bytes())
            if path.exists() and path.read_bytes() != raw:
                raise ValueError('Refuse to overwrite changed model input: ' + name)
            path.write_bytes(raw)
        else:
            raw = path.read_bytes()
            archive.write_bytes(gzip.compress(raw, mtime=0))
            assert gzip.decompress(archive.read_bytes()) == raw
    print('Four model metadata archives verified losslessly')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restore', action='store_true')
    run(parser.parse_args().restore)
