"""Explicit projection between monthly and month-aligned submonthly inventories."""
import calendar
import numpy as np
from prepare_submonthly_blocks import partitions


def boundary_positions(rows,max_hours=168):
    if rows!=partitions(2025,max_hours):
        raise ValueError('Exact supported chronological partition required')
    hours=[0];offset=0
    for month in range(1,13):
        offset+=calendar.monthrange(2025,month)[1]*24;hours.append(offset)
    new_hours=[0]+[row['end_hour_exclusive'] for row in rows]
    lookup={hour:i for i,hour in enumerate(new_hours)}
    return [lookup[hour] for hour in hours]


def project_state(state,storage_units,rows,max_hours=168):
    values=np.asarray(state,dtype=float)
    if storage_units<1 or values.shape!=((len(rows)+1)*storage_units,) or not np.isfinite(values).all():
        raise ValueError('Finite correctly sized submonthly inventory vector required')
    positions=boundary_positions(rows,max_hours)
    return values.reshape(len(rows)+1,storage_units)[positions].ravel()


def lift_gradient(gradient,storage_units,rows,max_hours=168):
    values=np.asarray(gradient,dtype=float)
    if storage_units<1 or values.shape!=(13*storage_units,) or not np.isfinite(values).all():
        raise ValueError('Finite correctly sized monthly cut gradient required')
    positions=boundary_positions(rows,max_hours)
    result=np.zeros((len(rows)+1,storage_units))
    result[positions]=values.reshape(13,storage_units)
    return result.ravel()


def month_blocks(month,rows,max_hours=168):
    boundary_positions(rows,max_hours)
    if not 1<=month<=12:raise ValueError('Invalid calendar month')
    return [row['index'] for row in rows if row['month']==month]
