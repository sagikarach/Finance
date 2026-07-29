from __future__ import annotations

from typing import Optional

from ..qt import QLabel, QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget, Qt


class OneTimeEventStatCards(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        c1, self._budget = self._build_stat_card(self, "תקציב", "MonthNetCard")
        c3, self._expenses = self._build_stat_card(self, "הוצאות", "MonthExpenseCard")
        c4, self._income = self._build_stat_card(self, "הכנסות", "MonthIncomeCard")
        c2, self._remaining = self._build_stat_card(
            self, "נותר מהתקציב", "MonthInfoCard"
        )
        for c in (c1, c3, c4, c2):
            root.addWidget(c, 1)

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
