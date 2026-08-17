---
title: Examples
nav_order: 5
---

# Examples

Worked, runnable examples. Each one states the goal, the exact command, the
output you should expect, and what to do with it.

Every example assumes the scanner and the model bundle are already in place
(see [install.md](install.md)):

```bash
brew install llama.cpp
pip install precommiteu
hf download AlexandruGirlea/precommiteu-models base.gguf gdpr/detector-adapter.gguf --local-dir ~/.precommiteu/models
export PRECOMMITEU_MODELS_DIR=~/.precommiteu/models
```

Model output is generated, not templated. Article ids, line ranges and quoted
evidence are stable; the wording of a description varies between runs. The
outputs below are representative, not byte-exact.

---

## 1. First scan on a real project

**Goal.** Find out what precommitEU says about your code, against one
regulation, without gating anything yet.

Start with the file selection. `--dry-run` loads no model and finishes
instantly:

```bash
precommiteu scan src/ --dry-run
```

```
src/api/handlers.py
src/billing/invoices.py
src/store/user_store.py
src/store/models.py
```

That is exactly the set a real scan will process. Test files, docs, generated
files, binaries, dependency directories and anything matched by `.eu-ignore`
are already gone. If the list is empty, jump to example 2: the filter is the
usual reason.

Now the scan:

```bash
precommiteu scan src/ --show-advisories --json-out result.json
```

Progress goes to stderr, one line per event:

```
[scan_start] files_total=4
[detector_adapter] regulation=gdpr adapter=gdpr/detector-adapter.gguf
[file_start] src/api/handlers.py regulation=gdpr
[orchestrator_done] src/api/handlers.py regulation=gdpr kept_raw=0 exit_reason=direct
[file_done] src/api/handlers.py regulation=gdpr kept=0
[file_start] src/store/user_store.py regulation=gdpr
[orchestrator_done] src/store/user_store.py regulation=gdpr kept_raw=1 exit_reason=emit
[finding] src/store/user_store.py
[file_done] src/store/user_store.py regulation=gdpr kept=1
[scan_done] findings_total=1
```

The summary goes to stdout:

```
Findings: 1
  [gdpr] src/store/user_store.py:50 gdpr_art32
      Full identity record is written to the application log.

Advisories (unconfirmed, non-blocking): 2
  [gdpr] src/billing/invoices.py: Customer records exported without a retention limit
  [gdpr] src/api/handlers.py: Request payload logged before field filtering
```

**What to do with it.** Read the findings first: each one is backed by a
verbatim quote from your file, so it takes seconds to agree or disagree.
Advisories are a reading list, not a task list. Nothing failed here: without
`--fail-on-findings` the exit code is 0 even with findings present.

Budget roughly a minute per file on CPU. Scan a directory, not the whole repo,
on the first run.

---

## 2. A cross-file finding, end to end

**Goal.** See the scanner catch a violation that only exists when two files are
read together.

The repository ships the pair as a test fixture:
`tests/fixtures/risky_code/models.py` and
`tests/fixtures/risky_code/user_store.py`.

`models.py` defines the record and a formatting helper:

```python
    def audit_line(self) -> str:
        return (
            f"{self.full_name} <{self.email}> national_id={self.national_id} "
            f"dob={self.date_of_birth.isoformat()} address={self.home_address}"
        )
```

`user_store.py` line 50 calls it:

```python
    def save_user(self, profile: UserProfile) -> None:
        logger.info("saving profile: %s", profile.audit_line())
```

Neither line is alarming alone. Together they write a full identity record
(name, email, national id, date of birth, home address) into the application
log.

### Read this before you try it: the fixture directory is not scannable

File discovery deliberately skips test and fixture paths: `tests/`, `test/`,
`spec/`, `fixtures/`, `testdata/`, `e2e/`, plus `*_test` / `*.spec` basenames.
Scanning the fixture in place returns nothing at all:

```bash
precommiteu scan tests/fixtures/risky_code --dry-run
```

```
```

Empty output, exit code 0, `files_total=0` on a real run. This is not a bug and
there is no flag to switch it off. Copy the two files somewhere that looks like
application code first:

