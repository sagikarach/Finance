from __future__ import annotations

from typing import List, Optional, Tuple

from ..qt import QHBoxLayout, QPushButton, QWidget, Signal


class TimeRangeBar(QWidget):

    range_changed = Signal(int)

    PRESETS: List[Tuple[str, int]] = [
        ("3M", 3),
        ("6M", 6),
        ("1Y", 12),
        ("2Y", 24),
        ("הכל", 0),
        ("תחזית", -1),
    ]

    # Sentinel value that means: show 3 recent months + AI projection
    FORECAST_VALUE = -1

    _STYLE = """
        QPushButton#RangeBtn {
            background: transparent;
            color: #6b7280;
            border: 1px solid #d1d5db;
            border-radius: 10px;
            padding: 2px 10px;
            font-size: 12px;
            min-width: 32px;
            max-height: 24px;
        }
        QPushButton#RangeBtn:hover {
            background: #f3f4f6;
            border-color: #9ca3af;
        }
        QPushButton#RangeBtn:checked {
            background: #2563eb;
            color: #ffffff;
            border-color: #2563eb;
            font-weight: 600;
        }
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        default_months: int = 0,
    ) -> None:
        super().__init__(parent)
        self._selected = default_months
        self._buttons: dict[int, QPushButton] = {}

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 2, 0, 2)
        row.setSpacing(4)
        row.addStretch()

        for label, months in self.PRESETS:
            btn = QPushButton(label, self)
            btn.setObjectName("RangeBtn")
            try:
                btn.setCheckable(True)
                btn.setChecked(months == default_months)
            except Exception:
                pass
            btn.clicked.connect(lambda _c, m=months: self._select(m))
            row.addWidget(btn)
            self._buttons[months] = btn

    def _select(self, months: int) -> None:
        if months == self._selected:
            # Re-check the button in case Qt unchecked it on click
            try:
                self._buttons[months].setChecked(True)
            except Exception:
                pass
            return
        self._selected = months
        for m, btn in self._buttons.items():
            try:
                btn.setChecked(m == months)
            except Exception:
                pass
        self.range_changed.emit(months)

    def selected_months(self) -> int:
        return self._selected
