---
title: CI integration
nav_order: 9
---

# CI integration

Scan the files each pull request changes and fail the build on confirmed
findings. Set up one machine once, then add one job to your CI.

## Where it runs

A scan needs 32 GB of RAM and about 23 GB of disk for the models. Standard
hosted runners such as GitHub `ubuntu-latest` are too small. GitHub Actions
works with a self-hosted runner; use a GPU for practical PR scan times.

## Azure GPU runners with Terraform or Pulumi

[precommitEU ops](https://github.com/AlexandruGirlea/precommiteu-ops) provisions
an ephemeral GitHub Actions runner on an Azure Container Apps T4 GPU, plus a
shared model volume. Follow the
[ops deployment guide](https://alexandrugirlea.github.io/precommiteu-ops/deployment.html)
for prerequisites and setup, then connect its CI workflow. Ops 0.2.0 uses
scanner/action 0.3.2 and model bundle v0.3.0. The runner already contains the
scanner and CUDA runtime:
use its workflow directly, without the CPU `container:` block below.

The Azure deployment needs GitHub and registry connectivity; it makes no
calls to an external LLM provider. A truly disconnected installation uses
the [offline installation steps](install.md#air-gapped-and-offline-installation).

## An existing runner

Alternatively, run the precommitEU container on a Linux machine of your own:

- 32 GB of RAM and 30 GB of free disk
- x86_64 or ARM64, with Docker installed
- registered as a runner (or agent) for your CI

## Set up the machine

Download the models once, on that machine:

```bash
docker run --rm -v /opt/precommiteu/models:/models ghcr.io/alexandrugirlea/precommiteu:0.3.2 hf download AlexandruGirlea/precommiteu-models base.gguf orchestrator.gguf gdpr/detector-adapter.gguf SHA256SUMS LICENSE.Apache-2.0.txt NOTICE --revision v0.3.0 --local-dir /models
```

Add one `<pack>/detector-adapter.gguf` per pack you scan, for example
`eu_ai_act/detector-adapter.gguf`. Jobs mount `/opt/precommiteu/models`
read-only at `/models`, where the image looks for the models.

The image `ghcr.io/alexandrugirlea/precommiteu` holds `llama-server`, the
scanner and git, tagged by release. It uses CPU inference; a machine with
enough RAM can still exceed the five-minute per-file budget. Use ops or a
native GPU runtime for the measured T4 performance.

## GitHub Actions

Register the machine as a self-hosted runner with the label `precommiteu`
(Settings → Actions → Runners → New self-hosted runner) and add the runner's
user to the `docker` group. Use it for private repositories only: on a public
repository, pull requests from forks would run on your machine.

```yaml
name: compliance-scan

on: pull_request

permissions:
  contents: read
  security-events: write

jobs:
  precommiteu:
    runs-on: [self-hosted, precommiteu]
    container:
      image: ghcr.io/alexandrugirlea/precommiteu:0.3.2
      volumes:
        - /opt/precommiteu/models:/models:ro
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: AlexandruGirlea/precommiteu@v0.3.2
        with:
          regulations: gdpr
      - uses: actions/upload-artifact@v4
        if: ${{ !cancelled() }}
        with:
          name: precommiteu-reports
          path: |
            precommiteu.sarif
            precommiteu-summary.md
      - uses: github/codeql-action/upload-sarif@v3
        if: ${{ !cancelled() && hashFiles('precommiteu.sarif') != '' }}
        with:
          sarif_file: precommiteu.sarif
```

The action scans with what the container provides. It installs and downloads
nothing.

SARIF upload to GitHub code scanning requires that feature to be enabled and
licensed for a private repository. Otherwise omit `upload-sarif` and the
`security-events` permission; the artifact download and failing check still
work. Mark the scan job as required in branch protection or a ruleset to
block merges on findings or incomplete scans.

| Input | Default | Notes |
|---|---|---|
| `regulations` | `gdpr` | Comma-separated packs, each with its adapter on the machine |
| `paths` | *(empty)* | Scan these paths instead of the branch diff |
| `fail-on-findings` | `true` | Fail the job on confirmed findings |
| `sarif` | `precommiteu.sarif` | SARIF output path |
| `summary` | `precommiteu-summary.md` | Markdown summary path |

`fetch-depth: 0` is still worth setting: the action un-shallows the clone
itself, but doing it in `checkout` is faster.

On `push`, the action compares the commit before the push with `HEAD`,
including all commits in a multi-commit push and changes from force pushes.
A newly created branch has no previous tree, so all its code is scanned.
If the previous commit cannot be fetched, the job fails.

## GitLab CI

Register the machine as a GitLab runner with the Docker executor and the tag
`precommiteu`. In the runner's `config.toml`, add the models to the volumes:

```toml
[runners.docker]
  volumes = ["/cache", "/opt/precommiteu/models:/models:ro"]
```

```yaml
precommiteu:
  image: ghcr.io/alexandrugirlea/precommiteu:0.3.2
  tags: [precommiteu]
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  variables:
    GIT_DEPTH: "0"
  script:
    - git fetch origin "+refs/heads/$CI_MERGE_REQUEST_TARGET_BRANCH_NAME:refs/remotes/origin/$CI_MERGE_REQUEST_TARGET_BRANCH_NAME"
    - export GIT_MERGE_TARGET_BRANCH="$CI_MERGE_REQUEST_TARGET_BRANCH_NAME"
    - precommiteu scan --ci --fail-on-findings --sarif precommiteu.sarif --out mr-summary.md --force
  artifacts:
    when: always
    paths: [precommiteu.sarif, mr-summary.md, precommiteu_scan.log]
```

SARIF is retained as a downloadable artifact. GitLab's `reports: sast`
expects its own JSON schema, so do not put the SARIF file under that key.

## Azure DevOps

Add the machine as a self-hosted agent in a pool named `precommiteu` and add
the agent's user to the `docker` group.

```yaml
trigger: none
pr:
  branches: { include: ['*'] }

pool: { name: precommiteu }

container:
  image: ghcr.io/alexandrugirlea/precommiteu:0.3.2
  options: -v /opt/precommiteu/models:/models:ro

steps:
  - checkout: self
    fetchDepth: 0          # required: shallow clones have no merge base

  - script: |
      export GIT_MERGE_TARGET_BRANCH="${SYSTEM_PULLREQUEST_TARGETBRANCH#refs/heads/}"
      set -eu
      git fetch --quiet origin "+refs/heads/$GIT_MERGE_TARGET_BRANCH:refs/remotes/origin/$GIT_MERGE_TARGET_BRANCH"
      precommiteu scan --ci --fail-on-findings --sarif precommiteu.sarif --out pr-summary.md --force
    displayName: Scan changed files

  - publish: precommiteu.sarif
    artifact: precommiteu-sarif
    condition: always()
```

`SYSTEM_PULLREQUEST_TARGETBRANCH` arrives as `refs/heads/main`. Strip the
prefix: the scanner resolves `<branch>` then `origin/<branch>`, and neither
matches a full ref path.

For Azure Repos Git, configure this pipeline as a build-validation branch
policy; YAML `pr:` triggers apply to GitHub and Bitbucket repositories.

## Any other CI

On the same machine, run the image against a non-shallow checkout:

```bash
docker run --rm -v "$PWD:/src" -w /src -v /opt/precommiteu/models:/models:ro -e GIT_MERGE_TARGET_BRANCH="${CHANGE_TARGET:-main}" ghcr.io/alexandrugirlea/precommiteu:0.3.2 precommiteu scan --ci --fail-on-findings --sarif precommiteu.sarif --force
```

## What `--ci` scans

The jobs above run `precommiteu scan --ci`. It scans only the files changed
on the current branch against `GIT_MERGE_TARGET_BRANCH`. For push jobs, set
`GIT_DIFF_BASE` to the commit before the push instead. The scanner reads
no platform-specific event variables directly; the GitHub action sets these
values automatically.

```bash
git diff --name-only --diff-filter=AM "<merge-target>...HEAD"
```

- Merge target comes from `GIT_MERGE_TARGET_BRANCH` (default `main`), resolved
  as the local ref first, then `origin/<branch>`. Neither present → exit 2.
- When set, `GIT_DIFF_BASE` takes precedence and uses `git diff <base> HEAD`
  instead of the three-dot comparison. Other CI platforms must supply their
  before-push commit explicitly; comparing `main` to itself scans nothing.
- Running from a subdirectory still selects files across the Git repository
  and applies the repository root's `.eu-ignore`.
- Three-dot diff, so commits landed on the target after you branched are not
  scanned. Added and modified files only; deletions are ignored.
- The usual file filter still applies: code files only, tests skipped, files
  over `--max-file-bytes` skipped.
- No changed files → exit 0 without loading a model.
- `--ci` and positional paths together is an error.

Wire your platform's variable through `GIT_MERGE_TARGET_BRANCH`:

| Platform | Value |
|---|---|
| GitHub Actions | The action sets the PR target or the push baseline automatically |
| GitLab CI | `$CI_MERGE_REQUEST_TARGET_BRANCH_NAME` |
| Azure DevOps | `${SYSTEM_PULLREQUEST_TARGETBRANCH#refs/heads/}` |
| Jenkins | `${CHANGE_TARGET:-main}` |

## Reports

| Flag | Use |
|---|---|
| `--sarif <file>` | GitHub code scanning / SARIF-compatible tooling |
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

Advisories never affect the exit code. Confirmed findings and incomplete
analysis fail CI; an interrupted or failed scan must not be treated as clean.

## Runtime cost

On the CPU the orchestrator model (35B parameters, about 3B active per token)
sets the pace. Budget several minutes per changed file; a GPU is much faster.
That is fine on a pull request touching a handful of files; for large PRs or a
whole-repo scan, use a scheduled job rather than blocking every push.

## Debugging scope

```bash
GIT_MERGE_TARGET_BRANCH=main precommiteu scan --ci --dry-run
```

Prints the files the scan would cover and exits. No model needed. Compare
with `git diff --name-only --diff-filter=AM "origin/main...HEAD"` to see what
the file filter removed.

## Updating

Scanner and model versions are independent: scanner/action/image **0.3.2**
uses models **v0.3.0**. Pin the bundle revision documented for the scanner,
then bump the image and action together. Do not infer a model tag from the
scanner version. Ops pins all three in its release; follow its update steps.

## GPU or no Docker

The image runs the models on the CPU. To use a GPU, or on a Mac runner,
install `llama-server`, the scanner and the models directly on the machine
([install.md](install.md)), set `PRECOMMITEU_MODELS_DIR`, and leave the
container settings out of the job. The action and the scan commands work the
same.

## Build the image yourself

To host the image in your own registry, build it from the repository's
`Dockerfile`:

```bash
docker build -t <your-registry>/precommiteu:0.3.2 https://github.com/AlexandruGirlea/precommiteu.git#v0.3.2
```

Push it to a registry your CI can pull from, and use that name in place of
`ghcr.io/alexandrugirlea/precommiteu:0.3.2`.
