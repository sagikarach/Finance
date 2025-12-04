from __future__ import annotations

from typing import Callable, Dict, List, Optional
import math

from ..qt import (
    QApplication,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    Qt,
    QSizePolicy,
    QToolButton,
    QPushButton,
    QLineEdit,
    QComboBox,
    QDateEdit,
    QDate,
    QLocale,
    QFrame,
    QDialog,
    QChart,
    QChartView,
    QLineSeries,
    QValueAxis,
    QCategoryAxis,
    QColor,
    QPainter,
    QPainterPath,
    QLinearGradient,
    QPointF,
    QToolTip,
    QCursor,
    charts_available,
)
from ..data.provider import AccountsProvider, JsonFileAccountsProvider
from ..models.accounts import SavingsAccount, Savings, MoneySnapshot, parse_iso_date
from .base_page import BasePage
from .savings_page import format_currency


class ShadowChartView(QChartView):
    """Custom chart view that paints a soft filled 'shadow' under each line."""

    def __init__(
        self,
        chart: QChart,
        shadows: List[tuple[QLineSeries, QColor]],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(chart, parent)
        self._shadows: List[tuple[QLineSeries, QColor]] = shadows

    def drawForeground(self, painter: QPainter, rect) -> None:  # type: ignore[override]
        # Keep any default foreground (e.g. tooltips) first.
        try:
            super().drawForeground(painter, rect)
        except Exception:
            pass

        try:
            chart = self.chart()
        except Exception:
            chart = None
        if chart is None or not self._shadows:
            return

        try:
            plot_rect = chart.plotArea()
        except Exception:
            plot_rect = rect
        bottom_y = plot_rect.bottom()

        for series, base_color in self._shadows:
            # Collect data points from the series.
            try:
                pts = list(series.points())  # type: ignore[attr-defined]
            except Exception:
                try:
                    pts = list(series.pointsVector())  # type: ignore[attr-defined]
                except Exception:
                    pts = []
            if len(pts) < 2:
                continue

            path = QPainterPath()
            try:
                first_pos = chart.mapToPosition(pts[0], series)  # type: ignore[arg-type]
            except Exception:
                continue
            path.moveTo(first_pos)
            last_pos = first_pos
            min_y = first_pos.y()

            for pt in pts[1:]:
                try:
                    pos = chart.mapToPosition(pt, series)  # type: ignore[arg-type]
                except Exception:
                    continue
                path.lineTo(pos)
                last_pos = pos
                if pos.y() < min_y:
                    min_y = pos.y()

            # Close the path down to the bottom of the plot area so the fill
            # appears only under the line.
            try:
                path.lineTo(QPointF(last_pos.x(), bottom_y))
                path.lineTo(QPointF(first_pos.x(), bottom_y))
            except Exception:
                pass
            try:
                path.closeSubpath()
            except Exception:
                pass

            # Create a vertical gradient that is strongest near the line
            # (around min_y) and fades out towards the bottom of the plot.
            gradient = None
            try:
                gradient = QLinearGradient(
                    QPointF(0.0, min_y), QPointF(0.0, bottom_y)
                )
                top_col = QColor(base_color)
                top_col.setAlpha(180)
                bottom_col = QColor(base_color)
                bottom_col.setAlpha(0)
                gradient.setColorAt(0.0, top_col)
                gradient.setColorAt(1.0, bottom_col)
            except Exception:
                gradient = None

            # Fallback flat fill if gradient creation fails for any reason.
            fill = QColor(base_color)
            try:
                fill.setAlpha(80)
            except Exception:
                pass

            painter.save()
            try:
                painter.setPen(Qt.PenStyle.NoPen)  # type: ignore[attr-defined]
            except Exception:
                try:
                    painter.setPen(Qt.NoPen)  # type: ignore[attr-defined]
                except Exception:
                    pass
            if gradient is not None:
                painter.setBrush(gradient)
            else:
                painter.setBrush(fill)
            try:
                painter.drawPath(path)
            except Exception:
                pass
            painter.restore()


class SavingsAccountPage(BasePage):
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
            page_title="פרטי חסכון",
            # Use a distinct route name so the sidebar can enable the per-account
            # selection arrow, while still treating it as part of the savings
            # section visually (handled in Sidebar.update_route).
            current_route="savings_account",
        )

    def _build_header_left_buttons(self) -> List[QToolButton]:
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
        while main_col.count():
            item = main_col.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        selected_name = ""
        try:
            selected_name = str(self._app_context.get("selected_savings_account", ""))
        except Exception:
            selected_name = ""

        target: Optional[SavingsAccount] = None
        for acc in self._accounts:
            if isinstance(acc, SavingsAccount) and acc.name == selected_name:
                target = acc
                break

        if target is None:
            # Fallback UI if nothing was selected or account was removed.
            placeholder = QLabel("לא נבחר חשבון חסכון", self)
            placeholder.setObjectName("Title")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_col.addWidget(placeholder, 1)
            return

        # --- Top third: summary rectangle with total amount and action buttons ---
        top_card = QWidget(self)
        top_card.setObjectName("Sidebar")
        try:
            top_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        top_layout = QHBoxLayout(top_card)
        top_layout.setContentsMargins(16, 16, 16, 16)
        top_layout.setSpacing(16)

        summary_col = QVBoxLayout()
        summary_col.setSpacing(4)

        name_label = QLabel(target.name, top_card)
        name_label.setObjectName("HeaderTitle")
        total_label = QLabel(format_currency(target.total_amount), top_card)
        total_label.setObjectName("StatValueLarge")
        liquid_text = "נזיל" if target.is_liquid else "לא נזיל"
        liquid_label = QLabel(liquid_text, top_card)
        liquid_label.setObjectName("StatTitle")

        # First row: name and liquid status on the same line, on opposite
        # sides, with the total amount displayed on its own row below.
        name_liquid_row = QHBoxLayout()
        name_liquid_row.setSpacing(8)
        # Swap positions: liquid label on the side where the name was, and the
        # name on the opposite side.
        name_liquid_row.addWidget(liquid_label, 0, Qt.AlignmentFlag.AlignRight)
        name_liquid_row.addStretch(1)
        name_liquid_row.addWidget(name_label, 0, Qt.AlignmentFlag.AlignLeft)

        summary_col.addLayout(name_liquid_row)
        summary_col.addWidget(total_label, 0, Qt.AlignmentFlag.AlignRight)

        # Buttons row: three actions in a single horizontal line, anchored to
        # the bottom of the top card rather than vertically centered.
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(8)

        add_saving_btn = QPushButton("הוסף חסכון", top_card)
        add_saving_btn.setObjectName("AddButton")
        update_saving_btn = QPushButton("עדכן חסכון", top_card)
        update_saving_btn.setObjectName("EditButton")
        delete_saving_btn = QPushButton("מחק חסכון", top_card)
        delete_saving_btn.setObjectName("DeleteButton")

        # Switch positions of add and delete in the row: delete, update, add.
        for b in (delete_saving_btn, update_saving_btn, add_saving_btn):
            try:
                b.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            except Exception:
                pass
            buttons_row.addWidget(b, 0, Qt.AlignmentFlag.AlignLeft)

        # Wrap the buttons row in a vertical layout with a stretch above so the
        # buttons sit at the bottom of the top card.
        buttons_col = QVBoxLayout()
        buttons_col.setSpacing(0)
        buttons_col.addStretch(1)
        buttons_col.addLayout(buttons_row)

        # Put buttons on one side and the summary on the other.
        top_layout.addLayout(buttons_col, 0)
        top_layout.addStretch(1)
        top_layout.addLayout(summary_col, 1)

        # Connect buttons to dialogs that actually modify savings in this
        # account and then refresh the page + chart.
        add_saving_btn.clicked.connect(  # type: ignore[arg-type]
            lambda: self._handle_add_saving(target)
        )
        update_saving_btn.clicked.connect(  # type: ignore[arg-type]
            lambda: self._handle_update_saving(target)
        )
        delete_saving_btn.clicked.connect(  # type: ignore[arg-type]
            lambda: self._handle_delete_saving(target)
        )

        # --- Bottom 2/3: rectangle with line chart of savings history ---
        chart_card = QWidget(self)
        chart_card.setObjectName("Sidebar")
        try:
            chart_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        chart_layout = QVBoxLayout(chart_card)
        chart_layout.setContentsMargins(8, 8, 8, 8)
        chart_layout.setSpacing(8)

        if charts_available and target.savings:
            chart = QChart()
            chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
            # Remove legend and background so the chart blends with the card.
            chart.legend().setVisible(False)
            chart.setBackgroundRoundness(0)
            chart.setBackgroundBrush(Qt.GlobalColor.transparent)
            chart.setPlotAreaBackgroundVisible(False)

            # Build a global ordered list of (year, month) keys across all
            # savings histories so all lines share the same month positions.
            month_keys: List[tuple[int, int]] = []
            seen_months: set[tuple[int, int]] = set()
            for s in target.savings:
                for snap in s.history:
                    dt = parse_iso_date(str(snap.date))
                    key = (dt.year, dt.month)
                    if key not in seen_months:
                        seen_months.add(key)
                        month_keys.append(key)

            if not month_keys:
                # Fallback: single synthetic month if there is no history.
                month_keys = [(0, 1)]

            month_keys.sort(key=lambda k: (k[0], k[1]))
            month_to_index = {key: idx for idx, key in enumerate(month_keys)}

            max_amount = 0.0

            # Track (series, color) so the custom view can paint shadows.
            shadow_specs: List[tuple[QLineSeries, QColor]] = []

            total_savings = max(1, len(target.savings))

            for idx, s in enumerate(target.savings):
                series = QLineSeries()
                series.setName(s.name)
                # Hide square markers on the line; we only want smooth lines.
                try:
                    series.setPointsVisible(False)
                except Exception:
                    pass

                # Group this savings' history by month and take the latest
                # snapshot amount within each month.
                latest_by_month: dict[tuple[int, int], MoneySnapshot] = {}
                for snap in s.history:
                    dt = parse_iso_date(str(snap.date))
                    key = (dt.year, dt.month)
                    existing = latest_by_month.get(key)
                    # Help type-checker: guard against None explicitly before
                    # assigning to the dictionary of concrete MoneySnapshot.
                    if existing is None:
                        latest_by_month[key] = snap
                    else:
                        if parse_iso_date(str(existing.date)) < dt:
                            latest_by_month[key] = snap

                # Build a base value for every month in month_keys so each
                # savings line is continuous across the whole range. For
                # months with no data, we carry forward the last known amount
                # (or 0 before the first data point). Then we densify this
                # sequence with an interpolated smooth curve between the
                # month samples so the drawn line looks rounded rather than
                # like a series of sharp corners.
                base_values: List[float] = []
                last_amount = 0.0
                if not latest_by_month:
                    # No history at all: use the current total amount flat
                    # across all months.
                    last_amount = float(s.amount)
                    for _key in month_keys:
                        base_values.append(last_amount)
                        if last_amount > max_amount:
                            max_amount = last_amount
                else:
                    for key in month_keys:
                        snap_opt = latest_by_month.get(key)
                        if snap_opt is not None:
                            last_amount = float(snap_opt.amount)
                        base_values.append(last_amount)
                        if last_amount > max_amount:
                            max_amount = last_amount

                n_months = len(month_keys)
                if n_months == 1:
                    # Single point: just draw it where the only month index is.
                    series.append(0.0, base_values[0])
                else:
                    # Slightly smooth the month-to-month knots using a small
                    # moving average so the curve looks even more rounded,
                    # while still staying very close to the real data.
                    smooth_knots: List[float] = list(base_values)
                    if n_months >= 3:
                        tmp = list(smooth_knots)
                        for i_k in range(1, n_months - 1):
                            tmp[i_k] = (
                                0.25 * smooth_knots[i_k - 1]
                                + 0.5 * smooth_knots[i_k]
                                + 0.25 * smooth_knots[i_k + 1]
                            )
                        smooth_knots = tmp

                    # Clamp the smoothed curve to the real data range of this
                    # series so we don't overshoot wildly above or below.
                    min_y_val = min(base_values)
                    max_y_val = max(base_values) if base_values else 0.0

                    def sample_catmull_rom(i_seg: int, t: float) -> float:
                        """Sample a Catmull-Rom spline between month i_seg and i_seg+1."""

                        i0 = max(0, min(n_months - 1, i_seg - 1))
                        i1 = max(0, min(n_months - 1, i_seg))
                        i2 = max(0, min(n_months - 1, i_seg + 1))
                        i3 = max(0, min(n_months - 1, i_seg + 2))
                        p0 = smooth_knots[i0]
                        p1 = smooth_knots[i1]
                        p2 = smooth_knots[i2]
                        p3 = smooth_knots[i3]
                        t2 = t * t
                        t3 = t2 * t
                        val = 0.5 * (
                            (2.0 * p1)
                            + (-p0 + p2) * t
                            + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
                            + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3
                        )
                        if val < min_y_val:
                            val = min_y_val
                        if val > max_y_val:
                            val = max_y_val
                        return val

                    # Start with the first knot at x=0.
                    series.append(0.0, smooth_knots[0])
                    # Number of intermediate samples between each pair of
                    # months – higher means smoother but more points.
                    steps_per_segment = 16
                    for i_seg in range(n_months - 1):
                        for j in range(1, steps_per_segment + 1):
                            t = float(j) / float(steps_per_segment)
                            x_val = float(i_seg) + t
                            y_val = sample_catmull_rom(i_seg, t)
                            series.append(x_val, y_val)

                # Choose a distinct color per savings line.
                try:
                    hue = int((360.0 * idx) / float(total_savings))
                    base_color = QColor.fromHsl(hue, 180, 140)
                except Exception:
                    base_color = QColor("#f97316")  # warm fallback

                # Style the visible line.
                try:
                    pen = series.pen()
                    pen.setColor(base_color)
                    try:
                        pen.setWidthF(2.0)
                    except Exception:
                        pass
                    try:
                        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)  # type: ignore[attr-defined]
                        pen.setCapStyle(Qt.PenCapStyle.RoundCap)  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    series.setPen(pen)
                except Exception:
                    pass

                shadow_specs.append((series, base_color))
                chart.addSeries(series)

                # Connect hover handler to show tooltip with month, savings
                # name and amount for each point.
                def make_hover_handler(savings_name: str, values: List[float]):
                    def on_hover(point, state):  # type: ignore[no-redef]
                        if not state:
                            return
                        # point.x() is the month index; clamp to values range.
                        idx = int(round(point.x()))
                        if idx < 0 or idx >= len(values):
                            return
                        amount_val = values[idx]
                        if 0 <= idx < len(month_keys):
                            year, month = month_keys[idx]
                            month_label = f"{month:02d}/{year % 100:02d}"
                        else:
                            month_label = str(idx)
                        text = f"{savings_name}\n{month_label}: {format_currency(amount_val)}"
                        try:
                            QToolTip.showText(QCursor.pos(), text)
                        except Exception:
                            pass

                    return on_hover

                # Capture the sequence of y-values for this series in month
                # order so the hover handler can look them up by index. We
                # use the base monthly values here rather than the dense
                # interpolated curve, so each tooltip still snaps cleanly to
                # the real month buckets.
                series_values: List[float] = list(base_values)

                try:
                    series.hovered.connect(make_hover_handler(s.name, series_values))  # type: ignore[arg-type]
                except Exception:
                    pass

            # X axis with month/year labels (no axis title, no grid).
            axis_x = QCategoryAxis()
            for key in month_keys:
                year, month = key
                label = f"{month:02d}/{year % 100:02d}"
                axis_x.append(label, float(month_to_index[key]))
            try:
                axis_x.setGridLineVisible(False)
                axis_x.setMinorGridLineVisible(False)  # type: ignore[attr-defined]
            except Exception:
                pass

            # Y axis with amount values (no axis title, no grid).
            axis_y = QValueAxis()
            axis_y.setLabelFormat("%.0f")
            # Round the top of the range up to the next 1000 so ticks are
            # aligned on multiples of 1000, and use a 1000 interval when
            # supported.
            if max_amount > 0:
                top = float(math.ceil(max_amount / 1000.0) * 1000.0)
            else:
                top = 1000.0
            axis_y.setRange(0.0, top)
            try:
                axis_y.setTickInterval(1000.0)  # type: ignore[attr-defined]
            except Exception:
                pass
            try:
                axis_y.setGridLineVisible(False)
                axis_y.setMinorGridLineVisible(False)  # type: ignore[attr-defined]
            except Exception:
                pass

            # Theme-aware axis label colors: pure white in dark mode, dark
            # navy in light mode.
            label_color = QColor("#0f172a")  # light mode default
            app = QApplication.instance()
            if app is not None:
                try:
                    theme = str(app.property("theme") or "light")
                    if theme == "dark":
                        label_color = QColor("#ffffff")
                except Exception:
                    pass
            try:
                axis_x.setLabelsBrush(label_color)
                axis_y.setLabelsBrush(label_color)
            except Exception:
                pass

            chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
            chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)

            for s_obj in chart.series():
                try:
                    s_obj.attachAxis(axis_x)  # type: ignore[arg-type]
                    s_obj.attachAxis(axis_y)  # type: ignore[arg-type]
                except Exception:
                    pass

            chart_view = ShadowChartView(chart, shadow_specs, chart_card)
            chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)  # type: ignore[attr-defined]
            chart_view.setFrameShape(QFrame.Shape.NoFrame)  # type: ignore[name-defined]
            chart_view.setStyleSheet("background: transparent;")
            chart_layout.addWidget(chart_view, 1)
        else:
            placeholder = QLabel("אין נתוני היסטוריה להצגה", chart_card)
            placeholder.setObjectName("Subtitle")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chart_layout.addWidget(placeholder, 1)

        # Layout: top card 1/3 height, bottom card 2/3 height.
        main_col.addWidget(top_card, 1)
        main_col.addWidget(chart_card, 2)

    def on_route_activated(self) -> None:
        """Called by Router.navigate whenever this route becomes active."""
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)

    def _on_theme_changed(self, is_dark: bool) -> None:
        """Ensure chart colors update when switching between light/dark mode."""
        # Call base implementation to keep header/sidebar/theme button in sync.
        super()._on_theme_changed(is_dark)
        # Rebuild content so axis label colors and chart styling reflect
        # the current theme.
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)

    # --- Helpers for modifying savings inside the current account ---

    def _get_savings_accounts(self) -> List[SavingsAccount]:
        return [acc for acc in self._accounts if isinstance(acc, SavingsAccount)]

    def _replace_savings_account(
        self, original: SavingsAccount, updated: SavingsAccount
    ) -> None:
        """Replace one SavingsAccount instance inside self._accounts."""
        for i, acc in enumerate(self._accounts):
            if acc is original:
                self._accounts[i] = updated
                return
        # Fallback: replace by name if identity didn't match (e.g. reloaded)
        for i, acc in enumerate(self._accounts):
            if isinstance(acc, SavingsAccount) and acc.name == original.name:
                self._accounts[i] = updated
                return

    def _save_savings_accounts_and_refresh(self, selected_name: str) -> None:
        """Persist savings accounts to JSON, refresh sidebar + this page."""
        if not isinstance(self._provider, JsonFileAccountsProvider):
            return

        savings_accounts = self._get_savings_accounts()
        try:
            self._provider.save_savings_accounts(savings_accounts)
        except Exception:
            return

        # Reload all accounts from provider
        try:
            self._accounts = self._provider.list_accounts()
        except Exception:
            pass

        # Update sidebar with latest accounts
        if self._sidebar is not None and hasattr(self._sidebar, "update_accounts"):
            try:
                self._sidebar.update_accounts(self._accounts)  # type: ignore[arg-type]
            except Exception:
                pass

        # Ensure the same account remains selected
        try:
            self._app_context["selected_savings_account"] = selected_name
        except Exception:
            pass

        # Rebuild this page's content
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)

    def _handle_add_saving(self, account: SavingsAccount) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("הוסף חסכון")
        dlg.setModal(True)
        try:
            dlg.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        except Exception:
            pass

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # Use RTL layout so labels appear on the right and fields on the left.
        try:
            dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                dlg.setLayoutDirection(Qt.RightToLeft)  # type: ignore[attr-defined]
            except Exception:
                pass

        name_row = QHBoxLayout()
        name_label = QLabel("שם חסכון:", dlg)
        name_edit = QLineEdit(dlg)
        name_row.addWidget(name_label, 0)
        name_row.addWidget(name_edit, 1)

        amount_row = QHBoxLayout()
        amount_label = QLabel("סכום התחלתי:", dlg)
        amount_edit = QLineEdit(dlg)
        amount_row.addWidget(amount_label, 0)
        amount_row.addWidget(amount_edit, 1)

        # Date picker for the initial history record, defaulting to today.
        date_row = QHBoxLayout()
        date_label = QLabel("תאריך:", dlg)
        date_edit = QDateEdit(dlg)
        # Default to today; visual arrow indicator is provided via QSS. Also
        # flip the calendar popup to Right-To-Left so it opens aligned for
        # Hebrew layout (days and navigation appear RTL).
        try:
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat("dd/MM/yyyy")
            date_edit.setMinimumWidth(130)
            date_edit.setObjectName("DateEdit")
            date_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            date_edit.setDate(QDate.currentDate())
            # Use Hebrew/Israel locale and RTL for both the edit and popup so
            # the whole calendar (month name, days) is right-to-left.
            try:
                try:
                    heb = QLocale(QLocale.Language.Hebrew, QLocale.Country.Israel)  # type: ignore[attr-defined]
                except Exception:
                    heb = QLocale(QLocale.Hebrew, QLocale.Israel)  # type: ignore[attr-defined]
                date_edit.setLocale(heb)
                date_edit.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
                cal = date_edit.calendarWidget()
                if cal is not None:
                    cal.setLocale(heb)
                    cal.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            except Exception:
                pass
        except Exception:
            pass
        date_row.addWidget(date_label, 0)
        date_row.addWidget(date_edit, 1)

        error_label = QLabel("", dlg)
        error_label.setStyleSheet("color: #b91c1c;")
        error_label.setWordWrap(True)
        error_label.hide()

        buttons_row = QHBoxLayout()
        ok_btn = QPushButton("שמור", dlg)
        cancel_btn = QPushButton("ביטול", dlg)
        # In RTL, add cancel first so it appears on the right, and "שמור" on
        # the left as the primary action.
        buttons_row.addWidget(cancel_btn)
        buttons_row.addStretch(1)
        buttons_row.addWidget(ok_btn)

        layout.addLayout(name_row)
        layout.addLayout(amount_row)
        layout.addLayout(date_row)
        layout.addWidget(error_label)
        layout.addLayout(buttons_row)

        def on_accept() -> None:
            name = name_edit.text().strip()
            amount_text = amount_edit.text().replace(",", "").strip()
            if not name or not amount_text:
                error_label.setText("חובה למלא שם וסכום.")
                error_label.show()
                return
            try:
                amount_val = float(amount_text)
            except Exception:
                error_label.setText("סכום לא חוקי.")
                error_label.show()
                return

            # Date for the first history entry
            try:
                date_qt = date_edit.date()
                date_str = date_qt.toString("yyyy-MM-dd")
            except Exception:
                date_str = ""

            # Prevent duplicate saving names inside this account
            if any(s.name == name for s in account.savings):
                error_label.setText("קיים חסכון עם שם זהה בחשבון.")
                error_label.show()
                return

            snap = MoneySnapshot(date=date_str, amount=amount_val)
            new_savings = list(account.savings) + [
                Savings(name=name, amount=amount_val, history=[snap])
            ]
            updated_account = SavingsAccount(
                name=account.name,
                total_amount=0.0,
                is_liquid=account.is_liquid,
                savings=new_savings,
            )
            self._replace_savings_account(account, updated_account)
            dlg.accept()
            self._save_savings_accounts_and_refresh(account.name)

        ok_btn.clicked.connect(on_accept)  # type: ignore[arg-type]
        cancel_btn.clicked.connect(dlg.reject)  # type: ignore[arg-type]
        dlg.exec()

    def _handle_update_saving(self, account: SavingsAccount) -> None:
        if not account.savings:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("עדכן חסכון")
        dlg.setModal(True)
        try:
            dlg.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        except Exception:
            pass

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # RTL layout so each label is on the right of its input field.
        try:
            dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                dlg.setLayoutDirection(Qt.RightToLeft)  # type: ignore[attr-defined]
            except Exception:
                pass

        select_row = QHBoxLayout()
        select_label = QLabel("בחר חסכון:", dlg)
        savings_combo = QComboBox(dlg)
        for s in account.savings:
            savings_combo.addItem(s.name, s)
        select_row.addWidget(select_label, 0)
        select_row.addWidget(savings_combo, 1)

        amount_row = QHBoxLayout()
        amount_label = QLabel("סכום חדש:", dlg)
        amount_edit = QLineEdit(dlg)
        # Pre-fill with current amount of first saving
        try:
            first = account.savings[0]
            amount_edit.setText(str(first.amount))
        except Exception:
            pass
        amount_row.addWidget(amount_label, 0)
        amount_row.addWidget(amount_edit, 1)

        # Date picker for the new history record
        date_row = QHBoxLayout()
        date_label = QLabel("תאריך:", dlg)
        date_edit = QDateEdit(dlg)
        # Same RTL calendar behavior for the edit dialog.
        try:
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat("dd/MM/yyyy")
            date_edit.setMinimumWidth(130)
            date_edit.setObjectName("DateEdit")
            date_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
            date_edit.setDate(QDate.currentDate())
            # Same Hebrew/RTL locale behavior for the edit dialog.
            try:
                try:
                    heb = QLocale(QLocale.Language.Hebrew, QLocale.Country.Israel)  # type: ignore[attr-defined]
                except Exception:
                    heb = QLocale(QLocale.Hebrew, QLocale.Israel)  # type: ignore[attr-defined]
                date_edit.setLocale(heb)
                date_edit.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
                cal = date_edit.calendarWidget()
                if cal is not None:
                    cal.setLocale(heb)
                    cal.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            except Exception:
                pass
        except Exception:
            pass
        date_row.addWidget(date_label, 0)
        date_row.addWidget(date_edit, 1)

        error_label = QLabel("", dlg)
        error_label.setStyleSheet("color: #b91c1c;")
        error_label.setWordWrap(True)
        error_label.hide()

        buttons_row = QHBoxLayout()
        ok_btn = QPushButton("שמור", dlg)
        cancel_btn = QPushButton("ביטול", dlg)
        buttons_row.addWidget(cancel_btn)
        buttons_row.addStretch(1)
        buttons_row.addWidget(ok_btn)

        layout.addLayout(select_row)
        layout.addLayout(amount_row)
        layout.addLayout(date_row)
        layout.addWidget(error_label)
        layout.addLayout(buttons_row)

        def on_accept() -> None:
            idx = savings_combo.currentIndex()
            if idx < 0 or idx >= len(account.savings):
                return
            target_saving = account.savings[idx]
            amount_text = amount_edit.text().replace(",", "").strip()
            if not amount_text:
                error_label.setText("סכום לא יכול להיות ריק.")
                error_label.show()
                return
            try:
                amount_val = float(amount_text)
            except Exception:
                error_label.setText("סכום לא חוקי.")
                error_label.show()
                return

            # Use the chosen date for the new history entry
            try:
                date_qt = date_edit.date()
                date_str = date_qt.toString("yyyy-MM-dd")
            except Exception:
                date_str = ""

            # Append a new snapshot for this saving and update its current amount
            new_history = list(target_saving.history) + [
                MoneySnapshot(date=date_str, amount=amount_val)
            ]
            updated_saving = Savings(
                name=target_saving.name, amount=amount_val, history=new_history
            )
            new_savings = list(account.savings)
            new_savings[idx] = updated_saving
            updated_account = SavingsAccount(
                name=account.name,
                total_amount=0.0,
                is_liquid=account.is_liquid,
                savings=new_savings,
            )
            self._replace_savings_account(account, updated_account)
            dlg.accept()
            self._save_savings_accounts_and_refresh(account.name)

        ok_btn.clicked.connect(on_accept)  # type: ignore[arg-type]
        cancel_btn.clicked.connect(dlg.reject)  # type: ignore[arg-type]
        dlg.exec()

    def _handle_delete_saving(self, account: SavingsAccount) -> None:
        if not account.savings:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("מחק חסכון")
        dlg.setModal(True)
        try:
            dlg.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        except Exception:
            pass

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        # RTL layout so label and combo/date read correctly in Hebrew.
        try:
            dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                dlg.setLayoutDirection(Qt.RightToLeft)  # type: ignore[attr-defined]
            except Exception:
                pass

        select_row = QHBoxLayout()
        select_label = QLabel("בחר חסכון למחיקה:", dlg)
        savings_combo = QComboBox(dlg)
        for s in account.savings:
            savings_combo.addItem(s.name, s)
        select_row.addWidget(select_label, 0)
        select_row.addWidget(savings_combo, 1)

        warning = QLabel("האם אתה בטוח שברצונך למחוק חסכון זה?", dlg)
        warning.setWordWrap(True)

        buttons_row = QHBoxLayout()
        delete_btn = QPushButton("מחק", dlg)
        delete_btn.setObjectName("DeleteButton")
        cancel_btn = QPushButton("ביטול", dlg)
        # Cancel on the right, delete on the left.
        buttons_row.addWidget(cancel_btn)
        buttons_row.addStretch(1)
        buttons_row.addWidget(delete_btn)

        layout.addLayout(select_row)
        layout.addWidget(warning)
        layout.addLayout(buttons_row)

        def on_delete() -> None:
            idx = savings_combo.currentIndex()
            if idx < 0 or idx >= len(account.savings):
                return
            new_savings = list(account.savings)
            del new_savings[idx]
            updated_account = SavingsAccount(
                name=account.name,
                total_amount=0.0,
                is_liquid=account.is_liquid,
                savings=new_savings,
            )
            self._replace_savings_account(account, updated_account)
            dlg.accept()
            self._save_savings_accounts_and_refresh(account.name)

        delete_btn.clicked.connect(on_delete)  # type: ignore[arg-type]
        cancel_btn.clicked.connect(dlg.reject)  # type: ignore[arg-type]
        dlg.exec()
