"""Validate/render complete 100-update score exports; this does not run a model.

The model producer must independently audit its hourly witnesses. This reporting
contract rejects missing months, updates, zones or forward periods. It cannot
establish scientific validity from score summaries alone.
"""
import argparse
import calendar
import csv
import json
import math
from pathlib import Path


def hours(month):
    return calendar.monthrange(2025,month)[1]*24


def validate(payload,modeled_count=48,observed_count=41):
    if not payload.get('model_id') or not payload.get('score_solver_id'):
        raise ValueError('A frozen model and explicit scoring solver are required')
    if payload.get('audit_status')!='passed':
        raise ValueError('Producer witness audit must pass before final reporting')
    modeled=payload['modeled_zones'];observed=payload['observed_zones']
    if len(set(modeled))!=modeled_count or len(modeled)!=modeled_count:
        raise ValueError('Modeled-zone coverage differs')
    if len(observed)!=observed_count or len(set(observed))!=observed_count or not set(observed)<=set(modeled):
        raise ValueError('Observed-zone coverage differs')
    rows={}
    for row in payload['records']:
        month,iteration=row['month'],row['iteration']
        if month not in range(1,13) or iteration not in range(101):
            raise ValueError('Only twelve2025 months and iterations0..100 are valid')
        if (month,iteration) in rows:raise ValueError('Duplicate score point')
        if row['training_hours']!=hours(month):raise ValueError('Incomplete training coverage')
        for name in ['training_zone_mae','validation_zone_mae']:
            if name=='validation_zone_mae' and month==12:
                if row.get(name) is not None or row.get('validation_hours') is not None:
                    raise ValueError('December has noJanuary2026 validation')
                continue
            values=row[name]
            if len(values)!=observed_count or not all(math.isfinite(x) and x>=0 for x in values):
                raise ValueError('Missing, negative or nonfinite per-zone MAE')
        if month<12 and row['validation_hours']!=hours(month+1):
            raise ValueError('Forward coverage must be the entire next month')
        rows[month,iteration]=row
    if set(rows)!={(m,i) for m in range(1,13) for i in range(101)}:
        raise ValueError('All101 points for all12 months are required')
    return rows


def aggregate(rows,iteration,kind,matched=False):
    months=range(2,13) if matched else range(1,13)
    numerator=denominator=0.
    for month in months:
        if kind=='validation' and month==12:continue
        row=rows[month,iteration];weight=row[kind+'_hours']
        values=row[kind+'_zone_mae']
        numerator+=weight*sum(values)/len(values);denominator+=weight
    return numerator/denominator,int(denominator)


def render(payload,prefix):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['svg.fonttype']='none'
    rows=validate(payload);prefix=Path(prefix);prefix.parent.mkdir(parents=True,exist_ok=True)
    label=f"{payload['model_id']} · {payload['score_solver_id']} · price MAE EUR/MWh"
    series=[]
    for kind,matched,name,color in [('training',False,'Training: Jan–Dec','#64748b'),
                                   ('training',True,'Training: Feb–Dec','#2563eb'),
                                   ('validation',False,'Forward validation: Feb–Dec','#ea580c')]:
        values=[aggregate(rows,i,kind,matched)[0] for i in range(101)]
        series.append((name,color,values))
    fig,ax=plt.subplots(figsize=(11,4))
    for name,color,values in series:ax.plot(range(101),values,color=color,label=name)
    ax.set(xlabel='Parameter update',ylabel='Price MAE (EUR/MWh)',xlim=(0,100),ylim=(0,None),title=label)
    ax.grid(alpha=.2);ax.legend();fig.tight_layout()
    fig.savefig(prefix.with_name(prefix.name+'-aggregate.svg'));plt.close(fig)
    fig,axes=plt.subplots(3,4,figsize=(14,8),sharex=True)
    fig.suptitle(label+' · parameter updates 0–100')
    with prefix.with_name(prefix.name+'-monthly.csv').open('w',newline='') as f:
        writer=csv.writer(f,lineterminator='\n');writer.writerow(['fit_month','iteration','training_hours','training_mae','validation_month','validation_hours','validation_mae'])
        for month in range(1,13):
            training=[];validation=[]
            for i in range(101):
                row=rows[month,i];t=sum(row['training_zone_mae'])/len(payload['observed_zones']);training.append(t)
                v=sum(row['validation_zone_mae'])/len(payload['observed_zones']) if month<12 else None
                if v is not None:validation.append(v)
                writer.writerow([month,i,hours(month),t,month+1 if month<12 else '',hours(month+1) if month<12 else '',v if v is not None else ''])
            ax=axes.flat[month-1]
            ax.plot(range(101),training,color='#2563eb',label='Training')
            if month<12:ax.plot(range(101),validation,color='#ea580c',label='Next-month validation')
            title=f'{calendar.month_abbr[month]} fit → {calendar.month_abbr[month+1]} validation' if month<12 else 'Dec fit · validation unavailable'
            ax.set(title=title,xlim=(0,100),ylim=(0,None),xlabel='Parameter update',ylabel='Price MAE (EUR/MWh)')
            ax.grid(alpha=.2);ax.legend(fontsize=7)
    fig.tight_layout();fig.savefig(prefix.with_name(prefix.name+'-months.svg'));plt.close(fig)
    with prefix.with_name(prefix.name+'-aggregate.csv').open('w',newline='') as f:
        writer=csv.writer(f,lineterminator='\n');writer.writerow(['iteration','training_jan_dec_mae','training_feb_dec_mae','validation_feb_dec_mae'])
        for i in range(101):writer.writerow([i]+[values[i] for _,_,values in series])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scores',type=Path);parser.add_argument('output_prefix',type=Path)
    args=parser.parse_args();render(json.loads(args.scores.read_text()),args.output_prefix)
