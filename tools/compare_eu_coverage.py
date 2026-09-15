"""Compare monthly quality reports produced with identical pipeline rules."""
import argparse
import json
from pathlib import Path


def summarize(report):
    groups={}
    for category in ['price','load','gen','charge','flow','capacity']:
        rows=[v for k,v in report['coverage'].items() if k.startswith(category+'/')]
        expected=sum(v['expected_hours'] for v in rows)
        groups[category]=dict(series=len(rows),complete_series=sum(v['coverage']==1 for v in rows),
            observed_hour_share=sum(v['observed_hours'] for v in rows)/expected if expected else None)
    return dict(month=report['month'],bank_sha256=report['bank_sha256'],groups=groups,
        issues=len(report['issues']),input_gate_passed=report['input_gate_passed'],
        balanced_zones=sum(v['observed_hours']==v['expected_hours'] and v['absolute_residual_share'] is not None and v['absolute_residual_share']<=.05 for v in report['balances'].values()))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('reports',nargs='+',type=Path)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    result=dict(source='ENTSO-E API',months=[summarize(json.loads(p.read_text())) for p in args.reports],
        interpretation='Coverage comparison only. Differences do not isolate reporting delay from geography, seasonal operation, publication practices or API coverage.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,allow_nan=False,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
