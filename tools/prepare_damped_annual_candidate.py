"""Prepare a conservative trial toward a master proposal; no feasibility claim."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy import sparse
from prepare_annual_inventory_candidate import prepare, checked_candidate
from monthly_dispatch import digest, save


def interpolate(anchor, proposal, fraction):
    anchor = np.asarray(anchor, dtype=float)
    proposal = np.asarray(proposal, dtype=float)
    if not 0 < fraction <= 1 or anchor.shape != proposal.shape or not np.isfinite(anchor).all() or not np.isfinite(proposal).all():
        raise ValueError('Finite matched states and a fraction in (0,1] required')
    return anchor + fraction * (proposal - anchor)


def prepare_trial(parent, output, fraction):
    proposal = json.loads((parent/'multi-cut-master.json').read_text())
    with np.load(parent/'master-state.npz', allow_pickle=False) as data:
        state = interpolate(data['warm_state_mwh'], proposal['proposal_mwh'], fraction)
        checked_candidate(state, data['bounds'], sparse.load_npz(parent/'master-equality.npz'), data['rhs'],
                          sparse.load_npz(parent/'master-inequality.npz'), data['limit'])
    # Existing preparation verifies all source/proposal/incumbent hashes before
    # creating this new, isolated workspace. No prior candidate is overwritten.
    prepare(parent, output, 'multi-cut-master.json')
    with np.load(output/'master-state.npz', allow_pickle=False) as data:
        arrays = {name: data[name].copy() for name in data.files}
    arrays['warm_state_mwh'] = state
    temporary = output/'master-state.tmp'
    with temporary.open('wb') as stream:
        np.savez_compressed(stream, **arrays)
    temporary.replace(output/'master-state.npz')
    master = json.loads((output/'master-workspace.json').read_text())
    master['workspace_sha256']['master-state.npz'] = digest(output/'master-state.npz')
    master['damped_trial'] = dict(fraction=fraction, producer_sha256=digest(Path(__file__)),
                                anchor_state_sha256=digest(parent/'master-state.npz'),
                                scope='Heuristic evaluation point only; unrestricted master lower bound unchanged. Full monthly feasibility replay required.')
    save(output/'master-workspace.json', master)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fraction', type=float, required=True)
    args = parser.parse_args()
    prepare_trial(args.parent.resolve(), args.output.resolve(), args.fraction)
    print('Damped inventory trial prepared; no dispatch feasibility or convergence claim.')
