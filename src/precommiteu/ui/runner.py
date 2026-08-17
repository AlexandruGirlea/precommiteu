from __future__ import annotations

import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime

from precommiteu.llama_server import PROC_NAME
from precommiteu.scan_ledger import ScanLedger
from precommiteu.ui import eta, ledger, settings, state

# Subprocess, not an in-process call: a scan must stay interruptible and its
# JSONL ledger tailable. -m resolves in a venv, pipx or system install alike.
# -P is load-bearing: the child runs with cwd set to the scanned repo, and
# without it a precommiteu.py sitting there would be imported instead.
SCANNER = (sys.executable, "-P", "-m", "precommiteu")
POLL_S = 0.25
SIGINT_GRACE_S = 25.0
# pgrep/pkill -f match anywhere in the command line, so the bare name also hits
# a shell that merely mentions it. Anchoring pins the match to argv[0].
SERVER_MATCH = rf"^{PROC_NAME}( |$)"


def _stamp() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def server_pids() -> list[str]:
    try:
        out = subprocess.run(["pgrep", "-f", SERVER_MATCH], capture_output=True,
                             text=True, check=False, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return out.stdout.split()


def kill_servers() -> None:
    subprocess.run(["pkill", "-f", SERVER_MATCH], check=False)


def discover(target: pathlib.Path | None) -> tuple[list[str], str | None]:
    if target is None or not target.is_dir():
        return [], None
    out = subprocess.run(
        [*SCANNER, "scan", ".", "--dry-run"],
        cwd=target,
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        return [], out.stderr.strip() or f"file discovery failed (exit {out.returncode})"
    return sorted(ln.strip() for ln in out.stdout.splitlines() if ln.strip()), None


class Session:
    def __init__(self, target: pathlib.Path | None, regulation: str) -> None:
        self.target = target
        self.regulation = regulation
        self.key = str(target) if target else ""
        self.scan_log = settings.ledger_path(target, regulation) if target else None
        self.state = state.load(regulation)
        if self.state.get("target") != self.key:
            self.state = state.empty(self.key, regulation)
        self.proc: subprocess.Popen | None = None
        self.thread: threading.Thread | None = None
        self.lock = threading.Lock()
        self.phase = "idle"
        self.error: str | None = None
        self.adapter: str | None = None
        self.files: list[str] = []
        self.plan: list[str] = []
        self.current: str | None = None
        self.current_started = 0.0
        self.spawned_at = 0.0
        self.first_file_at = 0.0
        self.shown_eta: float | None = None
        self.eta_at = 0.0
        self.forecast: dict[str, dict] = {}

    def refresh_plan(self) -> dict:
        files, self.error = discover(self.target)
        self.files = files
        self.forecast = {f: self._forecast(f) for f in files}
        self.plan = list(files)
        if files:
            # The core ledger is the only judge of what still needs scanning.
            book = ScanLedger.load(self.target, self.regulation, self.scan_log)
            self.plan = [f for f in files if book.reuse(f) is None]
        for rel in list(self.state["files"]):
            if rel not in self.forecast:
                self.state["files"].pop(rel)
        state.save(self.state)
        return {
            "files": files,
            "plan": self.plan,
            "cached": [f for f in files if f not in self.plan],
        }

    def _forecast(self, rel: str) -> dict:
        from precommiteu.chunking import token_chunks
        from precommiteu.scan import _references_siblings
        from precommiteu.src.ignore_directives import apply_prompt_ignore_directives

        path = self.target / rel
        text = apply_prompt_ignore_directives(path.read_text(errors="replace")) or ""
        route = "orchestrator" if _references_siblings(text, path) else "direct"
        return {"chunks": max(1, len(token_chunks(path, text))), "route": route}

    def start(self) -> None:
        if self.phase == "running":
            return
        self.refresh_plan()
        if self.error:
            self.phase = "failed"
            return
        if not self.files:
            self.phase = "done"
            return
        self.phase = "running"
        self.state["run"] = {"started_at": _stamp(), "interrupted": False}
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _argv(self, segment: str, run_dir: pathlib.Path) -> list[str]:
        keep_awake = ["caffeinate", "-dimsu"] if shutil.which("caffeinate") else []
        # Every file goes to the scanner; it decides which ones it can reuse.
        return [
            *keep_awake,
            *SCANNER, "scan", *self.files,
            "--regulations", self.regulation,
            "--models-dir", str(settings.models_dir()),
            "--scan-log", str(self.scan_log),
            "--agent-mode", "auto",
            "--progress", "jsonl",
            "--report", str(run_dir / f"{segment}.events.jsonl"),
            "--json-out", str(run_dir / f"{segment}.result.json"),
            "--sarif", str(run_dir / f"{segment}.sarif"),
            "--out", str(run_dir / f"{segment}.md"),
            "--log-file", str(run_dir / f"{segment}.log"),
        ]

    def _child_env(self) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if k != "PRECOMMITEU_DEBUG_VALIDATOR"}
        env["PRECOMMITEU_MODELS_DIR"] = str(settings.models_dir())
        return env

    def clear_ledger(self) -> None:
        if self.scan_log is not None:
            self.scan_log.unlink(missing_ok=True)

    def _commit(self, rel: str, entry: dict) -> None:
        with self.lock:
            if entry["status"] == "done":
                ledger.observe_timing(self.state["timing"], entry)
            # A reused file carries no route or chunk count of its own.
            self.state["files"][rel] = {**self.forecast.get(rel, {}), **entry}
            self.current = None
            state.save(self.state)

    def _run(self) -> None:
        try:
            self._scan()
        except Exception as exc:
            self.pause()
            with self.lock:
                self.error = f"{type(exc).__name__}: {exc}"
        finally:
            with self.lock:
                if self.phase == "running":
                    self.phase = "failed"
                    self.error = self.error or "scan stopped unexpectedly"

    def _scan(self) -> None:
        run_dir = settings.runs_dir()
        segment = state.next_segment(run_dir)
        report = run_dir / f"{segment}.events.jsonl"
        fold = ledger.LedgerFold(self._commit)
        self.spawned_at = time.monotonic()
        self.first_file_at = 0.0
        stderr_tail: list[str] = []

        self.proc = subprocess.Popen(
            self._argv(segment, run_dir),
            cwd=self.target,
            env=self._child_env(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        threading.Thread(
            target=lambda: [stderr_tail.append(ln) for ln in self.proc.stderr],
            daemon=True,
        ).start()

        offset = 0
        while True:
            records, offset = ledger.tail(report, offset)
            for record in records:
                fold.feed(record)
                if record.get("event") == "file_start":
                    with self.lock:
                        self.current = (record.get("payload") or {}).get("file")
                        self.current_started = time.monotonic()
                        if not self.first_file_at:
                            self.first_file_at = self.current_started
            self.adapter = fold.adapter
            if self.proc.poll() is not None:
                records, offset = ledger.tail(report, offset)
                for record in records:
                    fold.feed(record)
                break
            time.sleep(POLL_S)

        fold.close()
        code = self.proc.returncode
        interrupted = fold.interrupted or code == 130
        # Advisories exist only in --json-out, and the run covers every file:
        # the reused ones are replayed into it too.
        try:
            result = json.loads((run_dir / f"{segment}.result.json").read_text())
            self.state["advisories"] = result.get("advisories", [])
        except (OSError, json.JSONDecodeError):
            pass

        with self.lock:
            if self.first_file_at:
                observed = self.first_file_at - self.spawned_at
                n = self.state["timing"]["n_direct"] + self.state["timing"]["n_orch"]
                cold = self.state["timing"]["cold_start_sec"]
                self.state["timing"]["cold_start_sec"] = (
                    observed if n == 0 else cold * 0.7 + observed * 0.3
                )
            self.state["run"] = {"ended_at": _stamp(), "interrupted": interrupted}
            state.save(self.state)
            self.current = None
            if interrupted:
                self.phase = "paused"
            elif code == 0:
                self.phase = "done"
            else:
                self.phase = "failed"
                self.error = "".join(stderr_tail[-8:]).strip() or f"exit {code}"

    def is_running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def pause(self) -> None:
        proc = self.proc
        if proc is None or proc.poll() is not None:
            return
        pgid = os.getpgid(proc.pid)
        os.killpg(pgid, signal.SIGINT)
        # The grace period is waited out on a thread so the HTTP caller is not
        # held for SIGINT_GRACE_S while the scan winds down.
        threading.Thread(
            target=self._escalate, args=(proc, pgid), daemon=True
        ).start()

    def _escalate(self, proc: subprocess.Popen, pgid: int) -> None:
        deadline = time.monotonic() + SIGINT_GRACE_S
        while time.monotonic() < deadline and proc.poll() is None:
            time.sleep(0.2)
        if proc.poll() is None:
            os.killpg(pgid, signal.SIGKILL)
            kill_servers()

    def snapshot(self) -> dict:
        with self.lock:
            files = self.state["files"]
            timing = self.state["timing"]
            queued = [
                self.forecast[f] for f in self.plan if f != self.current and f not in files
            ]
            current_entry = self.forecast.get(self.current) if self.current else None
            elapsed = time.monotonic() - self.spawned_at if self.spawned_at else 0.0
            cold_left = (
                max(0.0, timing["cold_start_sec"] - elapsed)
                if self.phase == "running" and not self.first_file_at
                else 0.0
            )
            on_current = (
                time.monotonic() - self.current_started if self.current_started else 0.0
            )
            raw = (
                eta.remaining(timing, queued, current_entry, on_current, cold_left)
                if self.phase == "running"
                else 0.0
            )
            now = time.monotonic()
            dt = now - self.eta_at if self.eta_at else 0.0
            self.eta_at = now
            if self.phase == "running":
                self.shown_eta = eta.smooth(self.shown_eta, raw, dt)
            else:
                self.shown_eta = None

            rows = []
            for rel in sorted(self.forecast):
                record = files.get(rel)
                if rel == self.current:
                    status = "running"
                elif record is None:
                    status = "queued"
                elif rel not in self.plan:
                    status = "cached"
                else:
                    status = record["status"]
                rows.append(
                    {
                        "file": rel,
                        "status": status,
                        "route": (record or self.forecast[rel])["route"],
                        "kept": (record or {}).get("kept", 0),
                        "duration_s": round((record or {}).get("duration_s", 0), 1),
                        "error": (record or {}).get("error"),
                    }
                )

            findings = [f for r in files.values() for f in r.get("findings", [])]
            done = sum(1 for r in rows if r["status"] not in ("queued", "running"))
            return {
                "phase": self.phase,
                "error": self.error,
                "adapter": self.adapter,
                "regulation": self.regulation,
                "target": self.key,
                "cold_remaining": round(cold_left, 1),
                "cold_total": round(timing["cold_start_sec"], 1),
                "eta_s": round(self.shown_eta) if self.shown_eta else None,
                "elapsed_s": round(elapsed) if self.spawned_at else 0,
                "files": rows,
                "files_done": done,
                "files_total": len(rows),
                "chunks_done": sum(
                    r.get("chunks", 0) for r in files.values()
                ),
                "findings": findings,
                "advisories": self.state.get("advisories", []),
            }
