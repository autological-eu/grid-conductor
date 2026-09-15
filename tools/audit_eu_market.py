"""Coverage and historical energy reconciliation before EU dispatch (ENTSO-E only)."""
import argparse
import hashlib
import json
from pathlib import Path
from carbon_pilot import ROOT


def audit_bank(bank):
    from assemble_eu_market import to_hourly
    import calendar
    year, month = map(int, bank['month'].split('-'))
    hours = calendar.monthrange(year, month)[1] * 24
    coverage, hourly, issues = {}, {}, []

    def register(name, series, required=True):
        try:
            values = to_hourly(series, hours, name) if series is not None else [None]*hours
        except ValueError as error:
            issues.append(str(error)); values = [None]*hours
        count = sum(v is not None for v in values)
        coverage[name] = dict(observed_hours=count, expected_hours=hours, coverage=count/hours)
        hourly[name] = values
        if not name.startswith('price/') and any(v is not None and v < 0 for v in values):
            issues.append('Negative quantity '+name)
        if required and count != hours: issues.append('Incomplete '+name)
        return values

    if bank.get('schema_version') != 2: issues.append('Legacy bank must be recollected')
    if bank.get('caps_synthetic'): issues.append('Synthetic capacities are not historical constraints')
    for z in bank['zones']:
        register('load/'+z, bank.get('load_mw', {}).get(z))
        register('price/'+z, bank.get('prices', {}).get(z), False)
        generation = bank.get('generation_mw', {}).get(z, {})
        if not generation: issues.append('Missing generation/'+z)
        for fuel, series in generation.items(): register('gen/'+z+'/'+fuel, series)
        for fuel, series in bank.get('storage_charge_mw', {}).get(z, {}).items():
            register('charge/'+z+'/'+fuel, series)
        domain = bank.get('zone_domains', {}).get(z, {})
        if domain.get('gen') and domain['gen'] != domain['price']:
            issues.append('Unreconciled generation geography/'+z)
    internal = [tuple(e) for e in bank.get('interior_borders', [])]
    external = [tuple(e) for e in bank.get('exterior_borders', [])]
    required_flows = set()
    for a,b in internal+external:
        required_flows.update([a+'>'+b,b+'>'+a])
    for direction in sorted(required_flows):
        register('flow/'+direction, bank.get('flows_mw', {}).get(direction))
    for a,b in internal:
        for direction in [a+'>'+b,b+'>'+a]:
            register('capacity/'+direction, bank.get('caps_mw', {}).get(direction))
    balances = {}
    for z in bank['zones']:
        terms = [(hourly['load/'+z], -1)]
        terms += [(v,1) for k,v in hourly.items() if k.startswith('gen/'+z+'/')]
        terms += [(v,-1) for k,v in hourly.items() if k.startswith('charge/'+z+'/')]
        for direction in required_flows:
            a,b=direction.split('>')
            if z in (a,b):terms.append((hourly['flow/'+direction],1 if b==z else -1))
        residuals = [sum(v[h]*sign for v,sign in terms) if all(v[h] is not None for v,_ in terms) else None for h in range(hours)]
        valid = [abs(v) for v in residuals if v is not None]
        demand = sum(hourly['load/'+z][h] for h,v in enumerate(residuals) if v is not None)
        share = sum(valid)/demand if demand else None
        balances[z] = dict(observed_hours=len(valid), expected_hours=hours,
            residual_mae_mw=sum(valid)/len(valid) if valid else None,
            absolute_residual_share=share, hourly_residual_mw=residuals)
        if len(valid)!=hours or share is None or share>.05:issues.append('Historical balance gate/'+z)
    return dict(schema_version=1, source='ENTSO-E Transparency API', month=bank['month'],
        bank_sha256=hashlib.sha256(json.dumps(bank,sort_keys=True,allow_nan=False).encode()).hexdigest(),
        input_gate_passed=not issues, decision='inputs_ready_for_experimental_dispatch' if not issues else 'blocked_input_quality',
        annual_opportunity_meur=None, issues=sorted(set(issues)), coverage=coverage, balances=balances,
        policy=dict(required_hour_coverage=1.0, max_absolute_balance_share=.05,
            interpolation=False, mirrored_capacity=False, synthetic_capacity=False,
            storage='Reported charging and discharge included; absent fuel categories assumed not reported, not verified installed capacity',
            constraints='A61 estimated day-ahead NTC is a transport-model input, not complete historical market coupling constraints'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bank',type=Path,default=ROOT/'data/eu-market/bank-2026-08-v2.json')
    p.add_argument('--output',type=Path,default=ROOT/'public/research/eu-input-quality.json')
    args=p.parse_args()
    report=audit_bank(json.loads(args.bank.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,allow_nan=False,indent=2))
    print(json.dumps(dict(decision=report['decision'],issues=len(report['issues']),output=str(args.output))))


if __name__=='__main__':main()
