"""Bounded local improvement of the source-hashed 2025 budget search.

Each proposal is a fresh 8,760-hour reclear on the same physical LP.  This
remains a best-found finite search, not a certificate of global optimality.
"""
from __future__ import annotations

import fcntl
import json
from itertools import combinations
from pathlib import Path

from .budget_portfolio_search import (
    BUDGET_MEUR, OUT, annual_reclear, digest_text, portfolio_model,
)
from .evaluation import ANNUAL, physical_lp, saved_annual
from .run_scenario import profile_sources
from .source import ROOT, digest, grouped_fit_inputs

IMPROVE = OUT / 'local-improvement-v1'


def valid(ids):
    selected=set(ids)
    return all(x.replace(':2', ':1') in selected for x in selected if x.endswith(':2'))


def run():
    IMPROVE.mkdir(parents=True, exist_ok=True)
    with (IMPROVE/'job.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        parent=json.loads((OUT/'summary.json').read_text())
        parent_manifest=json.loads((OUT/'manifest.json').read_text())
        broad=json.loads((OUT/'broad_screen.json').read_text())
        by_id={x['id']:x for x in (*parent_manifest['blocks'], *broad)}
        manifest=dict(protocol='budget-local-improvement-v1',
            source_sha256=digest(Path(__file__)),
            search_source_sha256=digest(ROOT/'baselines/compact/budget_portfolio_search.py'),
            storage_source_sha256=digest(ROOT/'baselines/compact/portfolio_storage.py'),
            parent_summary_sha256=digest(OUT/'summary.json'),
            parent_manifest_sha256=digest(OUT/'manifest.json'),
            baseline_witness_sha256=digest(ANNUAL/'annual.npz'),
            scope='Finite one/two-block substitutions around greedy and wind branches; original 2025 source profiles')
        p=IMPROVE/'manifest.json'
        if p.exists() and json.loads(p.read_text())!=manifest:
            raise ValueError('Changed search identity')
        p.write_text(json.dumps(manifest,indent=2)+'\n')
        base_model=physical_lp();base_costs,baseline=saved_annual()
        schema,data,_=grouped_fit_inputs()
        sources=profile_sources(schema,data,base_model)
        greedy=parent['selected_ids']
        solar14=parent['frontier'][13]['asset_ids']
        proposals={}
        def add(ids,label):
            ids=tuple(sorted(ids))
            if not valid(ids):return
            if sum(by_id[x]['capex_m_eur'] for x in ids)>BUDGET_MEUR+1e-7:return
            proposals.setdefault(ids,[]).append(label)
        add(greedy,'greedy')
        for zone in ('GR','EE','DK1','IE-SEM','PL'):
            add([*solar14,f'wind:{zone}:1'],f'wind-{zone}-after-14-solar')
        for zone in ('IE-SEM','IT-SARD','LT','EE','LV'):
            add([*solar14,f'battery:{zone}:1'],f'battery-{zone}-after-14-solar')
        # Replace pairs of the last six selected solar blocks with one wind
        # block.  This tests the discrete budget effect missed by greedy ratio.
        last_solar=[step['added_id'] for step in parent['frontier'][10:]]
        for a,b in combinations(last_solar,2):
            for zone in ('GR','EE'):
                add([x for x in greedy if x not in (a,b)]+[f'wind:{zone}:1'],
                    f'greedy-drop-{a}-{b}-wind-{zone}')
        # Screened candidates just outside the original top-ten solar list.
        outside=('IT-CSUD','IE-SEM','HR','SI','HU')
        leaves=('solar:IT-SUD:2','solar:IT-SICI:1','solar:IT-CALA:2',
                'solar:MK:1','solar:RO:1')
        for old in leaves:
            for zone in outside:
                add([x for x in solar14 if x!=old]+['wind:GR:1',f'solar:{zone}:1'],
                    f'wind-branch-replace-{old}-with-{zone}')
        results=[]
        for idx,(ids,labels) in enumerate(proposals.items(),1):
            key=digest_text('|'.join(ids));receipt=IMPROVE/f'{key}.json'
            if receipt.exists():
                row=json.loads(receipt.read_text())
                if row['manifest_sha256']!=digest(p) or row['asset_ids']!=list(ids):
                    raise ValueError('Stale improvement receipt')
            else:
                prior=OUT/'portfolios'/f'{key}.json'
                if prior.exists():
                    old=json.loads(prior.read_text())
                    if old['manifest_sha256']!=digest(OUT/'manifest.json') or old['asset_ids']!=list(ids):
                        raise ValueError('Stale parent receipt')
                    metrics={k:old[k] for k in ('benefit_m_eur','annual_cost_eur',
                        'max_primal_residual','max_stock_error_mwh','charge_twh',
                        'discharge_twh','wall_seconds','battery_count','hours','emergency_mwh')}
                    origin=str(prior.relative_to(ROOT))
                else:
                    model,costs,batteries,_=portfolio_model(base_model,base_costs,
                        [by_id[x] for x in ids],sources)
                    metrics=annual_reclear(model,costs,batteries,baseline)
                    origin='fresh full-year reclear'
                row=dict(manifest_sha256=digest(p),asset_ids=list(ids),
                    capex_m_eur=sum(by_id[x]['capex_m_eur'] for x in ids),
                    labels=labels,origin=origin,**metrics)
                receipt.write_text(json.dumps(row,indent=2)+'\n')
            results.append(row)
            best=max(results,key=lambda x:x['benefit_m_eur'])
            print(f'{idx}/{len(proposals)} {labels[0]}: {row["benefit_m_eur"]:.2f} M€/yr; best {best["benefit_m_eur"]:.2f}',flush=True)
        best=max(results,key=lambda x:x['benefit_m_eur'])
        summary=dict(manifest_sha256=digest(p),tested_portfolios=len(results),
            best_asset_ids=best['asset_ids'],best_capex_m_eur=best['capex_m_eur'],
            best_benefit_m_eur=best['benefit_m_eur'],
            unspent_m_eur=BUDGET_MEUR-best['capex_m_eur'],
            greedy_benefit_m_eur=parent['modeled_annual_offer_cost_reduction_m_eur'],
            best_receipt=str((IMPROVE/f'{digest_text("|".join(best["asset_ids"]))}.json').relative_to(ROOT)))
        (IMPROVE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        return summary

if __name__=='__main__':
    print(json.dumps(run(),indent=2))
