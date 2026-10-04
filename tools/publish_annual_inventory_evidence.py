"""Publish compact verified inventory evidence, never a matched annual benchmark."""
import argparse
import json
import math
from pathlib import Path
from monthly_dispatch import digest, save


def publish(folder,output):
    witness_path=folder/'warm-audit'/'independent-witness-audit.json'
    master_path=folder/'initial-cut-master.json'
    witness=json.loads(witness_path.read_text());master=json.loads(master_path.read_text())
    if witness['status']!='annual_fixed_inventory_feasible' or witness['verified_months']!=12 or [r['month'] for r in witness['rows']]!=list(range(1,13)):
        raise ValueError('Twelve independently replayed chronological witnesses required')
    if master['witness_audit_sha256']!=digest(witness_path) or master['input_sha256']!=witness['input_sha256'] or master['annual_feasible_cost_eur']!=witness['annual_feasible_cost_eur']:
        raise ValueError('Annual master does not match verified witnesses')
    if master['tool_sha256']!=digest(Path(__file__).with_name('annual_inventory_master.py')):
        raise ValueError('Annual master implementation changed')
    upper=witness['annual_feasible_cost_eur'];lower=master['lower_bound_eur']
    if upper is None or not math.isfinite(upper) or not math.isfinite(lower) or upper<=0 or lower>upper:raise ValueError('Invalid annual bounds')
    rows=[]
    for row in witness['rows']:
        path=folder/'warm-audit'/f"{row['month']:02d}.json";receipt=json.loads(path.read_text())
        if digest(path)!=row['receipt_sha256'] or digest(path.parent/receipt['witness_file'])!=row['witness_sha256']:
            raise ValueError('Verified witness changed')
        rows.append(dict(**row,elapsed_seconds=receipt['elapsed_seconds'],peak_rss_bytes=receipt['peak_rss_bytes']))
    result=dict(schema_version=1,year=2025,hours=8760,status='verified_fixed_inventory_feasible_not_converged',
        annual_feasible_cost_eur=upper,conservative_lower_bound_eur=lower,absolute_gap_eur=upper-lower,
        relative_gap=(upper-lower)/upper,months=rows,input_sha256=witness['input_sha256'],
        warm_state_sha256=witness['warm_state_sha256'],witness_audit_sha256=digest(witness_path),
        master_diagnostic_sha256=digest(master_path),publication_tool_sha256=digest(Path(__file__)),
        limitations=['Fixed chronological warm inventories; not optimised annual inventories.',
          'Floating-point numerical lower bound, not interval certification.',
          'No matched annual native/fast investment benchmark or ENTSO-E empirical validation.',
          '2024 country nuclear availability remains a declared proxy for 2025.'],
        scope='Annual feasible dispatch evidence and initial cut relaxation; separate from 2013 weekly and 2025 conditional-window benchmarks.')
    save(output,result);return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--folder',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=publish(args.folder,args.output)
    print(f"Annual feasible evidence prepared; relative bound gap {result['relative_gap']:.2%}; not converged.")
