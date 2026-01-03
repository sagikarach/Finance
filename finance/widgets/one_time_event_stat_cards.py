from __future__ import annotations

from typing import Optional

from ..qt import QLabel, QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget, Qt


class OneTimeEventStatCards(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        row1 = QHBoxLayout()
        row1.setSpacing(12)
        c1, self._budget = self._build_stat_card(self, "תקציב", "StatCardPurple")
        c2, self._remaining = self._build_stat_card(
            self, "נותר מהתקציב", "StatCardPurple"
        )
        row1.addWidget(c1, 1)
        row1.addWidget(c2, 1)

        row2 = QHBoxLayout()
        row2.setSpacing(12)
        c3, self._expenses = self._build_stat_card(self, "הוצאות", "StatCardRed")
        c4, self._income = self._build_stat_card(self, "הכנסות", "StatCardGreen")
        row2.addWidget(c3, 1)
        row2.addWidget(c4, 1)

        root.addLayout(row1)
        root.addLayout(row2)

    def clear(self) -> None:
        for lbl in (self._budget, self._remaining, self._expenses, self._income):
            try:
                lbl.setText("")
            except Exception:
                pass

    def set_values(
        self, *, budget: str, remaining: str, expenses: str, income: str
    ) -> None:
        try:
            self._budget.setText(budget)
        except Exception:
            pass
        try:
            self._remaining.setText(remaining)
        except Exception:
            pass
        try:
            self._expenses.setText(expenses)
        except Exception:
            pass
        try:
            self._income.setText(income)
        except Exception:
            pass

    @staticmethod
    def _build_stat_card(
        parent: QWidget, title: str, card_style: str
    ) -> tuple[QWidget, QLabel]:
        card = QWidget(parent)
        card.setObjectName(card_style)
        try:
            card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            card.setAutoFillBackground(True)
        except Exception:
            pass

        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        try:
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        except Exception:
            pass
        try:
            card.setMinimumHeight(64)
            card.setMaximumHeight(98)
        except Exception:
            pass

        title_label = QLabel(title, card)
        title_label.setObjectName("StatTitle")
        value_label = QLabel("", card)
        value_label.setObjectName("StatValueCard")

        layout.addWidget(title_label, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(value_label, 0, Qt.AlignmentFlag.AlignHCenter)
        return card, value_label