```bash
mkdir -p /tmp/pceu-demo/app && cp tests/fixtures/risky_code/models.py tests/fixtures/risky_code/user_store.py /tmp/pceu-demo/app/
```

```bash
cd /tmp/pceu-demo && precommiteu scan app --dry-run
```

```
app/models.py
app/user_store.py
```

Two files selected. Now it is scannable.

### The scan

```bash
cd /tmp/pceu-demo && precommiteu scan app --json-out result.json --out summary.md
```

```
[scan_start] files_total=2
[detector_adapter] regulation=gdpr adapter=gdpr/detector-adapter.gguf
[file_start] app/models.py regulation=gdpr
[orchestrator_done] app/models.py regulation=gdpr kept_raw=0 exit_reason=direct
[file_done] app/models.py regulation=gdpr kept=0
[file_start] app/user_store.py regulation=gdpr
[orchestrator_done] app/user_store.py regulation=gdpr kept_raw=1 exit_reason=emit
[finding] app/user_store.py
[file_done] app/user_store.py regulation=gdpr kept=1
[scan_done] findings_total=1
```

```
Findings: 1
  [gdpr] app/user_store.py:50 gdpr_art32
      Personal data (full name, email, national id, date of birth, home
      address) is written to the application log via audit_line(), with no
      masking or access control on the log sink.
```

Two things in that trace are worth understanding.

`models.py` took the `direct` route (`exit_reason=direct`): it mentions no
sibling file, so the fast two-call path is enough. `user_store.py` imports
`models`, so the sibling stem `models` appears as a whole word in the file
text, and `auto` routing escalated it to the orchestrator, which read
`models.py` before deciding. That is the whole cross-file mechanism: structural
escalation, sandboxed to the scanned file's own directory.

The finding is filed against `user_store.py`, not `models.py`. The rule is that
a confirmed finding must quote code that is actually visible in the file being
judged. `audit_line()` on its own formats a string; the call on line 50 is what
sends it to the log.

### The evidence

```bash
jq '.findings[0]' result.json
```

```json
{
  "regulation": "gdpr",
  "source": "precommiteu",
  "file": "app/user_store.py",
  "start_line": 50,
  "end_line": 58,
  "probable_article_id": "gdpr_art32",
  "code_evidence": "logger.info(\"saving profile: %s\", profile.audit_line())",
  "description": "Personal data (full name, email, national id, date of birth, home address) is written to the application log via audit_line(), with no masking or access control on the log sink.",
  "eu_ignore_reason": null,
  "eu_ignore_source": null
}
```

`code_evidence` is the verbatim line 50. If the validator had returned a quote
that could not be located in the analyzed text, the finding would have been
dropped with the reason `evidence_not_visible` rather than reported. That is
the trade the scanner makes: fewer findings, each one checkable in one glance.

`summary.md` holds the same result as a PR comment: a `## precommitEU` heading,
a count line, and one table row per finding.

```markdown
**1 finding** across GDPR.

| Location | Article | Evidence | Description |
| --- | --- | --- | --- |
| app/user_store.py:50-58 | [GDPR Art. 32](https://eur-lex.europa.eu/LexUriServ/LexUriServ.do?uri=CELEX:32016R0679:EN:HTML) | `logger.info("saving profile: %s", profile.audit_line())` | Personal data ... is written to the application log ... |
```

**What to do with it.** Fix it (log the user id, not the record), or, if the
sink is genuinely access-controlled and reviewed, suppress it with an audited
marker. Example 7 shows how.

---

## 3. Several regulations in one run

**Goal.** Cover more than GDPR without drowning in output.

```bash
precommiteu scan src/ --regulations gdpr,eu_ai_act
```

The pack names are exactly: `gdpr`, `eu_ai_act`, `eu_data_act`, `dora`, `dsa`,
`cra_dma_nis2`. `gdpr` is the default. A typo is a configuration error, not a
silent no-op:

```bash
precommiteu scan src/ --regulations gdrp
```

```
error: regulation 'gdrp' not packaged in precommiteu.regulations
```

Exit code 2.

### Why "all six" is worse, not better

```bash
precommiteu scan src/ --regulations gdpr,eu_ai_act,eu_data_act,dora,dsa,cra_dma_nis2
```

That command is valid and it is usually a mistake.

