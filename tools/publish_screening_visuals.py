"""Publish reproducible SVG explanations from real screening aggregates.

No auction bid curves or interval samples are invented. The symmetric pair of
curves is explicitly illustrative and reproduces only the modelled price gap.
"""
import hashlib,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def publish():
 source=ROOT/'public/research/entsoe-fast-targets.json';raw=source.read_bytes();data=json.loads(raw)
 row=next(r for r in data['targets'] if r['border']=='SE4>PL');monthly=sorted([r for r in data['monthly']['rows'] if r['border']=='SE4>PL'],key=lambda r:r['month'])
 s=row['average_positive_spread_eur_mwh'];k=row['slope_a'];hours=.25*row['congested_quarters'];sat=s/k;added=500.;benefit=hours*(s*added-.5*k*added**2)/1e6
 assert len(monthly)==12 and sum(r['observed_quarters'] for r in monthly)==row['observed_quarters']
 assert sum(r['congested_quarters'] for r in monthly)==row['congested_quarters']
 weighted=sum(r['congested_quarters']*r['average_positive_spread_eur_mwh'] for r in monthly)/row['congested_quarters'];assert abs(weighted-s)<1e-10
 assert abs(hours*s*s/(2*k)/1e6-row['deadweight_loss_meur_year'])<1e-8
 out=ROOT/'public/research/screening-visuals';out.mkdir(exist_ok=True)
 plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'svg.fonttype':'none','svg.hashsalt':'grid-conductor-screening','axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','figure.facecolor':'white'})
 def save(fig,name):fig.savefig(out/name,bbox_inches='tight',metadata={'Date':None});plt.close(fig)
 q=np.linspace(0,sat,240);m=s-k*q;qc=np.linspace(0,added,100)
 fig,ax=plt.subplots(figsize=(10,5));ax.fill_between(q,m,color='#fde6b6',label='Remaining modelled opportunity');ax.fill_between(qc,s-k*qc,color='#76c8b7',label='+500 MW captured area');ax.plot(q,m,color='#134e4a',lw=2.5,label='Modelled marginal spread');ax.axvline(added,color='#134e4a',ls='--',lw=1);ax.set(xlabel='Additional trade above the existing schedule (MW)',ylabel='Marginal price gap (€/MWh)',xlim=(0,sat*1.04),ylim=(0,s*1.12),title='SE4 → PL: modelled response, not observed auction curves');ax.text(65,12,f'Captured: {benefit:.1f} M€/year\nunder the screening assumptions');ax.text(620,24,f'Remaining: {row["deadweight_loss_meur_year"]-benefit:.1f} M€/year');ax.annotate(f'Assumed saturation: {sat:,.2f} MW',xy=(sat,0),xytext=(600,47),arrowprops={'arrowstyle':'->','color':'#64748b'});ax.legend(loc='upper right',fontsize=9);fig.text(.13,-.02,f'Area × {hours:,.1f} event hours → annual estimate; q=0 means no ADDITIONAL trade.',fontsize=10);save(fig,'welfare-area.svg')
 fig,ax=plt.subplots(figsize=(10,4.8));ax.plot(q,k*q/2,color='#b45309',lw=2,label='Illustrative marginal supply response');ax.plot(q,s-k*q/2,color='#2563eb',lw=2,label='Illustrative marginal demand response');ax.fill_between(q,k*q/2,s-k*q/2,color='#fde6b6',alpha=.8,label='Gap closes with additional trade');ax.set(xlabel='Additional trade (MW)',ylabel='Relative marginal value (€/MWh)',title='One illustrative curve pair consistent with the assumed gap',xlim=(0,sat*1.04));ax.legend(fontsize=9);fig.text(.13,-.01,'Price origin and equal split are arbitrary. Neither curve is an ENTSO-E auction bid curve.',fontsize=10);save(fig,'illustrative-curves.svg')
 labels=[r['month'][-2:] for r in monthly];counts=np.array([r['congested_quarters'] for r in monthly]);observed=np.array([r['observed_quarters'] for r in monthly]);means=[r['average_positive_spread_eur_mwh'] for r in monthly]
 fig,(a,b)=plt.subplots(2,1,figsize=(10,6),sharex=True);a.bar(labels,counts/observed*100,color='#0f766e');a.set(ylabel='Event share (%)',ylim=(0,100),title='Published 2025 monthly diagnostics · SE4 → PL');b.bar(labels,means,color='#d97706');b.axhline(s,color='#475569',ls='--',label=f'Annual event-weighted mean: €{s:.2f}/MWh');b.set(xlabel='Month of 2025 (UTC bank windows)',ylabel='Mean event spread\n(€/MWh)');b.legend(fontsize=9);fig.text(.12,-.01,'Event = observed directed price spread > €5/MWh; not proof of a physically binding line.',fontsize=10);save(fig,'monthly-observations.svg')
 values=[row['realized_rent_meur_year'],row['positive_rent_meur_year'],row['opportunity_meur_year']['500'],row['opportunity_meur_year']['1000'],row['deadweight_loss_meur_year'],benefit]
 names=['Signed flow × spread','Above-€5 flow × spread','Fixed-spread +500 MW ladder','Fixed-spread +1,000 MW ladder','Mean-spread triangle bound','Price-response +500 MW benefit'];fig,ax=plt.subplots(figsize=(10,5));bars=ax.barh(names,values,color=['#64748b','#64748b','#d97706','#d97706','#0f766e','#76c8b7']);ax.invert_yaxis();ax.set(xlabel='M€ over calendar year 2025 / screening estimate',title='Different quantities: do not treat these as interchangeable benefits',xlim=(0,460))
 for bar,v in zip(bars,values):ax.text(v+4,bar.get_y()+bar.get_height()/2,f'{v:.2f}',va='center')
 save(fig,'metric-comparison.svg')
 fig,ax=plt.subplots(figsize=(9,7));ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off')
 boxes=[('1 · ENTSO-E observations','A44 prices + A11 scheduled flows; capacity when available'),('2 · Align and filter','Known prices AND flow; 0.25 h samples; spread > €5 events'),('3 · Aggregate across 2025','35,040 observed; 27,442 events; weighted event spread €57.47/MWh'),('4 · Declare the response assumption','Negative OLS fits → flow-derived fallback k = 0.04927'),('5 · Integrate the modelled area','Triangle €229.89m/year; +500 MW trapezoid €154.87m/year'),('6 · Evaluate the scenario separately','Gross welfare → capital assumptions, battery model and DWL cap')]
 for i,(title,description) in enumerate(boxes):
  y=.92-i*.16
  ax.text(.5,y,title+'\n'+description,ha='center',va='center',fontsize=10,bbox={'boxstyle':'round,pad=.7','facecolor':'#f0fdfa' if i<3 else '#fffbeb','edgecolor':'#0f766e' if i<3 else '#b45309'})
  if i<5:ax.annotate('',xy=(.5,y-.115),xytext=(.5,y-.055),arrowprops={'arrowstyle':'->','color':'#475569','lw':1.5})
 ax.set_title('Observed inputs → summaries → assumed model → scenario',pad=15);save(fig,'pipeline.svg')
 result=dict(source='entsoe-fast-targets.json',source_sha256=hashlib.sha256(raw).hexdigest(),border='SE4>PL',year=2025,annual=row,monthly=monthly,derived=dict(event_hours=hours,event_weighted_mean_spread=weighted,saturation_mw=sat,line_500_gross_meur_year=benefit,sum_monthly_dwl_meur=sum(r['deadweight_loss_meur_month'] for r in monthly)),limitations=['Source contains published aggregates, not auction supply/demand bids or interval series.','Curve pair is illustrative; only gap and welfare curve use the screening assumption.','Raw OLS slopes are negative; effective slopes use a heuristic flow-derived fallback.'])
 (out/'walkthrough.json').write_text(json.dumps(result,indent=2)+'\n');print('Published five figures and aggregate provenance JSON')
if __name__=='__main__':publish()
