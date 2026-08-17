from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import threading

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict

from precommiteu.ui import catalog, install, preflight, runner, settings, state

STATIC = pathlib.Path(__file__).resolve().parent / "static"
LOGOS = ("logo.svg", "logo.png")
EU_PACKS = tuple(pid for jurisdiction, pid, *_ in catalog.PACKS if jurisdiction == "eu")
CLONE_TIMEOUT_S = 180


def local(name: str) -> pathlib.Path | None:
    path = pathlib.Path.cwd() / name
    return path if path.is_file() else None


class Live:
    def __init__(self, regulation: str) -> None:
        self.regulation = regulation
        self.session = runner.Session(None, regulation)

    def idle(self) -> None:
        if self.session.is_running():
            raise HTTPException(status_code=409, detail="a scan is running, stop it first")

    def retarget(self, target: pathlib.Path | None, regulation: str | None = None) -> dict:
        # Swapping the Session out mid-scan would leave the child process with
        # nobody holding it, so Pause and Stop would have nothing to act on.
        self.idle()
        self.regulation = regulation or self.regulation
        self.session = runner.Session(target, self.regulation)
        return self.session.refresh_plan()


app = FastAPI(title="precommitEU local UI")
live = Live("eu_ai_act")
installer = install.Installer()


@app.middleware("http")
async def guard(request: Request, call_next):
    # This server installs software and starts scans, so treat it as sensitive
    # even on loopback: pin the Host to stop DNS rebinding, and refuse writes
    # carrying an Origin, which is what a cross-site POST would look like.
    if request.headers.get("host", "").split(":")[0] not in ("127.0.0.1", "localhost"):
        return JSONResponse({"detail": "bad host"}, status_code=421)
    if request.method != "GET" and request.headers.get("origin") not in (
        None, f"http://{request.headers.get('host')}"
    ):
        return JSONResponse({"detail": "cross-origin write"}, status_code=403)
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    return response


class TargetIn(BaseModel):
    path: str


class RegulationIn(BaseModel):
    name: str


class InstallIn(BaseModel):
    action: str
    id: str | None = None


class CloneIn(BaseModel):
    url: str
    dest: str


class SettingsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    models_dir: str | None = None
    ledger_dir: str | None = None
    reports_dir: str | None = None


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/i18n.json")
def i18n() -> FileResponse:
    return FileResponse(STATIC / "i18n.json", media_type="application/json")


@app.get("/theme.css")
def theme() -> FileResponse:
    return FileResponse(local("theme.css") or STATIC / "theme.css", media_type="text/css")


@app.get("/logo")
def logo() -> FileResponse:
    for name in LOGOS:
        if path := local(name):
            return FileResponse(path)
    raise HTTPException(status_code=404, detail="no logo here")


@app.get("/api/branding")
def api_branding() -> dict:
    return {"logo": any(local(name) for name in LOGOS),
            "picker": bool(shutil.which("osascript"))}


@app.get("/api/preflight")
def api_preflight() -> dict:
    rows = preflight.run(live.session.is_running())
    return {"rows": rows,
            "ok": all(r["ok"] for r in rows if not r.get("optional"))}


@app.get("/api/catalog")
def api_catalog() -> dict:
    return catalog.build(settings.models_dir())


@app.post("/api/regulation")
def api_regulation(body: RegulationIn) -> dict:
    if body.name not in EU_PACKS:
        raise HTTPException(status_code=400, detail=f"unknown pack: {body.name}")
    if not (settings.models_dir() / body.name / install.ADAPTER).exists():
        raise HTTPException(status_code=400, detail=f"{body.name} not installed")
    return live.retarget(live.session.target, body.name)


@app.post("/api/pick-folder")
def api_pick_folder() -> dict:
    if not shutil.which("osascript"):
        raise HTTPException(status_code=501, detail="type the path instead")
    out = subprocess.run(
        ["osascript", "-e",
         'POSIX path of (choose folder with prompt "Select a folder")'],
        capture_output=True,
        text=True,
        check=False,
    )
    picked = out.stdout.strip().rstrip("/")
    if not picked:
        raise HTTPException(status_code=400, detail="no folder selected")
    return {"path": picked}


