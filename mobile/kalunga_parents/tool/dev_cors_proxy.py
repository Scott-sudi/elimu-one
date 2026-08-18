"""Proxy CORS local pour Flutter Web → API Django o2switch.

Usage :
  python tool/dev_cors_proxy.py

Puis lancer Flutter sur Edge. Les appels /api/v1/* passent par
http://127.0.0.1:8788 (sans blocage CORS navigateur).
"""

from __future__ import annotations

import http.client
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = "institut-kalunga.net.susc3383.odns.fr"
LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 8788


class CorsProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _cors_headers(self) -> None:
        origin = self.headers.get("Origin", "*")
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header(
            "Access-Control-Allow-Headers",
            self.headers.get(
                "Access-Control-Request-Headers",
                "Content-Type, Authorization, Accept",
            ),
        )
        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, PUT, PATCH, DELETE, OPTIONS",
        )
        self.send_header("Vary", "Origin")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        self._proxy()

    def do_POST(self) -> None:  # noqa: N802
        self._proxy()

    def do_PUT(self) -> None:  # noqa: N802
        self._proxy()

    def do_PATCH(self) -> None:  # noqa: N802
        self._proxy()

    def do_DELETE(self) -> None:  # noqa: N802
        self._proxy()

    def _proxy(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(length) if length else None

        conn = http.client.HTTPConnection(UPSTREAM, timeout=45)
        headers = {
            "Accept": self.headers.get("Accept", "application/json"),
            "Content-Type": self.headers.get("Content-Type", "application/json"),
            # UA navigateur : le UA custom déclenche parfois Tiger Protect (503 HTML).
            "User-Agent": self.headers.get(
                "User-Agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36",
            ),
        }
        auth = self.headers.get("Authorization")
        if auth:
            headers["Authorization"] = auth

        try:
            conn.request(self.command, self.path, body=body, headers=headers)
            upstream = conn.getresponse()
            payload = upstream.read()
            status = upstream.status
            ctype = upstream.getheader("Content-Type", "application/json")

            # Tiger Protect renvoie une page HTML 503 au lieu du JSON API.
            if (status >= 500 and b"Tiger Protect" in payload) or (
                status == 503 and b"security-challenge" in payload
            ):
                data = json.dumps(
                    {
                        "success": False,
                        "message": (
                            "Le pare-feu o2switch (Tiger Protect) bloque cette "
                            "requête. Dans cPanel → Tiger Protect, désactivez "
                            "« I'm under attack » / règles trop strictes, ou "
                            "demandez à o2switch d'autoriser POST sur /api/v1/."
                        ),
                        "data": {},
                        "errors": {"code": "tiger_protect_blocked"},
                    }
                ).encode()
                self.send_response(503)
                self._cors_headers()
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

            self.send_response(status)
            self._cors_headers()
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except Exception as exc:  # noqa: BLE001
            data = json.dumps(
                {
                    "success": False,
                    "message": "Proxy local indisponible.",
                    "data": {},
                    "errors": {"detail": str(exc)},
                }
            ).encode()
            self.send_response(502)
            self._cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        finally:
            conn.close()

    def log_message(self, fmt: str, *args) -> None:
        print(f"[proxy] {self.command} {self.path} -> {fmt % args}")


def main() -> None:
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), CorsProxyHandler)
    print(f"Proxy CORS prêt : http://{LISTEN_HOST}:{LISTEN_PORT}")
    print(f"Upstream       : http://{UPSTREAM}")
    print("Ctrl+C pour arrêter.")
    server.serve_forever()


if __name__ == "__main__":
    main()
