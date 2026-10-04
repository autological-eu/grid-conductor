# Coordinating chronological storage inventories

## Current reference result — 3 October 2026

The two-block 48-hour conditional reference now passes its configured numerical
gates: **€0.0002267 master/feasible gap** and **€0.007903 difference from native
monolithic cost**, against pre-existing limits of €0.001 and €0.02 respectively.
Independent final-inventory re-solves reproduced the total €294,446,869.947464
objective; maximum original-unit equality residual was 8.09e-9, inequality
violation 1.85e-12 and variable-bound violation zero.

[Machine-readable reference and independent audit](../public/research/network-benchmark-2025/coordination-reference.json)

The floating-point lower bound is €0.007676 above the native objective. It
passes the declared parity tolerance, but does **not** exactly enclose that
known reference: do not describe it as an exact mathematical certificate.
All figures concern 1–2 January 2025 with fixed initial/final inventories,
not an annual optimum or seasonal water-value validation. Iteration 738 includes
checkpoint history; reported resumed-segment time is not total runtime or a
speed comparison.

The next task is the streamed/resumable annual coordinator and its independent
audits. The following sections preserve the failed-attempt history and explain
the numerical corrections. Reproduce the final audit with
tools/publish_2025_coordination_reference.py after the reference validator.


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

The scaled run reached iteration 598 and a €1.29946 gap before a local timeout.
An optional `--proposal-fraction` now interpolates the next candidate between
the best known feasible inventory and the master proposal. This is a search
heuristic: local LPs still verify feasibility, the unrestricted master still
provides the lower bound, and convergence/parity gates are unchanged. A damped
analytical test verifies the original optimum and lower bound. The real-data
attempt uses fraction 0.5 and remains uncertified.

## Bounded timeout recovery

The damped 48-hour reference reached a €0.02705 bound gap before a local
solver timed out at iteration 655. That result is **not certified**. Local
timeout status now triggers the same bounded fallback sequence as numerical
failure: dual simplex without presolve, then interior point with presolve.
Each attempt retains its 60-second limit and the original LP and tolerances.
A partial solution from a timed-out attempt never contributes an objective or
dual cut; exhausted retries stop with failure rather than implying infeasibility.
Two regression tests cover successful recovery and exhausted timeouts. The
€0.001 convergence threshold and €0.02 native-reference parity gate are unchanged.


The first timeout-recovery attempt also exhausted its three bounded solves at
the same reference candidate. The final interior-point retry now enables
presolve, allowing redundant rows and fixed variables to be removed before
factorisation. This changes solver preparation, not the physical LP, state
boundaries or certification thresholds. Regression tests assert that this
fallback uses presolve. Real-data convergence remains unverified.


## Reproducible numerical conflicts

The presolved fallback advanced the conditional reference to iteration 736 with
a reported €0.001223 gap, still above the €0.001 gate. It then stopped because
the cost LP reported infeasibility while Phase I found an 8.05e-8 violation.
This is not a certified result. Numerical disagreement does not authorize
accepting the candidate or weakening the convergence threshold.

The validator now saves the proposed boundary inventories, block index, source
hash, block hashes and Phase-I violation in ignored coordination-failure.json.
The standalone tools/diagnose_2025_coordination.py validates those fingerprints
and re-solves just that fixed-state block using bounded simplex/interior-point
attempts with and without presolve. It reports equality residuals and inequality
violations for successful solves. These are diagnostics, not objective cuts,
accepted upper bounds or an annual-optimum certificate. A regression test
checks that the conflict records its state and still fails closed.

The captured retry at iteration 736 gave Phase-I violation 4.75e-8. Replaying
that same fingerprinted local LP returned infeasibility for presolved dual
simplex and both interior-point configurations; dual simplex without presolve
timed out at its 30-second limit. No configuration returned an optimal primal
or usable objective duals. This reproducer now isolates boundary feasibility
and numerical conditioning from the preceding hundreds of master iterations.
No annual-result gate has passed.


## Inventory proposal roundoff

The captured state contains a -4.74848e-8 MWh inventory despite its zero lower
bound. Phase I placed exactly that amount in a single inequality slack. This
isolates an actual proposal bound violation, rather than proving that an
otherwise feasible state was rejected.

The scaled master may return a proposal with tiny original-unit roundoff.
Before local solves, candidate inventories now snap to their exact lower/upper
bounds only when the overshoot is within the existing feasibility tolerance.
Larger overshoots fail. Master equalities and supplied inequalities are checked
again after correction. The unrestricted master objective and lower bound are
never changed. Every corrected candidate is independently re-solved, and cuts
are anchored at the corrected state, not the original proposal.

Tests cover both bound directions, fixed states, unchanged source arrays,
rejection of larger violations, and a corrected candidate being solved before
any feasible upper bound is accepted. This is a numerical search correction,
not relaxation of storage physics or of the €0.001 convergence gate. The
real-data retry remains subject to native objective/bound parity.

