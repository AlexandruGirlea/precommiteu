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
| `precommiteu[ui]` | Optional, adds the local web UI | `pip install "precommiteu[ui]"` |
| Model bundle | An orchestrator GGUF, a detector base GGUF and one LoRA adapter per regulation | Hugging Face, downloaded once |

The wheel does not contain the models. The models do not contain the runtime.
All three stay on your machine: the scanner starts and stops `llama-server`
processes itself and talks to them over `127.0.0.1` only. Nothing is uploaded,
and nothing is fetched at scan time.

## Requirements

| Requirement | Detail                                                                                                                |
|---|-----------------------------------------------------------------------------------------------------------------------|
| Python | 3.11 or newer (3.11, 3.12 and 3.13 are declared supported)                                                            |
| `llama-server` | From [llama.cpp](https://github.com/ggml-org/llama.cpp), on `PATH`, build number 10158 or higher |
| Disk | About 22.5 GB for one regulation, about 22.9 GB for all six |
| RAM | 32 GB. A default scan peaks near 24 GiB across two servers - read [Memory](#memory) |
| CPU architecture | x86_64 and ARM64 (Apple Silicon, Graviton)                                                                            |
| Operating system | macOS and Linux. On Windows, use WSL2 and follow the Linux steps                                                      |
| Network | Needed for the three install steps only, never for a scan                                                             |

`llama-server` is the only external dependency. The scanner's single Python
dependency is `pydantic>=2`, installed automatically by pip. No
`llama-cpp-python`, no compiler and no CUDA toolkit are needed to install the
package.

## Memory

A scan runs **two** `llama-server` processes at once: one on `orchestrator.gguf`
(16.5 GiB) for the orchestrator and validator, and one on `base.gguf` (4.36 GiB)
with the detector adapter attached. Each keeps its own context window - the
running memory of everything that server has read so far, sized by `--n-ctx`.

That window costs about **20 KiB per token on the orchestrator server and
56 KiB per token on the detector server**. The model weights dominate the
footprint:

| `--n-ctx` | Orchestrator peak | Detector peak | Both servers | Run it on |
|---|---|---|---|---|
| 32768 (default) | ~17.5 GiB | ~6.3 GiB | **~23.7 GiB** | 32 GB or more |
| 16384 | ~17.1 GiB | ~5.4 GiB | ~22.6 GiB | 32 GB |

Figures are measured resident size on Apple Silicon with full Metal offload.
The two servers load different model files, so no pages are shared between
them. Plan for the combined number: it is what `top` and Activity Monitor
report, and it is what the operating system reacts to when it starts killing
processes to reclaim memory.

**On a machine with less than 32 GB the scan will swap or be killed.** Lowering
`--n-ctx` saves little. Do not set `--n-ctx` below 16384 - a single request can
carry an 8000 token message and ask for up to 8192 output tokens, and a smaller
window truncates model output mid-answer, marking that chunk as not analysed.

On a GPU both models need about 24 GB of the card's memory for full offload. On
a smaller card offload partially with `--gpu-layers 20` and expect a slower
scan.

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

The output looks like `version: 10450 (ece963f41)`. precommitEU parses that
number and requires **10158 or higher** (llama.cpp tags releases as `b10158`,
`b10159` and so on). The check runs once the first server has started and
reported healthy, so an outdated binary fails a few seconds into a scan rather
than at argument parsing.

Failures at this stage produce one of:

```
llama-server binary not found on PATH; install llama.cpp >= b10158
llama-server build b<N> is older than required b10158
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

The deployment combination is scanner/action/image **0.3.2**, model bundle
**v0.3.0**, and Azure ops **0.2.0**. Model and scanner versions are independent.
The model tag resolves to `fe15487df95233aac4478f9a08e2fc12e8dda7f1`;
use that commit in place of `v0.3.0` when an immutable revision is required.

Models are not shipped with pip. They are published on Hugging Face at
[AlexandruGirlea/precommiteu-models](https://huggingface.co/AlexandruGirlea/precommiteu-models).
The repository is public: no account, no token, no `hf auth login`.

### Two shared models, one adapter per regulation

`orchestrator.gguf` (Qwen3.6-35B-A3B, IQ4_XS, 16.5 GiB) runs the orchestrator
and the validator. `base.gguf` (Qwen2.5-Coder-7B-Instruct, Q4_K_M, 4.36 GiB) runs
the detector. Each regulation adds one small LoRA adapter (77 MiB) that is
loaded onto the detector server for that regulation's pass.

| `--regulations` value | Regulation | Adapter file |
|---|---|---|
| `gdpr` (default) | General Data Protection Regulation | `gdpr/detector-adapter.gguf` |
| `eu_ai_act` | EU AI Act | `eu_ai_act/detector-adapter.gguf` |
| `eu_data_act` | EU Data Act | `eu_data_act/detector-adapter.gguf` |
| `dora` | Digital Operational Resilience Act | `dora/detector-adapter.gguf` |
| `dsa` | Digital Services Act | `dsa/detector-adapter.gguf` |
| `cra_dma_nis2` | Cyber Resilience Act, DMA and NIS2 in one adapter | `cra_dma_nis2/detector-adapter.gguf` |

Adding a regulation later means one extra 77 MiB file, never another shared
model.

### Download only the packs you need

```bash
pip install -U huggingface_hub
```

The shared models plus GDPR only (about 22.5 GB):

```bash
hf download AlexandruGirlea/precommiteu-models base.gguf orchestrator.gguf gdpr/detector-adapter.gguf SHA256SUMS LICENSE.Apache-2.0.txt NOTICE --revision v0.3.0 --local-dir ~/.precommiteu/models
```

The whole bundle, all six adapters (about 22.9 GB):

```bash
hf download AlexandruGirlea/precommiteu-models --revision v0.3.0 --local-dir ~/.precommiteu/models
```

Add a regulation later by re-running with its adapter path. Files already
present are not downloaded again:

```bash
hf download AlexandruGirlea/precommiteu-models eu_ai_act/detector-adapter.gguf --revision v0.3.0 --local-dir ~/.precommiteu/models
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
mkdir -p ~/.precommiteu/models/gdpr && curl -fL -o ~/.precommiteu/models/base.gguf https://huggingface.co/AlexandruGirlea/precommiteu-models/resolve/v0.3.0/base.gguf && curl -fL -o ~/.precommiteu/models/orchestrator.gguf https://huggingface.co/AlexandruGirlea/precommiteu-models/resolve/v0.3.0/orchestrator.gguf && curl -fL -o ~/.precommiteu/models/gdpr/detector-adapter.gguf https://huggingface.co/AlexandruGirlea/precommiteu-models/resolve/v0.3.0/gdpr/detector-adapter.gguf
```

With HTTP downloads, also fetch `SHA256SUMS`, `LICENSE.Apache-2.0.txt` and
`NOTICE` from that same revision into the model directory.

### The layout the scanner expects

```
~/.precommiteu/models/
├── orchestrator.gguf               # orchestrator and validator, 16.5 GiB
├── base.gguf                       # detector base model, 4.36 GiB
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

Three rules, and that is the whole contract:

1. The orchestrator model is `<models-dir>/orchestrator.gguf`.
2. The detector base model is `<models-dir>/base.gguf`.
3. An adapter is `<models-dir>/<regulation>/detector-adapter.gguf`, where
   `<regulation>` is exactly the `--regulations` value.

Directory names are the pack names, so a typo in a directory name shows up as
a missing-adapter error. Recent `huggingface_hub` versions also
create a `.cache/huggingface/` metadata folder inside the local directory. It
is harmless; the scanner never looks at it.

### Disk space

| Contents | Size |
|---|---|
| `orchestrator.gguf` | 16.5 GiB |
| `base.gguf` | 4.36 GiB |
| One adapter | 77 MiB |
| Shared models plus one regulation | about 22.5 GB |
| Shared models plus all six regulations | about 22.9 GB |

Leave some headroom on top for the download metadata folder. The two shared
models are almost the whole cost: six regulations are only about 0.4 GB more
than one.

### Verify the download

`SHA256SUMS` covers all eight model files: both shared models and six adapters.
For a complete bundle:

```bash
cd ~/.precommiteu/models && shasum -a 256 -c SHA256SUMS
```

For the GDPR-only download, select exactly its three manifest entries so
missing unselected adapters do not hide an actual verification failure:

```bash
cd ~/.precommiteu/models && awk '$2 == "base.gguf" || $2 == "orchestrator.gguf" || $2 == "gdpr/detector-adapter.gguf"' SHA256SUMS | shasum -a 256 -c -
```

All three entries must report `OK`. Include the corresponding manifest entry
for every additional adapter you download.

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
pip download precommiteu==0.3.2 -d ./wheels
```

then, on the target machine:

```bash
pip install --no-index --find-links ./wheels precommiteu==0.3.2
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

Details worth knowing:

- `~` is expanded in both the flag and the environment variable.
- The bundle fixes model roles: `orchestrator.gguf` for orchestration and
  validation; `base.gguf` plus the selected adapter for detection.
- With no models directory and no environment variable,
  the scan exits 2 with
  `error: no model paths configured;` followed by a hint describing this
  layout.
- A missing `orchestrator.gguf`, `base.gguf` or selected adapter exits 2 with
  `error: required path not found: <path>`.
- Every selected adapter is required. There is no unadapted or alternate-model
  detection mode.

## Verify the installation

### 1. The command exists

```bash
precommiteu --version
```

Prints `precommiteu 0.3.2`.

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
the one to read on a first install: it confirms which adapter was loaded.

A timestamped log is appended to `precommiteu_scan.log` in the working
directory. Change the path with `--log-file`.

Run the same command again and the files that did not change are reused rather
than analysed:

```
Reused 3 unchanged file(s) for gdpr from /home/you/.precommiteu/scans/gdpr-4f1c9ab2e7d05631.json
```

That record is why a repository which took hours the first time takes minutes
afterwards. It is one small JSON file per scanned folder and regulation under
`~/.precommiteu/scans/`; nothing is written into the folder you scanned.
`--rescan-all` forces a full pass, for example after upgrading the model
bundle. See [Incremental rescans](cli.md#incremental-rescans).

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
- A scan runs **two** `llama-server` processes: one on `orchestrator.gguf` for
  orchestration and validation, and one on `base.gguf` with the regulation's
  LoRA adapter for detection. The detector process is restarted per regulation,
  so scanning several packs never exceeds two at once. The processes load
  separate model files; allow memory for both models and their runtime buffers.
- Do not judge speed from the first run. The initial model load from a cold
  page cache dominates it.

Each file gets a hard budget: 12 orchestrator iterations and 300 seconds of
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
| `--max-wall-seconds-per-file` | `300` | Wall-clock budget per file |
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
| `error: no model paths configured; ...` | Neither `--models-dir` nor `$PRECOMMITEU_MODELS_DIR` was set | Step 4 |
| `error: required path not found: <path>` | A shared model, selected adapter or grammar file is missing | Check the path and the bundle layout |
| `error: scan wiring failed: <exc>` | Startup failed, most often the `llama-server` runtime | Read the wrapped message, then Step 1 |
| `llama-server binary not found on PATH; install llama.cpp >= b10158` | The binary is not installed or not on `PATH` | Step 1 |
| `llama-server build b<N> is older than required b10158` | The build is too old | Upgrade llama.cpp |
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
rm -rf ~/.precommiteu ~/.precommiteu-ui
rm -f precommiteu_scan.log precommiteu_validator_debug.jsonl
```

`~/.precommiteu` holds the model bundle and the scan records; `~/.precommiteu-ui`
is the local UI's own state and its reports, and exists only if you ran
`precommiteu ui`.

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

Nothing else is left behind. Outside those two directories the scanner writes
only the paths you pass explicitly (`--json-out`, `--sarif`, `--out`,
`--report`) plus the scan log at `--log-file`, which defaults to
`precommiteu_scan.log` in the working directory. It never writes into the
folder it scans.

## Next steps

| Guide | Contents |
|---|---|
| [cli.md](cli.md) | CLI usage, complete flag reference, reports, suppressions |
| [ci.md](ci.md) | The CI container, GitHub Actions, GitLab, Azure DevOps, exit codes |
| [library.md](library.md) | Python API: `scan_paths`, `scan_diff`, schemas, callbacks |
| [reports.md](reports.md) | Report formats: JSON field reference, SARIF, summary, ledger |
| [suppressions.md](suppressions.md) | `.eu-ignore`, inline directives, audited ignore markers |
