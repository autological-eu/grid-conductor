# Durable research backup and recovery

Investigation: 4 October 2026. This is an engineering proposal, not evidence of a
completed remote backup. Product and model acceptance gates are unchanged.

## Findings

The current cloud workspace contains approximately 14 GiB under
`data/pypsa-eur/`, 1.3 GiB under `data/carbon-pilot/` and 63 MiB under
`data/price-trace/`. These totals include environments, upstream checkout,
rebuildable caches and a duplicate staged snapshot; they are not all unique
research inputs that need backup.

`tools/backup_2025_checkpoint.py` already stages an explicit file allowlist,
splits files into 512 MiB pieces and records SHA-256 hashes. Its local
`release-backup-20261001` snapshot is approximately 2.1 GiB. The GitHub draft
release `research-2025-checkpoint-20261001` exists, but its asset list is empty.
It is therefore **not a remote backup**. This investigation attempted a 476-byte
README upload using `gh release upload`, then the upload API with an explicit
Content-Length. Both returned HTTP 400, `Bad Content-Length`. The transport cause
is not established. No data asset upload or restore has been verified.

## Recommended storage

Use GitHub Release assets for immutable, attributable research snapshots,
provided their redistribution rights permit publication and upload/restore work.
Keep large artifacts out of ordinary Git history and Git LFS. Release downloads
are separate from the Pages deployment artifact.

GitHub's current [release documentation](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)
states at most 1,000 assets per release, each under 2 GiB, with no total release
size or bandwidth limit. This fits the project's zero-cost goal better than
metered object storage. It is still dependent on GitHub/account availability,
not an unconditional promise of permanent access.

Actions artifacts are useful for transferring a completed job, but have retention
and storage accounting; caches are evictable. Neither should be the sole durable
copy. A draft release requires authenticated access and is not a publicly
accessible download. Published assets in this public repository would be public:
review redistribution rights and the explicit allowlist before publishing.
Credentials, restricted provider data and raw account-specific responses do not
belong in a public release. Keep any such material in a separately authorized
private backup, rather than silently publishing it.

## Snapshot scope

1. Immutable 2025 prepared inputs: compact weather, annual hydro, prepared native
   network, verified month receipts, upstream version/patches and configuration.
2. Completed monthly dispatch and native LP blocks, with hashes and assumptions.
3. Versioned solver checkpoints and logs, stored separately from large immutable
   inputs so progress backups do not repeatedly upload weather.
4. Publicly redistributable generation/price inputs only after a source-rights
   audit. Published app artifacts already have a copy in Git.

Exclude dependency environments, downloaded upstream software that can be
reinstalled from pins, duplicate staging directories, temporary raw weather,
secret files and recursively selected cache trees. A snapshot of a live job must
copy only atomically committed checkpoints; retry if a file changes while being
copied. Backup status is not research validation.

## Implementation and acceptance gates

- Replace hard-coded date/paths with a versioned, explicit snapshot allowlist and
  caller-selected tag; record source commit, upstream commit, code/input hashes,
  model scope, snapshot time and file sizes.
- Preserve immutable snapshots. Do not use `--clobber` to replace an already
  verified backup; new data gets a new version/tag.
- Stream file hashing/chunking to bound memory and avoid staging duplicate whole
  caches. Reuse already verified immutable input snapshots in checkpoint manifests.
- Resolve the current upload transport failure with a small nonsecret asset first.
  Compare the downloaded bytes and hash, not merely reported asset sizes.
- Upload data parts first and a completion manifest last. A release without a
  verified completion manifest is incomplete, including the existing empty draft.
- Provide a restore command that downloads into a separate destination, rejects
  absolute/traversal paths and symlink escapes, checks every part and assembled
  file hash, and never overwrites current research or credentials by default.
- Perform a clean-directory restore drill. Verify network timestamps, original
  renewable availability and a prepared LP/checkpoint resume against its hashes.
- Retain at least the latest verified checkpoint and its predecessor, plus the
  immutable input snapshot they reference. Delete no local inputs until a remote
  download-and-restore check passes; remote retention cleanup is a separate action.

Next actionable step is fixing the small-asset upload and download test. Then
implement and test restore, and only then upload the expensive prepared inputs.
The existing snapshot protects neither current monthly coordination progress nor
new carbon collection until these steps succeed.
