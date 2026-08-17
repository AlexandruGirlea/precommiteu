---
title: Ignoring and suppressing
nav_order: 7
---

# Ignoring code and suppressing findings

precommitEU has three separate mechanisms for telling the scanner to leave
something alone. They work at different stages of the pipeline and they leave
very different audit trails. Picking the wrong one is the most common source of
confusion, so start here.

| Mechanism | Stage | What the model sees | Appears in reports | Use it for |
|---|---|---|---|---|
| `.eu-ignore` file | File discovery | Nothing. The file is never opened | No | Vendored, generated or third-party code |
| Inline `eu-ignore` directives | Before the prompt is built | Blank lines in place of your code | No, except `eu-ignore-file` | Secrets and noise that must never reach a model |
| `precommiteu-ignore` markers | After a finding is confirmed | Everything | Yes, with your reason | A reviewed finding you have decided to accept |

The rule of thumb: use `.eu-ignore` for code you do not own, inline directives
for code the model must not read, and `precommiteu-ignore` markers for findings
you have judged and accepted. Only the third one gives you a paper trail.

## 1. `.eu-ignore`, excluding paths from the scan

Put a `.eu-ignore` file in the directory the scan runs from. Matching files and
directories are dropped during discovery, so they are never read and never sent
anywhere.

```
# .eu-ignore, gitignore-like patterns, one per line
third_party/              # any directory named third_party, at any depth
/scripts/legacy.py        # a leading slash anchors to the scan root
*.sql                     # a pattern with no slash matches any path component
migrations/**/seed_*.py   # ** matches any number of directories
```

Syntax rules:

- `#` starts a comment. Blank lines are skipped.
- A trailing `/` restricts the pattern to directories.
- A leading `/` anchors the pattern to the scan root.
- `**` is supported in patterns that contain a slash.
- `fnmatch` wildcards (`*` and `?`) work in every path segment.
- Backslashes are normalised to forward slashes, so Windows-style paths work.

One important difference from `.gitignore`: **negation is not supported**. A
line beginning with `!` is parsed and then silently discarded. You cannot
re-include a path that an earlier pattern excluded. Write narrower patterns
instead.

To confirm what a scan will actually process, use `--dry-run`. It prints the
final file list after every filter has been applied, including `.eu-ignore`.

```bash
precommiteu scan src/ --dry-run
```

## 2. Inline `eu-ignore` directives, hiding code from the model

These directives blank out source lines before the prompt is assembled. The
model receives empty lines in their place, so line numbers in any finding stay
correct. Put them in a comment in whatever language you are writing; they are
matched as standalone words, so they work in `#`, `//` and `/* */` comments
alike.

There are five forms.

```python
API_KEY = load_key()  # eu-ignore
```

Blanks the line it appears on.

```python
# eu-ignore-next-line
send_receipt(user.home_address)
```

Blanks the following line.

```python
# eu-ignore-next-lines: 3
copy_a()
copy_b()
copy_c()
```

Blanks the next N lines. Both `:` and `=` are accepted before the count.

```python
# eu-ignore-start
legacy_export_block()
more_legacy_code()
# eu-ignore-end
```

Blanks everything between the two markers.

```python
# eu-ignore-file
```

Anywhere in a file, this skips the whole file. The scan records a `file_ignored`
event for it.

These directives also apply to files pulled in as cross-file context, so a
redacted definition stays redacted even when the orchestrator follows a
reference into it.

Because the code is removed before analysis, **nothing about the hidden lines
appears in any report**. There is no record that a line-level suppression
happened. That is the point when you are hiding a credential, and it is exactly
the wrong choice when you need to show an auditor what you decided and why. For
that, use the markers below.

The one exception is `eu-ignore-file`. Skipping a whole file emits a
`file_ignored` event, so it does show up in `--report`, in `--log-file` and in
the progress stream, though without any detail about what the file contained.

## 3. `precommiteu-ignore` markers, accepting a finding on the record

A marker suppresses a specific confirmed finding and records your reason in the
report.

```python
cursor.execute(EXPORT_QUERY)  # precommiteu-ignore: gdpr_art32 reason="DPA-approved export job, ticket SEC-1142"
```

The syntax is:

```
precommiteu-ignore: <article-rule> reason="<non-empty text>"
```

Single or double quotes both work, as long as they match.

**The article rule** is either an exact article id or an `fnmatch` glob over
article ids:

```python
process_profile(data)  # precommiteu-ignore: gdpr_art3? reason="Pseudonymised, reviewed by DPO 2026-05"
export_batch(rows)     # precommiteu-ignore: gdpr_* reason="Batch runs inside the DPA boundary"
```

Behaviour, precisely:

- A marker suppresses a confirmed finding whose cited article matches the rule
  **and** whose line range falls within 2 lines of the marker. Keep the marker
  on or next to the offending line.
- The `reason` is mandatory and must be non-empty. A marker without one is
  ignored entirely, and the finding stands.
- A bare wildcard rule such as `precommiteu-ignore: * reason="..."` is rejected
  and a warning is printed. Blanket inline suppression is deliberately not
  allowed.
- Markers are also recognised inside unified diffs, where they are mapped onto
  the new-file line numbers.

### What a suppressed finding does

A suppressed finding is removed from the console output and from the
`--fail-on-findings` exit-code check, so it will not fail your build. It stays
in the machine-readable output.

In `--json-out` it keeps its full entry, with two fields set:

```json
{
  "regulation": "gdpr",
  "file": "app/user_store.py",
  "start_line": 50,
  "probable_article_id": "gdpr_art32",
  "code_evidence": "logger.info(\"saving profile: %s\", profile.audit_line())",
  "description": "...",
  "eu_ignore_reason": "DPA-approved export job, ticket SEC-1142",
  "eu_ignore_source": "inline"
}
```

In SARIF the finding carries `properties.eu_ignored: true` alongside
`properties.eu_ignore_reason` and `properties.eu_ignore_source`.

To list every accepted finding across a repository, read the JSON:

```bash
precommiteu scan src/ --json-out report.json
jq -r '.findings[] | select(.eu_ignore_reason) | "\(.file):\(.start_line) \(.probable_article_id) \(.eu_ignore_reason)"' report.json
```

That list is the artefact to hand to a reviewer. It shows what was flagged, what
was accepted, and the stated justification for each.

## Choosing between them

Ask what you want to be true afterwards.

- *This code is not ours and should never be scanned.* Use `.eu-ignore`.
- *This line must never be sent to a model, even a local one.* Use an inline
  `eu-ignore` directive.
- *This is a real finding and we have decided to accept it.* Use a
  `precommiteu-ignore` marker, and write a reason a reviewer would accept.

If you find yourself reaching for an inline directive to quieten a finding you
disagree with, prefer the marker. Hiding the code makes the disagreement
invisible; the marker keeps it on the record and still unblocks your build.

## Related

- [CLI reference](cli.md) for `--dry-run`, `--fail-on-findings` and the report flags
- [Reports](reports.md) for the full JSON and SARIF field reference
- [Troubleshooting](troubleshooting.md) if a scan is finding nothing at all
