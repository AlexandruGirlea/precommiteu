<!--
SPDX-FileCopyrightText: 2026 Alexandru Girlea

SPDX-License-Identifier: Apache-2.0
-->

# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [semantic versioning](https://semver.org/).

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
