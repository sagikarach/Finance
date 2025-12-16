from __future__ import annotations

from typing import Callable, List, Optional, Tuple

from ..qt import QComboBox, QHBoxLayout, QLabel, QWidget, Qt


MonthKey = Tuple[int, int]


def _rtl_isolate(text: str) -> str:
    return f"\u2067{text}\u2069"


class MonthPickerWidget(QWidget):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        label_text: str = "בחר חודש:",
        on_changed: Optional[Callable[[MonthKey], None]] = None,
    ) -> None:
        super().__init__(parent)
        self._months: List[MonthKey] = []
        self._on_changed = on_changed

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._label = QLabel(label_text, self)
        self._label.setObjectName("Subtitle")
        try:
            self._label.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
        except Exception:
            align_right = getattr(Qt, "AlignRight", None)
            if align_right is not None:
                try:
                    self._label.setAlignment(align_right)
                except Exception:
                    pass

        self._combo = QComboBox(self)
        try:
            self._combo.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            view = self._combo.view()
            if view is not None:
                view.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            rtl = getattr(Qt, "RightToLeft", None)
            if rtl is not None:
                try:
                    self._combo.setLayoutDirection(rtl)
                    view = self._combo.view()
                    if view is not None:
                        view.setLayoutDirection(rtl)
                except Exception:
                    pass

        layout.addStretch(1)
        layout.addWidget(self._combo, 0)
        layout.addWidget(self._label, 0)
        layout.addStretch(1)

        self._combo.currentIndexChanged.connect(self._handle_index_changed)

    def set_on_changed(self, cb: Optional[Callable[[MonthKey], None]]) -> None:
        self._on_changed = cb

    def set_months(
        self, months: List[MonthKey], *, current: Optional[MonthKey] = None
    ) -> None:
        self._months = list(months)

        month_names = [
            "ינואר",
            "פברואר",
            "מרץ",
            "אפריל",
            "מאי",
            "יוני",
            "יולי",
            "אוגוסט",
            "ספטמבר",
            "אוקטובר",
            "נובמבר",
            "דצמבר",
        ]

        self._combo.blockSignals(True)
        self._combo.clear()
        for year, month in self._months:
            name = month_names[month - 1] if 1 <= month <= 12 else f"חודש {month}"
            self._combo.addItem(_rtl_isolate(f"{name} {year}"))
        if current is not None and current in self._months:
            self._combo.setCurrentIndex(self._months.index(current))
        else:
            self._combo.setCurrentIndex(0 if self._months else -1)
        self._combo.blockSignals(False)

    def current_month(self) -> Optional[MonthKey]:
        idx = self._combo.currentIndex()
        if 0 <= idx < len(self._months):
            return self._months[idx]
        return None

    def _handle_index_changed(self, index: int) -> None:
        if not (0 <= index < len(self._months)):
            return
        if self._on_changed is not None:
            self._on_changed(self._months[index])
