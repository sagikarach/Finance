from __future__ import annotations

from typing import List, Optional

from ..models.bank_movement import BankMovement
from ..utils.formatting import format_currency
from ..qt import (
    QApplication,
    QLabel,
    QHeaderView,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    Qt,
)


class MovementsTableCard(QWidget):
    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._title = QLabel(title, self)
        self._title.setObjectName("Subtitle")
        try:
            self._title.setAlignment(
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
            )
        except Exception:
            pass
        layout.addWidget(self._title, 0)

        self._table = QTableWidget(self)
        self._table.setObjectName("MovementsTable")
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            ["תאריך", "סכום", "קטגוריה", "חשבון", "תיאור"]
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        try:
            self._table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
                Qt.ScrollBarPolicy.ScrollBarAlwaysOn
            )
            self._table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        except Exception:
            pass
        try:
            self._table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            rtl = getattr(Qt, "RightToLeft", None)
            if rtl is not None:
                try:
                    self._table.setLayoutDirection(rtl)
                except Exception:
                    pass
        try:
            self._table.setFrameShape(QFrame.Shape.NoFrame)
        except Exception:
            no_frame = getattr(QFrame, "NoFrame", None)
            if no_frame is not None:
                try:
                    self._table.setFrameShape(no_frame)
                except Exception:
                    pass

        self._apply_header_settings()
        self._apply_stylesheet()

        layout.addWidget(self._table, 1)

    def set_title(self, title: str) -> None:
        self._title.setText(title)

    def set_movements(self, movements: List[BankMovement]) -> None:
        self._table.setRowCount(len(movements))
        for row, movement in enumerate(movements):
            try:
                date_str = str(movement.date or "")
                display_amount = abs(float(movement.amount))
                category_str = str(movement.category or "")
                account_str = str(movement.account_name or "")
                desc_str = str(movement.description or "")
            except Exception:
                continue
            date_item = QTableWidgetItem(date_str)
            amount_item = QTableWidgetItem(format_currency(display_amount))
            category_item = QTableWidgetItem(category_str)
            account_item = QTableWidgetItem(account_str)
            desc_item = QTableWidgetItem(desc_str)

            try:
                if movement.amount > 0:
                    amount_item.setForeground(Qt.GlobalColor.darkGreen)
                else:
                    amount_item.setForeground(Qt.GlobalColor.darkRed)
            except Exception:
                pass

            self._table.setItem(row, 0, date_item)
            self._table.setItem(row, 1, amount_item)
            self._table.setItem(row, 2, category_item)
            self._table.setItem(row, 3, account_item)
            self._table.setItem(row, 4, desc_item)

    def _apply_header_settings(self) -> None:
        try:
            header = self._table.horizontalHeader()
            try:
                header.setDefaultAlignment(
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
                )
            except Exception:
                align_center = getattr(Qt, "AlignCenter", None)
                if align_center is not None:
                    try:
                        header.setDefaultAlignment(align_center)
                    except Exception:
                        pass

            for i in range(self._table.columnCount()):
                header_item = self._table.horizontalHeaderItem(i)
                if header_item is None:
                    continue
                try:
                    alignment_int = int(
                        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
                    )
                    header_item.setTextAlignment(alignment_int)
                except Exception:
                    align_center = getattr(Qt, "AlignCenter", None)
                    if align_center is not None:
                        try:
                            header_item.setTextAlignment(int(align_center))
                        except Exception:
                            pass

            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
            header.setStretchLastSection(False)
        except Exception:
            pass

    def _apply_stylesheet(self) -> None:
        try:
            is_dark = False
            try:
                app = QApplication.instance()
                if app is not None:
                    is_dark = str(app.property("theme") or "light") == "dark"
            except Exception:
                is_dark = False

            handle = "#4b5563" if is_dark else "#9fc6f7"
            handle_hover = "#6b7280" if is_dark else "#9fc6f7"

            qss = """
                QTableWidget#MovementsTable { border: none; gridline-color: transparent; }
                QTableWidget#MovementsTable::item { border: none; }
                QTableWidget#MovementsTable::viewport { background: transparent; }
                QTableWidget#MovementsTable QHeaderView::section {
                    border: none;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 4px 6px;
                    background: transparent;
                }
                QTableWidget#MovementsTable QHeaderView {
                    background: transparent;
                }
                QTableWidget#MovementsTable QTableCornerButton::section {
                    background: transparent;
                    border: none;
                }
                QTableWidget#MovementsTable::corner {
                    background: transparent;
                    border: none;
                }

                QTableWidget#MovementsTable QScrollBar:vertical {
                    background: transparent;
                    width: 8px;
                    margin: 8px 2px 8px 2px;
                    border: none;
                }
                QTableWidget#MovementsTable QScrollBar::handle:vertical {
                    background: __HANDLE__;
                    border-radius: 999px;
                    min-height: 24px;
                }
                QTableWidget#MovementsTable QScrollBar::handle:vertical:hover {
                    background: __HANDLE_HOVER__;
                }

                QTableWidget#MovementsTable QScrollBar:horizontal {
                    background: transparent;
                    height: 8px;
                    margin: 2px 8px 2px 8px;
                    border: none;
                }
                QTableWidget#MovementsTable QScrollBar::handle:horizontal {
                    background: __HANDLE__;
                    border-radius: 999px;
                    min-width: 24px;
                }
                QTableWidget#MovementsTable QScrollBar::handle:horizontal:hover {
                    background: __HANDLE_HOVER__;
                }
                QTableWidget#MovementsTable QScrollBar::add-line:vertical,
                QTableWidget#MovementsTable QScrollBar::sub-line:vertical,
                QTableWidget#MovementsTable QScrollBar::add-line:horizontal,
                QTableWidget#MovementsTable QScrollBar::sub-line:horizontal {
                    height: 0px;
                    width: 0px;
                    border: none;
                    background: transparent;
                }
                QTableWidget#MovementsTable QScrollBar::up-arrow,
                QTableWidget#MovementsTable QScrollBar::down-arrow,
                QTableWidget#MovementsTable QScrollBar::left-arrow,
                QTableWidget#MovementsTable QScrollBar::right-arrow {
                    background: none;
                    border: none;
                    width: 0px;
                    height: 0px;
                }
                """
            qss = qss.replace("__HANDLE__", handle).replace(
                "__HANDLE_HOVER__", handle_hover
            )
            self._table.setStyleSheet(qss)
        except Exception:
            pass
