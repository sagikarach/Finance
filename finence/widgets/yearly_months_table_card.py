from __future__ import annotations

from typing import List, Optional

from ..models.yearly_report import MonthTypeSummary
from ..qt import (
    QApplication,
    QLabel,
    QFrame,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    Qt,
)
from ..utils.formatting import format_currency


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

        title = QLabel("סיכום חודשי", self)
        title.setObjectName("Subtitle")
        try:
            title.setAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
            )
        except Exception:
            pass
        layout.addWidget(title, 0)

        self._table = QTableWidget(self)
        self._table.setObjectName("YearlyMonthsTable")
        self._table.setColumnCount(8)
        self._table.setHorizontalHeaderLabels(
            [
                "חודש",
                "הכנסות חודשי",
                "הכנסות שנתי",
                "הכנסות חד פעמי",
                "הוצאות חודשי",
                "הוצאות שנתי",
                "הוצאות חד פעמי",
                "יתרה",
            ]
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(
            getattr(
                QTableWidget.EditTrigger, "NoEditTriggers", QTableWidget.NoEditTriggers
            )
        )
        self._table.setSelectionMode(
            getattr(QTableWidget.SelectionMode, "NoSelection", QTableWidget.NoSelection)
        )
        self._table.setSelectionBehavior(
            getattr(
                QTableWidget.SelectionBehavior, "SelectRows", QTableWidget.SelectRows
            )
        )
        try:
            self._table.setFocusPolicy(getattr(Qt.FocusPolicy, "NoFocus", Qt.NoFocus))
        except Exception:
            pass
        try:
            self._table.setShowGrid(False)
            self._table.setGridStyle(getattr(Qt.PenStyle, "NoPen", Qt.NoPen))
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
                getattr(Qt.ScrollBarPolicy, "ScrollBarAlwaysOn", Qt.ScrollBarAlwaysOn)
            )
            self._table.setVerticalScrollBarPolicy(
                getattr(Qt.ScrollBarPolicy, "ScrollBarAsNeeded", Qt.ScrollBarAsNeeded)
            )
        except Exception:
            pass
        try:
            self._table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            pass
        try:
            self._table.setFrameShape(getattr(QFrame.Shape, "NoFrame", QFrame.NoFrame))
        except Exception:
            pass

        self._apply_header_settings()
        self._apply_stylesheet()

        layout.addWidget(self._table, 1)

    def set_rows(self, rows: List[MonthTypeSummary]) -> None:
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

        self._table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            name = (
                month_names[row.month - 1] if 1 <= row.month <= 12 else str(row.month)
            )
            month_item = QTableWidgetItem(f"{name} {row.year}")
            in_m = QTableWidgetItem(
                format_currency(row.income_monthly, use_compact=True)
            )
            in_y = QTableWidgetItem(
                format_currency(row.income_yearly, use_compact=True)
            )
            in_o = QTableWidgetItem(
                format_currency(row.income_one_time, use_compact=True)
            )
            ex_m = QTableWidgetItem(
                format_currency(row.expense_monthly, use_compact=True)
            )
            ex_y = QTableWidgetItem(
                format_currency(row.expense_yearly, use_compact=True)
            )
            ex_o = QTableWidgetItem(
                format_currency(row.expense_one_time, use_compact=True)
            )
            net = QTableWidgetItem(format_currency(row.net_balance, use_compact=True))

            try:
                net_val = float(row.net_balance)
                if net_val >= 0:
                    net.setForeground(Qt.GlobalColor.darkGreen)
                else:
                    net.setForeground(Qt.GlobalColor.darkRed)
            except Exception:
                pass

            items = [month_item, in_m, in_y, in_o, ex_m, ex_y, ex_o, net]
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
                self._table.setItem(r, c, it)

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

            for i in range(self._table.columnCount()):
                header.setSectionResizeMode(
                    i,
                    getattr(
                        QHeaderView.ResizeMode,
                        "ResizeToContents",
                        QHeaderView.ResizeToContents,
                    ),
                )
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

            qss = f"""
                QTableWidget#YearlyMonthsTable {{ border: none; gridline-color: transparent; }}
                QTableWidget#YearlyMonthsTable::item {{ border: none; }}
                QTableWidget#YearlyMonthsTable::viewport {{ background: transparent; }}
                QTableWidget#YearlyMonthsTable QHeaderView::section {{
                    border: none;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 4px 6px;
                    background: transparent;
                }}
                QTableWidget#YearlyMonthsTable QHeaderView {{ background: transparent; }}
                QTableWidget#YearlyMonthsTable QTableCornerButton::section {{ background: transparent; border: none; }}
                QTableWidget#YearlyMonthsTable::corner {{ background: transparent; border: none; }}

                QTableWidget#YearlyMonthsTable QScrollBar:vertical {{
                    background: transparent;
                    width: 8px;
                    margin: 8px 2px 8px 2px;
                    border: none;
                }}
                QTableWidget#YearlyMonthsTable QScrollBar::handle:vertical {{
                    background: {handle};
                    border-radius: 999px;
                    min-height: 24px;
                }}
                QTableWidget#YearlyMonthsTable QScrollBar::handle:vertical:hover {{
                    background: {handle_hover};
                }}
                QTableWidget#YearlyMonthsTable QScrollBar:horizontal {{
                    background: transparent;
                    height: 8px;
                    margin: 2px 8px 2px 8px;
                    border: none;
                }}
                QTableWidget#YearlyMonthsTable QScrollBar::handle:horizontal {{
                    background: {handle};
                    border-radius: 999px;
                    min-width: 24px;
                }}
                QTableWidget#YearlyMonthsTable QScrollBar::handle:horizontal:hover {{
                    background: {handle_hover};
                }}
                QTableWidget#YearlyMonthsTable QScrollBar::add-line:vertical,
                QTableWidget#YearlyMonthsTable QScrollBar::sub-line:vertical,
                QTableWidget#YearlyMonthsTable QScrollBar::add-line:horizontal,
                QTableWidget#YearlyMonthsTable QScrollBar::sub-line:horizontal {{
                    background: transparent;
                    height: 0px;
                    width: 0px;
                    border: none;
                }}
                QTableWidget#YearlyMonthsTable QScrollBar::up-arrow,
                QTableWidget#YearlyMonthsTable QScrollBar::down-arrow,
                QTableWidget#YearlyMonthsTable QScrollBar::left-arrow,
                QTableWidget#YearlyMonthsTable QScrollBar::right-arrow {{
                    background: none;
                    border: none;
                    width: 0px;
                    height: 0px;
                }}
                """
            self._table.setStyleSheet(qss)
        except Exception:
            pass
