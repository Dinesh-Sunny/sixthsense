"""SixthSense engine: watch -> verify -> foresee -> self-check -> store.

    python3 pipeline/run.py --mode road --limit 12
    python3 pipeline/run.py --mode street --limit 12
Writes app/incidents.json and app/metrics.json (merged by mode). Every step is a Weave op.
Flags (env): VERIFY_MODE=boxes|cosmos   FORESEE_VIA=direct|text
"""
import argparse, datetime, json, math, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from vss import VSS, first
from models import cosmos, llm, op, parse_json, yolo
from modes import MODES

ROOT = os.path.join(os.path.dirname(__file__), "..")
APP = os.path.join(ROOT, "app")
VEHICLES = {"car", "truck", "bus", "motorcycle", "vehicle", "van", "forklift"}
v = VSS()


def seg_start(d):
    return float(first(d, ["start_sec", "segment_start_sec", "start_time", "start", "best_match_start_sec"], 0) or 0)


def seg_end(d):
    return float(first(d, ["end_sec", "segment_end_sec", "end_time", "end", "best_match_end_sec"], seg_start(d) + 5) or 0)


def desc(d):
    return first(d, ["reasoning_content", "description", "reasoning", "caption"], "") or ""


# ---------- 1 WATCH ----------
@op
def watch(mode: str, per_query: int) -> list:
    cfg, seen, out = MODES[mode], set(), []
    cams = cfg["camera"] if isinstance(cfg["camera"], list) else [cfg["camera"]]
    for q in cfg["queries"]:
      for cam in cams:
        try:
            res = v.search(q, cam, top_k=per_query, min_similarity=float(os.environ.get("MIN_SIM", "0.15")))
        except Exception as e:
            print("search failed:", q, e)
            continue
        for hit in res.get("results", []):
            src = first(hit, ["source"])
            if src and src not in seen:
                seen.add(src)
                hit["_query"] = q
                out.append(hit)
    out.sort(key=lambda h: -float(first(h, ["similarity_score", "score"], 0) or 0))
    print(f"watch: {len(out)} candidate segments")
    return out


# ---------- 2 VERIFY ----------
def _iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def _tracks(frames, step=2, min_conf=0.25, classes=None):
    """Tracking-lite: link vehicle boxes frame to frame by best IoU. Returns {track_id: [(t, box), ...]}."""
    tracks, last, nxt = {}, {}, 0
    for fr in frames[::step]:
        t = float(fr.get("time_sec", fr.get("frame_index", 0)))
        dets = [d["bbox"] for d in fr.get("detections", [])
                if str(d.get("label", "")).lower() in (classes or VEHICLES) and float(d.get("confidence", 1)) >= min_conf]
        new_last, used = {}, set()
        for box in dets:
            best, bid = 0.15, None
            for tid, pb in last.items():
                if tid in used:
                    continue
                o = _iou(box, pb)
                if o > best:
                    best, bid = o, tid
            if bid is None:
                bid, nxt = nxt, nxt + 1
            used.add(bid)
            tracks.setdefault(bid, []).append((t, box))
            new_last[bid] = box
        last = new_last
    return tracks


