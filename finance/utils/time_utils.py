from __future__ import annotations


def now_ts() -> float:
    return float(__import__("time").time())
