"""Step 1 on the VM: prove every API works and print the real JSON shapes (keys only, no secrets).

    python3 pipeline/probe.py            # saves fixtures/probe.json
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from vss import VSS, first

OUT = os.path.join(os.path.dirname(__file__), "..", "fixtures")


def shape(x, depth=0):
    if depth > 3:
        return "..."
    if isinstance(x, dict):
        return {k: shape(v, depth + 1) for k, v in list(x.items())[:25]}
    if isinstance(x, list):
        return [shape(x[0], depth + 1), f"len={len(x)}"] if x else []
    if isinstance(x, str):
        return x[:80]
    return x


def step(name, fn):
    t = time.time()
    try:
        r = fn()
        print(f"OK   {name} ({time.time()-t:.1f}s)")
        return r
    except Exception as e:
        print(f"FAIL {name}: {type(e).__name__}: {str(e)[:200]}")
        return None


v = VSS()
report = {}
step("login", v.login)
dash = step("dashboard", v.dashboard)
if dash:
    report["dashboard.overview"] = dash.get("overview")
    report["dashboard.objects"] = (dash.get("objects") or [])[:15]
    report["dashboard.metadata.camera_id"] = (dash.get("metadata") or {}).get("camera_id")
report["schema"] = shape(step("metadata schema", v.schema))
road = step("search road", lambda: v.search("truck changing lanes close to another vehicle", "i24_cam-1", top_k=5))
street = step("search street", lambda: v.search("car passing in front of houses", "neighborhood_cam-1", top_k=5))
report["search.shape"] = shape(road)
for name, res in (("road", road), ("street", street)):
    if res:
        json.dump(res, open(os.path.join(OUT, f"search_{name}.json"), "w"), indent=1)
hit = (road or {}).get("results", [{}])[0] if road and road.get("results") else {}
src = first(hit, ["source", "segment_source"])
parent = first(hit, ["original_video", "parent_video"])
if src:
    report["metadata.shape"] = shape(step("segment metadata", lambda: v.metadata(src)))
    report["detections.shape"] = shape(step("detections sidecar", lambda: v.detections(src)))
    clip = step("clip bytes", lambda: v.clip_bytes(src))
    if clip:
        print(f"     clip size {len(clip)//1024} KB")
        open(os.path.join(OUT, "sample_clip.mp4"), "wb").write(clip)
if parent:
    report["segments.shape"] = shape(step("segments of parent", lambda: v.segments(parent)))

try:
    from models import cosmos, yolo, llm_models, CFG
    if os.path.exists(os.path.join(OUT, "sample_clip.mp4")):
        clip = open(os.path.join(OUT, "sample_clip.mp4"), "rb").read()
        report["cosmos.reply"] = step("cosmos on clip", lambda: cosmos("Describe this clip in one sentence.", clip, 120))
        report["yolo.shape"] = shape(step("yolo on clip", lambda: yolo(clip)))
    if CFG.get("WANDB_API_KEY"):
        report["wandb.models"] = step("W&B models", llm_models)
except Exception as e:
    print("FAIL models import:", e)

json.dump(report, open(os.path.join(OUT, "probe.json"), "w"), indent=1, default=str)
print("\nSaved fixtures/probe.json - paste it to Claude.")