@app.post("/api/clone")
def api_clone(body: CloneIn) -> dict:
    # The URL reaches git as an argument, so anything that could be read as an
    # option, or as a transport that runs a command, is refused outright.
    if not body.url.startswith(("https://", "ssh://", "git@")):
        raise HTTPException(status_code=400, detail="use an https:// or git@ URL")
    parent = pathlib.Path(body.dest).expanduser().resolve()
    if not parent.is_dir():
        raise HTTPException(status_code=400, detail=f"not a directory: {parent}")
    target = parent / body.url.rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
    if target.exists():
        raise HTTPException(status_code=409, detail=f"already exists: {target}")
    out = subprocess.run(
        ["git", "clone", "--depth", "1", "--", body.url, str(target)],
        capture_output=True,
        text=True,
        check=False,
        timeout=CLONE_TIMEOUT_S,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    if out.returncode != 0:
        raise HTTPException(status_code=400, detail=out.stderr.strip()[-300:])
    return live.retarget(target)


@app.post("/api/target")
def api_target(body: TargetIn) -> dict:
    target = pathlib.Path(body.path).expanduser().resolve()
    if not target.is_dir():
        raise HTTPException(status_code=400, detail=f"not a directory: {target}")
    return live.retarget(target)


@app.get("/api/plan")
def api_plan() -> dict:
    return live.session.refresh_plan()


@app.get("/api/state")
def api_state() -> dict:
    return live.session.snapshot()


@app.post("/api/start")
def api_start() -> dict:
    if live.session.target is None:
        raise HTTPException(status_code=409, detail="no folder selected")
    live.session.start()
    return {"phase": live.session.phase}


@app.post("/api/pause")
def api_pause() -> dict:
    live.session.pause()
    return {"phase": live.session.phase}


@app.post("/api/stop")
def api_stop() -> dict:
    session = live.session
    session.pause()
    threading.Thread(target=_discard, args=(session,), daemon=True).start()
    return {"phase": session.phase}


def _discard(session: runner.Session) -> None:
    # The scan thread writes the state file one last time on its way out, so it
    # has to be gone before that file is deleted.
    if session.thread is not None:
        session.thread.join(timeout=runner.SIGINT_GRACE_S + 5)
    state.path_for(session.regulation).unlink(missing_ok=True)
    session.clear_ledger()
    live.retarget(session.target)


@app.post("/api/reset")
def api_reset() -> dict:
    live.idle()
    state.path_for(live.regulation).unlink(missing_ok=True)
    live.session.clear_ledger()
    return live.retarget(live.session.target)


@app.post("/api/ledger/clear")
def api_ledger_clear() -> dict:
    live.idle()
    path = live.session.scan_log
    cleared = path is not None and path.is_file()
    live.session.clear_ledger()
    return {"cleared": cleared, "path": str(path) if path else None,
            **live.session.refresh_plan()}


@app.get("/api/settings")
def api_settings() -> dict:
    return settings.view()


@app.post("/api/settings")
def api_settings_update(body: SettingsIn) -> dict:
    live.idle()
    if installer.snapshot()["phase"] == "running":
        raise HTTPException(status_code=409, detail="a download is running, wait for it")
    try:
        view = settings.update(body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # The session holds a ledger path built from the old settings.
    live.retarget(live.session.target)
    return view


@app.post("/api/install")
def api_install(body: InstallIn) -> dict:
    if body.action == "cancel":
        return installer.cancel()
    if body.action == "kill":
        runner.kill_servers()
        return {"started": False}
    if body.action == "base":
        return installer.install_pack(None)
    if body.action == "pack":
        if body.id not in EU_PACKS:
            raise HTTPException(status_code=400, detail=f"unknown pack: {body.id}")
        return installer.install_pack(body.id)
    raise HTTPException(status_code=400, detail=f"unknown action: {body.action}")


@app.get("/api/install")
def api_install_status() -> dict:
    return installer.snapshot()


@app.post("/api/reveal")
def api_reveal() -> dict:
    subprocess.run(["open", "-R", str(settings.runs_dir())], check=False)
    return {"ok": True}
