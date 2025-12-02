from __future__ import annotations

from typing import Dict, Optional, List

from ..qt import QLabel, QVBoxLayout, QHBoxLayout, QWidget, Qt, QColor, QGraphicsDropShadowEffect, QSizePolicy
from ..data.provider import AccountsProvider, JsonFileAccountsProvider
from ..models.accounts import (
    MoneyAccount,
    compute_total_amount,
    compute_total_liquid_amount,
)
from ..widgets.accounts_pie_chart import AccountsPieChart


class HomePage(QWidget):
    def __init__(
        self,
        app_context: Optional[Dict[str, str]] = None,
        parent: Optional[QWidget] = None,
        provider: Optional[AccountsProvider] = None,
    ) -> None:
        super().__init__(parent)
        self._app_context = app_context or {}
        self._provider: AccountsProvider = provider or JsonFileAccountsProvider()
        self._accounts: List[MoneyAccount] = self._provider.list_accounts()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(12)

        total_all = compute_total_amount(self._accounts)
        total_liquid = compute_total_liquid_amount(self._accounts)

        total_all_label = QLabel(f"{format_currency(total_all)}")
        total_liquid_label = QLabel(f"{format_currency(total_liquid)}")
        total_all_label.setObjectName("StatValueLarge")
        total_liquid_label.setObjectName("StatValueLarge")
        try:
            total_all_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            total_liquid_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass

        chart = AccountsPieChart(accounts=self._accounts, parent=self)

        page_card = QWidget(self)
        page_card.setObjectName("PageCard")
        try:
            page_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        page_layout = QVBoxLayout(page_card)
        page_layout.setContentsMargins(16, 16, 16, 16)
        page_layout.setSpacing(16)

        content_row = QHBoxLayout()
        content_row.setSpacing(16)
        content_row.addWidget(chart, stretch=2)

        totals_panel = QWidget(self)
        try:
            totals_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        except Exception:
            pass
        totals_layout = QVBoxLayout(totals_panel)
        totals_layout.setContentsMargins(0, 0, 0, 0)
        totals_layout.setSpacing(24)
        try:
            totals_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass

        total_all_card = QWidget(totals_panel)
        total_all_card.setObjectName("StatCardGreen")
        try:
            total_all_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        total_all_card_layout = QVBoxLayout(total_all_card)
        total_all_card_layout.setContentsMargins(14, 14, 14, 14)
        total_all_card_layout.setSpacing(6)
        try:
            total_all_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        except Exception:
            pass
        total_all_title = QLabel("סך הכל כסף", total_all_card)
        total_all_title.setObjectName("StatTitle")
        try:
            total_all_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass
        total_all_card_layout.addStretch(1)
        total_all_card_layout.addWidget(total_all_title, 0, Qt.AlignmentFlag.AlignHCenter)
        total_all_card_layout.addWidget(total_all_label, 0, Qt.AlignmentFlag.AlignHCenter)
        total_all_card_layout.addStretch(1)

        total_liquid_card = QWidget(totals_panel)
        total_liquid_card.setObjectName("StatCardPurple")
        try:
            total_liquid_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        total_liquid_card_layout = QVBoxLayout(total_liquid_card)
        total_liquid_card_layout.setContentsMargins(14, 14, 14, 14)
        total_liquid_card_layout.setSpacing(6)
        try:
            total_liquid_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        except Exception:
            pass
        total_liquid_title = QLabel("כסף נזיל", total_liquid_card)
        total_liquid_title.setObjectName("StatTitle")
        try:
            total_liquid_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass
        total_liquid_card_layout.addStretch(1)
        total_liquid_card_layout.addWidget(total_liquid_title, 0, Qt.AlignmentFlag.AlignHCenter)
        total_liquid_card_layout.addWidget(total_liquid_label, 0, Qt.AlignmentFlag.AlignHCenter)
        total_liquid_card_layout.addStretch(1)

        try:
            for card in (total_all_card, total_liquid_card):
                shadow = QGraphicsDropShadowEffect(card)
                shadow.setBlurRadius(36)
                shadow.setColor(QColor(0, 0, 0, 60))
                shadow.setOffset(0, 10)
                card.setGraphicsEffect(shadow)
        except Exception:
            pass

        totals_layout.addStretch(1)
        totals_layout.addWidget(total_all_card)
        totals_layout.addSpacing(16)
        totals_layout.addWidget(total_liquid_card)
        totals_layout.addStretch(1)
        try:
            idx_a = totals_layout.indexOf(total_all_card)
            idx_b = totals_layout.indexOf(total_liquid_card)
            totals_layout.setStretch(idx_a, 1)
            totals_layout.setStretch(idx_b, 1)
        except Exception:
            pass

        content_row.addWidget(totals_panel, stretch=1)

        page_layout.addLayout(content_row)
        try:
            content_row.setStretch(0, 2)
            content_row.setStretch(1, 1)
        except Exception:
            pass
        layout.addWidget(page_card)
        self.setLayout(layout)


def format_currency(value: float) -> str:
    try:
        return f"₪{value:,.2f}"
    except Exception:
        return f"₪{value:.2f}"
