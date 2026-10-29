"""Verify both named baseline witnesses and tracked catalog references."""
import json
from pathlib import Path
from generation_mix_2025 import ROOT, digest


def check():
    catalog=json.loads((ROOT/'baselines/catalog.json').read_text())
    if catalog['active']!='mixed_curve_fitting' or set(catalog['models'])!={'fast_dispatch_only','mixed_curve_fitting'}:
        raise ValueError('Unexpected baseline catalog')
    for name,row in catalog['models'].items():
        manifest=json.loads((ROOT/row['manifest']).read_text())
        if digest(ROOT/row['witness'])!=manifest['witness']['witness_sha256']:
            raise ValueError(f'{name}: witness hash mismatch')
        if abs(row['price_mae_eur_mwh']-manifest['prices']['equal_zone_mae'])>1e-9:
            raise ValueError(f'{name}: price score mismatch')
        if any(digest(ROOT/path)!=sha for path,sha in manifest['artifacts'].items()):
            raise ValueError(f'{name}: source artifact mismatch')
        if not (ROOT/row['report']).is_file():
            raise ValueError(f'{name}: report missing')
        print(name,row['price_mae_eur_mwh'],'verified artifacts',len(manifest['artifacts']))
    current=json.loads((ROOT/'config/active-research-baseline.json').read_text())
    if current['name']!=catalog['active']:
        raise ValueError('Active model name mismatch')

    # The witness-level check alone does not discover missing transitive source
    # files. Load both unchanged model input paths as a read-only replay gate.
    from solar_anchor_bids_2025 import model
    from monthly_lp_spline_inputs_2025 import aligned
    _, _, prior_lp = model()
    _, (schema, data, *_), _, _, _ = aligned()
    if prior_lp['ng'] != 799 or len(data['load']) != 8760 or len(schema['zones']) != 48:
        raise ValueError('Retained baseline input dimensions changed')
    print('baseline input loaders verified: 799 offers, 8760 hours, 48 zones')


if __name__=='__main__':
    check()
