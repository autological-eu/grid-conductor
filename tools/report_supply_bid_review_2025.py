"""Standalone scientific review; changes no model, website or historical receipt."""
import argparse, csv, json, textwrap
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.lines import Line2D
from generation_mix_2025 import digest

COLORS={'Gas':'#2563eb','Coal/lignite':'#92400e','Nuclear':'#7c3aed','Oil':'#ea580c',
        'Wind/solar':'#16a34a','Run-of-river':'#0891b2','Biomass':'#65a30d','Waste':'#64748b','Geothermal':'#be185d'}
UNIPER='https://www.uniper.energy/germany/power-plants-germany/ingolstadt'
RESERVE='https://www.bundesnetzagentur.de/1057990'


def csv_file(path,rows):
    with path.open('w',newline='')as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)


def report(folder):
    s=json.loads((folder/'summary.json').read_text()); audit=json.loads((folder/'audit.json').read_text())
    assert audit['status']=='passed' and audit['summary_sha256']==digest(folder/'summary.json')
    assert audit['auditor_sha256']==digest(Path(__file__).with_name('audit_supply_bid_review_2025.py'))
    with np.load(folder/'offers.npz')as z:a={k:z[k] for k in z.files}
    meta=json.loads((folder/'offers.json').read_text()); rows=s['technologies']; snapshots=[]
    gas=audit['gas_blocks']; top_share=100*gas[-1]['generation_twh']/sum(r['generation_twh'] for r in gas)
    pdf=folder/'supply-bid-review-2025.pdf'; outputs=[]
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.facecolor':'white'})
    with PdfPages(pdf)as book:
        fig,ax=plt.subplots(figsize=(11,7));fig.subplots_adjust(left=.19,right=.76,bottom=.2,top=.84)
        ordered=sorted(rows,key=lambda r:r['final_bid_quantiles'][2]); ys=np.arange(len(ordered))
        for y,row in zip(ys,ordered):
            for offset,key,color in [(-.13,'raw_bid_quantiles','#94a3b8'),(.13,'final_bid_quantiles','#1d4ed8')]:
                q=row[key];ax.plot([q[0],q[4]],[y+offset]*2,color=color,lw=1,alpha=.4)
                ax.plot([q[1],q[3]],[y+offset]*2,color=color,lw=5,solid_capstyle='round')
                ax.plot(q[2],y+offset,'o',color=color,ms=5)
            ax.text(1.03,y,f"{row['generation_twh']:,.1f} / {row['available_twh']:,.1f}",transform=ax.get_yaxis_transform(),va='center')
        ax.set_yticks(ys,[r['technology'].replace('Mixed: Geothermal,Run-of-river','Geothermal / ROR mix') for r in ordered]); ax.set_xlabel('EUR/MWh electricity');ax.grid(axis='x',alpha=.2)
        ax.set_ylim(-.7,len(ys)-.3); ax.text(1.03,1.04,'Generated / available\nTWh in 2025',transform=ax.transAxes,ha='left')
        fig.suptitle('Which supply prices actually enter the model?',fontsize=18,x=.08,ha='left',y=.96)
        fig.text(.08,.89,'All 8,760 hours · current joint + weekly checkpoint · potential-supply-weighted price distribution')
        ax.legend(handles=[Line2D([0],[0],color='#94a3b8',lw=4,label='Unfitted fuel/technology anchor'),Line2D([0],[0],color='#1d4ed8',lw=4,label='Final offer')],loc='lower right')
        fig.text(.08,.08,'Thick lines: P10–P90; dots: median; thin lines: full range. Weights are hourly available MW, not dispatch.\nAvailable TWh is a supply envelope, not observed energy or a generation target. Emergency excluded.\nReservoir hydro is fixed injection and therefore has no adjustable supply-bid curve in this model.',fontsize=10)
        fig.text(.08,.025,f"Gas 50% / 35% / 15% blocks: {gas[0]['generation_twh']:.2f} / {gas[1]['generation_twh']:.2f} / {gas[2]['generation_twh']:.3f} TWh generated; upper block supplies {top_share:.3f}% of gas output.",fontsize=9)
        file=folder/'annual-supply-bids.png';fig.savefig(file,dpi=160);outputs.append(file);book.savefig(fig);plt.close(fig)

        fig,axes=plt.subplots(2,2,figsize=(11.7,8.3));fig.subplots_adjust(left=.08,right=.98,bottom=.2,top=.87,hspace=.48,wspace=.22)
        t=int((np.datetime64('2025-01-15T12')-np.datetime64('2025-01-01T00')).astype('timedelta64[h]').astype(int))
        for ax,zone in zip(axes.ravel(),['DE-LU','PL','FR','ES']):
            zi=s['zones'].index(zone); ids=[j for j,m in enumerate(meta) if m['zone']==zone and m['category']!='Emergency' and a['availability'][t,j]>1e-5]
            order=sorted(ids,key=lambda j:(a['cost'][t,j],j)); cursor=0.
            for j in order:
                stop=cursor+a['availability'][t,j]/1000; price=a['cost'][t,j]
                ax.plot([cursor,stop],[price,price],color=COLORS.get(meta[j]['category'],'#64748b'),lw=2.4)
                snapshots.append(dict(zone=zone,utc='2025-01-15T12:00:00Z',offer=j,technology=meta[j]['category'],
                    available_mw=float(a['availability'][t,j]),bid_eur_mwh=float(price),anchor_eur_mwh=float(a['raw_cost'][t,j]),dispatch_mw=float(a['dispatch'][t,j])))
                cursor=stop
            native_order=sorted(ids,key=lambda j:(a['raw_cost'][t,j],j));vol=np.cumsum([a['availability'][t,j]/1000 for j in native_order]);cost=[a['raw_cost'][t,j] for j in native_order]
            ax.step(np.r_[0,vol],np.r_[cost,cost[-1]],where='post',color='#94a3b8',lw=1,alpha=.6)
            p=a['prices'][t,zi];o=a['observed_prices'][t,zi]
            ax.axhline(p,color='#1d4ed8',ls='--',lw=1);ax.axhline(o,color='#b91c1c',ls=':',lw=1.2)
            local=float(a['dispatch'][t,ids].sum()/1000);ax.axvline(local,color='#0f172a',lw=1,ls='--')
            ax.set_title(f'{zone}  |  model €{p:.1f} · observed €{o:.1f}');ax.set_xlabel('Available local variable supply (GW)');ax.set_ylabel('Offer (EUR/MWh)');ax.grid(alpha=.15)
            ax.set_xlim(0,cursor);ax.set_ylim(min(-5,p-5,o-5),max(max(a['cost'][t,ids]),o,p)*1.06)
        fig.suptitle('Local supply stacks: 15 January 2025, 12:00 UTC',fontsize=17,y=.96)
        fig.text(.08,.91,'Displayed joint/weekly checkpoint; the targeted oil-capacity + daily-price trial is used on the following page.',fontsize=10)
        handles=[Line2D([0],[0],color=color,lw=3,label=name) for name,color in COLORS.items() if name in ['Gas','Coal/lignite','Nuclear','Oil','Wind/solar','Run-of-river']]
        fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.095),ncol=6,frameon=False)
        fig.text(.08,.035,'Coloured steps: final offers; grey line: unfitted anchor. Horizontal blue/red: modeled/observed price.\nVertical black: dispatched local variable supply. Imports, losses, constraints and fixed hydro determine clearing.\nIllustrative high-error date from earlier diagnostics, not a representative sample; annual summaries use all hours.',fontsize=9)
        file=folder/'local-supply-curves.png';fig.savefig(file,dpi=160);outputs.append(file);book.savefig(fig);plt.close(fig)

        countries=s['oil_countries']; fig,axes=plt.subplots(1,2,figsize=(11.7,6));fig.subplots_adjust(left=.08,right=.97,bottom=.26,top=.75,wspace=.35)
        labels=[r['country'] for r in countries];shares=np.array([r['observed_energy_below_cheapest_oil_bid_fraction']*100 for r in countries]);gap=[r['mean_bid_minus_observed_price_on_oil_generation'] for r in countries]
        axes[0].barh(labels,shares,color='#ea580c');axes[0].set_xlim(0,115);axes[0].set_xlabel('% of reported oil generation')
        for i,value in enumerate(shares):axes[0].text(value+1,i,f'{value:.1f}%',va='center')
        axes[0].set_title('Generated when observed price\nwas below our cheapest oil bid')
        axes[1].barh(labels,gap,color='#2563eb');axes[1].set_xlabel('EUR/MWh electricity');axes[1].axvline(0,color='#64748b',lw=.8)
        axes[1].set_title('Bid minus observed price\nweighted by reported oil generation')
        fig.suptitle('The oil mismatch is more than missing nameplate',fontsize=17,y=.96)
        subtitle=' · '.join(f"{r['country']}: "+(f"{r['observed_oil_twh']:.3f} TWh" if r['observed_oil_twh']>=.01 else f"{r['observed_oil_twh']*1000:.3f} GWh")+f" ({r['known_hours']:,} h)" for r in countries)
        fig.text(.07,.89,subtitle,fontsize=9)
        fig.text(.07,.08,'Oil bids here use the audited capacity + daily-Brent trial; original non-oil bids and physics are unchanged.\nGeneration is rounded ENTSO-E B06 on covered hours; positive-output threshold >0.1 MW. Partial years are\nnot annualised. The gap is diagnostic: it does not identify actual fuel costs, heat credits or observed bids.\nFR national/Corsica scope and multi-zone country pooling are deliberately excluded from this comparison.',fontsize=10)
        file=folder/'oil-bid-price-gap.png';fig.savefig(file,dpi=160);outputs.append(file);book.savefig(fig);plt.close(fig)

        fig=plt.figure(figsize=(8.3,11.7));fig.text(.09,.94,'Supply-bid review: interpretation and provenance',fontsize=17,weight='bold')
        notes=[
            'This is a read-only review of the actual saved annual offer book, not another solve, parameter search, recovered order book or new accepted baseline.',
            f"Gas and coal have capacity-conserving 50/35/15% blocks. The upper gas block supplies only {top_share:.3f}% of annual gas generation: changing an expensive unused tail alone has little direct price leverage. Seasonal/local-hour, inverse and weekend adjustments apply to gas/coal/nuclear. Oil keeps its fuel/carbon/VOM rule. Renewable offers are zero; reservoir output is fixed.",
            'The five generation categories used in calibration are Wind, Solar, Nuclear, Gas and Coal. Oil, biomass and waste generation are not individually penalised by that objective; aggregate generation/trade still matter. Their omitted technology errors can survive a numerically valid fit.',
            'A positive oil bid minus local cleared price is its opportunity cost of producing in this LP. With positive available MW and zero output, this is consistent with merit-order exclusion, not a missing solver column. The independently verified original bid and availability signatures, saved dispatch and source oil formulas are replayed.',
            'Oil has different operating roles. The fleet catalogue labels 1,178 MW of German oil capacity CHP; this does not identify the units producing national B06 output. It also includes an Ingolstadt site entry. Uniper describes Ingolstadt as TSO-only grid reserve since 2015. BNetzA\'s 28 April 2025 release says domestic grid-reserve plants operate outside the market. Realised A75 generation therefore need not equal day-ahead cleared dispatch. Unit/date/role reconciliation is required before changing capacity.',
            'Next: reconcile market-eligible capacity separately from nameplate; distinguish wholesale, CHP/industrial and reserve roles with dated unit data. Add oil, biomass and waste to mix validation while separating out-of-market output. Check delivered fuel, heat credits, operating constraints and cheap-block volumes jointly. Avoid arbitrary oil discounts or generation-as-availability; every change needs a controlled full-year price/mix comparison.',
            f"Derivative replay passed for {audit['hours']:,} hours / {audit['offers']} offers. No new market solve. Source summary SHA256: {audit['summary_sha256']}",
            'Data: original PyPSA-Eur fleet/weather/demand lineage, IRENA renewable trajectories, retained fixed hydro, World Bank monthly fuels/ECB, calibrated joint+weekly saved witness, audited daily EIA Brent/ECB oil trial, and audited ENTSO-E B06 country exports. All original source hashes and coverage flags are retained in summary.json and audit.json.']
        y=.88
        for index,note in enumerate(notes,1):
            wrapped=textwrap.fill(f'{index}. {note}',width=105);height=.019*(wrapped.count('\n')+1)+.018
            if y-height<.1:
                book.savefig(fig);plt.close(fig);fig=plt.figure(figsize=(8.3,11.7));fig.text(.09,.94,'Supply-bid review: interpretation (continued)',fontsize=17,weight='bold');y=.88
            fig.text(.09,y,wrapped,va='top',fontsize=9.2,linespacing=1.55);y-=height
        fig.text(.09,.055,'Primary source: Uniper — Ingolstadt operating role',fontsize=8,color='#1d4ed8',url=UNIPER)
        fig.text(.09,.035,'Primary source: BNetzA — grid reserve, 28 April 2025',fontsize=8,color='#1d4ed8',url=RESERVE)
        book.savefig(fig);plt.close(fig)
    csv_file(folder/'local-curve-snapshot.csv',snapshots)
    flat=[]
    for r in rows:
        flat.append(dict(technology=r['technology'],available_twh=r['available_twh'],model_generation_twh=r['generation_twh'],
            anchor_p10_eur_mwh=r['raw_bid_quantiles'][1],anchor_median_eur_mwh=r['raw_bid_quantiles'][2],anchor_p90_eur_mwh=r['raw_bid_quantiles'][3],
            final_p10_eur_mwh=r['final_bid_quantiles'][1],final_median_eur_mwh=r['final_bid_quantiles'][2],final_p90_eur_mwh=r['final_bid_quantiles'][3],mean_shift_eur_mwh=r['available_weighted_mean_bid_shift']))
    csv_file(folder/'annual-bid-summary.csv',flat)
    csv_file(folder/'gas-blocks.csv',gas)
    files=outputs+[pdf,folder/'local-curve-snapshot.csv',folder/'annual-bid-summary.csv',folder/'gas-blocks.csv']
    (folder/'report-receipt.json').write_text(json.dumps(dict(summary_sha256=digest(folder/'summary.json'),audit_sha256=digest(folder/'audit.json'),renderer_sha256=digest(__file__),primary_sources=[UNIPER,RESERVE],files={p.name:digest(p) for p in files}),indent=2)+'\n')
    print(pdf)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);report(p.parse_args().folder.resolve())
