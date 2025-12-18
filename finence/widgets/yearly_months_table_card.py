from __future__ import annotations

from typing import Any, List, Optional, cast

from ..models.yearly_report import MonthTypeSummary
from ..qt import (
    QApplication,
    QColor,
    QFont,
    QFrame,
    QHeaderView,
    QPen,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    Qt,
)
from ..utils.formatting import format_currency


class SeparatorItemDelegate(QStyledItemDelegate):
    def __init__(self, parent, separator_rows):
        super().__init__(parent)
        self._separator_rows = separator_rows

    def paint(self, painter, option, index):
        try:
            super().paint(painter, option, index)
            row = index.row()
            col = index.column()

            if row in self._separator_rows and col == 1:
                app = QApplication.instance()
                is_dark = False
                if app is not None:
                    is_dark = str(app.property("theme") or "light") == "dark"
                separator_color = "#334155" if is_dark else "#e1ecfb"

                color = QColor(separator_color)
                pen = QPen(color, 3)
                parent = self.parent()
                if parent is not None:
                    viewport = parent.viewport()
                    if viewport is not None:
                        viewport_width = viewport.width()
                        full_rect = option.rect
                        try:
                            full_rect.setLeft(0)
                            full_rect.setWidth(viewport_width)
                        except Exception:
                            pass
                        y = full_rect.bottom()
                        painter.save()
                        try:
                            try:
                                painter.setClipping(False)
                            except Exception:
                                pass
                            painter.setPen(pen)
                            painter.drawLine(full_rect.left(), y, full_rect.right(), y)
                        finally:
                            painter.restore()
        except Exception:
            try:
                super().paint(painter, option, index)
            except Exception:
                pass


