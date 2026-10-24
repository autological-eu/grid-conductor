"""Equation-level review of the uploaded toy notebook; no notebook execution.

Port its three-zone forward equations to NumPy, replay the synthetic scenario,
check the analytic Jacobian and quantify ridge bias. This does NOT benchmark
PyTorch training or our European physical network.
"""
import argparse,ast,hashlib,json,time
from pathlib import Path
import numpy as np
from scipy.special import expit

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/bidding-zone-network-2025/supply-recovery-notebook-review-v1'
EXPECTED_NOTEBOOK_SHA256='661efd6583b4c3b9cc5955295851b1fb2c051d9e8a8cef3b3461fdc140a8b09e'


def constants(notebook):
    cells=json.loads(notebook.read_text())['cells']
    source='\n'.join(''.join(c['source']) for c in cells if c['cell_type']=='code')
    tree=ast.parse(source)
    values={}
    for node in tree.body:
        if not isinstance(node,ast.Assign):continue
        value=node.value
        if isinstance(value,ast.Call) and isinstance(value.func,ast.Attribute) and value.func.attr=='tensor':value=value.args[0]
        try:literal=ast.literal_eval(value)
        except (ValueError,TypeError):continue
        target=node.targets[0]
        if isinstance(target,ast.Name):values[target.id]=literal
        elif isinstance(target,ast.Tuple):
            for name,v in zip(target.elts,literal):values[name.id]=v
    truth=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='true_theta')
    node=next(n for n in truth.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='base_prices')
    values['base_prices']=ast.literal_eval(node.value.args[0])
    return values


def scenario(c):
    n=c['N_DAYS'];t=np.arange(24*n);hour=t%24;day=t//24;dow=day%7
    rng=np.random.default_rng(c['SEED_DATA'])
    fuel=np.cumsum(rng.normal(0,1.5,n));fuel-=fuel.mean();fuel=fuel[day]
    base=np.broadcast_to(np.array(c['base_prices'],float),(len(t),3,4,6)).copy()
    # Same ground-truth features as notebook cell3; no learned parameters loaded.
    for z,scale in enumerate([1.,.8,1.2]):
        base[:,z,2,3:]+=scale*8*np.cos(2*np.pi*(hour-19)/24)[:,None]
        base[:,z,2,:]+=scale*np.where(dow==5,-4,np.where(dow==6,-6,0))[:,None]
        base[:,z,2,2:]+=fuel[:,None]*np.array([.2,.5,.8,1.2])
    anchors=np.concatenate([base[...,:1],base[...,:1]+np.cumsum(np.logaddexp(0,np.diff(base,axis=-1))+.2,axis=-1)],axis=-1)
    shape=1+.10*np.exp(-((hour-8)/2.5)**2)+.17*np.exp(-((hour-19)/2.5)**2)-.14*np.exp(-((hour-13)/3)**2)-.10*np.exp(-((hour-3)/3.5)**2)
    dowfac=np.array([1.,1.01,1.01,1.,.98,.92,.87])[dow]
    def ar1(size,phi,sd):
        a=np.zeros(size)
        for j in range(1,size):a[j]=phi*a[j-1]+rng.normal(0,sd)
        return a
    common=ar1(n,.6,.07);demand=np.zeros((len(t),3))
    for z,level in enumerate([34.,32.,24.]):
        daily=(common+ar1(n,.6,.05))[day]
        demand[:,z]=level*shape*dowfac*(1+daily+ar1(len(t),.8,.025))
    return anchors,demand


def kernel(c):
    capacity=np.array(c['CAP'],float);linecap=np.array(c['LINE_CAP'],float)
    M=np.zeros((len(c['LINES']),3))
    for j,(a,b) in enumerate(c['LINES']):M[j,a],M[j,b]=-1,1
    def clip(x,cap,tau):return tau*(np.logaddexp(0,x/tau)-np.logaddexp(0,(x-cap)/tau))
    def evaluate(price,anchors,demand,tau,compute_jacobian=True):
        dp=np.maximum(np.diff(anchors,axis=-1),1e-3)
        slope=(capacity[None,:,:,None]/5)/dp
        x=price[:,:,None,None]-anchors[...,:-1]
        generation=(slope*clip(x,dp,tau)).sum(axis=-1)
        scarcity_x=(price-c['SCARC_A'])/c['SCARC_B']
        backstop=clip(scarcity_x,c['SCARC_CAP'],tau)
        xf=(price@M.T)/c['FLOW_COST']
        flow=clip(xf+linecap,2*linecap,tau)-linecap
        jac,gen_slope=None,None
        if compute_jacobian:
            gen_slope=(slope*(expit(x/tau)-expit((x-dp)/tau))).sum(axis=(-1,-2))
            backstop_slope=(expit(scarcity_x/tau)-expit((scarcity_x-c['SCARC_CAP'])/tau))/c['SCARC_B']
            flow_slope=(expit((xf+linecap)/tau)-expit((xf-linecap)/tau))/c['FLOW_COST']
            jac=np.einsum('lz,tl,ly->tzy',M,flow_slope,M)
            diagonal=gen_slope+backstop_slope
            jac[:,np.arange(3),np.arange(3)]+=diagonal
        excess=generation.sum(axis=-1)+backstop+flow@M-demand
        return excess,jac,generation,flow,backstop,gen_slope
    return evaluate


