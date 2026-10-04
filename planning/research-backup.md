# Research cache and recovery policy

Updated 4 October 2026 after the user's storage decision. The earlier proposal
for multi-gigabyte GitHub Release snapshots is superseded. No data assets were
successfully uploaded; the existing draft release was empty when inspected.

## Accepted direction

Do not put multi-gigabyte weather, network or raw-data backups in GitHub, including
Release assets. Do not establish a third-party bulk backup merely to download
reproducible inputs again. Keep these as local caches and make reconstruction
from original providers reproducible.

Prioritise compact recovery bundles for expensive computation state: solver
checkpoints, inventory states, receipts and results, together with code/input
hashes, source versions and model assumptions. A durable destination has not
been selected or verified; local staging is not remote protection. Keep secrets
and restricted source data out of any published recovery bundle.

## Reconstruction and verification

Record provider, exact request and UTC period, source version/license, upstream
commit and patches, configuration, expected hashes and preparation commands.
Credentials stay in environment secrets and never enter manifests. Re-downloads
must be checked against expected hashes. If a provider revised or removed data,
record a reproduction blocker rather than claiming identical matched inputs.

Prepared native networks and LP blocks require regeneration from the original
renewable availability and chronology; dispatch must never replace availability.
A reconstructed input with a changed hash cannot silently resume saved cuts.

A compact recovery bundle should copy atomically committed checkpoints, retry
files that change during copying, contain a versioned manifest and preserve
model scope (2013 weekly, 2025 conditional, annual). Verify downloaded hashes and
perform a clean-directory restore/resume drill before claiming durable recovery.
Do not overwrite current research or credentials during that drill.

## Current evidence and next actions

Local caches contain approximately 14 GiB of PyPSA-related data, including
reinstallable environments and duplicates; carbon caches are approximately
1.3 GiB. The old 2.1 GiB staged snapshot remains local and is not a verified
remote backup. The legacy `backup_2025_checkpoint.py` upload workflow is retired.

Next: inventory compact computation-state files, define an explicit credential-free
bundle allowlist, and document/test reconstruction of its pinned inputs. Choose a
remote destination only if needed for these compact bundles; no bulk upload is
authorised by this policy. Product/model validation gates remain unchanged.
