from __future__ import annotations

import hashlib
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import threading

from precommiteu.ui import settings

REPO = os.environ.get("PRECOMMITEU_MODELS_REPO", "AlexandruGirlea/precommiteu-models")
BASE = "base.gguf"
ORCHESTRATOR = "orchestrator.gguf"
SHARED = {BASE: 4_683_074_336, ORCHESTRATOR: 17_730_509_792}
ADAPTER = "detector-adapter.gguf"
SUMS = "SHA256SUMS"
EXTRA = ("NOTICE", "LICENSE.Apache-2.0.txt")
BREW = "brew install llama.cpp"
BASE_LABEL = "base"
# snapshot_download cannot be interrupted from another thread, so it runs in a
# child process we can terminate. A terminated child leaves its partial file
# behind for the next attempt.
FETCH = (
    "import sys;from huggingface_hub import snapshot_download;"
    "snapshot_download(sys.argv[1], local_dir=sys.argv[2], allow_patterns=sys.argv[3:])"
)


def sized(models: pathlib.Path, name: str) -> bool:
    path = models / name
    return path.is_file() and path.stat().st_size == SHARED[name]


def shared_ok(models: pathlib.Path) -> bool:
    return all(sized(models, name) for name in SHARED)


def engine_upgrade() -> str:
    if platform.system() == "Darwin":
        return "brew upgrade llama.cpp"
    if shutil.which("apt-get"):
        return "sudo apt-get install --only-upgrade llama.cpp-tools"
    return "rebuild llama.cpp from source"


def engine_command() -> str:
    if platform.system() == "Darwin":
        return BREW
    if shutil.which("apt-get"):
        return "sudo apt-get install llama.cpp-tools"
    return "build llama.cpp: https://github.com/ggml-org/llama.cpp"


def _dir_bytes(root: pathlib.Path) -> int:
    if not root.is_dir():
        return 0
    return sum(f.stat().st_size for f in root.rglob("*") if f.is_file())


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(models: pathlib.Path, names: list[str]) -> str | None:
    sums = models / SUMS
    if not sums.is_file():
        return f"{SUMS} missing, cannot verify the download"
    rows = (line.split() for line in sums.read_text(encoding="utf-8").splitlines())
    expected = {row[1]: row[0] for row in rows if len(row) == 2}
    for name in names:
        path = models / name
        if not path.is_file():
            return f"{name} did not download"
        if name in expected and _sha256(path) != expected[name]:
            return f"{name} failed checksum verification"
    return None


class Installer:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.phase = "idle"
        self.label = ""
        self.done_bytes = 0
        self.total_bytes = 0
        self.error: str | None = None
        self.proc: subprocess.Popen | None = None
        self._stop = threading.Event()
        self._cancel = threading.Event()

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "phase": self.phase,
                "label": self.label,
                "done_bytes": self.done_bytes,
                "total_bytes": self.total_bytes,
                "error": self.error,
                "cancelable": self.phase == "running" and self.proc is not None,
            }

    def _begin(self, label: str) -> bool:
        with self.lock:
            if self.phase == "running":
                return False
            self.phase = "running"
            self.label = label
            self.done_bytes = 0
            self.total_bytes = 0
            self.error = None
            self.proc = None
            self._stop.clear()
            self._cancel.clear()
            return True

    def _finish(self, error: str | None) -> None:
        with self.lock:
            if self._cancel.is_set():
                self.phase = "canceled"
            else:
                self.phase = "failed" if error else "done"
                self.error = error
                if not error:
                    self.done_bytes = self.total_bytes
            self._stop.set()

    def cancel(self) -> dict:
        with self.lock:
            proc = self.proc if self.phase == "running" else None
            if proc is None:
                return {"canceled": False}
            self._cancel.set()
        proc.terminate()
        return {"canceled": True}

    def install_pack(self, pack_id: str | None) -> dict:
        if not self._begin(pack_id or BASE_LABEL):
            return {"started": False}
        models = settings.models_dir()
        wanted = [SUMS, *EXTRA]
        if pack_id:
            wanted.insert(0, f"{pack_id}/{ADAPTER}")
        for name in SHARED:
            if sized(models, name):
                continue
            wanted.append(name)
            (models / ".cache/huggingface/download" / f"{name}.metadata").unlink(missing_ok=True)
        threading.Thread(target=self._run_pack, args=(models, wanted), daemon=True).start()
        return {"started": True}

    def _watch(self, models: pathlib.Path, baseline: int) -> None:
        while not self._stop.wait(0.5):
            with self.lock:
                self.done_bytes = max(0, _dir_bytes(models) - baseline)

    def _run_pack(self, models: pathlib.Path, wanted: list[str]) -> None:
        try:
            self._download(models, wanted)
        except BaseException as exc:
            self._finish(f"{type(exc).__name__}: {exc}")
            raise

    def _download(self, models: pathlib.Path, wanted: list[str]) -> None:
        from huggingface_hub import HfApi

        # total_bytes covers every wanted file, including the bytes already here,
        # so those bytes have to stay out of the baseline or the bar tops out short.
        here = sum((models / n).stat().st_size for n in wanted if (models / n).is_file())
        baseline = _dir_bytes(models) - here
        models.mkdir(parents=True, exist_ok=True)
        proc = subprocess.Popen(
            [sys.executable, "-c", FETCH, REPO, str(models), *wanted],
            env={**os.environ, "HF_HUB_DISABLE_PROGRESS_BARS": "1"},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        with self.lock:
            self.proc = proc
        try:
            info = HfApi().model_info(REPO, files_metadata=True)
            sizes = {s.rfilename: (s.size or 0) for s in info.siblings}
            with self.lock:
                self.total_bytes = sum(sizes.get(name, 0) for name in wanted)
        except Exception:
            pass

        threading.Thread(target=self._watch, args=(models, baseline), daemon=True).start()
        _, err = proc.communicate()
        if proc.returncode == 0:
            self._finish(verify(models, [n for n in wanted if n.endswith(".gguf")]))
            return
        tail = "\n".join((err or "").strip().splitlines()[-3:])
        self._finish(f"download failed: {tail or proc.returncode}")
