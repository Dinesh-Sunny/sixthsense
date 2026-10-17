"""Shared fakes: a VSS MockTransport and a ModelClients stand-in."""

import json

import httpx

from sixthsense.clients.vss import DetectionsResp

CLIP = bytes(range(256)) * 40  # 10,240 bytes


def converging_frames(n: int = 150, speed: int = 5, conf: float = 0.5, label_a: str = "car") -> list[dict]:
    frames = []
    for i in range(n):
        x = 100 + i * speed
        frames.append(
            {
                "frame_index": i,
                "time_sec": i / 30,
                "detections": [
                    {"label": label_a, "confidence": conf, "bbox": [x, 500, x + 200, 600]},
                    {"label": "truck", "confidence": 0.9, "bbox": [900, 500, 1100, 600]},
                ],
            }
        )
    return frames


def hit(i: int, parent: str = "s3://b/v1.mp4") -> dict:
    return {
        "source": f"s3://b/v1_chunk_{i:04d}.mp4",
        "original_video": parent,
        "segment_number": i,
        "segment_start_sec": i * 5.0,
        "segment_end_sec": i * 5.0 + 5,
        "reasoning_content": f"segment {i} description",
        "camera_id": "i24_cam-1",
        "similarity_score": 0.3 - i * 0.01,
    }


class FakeVSS:
    """Handler for httpx.MockTransport. Records calls; 401 once when `expire_token` is set."""

    def __init__(self) -> None:
        self.logins = 0
        self.calls: list[str] = []
        self.expire_token = False
        self.fail_status: dict[str, list[int]] = {}

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path.removeprefix("/api/v1")
        self.calls.append(path)
        if path == "/auth/login":
            self.logins += 1
            return httpx.Response(200, json={"access_token": f"tok{self.logins}"})
        if request.headers.get("authorization") != f"Bearer tok{self.logins}" or self.expire_token:
            self.expire_token = False
            return httpx.Response(401, json={"detail": "expired"})
        if self.fail_status.get(path):
            return httpx.Response(self.fail_status[path].pop(0), json={})
        if path == "/auth/me":
            return httpx.Response(200, json={"username": "x"})
        if path == "/search":
            return httpx.Response(200, json={"results": [hit(0), hit(1)]})
        if path == "/videos/detections":
            return httpx.Response(200, json={"fps": 30, "frames": converging_frames()})
        if path == "/tools/segments":
            return httpx.Response(200, json={"segments": [hit(i) for i in range(4)]})
        if path == "/agent/ask":
            body = json.loads(request.content)
            return httpx.Response(200, json={"answer": f"about {body['question']}", "evidence": ["e1", {"k": 1}]})
        if path == "/videos/stream":
            assert request.url.params.get("token") == f"tok{self.logins}"
            rng = request.headers.get("range")
            if rng:
                start, end = (int(x) for x in rng.removeprefix("bytes=").split("-"))
                async def body():
                    yield CLIP[start : end + 1]
                return httpx.Response(
                    206,
                    headers={
                        "content-type": "video/mp4",
                        "content-range": f"bytes {start}-{end}/{len(CLIP)}",
                        "content-length": str(end - start + 1),
                        "accept-ranges": "bytes",
                    },
                    content=body(),
                )
            return httpx.Response(200, headers={"content-type": "video/mp4"}, content=CLIP)
        return httpx.Response(404, json={})


class FakeModels:
    """Stands in for ModelClients: no openai, no GPU."""

    def __init__(self, risk: int = 4, came_true: str = "yes") -> None:
        self.risk = risk
        self.came_true = came_true

    async def cosmos(self, prompt, video, max_tokens, schema=None):
        return "yes"

    async def cosmos_json(self, prompt, video, model, max_tokens):
        if model.__name__ == "Forecast":
            return model(type="close cut-in", what_next="the car brakes", risk=self.risk)
        return model(came_true=self.came_true, evidence="brake lights")

    async def llm_json(self, prompt, model, max_tokens):
        return await self.cosmos_json(prompt, None, model, max_tokens)

    async def yolo(self, video):
        return DetectionsResp(frames=[])

    async def close(self):
        return None
