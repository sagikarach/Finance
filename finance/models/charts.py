from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple
from datetime import datetime, timedelta

from .accounts import MoneySnapshot, parse_iso_date
from ..utils.safe import PARSE_ERRORS


MonthKey = Tuple[int, int]


@dataclass(frozen=True)
class MonthAxis:
    keys: List[MonthKey]

    @property
    def month_to_index(self) -> Dict[MonthKey, int]:
        return {key: idx for idx, key in enumerate(self.keys)}


def latest_snapshots_by_month_with_axis(
    history: Iterable[MoneySnapshot],
) -> tuple[MonthAxis, Dict[MonthKey, MoneySnapshot]]:
    """
    One-pass helper for charts:
    - builds the set of month keys
    - tracks the latest snapshot per month
    This avoids scanning + parsing the same history multiple times.
    """
    keys_seen: set[MonthKey] = set()
    latest: Dict[MonthKey, MoneySnapshot] = {}
    latest_dt_by_key: Dict[MonthKey, datetime] = {}

    for snap in history:
        try:
            dt = parse_iso_date(str(snap.date))
        except PARSE_ERRORS:
            continue
        if dt == datetime.min:
            continue
        key = (dt.year, dt.month)
        keys_seen.add(key)
        prev_dt = latest_dt_by_key.get(key)
        if prev_dt is None or prev_dt < dt:
            latest_dt_by_key[key] = dt
            latest[key] = snap

    keys = sorted(keys_seen, key=lambda k: (k[0], k[1]))
    if not keys:
        now = datetime.now()
        keys = [(int(now.year), int(now.month))]
    return MonthAxis(keys=keys), latest


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


def cumulative_daily_series(points: Iterable[Any]) -> Tuple[List[str], List[float]]:
    """Gap-filled cumulative running total of dated expense ``points`` (each with
    ``.date_iso`` and ``.amount``): walk every calendar day from the first to the
    last point, summing that day's amounts into a rising total. Returns parallel
    ``(labels, values)`` — labels are ``dd/mm/yy``. Empty lists when there are no
    parseable dates."""
    pts = list(points or [])
    if not pts:
        return [], []
    try:
        pts = sorted(pts, key=lambda p: parse_iso_date(p.date_iso))
    except PARSE_ERRORS:
        pass
    try:
        start_dt = parse_iso_date(pts[0].date_iso).date()
        end_dt = parse_iso_date(pts[-1].date_iso).date()
    except PARSE_ERRORS:
        return [], []

    day_sum: Dict[str, float] = {}
    for p in pts:
        try:
            d = parse_iso_date(p.date_iso).date().isoformat()
        except PARSE_ERRORS:
            continue
        day_sum[d] = float(day_sum.get(d, 0.0) + float(p.amount))

    labels: List[str] = []
    values: List[float] = []
    cum = 0.0
    dcur = start_dt
    while dcur <= end_dt:
        cum += float(day_sum.get(dcur.isoformat(), 0.0))
        labels.append(dcur.strftime("%d/%m/%y"))
        values.append(float(cum))
        dcur = dcur + timedelta(days=1)
    return labels, values
