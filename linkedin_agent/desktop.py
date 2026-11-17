"""Desktop app: runs the portal locally and opens it in a native window.

Installed builds (Windows .exe, macOS .app, Linux AppImage) start here. If the
native webview isn't available, the portal opens in the default browser.
Data lives in ~/.linkedin-agent like the CLI, so the desktop app, CLI and MCP
server all share the same workspaces, queue and LinkedIn connection.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser


def _free_port(preferred: int = 8787) -> int:
    for port in (preferred, 0):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return s.getsockname()[1]
            except OSError:
                continue
    return preferred


def main() -> None:
    port = _free_port(int(os.getenv("LA_PORT", "8787")))
    os.environ["LA_PORT"] = str(port)
    os.environ.setdefault("LA_HOST", "127.0.0.1")

    import uvicorn

    from linkedin_agent.server import app

    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    url = f"http://127.0.0.1:{port}/"
    for _ in range(100):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)

    try:
        import webview  # pywebview

        webview.create_window("LinkedIn Agent", url, width=1360, height=880, min_size=(960, 640))
        webview.start()
    except Exception:  # noqa: BLE001 - no GUI toolkit: fall back to the browser
        webbrowser.open(url)
        print(f"LinkedIn Agent is running at {url}  (Ctrl+C to quit)")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
    server.should_exit = True
    sys.exit(0)


if __name__ == "__main__":
    main()
