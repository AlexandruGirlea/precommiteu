---
title: CI integration
nav_order: 8
---

# CI integration

`precommiteu scan --ci` scans only the files changed on the current branch
against a merge-target branch. It reads exactly one environment variable,
`GIT_MERGE_TARGET_BRANCH`, and nothing else from the CI platform.

```bash
GIT_MERGE_TARGET_BRANCH="${GITHUB_BASE_REF:-main}" precommiteu scan --ci --fail-on-findings
```

## What `--ci` scans

```bash
git diff --name-only --diff-filter=AM "<merge-target>...HEAD"
```

- Merge target comes from `GIT_MERGE_TARGET_BRANCH` (default `main`), resolved
  as the local ref first, then `origin/<branch>`. Neither present → exit 2.
- Three-dot diff, so commits landed on the target after you branched are not
  scanned. Added and modified files only; deletions are ignored.
- The usual file filter still applies: code files only, tests skipped, files
  over `--max-file-bytes` skipped.
- No changed files → exit 0 without loading a model.
- `--ci` and positional paths together is an error.

Wire your platform's variable through `GIT_MERGE_TARGET_BRANCH`:

| Platform | Value |
|---|---|
| GitHub Actions | `${{ github.base_ref }}` (empty on push; fall back to `main`) |
| GitLab CI | `$CI_MERGE_REQUEST_TARGET_BRANCH_NAME` |
| Azure DevOps | `${SYSTEM_PULLREQUEST_TARGETBRANCH#refs/heads/}` |
| Jenkins | `${CHANGE_TARGET:-main}` |

## GitHub Actions: the action

```yaml
name: compliance-scan

on: pull_request

permissions:
  contents: read
  security-events: write

jobs:
  precommiteu:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: AlexandruGirlea/precommiteu@v0.1.0
        with:
          regulations: gdpr,eu_ai_act
      - uses: github/codeql-action/upload-sarif@v3
        if: ${{ !cancelled() }}
        with:
          sarif_file: precommiteu.sarif
```

The action installs `llama-server` and the scanner, caches and downloads the
model bundle, and scans the changed files.

| Input | Default | Notes |
|---|---|---|
| `regulations` | `gdpr` | Comma-separated packs |
| `paths` | *(empty)* | Scan these paths instead of the branch diff |
| `fail-on-findings` | `true` | Fail the job on confirmed findings |
| `sarif` | `precommiteu.sarif` | SARIF output path |
| `summary` | `precommiteu-summary.md` | Markdown summary path |
| `version` | *(latest)* | Pin the scanner version |
| `models-revision` | `main` | Pin the model bundle revision |

Pin both for reproducible runs:

```yaml
- uses: AlexandruGirlea/precommiteu@v0.1.0
  with:
    version: 0.1.0
    models-revision: v1.0.0
```

`fetch-depth: 0` is still worth setting: the action un-shallows the clone
itself, but doing it in `checkout` is faster.

## GitHub Actions: without the action

```yaml
name: compliance-scan

on: pull_request

permissions:
  contents: read
  security-events: write        # for the SARIF upload

jobs:
  precommiteu:
    runs-on: ubuntu-latest
    env:
      LLAMA_BUILD: b10158       # b4400 or newer
      PRECOMMITEU_MODELS_DIR: ${{ github.workspace }}/.precommiteu-models
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0        # required: shallow clones have no merge base

      - name: Install llama-server
        run: |
          curl -fsSL -o /tmp/llama.tar.gz \
            "https://github.com/ggml-org/llama.cpp/releases/download/${LLAMA_BUILD}/llama-${LLAMA_BUILD}-bin-ubuntu-x64.tar.gz"
          mkdir -p "$HOME/llama" && tar -xzf /tmp/llama.tar.gz -C "$HOME/llama"
          dirname "$(find "$HOME/llama" -name llama-server -type f | head -1)" >> "$GITHUB_PATH"

      - run: pip install precommiteu

      - name: Cache the model bundle
        id: models
        uses: actions/cache@v4
        with:
          path: ${{ env.PRECOMMITEU_MODELS_DIR }}
          key: precommiteu-models-gdpr-v1

      - name: Download the model bundle
        if: steps.models.outputs.cache-hit != 'true'
        run: |
          pip install -U "huggingface_hub[cli]"
          hf download AlexandruGirlea/precommiteu-models \
            base.gguf gdpr/detector-adapter.gguf \
            --local-dir "$PRECOMMITEU_MODELS_DIR"

      - name: Scan changed files
        env:
          GIT_MERGE_TARGET_BRANCH: ${{ github.base_ref || 'main' }}
        run: |
          precommiteu scan --ci \
            --fail-on-findings \
            --sarif precommiteu.sarif \
            --out pr-summary.md \
            --force

      - name: Upload SARIF
        if: ${{ !cancelled() }}   # the scan exits 1 on findings; upload anyway
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: precommiteu.sarif
          category: precommiteu
```

Cache the bundle or every run re-downloads 4.4 GB. The cache key is yours to
bump when you change regulations or update the models.

## GitLab CI

