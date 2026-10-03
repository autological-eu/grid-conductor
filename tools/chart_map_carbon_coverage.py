"""Visualise monthly reported-generation coverage of the published snapshot."""
import calendar,json
from carbon_pilot import ROOT

def chart():
 import numpy as np
 import matplotlib
 matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 folder=ROOT/'public/research/production-carbon-2025'
 data=json.loads((folder/'map-summary.json').read_text());zones=sorted(data['zones']);values=np.full((len(zones),12),np.nan)
 for i,zone in enumerate(zones):
  for receipt in data['provenance'][zone]:
   month=receipt['month'];values[i,month-1]=100*receipt['complete_hours']/(24*calendar.monthrange(2025,month)[1])
 fig,ax=plt.subplots(figsize=(10,13),layout='constrained');cmap=plt.get_cmap('YlGnBu').copy();cmap.set_bad('#dddddd')
 plot=ax.imshow(np.ma.masked_invalid(values),aspect='auto',vmin=0,vmax=100,cmap=cmap)
 ax.set_xticks(range(12),range(1,13));ax.set_yticks(range(len(zones)),zones);ax.set_xlabel('UTC month, 2025');ax.set_title('Complete reported generation hours (%)\nGrey: no usable collected month; not zero generation')
 fig.colorbar(plot,ax=ax,label='Generation-data coverage (%)');fig.savefig(folder/'map-coverage.svg');plt.close(fig)
 print('Wrote map-wide monthly coverage chart')
if __name__=='__main__':chart()
