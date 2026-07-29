from __future__ import annotations

from typing import Callable, List, Optional, Tuple

from ..qt import (
    QColor,
    QHBoxLayout,
    QLabel,
    QPainter,
    QPen,
    QPointF,
    QPushButton,
    QWidget,
    Qt,
)


MonthKey = Tuple[int, int]

_MONTH_NAMES = [
    "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
    "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר",
]

_ARROW_STYLE = (
    "QPushButton{background:#eceadf;border:none;border-radius:10px;}"
    "QPushButton:hover{background:#ddd9c9;}"
    "QPushButton:disabled{background:#f5f3ec;}"
)


class _ArrowButton(QPushButton):
    """A pill button that paints a chevron (‹ or ›) itself, so it never
    depends on a font having the glyph."""

    def __init__(self, direction: int, parent: Optional[QWidget] = None) -> None:
        super().__init__("", parent)
        self._dir = -1 if direction < 0 else 1  # -1 = points left, +1 = right
        self.setStyleSheet(_ARROW_STYLE)
        try:
            self.setFixedSize(30, 30)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        except Exception:
            pass

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)  # background from the stylesheet
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            color = QColor("#2c2f28") if self.isEnabled() else QColor("#c4c2b6")
            pen = QPen(color)
            pen.setWidthF(2.2)
            try:
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            except Exception:
                pass
            p.setPen(pen)
            cx, cy = self.width() / 2.0, self.height() / 2.0
            arm = 4.0
            # Tip points toward the button's direction (-1 left ‹, +1 right ›).
            tip_x = cx + self._dir * (arm / 2.0)
            base_x = cx - self._dir * (arm / 2.0)
            p.drawLine(QPointF(base_x, cy - arm), QPointF(tip_x, cy))
            p.drawLine(QPointF(tip_x, cy), QPointF(base_x, cy + arm))
            p.end()
        except Exception:
            pass


class MonthPickerWidget(QWidget):
    """Pill month selector with prev/next arrows: ‹ יולי 2026 ›."""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        label_text: str = "",  # kept for API compatibility (unused)
        on_changed: Optional[Callable[[MonthKey], None]] = None,
    ) -> None:
        super().__init__(parent)
        self._months: List[MonthKey] = []
        self._index: int = -1
        self._on_changed = on_changed

        self.setObjectName("MonthPicker")
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        except Exception:
            pass
        self.setStyleSheet(
            "QWidget#MonthPicker{background:#ffffff;border:1px solid #ecece2;"
            "border-radius:14px;}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 5, 6, 5)
        layout.setSpacing(8)

        # Newer months are to the left (‹), older to the right (›) — natural
        # for a list sorted newest-first.
        self._newer_btn = _ArrowButton(-1, self)
        self._older_btn = _ArrowButton(+1, self)
        self._newer_btn.clicked.connect(lambda: self._step(-1))
        self._older_btn.clicked.connect(lambda: self._step(+1))

        self._label = QLabel("", self)
        self._label.setStyleSheet(
            "font-size:15px;font-weight:800;color:#1e1e22;background:transparent;"
        )
        try:
            self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._label.setMinimumWidth(118)
        except Exception:
            pass

        layout.addWidget(self._newer_btn)
        layout.addWidget(self._label, 1)
        layout.addWidget(self._older_btn)

    def set_on_changed(self, cb: Optional[Callable[[MonthKey], None]]) -> None:
        self._on_changed = cb

    def set_months(
        self, months: List[MonthKey], *, current: Optional[MonthKey] = None
    ) -> None:
        self._months = list(months)
        if current is not None and current in self._months:
            self._index = self._months.index(current)
        else:
            self._index = 0 if self._months else -1
        self._sync(fire=False)

    def current_month(self) -> Optional[MonthKey]:
        if 0 <= self._index < len(self._months):
            return self._months[self._index]
        return None

    def _label_for(self, key: MonthKey) -> str:
        year, month = key
        name = _MONTH_NAMES[month - 1] if 1 <= month <= 12 else f"חודש {month}"
        return f"⁧{name} {year}⁩"

    def _sync(self, *, fire: bool) -> None:
        n = len(self._months)
        if not (0 <= self._index < n):
            self._label.setText("")
            self._newer_btn.setEnabled(False)
            self._older_btn.setEnabled(False)
            return
        self._label.setText(self._label_for(self._months[self._index]))
        self._newer_btn.setEnabled(self._index > 0)
        self._older_btn.setEnabled(self._index < n - 1)
        if fire and self._on_changed is not None:
            self._on_changed(self._months[self._index])

    def _step(self, delta: int) -> None:
        new = self._index + delta
        if not (0 <= new < len(self._months)) or new == self._index:
            return
        self._index = new
        self._sync(fire=True)
