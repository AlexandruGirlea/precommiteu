# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [semantic versioning](https://semver.org/).

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
