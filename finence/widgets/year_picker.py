from __future__ import annotations

from typing import Callable, List, Optional

from ..qt import QComboBox, QHBoxLayout, QLabel, QWidget, Qt


def _rtl_isolate(text: str) -> str:
    return f"\u2067{text}\u2069"


class YearPickerWidget(QWidget):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        label_text: str = "בחר שנה:",
        on_changed: Optional[Callable[[int], None]] = None,
        centered: bool = True,
        label_on_right: bool = True,
    ) -> None:
        super().__init__(parent)
        self._years: List[int] = []
        self._on_changed = on_changed

        if label_on_right:
            try:
                self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            except Exception:
                ltr = getattr(Qt, "LeftToRight", None)
                if ltr is not None:
                    try:
                        self.setLayoutDirection(ltr)
                    except Exception:
                        pass

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12 if centered else 8)

        label = QLabel(label_text, self)
        label.setObjectName("Subtitle")
        try:
            label.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
        except Exception:
            align_right = getattr(Qt, "AlignRight", None)
            if align_right is not None:
                try:
                    label.setAlignment(align_right)
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

        if centered:
            layout.addStretch(1)
        layout.addWidget(self._combo, 0)
        layout.addWidget(label, 0)
        if centered:
            layout.addStretch(1)

        self._combo.currentIndexChanged.connect(self._handle_index_changed)

    def set_on_changed(self, cb: Optional[Callable[[int], None]]) -> None:
        self._on_changed = cb

    def set_years(self, years: List[int], *, current: Optional[int] = None) -> None:
        self._years = list(years)
        self._combo.blockSignals(True)
        self._combo.clear()
        for y in self._years:
            self._combo.addItem(_rtl_isolate(str(y)))
        if current is not None and current in self._years:
            self._combo.setCurrentIndex(self._years.index(current))
        else:
            self._combo.setCurrentIndex(0 if self._years else -1)
        self._combo.blockSignals(False)

    def current_year(self) -> Optional[int]:
        idx = self._combo.currentIndex()
        if 0 <= idx < len(self._years):
            return self._years[idx]
        return None

    def _handle_index_changed(self, index: int) -> None:
        if not (0 <= index < len(self._years)):
            return
        if self._on_changed is not None:
            self._on_changed(self._years[index])
