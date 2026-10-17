"""One engine, mode = config. Edit queries and thresholds here, not in code."""

from typing import Literal, TypedDict

Mode = Literal["road", "street", "city", "bus"]
MODE_NAMES: tuple[Mode, ...] = ("road", "street", "city", "bus")


class ModeConfig(TypedDict, total=False):
    cameras: list[str]
    verify: Literal["boxes", "cosmos"]
    label: str
    classes: frozenset[str]
    queries: list[str]
    role: str
    horizon: str
    prompt: str  # "bus" = London bus safety analyst prompt (pipeline.FORESEE_BUS)
    round_robin: bool  # take candidates query by query so every hazard type is represented


# COCO ids as returned by YOLO11; the tracker is class-agnostic, so ids gate what it sees.
COCO_IDS: dict[str, int] = {"person": 0, "bicycle": 1, "car": 2, "motorcycle": 3, "bus": 5, "truck": 7}
VEHICLES: frozenset[str] = frozenset({"car", "motorcycle", "bus", "truck"})
# person/bicycle only ever count as the other party of a pair with a vehicle.
VULNERABLE: frozenset[str] = frozenset({"person", "bicycle"})

MODES: dict[Mode, ModeConfig] = {
    "road": {
        "cameras": ["i24_cam-1"],
        "verify": "boxes",
        "label": "Road - Nashville I-24 highway",
        "classes": VEHICLES,
        "queries": [
            "truck cutting in close in front of a car",
            "sudden hard braking in traffic",
            "vehicle changing lanes very close to another vehicle",
            "stopped vehicle in a live lane",
            "tailgating at highway speed",
        ],
        "role": "road-safety analyst watching highway CCTV",
        "horizon": "the next 5-10 seconds",
    },
    "street": {
        "cameras": ["neighborhood_cam-1"],
        "verify": "cosmos",
        "label": "Street - neighbourhood camera, 2 days",
        "classes": VEHICLES,
        "queries": [
            "vehicle parked with nobody getting out",
            "same vehicle driving past slowly",
            "person lingering near a front door",
            "activity on the street late at night",
        ],
        "role": "neighbourhood-security analyst watching a street camera",
        "horizon": "the next visit or the next few minutes",
    },
    "city": {
        "cameras": [
            "nyc_streets_cam-1",
            "nyc_streets_cam-2",
            "sf_streets_cam-1",
            "sf_streets_cam-2",
            "sf_streets_cam-4",
            "sf_streets_cam-5",
        ],
        "verify": "boxes",
        "label": "City - NYC + SF intersections",
        "classes": VEHICLES | VULNERABLE,
        "queries": [
            "pedestrian crossing close in front of a moving car",
            "car turning while people are crossing",
            "cyclist close to a moving vehicle",
            "vehicle running a red light at an intersection",
            "person stepping into the road between cars",
        ],
        "role": "road-safety analyst watching city intersection CCTV",
        "horizon": "the next 5-10 seconds",
    },
}

CITY_CAMERAS = MODES["city"]["cameras"]
STREET_CAMERAS = MODES["street"]["cameras"]

# Footage is SF/NYC + one street camera; the bus mode reads it as a London bus front camera
# would, but every sentence must still describe what is really in the clip.
BUS_HAZARD_TYPES: tuple[str, ...] = (
    "Cyclist on the nearside",
    "Pedestrian stepping out",
    "Vehicle cutting in",
    "Car pulling out",
    "Close following",
    "Blocked lane",
    "Turning across a crossing",
    "Scooter weaving",
)

MODES["bus"] = {
    "cameras": [*CITY_CAMERAS, *STREET_CAMERAS],
    "verify": "boxes",
    "label": "Bus - London bus safety view over city + street cameras",
    "classes": VEHICLES | VULNERABLE,
    "queries": [
        "cyclist riding close beside a large vehicle",
        "pedestrian stepping off the kerb into the road",
        "vehicle cutting in front of a bus or truck",
        "car pulling out from a side road or parking space",
        "person running across the road to a bus stop",
        "delivery van stopped in the traffic lane",
        "scooter or bike weaving between vehicles",
        "vehicles turning across a crossing with people on it",
    ],
    "role": "London bus safety analyst",
    "horizon": "the next 5-10 seconds",
    "prompt": "bus",
    "round_robin": True,
}

# --- candidate de-duplication (round-robin modes) ---
NEAR_DUP_SEGMENTS = 1  # segments of the same video within this many numbers are one event
NEAR_DUP_DESC_RATIO = 0.9  # difflib ratio above which two descriptions count as the same scene

# --- verify (closing-gap) thresholds, ported from pipeline/run.py ---
MIN_DET_CONF = 0.25  # boxes below this never reach the tracker
TRACK_ACTIVATION = 0.4  # trackers default 0.7 starves YOLO scores (brief-cv)
# New tracks are born only from "high" boxes, so this must not sit above TRACK_ACTIVATION
# (default 0.6 left a conf-0.5 car untracked for a whole clip; verified 2026-10-17).
HIGH_CONF_DET = 0.4
MIN_TRACK_FRAMES = 5
MIN_SHARED_FRAMES = 5
CLOSE_CL = 1.5  # a pair must end within ~1.5 car lengths (box diagonals)
VERIFY_MIN = 0.30  # closing score needed to call a candidate verified
GAP_SERIES_MAX_POINTS = 60

# --- watch ---
MIN_SIMILARITY = 0.15
PER_QUERY = 6
SEARCH_LLM_TOP_N = 1  # VSS rejects llm_top_n < 1

# --- models ---
COSMOS_NUM_FRAMES = 16  # NIM media_io_kwargs; fps and num_frames are mutually exclusive
FORESEE_MAX_TOKENS = 1024
JUDGE_MAX_TOKENS = 400
YES_NO_MAX_TOKENS = 16
RISK_MIN, RISK_MAX = 1, 5
RISK_SKIP_BELOW = 2  # risk 1 = nothing notable, not an incident
EVIDENCE_MAX_CHARS = 200
NEXT_DESC_MAX_CHARS = 1500
DESCRIPTION_MAX_CHARS = 600

# --- api limits ---
RUN_LIMIT_MAX = 10
ASK_MAX_CHARS = 500
DISCORD_MAX_CHARS = 1500
ALERTS_MAX = 50
