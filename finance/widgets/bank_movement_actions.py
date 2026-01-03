from __future__ import annotations

from typing import Callable, Optional

from ..qt import QWidget, QVBoxLayout, QPushButton, QSizePolicy, Qt


class BankMovementActions(QWidget):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        on_add_income: Optional[Callable[[], None]] = None,
        on_add_outcome: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("SidebarActions")
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)

        self._income_btn = QPushButton("הוספת הכנסה", self)
        self._income_btn.setObjectName("SidebarIncomeButton")
        try:
            self._income_btn.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
        except Exception:
            pass
        if on_add_income is not None:
            self._income_btn.clicked.connect(on_add_income)

        self._outcome_btn = QPushButton("הוספת הוצאה", self)
        self._outcome_btn.setObjectName("SidebarOutcomeButton")
        try:
            self._outcome_btn.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
        except Exception:
            pass
        if on_add_outcome is not None:
            self._outcome_btn.clicked.connect(on_add_outcome)

        layout.addWidget(self._income_btn)
        layout.addWidget(self._outcome_btn)

    def income_button(self) -> QPushButton:
        return self._income_btn

    def outcome_button(self) -> QPushButton:
        return self._outcome_btn
