"""Combine completed independently verified candidates; not a convergence claim."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy import sparse
from annual_inventory_master import audit as initial_master, solve_cut_master
from monthly_dispatch import digest, save


def matching_domain(reference,candidate):
    for name in ['bounds','rhs','limit']:
        if not np.array_equal(reference[name],candidate[name]):
            raise ValueError('Candidate inventory domain differs from reference')


def build(folders):
    if not folders or len(set(p.resolve() for p in folders))!=len(folders):raise ValueError('Distinct verified workspaces required')
    domains=[];cuts=[];evidence=[];best=None;seen=set()
    for folder in folders:
        # Rechecks workspace/source/block/witness hashes and objective floors.
        initial_master(folder)
        manifest=json.loads((folder/'master-workspace.json').read_text())
        audit_path=folder/'warm-audit'/'independent-witness-audit.json'
        audit=json.loads(audit_path.read_text())
        if audit['status']!='annual_fixed_inventory_feasible' or audit['verified_months']!=12 or audit['annual_feasible_cost_eur'] is None:
            raise ValueError('Every candidate must have twelve independently verified witnesses')
        with np.load(folder/'master-state.npz',allow_pickle=False) as saved:
            domain={name:saved[name].copy() for name in ['bounds','rhs','limit','warm_state_mwh']}
        if domains:
            matching_domain(domains[0],domain)
            for name in ['input_sha256']:
                if manifest[name]!=evidence[0]['manifest'][name]:raise ValueError('Candidate model source differs')
            for name in ['master-equality.npz','master-inequality.npz']:
                if manifest['workspace_sha256'][name]!=evidence[0]['manifest']['workspace_sha256'][name]:raise ValueError('Candidate chronology/reachability differs')
        if audit['warm_state_sha256'] in seen:raise ValueError('Duplicate inventory evaluation')
        seen.add(audit['warm_state_sha256']);domains.append(domain)
        for row in audit['rows']:
            receipt=json.loads((folder/'warm-audit'/f"{row['month']:02d}.json").read_text())
            if evidence:
                baseline=json.loads((folders[0]/f"{row['month']:02d}.json").read_text())
                if receipt['block_sha256']!=baseline['block_sha256']:raise ValueError('Candidate LP coefficients differ')
            cuts.append((row['month']-1,receipt['gradient_eur_per_mwh'],receipt['dual_intercept_eur']))
        evidence.append(dict(folder=str(folder.resolve()),manifest=manifest,audit_sha256=digest(audit_path),cost_eur=audit['annual_feasible_cost_eur']))
        if best is None or audit['annual_feasible_cost_eur']<evidence[best]['cost_eur']:best=len(evidence)-1
    parent=folders[best];domain=domains[best]
    floors=json.loads((parent/'objective-floors.json').read_text())
    result=solve_cut_master(domain['bounds'],sparse.load_npz(parent/'master-equality.npz'),domain['rhs'],
        sparse.load_npz(parent/'master-inequality.npz'),domain['limit'],[r['objective_floor_eur'] for r in floors['rows']],cuts,warm=domain['warm_state_mwh'])
    upper=evidence[best]['cost_eur']
    if result['lower_bound_eur']>upper+1e-7:raise ValueError('Combined annual bounds inconsistent')
    result.update(input_sha256=evidence[best]['manifest']['input_sha256'],annual_feasible_cost_eur=upper,
        annual_gap_eur=upper-result['lower_bound_eur'],candidate_count=len(folders),cut_count=len(cuts),
        witness_audit_sha256=evidence[best]['audit_sha256'],floor_audit_sha256=digest(parent/'objective-floors.json'),
        tool_sha256=digest(Path(__file__)),dependencies={name:digest(Path(__file__).with_name(name)) for name in ['annual_inventory_master.py','storage_coordinator.py','storage_master_dual.py']},
        candidates=[{k:v for k,v in item.items() if k!='manifest'} for item in evidence],
        scope='Combined verified objective cuts and best feasible incumbent; no annual convergence, empirical validation or investment claim.')
    save(parent/'multi-cut-master.json',result)
    return parent,result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--folders',type=Path,nargs='+',required=True)
    parent,result=build(parser.parse_args().folders)
    print(f"Combined {result['candidate_count']} verified candidates; gap €{result['annual_gap_eur']:.6f}; selected incumbent {parent}")
