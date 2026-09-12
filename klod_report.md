# precommitEU · KLOD report

- **Project:** precommitEU 0.2.1 (pyproject.toml:10-12)
- **Git origin:** ssh://github.com/AlexandruGirlea/precommiteu.git
- **Revision:** 26baea4ad37721a9a7888e4d26bf43cb167956b9
- **Model:** claude-fable-5-1 (source: Claude Code host system prompt)
- **Report timestamp:** 2026-09-12T14:00:42+03:00 (Europe/Bucharest)

**Result: PASS.** No dependence on an external AI provider. 0 dependent capabilities. Coverage: complete.

## Summary

- Classification: product, a command-line scanner with a GitHub Action and a local web UI (pyproject.toml:67; action.yml:1-9; src/precommiteu/ui/server.py:17-18).
- No business work depends on a hosted model. Compliance scanning runs on language models the operator holds, served by `llama-server` processes the scanner starts on the loopback address (src/precommiteu/llama_server.py:156-186; src/precommiteu/model_factory.py:51-67).
- No gap against the numbered clauses. One human-control gap: the documentation never says what a team does when the scanner cannot run (see Human control).
- First action: add one paragraph to docs/ci.md stating that a failed or skipped scan means a person reviews the change against the regulation summaries, and that exit 3 must block the merge. Owner: maintainer.
- Assessed against specification 0.1.0.

## AI inventory

| AI use | Where | Workflow | Type | Counts toward a level |
|---|---|---|---|---|
| Base model on a local llama-server, used by the validator and the orchestrator | src/precommiteu/scan.py:713-727; src/precommiteu/model_factory.py:118-135 | Compliance scanning | Self-run | No |
| Per-regulation LoRA detector adapter on a second local llama-server | src/precommiteu/scan.py:751-764; src/precommiteu/llama_server.py:175-176 | Compliance scanning | Self-run | No |
| Model bundle downloaded once from Hugging Face, then verified by checksum | src/precommiteu/ui/install.py:15-29, 66-78; action.yml:90-101 | Installation, before any scan | Installation-time | No |
| llama.cpp release binary downloaded by the GitHub Action | action.yml:61-70 | Installation in CI | Installation-time | No |
| OpenAI client inside the demo codebase written for the scanner to find | example-local-ui/demo_ai_act_violations/api/candidate_chat.py:6-10 | None, a scan target | Sample | No |

No development-time AI in CI (.github/workflows/ci.yml, release.yml). No hosted model API, gateway or provider SDK on any runtime path.

## Capabilities

| Capability | Supplier | Declared | Supported | Blocking gap |
|---|---|---|---|---|
| None | No hosted AI supplier; models run locally from held weights | None | No level applies | None |

Portability: not applicable. For information, model access goes through one adapter class (src/precommiteu/model_factory.py:30-49) to an OpenAI-compatible loopback endpoint (src/precommiteu/llama_server.py:299), and model files are chosen by configuration (src/precommiteu/defaults.py:22-35).

## Findings

No findings against the numbered clauses.

### Human control (principle 6)

| Control | Status | Evidence | Next action |
|---|---|---|---|
| AI-off switch that works without the supplier, with the mode visible | In place | Every run is a deliberate invocation; `--dry-run` lists files without loading a model (src/precommiteu/cli.py:238-243); a missing model stops the run before any scan (src/precommiteu/defaults.py:8-14; docs/troubleshooting.md:87-93); a missing adapter continues in a labelled degraded mode (src/precommiteu/scan.py:738-748) | None |
| Mode enforced where actions are accepted, kept across restarts | In place | The models only read and report: tools are confined to sandbox roots (src/precommiteu/src/tools/sandbox.py:19-30) and the grep worker is read-only with a timeout (src/precommiteu/src/tools/read_tools.py:264-283); findings act only through an exit code the operator selects (src/precommiteu/cli.py:513-517) | None |
| Late results and queued AI actions rejected after switch-off | In place | A stopped scan exits 130 with partial results (src/precommiteu/cli.py:509-511); the ledger records only files analysed end to end, so unfinished files are scanned again (src/precommiteu/scan.py:90-99); servers are terminated when the scan ends (src/precommiteu/llama_server.py:121-138) and stale ones are killed by the UI (src/precommiteu/ui/runner.py:33-44) | None |
| Manual work usable: inputs, status, permissions, controls | Gap | The scanner fails closed: an unanalysed file is reported and, under `--ci`, exits 3 so an incomplete scan never reads as a clean pass (src/precommiteu/cli.py:224-227, 498-514). The regulation knowledge a reviewer needs is in readable files (src/precommiteu/regulations/gdpr/regulations_summary.md:1-8 and five more packs). No page tells a team to review by hand when the scanner cannot run | Add the paragraph named in the summary to docs/ci.md |
| Restart needs a recorded human decision | In place | Each scan is started by a person or a CI job; a finding can be accepted only with a recorded reason that stays in the report (docs/suppressions.md:11-18; docs/reports.md:45) | None |

Installation-time note: a fresh install needs Hugging Face for the model bundle and, in the Action, GitHub releases for the llama.cpp binary. An installed copy works without any network service (SECURITY.md:17-19; docs/install.md:270); the Action caches the bundle (action.yml:83-88).

## Coverage

| Area | Status | Note |
|---|---|---|
| src/precommiteu/ (7,725 lines) | Inspected | Self-run detector, validator and orchestrator models |
| src/precommiteu/regulations/ | Inspected | Prompts and readable regulation summaries; no model calls |
| src/precommiteu/ui/ | Inspected | Bundle download, preflight checks, local scan runner |
| tests/ (1,199 lines) | Inspected | Fallback, output guard and ledger tests; read, not run |
| action.yml, .github/workflows/ | Inspected | Installation-time downloads; no development-time AI |
| docs/, README.md, SECURITY.md, CHANGELOG.md | Inspected | Exit codes, suppressions, air-gapped install |
| example-local-ui/ | Inspected | Sample code with a hosted AI client, by design |
| pyproject.toml, uv.lock | Inspected | No AI SDK dependencies; `huggingface_hub` optional for the UI |
| dist/, .venv/, tool caches | Excluded | Built artefacts of earlier versions and local environments |

## Evidence to obtain

- None. A recorded CI run of the three failure modes (missing model, missing engine, interrupted scan) would turn inspected tests into observed behaviour.

## Scope and limits

- Repository review, not a drill. No service was interrupted and no provider was called.
- Tests were read, not run. Model weights, the Hugging Face bundle and the deployed behaviour of the Action were not inspected.
- Working tree clean.
- Previous scan: none (first scan).
