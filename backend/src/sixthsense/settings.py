"""All configuration. The only module allowed to read the environment."""

import glob
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends
from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from .modes import MIN_SIMILARITY, PER_QUERY


def _alias(*names: str) -> AliasChoices:
    return AliasChoices(*names)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        validate_by_name=True,
        validate_by_alias=True,
    )

    # VSS backend (deployed pod uses VSS_*; the lab VM config file uses INGRESS_URL/USERNAME/PASSWORD)
    vss_url: str = Field("", validation_alias=_alias("vss_url", "VSS_URL", "INGRESS_URL"))
    vss_username: str = Field("", validation_alias=_alias("vss_username", "VSS_USERNAME", "USERNAME"))
    vss_password: SecretStr = Field(
        SecretStr(""), validation_alias=_alias("vss_password", "VSS_PASSWORD", "PASSWORD")
    )
    # Lab-only: the VSS ingress uses a self-signed cert. Public clients keep verification on.
    vss_verify_tls: bool = False
    clip_bucket: str = ""  # empty = any s3:// source; set to pin the proxy to one bucket

    # GPU models
    gpu_host: str = "166.19.38.112"
    cosmos_url: str = Field("", validation_alias=_alias("cosmos_url", "COSMOS3_REASON_URL"))
    cosmos_model: str = Field("", validation_alias=_alias("cosmos_model", "COSMOS3_REASON_MODEL"))
    yolo_url: str = ""
    gpu_token: SecretStr = Field(SecretStr(""), validation_alias=_alias("gpu_token", "GPU_BEARER_TOKEN"))
    structured_output: bool = False  # set true once `sixthsense probe` shows response_format works

    # W&B inference + Weave
    wandb_api_key: SecretStr = SecretStr("")
    wandb_team: str = ""
    wandb_project: str = "sixthsense"
    llm_base_url: str = "https://api.inference.wandb.ai/v1"
    llm_model: str = "meta-llama/Llama-3.3-70B-Instruct"

    # Store
    store_backend: Literal["vast", "json"] = "vast"
    s3_endpoint: str = ""
    access_key: SecretStr = SecretStr("")
    secret_key: SecretStr = SecretStr("")
    vastdb_bucket: str = ""
    vast_schema: str = "sixthsense"
    vast_ssl_verify: bool = False  # lab data VIP, see vastdb-write skill
    data_dir: Path = Path("data")

    # Pipeline behaviour
    verify_mode: Literal["boxes", "cosmos"] = "boxes"
    foresee_via: Literal["direct", "text"] = "direct"
    selfcheck_via: Literal["video", "text"] = "video"
    yolo_fallback: bool = True
    min_similarity: float = MIN_SIMILARITY
    per_query: int = PER_QUERY
    gpu_concurrency: int = 3
    step_timeout: float = 180.0

    # Public API guards (no end-user auth today)
    runs_enabled: bool = True
    run_cooldown_s: float = 60.0
    ask_concurrency: int = 2
    discord_webhook_url: SecretStr = SecretStr("")

    # Weather (London: footage is archive, so camera-city "now" would mislead)
    weather_city: str = "London"
    weather_lat: float = 51.5072
    weather_lon: float = -0.1276
    weather_tz: str = "Europe/London"
    weather_ttl_s: float = 600.0

    # Web
    web_dir: Path = Path("../web/out")
    seed_file: Path | None = None  # Sample incidents shown while a mode has no runs

    @property
    def wandb_project_path(self) -> str:
        return f"{self.wandb_team}/{self.wandb_project}".strip("/")

    @property
    def resolved_cosmos_url(self) -> str:
        return (self.cosmos_url or f"http://{self.gpu_host}:8001").rstrip("/")

    @property
    def resolved_yolo_url(self) -> str:
        return (self.yolo_url or f"http://{self.gpu_host}:8002").rstrip("/")


def env_files() -> tuple[str, ...]:
    """The lab VM keeps one /config/<team>.config; .env (later in the tuple) overrides it."""
    team = sorted(glob.glob("/config/*.config"))
    return (*team[:1], ".env") if len(team) == 1 else (".env",)


@lru_cache
def get_settings() -> Settings:
    return Settings(_env_file=env_files())  # type: ignore[call-arg]


SettingsDep = Annotated[Settings, Depends(get_settings)]
