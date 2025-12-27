from __future__ import annotations

from typing import Callable, Dict, List, Optional

from ..data.bank_movement_provider import JsonFileBankMovementProvider
from ..data.provider import AccountsProvider
from ..models.yearly_report_service import YearlyReportService
from ..qt import (
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
    Qt,
)
from ..widgets.year_picker import YearPickerWidget
from ..widgets.yearly_months_table_card import YearlyMonthsTableCard
from .base_page import BasePage


class YearlySummaryPage(BasePage):
    def __init__(
        self,
        app_context: Optional[Dict[str, str]] = None,
        parent: Optional[QWidget] = None,
        provider: Optional[AccountsProvider] = None,
        navigate: Optional[Callable[[str], None]] = None,
        movement_provider: Optional[JsonFileBankMovementProvider] = None,
        yearly_service: Optional[YearlyReportService] = None,
    ) -> None:
        self._movement_provider = movement_provider or JsonFileBankMovementProvider()
        self._yearly_service = yearly_service or YearlyReportService(
            self._movement_provider
        )

        self._current_year: Optional[int] = None
        self._available_years: List[int] = []

        self._year_picker: Optional[YearPickerWidget] = None
        self._months_table: Optional[YearlyMonthsTableCard] = None

        super().__init__(
            app_context=app_context,
            parent=parent,
            provider=provider,
            navigate=navigate,
            page_title="פירוט שנה",
            current_route="yearly_data",
        )

    def _build_header_left_buttons(self) -> List[QToolButton]:
        buttons: List[QToolButton] = []
        settings_btn = QToolButton(self)
        settings_btn.setObjectName("IconButton")
        settings_btn.setText("⚙")
        settings_btn.setToolTip("הגדרות")
        if self._navigate is not None:
            settings_btn.clicked.connect(lambda: self._navigate("settings"))
        buttons.append(settings_btn)
        return buttons

    def _build_content(self, main_col: QVBoxLayout) -> None:
        self._clear_content_layout(main_col)

        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        try:
            container.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
        except Exception:
            pass

        self._year_picker = YearPickerWidget(
            container, on_changed=self._on_year_changed
        )
        layout.addWidget(self._year_picker, 0, Qt.AlignmentFlag.AlignHCenter)

        table_card = QWidget(container)
        table_card.setObjectName("Sidebar")
        try:
            table_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(16, 16, 16, 16)
        table_layout.setSpacing(12)

        self._months_table = YearlyMonthsTableCard(table_card)
        table_layout.addWidget(self._months_table, 1)

        layout.addWidget(table_card, 1)
        main_col.addWidget(container, 1)

        self._available_years = list(self._yearly_service.get_available_years())
        if not self._available_years:
            placeholder = QLabel("אין נתונים שנתיים להצגה", container)
            placeholder.setObjectName("Title")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(placeholder, 1)
            return

        if (
            self._current_year is None
            or self._current_year not in self._available_years
        ):
            self._current_year = self._available_years[0]

        if self._year_picker is not None:
            self._year_picker.set_years(
                self._available_years, current=self._current_year
            )

        self._refresh_report()

    def _refresh_report(self) -> None:
        if self._current_year is None or self._months_table is None:
            return

        self._months_table.set_rows(
            self._yearly_service.get_month_type_summaries(self._current_year)
        )

    def _on_year_changed(self, year: int) -> None:
        if year == self._current_year:
            return
        self._current_year = year
        self._refresh_report()

    def on_route_activated(self) -> None:
        super().on_route_activated()
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)

    def _on_theme_changed(self, is_dark: bool) -> None:
        super()._on_theme_changed(is_dark)
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)
