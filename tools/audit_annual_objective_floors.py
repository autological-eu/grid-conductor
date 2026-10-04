"""Hash-check source-bounded nonnegative monthly objective floors; no dispatch."""
import argparse
from pathlib import Path
from disk_storage_blocks import load_block
from monthly_dispatch import digest, save
from storage_objective_floor import nonnegative_objective_floor
import json


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',type=Path,required=True)
    args=parser.parse_args()
    rows=[]
    master=json.loads((args.folder/'master-workspace.json').read_text())
    for month in range(1,13):
        receipt=json.loads((args.folder/f'{month:02d}.json').read_text())
        path=args.folder/f'{month:02d}.npz'
        if receipt['input_sha256']!=master['input_sha256'] or digest(path)!=receipt['block_sha256']:
            raise ValueError('Monthly/source fingerprint mismatch')
        prepared=load_block(path)
        floor=nonnegative_objective_floor(prepared)
        rows.append(dict(month=month,block_sha256=receipt['block_sha256'],objective_floor_eur=floor))
        del prepared
        print(f'Month {month}: source-bounded objective floor {floor}',flush=True)
    save(args.folder/'objective-floors.json',dict(status='source_nonnegative_floors_audited',
         input_sha256=master['input_sha256'],rows=rows,
         dependencies={name:digest(Path(__file__).with_name(name)) for name in ['storage_objective_floor.py','check_storage_dual_bounds.py','disk_storage_blocks.py']},
         scope='Conservative cost floors from nonnegative source bounds; no dispatch or annual gap'))