- **Cost is linear in packs.** Every selected file is scanned once per
  regulation, with that regulation's detector adapter. Six packs is six passes
  over the same files, so roughly six times the wall-clock.
- **Noise is worse than linear.** Each pack has its own detector, and a
  detector that finds nothing still produces candidates. Candidates that fail
  validation become advisories. Running a pack that does not apply to your
  product adds advisories about obligations you do not have, and those are the
  ones people learn to ignore, which is how they stop reading the real ones.
- **Findings stay honest, attention does not.** Only confirmed, evidence-backed
  findings gate a build, so extra packs will not fail your PR spuriously. They
  will still cost you review time.

Pick the packs that match what the code actually does. A CRUD product with
personal data wants `gdpr`. Add `eu_ai_act` when you ship model inference,
`dora` in financial services, `dsa` for a platform with user-generated content,
`eu_data_act` for connected-product or cloud-switching obligations,
`cra_dma_nis2` for product security, gatekeeper or critical-infrastructure
duties.

One constraint to know: `--detector-adapter` points at a single file, so it
cannot be combined with multiple regulations. Omit it and let each pack resolve
its own adapter from the models directory.

```
error: a single --detector-adapter can't be combined with multiple regulations; omit it to auto-resolve per regulation
```

---

## 4. Gating a pull request

**Goal.** Fail a PR that introduces a confirmed violation, and show the finding
in the code-scanning UI.

The scanner reads exactly one CI variable, `GIT_MERGE_TARGET_BRANCH`. Wire your
platform's variable into it:

```bash
GIT_MERGE_TARGET_BRANCH="${GITHUB_BASE_REF:-main}" precommiteu scan --ci --fail-on-findings --sarif precommiteu.sarif --out pr-summary.md
```

`--ci` scans only files added or modified in
`git diff --name-only --diff-filter=AM <target>...HEAD`, so a PR touching three
files costs three files of inference, not a whole repo. It also turns on
`--fail-on-error` implicitly, so a scan that could not read a file never
reports a clean pass.

As a GitHub Actions workflow:

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
      - uses: AlexandruGirlea/precommiteu@v0.2.0
        with:
          regulations: gdpr
          fail-on-findings: "true"
      - uses: github/codeql-action/upload-sarif@v3
        if: ${{ !cancelled() }}
        with:
          sarif_file: precommiteu.sarif
          category: precommiteu
```

Two details that decide whether this works.

`fetch-depth: 0` gives the runner a merge base. A shallow clone cannot resolve
the target branch, and the scan exits 2.

`if: ${{ !cancelled() }}` on the upload step matters because the scan exits 1
when it finds something. Without it, the failing run never uploads the SARIF
and reviewers see a red check with no detail.

What the job does on a PR that adds the `logger.info` line from example 2:

```
Findings: 1
  [gdpr] app/user_store.py:50 gdpr_art32
      Personal data is written to the application log ...
