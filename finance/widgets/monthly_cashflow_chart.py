from __future__ import annotations

from typing import List, Optional

from ..qt import QWidget, QPainter, QColor, QPen, QFont, Qt, QApplication
from ..utils.formatting import format_currency


class MonthlyCashflowChart(QWidget):
    """Rounded pill bars for the monthly cash-flow (matches the mobile design):
    a light track per month with an ink fill (clay when the month is negative),
    the most recent month highlighted with a value pill above it."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._values: List[float] = []
        self._labels: List[str] = []
        self._hover: int = -1  # bar under the mouse (-1 = none)
        try:
            self.setMinimumHeight(150)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setMouseTracking(True)
        except Exception:
            pass

    def set_data(self, values: List[float], labels: List[str]) -> None:
        self._values = [float(v) for v in values]
        self._labels = [str(x) for x in labels]
        self._hover = -1
        self.update()

    def _bar_at(self, x: float) -> int:
        n = len(self._values)
        if n == 0 or self.width() <= 0:
            return -1
        idx = int(x / (self.width() / float(n)))
        return idx if 0 <= idx < n else -1

    def mouseMoveEvent(self, event) -> None:
        try:
            x = event.position().x()
        except Exception:
            x = event.x()
        idx = self._bar_at(x)
        if idx != self._hover:
            self._hover = idx
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        if self._hover != -1:
            self._hover = -1
            self.update()
        super().leaveEvent(event)

    def _is_dark(self) -> bool:
        app = QApplication.instance()
        if app is None:
            return False
        try:
            return str(app.property("theme") or "light") == "dark"
        except Exception:
            return False

    def paintEvent(self, event) -> None:  # noqa: D401
        if not self._values:
            return
        dark = self._is_dark()
        track_c = QColor("#273043" if dark else "#efede4")
        pos_c = QColor("#e5e7eb" if dark else "#1e1e22")
        neg_c = QColor("#e9a491")
        hi_c = QColor("#b9b6f0")
        muted_c = QColor("#94a3b8" if dark else "#8b8e86")
        tip_bg = QColor("#0b1220" if dark else "#1e1e22")

        p = QPainter(self)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        except Exception:
            pass

        w = int(self.width())
        h = int(self.height())
        n = len(self._values)
        if n == 0:
            return

        label_h = 22
        top_pad = 28  # room for the value pill
        chart_bottom = h - label_h
        chart_h = max(1, chart_bottom - top_pad)
        bar_w = 20
        radius = 10
        slot = w / float(n)
        maxv = max((abs(v) for v in self._values), default=1.0) or 1.0
        hover = self._hover  # highlight only the bar the mouse is over

        lab_font = QFont(self.font())
        lab_font.setPixelSize(11)

        no_pen = Qt.PenStyle.NoPen
        for i, v in enumerate(self._values):
            cx = slot * i + slot / 2.0
            x = int(cx - bar_w / 2.0)

            p.setPen(no_pen)
            p.setBrush(track_c)
            p.drawRoundedRect(x, top_pad, bar_w, chart_h, radius, radius)

            frac = abs(v) / maxv
            frac = 0.04 if frac < 0.04 else (1.0 if frac > 1.0 else frac)
            fill_h = int(chart_h * frac)
            fill_y = chart_bottom - fill_h
            if i == hover:
                p.setBrush(hi_c)
            elif v >= 0:
                p.setBrush(pos_c)
            else:
                p.setBrush(neg_c)
            p.drawRoundedRect(x, fill_y, bar_w, fill_h, radius, radius)

            p.setPen(QPen(muted_c))
            p.setFont(lab_font)
            lab = self._labels[i] if i < len(self._labels) else ""
            p.drawText(
                int(slot * i), chart_bottom + 2, int(slot), label_h,
                int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter),
                lab,
            )

            if i == hover:
                sign = "+" if v >= 0 else "-"
                txt = f"{sign}{format_currency(abs(v), use_compact=True)}"
                tip_font = QFont(self.font())
                tip_font.setPixelSize(11)
                tip_font.setBold(True)
                p.setFont(tip_font)
                tw = p.fontMetrics().horizontalAdvance(txt) + 16
                th = 20
                tx = int(cx - tw / 2.0)
                if tx < 0:
                    tx = 0
                if tx + tw > w:
                    tx = w - tw
                ty = fill_y - th - 6
                if ty < 0:
                    ty = 0
                p.setPen(no_pen)
                p.setBrush(tip_bg)
                p.drawRoundedRect(tx, ty, tw, th, 8, 8)
                p.setPen(QPen(QColor("#ffffff")))
                p.drawText(
                    tx, ty, tw, th,
                    int(Qt.AlignmentFlag.AlignCenter), txt,
                )
        p.end()
