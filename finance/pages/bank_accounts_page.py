from __future__ import annotations

from typing import Callable, Dict, List, Optional

from ..qt import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    Qt,
    QSizePolicy,
    QApplication,
    QToolButton,
)
from ..data.provider import AccountsProvider
from ..models.accounts import BankAccount
from ..models.accounts_service import AccountsService
from ..models.overview import AccountsOverview
from ..widgets.accounts_pie_chart import AccountsPieChart
from ..utils.formatting import format_currency
from .base_page import BasePage


class BankAccountsPage(BasePage):
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
        self._accounts_service = AccountsService(
            self._provider, history_provider=self._history_provider
        )

    def on_route_activated(self) -> None:
        super().on_route_activated()
        self._load_and_refresh_accounts()
        if isinstance(self._content_col, QVBoxLayout):
            try:
                self.setUpdatesEnabled(False)
                self._clear_content_layout(self._content_col)
                self._build_content(self._content_col)
            finally:
                self.setUpdatesEnabled(True)
                self.update()

        app = QApplication.instance()
        is_dark = False
        if app is not None:
            try:
                is_dark = str(app.property("theme") or "light") == "dark"
            except Exception:
                is_dark = False
        self._on_theme_changed(is_dark)

    _PASTEL = [
        "#B9B6F0", "#C6D3B4", "#F2D06B", "#E9A491", "#9BB4E6",
        "#8FBF9F", "#E0B0D8", "#F7E2A6", "#7FB3B3", "#E8A87C",
    ]

    def _stat_card(self, object_name: str, title: str, value: str) -> QWidget:
        card = QWidget(self)
        card.setObjectName(object_name)
        try:
            card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            card.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
            )
            card.setMinimumHeight(118)
            card.setMaximumHeight(150)
        except Exception:
            pass
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(6)
        t = QLabel(title, card)
        t.setObjectName("StatTitle")
        v = QLabel(value, card)
        v.setObjectName("StatValueLarge")
        lay.addStretch(1)
        lay.addWidget(t, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addWidget(v, 0, Qt.AlignmentFlag.AlignHCenter)
        lay.addStretch(1)
        return card

    def _panel(self, title: str, inner: QWidget) -> QWidget:
        return self._content_panel(title, inner)

    def _accounts_list(self, accounts: List[BankAccount]) -> QWidget:
        wrap = QWidget(self)
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(0)
        for idx, acc in enumerate(accounts):
            row = QWidget(wrap)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(2, 11, 2, 11)
            rl.setSpacing(10)
            dot = QLabel(row)
            dot.setFixedSize(12, 12)
            color = self._PASTEL[idx % len(self._PASTEL)]
            dot.setStyleSheet(
                f"background:{color}; border-radius:4px;"
            )
            name = QLabel(str(acc.name), row)
            name.setStyleSheet(
                "font-size:14px; font-weight:600; color:#40433c; background:transparent;"
            )
            val = QLabel(format_currency(acc.total_amount), row)
            val.setStyleSheet(
                "font-size:14px; font-weight:800; color:#2f9e68; background:transparent;"
            )
            rl.addWidget(dot)
            rl.addWidget(name)
            rl.addStretch(1)
            rl.addWidget(val)
            if idx > 0:
                row.setStyleSheet("border-top:1px solid #ecece2;")
                try:
                    row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
                except Exception:
                    pass
            lay.addWidget(row)
        lay.addStretch(1)
        return wrap

    def _build_content(self, main_col: QVBoxLayout) -> None:
        overview = AccountsOverview.for_bank_accounts(self._accounts)
        bank_accounts: List[BankAccount] = [
            acc for acc in overview.accounts if isinstance(acc, BankAccount)
        ]
        bank_accounts.sort(key=lambda a: float(a.total_amount), reverse=True)

        # ── top row: total + liquid cards ──
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        cards_row.addWidget(
            self._stat_card(
                "DashHeroYellow", "סה״כ בחשבונות",
                format_currency(overview.total_all),
            ),
            3,
        )
        cards_row.addWidget(
            self._stat_card(
                "DashCardGreen", "נזיל",
                format_currency(overview.total_liquid),
            ),
            2,
        )
        main_col.addLayout(cards_row, 0)

        if not bank_accounts:
            placeholder = QLabel("אין חשבונות בנק להצגה", self)
            placeholder.setObjectName("Subtitle")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_col.addWidget(placeholder, 1)
            return

        # ── content row: donut + colour-coded account list ──
        donut = AccountsPieChart(accounts=bank_accounts, parent=self)
        donut_panel = self._panel("פילוח חשבונות", donut)
        list_panel = self._panel("חשבונות", self._accounts_list(bank_accounts))

        content_row = QHBoxLayout()
        content_row.setSpacing(16)
        content_row.addWidget(donut_panel, 2)
        content_row.addWidget(list_panel, 3)
        main_col.addLayout(content_row, 1)