```

Exit code 1, the check fails, and the finding appears in the Security tab
against GDPR Art. 32 with a link to the article text.

| Exit | Meaning | What the PR author does |
|---|---|---|
| 0 | No confirmed findings | Nothing |
| 1 | Confirmed findings remain | Fix the code, or add an audited marker (example 7) |
| 2 | Usage or configuration error | Fix the workflow: shallow clone, wrong pack name, missing model |
| 3 | A file could not be scanned | Re-run; results were incomplete, so a pass would have been a lie |
| 130 | Interrupted | Partial reports are still on disk |

Advisories never appear in this table. They cannot fail a build.

---

## 5. Machine-readable output

**Goal.** Feed the result to something other than a human.

All four report flags can be combined in one run. Each writes a different
artifact:

```bash
precommiteu scan src/ --json-out result.json --sarif precommiteu.sarif --out pr-summary.md --report scan-events.jsonl --log-file scan.log
```

| Flag | Format | Consumed by |
|---|---|---|
| `--json-out` | JSON | Your own tooling, dashboards, policy checks. The complete result: findings (including suppressed ones), advisories, per-regulation statuses |
| `--sarif` | SARIF 2.1.0 | GitHub code scanning, GitLab SAST, any SARIF viewer. Findings only, and only those whose article resolves in the pack registry |
| `--out` | Markdown | A PR comment, posted verbatim. Findings table only |
| `--report` | JSONL | Audit trails and debugging. Append-only ledger of every event in the order it happened |
| `--log-file` | Text | Operators. Same events plus warnings and errors, timestamped. Written to `precommiteu_scan.log` by default |

`--json-out`, `--sarif` and `--out` are snapshots, rewritten atomically after
every file and every finding, so a cancelled or crashed run still leaves valid,
partial files. `--report` is an append-only stream and never overwrites a
previous run.

Useful queries:

```bash
jq -r '.findings[] | "\(.file):\(.start_line) \(.probable_article_id)"' result.json
```

```
app/user_store.py:50 gdpr_art32
```

Count findings that would actually gate a build (suppressed ones do not):

```bash
jq '[.findings[] | select(.eu_ignore_reason == null)] | length' result.json
```

Check the scan was complete before trusting a clean result:

```bash
jq -r '.statuses[] | "\(.regulation) \(.status) chunks=\(.chunks_scanned) candidates=\(.detector_candidates) rejected=\(.validator_rejected)"' result.json
```

```
gdpr scanned chunks=2 candidates=3 rejected=2
```

Find out which route each file took, from the ledger:

```bash
jq -r 'select(.event == "orchestrator_done") | "\(.payload.file) \(.payload.route) tools=\(.payload.tool_calls)"' scan-events.jsonl
```

```
app/models.py direct tools=0
app/user_store.py orchestrator tools=3
```

Post the summary as a PR comment:

```bash
gh pr comment "$PR_NUMBER" --body-file pr-summary.md
```

---

## 6. Using the Python library

**Goal.** Run the same engine from your own script and do something custom with
the results.

Each call starts the local inference servers it needs and shuts them down
before returning. There is no server lifecycle to manage.

```python
import os
from precommiteu import scan_paths

os.environ["PRECOMMITEU_MODELS_DIR"] = "/opt/precommiteu/models"

result = scan_paths(["app/"], regulations=("gdpr",))

for f in result.findings:
    if f.eu_ignore_reason:
        print(f"suppressed {f.file}:{f.start_line} ({f.eu_ignore_reason})")
        continue
    print(f"{f.file}:{f.start_line}-{f.end_line} [{f.probable_article_id}]")
    print(f"  {f.description}")
    if f.code_evidence:
        print(f"  evidence: {f.code_evidence}")

for a in result.advisories:
    print(f"advisory {a.file}: {a.description}")

blocking = [f for f in result.findings if f.eu_ignore_reason is None]
raise SystemExit(1 if blocking else 0)
```

```
app/user_store.py:50-58 [gdpr_art32]
  Personal data is written to the application log via audit_line().
  evidence: logger.info("saving profile: %s", profile.audit_line())
```

`code_evidence` is `None` on findings with `source == "retrieval"`: those are
advisories promoted by a high-confidence match against known violation cases,
so there is no quoted line. Guard for it, as above.

Scanning a branch diff instead of a path:

```python
from precommiteu import GitDiffError, scan_diff

try:
    result = scan_diff(merge_target="main", agent_mode="direct")
except GitDiffError as exc:
    print(f"diff scan unavailable: {exc}")
    raise SystemExit(2)

if not result.findings:
    print("clean")
```

`GitDiffError` covers the three real failure modes: the working directory is
not a git repository, the merge target resolves as neither `main` nor
`origin/main`, or `git diff` itself failed. When nothing changed, `scan_diff`
returns immediately with empty findings and a status whose `detail` is
`"no files changed vs merge target"`, without loading a model.

Streaming, when you want output before the scan ends:

```python
from precommiteu import scan_paths

def on_progress(event):
    if event["event"] == "file_done":
        print(f"{event['file']}: {event['kept']} finding(s)")

def on_finding(f):
    print(f"FINDING {f.file}:{f.start_line} {f.probable_article_id}")

