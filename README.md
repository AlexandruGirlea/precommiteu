<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/AlexandruGirlea/precommiteu/main/docs/assets/img/bat-hero-dark.png">
    <img src="https://raw.githubusercontent.com/AlexandruGirlea/precommiteu/main/docs/assets/img/bat-hero-light.png" alt="precommitEU" width="180" height="180">
  </picture>
</p>

<h1 align="center">precommitEU</h1>

<p align="center">
  <strong>Catch EU regulatory violations at PR time, on your own machine, with
  zero data egress.</strong>
</p>

<p align="center">
  One local scanner, eight EU regulations: GDPR, the EU AI Act, NIS2, DORA, the
  Cyber Resilience Act, the Digital Services Act, the Digital Markets Act and
  the Data Act.
</p>

<p align="center">
  <a href="https://alexandrugirlea.github.io/precommiteu/"><strong>Documentation</strong></a>
  &nbsp;&middot;&nbsp;
  <a href="https://alexandrugirlea.github.io/precommiteu/install.html">Install</a>
  &nbsp;&middot;&nbsp;
  <a href="https://alexandrugirlea.github.io/precommiteu/cli.html">CLI reference</a>
  &nbsp;&middot;&nbsp;
  <a href="https://huggingface.co/AlexandruGirlea/precommiteu-models">Model bundle</a>
  &nbsp;&middot;&nbsp;
  <a href="https://precommit.eu">precommit.eu</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/AlexandruGirlea/precommiteu/main/docs/assets/img/scan-demo.gif" alt="precommitEU scanning a Python project for GDPR violations">
</p>

A real scan, unedited: about 80 seconds on an M-series MacBook, played back at
5&times;. `models.py` holds only a dataclass, so the detector clears it and the
validator is never called. `user_store.py` mentions a sibling file, so the
orchestrator takes over: it resolves `UserProfile` into `models.py`, finds that
`audit_line()` interpolates a national ID and a home address, and confirms a
GDPR Art. 32 violation on a log line that looks harmless on its own. Grep
cannot find that one.

