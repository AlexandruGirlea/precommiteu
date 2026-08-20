<!--
SPDX-FileCopyrightText: 2026 Alexandru Girlea

SPDX-License-Identifier: Apache-2.0
-->

# Contributing

## Setup

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
```

Tests need no model bundle. Scanning does, see [docs/install.md](docs/install.md).

## Pull requests

- One change per PR, with a note on why.
- `pytest` and `ruff check .` must pass; CI runs both on Python 3.11 to 3.13.
- New functionality ships with its tests. A PR that adds a flag, an output
  format or a code path adds the tests covering it in the same PR.
- Detection quality changes (prompts, adapters, thresholds) are gated on an
  evaluation run, not unit tests. Open an issue before starting one.

## Reporting a missed or wrong finding

Include the source snippet, the regulation, and what you expected. A false
positive is a higher-priority bug than a false negative.

Do not paste proprietary or personal data into an issue. Reduce it to a small
synthetic example that still reproduces the behaviour.

## Licensing of contributions

This project is fully open source under the Apache License 2.0. Contributions
are accepted on the same terms: as set out in section 5 of that license, any
contribution you intentionally submit for inclusion is licensed under
Apache-2.0, without any additional terms. No separate contributor licence
agreement is required.

Only submit work you have the right to contribute. Do not submit code, data or
text owned by an employer or a client unless you are permitted to do so.

## Disclaimer

precommitEU is provided as is, without warranty or condition of any kind. It
produces a compliance signal, not legal advice, and it is not a substitute for
legal analysis. See [LICENSE](LICENSE) and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
