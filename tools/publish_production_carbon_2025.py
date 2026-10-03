"""Publish coverage-gated January 2025 production-carbon accounting."""
import hashlib,json
from pathlib import Path
from carbon_pilot import FACTORS,STORAGE,IPCC
ROOT=Path(__file__).resolve().parents[1]
FUEL_SOURCE="https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_2_Ch2_Stationary_Combustion.pdf"
ASSUMPTIONS={"B04":(56.1,.50),"B05":(94.6,.40),"B02":(101.,.35)}
DIRECT={k:f*3.6/eta for k,(f,eta) in ASSUMPTIONS.items()}
DIRECT.update({k:0. for k in ["B09","B11","B12","B13","B14","B16","B18","B19"]})
NAMES={"B01":"Biomass","B04":"Gas","B05":"Hard coal","B06":"Oil","B11":"Run-of-river","B12":"Reservoir","B14":"Nuclear","B15":"Other renewable","B16":"Solar","B17":"Waste","B18":"Offshore wind","B19":"Onshore wind"}
def accounting(row,factors):
 if row["primary_generation_mwh"] is None:return dict(full_intensity=None,mapped_mix_intensity=None,mapped_share=None)
 energy={k:v for k,v in row["generation_mwh_by_type"].items() if k not in STORAGE}
 total=sum(energy.values());mapped=sum(v for k,v in energy.items() if k in factors)
 emissions=sum(v*factors[k] for k,v in energy.items() if k in factors)
 unknown=any(v>0 and k not in factors for k,v in energy.items())
 return dict(full_intensity=emissions/total if total and not unknown else None,
  mapped_mix_intensity=emissions/mapped if mapped else None,mapped_share=mapped/total if total else None)
def publish():
 folder=ROOT/"data/carbon-pilot/entsoe/2025-01";output=ROOT/"public/research/production-carbon-2025"
 source=json.loads((folder/"summary.json").read_text())
 rows=[json.loads(x) for x in (folder/"hourly.jsonl").read_text().splitlines()]
 for row in rows:row["operational"]=accounting(row,DIRECT)
 zones={}
 for zone in source["zones"]:
  group=[r for r in rows if r["zone"]==zone];valid=[r for r in group if r["primary_generation_mwh"]]
  mix={k:sum(r["generation_mwh_by_type"].get(k,0) for r in valid) for k in group[0]["reported_types"] if k not in STORAGE}
  total=sum(mix.values())
  zones[zone]=dict(expected_hours=len(group),complete_generation_hours=len(valid),generation_mwh_by_type=mix,
   full_lifecycle_hours=sum(r["carbon_intensity"] is not None for r in group),
   full_operational_hours=sum(r["operational"]["full_intensity"] is not None for r in group),
   operational_mapped_share=sum(v for k,v in mix.items() if k in DIRECT)/total,
   lifecycle_mapped_share=sum(v for k,v in mix.items() if k in FACTORS)/total)
 output.mkdir(parents=True,exist_ok=True)
 result=dict(schema_version=1,start=source["start"],end_exclusive=source["end_exclusive"],
  basis="reported primary production; storage discharge excluded",provenance=source["source"],
  input_sha256=hashlib.sha256((folder/"hourly.jsonl").read_bytes()).hexdigest(),
  lifecycle=dict(source=IPCC,factors=FACTORS,unit="gCO2e/kWh"),
  operational=dict(source=FUEL_SOURCE,fuel_kgco2_gj_and_efficiency=ASSUMPTIONS,factors=DIRECT,unit="gCO2/kWh",
   limitations=["Generic fuel factors and assumed electrical efficiencies, not measured fleet emissions","Biomass and other unsupported fuels remain unknown","Non-combustion zero covers combustion CO2 only, excluding lifecycle and reservoir greenhouse gases"]),
  limitations=source["limitations"]+["Mapped subset is not full-zone intensity; complete reported categories do not prove full-fleet coverage","Month only, complete-generation hours only; never annualize"],zones=zones,hourly=rows)
 (output/"results.json").write_text(json.dumps(result,allow_nan=False,separators=(",",":"))+"\n")
 import matplotlib
 matplotlib.use("Agg")
 import matplotlib.pyplot as plt
 import numpy as np
 fig,axes=plt.subplots(3,2,figsize=(13,10.5),layout="constrained")
 for (zone,s),(left,right) in zip(zones.items(),axes):
  group=[r for r in rows if r["zone"]==zone];mix=s["generation_mwh_by_type"]
  items=sorted([(k,v) for k,v in mix.items() if v>0],key=lambda x:x[1],reverse=True)
  left.barh([NAMES.get(k,k) for k,v in items],[v/1000 for k,v in items],color="#0f766e");left.invert_yaxis()
  left.set_title(f'{zone}: mix, {s["complete_generation_hours"]}/744 hours');left.set_xlabel("GWh in complete-generation hours")
  for values,label,color in [([r["operational"]["mapped_mix_intensity"] for r in group],"Operational mapped subset","#2563eb"),([r["mapped_mix_intensity"] for r in group],"Lifecycle mapped subset","#d97706")]:
   right.plot([np.nan if v is None else v for v in values],label=label,color=color,linewidth=.8)
  right.set_title("Partial estimates, not whole-zone intensity");right.set_xlabel("Hour from 1 January 2025, 00:00 UTC")
  right.set_ylabel("gCO2/kWh operational; gCO2e/kWh lifecycle");right.legend(fontsize=8);right.grid(alpha=.2)
 fig.savefig(output/"production-carbon.svg");plt.close(fig)
 print(json.dumps(zones,indent=2))
if __name__=="__main__":publish()