result = scan_paths(["app/"], on_progress=on_progress, on_finding=on_finding)
```

Exceptions raised inside a callback are logged and swallowed. They never abort
the scan.

---

## 7. Suppressing a reviewed false positive

**Goal.** Stop a finding from failing the build, while keeping a record that a
human decided it was acceptable.

Take the finding from example 2. Suppose the log sink is access-controlled, the
DPO signed off, and there is a ticket. Add an audited marker on the line:

```python
    def save_user(self, profile: UserProfile) -> None:
        logger.info("saving profile: %s", profile.audit_line())  # precommiteu-ignore: gdpr_art32 reason="Restricted audit sink, DPO sign-off SEC-1142"
```

Syntax: `precommiteu-ignore: <article-rule> reason="<non-empty text>"`. The
rule may be an exact article id (`gdpr_art32`) or an `fnmatch` glob over
article ids (`gdpr_art3*`). The reason is mandatory: a marker without one is
ignored. A bare wildcard is rejected with a warning, because blanket inline
suppression defeats the point:

```
::warning::precommitEU: inline wildcard marker `precommiteu-ignore: *` rejected at line 50 (wildcard inline ignores are not supported).
```

The marker suppresses a confirmed finding citing a matching article whose line
range falls within 2 lines of the marker. Keep it on or beside the offending
line, not at the top of the file.

Re-run with gating on:

```bash
cd /tmp/pceu-demo && precommiteu scan app --fail-on-findings --json-out result.json ; echo "exit=$?"
```

```
No findings.
exit=0
```

The build passes. The record does not disappear:

```bash
jq '.findings[] | {file, probable_article_id, eu_ignore_reason, eu_ignore_source}' result.json
```

```json
{
  "file": "app/user_store.py",
  "probable_article_id": "gdpr_art32",
  "eu_ignore_reason": "Restricted audit sink, DPO sign-off SEC-1142",
  "eu_ignore_source": "inline"
}
```

The same is true in SARIF, where the result carries
`properties.eu_ignored: true` and `properties.eu_ignore_reason`.

So: removed from the console, removed from the `--fail-on-findings` exit check,
still in the reports with the reason attached. An auditor can list every
suppression in the repo from one file:

```bash
jq -r '.findings[] | select(.eu_ignore_reason != null) | "\(.file):\(.start_line) \(.probable_article_id) :: \(.eu_ignore_reason)"' result.json
```

### When you want no trace at all

The inline redaction directives are a different mechanism. They blank the
source before the model ever sees it, preserving line numbers:

```python
API_KEY = load_key()  # eu-ignore

# eu-ignore-next-line
send_email(user.address)

# eu-ignore-next-lines: 3
copy_a()
copy_b()
copy_c()

# eu-ignore-start
legacy_export_block()
# eu-ignore-end
```

`# eu-ignore-file` anywhere in a file skips the whole file.
`eu-ignore-next-lines` accepts `:` or `=` before the count.

These leave nothing in any report: no finding, no reason, no audit trail. Use
them for code the scanner has no business reading. Use audited markers for
decisions you may need to defend.

---

## 8. Excluding vendored or generated code

**Goal.** Keep third-party and machine-written code out of the scan entirely.

Create `.eu-ignore` in the directory you run the scan from:

```
# .eu-ignore
third_party/
vendor/
/scripts/legacy_import.py
*.pb.go
migrations/**/seed_*.py
```

Rules, in the order they usually bite:

| Pattern | Effect |
|---|---|
| `third_party/` | Trailing slash restricts the match to directories. Any directory named `third_party`, at any depth |
| `/scripts/legacy_import.py` | Leading slash anchors the pattern to the scan root |
| `*.pb.go` | No slash in the pattern, so it matches any path component |
| `migrations/**/seed_*.py` | `**` matches any number of directories in slash-containing patterns |
| `# comment` | Comments and blank lines are skipped |

**Negation lines (`!pattern`) are not supported.** They are parsed and silently
skipped, so a file re-included by `!keep_this.py` stays excluded. There is no
warning. Do not build an ignore file that depends on negation.

Verify before you trust it. `--dry-run` applies `.eu-ignore` and prints the
survivors:

```bash
precommiteu scan . --dry-run | head -20
```

Note that a lot of exclusion is already automatic and does not belong in
`.eu-ignore`: `node_modules`, `vendor`, `dist`, `build`, `target`, `.venv`,
`__pycache__`, `coverage`, `.terraform`, `generated`, lockfiles, minified and
`.pb.*` bundles, binaries, prose files, `docs/`, and every test and fixture
path. Add patterns for what your repo does that the defaults cannot guess.

