"""Full valid two-solar-for-Greek-wind neighborhood of the greedy portfolio."""
from __future__ import annotations

import fcntl
import json
from itertools import combinations
from pathlib import Path

from .budget_portfolio_search import OUT, annual_reclear, digest_text, portfolio_model
from .budget_portfolio_improve import valid
from .evaluation import ANNUAL, physical_lp, saved_annual
from .run_scenario import profile_sources
from .source import ROOT, digest, grouped_fit_inputs

SCAN=OUT/'pair-scan-v1'


def run():
    SCAN.mkdir(parents=True,exist_ok=True)
    with (SCAN/'job.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        parent=json.loads((OUT/'summary.json').read_text())
        original=json.loads((OUT/'manifest.json').read_text())
        by_id={row['id']:row for row in original['blocks']}
        manifest=dict(protocol='all-valid-greedy-two-solar-for-greek-wind-v1',
            source_sha256=digest(Path(__file__)),
            search_source_sha256=digest(ROOT/'baselines/compact/budget_portfolio_search.py'),
            storage_source_sha256=digest(ROOT/'baselines/compact/portfolio_storage.py'),
            parent_summary_sha256=digest(OUT/'summary.json'),
            original_manifest_sha256=digest(OUT/'manifest.json'),
            local_manifest_sha256=digest(OUT/'local-improvement-v1/manifest.json'),
            baseline_witness_sha256=digest(ANNUAL/'annual.npz'))
        mp=SCAN/'manifest.json'
        if mp.exists() and json.loads(mp.read_text())!=manifest:
            raise ValueError('Changed pair-scan identity')
        mp.write_text(json.dumps(manifest,indent=2)+'\n')
        greedy=parent['selected_ids']
        proposals=[]
        for drop in combinations(greedy,2):
            ids=tuple(sorted([x for x in greedy if x not in drop]+['wind:GR:1']))
            if valid(ids):proposals.append((ids,drop))
        model=physical_lp();costs,baseline=saved_annual()
        schema,data,_=grouped_fit_inputs();sources=profile_sources(schema,data,model)
        local=OUT/'local-improvement-v1'
        all_rows=[]
        for idx,(ids,drop) in enumerate(proposals,1):
            key=digest_text('|'.join(ids));p=SCAN/f'{key}.json'
            if p.exists():
                row=json.loads(p.read_text())
                if row['manifest_sha256']!=digest(mp) or row['asset_ids']!=list(ids):
                    raise ValueError('Stale pair-scan receipt')
            else:
                prior=local/f'{key}.json'
                if prior.exists():
                    old=json.loads(prior.read_text())
                    if old['manifest_sha256']!=digest(local/'manifest.json') or old['asset_ids']!=list(ids):
                        raise ValueError('Stale local receipt')
                    metrics={k:old[k] for k in ('benefit_m_eur','annual_cost_eur',
                        'max_primal_residual','max_stock_error_mwh','charge_twh',
                        'discharge_twh','wall_seconds','battery_count','hours','emergency_mwh')}
                    origin='cached local-improvement full-year reclear'
                else:
                    changed,changed_costs,batteries,_=portfolio_model(model,costs,[by_id[x] for x in ids],sources)
                    metrics=annual_reclear(changed,changed_costs,batteries,baseline)
                    origin='fresh full-year reclear'
                row=dict(manifest_sha256=digest(mp),asset_ids=list(ids),
                    dropped_ids=list(drop),capex_m_eur=sum(by_id[x]['capex_m_eur'] for x in ids),
                    origin=origin,**metrics)
                p.write_text(json.dumps(row,indent=2)+'\n')
            all_rows.append(row)
            best=max(all_rows,key=lambda x:x['benefit_m_eur'])
            print(f'{idx}/{len(proposals)} drop {drop}: {row["benefit_m_eur"]:.2f} M€/yr, best {best["benefit_m_eur"]:.2f}',flush=True)
        best=max(all_rows,key=lambda x:x['benefit_m_eur'])
        summary=dict(manifest_sha256=digest(mp),tested_portfolios=len(all_rows),
            best_asset_ids=best['asset_ids'],best_dropped_ids=best['dropped_ids'],
            best_capex_m_eur=best['capex_m_eur'],best_benefit_m_eur=best['benefit_m_eur'],
            best_receipt=str((SCAN/f'{digest_text("|".join(best["asset_ids"]))}.json').relative_to(ROOT)))
        (SCAN/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        return summary

if __name__=='__main__':
    print(json.dumps(run(),indent=2))
