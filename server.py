#!/usr/bin/env python3
"""Loopback-only local server for STALKER PDA on Android/Termux."""
from __future__ import annotations

import argparse
import http.server
import os
import sys
from pathlib import Path


class PDARequestHandler(http.server.SimpleHTTPRequestHandler):
    """Serve project files with conservative local-only headers."""

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "geolocation=(self)")
        super().end_headers()

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stdout.write("[PDA] " + (fmt % args) + "\n")
        sys.stdout.flush()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run STALKER PDA on localhost.")
    parser.add_argument("--port", type=int, default=8080, help="TCP port (default: 8080)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not (1024 <= args.port <= 65535):
        print("Ошибка: порт должен быть от 1024 до 65535.", file=sys.stderr)
        return 2

    root = Path(__file__).resolve().parent
    os.chdir(root)
    address = ("127.0.0.1", args.port)

    try:
        server = http.server.ThreadingHTTPServer(address, PDARequestHandler)
    except OSError as exc:
        print(f"Не удалось запустить сервер на порту {args.port}: {exc}", file=sys.stderr)
        print("Попробуйте: python server.py --port 8081", file=sys.stderr)
        return 1

    print("\nSTALKER PDA запущен локально.")
    print(f"Откройте в Chrome именно: http://localhost:{args.port}/")
    print("Не открывайте index.html через file:// или content://.")
    print("Для остановки сервера нажмите Ctrl+C.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nСервер остановлен.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
