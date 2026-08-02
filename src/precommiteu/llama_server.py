from __future__ import annotations

import atexit
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from precommiteu.config import (
    SERVER_HEALTH_POLL_INTERVAL_S,
    SERVER_HEALTH_TIMEOUT_S,
    SERVER_PORT_RETRY_LIMIT,
    SERVER_TERMINATE_GRACE_S,
)

# Every request goes to the loopback llama-server. urllib's default opener seeds
# a ProxyHandler from $HTTP_PROXY and does not exempt localhost, which would send
# the user's source code to a corporate proxy and break the zero-egress promise.
LOOPBACK_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

PROC_NAME = "precommiteu-llama-server"

BUILD_RE = re.compile(r"(?:\bb|version:\s*)(\d{4,6})\b")
MIN_BUILD = 4400
HEALTH_TIMEOUT_S = SERVER_HEALTH_TIMEOUT_S
HEALTH_POLL_INTERVAL_S = SERVER_HEALTH_POLL_INTERVAL_S
PORT_RETRY_LIMIT = SERVER_PORT_RETRY_LIMIT
TERMINATE_GRACE_S = SERVER_TERMINATE_GRACE_S


@dataclass(frozen=True)
class ServerHandle:
    url: str
    api_key: str


def parse_build(s: str) -> int:
    m = BUILD_RE.search(s)
    if not m:
        raise RuntimeError(f"could not parse llama-server build from {s!r}")
    return int(m.group(1))


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _poll_health(port: int, timeout_s: float, proc: subprocess.Popen | None = None) -> None:
    url = f"http://127.0.0.1:{port}/health"
    deadline = time.monotonic() + timeout_s
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        if proc is not None and proc.poll() is not None:
            stderr = (
                proc.stderr.read().decode("utf-8", errors="replace")
                if proc.stderr
                else ""
            )
            tail = stderr.strip().splitlines()[-8:]
            raise RuntimeError(
                "llama-server exited during startup. The model file may be "
                "corrupt or incompatible:\n" + "\n".join(tail)
            )
        try:
            with LOOPBACK_OPENER.open(url, timeout=2.0) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    data = {}
                if isinstance(data, dict) and data.get("status") == "ok":
                    return
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
            last_err = e
        time.sleep(HEALTH_POLL_INTERVAL_S)
    raise RuntimeError(
        f"llama-server at 127.0.0.1:{port} did not report healthy within "
        f"{timeout_s:.0f}s (last error: {last_err!r})"
    )


