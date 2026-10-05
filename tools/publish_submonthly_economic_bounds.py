"""Publish replayed shorter-block annual bounds, not a validated annual benchmark."""
import argparse,json,math
from pathlib import Path
from monthly_dispatch import digest,save
from submonthly_inventory_driver import verify_annual,verify_master
import numpy as np
from scipy import sparse
from annual_inventory_workspace import validate_warm


def summary(annual,master,upper,lower):
    if (annual['status']!='independently_replayed_economic_annual_feasible'
            or annual['year']!=2025 or annual['hours']!=8760 or annual['blocks']!=59
            or annual['input_sha256']!=master['input_sha256']
            or [row['index'] for row in annual['rows']]!=list(range(59))):
        raise ValueError('Complete source-matched economic annual replay required')
    if not all(math.isfinite(v) for v in (upper,lower)) or upper<=0 or lower>upper:
        raise ValueError('Consistent finite original-unit annual bounds required')
    if upper!=annual['annual_feasible_cost_eur']:raise ValueError('Annual upper bound differs')
    for row in annual['rows']:
        for key in ('max_equality_residual','max_inequality_violation','max_bound_violation'):
            value=row[key]
            if not math.isfinite(value) or value<0 or value>1e-7:raise ValueError('Original-unit annual primal acceptance gate fails')
    return dict(schema_version=1,status='replayed_economic_annual_bounds_not_validated',year=2025,hours=8760,blocks=59,
        input_sha256=annual['input_sha256'],annual_feasible_cost_eur=upper,lower_support_eur=lower,
        absolute_gap_eur=upper-lower,relative_gap=(upper-lower)/upper,
        cyclic_closure_residual_mwh=annual['cyclic_closure_residual_mwh'],
        maximum_primal_equality_residual=max(row['max_equality_residual'] for row in annual['rows']),
        maximum_primal_inequality_violation=max(row['max_inequality_violation'] for row in annual['rows']),
        maximum_primal_bound_violation=max(row['max_bound_violation'] for row in annual['rows']),
        methods=dict(interval_certificate=False,annual_convergence_claimed=False,
            native_fast_annual_comparison_verified=False,entsoe_empirical_validation_verified=False,
            paired_annual_investment_comparison_verified=False),
        quantity='Fixed-asset full-year model operating cost in EUR, not investment benefit or congestion rent',
        limitations=['One exact linked chronological inventory state; original renewable availability preserved.',
            'Floating-point independently replayed lower support; not interval certification.',
            'A finite gap is reported without claiming an annual optimum or observed-market agreement.',
            'The source has zero operational carbon price and a 2024 nuclear availability proxy.',
            'Separate from the 2013 weekly and 2025 conditional-window benchmarks.'])


def publish(folder,master_path,workspace,input_path,output):
    domain_path=workspace/'master-workspace.json';domain=json.loads(domain_path.read_text())
    if domain['input_sha256']!=digest(input_path):raise ValueError('Original annual input changed')
    for name,value in domain['workspace_sha256'].items():
        if digest(workspace/name)!=value:raise ValueError('Annual inventory workspace changed')
    upper=verify_annual(folder,domain);lower=verify_master(master_path,domain['input_sha256'])
    annual_path=folder/'annual-replay.json';annual=json.loads(annual_path.read_text());master=json.loads(master_path.read_text())
    with np.load(workspace/'master-state.npz',allow_pickle=False) as data:
        bounds=data['bounds'].copy();rhs=data['rhs'].copy();limits=data['limit'].copy()
    with np.load(folder/'annual-state.npz',allow_pickle=False) as data:state=data['inventories_mwh'].copy()
    equality=sparse.load_npz(workspace/'master-equality.npz')
    state=validate_warm(state,bounds,equality,rhs)
    if np.max(sparse.load_npz(workspace/'master-inequality.npz')@state-limits,initial=0.)>1e-7:
        raise ValueError('Annual state no longer satisfies necessary envelopes')
    closure=float(np.max(abs(equality@state-rhs),initial=0.))
    if closure!=annual['cyclic_closure_residual_mwh']:raise ValueError('Cyclic closure no longer reproduces')
    result=summary(annual,master,upper,lower)
    result.update(annual_replay_sha256=digest(annual_path),annual_state_sha256=annual['annual_state_sha256'],
        master_receipt_sha256=digest(master_path),master_dual_replay_sha256=digest(master_path.with_suffix('.dual-replay.json')),
        master_witness_sha256=digest(master_path.with_suffix('.witness.npz')),
        inventory_workspace_sha256=digest(domain_path),publication_tool_sha256=digest(Path(__file__)),
        source_replay_tool_sha256=digest(Path(__file__).with_name('submonthly_inventory_driver.py')))
    timings=[]
    for row in annual['rows']:
        status_path=folder/f"{row['index']:02d}"/'status.json'
        status=json.loads(status_path.read_text())
        if status['status']!='conditional_candidate_check_complete' or status['returncode']!=0:
            raise ValueError('Worker performance receipt is incomplete')
        seconds=status['elapsed_seconds'];rss=status['peak_rss_bytes']
        if not math.isfinite(seconds) or seconds<0 or type(rss) is not int or rss<=0:
            raise ValueError('Invalid worker performance receipt')
        timings.append(dict(index=row['index'],elapsed_seconds=seconds,peak_rss_bytes=rss,status_sha256=digest(status_path)))
    result['conditional_worker_performance']=dict(rows=timings,
        summed_elapsed_seconds=math.fsum(row['elapsed_seconds'] for row in timings),
        maximum_sampled_worker_rss_bytes=max(row['peak_rss_bytes'] for row in timings),
        scope='Conditional worker runs only; excludes preparation, master solves, independent replays and complete coordination wall time. Peak RSS is sampled, not an exact memory maximum.')
    save(output,result);return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('folder','master','workspace','input','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();result=publish(args.folder,args.master,args.workspace,args.input,args.output)
    print(f"Replayed annual bounds prepared, gap {result['relative_gap']:.2%}; empirical/investment gates remain open.")