The corrected real-data retry passed the captured candidate and reached
iteration 738, then stopped on a proposal lower-bound overshoot larger than
the existing tolerance. The last recorded gap remained €0.001223. The check
therefore exposed a second master-precision issue rather than certifying
convergence. No annual result or model integration follows from this retry.


## Finite master scaling cap

Finite master-variable scales now use min(100, max(1, upper - lower)).
Previously a large reservoir range could amplify a 1e-10 solver bound
tolerance into a material original-unit inventory overshoot. The capped
transformation limits that nominal amplification to 1e-8 in original units.
This is numerical scaling, not a guarantee of arbitrary solver residuals:
proposal bound checks and independent local solves remain mandatory.
Unbounded objective variables retain their existing scaling. Physical bounds,
master cuts and the convergence/parity thresholds are unchanged.

A regression test uses a billion-unit inventory range and a solver boundary
roundoff value to verify the restored error remains below the existing
proposal tolerance. The real-data checkpoint retry is still required before
claiming reference convergence.


## Annual preparation pipeline

tools/prepare_annual_coordination.py now prepares native monthly LP coefficients
in separate worker processes, one month at a time. It requires a complete ordered
hourly calendar with unit weights and rejects unsupported Stores, commitment,
ramps, annual generation budgets, expansion and dynamic storage parameters.
Only a transmission-volume expansion constraint on checked fixed capacities is
removed, with its identity recorded explicitly.

Every block links to a shared 13-boundary inventory vector and keeps original
hourly generation availability, demand and inflows. Source/code/block hashes
guard resume; a 6 GiB worker memory limit and free-disk check bound preparation.
Raw matrices and receipts remain ignored. All twelve 2025 months prepared successfully. The reproducible audit tool
tools/audit_annual_coordination_preparation.py verified source/code/archive
hashes, 8,760-hour chronology, 160 storage identities and 2,080 shared boundary
variables. Compressed archives total 271 MB and remain offline.
This step exports coefficients only: it is not a monthly dispatch result, an
annual solve or a convergence certificate. Annual coordination, boundary
conditions, warm-state validation and final independent audits remain unfinished.


## Annual inventory workspace and warm checks

The annual workspace now encodes the source boundary semantics explicitly.
Cyclic units have free bounded initial inventories with final=initial;
noncyclic initial inventories stay fixed to the source, and their terminal
inventories remain free within capacity. All 160 units in this prepared
network are cyclic. This is different from fixing cyclic initial values at
zero merely because the sequential warm run started there.

tools/build_annual_inventory_workspace.py verifies all block and sequential
result hashes and exact month-to-month warm continuity, then writes sparse
closure/reachability constraints and candidate inventories. The prepared
workspace has 2,080 variables, 160 closure equalities and 5,760 necessary
single-asset reachability inequalities. The warm inventories passed with
zero reachability violation. This does not establish network feasibility.

tools/audit_annual_warm_state.py independently re-solves fixed monthly
inventories in separate memory-guarded processes, verifies original-unit
primal residuals and records source/workspace/block fingerprints. A result
is not reused against changed inventories. Monthly results are conditional,
not annual optima; a feasible annual upper bound requires all twelve
successful re-solves and verified continuity. Annual coordination, objective
cuts, convergence and final independent result audits remain unfinished.

The first January fixed-inventory re-solve exhausted the existing bounded
60-second solver attempts. Peak sampled memory was 5.71 GiB, below its 6 GiB
guard. No optimal primal or monthly cost receipt was accepted. Full-month
solver budgeting/configuration remains a blocker; the small-reference time
limits are not evidence that the prepared monthly LP is infeasible.

### Full-month execution budget

The annual warm audit now accepts `--solver-seconds` (default 300, at most
600 per attempt) and `--first-solver` (`highs-ipm` by default). It makes at
most three solver attempts; with the default budget their solver time is
bounded by 900 seconds, excluding input loading and preprocessing. The
6 GiB process-memory guard remains active. Reference solves retain their
60-second default.

This changes execution configuration only: the original monthly LP,
1e-10 primal/dual solver tolerances, 1e-12 IPM optimality tolerance and
1e-7 original-unit residual acceptance gates are unchanged. Time-limit
solutions are rejected. A successful fixed-boundary month establishes
conditional feasibility and cost, not an optimised annual trajectory.
The January retry exhausted all three 300-second attempts. Peak sampled
memory was 5.91 GiB, below the 6 GiB guard, and no successful monthly receipt
was accepted. The failure logs are preserved offline. A further January retry
uses the configured maximum of 600 seconds per attempt (at most 1,800 seconds
of solver time). It reached a solver solution but failed the unchanged
1e-7 original-unit residual gate, with peak sampled memory 5.18 GiB.
No successful receipt was written. The audit now writes a separate rejected
diagnostic containing equality, inequality and variable-bound violation
magnitudes. These diagnostics cannot be used as accepted monthly results. All 25 storage coordinator tests pass, including budget validation
and preservation of the requested IPM tolerances.

