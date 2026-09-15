"""Small ERA5 access check before requesting the full January cutout."""
import json
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]

if __name__ == '__main__':
    config = yaml.safe_load((Path.home()/'.cdsapirc').read_text())
    if not isinstance(config, dict) or not config.get('key') or not config.get('url'):
        raise ValueError('CDS configuration is malformed; contents withheld')
    import cdsapi
    client = cdsapi.Client(quiet=True, debug=False)
    destination = ROOT/'data/pypsa-eur/cds-probe.nc'
    try:
        client.retrieve('reanalysis-era5-single-levels', {
            'product_type': ['reanalysis'], 'variable': ['2m_temperature'],
            'year': ['2026'], 'month': ['01'], 'day': ['01'], 'time': ['00:00'],
            'data_format': 'netcdf', 'download_format': 'unarchived',
            'area': [51, 9, 50, 10],
        }, str(destination))
        print(json.dumps({'status': 'downloaded', 'bytes': destination.stat().st_size}))
    except Exception as exc:
        detail = str(exc).replace(str(config['key']), '[redacted]')
        print(json.dumps({'status': 'failed', 'detail': detail}))
        raise SystemExit(1)
