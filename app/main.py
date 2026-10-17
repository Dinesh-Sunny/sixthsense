"""SixthFrame web app - stdlib only (no pip needed in the pod).

Serves index.html, the incidents/metrics JSON, an alerts feed, an "ask the footage" proxy
and a /clip proxy that streams segments from VSS (with Range support, so <video> can seek).
Runs on 0.0.0.0:$PORT; the cluster Ingress maps /app -> /, so the page uses relative URLs.
"""
import json, os, sys, threading, urllib.error, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "pipeline"))
from vss import VSS  # noqa: E402  (copied next to main.py on deploy)

DATA = os.environ.get("DATA_DIR", HERE)
ALERTS = os.path.join(os.environ.get("ALERTS_DIR", "/tmp"), "alerts.json")
LOCK = threading.Lock()
_vss = None


def vss():
    global _vss
    if _vss is None:
        _vss = VSS()
    return _vss


def read_json(path, default):
    try:
        return json.load(open(path))
    except Exception:
        return default


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.command, self.path.split("?")[0]))

    def send_json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = dict(urllib.parse.parse_qsl(u.query))
        p = u.path.rstrip("/") or "/"
        if p == "/health":
            return self.send_json({"ok": True})
        if p in ("/", "/index.html"):
            b = open(os.path.join(HERE, "index.html"), "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            return self.wfile.write(b)
        if p == "/api/incidents":
            inc = read_json(os.path.join(DATA, "incidents.json"), [])
            mode = q.get("mode")
            inc = [i for i in inc if not mode or i.get("mode") == mode]
            inc.sort(key=lambda i: (-int(i.get("risk", 1)), i.get("start_s", 0)))
            return self.send_json(inc)
        if p == "/api/metrics":
            return self.send_json(read_json(os.path.join(DATA, "metrics.json"), []))
        if p == "/api/alerts":
            return self.send_json(read_json(ALERTS, []))
        if p == "/clip":
            return self.clip(q.get("source", ""))
        self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        p = urllib.parse.urlparse(self.path).path.rstrip("/")
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        if p == "/api/alerts":
            with LOCK:
                a = read_json(ALERTS, [])
                a.insert(0, {k: body.get(k) for k in ("id", "camera_id", "type", "what_next", "risk", "start_s")})
                a[0]["sent_at"] = __import__("datetime").datetime.now().strftime("%H:%M:%S")
                json.dump(a[:50], open(ALERTS, "w"))
            hook = os.environ.get("DISCORD_WEBHOOK_URL")
            if hook:
                try:
                    msg = f"SixthFrame alert - risk {body.get('risk')} on {body.get('camera_id')}: {body.get('what_next')}"
                    urllib.request.urlopen(urllib.request.Request(hook, data=json.dumps({"content": msg}).encode(),
                                                                  headers={"Content-Type": "application/json"}), timeout=10)
                except Exception as e:
                    sys.stderr.write(f"webhook failed {e}\n")
            return self.send_json({"ok": True})
        if p == "/api/ask":
            try:
                r = vss().ask(body.get("question", ""), body.get("original_video"), 10)
                return self.send_json({"answer": r.get("answer"), "evidence": r.get("evidence")})
            except Exception as e:
                return self.send_json({"error": str(e)[:200]}, 502)
        self.send_json({"error": "not found"}, 404)

    def clip(self, source):
        if not source.startswith("s3://"):
            return self.send_json({"error": "bad source"}, 400)
        try:
            r = vss().stream(source, self.headers.get("Range"))
        except urllib.error.HTTPError as e:
            return self.send_json({"error": f"upstream {e.code}"}, 502)
        self.send_response(r.status)
        for h in ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges"):
            if r.headers.get(h):
                self.send_header(h, r.headers[h])
        self.end_headers()
        try:
            while chunk := r.read(64 * 1024):
                self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            r.close()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"SixthFrame on :{port}")
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()
