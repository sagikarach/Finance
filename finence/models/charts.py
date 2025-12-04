from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from .accounts import MoneySnapshot, parse_iso_date


MonthKey = Tuple[int, int]  # (year, month)


@dataclass(frozen=True)
class MonthAxis:
    keys: List[MonthKey]

    @property
    def month_to_index(self) -> Dict[MonthKey, int]:
        return {key: idx for idx, key in enumerate(self.keys)}


def build_month_axis_from_histories(
    histories: Iterable[Iterable[MoneySnapshot]],
) -> MonthAxis:
    keys: List[MonthKey] = []
    seen: set[MonthKey] = set()
    for history in histories:
        for snap in history:
            dt = parse_iso_date(str(snap.date))
            key = (dt.year, dt.month)
            if key not in seen:
                seen.add(key)
                keys.append(key)

    if not keys:
        keys = [(0, 1)]

    keys.sort(key=lambda k: (k[0], k[1]))
    return MonthAxis(keys=keys)


def build_month_axis_from_history(history: Iterable[MoneySnapshot]) -> MonthAxis:
    return build_month_axis_from_histories([history])


def latest_snapshots_by_month(
    history: Iterable[MoneySnapshot],
) -> Dict[MonthKey, MoneySnapshot]:
    latest: Dict[MonthKey, MoneySnapshot] = {}
    for snap in history:
        dt = parse_iso_date(str(snap.date))
        key = (dt.year, dt.month)
        existing = latest.get(key)
        if existing is None or parse_iso_date(str(existing.date)) < dt:
            latest[key] = snap
    return latest


def build_base_values(
    axis: MonthAxis,
    latest_by_month: Dict[MonthKey, MoneySnapshot],
    fallback_amount: float,
) -> Tuple[List[float], float]:
    base_values: List[float] = []
    last_amount = 0.0
    max_amount = 0.0

    if not latest_by_month:
        last_amount = float(fallback_amount)
        for _key in axis.keys:
            base_values.append(last_amount)
            if last_amount > max_amount:
                max_amount = last_amount
    else:
        for key in axis.keys:
            snap_opt = latest_by_month.get(key)
            if snap_opt is not None:
                last_amount = float(snap_opt.amount)
            base_values.append(last_amount)
            if last_amount > max_amount:
                max_amount = last_amount

    return base_values, max_amount


def catmull_rom_spline_samples(
    base_values: List[float],
    steps_per_segment: int = 16,
) -> List[Tuple[float, float]]:
    n = len(base_values)
    if n == 0:
        return []
    if n == 1:
        return [(0.0, float(base_values[0]))]

    smooth_knots: List[float] = list(base_values)
    if n >= 3:
        tmp = list(smooth_knots)
        for i_k in range(1, n - 1):
            tmp[i_k] = (
                0.25 * smooth_knots[i_k - 1]
                + 0.5 * smooth_knots[i_k]
                + 0.25 * smooth_knots[i_k + 1]
            )
        smooth_knots = tmp

    min_y_val = min(base_values)
    max_y_val = max(base_values) if base_values else 0.0

    def sample_segment(i_seg: int, t: float) -> float:
        i0 = max(0, min(n - 1, i_seg - 1))
        i1 = max(0, min(n - 1, i_seg))
        i2 = max(0, min(n - 1, i_seg + 1))
        i3 = max(0, min(n - 1, i_seg + 2))
        p0 = smooth_knots[i0]
        p1 = smooth_knots[i1]
        p2 = smooth_knots[i2]
        p3 = smooth_knots[i3]
        t2 = t * t
        t3 = t2 * t
        val = 0.5 * (
            (2.0 * p1)
            + (-p0 + p2) * t
            + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
            + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3
        )
        if val < min_y_val:
            val = min_y_val
        if val > max_y_val:
            val = max_y_val
        return val

    samples: List[Tuple[float, float]] = []
    samples.append((0.0, smooth_knots[0]))
    for i_seg in range(n - 1):
        for j in range(1, steps_per_segment + 1):
            t = float(j) / float(steps_per_segment)
            x_val = float(i_seg) + t
            y_val = sample_segment(i_seg, t)
            samples.append((x_val, y_val))

    return samples