def closing_gap(det, classes=None):
    """Best pair of tracked vehicles that close in: distance measured in car lengths (box diagonals)."""
    frames = (det or {}).get("frames") or (det or {}).get("perception_json", {}).get("frames") or []
    if not frames:
        return None
    tr = {k: dict(v) for k, v in _tracks(frames, classes=classes).items() if len(v) >= 5}
    ids, best = list(tr), (0.0, None)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = tr[ids[i]], tr[ids[j]]
            ts = sorted(set(a) & set(b))
            if len(ts) < 5:
                continue
            dist = []
            for t in ts:
                ba, bb = a[t], b[t]
                ca = ((ba[0] + ba[2]) / 2, (ba[1] + ba[3]) / 2); cb = ((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)
                size = (math.hypot(ba[2] - ba[0], ba[3] - ba[1]) + math.hypot(bb[2] - bb[0], bb[3] - bb[1])) / 2
                dist.append(math.hypot(ca[0] - cb[0], ca[1] - cb[1]) / max(size, 1.0))
            d0, dmin = sum(dist[:2]) / 2, min(dist)
            k = dist.index(dmin)
            if d0 <= 0 or dmin > 1.5:  # only pairs that end up within ~1.5 car lengths
                continue
            score = (d0 - dmin) / d0
            if score > best[0]:
                best = (score, f"two vehicles closed from {d0:.1f} to {dmin:.1f} car lengths in {ts[k]-ts[0]:.1f}s")
    if best[1] is None:
        return 0.0, f"{len(tr)} vehicles tracked, no pair closing within 1.5 car lengths"
    return round(best[0], 2), best[1]


@op
def verify(hit: dict, mode: str) -> dict:
    src = hit["source"]
    if os.environ.get("VERIFY_MODE", "boxes") == "boxes" and MODES[mode].get("verify") == "boxes":
        det = None
        try:
            det = v.detections(src)
        except Exception as e:
            print("detections failed", e)
        cg = closing_gap(det, MODES[mode].get("classes")) if det else None
        if cg is None and os.environ.get("YOLO_FALLBACK", "1") == "1":
            try:
                cg = closing_gap(yolo(v.clip_bytes(src)), MODES[mode].get("classes"))
            except Exception as e:
                print("yolo failed", e)
        if cg is not None:
            score, note = cg
            return {"verified": score >= float(os.environ.get("VERIFY_MIN", "0.30")), "verify_score": round(score, 2), "verify_note": note, "verify_by": "yolo boxes"}
    # fallback / street: strict Cosmos yes-no, asked on the clip
    q = ("Answer only yes or no. Are two vehicles within about one car length of each other and getting closer?"
         if MODES[mode].get("verify") == "boxes" else
         "Answer only yes or no. Is there a vehicle or person here behaving unusually for a quiet residential street?")
    try:
        ans = cosmos(q, v.clip_bytes(src), 10).strip().lower()
    except Exception as e:
        ans = f"error {e}"
    ok = ans.startswith("yes")
    return {"verified": ok, "verify_score": 1.0 if ok else 0.0, "verify_note": f"Cosmos check: {ans[:20]}", "verify_by": "cosmos"}


# ---------- 3 FORESEE ----------
FORESEE = """You are a {role}. Look only at what is visible in this clip.
Answer in JSON only:
{{"type": "<2-4 word label, e.g. close cut-in>",
 "what_happens": "<one sentence>",
 "what_next": "<the most likely thing in {horizon}>",
 "why": "<the visible cause>",
 "fix": "<one practical change that would prevent it>",
 "risk": <integer 1-5>}}
If nothing risky is happening, set risk to 1 and what_next to "nothing notable".
Never invent people, vehicles or events you cannot see."""


@op
def foresee(hit: dict, mode: str) -> dict:
    cfg = MODES[mode]
    prompt = FORESEE.format(role=cfg["role"], horizon=cfg["horizon"])
    if os.environ.get("FORESEE_VIA", "direct") == "direct":
        reply = cosmos(prompt, v.clip_bytes(hit["source"]))
    else:  # text-only: reason over the stored description
        reply = llm(prompt + "\n\nClip description: " + desc(hit))
    out = parse_json(reply)
    out["risk"] = int(max(1, min(5, int(out.get("risk", 1) or 1))))
    return out


# ---------- 4 SELF-CHECK ----------
JUDGE = """Prediction: "{what_next}"
What the camera recorded next: "{next_desc}"
Did the prediction come true? Reply JSON only: {{"came_true": "yes|partly|no", "evidence": "<one short line from the next description>"}}
Be strict: "yes" only if the same kind of vehicles/people and the same kind of event appear."""


def _seg_list(parent):
    r = v.segments(parent)
    lst = r if isinstance(r, list) else first(r, ["segments", "results", "items", "data"], []) or []
    return sorted(lst, key=lambda s: (float(first(s, ["segment_number", "segment_index"], 0) or 0), seg_start(s)))


@op
def selfcheck(hit: dict, what_next: str) -> dict:
    parent = first(hit, ["original_video"])
    if not parent or "nothing notable" in (what_next or "").lower():
        return {"came_true": "unknown", "came_true_evidence": ""}
    try:
        segs = _seg_list(parent)
    except Exception as e:
        return {"came_true": "unknown", "came_true_evidence": f"no segments: {e}"}
    idx = next((i for i, s in enumerate(segs) if first(s, ["source"]) == hit["source"]), None)
    if idx is None or idx + 1 >= len(segs):
        return {"came_true": "unknown", "came_true_evidence": "no next segment"}
    nxt = segs[idx + 1]
    nd = desc(nxt)
    if not nd:
        try:
            nd = desc(v.metadata(nxt["source"]))
        except Exception:
            nd = ""
    j = parse_json(llm(JUDGE.format(what_next=what_next, next_desc=nd[:1500])))
    ct = str(j.get("came_true", "unknown")).lower()
    return {"came_true": ct if ct in ("yes", "partly", "no") else "unknown",
            "came_true_evidence": str(j.get("evidence", ""))[:200], "next_source": nxt.get("source")}


# ---------- 5 STORE ----------
def load(name, default):
    p = os.path.join(APP, name)
    return json.load(open(p)) if os.path.exists(p) else default


def save(name, data):
    json.dump(data, open(os.path.join(APP, name), "w"), indent=1)


@op
def run(mode: str, limit: int, per_query: int) -> dict:
    cands = watch(mode, per_query)[:limit]
    incidents = []
    for n, hit in enumerate(cands, 1):
        t = time.time()
        ver = verify(hit, mode)
        if not ver["verified"]:
            print(f"[{n}/{len(cands)}] rejected ({ver['verify_note']})")
            continue
        fs = foresee(hit, mode)
        sc = selfcheck(hit, fs.get("what_next", ""))
        cam = first(hit, ["camera_id"], MODES[mode]["camera"])
        incidents.append({
            "id": f"{cam}-{abs(hash(hit['source'])) % 10**8}", "mode": mode, "camera_id": cam,
            "source": hit["source"], "original_video": first(hit, ["original_video"]),
            "start_s": seg_start(hit), "end_s": seg_end(hit), "query": hit.get("_query"),
            "similarity": first(hit, ["similarity_score"]), "description": desc(hit)[:600],
            **ver, **{k: fs.get(k, "") for k in ("type", "what_happens", "what_next", "why", "fix")},
            "risk": fs.get("risk", 1), **sc, "fixture": False,
        })
        print(f"[{n}/{len(cands)}] risk {fs.get('risk')} came_true={sc['came_true']} ({time.time()-t:.0f}s)")
    checked = [i for i in incidents if i["came_true"] in ("yes", "partly", "no")]
    yes = sum(i["came_true"] == "yes" for i in checked)
    partly = sum(i["came_true"] == "partly" for i in checked)
    metrics = {"mode": mode, "candidates": len(cands), "verified": len(incidents), "checked": len(checked),
               "came_true_yes": yes, "came_true_partly": partly,
               "accuracy": round((yes + 0.5 * partly) / len(checked), 3) if checked else None,
               "generated_at": datetime.datetime.now().isoformat(timespec="seconds")}
    allinc = [i for i in load("incidents.json", []) if i.get("mode") != mode and not i.get("fixture")]
    save("incidents.json", allinc + incidents)
    allm = {m["mode"]: m for m in load("metrics.json", []) if not m.get("fixture")}
    allm[mode] = metrics
    save("metrics.json", list(allm.values()))
    print(json.dumps(metrics, indent=1))
    return metrics


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="road", choices=list(MODES))
    ap.add_argument("--dry", action="store_true", help="verify only, print scores")
    ap.add_argument("--limit", type=int, default=12)
    ap.add_argument("--per-query", type=int, default=6)
    a = ap.parse_args()
    run(a.mode, a.limit, a.per_query)
