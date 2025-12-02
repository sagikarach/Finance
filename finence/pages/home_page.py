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
        # Bring the sidebar (right) closer to the edge by reducing the right margin
        layout.setContentsMargins(40, 40, 16, 40)
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

        # Build total cards (reused below)
        total_all_card = QWidget(self)
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

        total_liquid_card = QWidget(self)
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
        # Header row with title and icon buttons
        from ..qt import QToolButton  # local import to avoid circular at top
        header_row = QHBoxLayout()
        header_row.setSpacing(12)
        header_title = QLabel("לוח בקרה", self)
        header_title.setObjectName("HeaderTitle")
        bell_btn = QToolButton(self)
        bell_btn.setObjectName("IconButton")
        bell_btn.setText("🔔")
        bell_btn.setToolTip("התראות")
        settings_btn = QToolButton(self)
        settings_btn.setObjectName("IconButton")
        settings_btn.setText("⚙")
        settings_btn.setToolTip("הגדרות")
        # Wrap header in a background container with the Sidebar color
        header_container = QWidget(self)
        header_container.setObjectName("Sidebar")
        try:
            header_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        header_container_layout = QHBoxLayout(header_container)
        header_container_layout.setContentsMargins(12, 8, 12, 8)
        header_container_layout.setSpacing(12)
        # Place both settings and bell on the left, title on the right
        header_container_layout.addWidget(settings_btn)
        header_container_layout.addWidget(bell_btn)
        header_container_layout.addStretch(1)
        header_container_layout.addWidget(header_title)

        # Cards row (side by side)
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        cards_row.addWidget(total_all_card, 1)
        cards_row.addWidget(total_liquid_card, 1)

        # Main content column (header, cards, chart)
        main_area = QWidget(self)
        main_col = QVBoxLayout(main_area)
        main_col.setContentsMargins(0, 0, 0, 0)
        main_col.setSpacing(16)
        main_col.addWidget(header_container, 0)
        main_col.addLayout(cards_row, 0)

        # Chart card background (same color as sidebar) taking ~2/3 of width
        chart_card = QWidget(main_area)
        chart_card.setObjectName("Sidebar")
        try:
            chart_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        chart_card_layout = QVBoxLayout(chart_card)
        # Let the chart fill almost the entire background square
        chart_card_layout.setContentsMargins(4, 4, 4, 4)
        chart_card_layout.setSpacing(0)
        chart_card_layout.addWidget(chart, 1)

        # Empty rectangle on the right with the same color, occupying the other 1/3
        chart_side_card = QWidget(main_area)
        chart_side_card.setObjectName("Sidebar")
        try:
            chart_side_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        chart_side_layout = QVBoxLayout(chart_side_card)
        chart_side_layout.setContentsMargins(12, 12, 12, 12)
        chart_side_layout.setSpacing(0)

        chart_row = QHBoxLayout()
        chart_row.setSpacing(16)  # visual separation between the two rectangles
        chart_row.addWidget(chart_card, 2)
        chart_row.addWidget(chart_side_card, 1)

        main_col.addLayout(chart_row, 1)

        # Sidebar placeholder
        sidebar = QWidget(self)
        sidebar.setObjectName("Sidebar")
        try:
            sidebar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        try:
            sidebar.setMinimumWidth(220)
        except Exception:
            pass

        # Two-column layout: main area (left) and sidebar (right)
        split_row = QHBoxLayout()
        split_row.setSpacing(16)
        split_row.addWidget(main_area, 3)
        split_row.addWidget(sidebar, 1)

        layout.addLayout(split_row)
        self.setLayout(layout)


def format_currency(value: float) -> str:
    try:
        return f"₪{value:,.2f}"
    except Exception:
        return f"₪{value:.2f}"
