# Python tool inventory

The two research baseline entrypoints are listed in `../baselines/fast_dispatch_only/README.md` and `../baselines/mixed_curve_fitting/README.md`. The site checks are `check_public_assets.py` and `check_zone_price_traces.py`; `check_baseline_catalog.py` verifies the two retained research witnesses.

This directory retains 112 Python files. A static import trace from the two baselines and site checks reaches 91 modules. Additional files are named in the live country explorer's receipts and retained so its provenance checker can verify their original source hashes. They are not additional active model candidates. Source-hashed files remain at their original paths; moving or editing them would detach saved receipts.

Reducing the tree to about 20 Python files would require consolidating the solver modules, rebuilding the numerical replay and source hashes, and migrating the country explorer to a current model or source-only view. File count alone is not a safe cleanup criterion. Retired code and reports remain available in Git history.
