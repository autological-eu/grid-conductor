"""Publish an explicit linked-dispatch input without reconstructing weather.

Consumes tools/market_model.py input, NOT solved hourly dispatch CSVs.
Unknown/unsupported fields fail closed instead of being silently dropped.
"""
import argparse
import hashlib
import json
from pathlib import Path
from market_model import validate

FIELDS = {'timestamps', 'interval_hours', 'zones', 'load_mw', 'external_net_import_mw',
          'generators', 'edges', 'storage', 'flow_based_regions', 'unserved_cost_eur_mwh'}
DOCUMENTATION = {'schema_version', 'provenance', 'assumptions', 'observed_price_eur_mwh', 'emission_basis'}

def export(source, dataset_id, assumptions):
    raw = source.read_bytes()
    data = json.loads(raw)
    unknown = set(data) - FIELDS - DOCUMENTATION
    if unknown:
        raise ValueError(f'Unsupported input fields: {sorted(unknown)}')
    allowed = {
        'generators': {'id', 'zone', 'max_mw', 'min_mw', 'cost_eur_mwh', 'co2_t_per_mwh', 'energy_budget_mwh', 'ramp_mw_per_hour'},
        'edges': {'id', 'a', 'b', 'ab_mw', 'ba_mw'},
        'storage': {'id', 'zone', 'power_mw', 'energy_mwh', 'initial_mwh', 'terminal_mwh', 'charge_efficiency', 'discharge_efficiency', 'throughput_cost_eur_mwh', 'charge_power_mw', 'inflow_mw', 'standing_loss', 'cyclic'},
        'flow_based_regions': {'id', 'zones', 'constraints'},
    }
    for key, fields in allowed.items():
        for item in data.get(key, []):
            extra = set(item) - fields
            if extra:
                raise ValueError(f'Unsupported {key} fields: {sorted(extra)}')
    for region in data.get('flow_based_regions', []):
        for constraint in region['constraints']:
            if set(constraint) != {'id', 'interval', 'ptdf', 'ram_mw'}:
                raise ValueError('Unsupported PTDF restriction')
    validate(data)
    if not assumptions:
        raise ValueError('Explicit modelling assumptions required')
    output = {key: value for key, value in data.items() if key in FIELDS}
    output.setdefault('storage', [])
    output.setdefault('flow_based_regions', [])
    output.update(schema_version=data.get('schema_version',1), dataset_id=dataset_id, provenance=dict(
        source=f'Offline linked-dispatch input: {source.name}',
        source_sha256=hashlib.sha256(raw).hexdigest(), assumptions=assumptions))
    return output

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--dataset-id', required=True)
    parser.add_argument('--assumption', action='append', required=True)
    args = parser.parse_args()
    output = export(args.input, args.dataset_id, args.assumption)
    # Browser schema independently checks the versioned publication on import.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, allow_nan=False, separators=(',', ':'))+'\n')
    print(json.dumps(dict(status='experimental_not_validated', intervals=len(output['timestamps']),
        sha256=output['provenance']['source_sha256'])))