---

## 9. Speeding up a large repository

**Goal.** Get a useful answer out of a big codebase without waiting hours.

The single biggest lever is scanning fewer files. The second is skipping the
orchestrator.

```bash
precommiteu scan src/billing src/identity --agent-mode direct --max-wall-seconds-per-file 45 --max-orchestrator-iterations 6 --regulations gdpr
```

| Lever | Flag | Effect |
|---|---|---|
| Scope | positional paths | Scan the directories that touch personal data, not the repo |
| Diff only | `--ci` | Only files changed vs the merge target |
| Route | `--agent-mode direct` | Fixed detector plus validator per file, no tool use, no cross-file reads. Fastest path |
| Time budget | `--max-wall-seconds-per-file 45` | Hard wall-clock cap per file (default 90 s) |
| Steps budget | `--max-orchestrator-iterations 6` | Cap on agent steps per file (default 12) |
| Size cutoff | `--max-file-bytes 200000` | Skip large files (default 1000000; `0` removes the limit) |
| Packs | `--regulations gdpr` | One pass per pack, so one pack is one pass |
| GPU | `--gpu-layers 99` | Default. Offloads everything if your `llama-server` build has CUDA or Metal |

What `direct` costs you: the cross-file case from example 2. `user_store.py`
would be judged on its own text, without reading `models.py`. Use `direct` for
a broad first pass, then re-run the interesting directories on `auto`.

Budgets are per file and hard: 12 orchestrator iterations, 90 seconds of
wall-clock, and an 8000-token cap on every message sent to the model. A file
that exhausts its budget is reported, not silently dropped, and a file that
fails to scan raises the exit code to 3 under `--fail-on-error`.

Confirm the workload before committing to it:

```bash
precommiteu scan src/ --dry-run | wc -l
```

Multiply by roughly a minute per file on CPU. If that number is unpleasant,
scope harder or move the whole-repo scan to a nightly job on a GPU machine and
keep `--ci` on pull requests.

---

## 10. The local pre-commit loop

**Goal.** Catch a violation before it becomes a PR, without waiting a minute
per commit.

Scan only what is staged, on the direct route:

```bash
git diff --cached --name-only --diff-filter=AM | xargs -r precommiteu scan --agent-mode direct --fail-on-findings
```

`xargs -r` matters: `precommiteu scan` with no paths and no `--ci` is a usage
error (exit 2), so an empty staged set must not invoke it at all.

As a git hook, `.git/hooks/pre-commit`:

```bash
#!/usr/bin/env bash
set -eu
files=$(git diff --cached --name-only --diff-filter=AM)
[ -n "$files" ] || exit 0
echo "$files" | xargs precommiteu scan --agent-mode direct --fail-on-findings --progress none --json-out .git/precommiteu-last.json
```

```bash
chmod +x .git/hooks/pre-commit
```

A commit that stages the `logger.info` line from example 2:

```
Findings: 1
  [gdpr] app/user_store.py:50 gdpr_art32
      Personal data is written to the application log via audit_line().
```

The commit is refused. Fix the line, or add the audited marker from example 7,
and commit again.

With the [pre-commit](https://pre-commit.com) framework, as a local hook in
`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: local
    hooks:
      - id: precommiteu
        name: precommitEU compliance scan
        entry: precommiteu scan --agent-mode direct --fail-on-findings --progress none
        language: system
        pass_filenames: true
        types_or: [python, java, javascript, ts, tsx, go]
```

`pass_filenames: true` appends the staged files as positional paths, which is
exactly what `scan` expects. pre-commit does not run a hook when its file set
is empty, so no empty-invocation guard is needed here.

Three habits that keep this loop tolerable:

- `--agent-mode direct` on commit, `auto` in CI. Local speed, thorough gate.
- One regulation locally. Add packs in CI where the wait is someone else's.
- `--progress none` so the hook prints findings and nothing else.

If the loop is still too slow for your commit rhythm, drop the hook and rely on
`--ci` in the pull request. A gate that people disable is worse than a gate
that runs later.
