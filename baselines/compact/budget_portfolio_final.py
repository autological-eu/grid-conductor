"""Independent hourly witness for the final €5bn best-found portfolio."""
from __future__ import annotations

import fcntl
import json
from pathlib import Path

import numpy as np

from .budget_portfolio_search import OUT, digest_text, portfolio_model
from .evaluation import ANNUAL, physical_lp, saved_annual
from .lp import clear_hour, solver
from .portfolio_storage import PortfolioWindow
from .run_scenario import profile_sources
from .source import ROOT, digest, grouped_fit_inputs

FINAL=OUT/'selected-final-v1'


def run():
    FINAL.mkdir(parents=True,exist_ok=True)
    with (FINAL/'job.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        best=json.loads((OUT/'complements-v1/summary.json').read_text())
        parent=json.loads((OUT/'manifest.json').read_text())
        by_id={x['id']:x for x in parent['blocks']}
        ids=best['best_asset_ids'];key=digest_text('|'.join(ids))
        source_folder=(OUT/'complements-v1' if best['improved'] else OUT/'pair-scan-v1')
        source_receipt=source_folder/f'{key}.json'
        if not source_receipt.exists():raise ValueError('Selected source receipt missing')
        expected=json.loads(source_receipt.read_text())
        if expected['asset_ids']!=ids:raise ValueError('Selected source identity changed')
        manifest=dict(protocol='best-found-2025-hourly-witness-v1',
            source_sha256=digest(Path(__file__)),
            selected_summary_sha256=digest(OUT/'complements-v1/summary.json'),
            selected_receipt_sha256=digest(source_receipt),
            original_manifest_sha256=digest(OUT/'manifest.json'),
            baseline_witness_sha256=digest(ANNUAL/'annual.npz'),asset_ids=ids)
        mp=FINAL/'manifest.json'
        if mp.exists() and json.loads(mp.read_text())!=manifest:
            raise ValueError('Changed selected-final identity')
        mp.write_text(json.dumps(manifest,indent=2)+'\n')
        if (FINAL/'summary.json').exists():
            old=json.loads((FINAL/'summary.json').read_text())
            if old['manifest_sha256']!=digest(mp) or old['witness_sha256']!=digest(FINAL/'annual.npz'):
                raise ValueError('Stale final witness')
            return old
        base_model,base_costs=physical_lp(),None
        base_costs,baseline=saved_annual()
        schema,data,_=grouped_fit_inputs();sources=profile_sources(schema,data,base_model)
        model,costs,batteries,description=portfolio_model(base_model,base_costs,[by_id[x] for x in ids],sources)
        ncols=model['A'].shape[1];nz=model['nz'];ng=model['ng']
        values=np.empty((8760,ncols));prices=np.empty((8760,nz))
        stocks=np.empty((len(batteries),8760,3))
        objective=0.;maximum_primal=0.;charge=0.;discharge=0.;max_stock_error=0.
        if batteries:
            regular=PortfolioWindow(model,costs,batteries,48)
            final=PortfolioWindow(model,costs,batteries,24)
            current=np.array([b.initial_mwh for b in batteries],float)
            for day in range(365):
                capacities=np.array([b.energy_mwh for b in batteries])
                corrected=np.clip(current,0,capacities)
                if np.max(np.abs(corrected-current))>1e-6:
                    raise ValueError(f'Day {day}: stock outside battery bounds')
                current=corrected
                result=(regular if day<364 else final).clear(day*24,tuple(current))
                sl=slice(day*24,(day+1)*24)
                values[sl]=result['values'][:24]
                prices[sl]=result['zonal_prices'][:24]
                stocks[:,sl,:]=result['storage'][:,:24]
                objective+=float(np.sum(values[sl,:ng]*costs[sl]))
                for bi,b in enumerate(batteries):
                    stock=stocks[bi,sl]
                    replay=current[bi]+np.cumsum(b.charge_efficiency*stock[:,0]-stock[:,1]/b.discharge_efficiency)
                    err=float(np.max(np.abs(replay-stock[:,2])))
                    if err>1e-6:raise ValueError(f'Day {day}: stock replay failed')
                    max_stock_error=max(max_stock_error,err)
                    objective+=b.throughput_eur_mwh*float(stock[:,:2].sum())
                    charge+=float(stock[:,0].sum());discharge+=float(stock[:,1].sum())
                    current[bi]=stock[-1,2]
                maximum_primal=max(maximum_primal,result['maximum_primal_residual'])
            if np.max(np.abs(current-[b.terminal_mwh for b in batteries]))>1e-6:
                raise ValueError('Annual battery terminal stock failed')
        else:
            highs=solver(model,costs)
            for h in range(8760):
                x,dual,value,error=clear_hour(highs,model,costs,h)
                values[h]=x;prices[h]=dual[:nz]
                objective+=value;maximum_primal=max(maximum_primal,error)
        if np.any(values[:,:ng][:,model['emergency_mask']].sum(axis=1)>1e-6):
            raise ValueError('Emergency dispatch in final witness')
        if abs(objective-expected['annual_cost_eur'])>0.01:
            raise ValueError(f'Final objective differs from selected receipt: {objective-expected["annual_cost_eur"]}')
        benefit=(baseline['objectives'].sum()-objective)/1e6
        if abs(benefit-best['best_benefit_m_eur'])>1e-8:
            raise ValueError('Final benefit differs from search')
        np.savez_compressed(FINAL/'annual.npz',values=values,zonal_prices=prices,storage=stocks,
            hours=np.arange(8760))
        old_prices=np.asarray(baseline['row_duals'])[:,:nz]
        zones=list(map(str,model['zones']))
        generator_dispatch=[dict(zone=g['zone'],name=g['name'],capacity_mw=g['capacity_mw'],
            dispatch_twh=float(values[:,g['column']].sum()/1e6)) for g in description['generators']]
        summary=dict(manifest_sha256=digest(mp),status='independent_hourly_replay_passed',
            witness_sha256=digest(FINAL/'annual.npz'),asset_ids=ids,
            hours=8760,max_primal_residual=maximum_primal,emergency_mwh=0.,
            max_stock_replay_error_mwh=max_stock_error,
            annual_cost_eur=objective,benefit_m_eur=benefit,
            capex_m_eur=expected['capex_m_eur'],
            mean_abs_zonal_price_change_eur_mwh=float(np.mean(np.abs(prices-old_prices))),
            zonal_mean_price_changes_eur_mwh={z:float((prices[:,i]-old_prices[:,i]).mean()) for i,z in enumerate(zones)},
            generator_dispatch=generator_dispatch,
            battery_charge_twh=charge/1e6,battery_discharge_twh=discharge/1e6,
            battery_stock_min_mwh=[float(stocks[i,:,2].min()) for i in range(len(batteries))],
            battery_stock_max_mwh=[float(stocks[i,:,2].max()) for i in range(len(batteries))])
        (FINAL/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        return summary

if __name__=='__main__':
    print(json.dumps(run(),indent=2))