```yaml
precommiteu:
  stage: test
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  variables:
    GIT_DEPTH: "0"
    PRECOMMITEU_MODELS_DIR: "$CI_PROJECT_DIR/.precommiteu-models"
  cache:
    key: precommiteu-models-gdpr-v1
    paths: [.precommiteu-models/]
  script:
    - git fetch origin "+refs/heads/$CI_MERGE_REQUEST_TARGET_BRANCH_NAME:refs/remotes/origin/$CI_MERGE_REQUEST_TARGET_BRANCH_NAME"
    - export GIT_MERGE_TARGET_BRANCH="$CI_MERGE_REQUEST_TARGET_BRANCH_NAME"
    - precommiteu scan --ci --fail-on-findings --sarif precommiteu.sarif --out mr-summary.md --force
  artifacts:
    when: always
    paths: [mr-summary.md, precommiteu_scan.log]
    reports:
      sast: precommiteu.sarif
```

## Azure DevOps

```yaml
trigger: none
pr:
  branches: { include: ['*'] }

pool: { vmImage: ubuntu-latest }

variables:
  PRECOMMITEU_MODELS_DIR: $(Pipeline.Workspace)/.precommiteu-models
  LLAMA_BUILD: b10158

steps:
  - checkout: self
    fetchDepth: 0          # required: shallow clones have no merge base

  - task: Cache@2
    inputs:
      key: 'precommiteu-models-gdpr-v1'
      path: $(PRECOMMITEU_MODELS_DIR)
      cacheHitVar: MODELS_CACHED

  - script: |
      curl -fsSL -o /tmp/llama.tar.gz "https://github.com/ggml-org/llama.cpp/releases/download/$(LLAMA_BUILD)/llama-$(LLAMA_BUILD)-bin-ubuntu-x64.tar.gz"
      mkdir -p "$HOME/llama" && tar -xzf /tmp/llama.tar.gz -C "$HOME/llama"
      echo "##vso[task.prependpath]$(dirname $(find $HOME/llama -name llama-server -type f | head -1))"
      pip install precommiteu "huggingface_hub[cli]"
    displayName: Install llama-server and precommiteu

  - script: hf download AlexandruGirlea/precommiteu-models base.gguf gdpr/detector-adapter.gguf --local-dir "$(PRECOMMITEU_MODELS_DIR)"
    condition: ne(variables.MODELS_CACHED, 'true')
    displayName: Download the model bundle

  - script: |
      export GIT_MERGE_TARGET_BRANCH="${SYSTEM_PULLREQUEST_TARGETBRANCH#refs/heads/}"
      git fetch --quiet origin "+refs/heads/$GIT_MERGE_TARGET_BRANCH:refs/remotes/origin/$GIT_MERGE_TARGET_BRANCH" || true
      precommiteu scan --ci --fail-on-findings --sarif precommiteu.sarif --out pr-summary.md --force
    displayName: Scan changed files

  - publish: precommiteu.sarif
    artifact: precommiteu-sarif
    condition: always()
```

`SYSTEM_PULLREQUEST_TARGETBRANCH` arrives as `refs/heads/main`. Strip the
prefix: the scanner resolves `<branch>` then `origin/<branch>`, and neither
matches a full ref path.

## Any other CI

One variable is all it takes:

```bash
GIT_MERGE_TARGET_BRANCH="${CHANGE_TARGET:-main}" \
    precommiteu scan --ci --fail-on-findings --sarif precommiteu.sarif --force
```

The agent needs a non-shallow checkout where the target branch resolves,
`llama-server` on `PATH`, and `PRECOMMITEU_MODELS_DIR` pointing at the bundle.

## Reports

| Flag | Use |
|---|---|
| `--sarif <file>` | GitHub code scanning / GitLab SAST |
| `--out <file>` | Markdown summary to post as a PR comment |
| `--json-out <file>` | Full result for downstream tooling |
| `--report <file>` | JSONL event ledger, for an audit trail |

All are written incrementally, so partial results survive a cancelled job.

precommitEU refuses to overwrite an existing file: if the target of any of
these flags is already on disk, the scan exits 2 without loading a model.
This fires on a self-hosted or cached runner that kept the previous run's
output, and on a repo that has committed a file of the same name. Pass
`--force` to rewrite the target anyway - the bundled
`AlexandruGirlea/precommiteu` action already does. See
[cli.md](cli.md#never-overwriting-your-files) for the full rules.

## Exit codes

`0` clean · `1` confirmed findings · `2` usage/config error · `3` a file could
not be scanned · `130` interrupted. Full detail in [cli.md](cli.md).

Advisories never affect the exit code. Only confirmed, evidence-backed
findings can fail a build.

## CPU or GPU

One wheel, one bundle. The llama.cpp build you install decides which you get.

```bash
precommiteu scan src/                  # default: --gpu-layers 99, full offload
precommiteu scan src/ --gpu-layers 0   # CPU only
```

Hosted runners (GitHub, GitLab SaaS, Azure DevOps) have **no GPU**, so the
default full-offload setting simply falls back to CPU, with nothing to configure.
On a self-hosted runner with an NVIDIA card, install a CUDA build of
`llama-server` and the default offloads automatically. See
[install.md](install.md) for the build commands.

## Runtime cost

Scans run on CPU on hosted runners, and the model is 7B. Budget roughly a
minute per changed file. That is fine on a pull request touching a handful of
files; for large PRs or a whole-repo scan, use a scheduled job, a self-hosted
GPU runner, or a bigger machine rather than blocking every push.

## Debugging scope

```bash
GIT_MERGE_TARGET_BRANCH=main precommiteu scan --ci --dry-run
```

Prints the files the scan would cover and exits. No model needed. Compare
with `git diff --name-only --diff-filter=AM "origin/main...HEAD"` to see what
the file filter removed.
