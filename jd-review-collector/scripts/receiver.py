#!/usr/bin/env python3
"""Local receiver: browser posts scraped JSON payloads per page.
usage: receiver.py <incoming_dir> [port=18923]
"""
import http.server, json, os, sys, datetime

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.getcwd(), "incoming")
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 18923
os.makedirs(OUT, exist_ok=True)

class H(http.server.BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()

    def do_POST(self):
        ln = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(ln)
        name = self.path.strip("/").replace("/", "_") or "data"
        ts = datetime.datetime.now().strftime("%H%M%S")
        fn = os.path.join(OUT, f"{name}_{ts}.json")
        with open(fn, "wb") as f:
            f.write(data)
        ok = True
        try:
            json.loads(data.decode("utf-8"))
        except Exception:
            ok = False
        self.send_response(200); self._cors()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"saved": fn, "bytes": len(data), "valid_json": ok}).encode())
        print(f"[{ts}] saved {name} {len(data)}B valid={ok}", flush=True)

    def do_GET(self):
        self.send_response(200); self._cors(); self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a):
        pass

if __name__ == "__main__":
    print(f"receiver listening on 127.0.0.1:{PORT} -> {OUT}", flush=True)
    http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
