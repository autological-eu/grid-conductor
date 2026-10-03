"""Publish the audited carbon-price sensitivity as CSV and standalone figures."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
DIRECTORY=ROOT/'public/research/network-benchmark'

def main():
    report=json.loads((DIRECTORY/'carbon-sensitivity.json').read_text())
    if len(report['cases'])!=16 or not report['gates']['transport_objectives_within_one_cent']:
        raise ValueError('Complete numerical comparison required before publication')
    records=[]
    for row in report['cases']:
        for model in ['pypsa_transport','pypsa_ac']:
            r=row[model]
            if abs(r['carbon_inclusive_benefit_eur']-r['non_carbon_operating_benefit_eur']-row['carbon_price_eur_t']*r['avoided_co2_t'])>.01:
                raise ValueError('Carbon benefit decomposition failed')
            records.append(dict(carbon_price_eur_t=row['carbon_price_eur_t'],case=row['id'],model=model,
                carbon_inclusive_benefit_eur=r['carbon_inclusive_benefit_eur'],non_carbon_operating_benefit_eur=r['non_carbon_operating_benefit_eur'],avoided_co2_t=r['avoided_co2_t']))
    with (DIRECTORY/'carbon-sensitivity.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]),lineterminator='\n');writer.writeheader();writer.writerows(records)
    selected=[r for r in records if r['case']=='swepol-plus-500']
    fig,axes=plt.subplots(2,1,figsize=(9,8),layout='constrained',sharex=True)
    for model,label,color in [('pypsa_transport','Transport relaxation','#2563eb'),('pypsa_ac','PyPSA / Kirchhoff','#d97706')]:
        rows=[r for r in selected if r['model']==model];prices=[r['carbon_price_eur_t'] for r in rows]
        axes[0].plot(prices,[r['carbon_inclusive_benefit_eur']/1e6 for r in rows],marker='o',label=label,color=color)
        axes[1].plot(prices,[r['avoided_co2_t']/1000 for r in rows],marker='o',label=label,color=color)
    axes[0].set_ylabel('Carbon-inclusive benefit (€ million / week)')
    axes[0].set_title('Poland–Sweden +500 MW · same archived 168-hour test period\nIllustrative carbon-price assumptions; each price has its own baseline')
    axes[1].set_ylabel('Avoided generation CO₂ (thousand tonnes / week)')
    axes[1].set_xlabel('Assumed carbon price (€/tonne CO₂)');axes[1].axhline(0,color='black',linewidth=.8)
    axes[1].text(2,-46000/1000,'Negative = investment increases emissions',fontsize=9)
    axes[1].set_xticks(report['carbon_prices_eur_t'])
    for ax in axes:ax.legend();ax.grid(alpha=.2)
    fig.savefig(DIRECTORY/'carbon-sensitivity.png',dpi=180);fig.savefig(DIRECTORY/'carbon-sensitivity.svg');plt.close(fig)
    print('Published carbon sensitivity; historical and annual validation not claimed.')

if __name__=='__main__':main()
