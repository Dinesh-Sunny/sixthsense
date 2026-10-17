"""One engine, mode = config. Edit queries here, not in code."""
MODES = {
    "road": {
        "camera": "i24_cam-1",
        "verify": "boxes",
        "label": "Road - Nashville I-24 highway",
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
        "camera": "neighborhood_cam-1",
        "verify": "cosmos",
        "label": "Street - neighbourhood camera, 2 days",
        "days": ["2026-09-01", "2026-09-02"],
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
        "camera": ["nyc_streets_cam-1", "nyc_streets_cam-2", "sf_streets_cam-1", "sf_streets_cam-2", "sf_streets_cam-4", "sf_streets_cam-5"],
        "label": "City - NYC + SF intersections",
        "verify": "boxes",
        "classes": {"person", "car", "truck", "bus", "motorcycle", "bicycle"},
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
