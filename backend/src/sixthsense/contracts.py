"""The API contract. Mirrored by hand in web/src/lib/api/types.ts - keep field names in sync."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .modes import ASK_MAX_CHARS, RUN_LIMIT_MAX, Mode

CameTrue = Literal["yes", "partly", "no", "unknown"]
StepState = Literal["pending", "running", "done", "error"]
RunState = Literal["idle", "running", "done", "error"]
Wx = Literal["clear", "cloudy", "rain", "night"]


class _Out(BaseModel):
    model_config = ConfigDict(extra="ignore")


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GapPoint(_Out):
    t: float  # seconds from clip start
    cl: float  # gap in car lengths (box diagonals)


class Incident(_Out):
    id: str
    mode: Mode
    camera_id: str | None = None
    source: str | None = None
    original_video: str | None = None
    start_s: float = 0.0
    end_s: float = 0.0
    query: str | None = None
    similarity: float | None = None
    description: str = ""
    verified: bool = False
    verify_score: float = 0.0
    verify_note: str = ""
    verify_by: str = ""
    type: str = ""
    what_happens: str = ""
    what_next: str = ""
    why: str = ""
    fix: str = ""
    risk: int = 1
    came_true: CameTrue = "unknown"
    came_true_evidence: str = ""
    next_source: str | None = None
    judged_by: str | None = None
    fixture: bool = False  # true = Sample data, never live
    gap_series: list[GapPoint] = Field(default_factory=list)
    run_id: str | None = None
    trace_url: str | None = None


class ModeMetrics(_Out):
    mode: Mode
    run_id: str | None = None
    candidates: int = 0
    ruled_out: int = 0
    verified: int = 0
    checked: int = 0
    came_true_yes: int = 0
    came_true_partly: int = 0
    accuracy: float | None = None  # yes / checked; "N of M came true"
    generated_at: str = ""
    eval_url: str | None = None


class StepProgress(_Out):
    done: int = 0
    total: int = 0
    state: StepState = "pending"


class RunSteps(_Out):
    find: StepProgress = Field(default_factory=StepProgress)
    rule_out: StepProgress = Field(default_factory=StepProgress)
    predict: StepProgress = Field(default_factory=StepProgress)
    check: StepProgress = Field(default_factory=StepProgress)


class RunStatus(_Out):
    run_id: str | None = None
    mode: Mode | None = None
    limit: int = 0
    state: RunState = "idle"
    steps: RunSteps = Field(default_factory=RunSteps)
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None  # exception class only, never upstream text
    runs_enabled: bool = True
    cooldown_until: str | None = None  # ISO time a new run may start


class RunIn(_In):
    mode: Mode
    limit: int = Field(3, ge=1, le=RUN_LIMIT_MAX)


class AskIn(_In):
    question: str = Field(min_length=1, max_length=ASK_MAX_CHARS)
    original_video: str | None = None


class AskOut(_Out):
    answer: str = ""
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class AlertIn(_In):
    incident_id: str = Field(min_length=1, max_length=200)


class Alert(_Out):
    id: str
    incident_id: str
    camera_id: str | None = None
    type: str = ""
    what_next: str = ""
    risk: int = 1
    start_s: float = 0.0
    sent_at: str
    delivered: bool = False  # true when the Discord webhook accepted it


class Weather(_Out):
    city: str
    temp_c: float | None = None
    label: str
    wx: Wx
    source: Literal["open-meteo", "clock"]


class Health(_Out):
    ok: bool
    store: str | None = None  # "vast" | "json" | "degraded"
    vss: bool | None = None


# ---------- v2: London buses live map ----------
Direction = Literal["inbound", "outbound"]


class Vehicle(_Out):
    id: str  # TfL vehicleId (a registration)
    route: str
    dir: Direction
    towards: str = ""
    next_stop: str  # naptanId
    next_stop_name: str = ""
    eta_s: int
    lon: float
    lat: float
    bearing: float | None = None
    ts: str


class FleetSnapshot(_Out):
    ts: str
    vehicles: list[Vehicle] = Field(default_factory=list)
    routes: int = 0
    latency_ms: int = 0
    source: Literal["tfl"] = "tfl"


class RouteSummary(_Out):
    id: str
    name: str


class RouteStop(_Out):
    id: str
    name: str
    lon: float
    lat: float


class RouteDirection(_Out):
    dir: Direction
    coords: list[list[float]] = Field(default_factory=list)  # [[lon, lat], ...]
    stops: list[RouteStop] = Field(default_factory=list)


class RouteDetail(_Out):
    id: str
    directions: list[RouteDirection] = Field(default_factory=list)


class Pairing(_Out):
    """Stand-in: a real incident shown on a live bus. Labelled "Stand-in clip" on screen."""

    incident_id: str
    vehicle_id: str
    route: str
    risk: int
    came_true: CameTrue
    mode: Mode
    stop_name: str = ""  # live vehicle's next stop at pairing time
    towards: str = ""


class MapConfig(_Out):
    mapbox_token: str | None = None
