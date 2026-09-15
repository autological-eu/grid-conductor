"""Reconcile ENTSO-E inputs, then solve only if the input gate passes."""
import argparse
import json
from pathlib import Path
from carbon_pilot import ROOT
from audit_eu_market import audit_bank


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bank',type=Path,default=ROOT/'data/eu-market/bank-2026-08-v2.json')
    p.add_argument('--output-dir',type=Path,default=ROOT/'public/research')
    p.add_argument('--jao-report',type=Path,help='Attach scoped JAO network validation evidence; never bypass quantity gates')
    p.add_argument('--network-coverage',type=Path,help='Attach monthly regional publication coverage separately from solver readiness')
    args=p.parse_args()
    bank=json.loads(args.bank.read_text())
    quality=audit_bank(bank)
    public=args.output_dir
    public.mkdir(parents=True,exist_ok=True)
    (public/'eu-input-quality.json').write_text(json.dumps(quality,allow_nan=False,indent=2))
    report=dict(decision='blocked_input_quality',bank_sha256=quality['bank_sha256'],
        input_gate_passed=quality['input_gate_passed'],annual_opportunity_meur=None,
        issues=quality['issues'],baseline_run=False)
    if args.jao_report:
        evidence=json.loads(args.jao_report.read_text())
        report['jao_network_evidence']=evidence
        report['network_integration_status']='sample_verified_full_market_domain_not_yet_integrated'
        # A successful sample is not month-wide constraint coverage and does not
        # make missing A61 directions zero or independently unconstrained.
    if args.network_coverage:
        coverage=json.loads(args.network_coverage.read_text())
        if coverage['month']!=bank['month']:raise ValueError('Network coverage month mismatch')
        report['network_publication_coverage']=coverage
    if quality['input_gate_passed']:
        from assemble_eu_market import assemble
        from market_model import dispatch
        data=assemble(bank);result=dispatch(data)
        out=ROOT/'data/eu-market'
        (out/f"input-{bank['month']}-v2.json").write_text(json.dumps(data,allow_nan=False))
        (out/f"dispatch-{bank['month']}-v2.json").write_text(json.dumps(result,allow_nan=False))
        report.update(baseline_run=True,decision='experimental_not_validated',
            unserved_mwh=result['unserved_mwh'],price_mae_eur_mwh={})
        for z in data['zones']:
            pairs=[(r['price_eur_mwh'][z],v) for r,v in zip(result['hourly'],data['observed_price_eur_mwh'].get(z,[])) if v is not None]
            report['price_mae_eur_mwh'][z]=sum(abs(a-b) for a,b in pairs)/len(pairs) if pairs else None
        report['note']='Dispatch diagnostics only; no EU market validation approval or annual attribution.'
    (public/'eu-model-validation.json').write_text(json.dumps(report,allow_nan=False,indent=2))
    print(json.dumps(dict(decision=report['decision'],issues=len(report['issues']),baseline_run=report['baseline_run'])))


if __name__=='__main__':main()
