"""Run and publish the FR–CH relaxation experiments.

Solves baseline and each enlargement variant (100/500/1000 MW and a loose
limit) under identical rules, then writes one machine artifact. `--validated`
only flips the status marker; it must be supplied by a human after the M2
gates in docs/market-model-validation.md pass. `co2_change_t` and
`annual_opportunity_meur` are reported as-is (never scaled to annual).
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from carbon_pilot import ROOT
from market_model import experiment

VARIANTS=[100,500,1000,'loose']


def loose_addition_mw(data):
    huge=max(max(max(e['ab_mw']+e['ba_mw']) for e in data['edges']),1)
    return int(10*huge)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,default=ROOT/'data/carbon-pilot/market/input.json')
    p.add_argument('--edge',default='FR-CH')
    p.add_argument('--output',type=Path,default=ROOT/'public/research/market-experiment.json')
    p.add_argument('--validated',action='store_true',help='M2 gates have passed; mark status pilot_validated')
    args=p.parse_args()
    if not args.input.exists():p.error(f'Input missing (build it first): {args.input}')
    data=json.loads(args.input.read_text(encoding='utf-8'))
    target=args.edge if args.edge in [e['id'] for e in data['edges']] else p.error(f'Unknown edge {args.edge}')
    runs=[]
    for variant in VARIANTS:
        add_mw=loose_addition_mw(data) if variant=='loose' else variant
        run=experiment(data,target,add_mw)
        run['variant']=str(variant);run['additional_mw']=add_mw
        if args.validated:run['status']='pilot_validated'
        runs.append(run)
    artifact=dict(model='linked-dispatch-v1 FR–CH pilot',edge=target,validated=args.validated,
        variants=[r['variant'] for r in runs],
        experiments=[{k:r[k] for k in ['variant','status','co2_change_t','period_opportunity_meur',
            'annual_opportunity_meur','validation','emission_basis']} for r in runs],
        series=dict(baseline=runs[0]['baseline'],hourly_difference=[dict(start=h['start'],benefit_eur=h['benefit_eur'],
            co2_benefit_t=h['co2_benefit_t']) for h in runs[0]['hourly_difference']]),
        scenario_reference='loose run scenario carries the enlarged-edge dispatch for reference',
        note='per-hour benefit/co2_benefit: signed net effect of the enlarged link on that interval. '
            'annual_opportunity_meur stays None until the full-year build passes M2 gates.',
        generated_at=datetime.now(timezone.utc).isoformat())
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(artifact,allow_nan=False,indent=2),encoding='utf-8')
    for r in runs:
        ann=r['annual_opportunity_meur'];print(f"{r['variant']:>6}  add {r['additional_mw']:>5} MW  "
            f"opportunity {r['period_opportunity_meur']*1000:.0f} kEUR  co2_change_t {r['co2_change_t']:.0f}  "
            f"annual {ann if ann is None else round(ann,1)}  status {r['status']}")
    print(f"wrote {args.output}")


if __name__=='__main__':main()