def solve(evaluate,anchors,demand,tau,p0=None):
    p=np.full((len(demand),3),60.) if p0 is None else p0.copy()
    ridge=1e-3*np.eye(3)
    for iteration in range(300):
        residual,J,*_=evaluate(p,anchors,demand,tau)
        if abs(residual).max()<1e-9:break
        step=np.linalg.solve(J+ridge,residual[...,None])[...,0].clip(-25,25)
        best=np.full(len(p),np.inf);candidate=p.copy()
        for alpha in [1.,.5,.25,.125,.0625,.03]:
            trial=p-alpha*step;loss=(evaluate(trial,anchors,demand,tau,compute_jacobian=False)[0]**2).sum(axis=1)
            improve=loss<best;best=np.where(improve,loss,best);candidate=np.where(improve[:,None],trial,candidate)
        p=candidate
    else:raise RuntimeError('Toy forward port did not converge; no speed claim')
    # Same detached-solution reattachment's numerical forward correction.
    residual,J,*_=evaluate(p,anchors,demand,tau)
    p-=np.linalg.solve(J+ridge,residual[...,None])[...,0]
    return p,iteration


def run(path):
    if hashlib.sha256(path.read_bytes()).hexdigest()!=EXPECTED_NOTEBOOK_SHA256:
        raise ValueError('This equation port is bound to the reviewed upload; review changed notebooks separately')
    c=constants(path)
    if len(c['CAP'])!=3 or len(c['CAP'][0])!=4 or c['N_DAYS']!=30:raise ValueError('This review port is specific to the supplied30-day/three-zone notebook')
    anchors,demand=scenario(c);evaluate=kernel(c);tau=c['TAU_TRUE']
    cold=[]
    for _ in range(3):
        began=time.perf_counter();price,iterations=solve(evaluate,anchors,demand,tau);cold.append(time.perf_counter()-began)
    residual,J,gen,flow,backstop,gen_slope=evaluate(price,anchors,demand,tau)
    perturbation=np.zeros_like(price);perturbation[:,1]=1e-4
    finite=(evaluate(price+perturbation,anchors,demand,tau)[0]-evaluate(price-perturbation,anchors,demand,tau)[0])/2e-4
    error=float(abs(finite-J[:,:,1]).max())
    exact=np.linalg.solve(J,gen_slope[...,None])[...,0]
    ridged=np.linalg.solve(J+1e-3*np.eye(3),gen_slope[...,None])[...,0]
    warm=[]
    for _ in range(3):
        began=time.perf_counter();shifted,warm_iterations=solve(evaluate,anchors+.1,demand,tau,price);warm.append(time.perf_counter()-began)
    capacity=np.array(c['CAP'],float);linecap=np.array(c['LINE_CAP'],float)
    if abs(residual).max()>1e-9 or error>1e-7:raise ValueError('Equation/Jacobian replay failed')
    bias_checks=[]
    for temperature in [c['TAU_FIT_START'],c['TAU_FIT_END']]:
        p,_=solve(evaluate,anchors,demand,temperature)
        _,j,_,_,scarce,dq=evaluate(p,anchors,demand,temperature)
        exact_sensitivity=np.linalg.solve(j,dq[...,None])[...,0]
        notebook_sensitivity=np.linalg.solve(j+1e-3*np.eye(3),dq[...,None])[...,0]
        bias_checks.append(dict(tau=temperature,parameters='synthetic true parameters, not learned theta_hat',max_scarcity_gw=float(scarce.max()),
            max_price_sensitivity_bias=float(abs(exact_sensitivity-notebook_sensitivity).max())))
    OUT.mkdir(exist_ok=True)
    record=dict(status='passed_numpy_equation_replay_only',notebook_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        audit_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),hours=len(demand),zones=3,technologies=4,
        notebook_parameters=3*4*6*(1+10+1),numpy_version=np.__version__,cold_forward_seconds=cold,warm_shifted_forward_seconds=warm,
        cold_newton_iterations=iterations,warm_newton_iterations=warm_iterations,max_balance_residual_gw=float(abs(residual).max()),
        max_analytic_jacobian_error=float(error),max_scarcity_gw=float(backstop.max()),
        max_generation_bound_violation_gw=float(max(np.maximum(-gen,0).max(),np.maximum(gen-capacity,0).max())),
        max_flow_bound_violation_gw=float(np.maximum(abs(flow)-linecap,0).max()),
        price_quantiles=np.quantile(price,[.05,.5,.95],axis=0).T.tolist(),
        exact_uniform_bid_shift_sensitivity_max_error=float(abs(exact-1).max()),
        notebook_ridged_uniform_shift_sensitivity_max_bias=float(abs(ridged-exact).max()),
        ridge_bias_at_fit_temperatures=bias_checks,
        warm_uniform_shift_price_error=float(abs(shifted-price-.1).max()),
        limitations='NumPy forward equations only; no PyTorch/Adam training executed; no European-data/physical-network speed or price-fit claim.')
    (OUT/'audit.json').write_text(json.dumps(record,indent=2))
    print(json.dumps(record,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--notebook',required=True,type=Path);run(p.parse_args().notebook)
