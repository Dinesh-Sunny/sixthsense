"""VSS backend calls (/api/v1) and the response models that replace `first()` key lookups.

Shapes recorded by the on-VM probe (request.md "Real API facts").
"""

from typing import Any

import httpx
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from sixthsense.modes import SEARCH_LLM_TOP_N

from .http import HttpClient, VSSAuth, with_retry


class _Up(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


def _a(*names: str) -> AliasChoices:
    return AliasChoices(*names)


class Segment(_Up):
    source: str = ""
    original_video: str | None = Field(None, validation_alias=_a("original_video", "parent_video"))
    segment_number: float = Field(0, validation_alias=_a("segment_number", "segment_index"))
    total_segments: int | None = None
    start_s: float = Field(
        0.0,
        validation_alias=_a(
            "segment_start_sec", "start_sec", "start_time", "start", "best_match_start_sec"
        ),
    )
    end_s: float | None = Field(
        None,
        validation_alias=_a("segment_end_sec", "end_sec", "end_time", "end", "best_match_end_sec"),
    )
    description: str = Field(
        "", validation_alias=_a("reasoning_content", "description", "reasoning", "caption")
    )
    camera_id: str | None = None
    location: str | None = None
    object_classes: Any = None
    similarity: float = Field(0.0, validation_alias=_a("similarity_score", "score"))

    @model_validator(mode="before")
    @classmethod
    def _drop_nulls(cls, data: Any) -> Any:
        # VSS sends explicit nulls/empty strings; let defaults apply (old first() semantics).
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if v not in (None, "")}
        return data

    @property
    def end(self) -> float:
        return self.end_s if self.end_s is not None else self.start_s + 5.0


class SearchResp(_Up):
    results: list[Segment] = Field(default_factory=list)


class SegmentsResp(_Up):
    original_video: str | None = None
    segments: list[Segment] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _accept_list(cls, data: Any) -> Any:
        if isinstance(data, list):
            return {"segments": data}
        if isinstance(data, dict) and "segments" not in data:
            for key in ("results", "items", "data"):
                if isinstance(data.get(key), list):
                    return {**data, "segments": data[key]}
        return data

    def ordered(self) -> list[Segment]:
        return sorted(self.segments, key=lambda s: (s.segment_number, s.start_s))


class Box(_Up):
    label: str = ""
    confidence: float = 1.0
    bbox: list[float] = Field(default_factory=list)


class Frame(_Up):
    frame_index: int = 0
    time_sec: float | None = None
    detections: list[Box] = Field(default_factory=list)


class DetectionsResp(_Up):
    """VSS detections sidecar and YOLO /v1/infer share this shape."""

    source: str | None = None
    fps: float | None = None
    frame_count: int | None = None
    frames: list[Frame] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _unwrap(cls, data: Any) -> Any:
        if isinstance(data, dict) and not data.get("frames"):
            nested = data.get("perception_json")
            if isinstance(nested, dict) and nested.get("frames"):
                return {**data, "frames": nested["frames"]}
        return data


class VSSClient:
    def __init__(self, http: HttpClient) -> None:
        self.http = http

    @property
    def has_token(self) -> bool:
        auth = self.http.auth
        return isinstance(auth, VSSAuth) and auth.has_token

    async def _get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        async def call() -> Any:
            r = await self.http.get(path, params=params)
            r.raise_for_status()
            return r.json()

        return await with_retry(call)

    async def _post_json(self, path: str, body: dict[str, Any], retry: bool) -> Any:
        async def call() -> Any:
            r = await self.http.post(path, json=body)
            r.raise_for_status()
            return r.json()

        return await (with_retry(call) if retry else call())

    async def login_check(self) -> None:
        await self._get_json("/auth/me")

    async def search(
        self, query: str, camera_id: str | None, top_k: int, min_similarity: float
    ) -> SearchResp:
        body: dict[str, Any] = {
            "query": query,
            "top_k": top_k,
            "min_similarity": min_similarity,
            "llm_top_n": SEARCH_LLM_TOP_N,
            "include_public": True,
        }
        if camera_id:
            body["metadata_filters"] = {"camera_id": camera_id}
        # Search is read-only, so it is safe to retry.
        return SearchResp.model_validate(await self._post_json("/search", body, retry=True))

    async def segments(self, original_video: str) -> SegmentsResp:
        data = await self._get_json("/tools/segments", {"original_video": original_video})
        return SegmentsResp.model_validate(data)

    async def metadata(self, source: str) -> Segment:
        return Segment.model_validate(await self._get_json("/videos/metadata", {"source": source}))

    async def detections(self, source: str) -> DetectionsResp | None:
        try:
            data = await self._get_json("/videos/detections", {"source": source})
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:  # no YOLO sidecar for this segment - normal
                return None
            raise
        return DetectionsResp.model_validate(data)

    async def ask(self, question: str, original_video: str | None, top_k: int = 10) -> dict[str, Any]:
        body: dict[str, Any] = {"question": question, "top_k": top_k}
        if original_video:
            body["original_video"] = original_video
        data = await self._post_json("/agent/ask", body, retry=False)
        return data if isinstance(data, dict) else {}

    async def dashboard(self) -> Any:
        return await self._get_json("/dashboard/stats", {"scope": "all"})

    def stream_request(self, source: str, range_header: str | None, if_range: str | None) -> httpx.Request:
        headers = {k: v for k, v in (("Range", range_header), ("If-Range", if_range)) if v}
        return self.http.build_request("GET", "/videos/stream", params={"source": source}, headers=headers)

    async def clip_bytes(self, source: str) -> bytes:
        async def call() -> bytes:
            r = await self.http.get("/videos/stream", params={"source": source})
            r.raise_for_status()
            return r.content

        return await with_retry(call)
