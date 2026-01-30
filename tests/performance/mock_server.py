from __future__ import annotations

import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer


class MockHandler(BaseHTTPRequestHandler):
    def _write_json(self, payload: dict, status: int = 200) -> None:
        latency_ms = float(self.server.latency_ms)
        if latency_ms:
            time.sleep(latency_ms / 1000)

        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._write_json({"status": "ok"})
            return
        if self.path == "/api/connectors":
            self._write_json({"connectors": ["demo-connector"]})
            return
        self._write_json({"error": "not found"}, status=404)

    def do_POST(self) -> None:
        if self.path == "/api/connectors/sync":
            self._write_json({"status": "queued"})
            return
        self._write_json({"error": "not found"}, status=404)

    def log_message(self, format: str, *args: object) -> None:
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mock API server for performance testing.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--latency-ms", type=float, default=15.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    server = HTTPServer((args.host, args.port), MockHandler)
    server.latency_ms = args.latency_ms
    print(f"Mock performance server running on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