### Acceptance-aware local retries

The January diagnostic measured equality residual 2.854e-7, inequality
violation 1.58e-12 and zero bound violation. The 1e-7 gate therefore rejected
the result despite solver-reported success. Monthly warm audits now check
original-unit residuals within the retry loop, allowing remaining bounded
configurations to run after an inaccurate success. At most three attempts
are still permitted; no tolerances or physical constraints are relaxed.
All 27 storage tests pass, including retry after inaccurate success and
failure after three inaccurate successes. Annual feasibility is still unverified.

### Retaining rejected monthly candidates

The acceptance-aware January retry failed: a solver-reported success exceeded
the original-unit residual gate, while the remaining configurations timed
out. Peak sampled memory was 5.92 GiB, below the 6 GiB guard. No monthly
receipt was accepted.

Monthly audits now retain a rejected primal vector as numeric-only NPZ
(without pickle), together with its source/block/warm-state hashes, solver
configuration, objective and residual diagnostics. This permits independent
inspection of the offending rows without another full solve. These files
are explicitly rejected diagnostics and cannot supply accepted feasibility
or convergence evidence. A bounded diagnostic retry is launched to capture
a candidate. The original physical LP and acceptance tolerances are unchanged;
all 27 storage tests pass, including rejected-candidate callback coverage.

### Rejected January row inspection (4 October 2026)

The diagnostic retry failed, but retained its rejected primal vector.
`inspect_rejected_monthly_primal.py` verifies the block, warm-state and
primal hashes, then inspects the 100 largest CSR equality residuals.
Worst row 117846 has 256 nonzero terms and zero right-hand side. Its
coefficients range in absolute value from 2.654 to 185.186; the sum of
absolute evaluated terms is about 419,349.

| Arithmetic | Worst-row residual |
| --- | --- |
| Original CSR evaluation | 2.854330887e-7 |
| Compensated sum of double-precision products | 2.854421837e-7 |
| Extended-precision products and sum | 2.854404126e-7 |

Agreement across these evaluations rules out ordinary summation error as
the explanation for this row's failed 1e-7 gate. This diagnostic inspects
selected rows only and is not a new acceptance check. The solution remains
rejected; no annual feasibility or optimality claim follows. No identical
full-month solve is restarted. Next work is a controlled conditioning or
solver-refinement experiment validated on the smaller matched reference
and audited in original units before returning to January.

    python tools/inspect_rejected_monthly_primal.py --folder data/pypsa-eur/annual-coordination

Raw diagnostic outputs stay ignored offline. All 27 existing storage tests
pass; the inspector was run on the actual hash-verified retained candidate.

### Rejected row-normalization experiment

`condition_storage_block.py` multiplies each equality/inequality and its
boundary coupling/right-hand side by the same positive row factor. Costs
and variable bounds stay unchanged. Analytical tests preserve objective
values and boundary gradients, including inequalities.

The experiment compared original and normalized blocks at the saved 48-hour
reference boundary state. Its initial run imposed an unnecessary extra
scaled-unit 1e-10 residual limit and failed; that limit was removed. The
second run used the original-unit 1e-7 feasibility and €0.02 cost-parity gates.
Block 1 still failed: equality residual 2.56179e-7, inequality violation
7.28e-12, zero bound violation. Cost difference was -4.77e-7 EUR; maximum
boundary-gradient difference was 2.46e-10.

Near-identical objectives do not establish feasible dispatch. This simple
normalization is rejected for annual use and no January solve is launched
with it. The experiment and failing diagnostics are retained for further
conditioning/refinement work. All 29 storage tests pass; this includes
analytical tests, not a passing numerical-reference experiment.

    python tools/check_conditioned_storage_reference.py

The tool writes a failure receipt before raising if an original-unit gate
fails. Offline diagnostics remain separate from accepted research artifacts.

### Bounded primal-correction diagnostic

`refine_rejected_primal.py` tests feasibility correction around a retained
rejected solution. It leaves the physical LP unchanged, solves for a correction
within ±1e-6 of each original variable, and audits the corrected vector against
all original equations, inequalities and variable bounds. The diagnostic
objective is zero; its duals cannot supply original-model objective cuts, and
a feasible result would not establish optimality.

The January test exceeded the 6 GiB memory guard (peak sampled 6.0036 GiB)
and was terminated before producing a result. No corrected candidate was
accepted. The original retained candidate remains unchanged. The CLI now
includes a 6 GiB memory guard and 120-second overall wall-time guard; the LP
solver budget is 60 seconds. These execution limits do not relax feasibility
checks. All 32 storage tests pass, including small-error correction, infeasible
correction boxes and invalid limits.

    python tools/refine_rejected_primal.py --folder data/pypsa-eur/annual-coordination

Next work should reduce refinement memory and validate on the smaller reference
before annual use. The failed full-month correction is not retried unchanged.