class YearlyMonthsTableCard(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._table = QTableWidget(self)
        self._table.setObjectName("YearlyMonthsTable")
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(
            [
                "חודש",
                "הכנסות",
                "הוצאות",
                "יתרה",
            ]
        )
        try:
            self._table.horizontalHeader().setObjectName("YearlyMonthsHeader")
        except Exception:
            pass
        self._table.verticalHeader().setVisible(False)
        try:
            self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        except Exception:
            try:
                fallback = getattr(QTableWidget, "NoEditTriggers", None)
                if fallback is not None:
                    self._table.setEditTriggers(cast(Any, fallback))
            except Exception:
                pass
        try:
            self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        except Exception:
            try:
                fallback = getattr(QTableWidget, "NoSelection", None)
                if fallback is not None:
                    self._table.setSelectionMode(cast(Any, fallback))
            except Exception:
                pass
        try:
            self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        except Exception:
            try:
                fallback = getattr(QTableWidget, "SelectRows", None)
                if fallback is not None:
                    self._table.setSelectionBehavior(cast(Any, fallback))
            except Exception:
                pass
        try:
            self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        except Exception:
            try:
                fallback = getattr(Qt, "NoFocus", None)
                if fallback is not None:
                    self._table.setFocusPolicy(cast(Any, fallback))
            except Exception:
                pass
        try:
            self._table.setShowGrid(False)
            self._table.setGridStyle(Qt.PenStyle.NoPen)
        except Exception:
            try:
                self._table.setShowGrid(False)
            except Exception:
                pass
        try:
            self._table.setWordWrap(False)
        except Exception:
            pass
        try:
            self._table.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            self._table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        except Exception:
            try:
                fallback = getattr(Qt, "ScrollBarAsNeeded", None)
                if fallback is not None:
                    self._table.setHorizontalScrollBarPolicy(cast(Any, fallback))
                    self._table.setVerticalScrollBarPolicy(cast(Any, fallback))
            except Exception:
                pass
        try:
            self._table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            pass
        try:
            self._table.setFrameShape(QFrame.Shape.NoFrame)
        except Exception:
            try:
                fallback = getattr(QFrame, "NoFrame", None)
                if fallback is not None:
                    self._table.setFrameShape(cast(Any, fallback))
            except Exception:
                pass

        self._apply_header_settings()
        self._apply_stylesheet()

        self._separator_rows: set[int] = set()
        self._delegate = None

        try:
            self._delegate = SeparatorItemDelegate(self._table, self._separator_rows)
            self._table.setItemDelegate(self._delegate)
        except Exception:
            pass

        layout.addWidget(self._table, 1)

    def set_rows(self, rows: List[MonthTypeSummary]) -> None:
        self._separator_rows.clear()

        month_names = [
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

        type_names = ["חודשי", "שנתי", "חד פעמי"]
        type_data = [
            ("income_monthly", "expense_monthly"),
            ("income_yearly", "expense_yearly"),
            ("income_one_time", "expense_one_time"),
        ]

        total_rows = len(rows) * 3
        self._table.setRowCount(total_rows)

        row_idx = 0
        for row in rows:
            month_name = (
                month_names[row.month - 1] if 1 <= row.month <= 12 else str(row.month)
            )
            month_display = month_name
            overall_balance = row.net_balance

            month_item = QTableWidgetItem(month_display)
            try:
                month_item.setTextAlignment(
                    int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
                )
            except Exception:
                pass
            try:
                font = month_item.font()
                font.setPointSize(int(font.pointSize() * 1.6))
                month_item.setFont(font)
            except Exception:
                pass
            self._table.setItem(row_idx, 0, month_item)
            try:
                self._table.setSpan(row_idx, 0, 3, 1)
            except Exception:
                pass

            if overall_balance < 0:
                abs_formatted = format_currency(abs(overall_balance), use_compact=True)
                balance_text = abs_formatted.replace("₪", "") + "-₪"
            else:
                balance_text = format_currency(overall_balance, use_compact=True)
            net_item = QTableWidgetItem(balance_text)
            try:
                net_item.setTextAlignment(
                    int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
                )
            except Exception:
                pass
            try:
                if overall_balance >= 0:
                    net_item.setForeground(Qt.GlobalColor.darkGreen)
                else:
                    net_item.setForeground(Qt.GlobalColor.darkRed)
            except Exception:
                pass
            try:
                font = net_item.font()
                font.setPointSize(int(font.pointSize() * 1.6))
                net_item.setFont(font)
            except Exception:
                pass
            self._table.setItem(row_idx, 3, net_item)
            try:
                self._table.setSpan(row_idx, 3, 3, 1)
            except Exception:
                pass

            for type_idx, (type_name, (income_attr, expense_attr)) in enumerate(
                zip(type_names, type_data)
            ):
                income_val = getattr(row, income_attr)
                expense_val = getattr(row, expense_attr)

                income_text = (
                    f"{type_name}: {format_currency(income_val, use_compact=True)}"
                )
                expense_text = (
                    f"{type_name}: {format_currency(expense_val, use_compact=True)}"
                )

                income_item = QTableWidgetItem(income_text)
                expense_item = QTableWidgetItem(expense_text)

                items = [income_item, expense_item]
                for c, it in enumerate(items):
                    try:
                        it.setTextAlignment(
                            int(
                                Qt.AlignmentFlag.AlignHCenter
                                | Qt.AlignmentFlag.AlignVCenter
                            )
                        )
                    except Exception:
                        pass
                    self._table.setItem(row_idx, c + 1, it)

                row_idx += 1

                if type_idx == 2 and row_idx < total_rows:
                    self._separator_rows.add(row_idx - 1)

        if self._delegate is not None:
            try:
                self._delegate._separator_rows = self._separator_rows.copy()
            except Exception:
                pass
        try:
            self._table.viewport().update()
            self._table.viewport().repaint()
            self._table.update()
            self._table.repaint()
        except Exception:
            pass

    def _apply_header_settings(self) -> None:
        try:
            header = self._table.horizontalHeader()
            try:
                header.setDefaultAlignment(
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
                )
            except Exception:
                pass

            for i in range(self._table.columnCount()):
                item = self._table.horizontalHeaderItem(i)
                if item is None:
                    continue
                try:
                    item.setTextAlignment(
                        int(
                            Qt.AlignmentFlag.AlignHCenter
                            | Qt.AlignmentFlag.AlignVCenter
                        )
                    )
                except Exception:
                    pass
                if i == 0 or i == 3:
                    try:
                        font = QFont()
                        try:
                            existing_font = item.font()
                            if existing_font is not None:
                                font = existing_font
                        except Exception:
                            pass
                        try:
                            base_size = font.pointSize()
                            if base_size <= 0:
                                base_size = 12
                            font.setPointSize(int(base_size * 1.6))
                        except Exception:
                            try:
                                font.setPointSize(19)
                            except Exception:
                                pass
                        item.setFont(font)
                    except Exception:
                        pass

            try:
                fixed_mode = QHeaderView.ResizeMode.Fixed
                header.setSectionResizeMode(0, fixed_mode)
                header.resizeSection(0, 140)
            except Exception:
                pass
            try:
                stretch_mode = QHeaderView.ResizeMode.Stretch
                header.setSectionResizeMode(1, stretch_mode)
                header.setSectionResizeMode(2, stretch_mode)
            except Exception:
                pass
            try:
                fixed_mode = QHeaderView.ResizeMode.Fixed
                header.setSectionResizeMode(3, fixed_mode)
                header.resizeSection(3, 120)
            except Exception:
                pass
            header.setStretchLastSection(False)
        except Exception:
            pass

    def _apply_stylesheet(self) -> None:
        try:
            app = QApplication.instance()
            is_dark = False
            if app is not None:
                is_dark = str(app.property("theme") or "light") == "dark"

            handle = "#4b5563" if is_dark else "#9fc6f7"
            handle_hover = "#6b7280" if is_dark else "#9fc6f7"
            header_line = "#e1ecfb" if not is_dark else "#334155"

            qss = f"""
                QTableWidget#YearlyMonthsTable {{ border: none; gridline-color: transparent; }}
                QTableWidget#YearlyMonthsTable::item {{ border: none; }}
                QTableWidget#YearlyMonthsTable::viewport {{ background: transparent; }}

                QHeaderView#YearlyMonthsHeader {{
                    background: transparent;
                    border: none;
                    border-bottom: 2px solid {header_line};
                }}
                QTableWidget#YearlyMonthsTable QHeaderView::section {{
                    border: none;
                    font-weight: 600;
                    padding: 4px 6px;
                    background: transparent;
                }}
                QTableWidget#YearlyMonthsTable QHeaderView::section:nth-child(1),
                QTableWidget#YearlyMonthsTable QHeaderView::section:nth-child(4) {{
                    font-size: 30px;
                }}
                QTableWidget#YearlyMonthsTable QHeaderView::section:nth-child(2),
                QTableWidget#YearlyMonthsTable QHeaderView::section:nth-child(3) {{
                    font-size: 30px;
                }}
                QTableWidget#YearlyMonthsTable QHeaderView {{ background: transparent; }}
                QTableWidget#YearlyMonthsTable QTableCornerButton::section {{ background: transparent; border: none; }}
                QTableWidget#YearlyMonthsTable::corner {{ background: transparent; border: none; }}
                """
            self._table.setStyleSheet(qss)

            try:
                vbar = self._table.verticalScrollBar()
                if vbar is not None:
                    vbar.setStyleSheet(
                        f"""
                        QScrollBar:vertical {{ background: transparent; width: 8px; margin: 8px 2px 8px 2px; border: none; }}
                        QScrollBar::handle:vertical {{ background: {handle}; border-radius: 999px; min-height: 24px; }}
                        QScrollBar::handle:vertical:hover {{ background: {handle_hover}; }}
                        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ background: transparent; border: none; height: 0px; width: 0px; }}
                        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; border: none; }}
                        QScrollBar::up-arrow, QScrollBar::down-arrow {{ background: none; border: none; width: 0px; height: 0px; }}
                        """
                    )
            except Exception:
                pass

            try:
                hbar = self._table.horizontalScrollBar()
                if hbar is not None:
                    hbar.setStyleSheet(
                        f"""
                        QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 2px 8px 2px 8px; border: none; }}
                        QScrollBar::handle:horizontal {{ background: {handle}; border-radius: 999px; min-width: 24px; }}
                        QScrollBar::handle:horizontal:hover {{ background: {handle_hover}; }}
                        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ background: transparent; border: none; height: 0px; width: 0px; }}
                        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; border: none; }}
                        QScrollBar::left-arrow, QScrollBar::right-arrow {{ background: none; border: none; width: 0px; height: 0px; }}
                        """
                    )
            except Exception:
                pass
        except Exception:
            pass
