"""The one place openai is imported: Cosmos3-Reason (NIM) and W&B Inference, plus YOLO over httpx.

openai calls are not wrapped in tenacity: the SDK's max_retries=2 already covers 408/409/429/5xx.
"""

import base64
import json
import logging
import re
from typing import Any

import httpx
from openai import APIError, AsyncOpenAI
from pydantic import BaseModel, ValidationError

from sixthsense.modes import COSMOS_NUM_FRAMES
from sixthsense.settings import Settings
from sixthsense.tracing import op

from .vss import DetectionsResp

log = logging.getLogger("sixthsense.models")
OPENAI_TIMEOUT = 120.0
OPENAI_RETRIES = 2


class UpstreamError(Exception):
    """A model call failed after the SDK's own retries. Message never carries upstream text."""


def extract_json(text: str) -> str:
    """First {...} object in a reply; strips <think> blocks and ``` fences."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    m = re.search(r"\{.*\}", text, flags=re.S)
    return m.group(0) if m else "{}"


def parse_reply[M: BaseModel](text: str, model: type[M]) -> M | None:
    try:
        return model.model_validate_json(extract_json(text))
    except ValidationError:
        try:  # a reply that is valid JSON but not the schema: keep what fits
            return model.model_validate(json.loads(extract_json(text)))
        except (ValidationError, json.JSONDecodeError):
            return None


def _video_part(video: bytes) -> dict[str, Any]:
    b64 = base64.b64encode(video).decode()
    return {"type": "video_url", "video_url": {"url": f"data:video/mp4;base64,{b64}"}}


class ModelClients:
    def __init__(
        self,
        settings: Settings,
        gpu_http: httpx.AsyncClient,
        cosmos: AsyncOpenAI | None = None,
        llm: AsyncOpenAI | None = None,
    ) -> None:
        self.settings = settings
        self.gpu_http = gpu_http
        token = settings.gpu_token.get_secret_value() or "none"
        self.cosmos_client = cosmos or AsyncOpenAI(
            base_url=settings.resolved_cosmos_url + "/v1",
            api_key=token,
            max_retries=OPENAI_RETRIES,
            timeout=OPENAI_TIMEOUT,
        )
        key = settings.wandb_api_key.get_secret_value()
        self.llm_client = llm or (
            AsyncOpenAI(
                base_url=settings.llm_base_url,
                api_key=key,
                project=settings.wandb_project_path or None,
                max_retries=OPENAI_RETRIES,
                timeout=OPENAI_TIMEOUT,
            )
            if key
            else None
        )
        self._cosmos_model = settings.cosmos_model or None

    async def close(self) -> None:
        await self.cosmos_client.close()
        if self.llm_client is not None:
            await self.llm_client.close()

    async def cosmos_model(self) -> str:
        if not self._cosmos_model:
            page = await self.cosmos_client.models.list()
            self._cosmos_model = page.data[0].id
        return self._cosmos_model

    async def _chat(
        self, client: AsyncOpenAI, model: str, content: Any, max_tokens: int, **extra: Any
    ) -> str:
        try:
            r = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": content}],
                max_tokens=max_tokens,
                temperature=0,
                **extra,
            )
        except APIError as e:
            raise UpstreamError(f"{type(e).__name__} from {model}") from e
        return r.choices[0].message.content or ""

    @op(kind="llm", name="cosmos")
    async def cosmos(
        self, prompt: str, video: bytes | None, max_tokens: int, schema: dict[str, Any] | None = None
    ) -> str:
        """Ask Cosmos3-Reason about a clip (video sent inline as a data URL)."""
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        extra: dict[str, Any] = {}
        if video:
            content.append(_video_part(video))
            extra["extra_body"] = {"media_io_kwargs": {"video": {"num_frames": COSMOS_NUM_FRAMES}}}
        if schema is not None:
            extra["response_format"] = {"type": "json_schema", "json_schema": schema}
        return await self._chat(self.cosmos_client, await self.cosmos_model(), content, max_tokens, **extra)

    async def cosmos_json[M: BaseModel](
        self, prompt: str, video: bytes | None, model: type[M], max_tokens: int
    ) -> M | None:
        # Guided JSON only when the probe showed the endpoint supports it; else prompt + extract_json.
        schema = (
            {"name": model.__name__, "schema": model.model_json_schema()}
            if self.settings.structured_output
            else None
        )
        return parse_reply(await self.cosmos(prompt, video, max_tokens, schema), model)

    @op(kind="llm", name="llm")
    async def llm(self, prompt: str, max_tokens: int) -> str:
        """W&B serverless LLM; falls back to Cosmos text-only when no W&B key."""
        if self.llm_client is None:
            return await self.cosmos(prompt, None, max_tokens)
        return await self._chat(
            self.llm_client,
            self.settings.llm_model,
            prompt,
            max_tokens,
            response_format={"type": "json_object"},
        )

    async def llm_json[M: BaseModel](self, prompt: str, schema: type[M], max_tokens: int) -> M | None:
        return parse_reply(await self.llm(prompt, max_tokens), schema)

    @op(kind="tool", name="yolo")
    async def yolo(self, video: bytes, filename: str = "clip.mp4") -> DetectionsResp:
        body = {
            "video_base64": base64.b64encode(video).decode(),
            "filename": filename,
            "include_frames": True,
        }
        r = await self.gpu_http.post("/v1/infer", json=body)
        r.raise_for_status()
        return DetectionsResp.model_validate(r.json())

    async def llm_models(self) -> list[str]:
        if self.llm_client is None:
            return []
        page = await self.llm_client.models.list()
        return [m.id for m in page.data]

    async def supports_schema(self, client_name: str, schema: type[BaseModel]) -> bool:
        """Probe: does this endpoint accept response_format json_schema? (prints y/n, never values)"""
        client = self.cosmos_client if client_name == "cosmos" else self.llm_client
        if client is None:
            return False
        model = await self.cosmos_model() if client_name == "cosmos" else self.settings.llm_model
        rf = {
            "type": "json_schema",
            "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()},
        }
        try:
            text = await self._chat(client, model, "Reply with an example object.", 300, response_format=rf)
        except UpstreamError:
            return False
        return parse_reply(text, schema) is not None
