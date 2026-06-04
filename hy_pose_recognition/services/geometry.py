from __future__ import annotations

import math


def point(x: float, y: float, visibility: float = 0.94, z: float = 0.0) -> dict[str, float]:
    return {
        "x": round(max(0.0, min(1.0, x)), 4),
        "y": round(max(0.0, min(1.0, y)), 4),
        "z": round(z, 4),
        "visibility": round(visibility, 3),
    }


def angle_between(a: dict[str, float], b: dict[str, float], c: dict[str, float]) -> float:
    bax = a["x"] - b["x"]
    bay = a["y"] - b["y"]
    bcx = c["x"] - b["x"]
    bcy = c["y"] - b["y"]
    mag_a = math.hypot(bax, bay)
    mag_c = math.hypot(bcx, bcy)
    if mag_a == 0 or mag_c == 0:
        return 0.0
    cosine = max(-1.0, min(1.0, (bax * bcx + bay * bcy) / (mag_a * mag_c)))
    return round(math.degrees(math.acos(cosine)), 1)


def segment_angle(a: dict[str, float], b: dict[str, float]) -> float:
    return round(math.degrees(math.atan2(b["y"] - a["y"], b["x"] - a["x"])), 1)
