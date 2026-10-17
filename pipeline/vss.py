"""Thin client for the team's VSS backend (the same API the .cursor/skills call).

Reads INGRESS_URL / USERNAME / PASSWORD from the environment, or from the single
/config/*.config file on the lab VM. Never prints credentials.
"""
import glob, json, os, ssl, urllib.error, urllib.parse, urllib.request

_CTX = ssl.create_default_context()
if os.environ.get("VSS_INSECURE", "1") == "1":  # lab endpoints often use self-signed certs
    _CTX.check_hostname = False
    _CTX.verify_mode = ssl.CERT_NONE


def team_config() -> dict:
    """Env first, then the one /config/*.config file (parsed, not sourced - zsh-safe)."""
    cfg = {}
    files = sorted(glob.glob("/config/*.config"))
    if len(files) == 1:
        for line in open(files[0]):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    for k, v in os.environ.items():
        cfg[k] = v
    # deployed app uses VSS_* names
    cfg.setdefault("INGRESS_URL", cfg.get("VSS_URL", ""))
    cfg.setdefault("USERNAME", cfg.get("VSS_USERNAME", ""))
    cfg.setdefault("PASSWORD", cfg.get("VSS_PASSWORD", ""))
    if cfg.get("VSS_URL"):
        cfg["INGRESS_URL"] = cfg["VSS_URL"]
    if cfg.get("VSS_USERNAME"):
        cfg["USERNAME"] = cfg["VSS_USERNAME"]
    if cfg.get("VSS_PASSWORD"):
        cfg["PASSWORD"] = cfg["VSS_PASSWORD"]
    return cfg


def first(d: dict, keys, default=None):
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return d[k]
    return default


class VSS:
    def __init__(self, cfg: dict | None = None):
        cfg = cfg or team_config()
        self.base = cfg["INGRESS_URL"].rstrip("/") + "/api/v1"
        self.user, self.pw = cfg["USERNAME"], cfg["PASSWORD"]
        self.token = None

    # ---- plumbing ----
    def login(self):
        body = json.dumps({"username": self.user, "password": self.pw}).encode()
        req = urllib.request.Request(self.base + "/auth/login", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, context=_CTX, timeout=30) as r:
            self.token = json.load(r)["access_token"]
        return self.token

    def _req(self, method, path, body=None, params=None, raw=False, headers=None, retry=True):
        if not self.token:
            self.login()
        url = self.base + path
        if params:
            url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        h = {"Authorization": f"Bearer {self.token}"}
        if body is not None:
            h["Content-Type"] = "application/json"
        h.update(headers or {})
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, headers=h, method=method)
        try:
            r = urllib.request.urlopen(req, context=_CTX, timeout=120)
        except urllib.error.HTTPError as e:
            if e.code == 401 and retry:
                self.token = None
                return self._req(method, path, body, params, raw, headers, retry=False)
            raise
        if raw:
            return r  # caller reads + closes (used for video streaming)
        with r:
            txt = r.read()
            return json.loads(txt) if txt else None

    # ---- retrieval ----
    def search(self, query, camera_id=None, top_k=20, min_similarity=0.3, llm_top_n=1, **extra):
        body = {"query": query, "top_k": top_k, "min_similarity": min_similarity,
                "llm_top_n": llm_top_n, "include_public": True}
        if camera_id:
            body["metadata_filters"] = {"camera_id": camera_id}
        body.update(extra)
        return self._req("POST", "/search", body)

    def ask(self, question, original_video=None, top_k=10):
        body = {"question": question, "top_k": top_k}
        if original_video:
            body["original_video"] = original_video
        return self._req("POST", "/agent/ask", body)

    def explore(self, limit=100, offset=0, **filters):
        return self._req("GET", "/videos/explore", params={"scope": "all", "limit": limit, "offset": offset, **filters})

    def segments(self, original_video):
        return self._req("GET", "/tools/segments", params={"original_video": original_video})

    def metadata(self, source):
        return self._req("GET", "/videos/metadata", params={"source": source})

    def detections(self, source):
        try:
            return self._req("GET", "/videos/detections", params={"source": source})
        except urllib.error.HTTPError as e:
            if e.code == 404:  # no YOLO sidecar for this segment - normal
                return None
            raise

    def dashboard(self, scope="all"):
        return self._req("GET", "/dashboard/stats", params={"scope": scope})

    def schema(self):
        return self._req("GET", "/metadata/schema")

    def synthesize(self, original_video, question, max_segments=40):
        return self._req("POST", "/videos/synthesize",
                         {"original_video": original_video, "question": question, "max_segments": max_segments})

    def stream(self, source, range_header=None):
        """Open the seekable stream for one segment. Returns the raw response."""
        if not self.token:
            self.login()
        url = self.base + "/videos/stream?" + urllib.parse.urlencode({"source": source, "token": self.token})
        h = {"Range": range_header} if range_header else {}
        return urllib.request.urlopen(urllib.request.Request(url, headers=h), context=_CTX, timeout=120)

    def clip_bytes(self, source) -> bytes:
        with self.stream(source) as r:
            return r.read()