**[Replay this scan in your browser](https://precommit.eu/try)**. No install,
nothing to upload.

```bash
export PRECOMMITEU_MODELS_DIR=~/.precommiteu/models
precommiteu scan src/ --fail-on-findings
```

## The Zen of EU Code

1. Put purpose before collection.
2. Collect less than you could, and keep it for less time.
3. Let people know what the system knows.
4. Make consent a choice, not a trap.
5. Give people working controls over their data.
6. Protect what you keep, from design to update.
7. Children deserve stronger defaults.
8. Explain automated decisions before they become consequences.
9. Build systems that fail safely, recover clearly, and report harm responsibly.
10. Make switching, portability, and interoperability real.

*Run `precommiteu this` to print it.*

## Quick start

```bash
brew install llama.cpp
pip install precommiteu "huggingface_hub[cli]"
hf download AlexandruGirlea/precommiteu-models base.gguf gdpr/detector-adapter.gguf --local-dir ~/.precommiteu/models
export PRECOMMITEU_MODELS_DIR=~/.precommiteu/models
precommiteu scan src/
```

Linux, source and GPU builds, downloading more packs, air-gapped installs and
uninstall: **[Installation](https://alexandrugirlea.github.io/precommiteu/install.html)**.

`hf download` writes the bundle in the layout the scanner expects. Each
adapter must sit in a directory named exactly after its pack, because the
scanner resolves `<models-dir>/<regulation>/detector-adapter.gguf`:

```text
~/.precommiteu/models/
├── base.gguf                        # shared by every regulation
├── gdpr/detector-adapter.gguf
└── eu_ai_act/detector-adapter.gguf  # one directory per pack you downloaded
```

A flat directory does not work: a missing adapter is not an error, the scan
just continues on the base model alone in degraded mode and logs a warning.

```bash
precommiteu scan src/ --regulations gdpr,eu_ai_act    # several regulations
precommiteu scan --ci --fail-on-findings              # changed files only, gate the build
```

### From Python

```python
import os
from precommiteu import scan_paths

# Required unless you pass orchestrator_model_path / detector_adapter_path
# explicitly. Without it, scan_paths raises ValueError.
os.environ["PRECOMMITEU_MODELS_DIR"] = "~/.precommiteu/models"

result = scan_paths(["src/"], regulations=("gdpr",))
for finding in result.findings:
    print(finding.regulation, finding.file,
          finding.probable_article_id, finding.description)
```

Full API reference, every parameter, the result schemas and streaming
callbacks: **[Python library](https://alexandrugirlea.github.io/precommiteu/library.html)**.

## How it works

- **Your code never leaves your machine.** All analysis runs on local
  `llama-server` processes the scanner starts and stops itself. No cloud, no
  telemetry, no network egress.
- **No finding without proof.** A detector proposes candidates; a validator
  then has to locate the quoted evidence verbatim in your file, or the
  candidate is dropped. Confirmed findings cite the line. Candidates that fail
  validation are reported as advisories: clearly labeled, never gating. Only
  confirmed findings can fail a build.
- **Deterministic where it matters.** Grammar-constrained model output,
  fixed budgets per file, suppression rules with auditable reasons.

## Model bundle

precommitEU ships as two artifacts. The scanner is a pure-Python wheel on
PyPI; the weights are published separately on Hugging Face at
[AlexandruGirlea/precommiteu-models](https://huggingface.co/AlexandruGirlea/precommiteu-models)
(public, no token needed). `pip install` does **not** fetch them.

The repository holds seven files: one shared 4.36 GiB `base.gguf` used by every
regulation, plus a 77 MiB detector adapter per pack. **You choose which
adapters to download.** Name the files you want, or omit them to take
everything:

```bash
# base + GDPR only, about 4.5 GB
hf download AlexandruGirlea/precommiteu-models base.gguf gdpr/detector-adapter.gguf --local-dir ~/.precommiteu/models

# add another pack later, the base is already there
hf download AlexandruGirlea/precommiteu-models eu_ai_act/detector-adapter.gguf --local-dir ~/.precommiteu/models

# everything, about 4.9 GB
hf download AlexandruGirlea/precommiteu-models --local-dir ~/.precommiteu/models
```

`--regulations` then picks which of the downloaded packs to run. The two are
independent, and that is worth knowing: scanning with a regulation whose
adapter you never downloaded is **not** an error. The run continues on the base
model alone in degraded mode, logs a warning, and detects noticeably less. If a
scan seems weak, check the adapter is actually on disk.

Air-gapped installs, checksum verification and uninstall:
[Installation](https://alexandrugirlea.github.io/precommiteu/install.html).

## Regulation packs

Eight EU regulations, shipped as six adapter packs. `gdpr` is the default and
the sensible one for almost any product repo.

| `--regulations` value | Covers |
|---|---|
| `gdpr` *(default)* | General Data Protection Regulation |
| `eu_ai_act` | Artificial Intelligence Act |
| `eu_data_act` | Data Act |
| `dora` | Digital Operational Resilience Act |
| `dsa` | Digital Services Act |
| `cra_dma_nis2` | Cyber Resilience Act, Digital Markets Act and NIS2 |

```bash
precommiteu scan src/ --regulations gdpr,eu_ai_act
```

Each adapter is trained on code its own regulation governs, so scanning with
all six is noisier rather than more thorough. Application dates, what each pack
is for, and how several packs run in one scan are in
[Regulation packs](https://alexandrugirlea.github.io/precommiteu/regulations.html).

## Detection quality

precommitEU is not built to catch everything. The bar it aims for is: **flag
more than half of the real violations, and be right about nine out of ten
things it flags.**

From local evaluation runs on my own codebases, measured on confirmed findings
(advisories are excluded):

| Pack | Precision | Recall | False positive rate |
|---|---|---|---|
| `gdpr` | 97% | 98% | 6% |
| `eu_ai_act` | 97% | 93% | 5% |
| `eu_data_act` | 97% | 93% | 5% |
| `cra_dma_nis2` | 97% | 93% | 5% |
| `dsa` | 90% | 90% | 15% |
| `dora` | 100% | 73% | 0% |

Every pack clears both bars. `dora` is the most conservative and `dsa` the
noisiest, but nothing here is a compliance guarantee - treat a clean scan as
one useful signal, not as sign-off.

Numbers are for the shipped setup: shared base model plus the per-regulation
LoRA adapter, loaded at runtime, exactly as a normal scan runs them.

## In CI

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
- uses: AlexandruGirlea/precommiteu@v0.1.0
  with:
    regulations: gdpr,eu_ai_act
```

`--ci` scans only the files changed against the merge-target branch. Exit code
`1` on confirmed findings with `--fail-on-findings`, `0` when clean. GitLab,
Azure DevOps, the full input list and every exit code are in
[CI integration](https://alexandrugirlea.github.io/precommiteu/ci.html).

## Documentation

| Guide | Contents |
|---|---|
| [Installation](https://alexandrugirlea.github.io/precommiteu/install.html) | Requirements, per-platform install, model bundle download, CPU vs GPU, verify, uninstall |
| [CLI reference](https://alexandrugirlea.github.io/precommiteu/cli.html) | CLI usage, complete flag reference, reports, suppressions |
| [Regulation packs](https://alexandrugirlea.github.io/precommiteu/regulations.html) | The six packs, application dates, choosing packs, multi-regulation runs |
| [CI integration](https://alexandrugirlea.github.io/precommiteu/ci.html) | GitHub Actions, GitLab, exit codes, caching the model bundle |
| [Python library](https://alexandrugirlea.github.io/precommiteu/library.html) | Python API: `scan_paths`, `scan_diff`, schemas, callbacks |
| [Report reference](https://alexandrugirlea.github.io/precommiteu/reports.html) | Report formats: JSON field reference, SARIF, summary, ledger |
| [Ignoring and suppressing](https://alexandrugirlea.github.io/precommiteu/suppressions.html) | `.eu-ignore`, inline `eu-ignore` directives, audited `precommiteu-ignore` markers |
| [Examples](https://alexandrugirlea.github.io/precommiteu/examples.html) | Worked scans, real output, common flag combinations |
| [Troubleshooting](https://alexandrugirlea.github.io/precommiteu/troubleshooting.html) | Model paths, `llama-server` startup, empty scans, error messages |

Rendered documentation site: <https://alexandrugirlea.github.io/precommiteu/>
Project site: <https://precommit.eu>

## Disclaimer

precommitEU is free and fully open source under the Apache License 2.0, and is
provided **as is**, without warranty or condition of any kind, express or
implied, as set out in sections 7 and 8 of that license. Use is entirely at
your own risk. There is no service level, no availability commitment and no
guarantee of accuracy or fitness for any purpose.

It produces a compliance signal, not legal advice: it can report findings that
are not violations and can miss violations that are present. Nothing it
outputs establishes, certifies or evidences compliance with any regulation.

The author is not a lawyer and provides no legal, regulatory or compliance
advice. This software does not replace legal analysis. To the maximum extent
permitted by applicable law, Alexandru Girlea accepts no liability for any
damages, losses, costs, regulatory outcome or misrepresentation arising from
use of this software or reliance on its output. Have findings reviewed by
qualified legal counsel before acting on them.

## License

Apache License 2.0, see
[LICENSE](https://github.com/AlexandruGirlea/precommiteu/blob/main/LICENSE),
[NOTICE](https://github.com/AlexandruGirlea/precommiteu/blob/main/NOTICE) and
[THIRD_PARTY_NOTICES.md](https://github.com/AlexandruGirlea/precommiteu/blob/main/THIRD_PARTY_NOTICES.md).
Copyright (c) 2026 Alexandru Girlea.

Everything precommitEU produces is Apache-2.0: the scanner, the
per-regulation LoRA detector adapters, the GBNF grammars and the regulation
knowledge packs, including everything in the
[model bundle](https://huggingface.co/AlexandruGirlea/precommiteu-models).
The base model weights (Qwen 2.5 Coder, Apache-2.0) and the `llama-server`
binary (llama.cpp, MIT) are delivered separately and carry their own
licenses.
