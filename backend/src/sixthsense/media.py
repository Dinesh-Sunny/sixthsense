"""Poster stills for clips: decode one frame with OpenCV (headless) and encode a JPEG.

Sanctioned cv2 importer alongside tracking.py. Decoding is CPU-bound and holds a whole clip in
memory, so it runs in a thread under a small semaphore, and results sit in an in-memory LRU.
"""

import asyncio
import os
import tempfile
from collections import OrderedDict

import cv2

from .modes import POSTER_CACHE_ITEMS, POSTER_CONCURRENCY, POSTER_QUALITY, POSTER_WIDTH


def poster_jpeg(video: bytes, t: float, width: int = POSTER_WIDTH, quality: int = POSTER_QUALITY) -> bytes | None:
    """JPEG of the frame at `t` seconds (first frame if the clip is shorter), or None if unreadable."""
    if not video:
        return None
    # VideoCapture reads from a path, not bytes; the temp file lives only for this call.
    fd, path = tempfile.mkstemp(suffix=".mp4")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(video)
        cap = cv2.VideoCapture(path)
        try:
            if not cap.isOpened():
                return None
            cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t) * 1000)
            ok, frame = cap.read()
            if not ok:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, frame = cap.read()
            if not ok or frame is None:
                return None
        finally:
            cap.release()
    finally:
        os.unlink(path)
    h, w = frame.shape[:2]
    if w != width:
        size = (width, max(1, round(h * width / w)))
        frame = cv2.resize(frame, size, interpolation=cv2.INTER_AREA if w > width else cv2.INTER_LINEAR)
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buf.tobytes() if ok else None


class PosterCache:
    def __init__(self, max_items: int = POSTER_CACHE_ITEMS, concurrency: int = POSTER_CONCURRENCY) -> None:
        self._items: OrderedDict[tuple[str, float], bytes] = OrderedDict()
        self._max = max_items
        self._sem = asyncio.Semaphore(concurrency)

    def get(self, key: tuple[str, float]) -> bytes | None:
        hit = self._items.get(key)
        if hit is not None:
            self._items.move_to_end(key)
        return hit

    def put(self, key: tuple[str, float], jpeg: bytes) -> None:
        self._items[key] = jpeg
        self._items.move_to_end(key)
        while len(self._items) > self._max:
            self._items.popitem(last=False)

    async def render(self, video: bytes, t: float) -> bytes | None:
        async with self._sem:
            return await asyncio.to_thread(poster_jpeg, video, t)
