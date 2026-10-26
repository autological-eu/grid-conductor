"""Test published national/regional stock aggregation against NVE sample method.

A source-method diagnostic, never replacement reservoir inventory or inflow.
Current public capacity tables require historical dating before dispatch adoption.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sigmoid_month_pairs_2025 import ROOT,digest
from run_differentiable_spline_2025 import atomic_json
SOURCE=ROOT/'data/bidding-zone-source-audit-2025/nve-reservoir-method-v1'
STOCK=ROOT/'data/bidding-zone-source-audit-2025/nve-reservoir-history.json'
OUT=ROOT/'data/bidding-zone-source-audit-2025/nve-stock-aggregation-v1'
def run():
 OUT.mkdir(exist_ok=True)
 if (OUT/'summary.json').exists():raise ValueError('Existing diagnostic sealed')
 manifest=json.loads((SOURCE/'manifest.json').read_text())
 for r in manifest['rows']:assert digest(SOURCE/r['file'])==r['sha256']
 receipt=json.loads(STOCK.with_name('nve-reservoir-history.meta.json').read_text());assert digest(STOCK)==receipt['sha256']
 reservoir=pd.read_excel(SOURCE/'reservoir.xlsx');detail=pd.read_excel(SOURCE/'reservoir-plant.xlsx');plant=pd.read_excel(SOURCE/'plant.xlsx');assert not reservoir['Magasinnr.'].duplicated().any();sample=reservoir.set_index('Magasinnr.')['Norgesmagasin'];assert detail['Magasinnr.'].isin(sample.index).all();detail['sample']=detail['Magasinnr.'].map(sample);detail=detail[detail['Områdetype'].eq('EL')]
 full=detail.groupby('Områdenr.')['Kapasitet [GWh]'].sum().reindex(range(1,6));samplecap=detail[detail['sample']].groupby('Områdenr.')['Kapasitet [GWh]'].sum().reindex(range(1,6));np.testing.assert_allclose(full,plant[plant['Områdetype'].eq('EL')].groupby('Områdenr.')['Kapasitet [GWh]'].sum().reindex(range(1,6)),atol=1e-5,rtol=0)
 raw=json.loads(STOCK.read_text());dates=sorted({r['dato_Id'] for r in raw if '2024-12-29'<=r['dato_Id']<='2025-03-02'});rows=[]
 for day in dates:
  a=[r for r in raw if r['dato_Id']==day];national=[r for r in a if r['omrType']=='NO' and r['omrnr']==0];regions={r['omrnr']:r for r in a if r['omrType']=='EL'}
  if len(national)!=1 or set(regions)!=set(range(1,6)):raise ValueError('Incomplete stock areas')
  national=national[0];regionalcap=np.array([regions[z]['kapasitet_TWh'] for z in range(1,6)])*1000;capacity_error=float(abs(full.values-regionalcap).max());assert capacity_error<.01
  filling=np.array([regions[z]['fyllingsgrad'] for z in range(1,6)]);prediction=float(np.sum(filling*samplecap.values)/samplecap.sum()*national['kapasitet_TWh']);simple=float(sum(regions[z]['fylling_TWh'] for z in range(1,6)))
  rows.append(dict(date=day,national_twh=national['fylling_TWh'],regional_sum_twh=simple,sample_weight_prediction_twh=prediction,regional_sum_minus_national_gwh=(simple-national['fylling_TWh'])*1000,sample_prediction_minus_national_gwh=(prediction-national['fylling_TWh'])*1000))
 atomic_json(OUT/'summary.json',dict(status='published_sample_method_test_not_dispatch_release',full_capacity_gwh=full.to_dict(),sample_capacity_gwh=samplecap.to_dict(),sample_coverage=(samplecap/full).to_dict(),rows=rows,max_simple_discrepancy_gwh=max(abs(r['regional_sum_minus_national_gwh']) for r in rows),max_method_discrepancy_gwh=max(abs(r['sample_prediction_minus_national_gwh']) for r in rows),sources={str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),STOCK,*[SOURCE/r['file'] for r in manifest['rows']]]},limitations=['Uses current published reference tables matching reported capacity values, not independent historical plant capacity certification.','NVE weekly measurement subset may vary; a method match does not provide individual reservoir observations.','Published filling extrapolates sample ratios; regional estimates need not sum to national estimate.']))
 print(json.dumps(dict(max_simple_gwh=max(abs(r['regional_sum_minus_national_gwh']) for r in rows),max_method_gwh=max(abs(r['sample_prediction_minus_national_gwh']) for r in rows),sample_coverage=(samplecap/full).to_dict(),rows=rows)),flush=True)
if __name__=='__main__':run()
