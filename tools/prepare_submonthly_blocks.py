"""Prepare shorter chronological native LP blocks; no dispatch/annual claim."""
import argparse
import calendar
import json
from pathlib import Path
import subprocess
import sys
import time
from monthly_dispatch import digest, save
from audit_annual_warm_state import guard_reason, terminate_worker


def partitions(year, max_hours):
    if year != 2025 or not 24 <= max_hours <= 168 or max_hours % 24:
        raise ValueError('2025 whole-day sub-blocks of at most 168h required')
    result=[];offset=0
    for month in range(1,13):
        end=offset+calendar.monthrange(year,month)[1]*24
        while offset<end:
            last=min(end,offset+max_hours)
            result.append(dict(index=len(result),month=month,start_hour=offset,end_hour_exclusive=last,hours=last-offset))
            offset=last
    return result


def worker(args):
    import pypsa
    from prepare_annual_coordination import validate_calendar
    from pypsa_storage_blocks import block
    from disk_storage_blocks import save_block
    rows=partitions(2025,args.max_hours);row=rows[args.index]
    n=pypsa.Network(args.input);validate_calendar(n,2025)
    ignored=n.global_constraints.index.tolist()
    n.global_constraints.drop(n.global_constraints.index,inplace=True)
    snapshots=n.snapshots[row['start_hour']:row['end_hour_exclusive']]
    prepared=block(n,snapshots,args.index,len(rows))
    path=args.output/'block.npz';save_block(path,prepared)
    save(args.output/'block.json',dict(**row,year=2025,max_hours=args.max_hours,block_count=len(rows),
         input_sha256=digest(args.input),block_sha256=digest(path),producer_sha256=digest(Path(__file__)),
         dependencies={name:digest(Path(__file__).with_name(name)) for name in ['pypsa_storage_blocks.py','prepare_annual_coordination.py','disk_storage_blocks.py']},
         start=str(snapshots[0]),last=str(snapshots[-1]),shared_variables=prepared.coupling.shape[1],
         storage_ids=n.storage_units.index.tolist(),source_cyclic=n.storage_units.cyclic_state_of_charge.tolist(),
         storage_capacity_mwh=(n.storage_units.p_nom*n.storage_units.max_hours).tolist(),
         ignored_fixed_transmission_volume_constraints=ignored,
         scope='Prepared native coefficients only. Inventory is shared across all sub-blocks; no reset, solve, annual optimum or equivalence claim.'))


def run(args):
    rows=partitions(2025,args.max_hours)
    if not 0<=args.index<len(rows):raise ValueError('Invalid sub-block index')
    if args.output.exists():raise ValueError('Existing evidence must not be overwritten')
    args.output.mkdir(parents=True)
    save(args.output/'partition-plan.json',dict(year=2025,blocks=rows,input_sha256=digest(args.input),
         scope='Month boundaries retained; storage must link every boundary and close at the annual boundary.'))
    with (args.output/'preparation.log').open('w') as log:
        child=subprocess.Popen([sys.executable,__file__,'--input',str(args.input),'--output',str(args.output),
                                '--index',str(args.index),'--max-hours',str(args.max_hours),'--worker'],
                                stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        save(args.output/'status.json',dict(status='preparing_submonthly_block',pid=child.pid));peak=0;started=time.monotonic()
        while child.poll() is None:
            try:rss=sum(int(line.split()[1])*1024 for line in Path(f'/proc/{child.pid}/status').read_text().splitlines() if line.startswith('VmRSS:'))
            except FileNotFoundError:rss=0
            peak=max(peak,rss);reason=guard_reason(time.monotonic()-started,rss,6.,300.)
            if reason:terminate_worker(child);save(args.output/'status.json',dict(status=reason,peak_rss_bytes=peak));return
            time.sleep(1)
        save(args.output/'status.json',dict(status='prepared_requires_equivalence_audit' if child.returncode==0 else 'failed',
             returncode=child.returncode,peak_rss_bytes=peak,elapsed_seconds=time.monotonic()-started))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--index',type=int,required=True);parser.add_argument('--max-hours',type=int,default=168)
    parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    args.input=args.input.resolve();args.output=args.output.resolve();worker(args) if args.worker else run(args)
