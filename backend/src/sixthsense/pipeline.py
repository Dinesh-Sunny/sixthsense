"""SixthSense engine: watch -> verify -> foresee -> self-check -> store. Every step is a Weave op.

Async port of pipeline/run.py. Candidates run concurrently under one GPU semaphore; one failing
candidate never cancels the others (gather with return_exceptions).
"""

import asyncio
import difflib
import hashlib
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

import httpx
from pydantic import BaseModel, ConfigDict, field_validator

from . import tracing
from .clients.models import ModelClients, UpstreamError
from .clients.vss import DetectionsResp, Segment, VSSClient
from .contracts import CameTrue, GapPoint, Incident, ModeMetrics, RunSteps
from .modes import (
    BUS_HAZARD_TYPES,
    DESCRIPTION_MAX_CHARS,
    EVIDENCE_MAX_CHARS,
    FORESEE_MAX_TOKENS,
    HAZARD_CLASSES,
    JUDGE_MAX_TOKENS,
    MODES,
    NEAR_DUP_DESC_RATIO,
    NEAR_DUP_SEGMENTS,
    NEXT_DESC_MAX_CHARS,
    RISK_MAX,
    RISK_MIN,
    RISK_SKIP_BELOW,
    VERIFY_MIN,
    YES_NO_MAX_TOKENS,
    Mode,
    ModeConfig,
)
from .settings import Settings
from .store import IncidentStore
from .tracking import GapResult, closing_gap, closing_on_us, hazard_match

log = logging.getLogger("sixthsense.pipeline")
op = tracing.op
NOTHING = "nothing notable"
ProgressFn = Callable[[RunSteps], None]


@dataclass
class Deps:
    settings: Settings
    vss: VSSClient
    models: ModelClients
    gpu_sem: asyncio.Semaphore


class Candidate(BaseModel):
    hit: Segment
    query: str


class Verification(BaseModel):
    verified: bool
    verify_score: float
    verify_note: str
    verify_by: str
    gap_series: list[GapPoint] = []
    # ego only: best passing (score, note) per road-user class; lets the note follow the hazard type
    ego_passing: dict[str, tuple[float, str]] = {}


