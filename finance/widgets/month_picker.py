from __future__ import annotations

from typing import Callable, List, Optional, Tuple

from ..qt import QHBoxLayout, QLabel, QPushButton, QWidget, Qt


MonthKey = Tuple[int, int]

_MONTH_NAMES = [
    "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
    "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר",
]

_ARROW_STYLE = (
    "QPushButton{background:#f4f2ec;border:none;border-radius:9px;color:#6b6f66;"
    "font-size:17px;font-weight:800;}"
    "QPushButton:hover{background:#e9e6db;}"
    "QPushButton:disabled{color:#cdcbc1;background:#f7f5ef;}"
)


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
        self._newer_btn = QPushButton("‹", self)
        self._older_btn = QPushButton("›", self)
        for b in (self._newer_btn, self._older_btn):
            b.setStyleSheet(_ARROW_STYLE)
            try:
                b.setFixedSize(28, 28)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
            except Exception:
                pass
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