def _query_version() -> str:
    result = subprocess.run(
        ["llama-server", "--version"],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    return (result.stdout or "") + "\n" + (result.stderr or "")


def _signal_group(proc: subprocess.Popen, sig: signal.Signals) -> bool:
    # start_new_session gives the server its own group; kill it whole.
    if os.name != "posix":
        return False
    try:
        os.killpg(proc.pid, sig)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def _terminate(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        if not _signal_group(proc, signal.SIGTERM):
            proc.terminate()
        try:
            proc.wait(timeout=TERMINATE_GRACE_S)
            return
        except subprocess.TimeoutExpired:
            if not _signal_group(proc, signal.SIGKILL):
                proc.kill()
            try:
                proc.wait(timeout=TERMINATE_GRACE_S)
            except subprocess.TimeoutExpired:
                pass
    except ProcessLookupError:
        pass


def _drain_stream(stream) -> None:
    try:
        for _ in iter(stream.readline, b""):
            pass
    except (ValueError, OSError):
        pass


def _spawn(
    model_path: Path,
    port: int,
    n_ctx: int,
    n_gpu_layers: int,
    n_threads: int | None,
    lora_path: Path | None = None,
) -> subprocess.Popen:
    cmd: list[str] = [
        PROC_NAME,
        "-m",
        str(model_path),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--ctx-size",
        str(n_ctx),
        "--n-gpu-layers",
        str(n_gpu_layers),
        "--parallel",
        "1",
        "--jinja",
    ]
    if n_threads is not None:
        cmd += ["-t", str(n_threads)]
    if lora_path is not None:
        cmd += ["--lora", str(lora_path)]
    # argv[0] is the name ps/pgrep show: an orphaned server must be traceable
    # back to precommiteu rather than looking like an unrelated llama-server.
    return subprocess.Popen(
        cmd,
        executable=shutil.which("llama-server") or "llama-server",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=(os.name == "posix"),
    )


@contextmanager
def launch_llama_server(
    model_path: Path,
    *,
    n_ctx: int = 32768,
    n_gpu_layers: int = 0,
    n_threads: int | None = None,
    lora_path: Path | None = None,
) -> Iterator[ServerHandle]:
    model_path = Path(model_path)
    resolved_lora = Path(lora_path) if lora_path is not None else None
    proc: subprocess.Popen | None = None
    chosen_port: int | None = None
    last_err: Exception | None = None

    for _ in range(PORT_RETRY_LIMIT):
        port = _pick_free_port()
        try:
            candidate = _spawn(
                model_path,
                port,
                n_ctx,
                n_gpu_layers,
                n_threads,
                resolved_lora,
            )
        except FileNotFoundError as e:
            raise RuntimeError(
                "llama-server binary not found on PATH; install llama.cpp >= b4400"
            ) from e
        time.sleep(0.05)
        if candidate.poll() is not None:
            stderr = (candidate.stderr.read().decode("utf-8", errors="replace")
                      if candidate.stderr else "")
            if "address" in stderr.lower() and "use" in stderr.lower():
                last_err = OSError(f"port {port} already in use")
                continue
            raise RuntimeError(f"llama-server exited immediately: {stderr.strip()}")
        proc = candidate
        chosen_port = port
        break

    if proc is None or chosen_port is None:
        raise RuntimeError(
            f"could not bind a free port after {PORT_RETRY_LIMIT} attempts "
            f"(last error: {last_err!r})"
        )

    def _cleanup() -> None:
        if proc is not None:
            _terminate(proc)

    atexit.register(_cleanup)
    prev_sigint = signal.getsignal(signal.SIGINT)
    prev_sigterm = signal.getsignal(signal.SIGTERM)

    def _sigint_handler(signum, frame):
        _cleanup()
        if callable(prev_sigint):
            prev_sigint(signum, frame)
        else:
            raise KeyboardInterrupt

    def _sigterm_handler(signum, frame):
        # default SIGTERM skips atexit and would orphan the server
        _cleanup()
        if callable(prev_sigterm):
            prev_sigterm(signum, frame)
        elif prev_sigterm is signal.SIG_IGN:
            return
        else:
            raise SystemExit(128 + signum)

    try:
        signal.signal(signal.SIGINT, _sigint_handler)
    except ValueError:
        pass
    try:
        signal.signal(signal.SIGTERM, _sigterm_handler)
    except ValueError:
        pass

    try:
        try:
            _poll_health(chosen_port, HEALTH_TIMEOUT_S, proc)
        except RuntimeError:
            _cleanup()
            raise

        version_raw = _query_version()
        try:
            build = parse_build(version_raw)
        except RuntimeError:
            _cleanup()
            raise
        if build < MIN_BUILD:
            _cleanup()
            raise RuntimeError(
                f"llama-server build b{build} is older than required b{MIN_BUILD}"
            )

        for stream in (proc.stdout, proc.stderr):
            if stream is not None:
                threading.Thread(
                    target=_drain_stream, args=(stream,), daemon=True
                ).start()

        handle = ServerHandle(
            url=f"http://127.0.0.1:{chosen_port}/v1",
            api_key="sk-no-key",
        )
        yield handle
    finally:
        _cleanup()
        try:
            atexit.unregister(_cleanup)
        except Exception:
            pass
        try:
            signal.signal(signal.SIGINT, prev_sigint)
        except (ValueError, TypeError):
            pass
        try:
            signal.signal(signal.SIGTERM, prev_sigterm)
        except (ValueError, TypeError):
            pass
