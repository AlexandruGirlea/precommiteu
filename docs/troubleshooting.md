---
title: Troubleshooting
nav_order: 11
---

# Troubleshooting

Every symptom below is reproducible from the CLI. Errors are printed to
stderr and always come with a non-zero exit code. Progress lines are printed
to stderr too, in the form `[event] file key=value`.

| Symptom | Section |
|---|---|
| `error: no model paths configured` | [1](#1-no-model-paths-configured) |
| `error: required path not found` | [1](#1-no-model-paths-configured) |
| `llama-server` missing, or exits at startup | [2](#2-llama-server-not-found-or-exits-immediately) |
| `files_total=0`, nothing scanned | [3](#3-the-scan-finds-nothing-and-reports-files_total0) |
| Scan is slow, `budget_exhausted_time` | [4](#4-the-scan-is-slow-or-hits-the-per-file-wall-clock) |
| Out of memory, model fails to load | [5](#5-out-of-memory-or-the-model-fails-to-load) |
| Advisories but no confirmed findings | [6](#6-findings-look-wrong-or-only-advisories-appear) |
| `regulation ... not packaged`, `Unknown regulation` | [7](#7-unknown-regulation) |
| Too much noise from a scan | [8](#8-the-wrong-pack-for-the-codebase-produces-noise) |
| Unexpected exit code in CI | [9](#9-exit-codes) |
| Ctrl-C, partial reports | [10](#10-interrupted-scans-and-partial-reports) |

---

## 1. No model paths configured

### What you see

```
error: no model paths configured; pass --models-dir (or set PRECOMMITEU_MODELS_DIR) pointing at the directory holding the precommitEU model bundle (expected layout: base.gguf, <regulation>/detector-adapter.gguf), or pass explicit --orchestrator-model / --detector-adapter paths; see docs/install.md for how to get the bundle
```

Exit code 2. Or, when a directory was given but the base model is not there:

```
error: required path not found: /opt/precommiteu/models/base.gguf
```

### Why it happens

Models are not bundled with the wheel. `pip install precommiteu` ships pure
Python only. The scanner resolves the base model in this order:

1. `--orchestrator-model` (explicit file path, bypasses the layout)
2. `--models-dir <dir>` then `<dir>/base.gguf`
3. `$PRECOMMITEU_MODELS_DIR` then `$PRECOMMITEU_MODELS_DIR/base.gguf`

If none of those resolve to an existing file, the run stops before any model
is loaded. The detector adapter is resolved the same way, at
`<models-dir>/<regulation>/detector-adapter.gguf`.

### Expected directory layout

```
~/.precommiteu/models/
├── base.gguf                          # shared, Qwen2.5-Coder-7B-Instruct Q4_K_M, ~4.36 GiB
├── gdpr/detector-adapter.gguf         # ~77 MiB per regulation
├── eu_ai_act/detector-adapter.gguf
├── eu_data_act/detector-adapter.gguf
├── dora/detector-adapter.gguf
├── dsa/detector-adapter.gguf
└── cra_dma_nis2/detector-adapter.gguf
```

The subdirectory name must match the `--regulations` value character for
character.

### How to fix

```bash
pip install -U "huggingface_hub[cli]"
hf download AlexandruGirlea/precommiteu-models base.gguf gdpr/detector-adapter.gguf --local-dir ~/.precommiteu/models
export PRECOMMITEU_MODELS_DIR=~/.precommiteu/models
precommiteu scan src/
```

The repository is public. No account and no token are required. Verify what
landed on disk:

```bash
ls -lh ~/.precommiteu/models ~/.precommiteu/models/gdpr
```

### Missing adapter is not fatal

A missing base model is a hard error. A missing detector adapter is not: the
scan continues on the base model alone, in degraded mode, and the progress
stream says so.

```
[detector_adapter] regulation=gdpr adapter=base model (degraded)
```

If you passed `--detector-adapter` explicitly and the file is absent, you
also get a `::warning::precommiteu: detector adapter missing (...)` line.
Degraded mode produces noticeably weaker detection. Fix the bundle rather
than living with it.

One more configuration error worth knowing: a single explicit
`--detector-adapter` cannot be combined with several regulations. Omit the
flag and let each regulation resolve its own adapter.

---

## 2. llama-server not found, or exits immediately

### What you see

```
error: scan wiring failed: llama-server binary not found on PATH; install llama.cpp >= b4400
```

```
error: scan wiring failed: llama-server exited immediately: <the binary's stderr>
```

```
error: scan wiring failed: llama-server exited during startup
```

```
error: scan wiring failed: llama-server build b4102 is older than required b4400
```

```
error: scan wiring failed: llama-server at 127.0.0.1:53412 did not report healthy within 90s
```

All of these exit with code 2.

### Why it happens

The scanner does not link llama.cpp. It spawns `llama-server` as a
subprocess, on a free loopback port, and waits for `GET /health` to return
`{"status":"ok"}` within 90 seconds. It then runs `llama-server --version`
and refuses any build older than b4400.

Common causes, in order of frequency:

- llama.cpp is not installed, or is installed somewhere not on `PATH` for
  the shell or CI runner that launches the scan.
- The GGUF file is truncated or corrupt (an interrupted download). The
  process starts, fails to load the model, and exits during startup.
- The build is too old for the LoRA and grammar options the scanner passes.
- The machine is slow enough, or the model large enough relative to memory,
  that loading exceeds the 90 second health window.

### How to verify llama-server standalone

Take the scanner out of the picture entirely.

```bash
which llama-server && llama-server --version
```

Then load the base model by hand and query it:

```bash
llama-server -m ~/.precommiteu/models/base.gguf --host 127.0.0.1 --port 8080 --ctx-size 4096 --n-gpu-layers 0 --parallel 1 --jinja
```

In a second terminal:

```bash
curl -s http://127.0.0.1:8080/health
```

A healthy server answers `{"status":"ok"}`. Stop it with Ctrl-C. If this
fails, the problem is llama.cpp or the model file, not precommitEU. If it
succeeds, re-run the scan with the same `--n-ctx` and `--gpu-layers` values
you just proved working.

Also test the adapter, since a corrupt adapter fails the same way:

```bash
llama-server -m ~/.precommiteu/models/base.gguf --lora ~/.precommiteu/models/gdpr/detector-adapter.gguf --host 127.0.0.1 --port 8080 --ctx-size 4096 --n-gpu-layers 0
```

### Notes

- The port is chosen automatically on `127.0.0.1` and cannot be set by flag.
  If the port is taken the scanner retries with a new one, five times.
- macOS: `brew install llama.cpp`. Linux: use a release binary or build from
  source, then copy `build/bin/llama-server` onto `PATH`.
- In CI, install llama.cpp in the same step or image as the scan, and echo
  `llama-server --version` before scanning so the log records the build.

---

## 3. The scan finds nothing and reports `files_total=0`

This is the most common surprise. It is almost never a model problem.

### What you see

```
[scan_start] files_total=0
[scan_done] findings_total=0

No findings.
```

### Why it happens

File discovery filters aggressively before any model runs. Test and fixture
paths are skipped **by design**, and so are documentation paths. If you
point the scanner at a directory of deliberately non-compliant example files
under `tests/` or `fixtures/`, it correctly returns nothing.

| Category | Skipped when |
|---|---|
| Test paths | The path starts with or contains `test/`, `tests/`, `__tests__/`, `spec/`, `specs/`, `fixtures/`, `fixture/`, `__fixtures__/`, `testdata/`, `test_data/`, `e2e/` |
| Test basenames | The basename starts with `test_` or `tests_`, or its stem ends with `_test`, `_tests`, `_spec`, `.test`, `.tests`, `.spec` |
| Prose paths | The path starts with `docs/`, `documentation/`, `doc/` |
| Prose files | `README*`, `CHANGELOG*`, `CONTRIBUTING*`, `CODE_OF_CONDUCT*`, `LICENSE*`, `NOTICE*`, `AUTHORS*`, `MAINTAINERS*`, `SECURITY.md`, and any `.md`, `.rst`, `.txt`, `.adoc`, `.org`, `.tex`, `.log` |
| Dependency and build dirs | Any path component in `.git`, `.venv`, `venv`, `env`, `__pycache__`, `node_modules`, `vendor`, `dist`, `build`, `target`, `coverage`, `.next`, `.nuxt`, `.terraform`, `.gradle`, `.idea`, `.vscode`, `generated`, `__generated__`, and the various tool caches |
| Generated files | `*.min.js`, `*.bundle.js`, `*.generated.*`, `*.pb.go`, `*.pb.cc`, `*.pb.h`, `*.g.cs`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `poetry.lock` |
| Binaries | Binary extensions, or a NUL byte in the first 4 KB |
| Oversized files | Larger than `--max-file-bytes` (default 1000000) |
| Ignored paths | Matched by `.eu-ignore` in the directory the scan runs from |
| Unknown types | Not a recognised source extension, not a known code filename, and no `#!` shebang |

Two details that catch people out:

- The filter applies to explicitly named files too, not only to directory
  walks. `precommiteu scan tests/leaky.py` selects nothing.
- Test and prose prefixes are matched against the path **relative to the
  working directory**, so where you run the command from matters.

### Confirm it with `--dry-run`

`--dry-run` prints exactly the files a real scan would process, and loads no
model. It is instant.

```bash
precommiteu scan src/ --dry-run
```

Empty output means discovery selected nothing. Worked example on a tree
containing `src/app.py`, `src/test_leaky.py`, `tests/leaky.py` and
`docs/sample.py`:

```
$ precommiteu scan . --dry-run
src/app.py

$ precommiteu scan tests/leaky.py --dry-run
$
```

Three of the four files were filtered: one for its `tests/` prefix, one for
its `test_` basename, one for its `docs/` prefix.

### Workarounds

If you genuinely want to scan files that live under a test or fixture path,
pick one of these.

1. Copy them to a normal source path and scan that. Rename anything called
   `test_*.py` or `*_spec.ts` at the same time.

   ```bash
   mkdir -p /tmp/eu-scan && cp tests/fixtures/*.py /tmp/eu-scan/ && precommiteu scan /tmp/eu-scan --dry-run
   ```

2. Run the scan from inside the directory, so the `tests/` prefix is no
   longer part of the relative path. The basename rule still applies, so
   files named `test_*.py` stay skipped.

   ```bash
   cd tests/fixtures && precommiteu scan . --dry-run
   ```

3. Point the scan at real application code. This is the intended use, and
   the packs are trained on real code rather than on synthetic fixtures.

There is no flag that disables the test-path filter.

### Other causes of an empty selection

- A `.eu-ignore` file at the scan root excluding more than you meant.
  Negation lines (`!pattern`) are parsed and then silently skipped, so a
  broad `build/` rule cannot be re-enabled with `!build/keep.py`.
- A `# eu-ignore-file` directive in the file: it is read and the whole file
  is skipped, with a `file_ignored` progress event and no report entry.
- `--ci` when the diff against the merge target is empty. The status detail
  reads `no files changed vs merge target`.
- Everything filtered as oversized. Look for a `files_oversized` progress
  event, then raise or disable the cap with `--max-file-bytes 0`.

---

## 4. The scan is slow, or hits the per-file wall clock

### What you see

Long pauses between `file_start` and `file_done`, and lines like:

```
[orchestrator_done] src/billing.py regulation=gdpr kept_raw=0 exit_reason=budget_exhausted_time
[orchestrator_done] src/billing.py regulation=gdpr kept_raw=1 exit_reason=budget_exhausted_iters
```

### Why it happens

Inference is local. Throughput is set by your hardware and by the llama.cpp
build, not by the scanner. On top of that, each file carries hard budgets:
12 orchestrator iterations, 90 seconds of wall clock, and an 8000 token cap
on every message sent to the model.

Budget exhaustion is not an error. The file keeps whatever the validator
already confirmed and the scan moves on. It does not set the exit code and
does not mark the regulation as failed. It does mean findings may be
missing from that file.

The route matters. Each file takes one of two paths:

| Route | Behaviour | Cost |
|---|---|---|
| `direct` | Detector call, then validator call, over the file's chunks. No tools. | Low, predictable |
| `orchestrator` | ReAct loop with sandboxed read tools and cross-file context gathering. | Several times higher |

`--agent-mode auto` (the default) runs `direct` and escalates to
`orchestrator` only when the file mentions the filename stem of a sibling
file in the same directory. In a tightly cross-referencing directory almost
every file escalates, and the scan slows down accordingly.

### Levers

```bash
# GPU offload is the single biggest lever. 99 = all layers (default), 0 = CPU only.
precommiteu scan src/ --gpu-layers 99

# CPU-only host: pin threads to physical cores.
precommiteu scan src/ --gpu-layers 0 --threads 8

# Pin the fast route for every file.
precommiteu scan src/ --agent-mode direct

# Tighter budgets: fail fast instead of spending 90s per file.
precommiteu scan src/ --max-wall-seconds-per-file 45 --max-orchestrator-iterations 6

# More budget: let the orchestrator finish on a slow machine.
precommiteu scan src/ --max-wall-seconds-per-file 180 --max-orchestrator-iterations 20

# Smaller context window: less memory to allocate and manage.
precommiteu scan src/ --n-ctx 16384

# Scan only what changed.
GIT_MERGE_TARGET_BRANCH=main precommiteu scan --ci
```

| Flag | Default | Effect on speed |
|---|---|---|
| `--gpu-layers` | `99` | Full offload is fastest. `0` forces CPU and is substantially slower per file. |
| `--threads` | auto | Only relevant when layers run on CPU. Over-subscribing cores makes it slower, not faster. |
| `--n-ctx` | `32768` | Lower values reduce allocation and memory pressure. Do not go below 16384 (see section 5). |
| `--agent-mode` | `auto` | `direct` is the fast route. `orchestrator` is the slow one. |
| `--max-wall-seconds-per-file` | `90` | Hard cap per file. Lower it to bound total runtime, raise it on slow hardware. |
| `--max-orchestrator-iterations` | `12` | Cap on agent steps. Only affects the orchestrator route. |
| `--max-file-bytes` | `1000000` | Large files chunk into many model calls. |

### Other things worth checking

- Server startup is paid per regulation, not per file. Scanning two
  regulations starts a second detector server. Prefer one pack per run when
  you are timing things.
- The first file of a run is always slower: the model is still warming.
- Passing several `--regulations` runs a full pass over every file per
  regulation. Cost scales linearly with the number of packs.

---

## 5. Out of memory, or the model fails to load

### What you see

Any of: `llama-server exited immediately` with an allocation failure in the
quoted stderr, the health check timing out after 90 seconds, the OS killing
the process, or the machine swapping until the scan crawls.

### Why it happens

A normal scan runs two `llama-server` processes: one on the base model for
the orchestrator and validator, and one on the base model with the detector
adapter attached. Each holds its own context window - the running memory of
everything that server has read - sized by `--n-ctx`. The default 32768 token
window is generous for a 7B model on a small GPU.

### How to fix

```bash
# Halve the context window.
precommiteu scan src/ --n-ctx 16384

# Run entirely on CPU. Slower, but bounded by system RAM rather than GPU memory.
precommiteu scan src/ --gpu-layers 0

# Partial offload: put some layers on the GPU, keep the rest on CPU.
precommiteu scan src/ --gpu-layers 20 --n-ctx 16384
```

Do not set `--n-ctx` below 16384. A single request can carry an 8000 token
user message and ask for up to 8192 output tokens. A window smaller than
their sum truncates model output mid-answer, and the affected chunk is
treated as not analysed.

Other checks:

- The bundle is already quantised (Q4_K_M, about 4.36 GiB for the base).
  There is no smaller variant to switch to, and no separate CPU or GPU
  build. Acceleration comes entirely from the llama.cpp build you installed.
- Budget for **both** servers, not one. Measured peak is ~6.3 GiB each at the
  default `--n-ctx 32768`, so about 12.6 GiB combined; 16 GB of RAM is the
  practical minimum. The context window costs 56 KiB per token per server, so
  halving `--n-ctx` saves about 1.75 GiB across the pair. Full numbers are in
  [install.md](install.md#memory).
- On an 8 GB machine the defaults will swap or be killed. Use
  `--n-ctx 16384 --gpu-layers 0` and close other applications.
- After the system kills a scan to reclaim memory, the servers can outlive the
  scanner. Check with
  `pgrep -fl precommiteu-llama-server` and `pkill -f precommiteu-llama-server`
  if any survived.
- Verify by hand with the standalone `llama-server` command from section 2,
  using the same `--ctx-size` and `--n-gpu-layers`. If it will not load
  there, it will not load under the scanner.

---

## 6. Findings look wrong, or only advisories appear

### What you see

```
No findings.
```

with `--show-advisories` producing:

```
Advisories (unconfirmed, non-blocking): 2
  [gdpr] src/export.py: Bulk export of user records without consent check
```

Or a `--json-out` whose `statuses` show a high `validator_rejected` count.

### Why it happens

precommitEU separates confirmed findings from advisories, and only findings
can fail a build.

- A **finding** passed validation: it cites an article known to the pack and
  quotes code evidence that is actually present in the analysed text.
- An **advisory** is an unconfirmed detector candidate. Advisories never
  affect the exit code, and they are emitted only for files that produced no
  confirmed finding.

The evidence rule is the reason candidates get dropped. If the validator's
quoted evidence cannot be located in the file, the finding is discarded with
the reason `evidence_not_visible`. That rule is what keeps false positives
out. Other drop reasons are `article_unparseable`,
`article_not_in_registry`, `description_missing` and `evidence_missing`.

### How to inspect

```bash
precommiteu scan src/ --show-advisories --json-out result.json
```

Per-regulation counters live in `statuses` inside `--json-out`:

| Counter | Meaning |
|---|---|
| `chunks_scanned` | Chunks sent to the detector |
| `detector_candidates` | Raw candidates the detector produced |
| `validator_rejected` | Validated candidates dropped before becoming findings |

A high `validator_rejected` with zero findings means the model kept
proposing violations it could not back with visible code. A high
`detector_candidates` with zero validator activity points at a run that hit
its budget instead (see section 4, and check `exit_reason`).

To see each drop decision:

```bash
PRECOMMITEU_DEBUG_VALIDATOR=1 precommiteu scan src/ --show-advisories
```

This writes `precommiteu_validator_debug.jsonl` in the working directory, one JSON
record per validated candidate, including `outcome`, `reason`,
`article_raw`, `article_id` and the evidence prefix. Set the variable to a
path to write elsewhere. Set it to `0` or leave it unset to disable.

For a quick stderr view of drops only:

```bash
PRECOMMITEU_DEBUG_RAW=1 precommiteu scan src/
```

```
[precommiteu:debug] validator gdpr src/export.py: DROP reason='evidence_not_visible' ...
```

### When a finding you expect is simply absent

Check for suppressions before blaming the model.

1. **Inline redaction directives** blank the code before the model sees it,
   preserving line numbers, and leave no trace in any report:
   `eu-ignore` (this line), `eu-ignore-next-line`,
   `eu-ignore-next-lines: N` (`:` or `=`), `eu-ignore-start` /
   `eu-ignore-end`, and `eu-ignore-file` (the whole file is skipped, with a
   `file_ignored` progress event). Grep for them:

   ```bash
   grep -rn "eu-ignore" src/
   ```

2. **Audited markers** suppress a confirmed finding rather than hiding the
   code: `precommiteu-ignore: <article-rule> reason="<text>"`, matched
   against a finding citing that article within 2 lines of the marker. The
   `reason` is mandatory, and a bare wildcard rule (`*`) is rejected with a
   warning. Suppressed findings disappear from console output and from the
   `--fail-on-findings` check, but they stay in `--json-out` with
   `eu_ignore_reason` and `eu_ignore_source: "inline"`, and in SARIF under
   `properties.eu_ignored`. So:

   ```bash
   grep -c '"eu_ignore_reason": null' result.json
   ```

   or simply read `result.json`, which is the full record including
   suppressed entries.

3. **`.eu-ignore`** excludes whole paths from the scan. Confirm with
   `--dry-run` (section 3).

### Findings with no code evidence

A finding whose `source` is `"retrieval"` was promoted from an advisory by
matching a known violation pattern from the pack's case index. It has no
`code_evidence` and its description ends with the matched article and a
similarity score. These are legitimate findings, but they are pattern
matches rather than quoted-evidence confirmations.

---

## 7. Unknown regulation

### What you see

```
error: regulation 'nis2' not packaged in precommiteu.regulations
```

Exit code 2. From the library API, a bad regulation or article prefix raises:

```
Unknown regulation 'gdrp'. Supported: ...
```

### The six pack names

`--regulations` accepts these values, and nothing else. They are also the
adapter subdirectory names in the model bundle.

| Pack name | Covers |
|---|---|
| `gdpr` | General Data Protection Regulation (default) |
| `eu_ai_act` | EU AI Act |
| `eu_data_act` | EU Data Act |
| `dora` | Digital Operational Resilience Act |
| `dsa` | Digital Services Act |
| `cra_dma_nis2` | Cyber Resilience Act, Digital Markets Act, NIS2 |

Use them exactly as written: lowercase, underscores, no spaces.

```bash
precommiteu scan src/ --regulations gdpr
precommiteu scan src/ --regulations gdpr,dora
precommiteu scan src/ --regulations cra_dma_nis2
```

Common mistakes: `nis2`, `cra`, `dma`, `ai_act` and `eu-ai-act` are not pack
names. CRA, DMA and NIS2 ship together as `cra_dma_nis2`. Hyphens are not
accepted where the pack name uses underscores.

If the pack name is valid but the scan runs in degraded mode, the adapter
directory under `--models-dir` is missing or misspelled. See section 1.

---

## 8. The wrong pack for the codebase produces noise

### What you see

A long list of advisories, or findings that cite articles which do not
apply to what the code does.

### Why it happens

Each pack is a separately trained LoRA adapter plus its own article
registry, detector prompt and validator prompt. A pack looks for the
violations of its own regulation and cites only that regulation's article
ids. Running the GDPR pack over infrastructure code that never touches
personal data asks a personal-data detector to judge something outside its
training. The result is candidates that the validator cannot confirm, which
surface as advisories.

### How to fix

Match the pack to the code.

| Code under scan | Start with |
|---|---|
| Anything handling personal data, user records, consent, retention | `gdpr` |
| Model training, inference, automated decision systems | `eu_ai_act` |
| Data sharing, access and portability between parties | `eu_data_act` |
| Financial services resilience, ICT risk, incident reporting | `dora` |
| Content moderation, notice-and-action, recommender systems | `dsa` |
| Product security, gatekeeper obligations, network and information security | `cra_dma_nis2` |

Scan the relevant subtree rather than the whole repository, and add packs
one at a time:

```bash
precommiteu scan src/api src/models --regulations gdpr
precommiteu scan src/ml --regulations eu_ai_act
```

Every extra pack is a full extra pass over every file, so cost scales
linearly with the number of packs. Advisories are informational and never
gate a build, so noise in the advisory stream is not a reason to fail CI.
Use `--fail-on-findings`, which only reacts to confirmed findings.

---

## 9. Exit codes

```bash
precommiteu scan src/ --fail-on-findings
echo $?
```

| Code | Meaning | Typical CI reading |
|---|---|---|
| `0` | Scan completed. No visible findings, or findings present without `--fail-on-findings`. Also returned by `--dry-run` and by bare `precommiteu` (help). | Pass |
| `1` | `--fail-on-findings` was set and at least one confirmed finding remains after suppression filtering. Advisories and suppressed findings never trigger it. | Compliance failure, block the merge |
| `2` | Usage or configuration error: unknown regulation, no model paths configured, a required file missing, an output target that already exists, `--ci` combined with positional paths, neither paths nor `--ci` given, or a git error in CI mode. | Broken job configuration, not a code problem |
| `3` | Scan incomplete: at least one file could not be analysed, and `--fail-on-error` was in effect. Always on under `--ci`. | Infrastructure problem, re-run before trusting a pass |
| `130` | Interrupted (Ctrl-C or SIGINT). Partial reports are preserved. | Cancelled job |

Notes for CI:

- Exit 3 exists so that an incomplete scan never reports a clean pass.
  `--ci` enables `--fail-on-error` automatically. Before it fires, stderr
  carries a `warning: scan incomplete` line naming the regulation and the
  reason, and the affected regulation's `status` in `--json-out` is
  `failed`.
- Distinguish 1 from 2 and 3 in your pipeline. Only 1 is a compliance
  result. 2 means the job is misconfigured. 3 means the scan did not finish.
- `--ci` derives its file list from
  `git diff $GIT_MERGE_TARGET_BRANCH...HEAD`. It reads no platform-specific
  variables, so wire yours through explicitly:

  ```bash
  GIT_MERGE_TARGET_BRANCH=${GITHUB_BASE_REF:-main} precommiteu scan --ci --fail-on-findings
  ```

- A shallow clone is the usual cause of `cannot resolve merge target` in
  CI. Fetch the target branch before scanning.

---

## 10. Interrupted scans and partial reports

### What you see

```
precommiteu: scan interrupted; partial results written to result.json, findings.sarif
```

Exit code 130. Or, when a regulation was interrupted part way, a status
detail reading `interrupted after 7 of 42 files`.

### What is guaranteed

`--json-out`, `--sarif` and `--out` are snapshot files. Each is rewritten to
a `.precommiteu_tmp_<pid>` sibling and then moved into place with an atomic
rename, after
every finding and after every `file_done` or `file_error` event. The file on
disk is therefore always a complete, parseable document, never a half-written
one. Interrupting a scan does not lose the results collected so far.

`--report` is different: it is an append-only JSONL ledger, flushed and
fsynced line by line, so it survives an interrupt by construction and never
overwrites a previous run.

One caveat when reading an interrupted `--json-out`: `statuses` is populated
only by the final write. In a snapshot from an interrupted run it is an
empty list. Findings and advisories are present as normal.

### Cleaning up

The scanner terminates its `llama-server` children on SIGINT, on SIGTERM and
via an exit hook, killing the whole process group. A stray server therefore
means the scanner itself was killed with SIGKILL. Check and clean up:

```bash
pgrep -fl llama-server
pkill -f llama-server
```

A leftover `result.json.precommiteu_tmp_<pid>` next to a report file is
harmless and can be deleted. The pid suffix means the scanner never writes
over a file of your own that happens to end in `.tmp`.

---

## 11. Collecting diagnostics

### Scan log

Every run appends a timestamped log to `precommiteu_scan.log` in the working
directory by default. It records the resolved model paths, every progress
event, warnings and errors.

```bash
precommiteu scan src/ --log-file /tmp/precommiteu_scan.log
```

### Machine-readable progress

```bash
precommiteu scan src/ --progress jsonl 2> progress.jsonl
```

One JSON object per line on stderr: `scan_start`, `detector_adapter`,
`file_start`, `orchestrator_done` (with `route`, `detector_called`,
`validator_called`, `exit_reason`), `finding`, `file_done`, `file_error`,
`files_oversized`, `file_ignored`, `scan_interrupted`, `scan_done`. Use
`--progress none` to silence it.

### Event ledger

```bash
precommiteu scan src/ --report scan-events.jsonl
```

The chronological audit trail of the run, including a full record per
finding.

### Debug environment variables

| Variable | Effect |
|---|---|
| `PRECOMMITEU_DEBUG_VALIDATOR` | `1` writes `precommiteu_validator_debug.jsonl` in the working directory, one record per validated candidate with its keep or drop reason. Any other non-empty value is used as the output path. `0` or unset disables it. |
| `PRECOMMITEU_DEBUG_RAW` | Prints one `[precommiteu:debug] validator ... DROP reason=...` line to stderr per dropped candidate. |
| `PRECOMMITEU_DEBUG_ENRICH` | Prints `PRECOMMITEU_DEBUG_ENRICH {...}` JSON to stderr with message and token sizes for each validator call and enrichment step. |
| `PRECOMMITEU_MODELS_DIR` | Model bundle directory, used when `--models-dir` is absent. |
| `GIT_MERGE_TARGET_BRANCH` | Merge target for `--ci` (default `main`). |

All debug output stays on the machine. Nothing is uploaded, at any verbosity.

---

## Collecting information for a bug report

Open issues at
<https://github.com/AlexandruGirlea/precommiteu/issues>. Include the
following, which is usually enough to reproduce a problem without access to
your code.

Environment:

```bash
precommiteu --version && llama-server --version && python3 --version && uname -sm
```

Model bundle listing:

```bash
ls -lR "$PRECOMMITEU_MODELS_DIR"
```

The exact command you ran, unedited, including every flag.

File selection, which rules out discovery problems:

```bash
precommiteu scan <your paths> --dry-run
```

A reproduction run with full instrumentation:

```bash
PRECOMMITEU_DEBUG_VALIDATOR=1 precommiteu scan <your paths> --progress jsonl --report scan-events.jsonl --json-out result.json --log-file scan.log 2> progress.jsonl
echo "exit=$?"
```

Attach `progress.jsonl`, `scan-events.jsonl`, `scan.log` and, if relevant,
`precommiteu_validator_debug.jsonl`. State the exit code and what you expected instead.

For a crash or a startup failure, add the standalone `llama-server` check
from section 2 and its output. That separates a llama.cpp or model problem
from a scanner problem immediately.

One caution before attaching anything: `--report`, `--json-out`, `--out`,
`--sarif` and the validator debug file contain code snippets from the files
you scanned, because the evidence is quoted code. Review and redact them, or
reproduce the problem on a small file you are happy to share publicly.
