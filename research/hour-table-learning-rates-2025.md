# Local-hour curves: Adam learning-rate comparison

User-authorized test: three separate January fits at Adam0.05,0.15,0.5, each100
updates plus initialization and full February evaluation. One sequential suite
avoids CPU contention; each trial starts in an isolated interpreter. No old fit
is resumed. Current status: launched, numerical completion pending.

One curve per local hour/technology/zone is shared across days. Two additive
daily conditions are January-centered weekend and available/reference fraction.
24-hour table initialization is exactly the same neutral60EUR/MWh utilization
slope and-30EUR/MWh markup for every rate. Cyclic neighbouring-hour regularization
and shrinkage each0.001. This is a new26-feature sharing model, not the prior
smooth harmonic conditioner. Within the suite only Adam rate changes.

Actual744January/672February hours,48 modeled/41 complete price-target areas,
monthly generation references, source fuel costs, fixed hydro and fast95-corridor
constraints remain. Reference capacity is the same annual available-output
proxy, not independently verified installed nameplate. No original coupled PTDF
or investment/annual acceptance claim. Forward February labels only score;
prior development exposure and any validation selection are explicit.

Five unit tests pass: local-hour sharing/neutral initialization, training-only
condition centering, regularizer gradients, spline quadrature/monotonicity and
inverse derivatives. Each trial also checks its full dispatch-condition gradient
on seven real European hours. All numerical gates unchanged. Failed rates retain
logs/receipts; remaining rates still run without changing their configuration.

Outputs are ignored under:
`data/bidding-zone-network-2025/hour-table-learning-rates-v1/`.
The read-only watcher refreshes report.md,comparison.png andlearning-curves.csv.
Per-rate plots refresh every five updates. Retain all parameters/hourly prices,
actual101-point histories, generation errors and source hashes. Check real child
PID/start/state and receipts before completion claims or new computation.

No automatic1000-update extension or baseline replacement. Compare price and
generation tradeoffs and stable convergence first. No public deployment.