class Forecast(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: str = ""
    what_happens: str = ""
    what_next: str = ""
    why: str = ""
    fix: str = ""
    risk: int = RISK_MIN

    @field_validator("risk", mode="before")
    @classmethod
    def _clamp(cls, v: object) -> int:
        try:
            n = int(float(str(v)))
        except ValueError:
            n = RISK_MIN
        return max(RISK_MIN, min(RISK_MAX, n))


class Judgement(BaseModel):
    model_config = ConfigDict(extra="ignore")
    came_true: str = "unknown"
    evidence: str = ""


class SelfCheck(BaseModel):
    came_true: CameTrue = "unknown"
    came_true_evidence: str = ""
    next_source: str | None = None
    judged_by: str | None = None


# ---------- prompts (ported verbatim) ----------
FORESEE = """You are a {role}. Look only at what is visible in this clip.
Answer in JSON only:
{{"type": "<2-4 word label, e.g. close cut-in>",
 "what_happens": "<one sentence>",
 "what_next": "<the most likely thing in {horizon}>",
 "why": "<the visible cause>",
 "fix": "<one practical change that would prevent it>",
 "risk": <integer 1-5>}}
"what_next" must be specific and checkable on camera (name the vehicle/person by colour or type and the action), never generic like "traffic continues".
If nothing risky is happening, set risk to 1 and what_next to "nothing notable".
Never invent people, vehicles or events you cannot see."""

JUDGE = """Prediction: "{what_next}"
What the camera recorded next: "{next_desc}"
Did the prediction come true? Reply JSON only: {{"came_true": "yes|partly|no", "evidence": "<one short line from the next description>"}}
Be strict: "yes" only if the same kind of vehicles/people and the same kind of event appear."""

JUDGE_VIDEO = (
    'Prediction made from the previous clip: "{what_next}". Watch this clip. Did that happen? '
    'Reply JSON only: {{"came_true": "yes|partly|no", "evidence": "<what you see, one short line>"}}'
)

FORESEE_BUS = """You are a London bus safety analyst. {camera_line}
Describe only what is really visible in this clip: never invent people, vehicles or events.
Answer in JSON only:
{{"type": "<exactly one of: {types}>",
 "what_happens": "<one sentence naming the specific road users and where they are: colour, side, distance>",
 "what_next": "<a CHANGE you expect in {horizon}, one sentence, checkable on camera, e.g. the pedestrian reaches the bus's lane in about 2 s>",
 "why": "<one sentence: the visible cause>",
 "fix": "<one sentence of advice to the bus driver, e.g. {fix_example}>",
 "risk": <integer 1-5>}}
"what_next" must predict something that is not already happening: never "continues walking", "keeps driving"
or "remains in the lane". Pick the type that best fits what you see. Use your own fresh wording for this clip.
If nothing risky is happening, set risk to 1 and what_next to "nothing notable"."""

# How the bus prompt frames the camera, per view (None = fixed street/city camera read as a bus view).
BUS_CAMERA_LINES: dict[str | None, tuple[str, str]] = {
    None: (
        "Treat this camera as the front camera of a London bus driving through this scene.",
        "Hold back at the stop until the cyclist clears",
    ),
    "front": (
        "This is the bus's front camera, behind the windscreen: the bonnet at the bottom of the frame is the "
        "front of the bus and the road ahead is the bus's lane.",
        "Ease off and cover the brake until the pedestrian is back on the pavement",
    ),
    "nearside": (
        "This is the bus's nearside camera, low on the kerb side: road users beside the camera are alongside "
        "the bus on its nearside. The handlebars, hands and front wheel at the bottom of the frame belong to "
        "the camera; ignore them, they are not a road user.",
        "Check the nearside mirror and hold at the stop until the cyclist has passed",
    ),
}


def bus_prompt(cfg: ModeConfig) -> str:
    camera_line, fix_example = BUS_CAMERA_LINES[cfg.get("view")]
    return FORESEE_BUS.format(
        camera_line=camera_line,
        fix_example=fix_example,
        types=", ".join(cfg.get("hazard_types", BUS_HAZARD_TYPES)),
        horizon=cfg["horizon"],
    )


# Bus-view judges: a prediction that only restates the present is not a forecast that came true.
JUDGE_RESTATE_RULE = (
    ' If the prediction only restates what was already happening (e.g. "continues walking", "keeps driving"), '
    'answer "partly", never "yes".'
)
VERIFY_EGO_Q = "Answer only yes or no. Is a person, bike or vehicle close to this camera and getting closer?"
VERIFY_BOXES_Q = (
    "Answer only yes or no. Are two vehicles within about one car length of each other and getting closer?"
)
VERIFY_STREET_Q = (
    "Answer only yes or no. Is there a vehicle or person here behaving unusually for a quiet residential street?"
)


def incident_id(mode: str, source: str) -> str:
    """Deterministic, so a re-run upserts instead of duplicating."""
    return hashlib.sha1(f"{mode}:{source}".encode()).hexdigest()[:16]


class _Clip:
    """Fetch a candidate's clip once and share it across verify/foresee."""

    def __init__(self, vss: VSSClient, source: str) -> None:
        self._vss, self._source, self._data = vss, source, None

    async def get(self) -> bytes:
        if self._data is None:
            self._data = await self._vss.clip_bytes(self._source)
        return self._data


# ---------- 1 WATCH ----------
@op(kind="search")
async def watch(deps: Deps, mode: Mode, per_query: int) -> list[Candidate]:
    cfg = MODES[mode]
    sem = asyncio.Semaphore(deps.settings.gpu_concurrency)
    pairs = [(q, cam) for q in cfg["queries"] for cam in cfg["cameras"]]

    async def one(q: str, cam: str) -> list[Candidate]:
        async with sem:
            try:
                res = await deps.vss.search(q, cam, per_query, deps.settings.min_similarity)
            except httpx.HTTPError as e:
                log.warning("search failed for one query (%s)", type(e).__name__)
                return []
        return [Candidate(hit=h, query=q) for h in res.results if h.source]

    seen: set[str] = set()
    out: list[Candidate] = []
    for batch in await asyncio.gather(*(one(q, c) for q, c in pairs)):
        for c in batch:
            if c.hit.source not in seen:
                seen.add(c.hit.source)
                out.append(c)
    out.sort(key=lambda c: -c.hit.similarity)
    if cfg.get("round_robin"):
        out = round_robin(out, cfg["queries"])
    log.info("watch: %d candidate segments", len(out))
    return out


def _near_duplicate(a: Segment, b: Segment) -> bool:
    if a.original_video and a.original_video == b.original_video:
        if abs(a.segment_number - b.segment_number) <= NEAR_DUP_SEGMENTS:
            return True
    if a.description and b.description:
        return difflib.SequenceMatcher(None, a.description, b.description).ratio() > NEAR_DUP_DESC_RATIO
    return False


def round_robin(cands: list[Candidate], queries: list[str]) -> list[Candidate]:
    """Best hit of each query in turn (so every hazard type gets a slot), skipping near-duplicates."""
    queues = {q: [c for c in cands if c.query == q] for q in queries}
    out: list[Candidate] = []
    while any(queues.values()):
        for q in queries:
            while queues[q]:
                c = queues[q].pop(0)
                if not any(_near_duplicate(c.hit, kept.hit) for kept in out):
                    out.append(c)
                    break
    return out


# ---------- 2 VERIFY ----------
@op(kind="tool")
async def verify(deps: Deps, cand: Candidate, mode: Mode, clip: _Clip) -> Verification:
    cfg = MODES[mode]
    src = cand.hit.source
    ego = cfg["verify"] == "ego"
    if deps.settings.verify_mode == "boxes" and cfg["verify"] in ("boxes", "ego"):

        def check(d: DetectionsResp | None) -> GapResult | None:
            # Vehicle-mounted cameras have no box for themselves: score "closing on us" instead.
            return closing_on_us(d, cfg["classes"], cfg["view"]) if ego else closing_gap(d, cfg["classes"])

        try:
            det = await deps.vss.detections(src)
        except httpx.HTTPError as e:
            log.warning("detections failed (%s)", type(e).__name__)
            det = None
        gap = check(det)
        by = "yolo boxes (closing on us)" if ego else "yolo boxes"
        if gap is None and deps.settings.yolo_fallback:
            try:
                gap = check(await deps.models.yolo(await clip.get()))
                by += " (live)"
            except httpx.HTTPError as e:
                log.warning("yolo failed (%s)", type(e).__name__)
        if gap is not None:
            return Verification(
                verified=gap.passed if gap.passed is not None else gap.score >= VERIFY_MIN,
                verify_score=gap.score,
                verify_note=gap.note,
                verify_by=by,
                gap_series=gap.gap_series,
                ego_passing=gap.passing,
            )
    # Street mode, or no boxes at all: a strict yes/no asked of Cosmos on the clip.
    q = {"boxes": VERIFY_BOXES_Q, "ego": VERIFY_EGO_Q}.get(cfg["verify"], VERIFY_STREET_Q)
    try:
        ans = (await deps.models.cosmos(q, await clip.get(), YES_NO_MAX_TOKENS)).strip().lower()
    except (UpstreamError, httpx.HTTPError) as e:
        ans = f"error {type(e).__name__}"
    ok = ans.startswith("yes")
    return Verification(
        verified=ok, verify_score=1.0 if ok else 0.0, verify_note=f"Cosmos check: {ans[:20]}", verify_by="cosmos"
    )


# ---------- 3 FORESEE ----------
@op(kind="llm")
async def foresee(deps: Deps, cand: Candidate, mode: Mode, clip: _Clip) -> tuple[Forecast | None, str | None]:
    cfg = MODES[mode]
    if cfg.get("prompt") == "bus":
        prompt = bus_prompt(cfg)
    else:
        prompt = FORESEE.format(role=cfg["role"], horizon=cfg["horizon"])
    if deps.settings.foresee_via == "direct":
        fc = await deps.models.cosmos_json(prompt, await clip.get(), Forecast, FORESEE_MAX_TOKENS)
    else:  # text-only: reason over the stored description
        fc = await deps.models.llm_json(
            prompt + "\n\nClip description: " + cand.hit.description, Forecast, FORESEE_MAX_TOKENS
        )
    if fc is not None and cfg.get("prompt") == "bus":
        fc.type = bus_hazard_type(fc.type, cfg.get("hazard_types", BUS_HAZARD_TYPES))
    return fc, tracing.current_call_url()


def bus_hazard_type(raw: str, types: tuple[str, ...] = BUS_HAZARD_TYPES) -> str:
    """Snap the model's label onto the fixed hazard set (case/spacing tolerant); keep it if no match."""
    by_key = {t.lower(): t for t in types}
    key = " ".join(raw.lower().split()).strip(" .\"'")
    if key in by_key:
        return by_key[key]
    close = difflib.get_close_matches(key, list(by_key), n=1, cutoff=0.6)
    return by_key[close[0]] if close else raw


def hazard_classes(hazard_type: str) -> frozenset[str] | None:
    """Road-user classes a hazard label names, or None when it names no specific one."""
    t = hazard_type.lower()
    for word, classes in HAZARD_CLASSES.items():
        if word in t:
            return classes
    return None


def retarget_ego(ver: Verification, hazard_type: str) -> Verification:
    """Cite the road user the hazard names. If none of that class passed, keep the best passing
    track of any class and say so, so the note never pretends a car is the pedestrian."""
    wanted = hazard_classes(hazard_type)
    if wanted is None or not ver.verified:
        return ver
    match = hazard_match(ver.ego_passing, wanted)
    if match is None:
        best = max(ver.ego_passing.items(), key=lambda kv: kv[1][0], default=None)
        if best is None:
            return ver
        label, (score, note) = best
        return ver.model_copy(
            update={"verify_score": score, "verify_note": f"{note} (closest road user: {label})"}
        )
    score, note = match
    return ver.model_copy(update={"verify_score": score, "verify_note": note})


# ---------- 4 SELF-CHECK ----------
def _came_true(value: str) -> CameTrue:
    v = value.strip().lower()
    return v if v in ("yes", "partly", "no") else "unknown"  # type: ignore[return-value]


@op(kind="llm")
async def selfcheck(deps: Deps, cand: Candidate, what_next: str, mode: Mode | None = None) -> SelfCheck:
    parent = cand.hit.original_video
    if not parent or NOTHING in what_next.lower():
        return SelfCheck()
    try:
        segs = (await deps.vss.segments(parent)).ordered()
    except httpx.HTTPError as e:
        return SelfCheck(came_true_evidence=f"no segments ({type(e).__name__})")
    idx = next((i for i, s in enumerate(segs) if s.source == cand.hit.source), None)
    if idx is None or idx + 1 >= len(segs):
        return SelfCheck(came_true_evidence="no next segment")
    nxt = segs[idx + 1]
    next_desc = nxt.description
    if not next_desc:
        try:
            next_desc = (await deps.vss.metadata(nxt.source)).description
        except httpx.HTTPError:
            next_desc = ""
    bus_view = mode is not None and MODES[mode].get("prompt") == "bus"
    rule = JUDGE_RESTATE_RULE if bus_view else ""
    text_prompt = JUDGE.format(what_next=what_next, next_desc=next_desc[:NEXT_DESC_MAX_CHARS]) + rule
    judge: Judgement | None = None
    judged_by = "llm-text"
    if deps.settings.selfcheck_via == "video":
        # Cosmos watches the NEXT clip itself: grounded in pixels, not another caption.
        try:
            clip = await deps.vss.clip_bytes(nxt.source)
            judge = await deps.models.cosmos_json(
                JUDGE_VIDEO.format(what_next=what_next) + rule, clip, Judgement, JUDGE_MAX_TOKENS
            )
            judged_by = "cosmos-video"
        except (UpstreamError, httpx.HTTPError) as e:
            log.warning("cosmos judge failed (%s), falling back to text", type(e).__name__)
    if judge is None:
        judge = await deps.models.llm_json(text_prompt, Judgement, JUDGE_MAX_TOKENS)
        judged_by = "llm-text"
    if judge is None:
        return SelfCheck(next_source=nxt.source, judged_by=judged_by)
    return SelfCheck(
        came_true=_came_true(judge.came_true),
        came_true_evidence=judge.evidence[:EVIDENCE_MAX_CHARS],
        next_source=nxt.source,
        judged_by=judged_by,
    )


# ---------- RUN ----------
def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


@op(kind="agent")
async def run_mode(
    deps: Deps, mode: Mode, limit: int, run_id: str, on_progress: ProgressFn | None = None
) -> tuple[list[Incident], ModeMetrics]:
    steps = RunSteps()

    def emit() -> None:
        if on_progress:
            on_progress(steps.model_copy(deep=True))

    steps.find.state = "running"
    emit()
    cands = (await watch(deps, mode, deps.settings.per_query))[:limit]
    steps.find = steps.find.model_copy(update={"done": 1, "total": 1, "state": "done"})
    steps.rule_out.total = len(cands)
    steps.rule_out.state = steps.predict.state = steps.check.state = "running"
    emit()
    timeout = deps.settings.step_timeout
    counts = {"ruled_out": 0}

    async def one(cand: Candidate) -> Incident | None:
        async with deps.gpu_sem:
            clip = _Clip(deps.vss, cand.hit.source)
            async with asyncio.timeout(timeout):
                ver = await verify(deps, cand, mode, clip)
            steps.rule_out.done += 1
            if not ver.verified:
                counts["ruled_out"] += 1
                emit()
                return None
            steps.predict.total += 1
            emit()
            async with asyncio.timeout(timeout):
                fc, trace_url = await foresee(deps, cand, mode, clip)
            steps.predict.done += 1
            if fc is None or fc.risk < RISK_SKIP_BELOW:
                emit()
                return None
            if ver.ego_passing or MODES[mode]["verify"] == "ego":
                ver = retarget_ego(ver, fc.type)
            steps.check.total += 1
            emit()
            async with asyncio.timeout(timeout):
                sc = await selfcheck(deps, cand, fc.what_next, mode)
            steps.check.done += 1
            emit()
        h = cand.hit
        return Incident(
            id=incident_id(mode, h.source),
            mode=mode,
            camera_id=h.camera_id or MODES[mode]["cameras"][0],
            source=h.source,
            original_video=h.original_video,
            start_s=h.start_s,
            end_s=h.end,
            query=cand.query,
            similarity=h.similarity,
            description=h.description[:DESCRIPTION_MAX_CHARS],
            verified=ver.verified,
            verify_score=ver.verify_score,
            verify_note=ver.verify_note,
            verify_by=ver.verify_by,
            gap_series=ver.gap_series,
            **fc.model_dump(),
            **sc.model_dump(),
            fixture=False,
            camera_view=MODES[mode].get("view"),
            run_id=run_id,
            trace_url=trace_url,
        )

    results = await asyncio.gather(*(one(c) for c in cands), return_exceptions=True)
    incidents: list[Incident] = []
    failed = 0
    for r in results:
        if isinstance(r, BaseException):
            if not isinstance(r, Exception):
                raise r  # cancellation / KeyboardInterrupt
            failed += 1
            log.warning("candidate failed (%s)", type(r).__name__)
        elif r is not None:
            incidents.append(r)
    for s in (steps.rule_out, steps.predict, steps.check):
        s.state = "done"
    emit()
    checked = [i for i in incidents if i.came_true in ("yes", "partly", "no")]
    yes = sum(i.came_true == "yes" for i in checked)
    metrics = ModeMetrics(
        mode=mode,
        run_id=run_id,
        candidates=len(cands),
        ruled_out=counts["ruled_out"],
        verified=len(incidents),
        checked=len(checked),
        came_true_yes=yes,
        came_true_partly=sum(i.came_true == "partly" for i in checked),
        accuracy=round(yes / len(checked), 3) if checked else None,
        generated_at=_now(),
    )
    if failed:
        log.warning("run %s: %d candidates failed", run_id, failed)
    return incidents, metrics


async def execute_run(
    deps: Deps,
    store: IncidentStore,
    mode: Mode,
    limit: int,
    run_id: str,
    on_progress: ProgressFn | None = None,
) -> ModeMetrics:
    with tracing.run_context(mode, run_id):
        incidents, metrics = await run_mode(deps, mode, limit, run_id, on_progress)
    await store.save_run(metrics, incidents)
    return metrics
