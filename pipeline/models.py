"""Direct calls to the shared GPU models (Cosmos3-Reason, YOLO11) and to W&B serverless LLMs.

Weave tracing is on when the `weave` package is installed and WANDB_API_KEY is set.
"""
import base64, json, os, re, urllib.request

from vss import _CTX, team_config

CFG = team_config()
GPU_HOST = CFG.get("GPU_HOST", "166.19.38.112")
COSMOS_URL = CFG.get("COSMOS3_REASON_URL") or f"http://{GPU_HOST}:8001"
YOLO_URL = CFG.get("YOLO_URL") or f"http://{GPU_HOST}:8002"
GPU_AUTH = {"Authorization": f"Bearer {CFG.get('GPU_BEARER_TOKEN', '')}"}
LLM_BASE = CFG.get("LLM_BASE_URL", "https://api.inference.wandb.ai/v1")
LLM_MODEL = CFG.get("LLM_MODEL", "")  # pick one from `python pipeline/probe.py` output
WANDB_PROJECT_PATH = f"{CFG.get('WANDB_TEAM', '')}/{CFG.get('WANDB_PROJECT', 'sixthsense')}".strip("/")

try:  # optional tracing
    import weave
    if CFG.get("WANDB_API_KEY"):
        os.environ.setdefault("WANDB_API_KEY", CFG["WANDB_API_KEY"])
        weave.init(WANDB_PROJECT_PATH or "sixthsense")
    op = weave.op
except Exception:  # weave missing or init failed -> plain functions
    def op(fn=None, **_):
        return fn if fn else (lambda f: f)


def _post(url, payload, headers, timeout=180):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, context=_CTX, timeout=timeout) as r:
        return json.load(r)


def _get(url, headers, timeout=30):
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), context=_CTX, timeout=timeout) as r:
        return json.load(r)


_cosmos_model = CFG.get("COSMOS3_REASON_MODEL")


def cosmos_model():
    global _cosmos_model
    if not _cosmos_model:
        _cosmos_model = _get(COSMOS_URL + "/v1/models", GPU_AUTH)["data"][0]["id"]
    return _cosmos_model


@op
def cosmos(prompt: str, video: bytes | None = None, max_tokens: int = 700) -> str:
    """Ask Cosmos3-Reason about a clip (video sent inline as base64)."""
    content = [{"type": "text", "text": prompt}]
    if video:
        b64 = base64.b64encode(video).decode()
        content.append({"type": "video_url", "video_url": {"url": f"data:video/mp4;base64,{b64}"}})
    r = _post(COSMOS_URL + "/v1/chat/completions",
              {"model": cosmos_model(), "messages": [{"role": "user", "content": content}],
               "max_tokens": max_tokens, "temperature": 0}, GPU_AUTH)
    return r["choices"][0]["message"]["content"] or ""


@op
def yolo(video: bytes, filename: str = "clip.mp4") -> dict:
    b64 = base64.b64encode(video).decode()
    return _post(YOLO_URL + "/v1/infer", {"video_base64": b64, "filename": filename, "include_frames": True}, GPU_AUTH)


@op
def llm(prompt: str, json_mode: bool = True) -> str:
    """W&B serverless inference (OpenAI-compatible). Falls back to Cosmos text-only if no key/model."""
    if not (CFG.get("WANDB_API_KEY") and LLM_MODEL):
        return cosmos(prompt, None, 400)
    payload = {"model": LLM_MODEL, "temperature": 0, "messages": [{"role": "user", "content": prompt}]}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    r = _post(LLM_BASE + "/chat/completions", payload,
              {"Authorization": f"Bearer {CFG['WANDB_API_KEY']}", "OpenAI-Project": WANDB_PROJECT_PATH})
    return r["choices"][0]["message"]["content"]


def llm_models():
    return [m["id"] for m in _get(LLM_BASE + "/models",
                                   {"Authorization": f"Bearer {CFG.get('WANDB_API_KEY', '')}",
                                    "OpenAI-Project": WANDB_PROJECT_PATH})["data"]]


def parse_json(text: str) -> dict:
    """Pull the first {...} object out of a model reply (handles ```json fences and <think> blocks)."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}
