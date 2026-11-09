"""Launch the app: python -m swe_prac [--port N] [--no-browser]."""

from __future__ import annotations

import argparse
import socket
import threading
import webbrowser

import uvicorn


def _free_port(preferred: int) -> int:
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise SystemExit(f"No free port found in {preferred}-{preferred + 19}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="SWE interview practice")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    port = _free_port(args.port)
    url = f"http://127.0.0.1:{port}/"
    print(f"SWE Practice running at {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    uvicorn.run("swe_prac.app:app", host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
