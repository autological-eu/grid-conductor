"""Challenge the retained €5bn portfolio across all source-covered zones.

Replace one selected wind, battery, or solar block at a time.  Each trial
reclears the unchanged 2025 physical joint LP for all 8,760 hours.  This is
a bounded neighborhood, not a global optimality certificate.
"""
from __future__ import annotations

import fcntl
import json
from pathlib import Path

from baselines.compact.budget_portfolio_search import OUT, annual_reclear, digest_text, portfolio_model
from baselines.compact.evaluation import ANNUAL, physical_lp, saved_annual
from baselines.compact.run_scenario import profile_sources
from baselines.compact.source import ROOT, digest, grouped_fit_inputs

CHALLENGE=OUT/'cross-zone-challenge-v1'


def run():
    CHALLENGE.mkdir(parents=True,exist_ok=True)
    with (CHALLENGE/'job.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        selected=json.loads((OUT/'complements-v1/summary.json').read_text())
        original=json.loads((OUT/'manifest.json').read_text())
        broad=json.loads((OUT/'broad_screen.json').read_text())
        by_id={r['id']:r for r in (*original['blocks'],*broad)}
        ids=selected['best_asset_ids']
        manifest=dict(protocol='best-found-cross-zone-single-block-challenge-v1',
            source_sha256=digest(Path(__file__)),
            selected_summary_sha256=digest(OUT/'complements-v1/summary.json'),
            original_manifest_sha256=digest(OUT/'manifest.json'),
            baseline_witness_sha256=digest(ANNUAL/'annual.npz'),
            replacement='one same-technology 500 MW/2 GWh block; original availability and full-year reclear')
        mp=CHALLENGE/'manifest.json'
        if mp.exists() and json.loads(mp.read_text())!=manifest:
            raise ValueError('Changed cross-zone challenge identity')
        mp.write_text(json.dumps(manifest,indent=2)+'\n')
        proposals=[]
        for family,old_id in (('wind','wind:GR:1'),('battery','battery:IE-SEM:1'),('solar','solar:MK:1')):
            for new in (r for r in broad if r['family']==family):
                new_id=new['id']
                if new_id==old_id or new_id in ids:continue
                swapped=tuple(sorted([x for x in ids if x!=old_id]+[new_id]))
                proposals.append((family,old_id,new_id,swapped))
        model=physical_lp();costs,baseline=saved_annual()
        schema,data,_=grouped_fit_inputs();sources=profile_sources(schema,data,model)
        best_benefit=selected['best_benefit_m_eur'];best_ids=ids
        for idx,(family,old_id,new_id,swapped) in enumerate(proposals,1):
            key=digest_text('|'.join(swapped));p=CHALLENGE/f'{key}.json'
            if p.exists():
                row=json.loads(p.read_text())
                if row['manifest_sha256']!=digest(mp) or row['asset_ids']!=list(swapped):
                    raise ValueError('Stale challenge receipt')
            else:
                changed,changed_costs,batteries,_=portfolio_model(model,costs,[by_id[x] for x in swapped],sources)
                metrics=annual_reclear(changed,changed_costs,batteries,baseline)
                row=dict(manifest_sha256=digest(mp),asset_ids=list(swapped),
                    family=family,replaced_id=old_id,new_id=new_id,
                    capex_m_eur=sum(by_id[x]['capex_m_eur'] for x in swapped),**metrics)
                p.write_text(json.dumps(row,indent=2)+'\n')
            if row['benefit_m_eur']>best_benefit:
                best_benefit=row['benefit_m_eur'];best_ids=list(swapped)
            print(f'{idx}/{len(proposals)} {old_id}->{new_id}: {row["benefit_m_eur"]:.2f} M€/yr; best {best_benefit:.2f}',flush=True)
        summary=dict(manifest_sha256=digest(mp),tested_portfolios=len(proposals),
            initial_benefit_m_eur=selected['best_benefit_m_eur'],
            best_benefit_m_eur=best_benefit,best_asset_ids=best_ids,
            best_capex_m_eur=sum(by_id[x]['capex_m_eur'] for x in best_ids),
            improved=best_benefit>selected['best_benefit_m_eur'])
        (CHALLENGE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        return summary

if __name__=='__main__':
    print(json.dumps(run(),indent=2))
