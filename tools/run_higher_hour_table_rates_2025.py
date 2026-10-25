"""Fresh rates1/2 via immutable hourly-table producer, isolated sequential trials."""
import fcntl,json,os,subprocess,sys,traceback
from pathlib import Path
import run_hour_table_learning_rates_2025 as trial
from sigmoid_month_pairs_2025 import ROOT,digest
from run_differentiable_spline_2025 import atomic_json
OUT=ROOT/'data/bidding-zone-network-2025/higher-hour-table-learning-rates-v1'

def child(rate):
    trial.RATE=rate;trial.OUT=OUT/f'lr-{rate:g}'
    original=trial.parent.provenance
    def provenance(base):
        result=original(base);result[str(Path(__file__).relative_to(ROOT))]=digest(__file__)
        return result
    trial.parent.provenance=provenance
    try:trial.trial()
    except Exception:
        trial.OUT.mkdir(exist_ok=True);atomic_json(trial.OUT/'failure.json',dict(traceback=traceback.format_exc()));raise

def run():
    OUT.mkdir(exist_ok=True);lock=(OUT/'suite.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if (OUT/'suite-started.json').exists():raise ValueError('Inspect existing higher-rate suite before restart')
    old=ROOT/'data/bidding-zone-network-2025/hour-table-learning-rates-v1'
    receipt=json.loads((old/'suite-finished.json').read_text());assert receipt['completed']==[.05,.15,.5]
    for rate in [.05,.15,.5]:
        folder=old/f'lr-{rate:g}'
        assert json.loads((folder/'complete.json').read_text())['points']==101
        for p,h in json.loads((folder/'provenance.json').read_text()).items():assert digest(ROOT/p)==h,p
    atomic_json(OUT/'suite-started.json',dict(rates=[1.,2.],updates=100,pid=os.getpid(),initialization='fresh identical neutral bids; not continuation',gates='unchanged; preserve failure and continue other rate',source_sha256=digest(__file__)))
    for rate in [1.,2.]:
        log=(OUT/f'lr-{rate:g}.log').open('ab',buffering=0)
        p=subprocess.Popen([sys.executable,'-u',__file__,'--trial',str(rate)],stdout=log,stderr=subprocess.STDOUT)
        atomic_json(OUT/'live-trial.json',dict(rate=rate,pid=p.pid));code=p.wait()
        if code:print('TRIAL FAILED',rate,'inspect recorded failure',flush=True)
    atomic_json(OUT/'suite-finished.json',dict(completed=[r for r in [1.,2.] if (OUT/f'lr-{r:g}/complete.json').exists()],failed=[r for r in [1.,2.] if (OUT/f'lr-{r:g}/failure.json').exists()]))

if __name__=='__main__':
    if len(sys.argv)>1:child(float(sys.argv[2]))
    else:run()
