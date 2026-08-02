---
title: Installation
nav_order: 2
---

# Installation

precommitEU installs as three separate pieces.

| Piece | What it is | Where it comes from |
|---|---|---|
| `llama-server` | The local inference server binary from llama.cpp | Homebrew, a release archive, or a source build |
| `precommiteu` | The scanner, a pure-Python wheel | `pip install precommiteu` |
| Model bundle | One shared base GGUF plus one LoRA adapter per regulation | Hugging Face, downloaded once |

The wheel does not contain the models. The models do not contain the runtime.
All three stay on your machine: the scanner starts and stops `llama-server`
processes itself and talks to them over `127.0.0.1` only. Nothing is uploaded,
and nothing is fetched at scan time.

## Requirements

| Requirement | Detail                                                                                                                |
|---|-----------------------------------------------------------------------------------------------------------------------|
| Python | 3.11 or newer (3.11, 3.12 and 3.13 are declared supported)                                                            |
| `llama-server` | From [llama.cpp](https://github.com/ggml-org/llama.cpp), on `PATH`, build number 4400 or higher                       |
| Disk | About 4.5 GB for one regulation, about 4.9 GB for all six                                                             |
| RAM | 16 GB recommended. A default scan peaks near 13 GB across two servers - read [Memory](#memory) before running on 8 GB |
| CPU architecture | x86_64 and ARM64 (Apple Silicon, Graviton)                                                                            |
| Operating system | macOS and Linux. On Windows, use WSL2 and follow the Linux steps                                                      |
| Network | Needed for the three install steps only, never for a scan                                                             |

`llama-server` is the only external dependency. The scanner's single Python
dependency is `pydantic>=2`, installed automatically by pip. No
`llama-cpp-python`, no compiler and no CUDA toolkit are needed to install the
package.

## Memory

A scan runs **two** `llama-server` processes at once: one on the base model for
the orchestrator and validator, one on the base model with the detector adapter
attached. Each loads the full 4.36 GiB base model, and each keeps its own
context window - the running memory of everything that server has read so far,
sized by `--n-ctx`.

That window costs **56 KiB per token, per server**, so it is the part of the
footprint you can actually control:

| `--n-ctx` | Window per server | Peak per server | Both servers | Run it on |
|---|---|---|---|---|
| 32768 (default) | 1.75 GiB | ~6.3 GiB | **~12.6 GiB** | 16 GB or more |
| 16384 | 0.88 GiB | ~5.4 GiB | ~10.8 GiB | 16 GB |
| 8192 | 0.44 GiB | ~4.9 GiB | ~9.8 GiB | 16 GB, or 8 GB with nothing else running |

Figures are measured resident size on Apple Silicon with full Metal offload.
Both processes memory-map the same base model file, so where those pages are
shared the true physical cost is roughly 4 GiB below the combined figure. Plan
for the combined number anyway: it is what `top` and Activity Monitor report,
and it is what the operating system reacts to when it starts killing processes
to reclaim memory.

**On an 8 GB machine the default settings will swap or be killed.** Use
`--n-ctx 16384 --gpu-layers 0`, expect a slow scan, and close other
applications. Do not set `--n-ctx` below 16384 - a single request can carry an
8000 token message and ask for up to 8192 output tokens, and a smaller window
truncates model output mid-answer, marking that chunk as not analysed.

On a GPU the same context window is held in the card's own memory for offloaded
layers, so a card with less than 8 GB should lower `--n-ctx` or offload
partially with `--gpu-layers 20`.

The scanner stops both servers on exit, including on Ctrl-C. They appear in
`ps` as `precommiteu-llama-server`; if a scan is killed with `SIGKILL` or by the
operating system reclaiming memory, check for survivors with
`pgrep -fl precommiteu-llama-server`.

x86_64 and ARM64 use the same artifacts: the wheel is pure Python
(`py3-none-any`, no compiled extensions) and GGUF files are
architecture-independent. Hardware acceleration is decided entirely by the
llama.cpp build you install.

## Step 1: install llama.cpp

### macOS (Apple Silicon or Intel)

```bash
brew install llama.cpp
```

Metal acceleration is included in the Homebrew build on Apple Silicon.

### Linux, prebuilt binary

Download the archive that matches your platform and backend from the
[llama.cpp releases page](https://github.com/ggml-org/llama.cpp/releases),
unpack it, then put the `llama-server` binary it contains on your `PATH`:

```bash
sudo install -m 0755 ./llama-server /usr/local/bin/llama-server
```

### Linux, build from source (CPU)

```bash
git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp && cmake -B build && cmake --build build --config Release -j && sudo install -m 0755 build/bin/llama-server /usr/local/bin/llama-server
```

### Linux, build from source (NVIDIA CUDA)

Requires the CUDA toolkit:

```bash
git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp && cmake -B build -DGGML_CUDA=ON && cmake --build build --config Release -j && sudo install -m 0755 build/bin/llama-server /usr/local/bin/llama-server
```

### Check the binary

```bash
llama-server --version
```

The output looks like `version: 9570 (3ac3c20c9)`. precommitEU parses that
number and requires **4400 or higher** (llama.cpp tags releases as `b4400`,
`b4401` and so on). The check runs once the first server has started and
reported healthy, so an outdated binary fails a few seconds into a scan rather
than at argument parsing.

Failures at this stage produce one of:

```
llama-server binary not found on PATH; install llama.cpp >= b4400
llama-server build b<N> is older than required b4400
```

## Step 2: install the scanner

```bash
pip install precommiteu
```

A virtual environment is recommended:

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install precommiteu
```

This provides the `precommiteu` command and the importable package
(`from precommiteu import scan_paths, scan_diff`).

## Step 3: download the model bundle

Models are not shipped with pip. They are published on Hugging Face at
[AlexandruGirlea/precommiteu-models](https://huggingface.co/AlexandruGirlea/precommiteu-models).
The repository is public: no account, no token, no `hf auth login`.

### One base, one adapter per regulation

There is a single shared `base.gguf` (Qwen2.5-Coder-7B-Instruct, Q4_K_M,
4.36 GiB). It serves every role: orchestrator, validator, and the detector
when no adapter is loaded. Each regulation adds one small LoRA adapter
(77 MiB) that is swapped onto the detector server for that regulation's pass.

| `--regulations` value | Regulation | Adapter file |
|---|---|---|
| `gdpr` (default) | General Data Protection Regulation | `gdpr/detector-adapter.gguf` |
| `eu_ai_act` | EU AI Act | `eu_ai_act/detector-adapter.gguf` |
| `eu_data_act` | EU Data Act | `eu_data_act/detector-adapter.gguf` |
| `dora` | Digital Operational Resilience Act | `dora/detector-adapter.gguf` |
| `dsa` | Digital Services Act | `dsa/detector-adapter.gguf` |
| `cra_dma_nis2` | Cyber Resilience Act, DMA and NIS2 in one adapter | `cra_dma_nis2/detector-adapter.gguf` |

Adding a regulation later means one extra 77 MiB file, never another base
model.

### Download only the packs you need

```bash
pip install -U "huggingface_hub[cli]"
```

Base plus GDPR only (about 4.5 GB):

```bash
hf download AlexandruGirlea/precommiteu-models base.gguf gdpr/detector-adapter.gguf --local-dir ~/.precommiteu/models
```

The whole bundle, all six adapters (about 4.9 GB):

```bash
hf download AlexandruGirlea/precommiteu-models --local-dir ~/.precommiteu/models
```

Add a regulation later by re-running with its adapter path. Files already
present are not downloaded again:

```bash
hf download AlexandruGirlea/precommiteu-models eu_ai_act/detector-adapter.gguf --local-dir ~/.precommiteu/models
```

Notes on this step:

- `--local-dir` writes real files into that directory instead of the
  symlinked Hub cache, so the result is directly usable as
  `PRECOMMITEU_MODELS_DIR`.
- `--dry-run` previews what a command would fetch, and its total size, without
  downloading.
- Older `huggingface_hub` installs expose the same command as
  `huggingface-cli download`.
- Unauthenticated downloads print a rate-limit warning suggesting `HF_TOKEN`.
  That is expected on a public repository and safe to ignore. A token only
  raises the rate limit.

Without the Hugging Face client, plain HTTP works too:

```bash
mkdir -p ~/.precommiteu/models/gdpr && curl -L -o ~/.precommiteu/models/base.gguf https://huggingface.co/AlexandruGirlea/precommiteu-models/resolve/main/base.gguf && curl -L -o ~/.precommiteu/models/gdpr/detector-adapter.gguf https://huggingface.co/AlexandruGirlea/precommiteu-models/resolve/main/gdpr/detector-adapter.gguf
```

### The layout the scanner expects

```
~/.precommiteu/models/
├── base.gguf                       # shared base model, 4.36 GiB
├── gdpr/detector-adapter.gguf      # one 77 MiB adapter per regulation
├── eu_ai_act/detector-adapter.gguf
├── eu_data_act/detector-adapter.gguf
├── dora/detector-adapter.gguf
├── dsa/detector-adapter.gguf
├── cra_dma_nis2/detector-adapter.gguf
├── SHA256SUMS
├── LICENSE.Apache-2.0.txt
└── NOTICE
```

Two rules, and that is the whole contract:

1. The base model is `<models-dir>/base.gguf`.
2. An adapter is `<models-dir>/<regulation>/detector-adapter.gguf`, where
   `<regulation>` is exactly the `--regulations` value.

Directory names are the pack names, so a typo in a directory name shows up as
a missing adapter, not as an error. Recent `huggingface_hub` versions also
create a `.cache/huggingface/` metadata folder inside the local directory. It
is harmless; the scanner never looks at it.

### Disk space

| Contents | Size |
|---|---|
| `base.gguf` | 4.36 GiB |
| One adapter | 77 MiB |
| Base plus one regulation | about 4.5 GB |
| Base plus all six regulations | about 4.9 GB |

Leave some headroom on top for the download metadata folder. The base file is
the whole cost: six regulations are only about 0.4 GB more than one.

### Verify the download

`SHA256SUMS` covers all seven model files, the shared base plus the six adapters:

```bash
cd ~/.precommiteu/models && shasum -a 256 -c SHA256SUMS
```

If you downloaded a subset, the files you skipped are reported as missing.
Every line for a file you did download must say `OK`.

### Air-gapped and offline installation

The bundle is plain files, so it copies like any other directory.

1. On a connected machine, download with `--local-dir` as above, then verify
   with `SHA256SUMS`.
2. Copy the directory to the target machine (`rsync`, USB, artefact store).
   Keep the subdirectory structure intact.
3. Copy the `llama-server` binary across as well, or install llama.cpp from
   your distribution's offline packages.
4. Get the wheel across with pip:

```bash
pip download precommiteu -d ./wheels
```

then, on the target machine:

```bash
pip install --no-index --find-links ./wheels precommiteu
```

Run `pip download` on a machine with the same OS and Python version as the
target. The `precommiteu` wheel itself is pure Python, but its `pydantic`
dependency ships platform-specific compiled wheels.

After that the machine never needs the network again. The scanner does not
contact Hugging Face, or anything else, at scan time. The only sockets it
opens are local `llama-server` ports on `127.0.0.1`.

## Step 4: point the scanner at the bundle

Persistently:

```bash
export PRECOMMITEU_MODELS_DIR=~/.precommiteu/models
```

Or per invocation, which overrides the environment variable:

```bash
precommiteu scan src/ --models-dir ~/.precommiteu/models
```

| Setting | Scope | Precedence |
|---|---|---|
| `--models-dir` | One invocation | Highest |
| `$PRECOMMITEU_MODELS_DIR` | Shell or CI environment | Used when the flag is absent |
| `--orchestrator-model` | Explicit path to the base GGUF | Bypasses both; adapters then resolve next to that file |
| `--detector-adapter` | Explicit path to one adapter GGUF | Bypasses adapter resolution entirely |

Details worth knowing:

- `~` is expanded in both the flag and the environment variable.
- `--orchestrator-model /opt/m/base.gguf` makes adapters resolve from
  `/opt/m/<regulation>/detector-adapter.gguf`, that is, from the directory
  holding the base file.
- `--detector-adapter` pins one adapter, so it is valid with a single
  regulation only. Combining it with several is a usage error (exit 2).
- With no models directory, no environment variable and no explicit base path,
  the scan exits 2 with
  `error: no model paths configured;` followed by a hint describing this
  layout.
- A configured but missing base model exits 2 with
  `error: required path not found: <path>`.
- A missing adapter is **not** fatal. The regulation still runs in degraded
  mode with the detector on the untrained base weights. The progress line
  reads `adapter=base model (degraded)` and the scan log records a warning. If
  you passed `--detector-adapter` explicitly and the file is absent, stderr
  also gets
  `::warning::precommiteu: detector adapter missing (<path>); running without a LoRA-bound detector (degraded mode).`

## Verify the installation

### 1. The command exists

```bash
precommiteu --version
```

Prints `precommiteu 0.1.0`.

### 2. File discovery works

```bash
precommiteu scan src/ --dry-run
```

Lists the files that would be scanned, one per line, and exits without loading
any model. This is the fast check of path selection and `.eu-ignore` rules.

**If this prints nothing, discovery skipped everything, and that is usually
deliberate.** File discovery ignores test and fixture paths (`tests/`, `test/`,
`spec/`, `specs/`, `fixtures/`, `testdata/`, `e2e/` and basenames such as
`*_test.py` or `*.spec.ts`) and prose paths (`docs/`, `README`, `CHANGELOG`
and similar). Pointing precommitEU at a directory of sample files is the
common first-run surprise: the scan reports `files_total=0` and finds nothing.
Copy the sample into a normal source path to try it.

### 3. `llama-server` can load the base model

Optional, but it isolates runtime problems from scanner problems. In one
terminal:

```bash
llama-server -m ~/.precommiteu/models/base.gguf --ctx-size 4096 --port 8081
```

In another:

```bash
curl -s http://127.0.0.1:8081/health
```

`{"status":"ok"}` is what the scanner itself waits for. Stop the server with
Ctrl-C afterwards. If it exits instead of serving, the model file is truncated
or corrupt; re-download and re-check `SHA256SUMS`.

### 4. A real scan

```bash
precommiteu scan src/
```

Progress goes to stderr, results to stdout:

```
[scan_start] files_total=3
[detector_adapter] regulation=gdpr adapter=gdpr/detector-adapter.gguf
[file_done] src/user_store.py regulation=gdpr kept=1
[scan_done] findings_total=1

Findings: 1
  [gdpr] src/user_store.py:42 gdpr_art32
      ...
```

A clean run ends with `No findings.` instead. The `detector_adapter` line is
the one to read on a first install: it confirms which adapter was resolved,
and shows `base model (degraded)` when none was found.

A timestamped log is appended to `precommiteu_scan.log` in the working
directory. Change the path with `--log-file`.

### 5. The exit code

```bash
precommiteu scan src/ --fail-on-findings ; echo "exit=$?"
```

| Code | Meaning |
|---|---|
| `0` | Clean |
| `1` | Confirmed findings remain (only with `--fail-on-findings`) |
| `2` | Usage or configuration error |
| `3` | Scan incomplete, one or more files could not be analysed (with `--fail-on-error`, always on under `--ci`) |
| `130` | Interrupted, partial results still written |

Only confirmed findings can fail a build. A confirmed finding has to quote
verbatim code that is actually present in the file: if the evidence cannot be
located, the finding is dropped. Unconfirmed candidates are reported as
advisories (`--show-advisories`) and never affect the exit code.

## CPU vs GPU

```bash
precommiteu scan src/                  # default: --gpu-layers 99, full offload
precommiteu scan src/ --gpu-layers 0   # CPU only
```

`--gpu-layers` is the number of model layers offloaded to the GPU and is
passed straight through to `llama-server`. The default of `99` means all
layers. If your llama.cpp build has no GPU backend, there is nothing to
offload and the flag has no effect, so the default is safe everywhere.

There is no separate CPU or GPU package: one wheel, one model bundle. The
llama.cpp build you installed decides the acceleration.

What to expect, qualitatively:

- GPU offload is the fast path. Metal on Apple Silicon and CUDA on NVIDIA both
  work with the matching llama.cpp build and no extra configuration.
- CPU-only mode produces the same findings and is substantially slower per
  file. It is a fine choice for CI runners with no GPU, given a large enough
  per-file budget.
- A scan runs **two** `llama-server` processes: one on the base model, shared
  by the orchestrator and validator, and one on the same base file with the
  regulation's LoRA adapter for detection. The detector process is restarted
  per regulation, so scanning several packs never exceeds two at once.
  llama.cpp memory-maps the weights and precommitEU does not disable that, so
  the two processes share the mapped file rather than reading it twice. Plan
  for more headroom than a single copy of the weights all the same,
  especially in GPU memory, where each process holds its own copy of the
  offloaded layers.
- Do not judge speed from the first run. The initial model load from a cold
  page cache dominates it.

Each file gets a hard budget: 12 orchestrator iterations and 90 seconds of
wall-clock time, with an 8000-token cap on every message sent to a model. On
slow hardware the time budget can end context gathering early, so a file may
be judged with less cross-file context. That is not counted as an error and
findings already collected are kept. Raise `--max-wall-seconds-per-file` if
you see it happening.

Flags that affect cost and speed:

| Flag | Default | Purpose |
|---|---|---|
| `--gpu-layers` | `99` | Layers offloaded to the GPU (`0` = CPU only) |
| `--threads` | auto | CPU threads for inference |
| `--n-ctx` | `32768` | Model context window in tokens |
| `--max-wall-seconds-per-file` | `90` | Wall-clock budget per file |
| `--max-orchestrator-iterations` | `12` | Maximum agent steps per file |
| `--max-file-bytes` | `1000000` | Skip files larger than this (`0` = no limit) |
| `--agent-mode` | `auto` | Per-file route, see below |

`--agent-mode direct` is the cheapest route: the detector proposes candidates
and the validator confirms them, two model calls per chunk, no tools.
`--agent-mode orchestrator` runs the full ReAct loop with sandboxed read tools
for cross-file context. The default `auto` picks the orchestrator only when
the file mentions the name of a sibling file in the same directory, and uses
the direct route otherwise.

## Troubleshooting

| Message | Meaning | Fix |
|---|---|---|
| `error: no model paths configured; ...` | Neither `--models-dir`, `$PRECOMMITEU_MODELS_DIR` nor `--orchestrator-model` was set | Step 4 |
| `error: required path not found: <path>` | The base model or a grammar file is not where you said it is | Check the path and the bundle layout |
| `error: scan wiring failed: <exc>` | Startup failed, most often the `llama-server` runtime | Read the wrapped message, then Step 1 |
| `llama-server binary not found on PATH; install llama.cpp >= b4400` | The binary is not installed or not on `PATH` | Step 1 |
| `llama-server build b<N> is older than required b4400` | The build is too old | Upgrade llama.cpp |
| `llama-server exited immediately: <stderr>` | The server died before serving | Read the captured stderr, usually a bad or unsupported model file |
| `llama-server exited during startup ...` | The model file may be corrupt or incompatible | Re-download and re-check `SHA256SUMS` |
| `error: regulation '<value>' not packaged in precommiteu.regulations` | A `--regulations` value is misspelled | Use one of the six pack names |
| `warning: scan incomplete` | At least one regulation ended with failed files | Results may be missing findings; treat as a red build under `--ci` |
| `precommiteu: scan interrupted` | Ctrl-C, exit 130 | Partial reports have already been written |

Two more things people hit on day one:

- A scan of a fixture or test directory reports `files_total=0`. See
  [step 2 of the verification](#2-file-discovery-works).
- Findings you expect are missing because a suppression is in force. Check for
  a `.eu-ignore` file at the scan root, inline `eu-ignore` directives (which
  blank code before the model sees it and leave no trace in any report), and
  audited `precommiteu-ignore: <article-rule> reason="..."` markers, whose
  findings are hidden from the console but stay in `--json-out` and SARIF. See
  [suppressions.md](suppressions.md).

## Uninstall

```bash
pip uninstall precommiteu
rm -rf ~/.precommiteu/models
rm -f precommiteu_scan.log precommiteu_validator_debug.jsonl
```

Then remove the runtime, only if nothing else uses it:

```bash
brew uninstall llama.cpp
```

or, for a Linux source build or a prebuilt binary:

```bash
sudo rm /usr/local/bin/llama-server
```

Finally, remove the `PRECOMMITEU_MODELS_DIR` export from your shell profile or
CI configuration, and delete `~/.cache/huggingface` if you downloaded the
bundle without `--local-dir`.

Nothing else is left behind. The scanner writes only the paths you pass
explicitly (`--json-out`, `--sarif`, `--out`, `--report`) plus the scan log at
`--log-file`, which defaults to `precommiteu_scan.log` in the working
directory.

## Next steps

| Guide | Contents |
|---|---|
| [cli.md](cli.md) | CLI usage, complete flag reference, reports, suppressions |
| [ci.md](ci.md) | GitHub Actions, GitLab, exit codes, caching the model bundle |
| [library.md](library.md) | Python API: `scan_paths`, `scan_diff`, schemas, callbacks |
| [reports.md](reports.md) | Report formats: JSON field reference, SARIF, summary, ledger |
| [suppressions.md](suppressions.md) | `.eu-ignore`, inline directives, audited ignore markers |
