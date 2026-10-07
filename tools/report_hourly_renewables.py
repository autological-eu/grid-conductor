"""Publish compact renewable reconstruction diagnostics and reproducible SVGs."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from hourly_renewable_estimates import digest


def verified_summary(root):
    report = json.loads((root/'summary.json').read_text())
    if report['year'] != 2025 or report['hours'] != 8760 or digest(root/'hourly.npz') != report['hourly_sha256']:
        raise ValueError('Hourly evidence identity changed')
    with np.load(root/'hourly.npz', allow_pickle=False) as data:
        expected = np.arange(np.datetime64('2025-01-01T00'), np.datetime64('2026-01-01T00'), np.timedelta64(1, 'h'))
        if not np.array_equal(data['hours_utc'], expected): raise ValueError('Hourly chronology changed')
        months = expected.astype('datetime64[M]').astype(int) % 12 + 1
        seen = set()
        for row in report['countries']:
            key = row['country']+'_'+row['technology']
            if key in seen: raise ValueError('Duplicate country technology')
            seen.add(key)
            available = data[key+'_available_mw']; generated = data[key+'_reconstructed_generation_mw']
            capacity = row['capacity_mw']
            if available.shape != (8760,) or generated.shape != (8760,) or not np.isfinite(capacity) or capacity <= 0:
                raise ValueError('Invalid hourly shape or capacity')
            if not np.isfinite(available).all() or np.any(available < 0) or np.any(available > capacity+1e-6):
                raise ValueError('Invalid availability')
            if not np.isclose(available.sum(), row['available_energy_mwh'], rtol=1e-10, atol=1e-5):
                raise ValueError('Annual availability does not reconcile')
            if [m['month'] for m in row['months']] != list(range(1,13)): raise ValueError('Incomplete monthly inventory')
            for month in row['months']:
                mask = months == month['month']; values = generated[mask]
                if not np.isclose(available[mask].sum(), month['available_energy_mwh'], rtol=1e-10, atol=1e-5):
                    raise ValueError('Monthly availability does not reconcile')
                if month['status'] in ['monthly_constrained_shape_not_availability','zero_reported_generation']:
                    if not np.isfinite(values).all() or np.any(values < 0) or np.any(values > capacity+1e-6):
                        raise ValueError('Invalid reconstructed generation')
                    if np.any(values[available[mask] == 0] != 0): raise ValueError('Generation in zero-weather hours')
                    if not np.isclose(values.sum(), month['observed_generation_mwh'], rtol=1e-10, atol=1e-5):
                        raise ValueError('Monthly generation does not reconcile')
                elif month['status'] in ['missing_observation','target_exceeds_positive_weather_support','no_weather_support','scaling_limit']:
                    if not np.isnan(values).all(): raise ValueError('Unavailable month was filled')
                else: raise ValueError('Unknown reconstruction status')
    return report


def run():
    root=Path('data/pypsa-eur/hourly-renewable-estimates-v1')
    report=verified_summary(root)
    out=Path('public/research/hourly-renewables-2025');out.mkdir(parents=True,exist_ok=True)
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    plt.rcParams.update({'svg.fonttype':'none','font.size':10})
    selected=['DE','FR','ES','PL']
    fig,axes=plt.subplots(2,4,figsize=(15,7),sharex=True)
    for i,tech in enumerate(['wind','solar']):
        for j,country in enumerate(selected):
            row=next(r for r in report['countries'] if r['country']==country and r['technology']==tech)
            ax=axes[i,j];ax.plot(range(1,13),[m['available_energy_mwh']/1e6 for m in row['months']],label='Weather availability')
            ax.plot(range(1,13),[np.nan if m['observed_generation_mwh'] is None else m['observed_generation_mwh']/1e6 for m in row['months']],label='Ember generation')
            ax.set_title(country+' '+tech);ax.set_ylabel('TWh/month');ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=8);fig.suptitle('Available energy versus observed generation — different quantities, no forced fit')
    fig.tight_layout();fig.savefig(out/'monthly.svg');plt.close(fig)
    with np.load(root/'hourly.npz') as data:
        fig,axes=plt.subplots(2,1,figsize=(12,6))
        for ax,tech in zip(axes,['wind','solar']):
            # First week in June; reconstruction uses the whole June total.
            start=3624;stop=start+168
            ax.plot(np.arange(168),data['FR_'+tech+'_available_mw'][start:stop]/1000,label='Original availability')
            ax.plot(np.arange(168),data['FR_'+tech+'_reconstructed_generation_mw'][start:stop]/1000,label='Monthly-constrained estimate')
            ax.set_title('France '+tech+' · 1–7 June 2025 UTC');ax.set_ylabel('GW');ax.grid(alpha=.2);ax.legend()
        axes[-1].set_xlabel('Hour from 1 June 00:00 UTC');fig.tight_layout();fig.savefig(out/'hourly.svg');plt.close(fig)
    for figure in out.glob('*.svg'):
        figure.write_text('\n'.join(line.rstrip() for line in figure.read_text().splitlines())+'\n')
    statuses={}
    for row in report['countries']:
        for m in row['months']:statuses[m['status']]=statuses.get(m['status'],0)+1
    print('series',len(report['countries']),'countries',len({r['country'] for r in report['countries']}),'months',statuses)
    for c in selected:
        for t in ['wind','solar']:
            r=next(r for r in report['countries'] if r['country']==c and r['technology']==t)
            obs=[m['observed_generation_mwh'] for m in r['months']]
            print(c,t,round(r['capacity_mw']/1000,3),round(r['available_energy_mwh']/1e6,3),None if any(v is None for v in obs) else round(sum(obs)/1e6,3))
if __name__=='__main__':run()
