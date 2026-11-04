<!--
SPDX-FileCopyrightText: 2026 Alexandru Girlea

SPDX-License-Identifier: Apache-2.0
-->

# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [semantic versioning](https://semver.org/).

## 0.3.2

- Refresh the README and package description with air-gapped installation,
  local model inference and the Azure deployment path through precommitEU ops.
- Publish the 450-case 0.3.0 evaluation summary, including per-pack results,
  false-positive denominators, recall tradeoffs and limitations.
- Pin model downloads to v0.3.0 and clarify that model and scanner versions
  are independent. Include checksums and licence files in download examples.
- Correct CI examples and document report retention and merge gating.
- Scanner logic, prompts and model weights are unchanged from 0.3.1.

## 0.3.1

- Scan every change in a GitHub push, including multi-commit and force pushes.
  Use the remote merge target for pull requests and fail when required history
  cannot be fetched. Other CI systems can set `GIT_DIFF_BASE` explicitly.
- Resolve CI scans from the repository root when invoked in a subdirectory.
- Support Vue, Svelte, SQL and shell source files. Apply code-file and ignore
  filtering to repository context reads, searches and directory listings.
- Keep the active regulation's labels and article titles after refreshing the UI.
- Preserve completed, paused and failed scan status when reselecting a pack or
  saving settings.
- Stop the elapsed-time counter when a scan ends, including in PDF reports.
- Keep the selected sidebar item readable when hovered.

## 0.3.0

- Run the orchestrator and validator on a new shared model, `orchestrator.gguf`
  (Qwen3.6-35B-A3B). The detector keeps `base.gguf` with the per-regulation
  adapters. Model roles are fixed by the bundle layout; individual model and
  adapter overrides are removed. Missing models or selected adapters stop the scan.
- Add `orchestrator.gguf` (16.5 GiB) to the model bundle. Scans need 32 GB of
  RAM and about 23 GB of disk. The UI downloads both shared models and warns
  when the machine has less memory.
- Raise the per-file wall-clock budget from 90 to 300 seconds.
- Require llama.cpp build 10158 or newer.
- Turn off chat-template thinking on every model request.
- Run CI scans in the precommitEU container on your own Linux runner with
  32 GB of RAM; hosted runners are too small. Each release publishes the
  image to `ghcr.io/alexandrugirlea/precommiteu`, built from the new
  `Dockerfile`; the models are mounted from the runner machine. See CI
  integration.
- Run the GitHub Action inside that container. It no longer installs
  llama.cpp or the scanner or downloads models, and the `version`,
  `models-revision` and `llama-build` inputs are removed. Older action
  versions install the latest scanner by default and fail without
  `orchestrator.gguf`; pin `version: 0.2.4` there until you move.
- Recheck cached files after upgrading so the new model runs on unchanged code
  too.

## 0.2.4

- Check AI Act findings against the actor, activity and literal configuration
  values in the source. Correct provider/deployer article assignments and handle
  CE-marking and trial-erasure exceptions.
- Add scope and article checks for GDPR, EU Data Act, DORA and DSA. Require the
  validator to describe source facts before classifying CRA/DMA/NIS2 findings.
- Recheck cached files after upgrading so the new validation runs on unchanged
  code too.
- Add opt-in local-model evaluation tools and regression fixtures for article
  selection and scope checks.

## 0.2.3

Fixed false positives for AI Act Articles 59 and 78 in customer storage and
support logs. Other regulation checks are unchanged.

## 0.2.2

- Constrain validator evidence to exact visible source lines, preventing invented
  or abbreviated quotations from discarding otherwise valid findings. Invalid
  validator output now marks the scan incomplete.
- Require supported AI Act applicability before confirming a finding, including
  the registration and confidentiality contexts for Articles 71 and 78.
- Keep case-retrieval matches as unconfirmed, non-blocking advisories across all
  regulations; similarity alone no longer promotes a candidate to a finding.
- Fix the orchestrator output grammar and stop HTTP URL paths from being
  mistaken for references to local sibling modules.
- Invalidate older scan caches so unchanged files are rechecked with these fixes.
- Add regression tests and a workplace emotion-recognition Java fixture.

## 0.2.1

- Releases are built in CI and published to PyPI through Trusted Publishing,
  with SLSA level 3 provenance attached to the GitHub release and PEP 740
  attestations on the published artifacts.
- The repository is REUSE 3.3 compliant: every file carries copyright and
  licensing information, and the Apache-2.0 text is in `LICENSES/`.
- No changes to the scanner itself.

## 0.2.0

- Incremental rescans: a scan records every file it analysed cleanly, and the
  next scan of the same folder and regulation reuses the unchanged ones instead
  of analysing them again. The record is one JSON file per folder and
  regulation under `~/.precommiteu/scans/`, never inside the scanned folder.
  `--rescan-all` forces a full pass, `--scan-log` moves the record, `--ci`
  keeps none.
- `precommiteu ui`: starts a local web UI over the scanner and nothing else;
  the folder to scan is chosen in the UI. Readiness checks with
  one-click installation of what is missing, a regulation screen that downloads
  adapter packs on demand and verifies their checksums, live per-file progress
  and ETA, then findings and advisories. Install with `pip install
  precommiteu[ui]`; `fastapi`, `uvicorn` and `huggingface_hub` stay optional so
  CI installs are unaffected.
- One regulation pack is active per scan, selected in the UI. Scan state and
  cached results are kept per pack.
- UI: the Target screen scans only the changed files, starts clean, or forgets
  the cached findings for a folder. A Settings screen moves the model bundle,
  the scan cache and the reports directory without a restart.

## 0.1.0

First release.

- Local scanning of source files against GDPR, EU AI Act, EU Data Act, DORA,
  DSA and CRA/DMA/NIS2.
- Confirmed findings backed by code evidence; unconfirmed candidates reported
  as non-blocking advisories.
- `precommiteu scan` with `--ci` diff mode, `--json-out`, `--sarif`, `--out`
  and `--report` output, written incrementally.
- `eu-ignore` directives and `precommiteu-ignore` inline markers.
- Python API: `scan_paths`, `scan_diff`.
