"""Bounded mixed-technology complements around the €5bn best-found case."""
from __future__ import annotations

import fcntl
import json
from itertools import combinations
from pathlib import Path

from .budget_portfolio_search import BUDGET_MEUR, OUT, annual_reclear, digest_text, portfolio_model
from .budget_portfolio_improve import valid
from .evaluation import ANNUAL, physical_lp, saved_annual
from .run_scenario import profile_sources
from .source import ROOT, digest, grouped_fit_inputs

OUTDIR=OUT/'complements-v1'


def run():
    OUTDIR.mkdir(parents=True,exist_ok=True)
    with (OUTDIR/'job.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        best=json.loads((OUT/'pair-scan-v1/summary.json').read_text())
        original=json.loads((OUT/'manifest.json').read_text())
        by_id={row['id']:row for row in original['blocks']}
        manifest=dict(protocol='budget-mixed-complements-v1',
            source_sha256=digest(Path(__file__)),
            search_source_sha256=digest(ROOT/'baselines/compact/budget_portfolio_search.py'),
            storage_source_sha256=digest(ROOT/'baselines/compact/portfolio_storage.py'),
            pair_summary_sha256=digest(OUT/'pair-scan-v1/summary.json'),
            original_manifest_sha256=digest(OUT/'manifest.json'),
            baseline_witness_sha256=digest(ANNUAL/'annual.npz'),
            proposal='Best 14 solar+Greek wind; drop 2 of 5 declared leaves for one battery, or drop 3 for one second wind block')
        mp=OUTDIR/'manifest.json'
        if mp.exists() and json.loads(mp.read_text())!=manifest:
            raise ValueError('Changed complement search identity')
        mp.write_text(json.dumps(manifest,indent=2)+'\n')
        chosen=best['best_asset_ids']
        leaves=('solar:IT-CALA:2','solar:IT-SUD:1','solar:MK:1','solar:RO:1','solar:BG:2')
        proposals=[]
        for drop in combinations(leaves,2):
            for zone in ('IE-SEM','IT-SARD'):
                ids=tuple(sorted([x for x in chosen if x not in drop]+[f'battery:{zone}:1']))
                if valid(ids) and sum(by_id[x]['capex_m_eur'] for x in ids)<=BUDGET_MEUR:
                    proposals.append((ids,drop))
        for drop in combinations(leaves,3):
            for zone in ('EE','DK1'):
                ids=tuple(sorted([x for x in chosen if x not in drop]+[f'wind:{zone}:1']))
                if valid(ids) and sum(by_id[x]['capex_m_eur'] for x in ids)<=BUDGET_MEUR:
                    proposals.append((ids,drop))
        model=physical_lp();costs,baseline=saved_annual()
        schema,data,_=grouped_fit_inputs();sources=profile_sources(schema,data,model)
        rows=[]
        for idx,(ids,drop) in enumerate(proposals,1):
            key=digest_text('|'.join(ids));p=OUTDIR/f'{key}.json'
            if p.exists():
                row=json.loads(p.read_text())
                if row['manifest_sha256']!=digest(mp) or row['asset_ids']!=list(ids):
                    raise ValueError('Stale complement receipt')
            else:
                changed,changed_costs,batteries,_=portfolio_model(model,costs,[by_id[x] for x in ids],sources)
                metrics=annual_reclear(changed,changed_costs,batteries,baseline)
                row=dict(manifest_sha256=digest(mp),asset_ids=list(ids),dropped_ids=list(drop),
                    capex_m_eur=sum(by_id[x]['capex_m_eur'] for x in ids),**metrics)
                p.write_text(json.dumps(row,indent=2)+'\n')
            rows.append(row)
            print(f'{idx}/{len(proposals)} {ids[-1]} drop {drop}: {row["benefit_m_eur"]:.2f} M€/yr',flush=True)
        candidate=max(rows,key=lambda x:x['benefit_m_eur'])
        winning=(candidate if candidate['benefit_m_eur']>best['best_benefit_m_eur'] else None)
        summary=dict(manifest_sha256=digest(mp),tested_portfolios=len(rows),
            best_complement_asset_ids=candidate['asset_ids'],
            best_complement_benefit_m_eur=candidate['benefit_m_eur'],
            previous_best_benefit_m_eur=best['best_benefit_m_eur'],
            improved=winning is not None,
            best_asset_ids=winning['asset_ids'] if winning else best['best_asset_ids'],
            best_benefit_m_eur=winning['benefit_m_eur'] if winning else best['best_benefit_m_eur'],
            best_capex_m_eur=winning['capex_m_eur'] if winning else best['best_capex_m_eur'])
        (OUTDIR/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        return summary

if __name__=='__main__':
    print(json.dumps(run(),indent=2))
