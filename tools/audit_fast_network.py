"""Inventory tracked PyPSA artifacts without treating dispatch as availability."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def audit(ref):
    commit = subprocess.check_output(['git', 'rev-parse', ref], cwd=ROOT, text=True).strip()
    files = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', commit], cwd=ROOT, text=True).splitlines()
    inventory = []
    for name in files:
        if name.startswith('public/research/baseline/') or name == 'public/research/pypsa-targets.json':
            raw = subprocess.check_output(['git', 'show', f'{commit}:{name}'], cwd=ROOT)
            inventory.append(dict(path=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
    required = ['data/pypsa-eur/baseline-manifest.json']
    missing = [name for name in required if not (ROOT/name).is_file()]
    networks = list((ROOT/'data/pypsa-eur').rglob('*.nc')) if (ROOT/'data/pypsa-eur').exists() else []
    if not networks:
        missing.append('Solved PyPSA NetCDF (not in tracked research artifacts)')
    return dict(schema_version=1, status='inputs_not_exported', source_commit=commit,
        methodology_status='experimental_not_validated', published_outputs=inventory,
        local_missing_sources=missing,
        required_dispatch_inputs=['generation availability and marginal costs', 'minimum generation and ramps',
          'demand and external injections', 'directional capacity or non-overlapping PTDF/RAM',
          'storage/hydro chronology, inflows and energy budgets', 'snapshot weights and source manifest'],
        warning='Published hourly dispatch is an optimization output, not renewable availability. No annual counterfactual benefit is inferred from it.',
        next_step='Recover the solved source network and manifest; explicitly audit unsupported PyPSA physics before exporting a reduced transport model.')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ref', default='origin/codex/carbon-pilot')
    p.add_argument('--output', type=Path, default=ROOT/'public/research/network-model-input-audit.json')
    args = p.parse_args()
    report = audit(args.ref)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(status=report['status'], outputs=len(report['published_outputs']), missing=report['local_missing_sources'])))
