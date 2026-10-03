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

## Numerical certificate audit

At iteration 791, the two-block run closed its configured gap but failed
monolithic parity: its feasible objective exceeded the reference by €0.03496,
and its lower bound exceeded the reference by €0.02476. This is a numerical
certificate discrepancy, not evidence of a different economic optimum. The
attempt is retained for diagnosis and is explicitly uncertified.

The next reference attempt uses primal/dual tolerances of 10⁻¹⁰ and a €0.001
absolute stopping gap with no relative contribution. It starts with fresh cuts
to avoid retaining the earlier numerical lower-bound error. Reference validation
now also rejects a lower bound more than €0.02 above the monolith. This stricter
attempt has not yet passed; an annual optimum remains unverified.

## Disk-backed block preparation

`tools/disk_storage_blocks.py` stores sparse LP coefficients in atomic numeric
NPZ archives and loads one block at a time without retaining a matrix cache.
The reference driver accepts `--disk-blocks` to exercise this path. Round-trip
and coordinator-parity tests cover coefficients, optional constraints, bounds
and objective certificates. Archives do not use pickle.

This reduces retained block-matrix memory; it does not yet constitute an annual
runner. Preparing a full monthly native LP must still fit available memory, and
the master cuts remain in memory. Annual source fingerprints, boundary closure,
paired intervention validation and a convergence certificate remain required.

Disk-backed sequences fingerprint each prepared archive with SHA-256 and verify
it before every load, including slices. Changed archives abort rather than
silently alter the coordinated model. The tighter reference was interrupted
without a solver traceback after iteration 558, with a €1.45 gap; the saved
cuts remain resumable, but its stale running receipt is not a live process.

The disk-backed resumption stopped on contradictory local infeasibility at
iteration 558: Phase I measured only 1.78×10⁻¹⁰ violation. Local solves now
try interior point with crossover after persistent simplex status 2 or 4,
keeping the same LP and primal/dual tolerances; IPM optimality tolerance is
10⁻¹². Persistent inconsistency still aborts. No feasibility gate is waived.

The driver records `preparing`, process ID and UTC start time before loading
the network or constructing blocks. Iteration receipts also include the process
ID. An absent process still overrides these receipts: preparation and running
labels are not proof of a live job. The prior receipt status/iteration is retained
in the preparation record to distinguish a fresh attempt from stale progress.

Disk-backed preparation is reusable across restarts. A manifest fingerprints the
native input, diagnostic input, driver, exporter, diagnostic implementation and
archive implementation. Matching dependencies allow reuse only after every
archive passes its stored hash. Changed dependencies trigger fresh preparation;
changed archives fail rather than silently change coefficients. No manifest
means preparation must be regenerated before the cache can be trusted.

Stage receipts now distinguish independent block relaxations, unrestricted master
solves and local block solves. Each stage records process identity and elapsed
time atomically, so an interrupted resume can be located before its next
iteration checkpoint. These diagnostics do not alter LP coefficients or gates.

Each local solver attempt now has a 60-second solver time limit. The previous
retry was last observed inside block 0 at iteration 559 and stopped without
a traceback. A solver time-limit status now raises a diagnostic failure; it
never supplies a cut, feasible upper bound or convergence certificate. This
bounds one numerical retry sequence to at most three solver attempts, excluding
Python assembly and archive loading time. The real-data reference is still
uncertified and annual coordination remains blocked.

The bounded retry recorded a local solver timeout at the stabilized proposal
for block 0, iteration 559. The driver now offers `--no-stabilization` to use
unrestricted master proposals while retaining all saved cuts, physical
constraints and convergence gates. Stabilization is a proposal heuristic, not
part of the lower-bound certificate. A test covers unstabilized resumption.
The new real-data attempt remains unverified.

The unrestricted-proposal run advanced through iteration 586 before the master
solver reported unboundedness. With finite inventory bounds and finite cost
variable floors, this master has a finite objective lower bound. The master
retry now includes status 3 (unbounded), using the identical LP without presolve.
A targeted bounded-master test covers this contradictory status. Persistent
failure remains fatal; the last recorded gap was €1.43915, not convergence.

## Master numerical scaling

The saved real-data master reached 3,092 rows, coefficient magnitudes up to
11,547 and right-hand sides up to €602 million. `solve_master` now translates
variables by finite lower bounds, scales finite ranges (or uses 10⁶ for an
unbounded range), normalizes constraint rows and normalizes the objective.
It restores the returned primal variables and objective to original MWh/euro
units. These invertible transformations preserve the LP; numerical tolerances
operate in scaled units, so the existing native-reference objective and bound
parity gates remain essential. Analytical tests include a €300 million case.
The real-data scaled retry remains uncertified.
