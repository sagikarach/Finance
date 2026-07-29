from __future__ import annotations

from typing import Callable, List, Optional

from ..qt import QHBoxLayout, QLabel, QWidget, Qt

from .month_picker import _ArrowButton


class YearPickerWidget(QWidget):
    """Pill year selector with prev/next arrows: ‹ 2026 ›.

    Mirrors :class:`MonthPickerWidget`. The ``label_text`` / ``centered`` /
    ``label_on_right`` arguments are kept for API compatibility (the pill has
    no separate caption), so existing call sites don't need to change.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        label_text: str = "",  # kept for API compatibility (unused)
        on_changed: Optional[Callable[[int], None]] = None,
        centered: bool = True,  # kept for API compatibility
        label_on_right: bool = True,  # kept for API compatibility
    ) -> None:
        super().__init__(parent)
        self._years: List[int] = []
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

        # Left arrow (‹) steps to older years, right arrow (›) to newer.
        # (years are sorted newest-first, so older = higher index.)
        self._left_btn = _ArrowButton(-1, self)
        self._right_btn = _ArrowButton(+1, self)
        self._left_btn.clicked.connect(lambda: self._step(+1))
        self._right_btn.clicked.connect(lambda: self._step(-1))

        self._label = QLabel("", self)
        self._label.setStyleSheet(
            "font-size:15px;font-weight:800;color:#1e1e22;background:transparent;"
        )
        try:
            self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._label.setMinimumWidth(84)
        except Exception:
            pass

        layout.addWidget(self._left_btn)
        layout.addWidget(self._label, 1)
        layout.addWidget(self._right_btn)

    def set_on_changed(self, cb: Optional[Callable[[int], None]]) -> None:
        self._on_changed = cb

    def set_years(self, years: List[int], *, current: Optional[int] = None) -> None:
        self._years = list(years)
        if current is not None and current in self._years:
            self._index = self._years.index(current)
        else:
            self._index = 0 if self._years else -1
        self._sync(fire=False)

    def current_year(self) -> Optional[int]:
        if 0 <= self._index < len(self._years):
            return self._years[self._index]
        return None

    def _sync(self, *, fire: bool) -> None:
        n = len(self._years)
        if not (0 <= self._index < n):
            self._label.setText("")
            self._left_btn.setEnabled(False)
            self._right_btn.setEnabled(False)
            return
        self._label.setText(f"⁧{self._years[self._index]}⁩")
        # Left goes older (index+1), right goes newer (index-1).
        self._left_btn.setEnabled(self._index < n - 1)
        self._right_btn.setEnabled(self._index > 0)
        if fire and self._on_changed is not None:
            self._on_changed(self._years[self._index])

    def _step(self, delta: int) -> None:
        new = self._index + delta
        if not (0 <= new < len(self._years)) or new == self._index:
            return
        self._index = new
        self._sync(fire=True)
