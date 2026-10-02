# Coordinating chronological storage inventories

The sequential 2025 monthly run preserves inventory continuity, but each month chooses its ending inventory without optimising future water value. It is a feasible chronological reference, not an annual optimum. The new coordinator addresses that missing optimisation; it remains under validation.

## Shared boundary states

Let $x_m$ contain reservoir and battery inventories at boundary $m$. A local block retains every hourly generation, flow, charging, discharging, spill and inventory variable. Only its starting and ending inventories are shared. With fixed capacity and continuous dispatch, each block is an LP:

$$q_m(x)=\min_{y_m} c_m^T y_m,$$

subject to

$$A_m y_m+B_m x=b_m,\qquad U_m y_m+V_m x\le r_m.$$

Inventory bounds live in the master. Originally cyclic assets require $x_0=x_{12}$, with the starting inventory optimised rather than silently fixed to zero. Noncyclic assets retain the source initial condition. Generator ramping, unit commitment, Stores, annual fuel/emissions budgets and expansion require additional shared state or constraints; unsupported features must fail rather than disappear.

## Objective and feasibility cuts

At a feasible candidate $x^k$, local duals give a subgradient $g_m$. The master accumulates supporting planes:

$$\theta_m\ge q_m(x^k)+g_m^T(x-x^k).$$

Minimising $\sum_m\theta_m$ gives a lower bound. Solving all blocks at one feasible shared state gives an upper bound. Independent block relaxations initialise valid objective floors; zero is not assumed when that would be invalid.

A proposed state can be infeasible—for example, a reservoir cannot reach a requested level with the available inflow and charging capability. A separate Phase-I LP minimises nonnegative violations of its equality and inequality constraints. Its duals generate a necessary feasibility cut:

$$\phi_m(x^k)+h_m^T(x-x^k)\le0.$$

Phase-I slack is a diagnostic used to exclude infeasible boundary proposals. It is never treated as genuine energy supply or an acceptable dispatch result.

## Convergence and validation

The implementation reports lower bound, best feasible upper bound and their gap on every iteration. It stops successfully only when

$$UB-LB\le\epsilon_{abs}+\epsilon_{rel}\max(1,|UB|).$$

An iteration limit means **not certified**. A lower bound materially above a feasible upper bound is an error. Numerical tolerances mean the reported gap is an LP solver certificate, not a formal exact-arithmetic proof.

`tools/storage_coordinator.py` implements the cut algorithm. `tools/pypsa_storage_blocks.py` exports native Linopy matrix coefficients and introduces explicit boundary inventories. It preserves hourly chronology, storage efficiencies and standing losses. Tests compare the coordinator with both a monolithic analytical LP and a native PyPSA model with cyclic inventory, asymmetric efficiency and standing loss; infeasible proposals and iteration-limit handling are tested separately.

`tools/validate_2025_coordination.py` additionally compares two 24-hour blocks against the saved 48-hour conditional native 2025 reference. That experiment uses fixed initial and terminal inventories, not the annual cyclic boundary. Passing it cannot establish full-year optimality.

## Remaining annual gate

The twelve-month production coordinator has not been validated or certified. Retaining all yearly LP matrices in memory would undermine the memory-saving purpose; the production driver needs streamed block workers, guarded resources and resumable cuts/checkpoints. A real annual run must retain the original free cyclic initial inventories, unsupported-feature gates and published availability inputs. No annual investment results should be derived from a nonconverged bound or extrapolated from the 48-hour benchmark.

The real-network reference run encountered a numerical Phase-I failure after
29 iterations and had not converged (last gap approximately €885,049).
The driver now records failures explicitly, retries HiGHS numerical-status
failures with dual simplex and presolve disabled, and saves atomic cut/bound
checkpoints for resumption. These changes are recovery mechanisms, not evidence
that the network reference or annual model has converged.

The unrestricted proposal rule stalled on the real reference: after 57
iterations the best feasible objective remained unchanged and the gap was
approximately €866,005. A level-stabilized proposal now minimizes scaled
inventory distance from the best feasible state, subject to an objective
level halfway between the current bounds. Every fifth iteration uses the
unrestricted proposal. The unrestricted master still supplies the lower bound;
stabilization never restricts that certificate. This change is being tested on
the real reference and does not constitute a convergence claim.

Single-asset inventory reachability is also projected directly into the
master. For a block, let $a$ be the product of retention factors, $R$ the
retention-weighted charging capability plus inflow, and $D$ the weighted
discharging capability. Boundaries satisfy

$$x_{end}\le a x_{start}+R,\qquad x_{end}\ge a x_{start}-D.$$

An additional constant upper envelope accounts for intermediate capacity
limits. `tools/inventory_reachability.py` derives these bounds for controllable
spill limited to available inflow. Forty randomized cases match full hourly
storage LP minima and maxima. These are storage-feasibility projections, not
an economic dispatch substitute; Phase-I checks remain active. They apply
only to the stated continuous storage assumptions. The current network
reference uses hourly weights and constant power/efficiency bounds.

A subsequent run stopped after iteration 110 because the local infeasibility
status disagreed with a near-zero Phase-I violation. Master and local solves
now use matching feasibility/duality tolerances, and an infeasible local status
is retried with presolve disabled before it is treated as a genuine feasibility
failure. This changes numerical handling, not the physical constraints. The
restart passed the previously failing point; convergence remains a separate gate.

## Reference validation tolerance and resumption

The 48-hour driver now uses an absolute gap of €0.01 plus a relative gap of
10⁻¹² times the objective magnitude, keeping its stopping threshold below the
€0.02 monolithic objective-parity gate for this reference. A parity failure is
written as `failed_not_certified` before the driver raises an error.

The 400-iteration run reached a feasible objective €117.11 above the native
monolith, with a €289.02 lower-to-upper-bound gap. It did not converge. A resumed
process stopped after iteration 402 without a recorded solver exception; its
`running` receipt therefore does not demonstrate an active job. Saved cuts allow
resumption, but neither result supports an annual-optimum claim.

The resumed reference reached iteration 766 with a €0.074635 bound gap, but
stopped on an unknown HiGHS master-LP status. It remains uncertified. Master
and level LPs now retry statuses 2 and 4 using dual simplex without presolve,
with identical constraints, cuts and feasibility tolerances. A targeted test
checks this retry; persistent failure still stops the run.
