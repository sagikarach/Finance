from __future__ import annotations

from typing import Callable, Dict, List, Optional

from ..qt import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    Qt,
    QColor,
    QGraphicsDropShadowEffect,
    QSizePolicy,
    QApplication,
    QToolButton,
)
from ..data.provider import AccountsProvider
from ..models.accounts import (
    BankAccount,
    compute_total_amount,
    compute_total_liquid_amount,
)
from ..widgets.accounts_pie_chart import AccountsPieChart
from .base_page import BasePage


class BankAccountsPage(BasePage):
    """Bank accounts overview page (חשבונות) similar to the savings overview."""

    def __init__(
        self,
        app_context: Optional[Dict[str, str]] = None,
        parent: Optional[QWidget] = None,
        provider: Optional[AccountsProvider] = None,
        navigate: Optional[Callable[[str], None]] = None,
    ) -> None:
        super().__init__(
            app_context=app_context,
            parent=parent,
            provider=provider,
            navigate=navigate,
            page_title="חשבונות",
            current_route="bank_accounts",
        )

    def on_route_activated(self) -> None:
        """Sync header toggle + sidebar with current theme when opened."""
        app = QApplication.instance()
        is_dark = False
        if app is not None:
            try:
                is_dark = str(app.property("theme") or "light") == "dark"
            except Exception:
                is_dark = False
        self._on_theme_changed(is_dark)

    def _build_header_left_buttons(self) -> List[QToolButton]:
        """Add settings button to header."""
        buttons: List[QToolButton] = []
        settings_btn = QToolButton(self)
        settings_btn.setObjectName("IconButton")
        settings_btn.setText("⚙")
        settings_btn.setToolTip("הגדרות")
        if self._navigate is not None:
            settings_btn.clicked.connect(lambda: self._navigate("settings"))  # type: ignore[arg-type]
        buttons.append(settings_btn)
        return buttons

    def _build_content(self, main_col: QVBoxLayout) -> None:
        """Build bank-accounts page content with totals and a pie chart."""
        bank_accounts: List[BankAccount] = [
            acc for acc in self._accounts if isinstance(acc, BankAccount)
        ]

        total_all = compute_total_amount(bank_accounts)
        total_liquid = compute_total_liquid_amount(bank_accounts)

        # --- Top cards: total and liquid amounts for bank accounts only ---
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
            total_all_card.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
            )
        except Exception:
            pass
        total_all_title = QLabel("סה״כ בחשבונות", total_all_card)
        total_all_title.setObjectName("StatTitle")
        total_all_label = QLabel(format_currency(total_all), total_all_card)
        total_all_label.setObjectName("StatValueLarge")
        total_all_card_layout.addStretch(1)
        total_all_card_layout.addWidget(
            total_all_title, 0, Qt.AlignmentFlag.AlignHCenter
        )
        total_all_card_layout.addWidget(
            total_all_label, 0, Qt.AlignmentFlag.AlignHCenter
        )
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
            total_liquid_card.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
            )
        except Exception:
            pass
        total_liquid_title = QLabel("סכום נזיל בחשבונות", total_liquid_card)
        total_liquid_title.setObjectName("StatTitle")
        total_liquid_label = QLabel(
            format_currency(total_liquid), total_liquid_card
        )
        total_liquid_label.setObjectName("StatValueLarge")
        total_liquid_card_layout.addStretch(1)
        total_liquid_card_layout.addWidget(
            total_liquid_title, 0, Qt.AlignmentFlag.AlignHCenter
        )
        total_liquid_card_layout.addWidget(
            total_liquid_label, 0, Qt.AlignmentFlag.AlignHCenter
        )
        total_liquid_card_layout.addStretch(1)

        # Shared drop shadow styling with the savings and home pages.
        try:
            for card in (total_all_card, total_liquid_card):
                shadow = QGraphicsDropShadowEffect(card)
                shadow.setBlurRadius(36)
                app = QApplication.instance()
                is_dark = False
                if app is not None:
                    try:
                        current_theme = str(app.property("theme") or "light")
                        is_dark = current_theme == "dark"
                    except Exception:
                        pass
                if is_dark:
                    shadow.setColor(QColor(0, 0, 0, 120))
                else:
                    shadow.setColor(QColor(0, 0, 0, 60))
                shadow.setOffset(0, 10)
                card.setGraphicsEffect(shadow)
        except Exception:
            pass

        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        cards_row.addWidget(total_all_card, 1)
        cards_row.addWidget(total_liquid_card, 1)
        main_col.addLayout(cards_row, 0)

        # --- Middle: pie chart of bank accounts only ---
        if bank_accounts:
            chart = AccountsPieChart(accounts=bank_accounts, parent=self)

            chart_card = QWidget(self)
            chart_card.setObjectName("Sidebar")
            try:
                chart_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            except Exception:
                pass
            chart_card_layout = QVBoxLayout(chart_card)
            chart_card_layout.setContentsMargins(4, 4, 4, 4)
            chart_card_layout.setSpacing(0)
            chart_card_layout.addWidget(chart, 1)

            main_col.addWidget(chart_card, 1)
        else:
            placeholder = QLabel("אין חשבונות בנק להצגה", self)
            placeholder.setObjectName("Subtitle")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_col.addWidget(placeholder, 1)


def format_currency(value: float) -> str:
    try:
        return f"₪{value:,.2f}"
    except Exception:
        return f"₪{value}"


