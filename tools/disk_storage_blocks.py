"""Disk-backed LP blocks: iteration retains only the currently loaded block.

NPZ contains numeric arrays only; no pickle or executable object serialization.
These are internal prepared LP coefficients, not published model results.
"""
import json
from pathlib import Path
from collections.abc import Sequence
import numpy as np
from scipy import sparse
from storage_coordinator import Block


def save_block(path, block):
    path=Path(path)
    arrays={'cost':np.asarray(block.cost),'rhs':np.asarray(block.rhs)}
    matrices={}
    for name in ('equality','coupling','inequality','inequality_coupling'):
        value=getattr(block,name)
        if value is None:
            matrices[name]=None
            continue
        matrix=sparse.csr_matrix(value)
        matrices[name]=list(matrix.shape)
        arrays[name+'_data']=matrix.data
        arrays[name+'_indices']=matrix.indices
        arrays[name+'_indptr']=matrix.indptr
    arrays['metadata']=np.array(json.dumps({'version':1,'bounds':block.bounds,'matrices':matrices,'has_limit':block.limit is not None}))
    if block.limit is not None:arrays['limit']=np.asarray(block.limit)
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    with temp.open('wb') as stream:np.savez_compressed(stream,**arrays)
    temp.replace(path)


def load_block(path):
    with np.load(path,allow_pickle=False) as data:
        meta=json.loads(str(data['metadata']))
        if meta['version']!=1:raise ValueError('Unsupported block archive version')
        matrices={}
        for name,shape in meta['matrices'].items():
            matrices[name]=None if shape is None else sparse.csr_matrix((data[name+'_data'],data[name+'_indices'],data[name+'_indptr']),shape=tuple(shape))
        return Block(cost=data['cost'].copy(),bounds=[tuple(v) for v in meta['bounds']],rhs=data['rhs'].copy(),limit=data['limit'].copy() if meta['has_limit'] else None,**matrices)


class DiskBlocks(Sequence):
    """Reload blocks on demand; retain no in-memory matrix cache."""
    def __init__(self,paths):self.paths=tuple(Path(p) for p in paths)
    def __len__(self):return len(self.paths)
    def __getitem__(self,index):
        if isinstance(index,slice):return DiskBlocks(self.paths[index])
        return load_block(self.paths[index])
