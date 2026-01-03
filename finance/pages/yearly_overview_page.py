from __future__ import annotations

from typing import Callable, Dict, List, Optional

from ..data.bank_movement_provider import JsonFileBankMovementProvider
from ..data.provider import AccountsProvider
from ..models.yearly_report_service import YearlyReportService
from ..qt import (
    QLabel,
    QHBoxLayout,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
    Qt,
)
from ..utils.formatting import format_currency
from ..widgets.yearly_balance_chart import YearlyBalanceChart
from ..widgets.year_picker import YearPickerWidget
from .base_page import BasePage


class AutoStatCard(QWidget):
    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        try:
            self.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
        except Exception:
            pass
        try:
            self.setMinimumHeight(100)
            self.setMinimumWidth(90)
        except Exception:
            pass

        v = QVBoxLayout(self)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(2)

        self._title = QLabel(title, self)
        self._title.setObjectName("Subtitle")
        try:
            self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception:
            pass

        self._value = QLabel("", self)
        self._value.setObjectName("StatValueLarge")
        try:
            self._value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception:
            pass

        v.addStretch(1)
        v.addWidget(self._title, 0, Qt.AlignmentFlag.AlignHCenter)
        v.addWidget(self._value, 0, Qt.AlignmentFlag.AlignHCenter)
        v.addStretch(1)

        self._apply_fonts()

    def set_value(self, text: str) -> None:
        self._value.setText(text)
        self._apply_fonts()

    def value_label(self) -> QLabel:
        return self._value

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_fonts()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply_fonts()

    def _clamp(self, v: int, lo: int, hi: int) -> int:
        return max(lo, min(hi, int(v)))

    def _apply_fonts(self) -> None:
        base = min(max(1, int(self.width())), max(1, int(self.height())))
        title_px = self._clamp(int(base * 0.7), 8, 18)
        value_px = self._clamp(int(base), 12, 30)
        try:
            f = self._title.font()
            f.setPixelSize(int(title_px))
            self._title.setFont(f)
        except Exception:
            pass
        try:
            f = self._value.font()
            f.setPixelSize(int(value_px))
            self._value.setFont(f)
        except Exception:
            pass


class YearlyOverviewPage(BasePage):
    def __init__(
        self,
        app_context: Optional[Dict[str, str]] = None,
        parent: Optional[QWidget] = None,
        provider: Optional[AccountsProvider] = None,
        navigate: Optional[Callable[[str], None]] = None,
        movement_provider: Optional[JsonFileBankMovementProvider] = None,
    ) -> None:
        self._movement_provider = movement_provider or JsonFileBankMovementProvider()
        self._yearly_service = YearlyReportService(self._movement_provider)
        self._current_year: Optional[int] = None
        self._available_years: List[int] = []

        self._year_picker: Optional[YearPickerWidget] = None
        self._income_value: Optional[QLabel] = None
        self._expense_value: Optional[QLabel] = None
        self._net_value: Optional[QLabel] = None
        self._balance_chart: Optional[YearlyBalanceChart] = None

        super().__init__(
            app_context=app_context,
            parent=parent,
            provider=provider,
            navigate=navigate,
            page_title="סיכום שנתי",
            current_route="yearly_overview",
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
            container.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            pass

        year_picker_block = QWidget(container)
        year_picker_block_layout = QVBoxLayout(year_picker_block)
        year_picker_block_layout.setContentsMargins(0, 0, 0, 0)
        year_picker_block_layout.setSpacing(4)

        year_picker_label = QLabel("בחר שנה", year_picker_block)
        year_picker_label.setObjectName("Subtitle")
        try:
            year_picker_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        except Exception:
            pass
        year_picker_block_layout.addWidget(year_picker_label, 0)

        self._year_picker = YearPickerWidget(
            year_picker_block,
            label_text="",
            on_changed=self._on_year_changed,
            centered=False,
            label_on_right=False,
        )
        try:
            for lbl in self._year_picker.findChildren(QLabel):
                if not (lbl.text() or "").strip():
                    lbl.setVisible(False)
        except Exception:
            pass
        year_picker_block_layout.addWidget(self._year_picker, 0)

        top_row = QWidget(container)
        top_row_layout = QHBoxLayout(top_row)
        top_row_layout.setContentsMargins(0, 0, 0, 0)
        top_row_layout.setSpacing(16)

        income_card = AutoStatCard("הכנסות", container)
        expense_card = AutoStatCard("הוצאות", container)
        net_card = AutoStatCard("יתרה", container)
        income_card.setObjectName("StatCardGreen")
        expense_card.setObjectName("StatCardRed")
        net_card.setObjectName("StatCardPurple")
        try:
            income_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            expense_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            net_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass

        self._income_value = income_card.value_label()
        self._expense_value = expense_card.value_label()
        self._net_value = net_card.value_label()

        try:
            year_picker_block.setSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
            )
        except Exception:
            pass
        top_row_layout.addWidget(year_picker_block, 0, Qt.AlignmentFlag.AlignVCenter)

        top_row_layout.addWidget(income_card, 1)
        top_row_layout.addWidget(expense_card, 1)
        top_row_layout.addWidget(net_card, 1)

        chart_card = QWidget(container)
        chart_card.setObjectName("Sidebar")
        try:
            chart_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(16, 16, 16, 16)
        chart_layout.setSpacing(8)

        self._balance_chart = YearlyBalanceChart(chart_card)
        chart_layout.addWidget(self._balance_chart, 1)

        layout.addWidget(top_row, 0)
        layout.addWidget(chart_card, 1)

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

        self._refresh()

    def _refresh(self) -> None:
        if self._current_year is None:
            return

        report = self._yearly_service.get_yearly_report(self._current_year)
        if report is not None:
            if self._income_value is not None:
                self._income_value.setText(format_currency(report.summary.total_income))
            if self._expense_value is not None:
                self._expense_value.setText(
                    format_currency(report.summary.total_outcome)
                )
            if self._net_value is not None:
                self._net_value.setText(format_currency(report.summary.net_amount))

        if self._balance_chart is not None:
            month_labels = [
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
            nets = [0.0] * 12
            for s in self._yearly_service.get_month_type_summaries(self._current_year):
                try:
                    idx = max(0, min(11, int(s.month) - 1))
                    nets[idx] = float(s.net_balance)
                except Exception:
                    continue
            self._balance_chart.set_monthly_net(nets, month_labels)

    def _on_year_changed(self, year: int) -> None:
        if year == self._current_year:
            return
        self._current_year = year
        self._refresh()

    def on_route_activated(self) -> None:
        super().on_route_activated()
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)

    def _on_theme_changed(self, is_dark: bool) -> None:
        super()._on_theme_changed(is_dark)
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)
