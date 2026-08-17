from __future__ import annotations

import sys
import threading
import webbrowser


def serve(port: int = 8787, open_browser: bool = True) -> int:
    try:
        import uvicorn

        from precommiteu.ui.app import app
    except ImportError:
        print("the UI needs extras: pip install 'precommiteu[ui]'", file=sys.stderr)
        return 2

    url = f"http://127.0.0.1:{port}"
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    if open_browser:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    print(f"precommitEU UI on {url}  (ctrl-c to stop)")
    server.run()
    return 0 if server.started else 1
