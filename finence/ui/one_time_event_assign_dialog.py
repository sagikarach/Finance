from __future__ import annotations

from typing import List, Optional

from ..qt import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    Qt,
)
from ..models.bank_movement import BankMovement
from ..models.one_time_event import OneTimeEvent
from ..models.one_time_events_service import OneTimeEventsService
from .dialog_utils import setup_standard_rtl_dialog, wrap_hebrew_rtl


class OneTimeEventAssignDialog(QDialog):
    def __init__(
        self,
        *,
        service: OneTimeEventsService,
        event: OneTimeEvent,
        parent: Optional[QDialog] = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._event = event
        self._assigned: List[BankMovement] = []
        self._unassigned: List[BankMovement] = []

        layout = setup_standard_rtl_dialog(
            self,
            title=f"שיוך תנועות לאירוע: {event.name}",
            margins=(24, 20, 24, 20),
            spacing=12,
        )
        self.setMinimumWidth(980)
        self.setMinimumHeight(620)

        header = QLabel(wrap_hebrew_rtl(f"שיוך תנועות לאירוע: {event.name}"), self)
        header.setObjectName("HeaderTitle")
        try:
            header.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass
        layout.addWidget(header)

        tables_row = QHBoxLayout()
        tables_row.setSpacing(12)

        left = QWidget(self)
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(6)
        left_lay.addWidget(QLabel("לא משויכות", left))
        self._unassigned_table = self._make_table(left)
        left_lay.addWidget(self._unassigned_table, 1)

        right = QWidget(self)
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(6)
        right_lay.addWidget(QLabel("משויכות לאירוע", right))
        self._assigned_table = self._make_table(right)
        right_lay.addWidget(self._assigned_table, 1)

        tables_row.addWidget(left, 1)
        tables_row.addWidget(right, 1)
        layout.addLayout(tables_row, 1)

        controls = QHBoxLayout()
        controls.setSpacing(10)
        assign_btn = QPushButton("← שייך", self)
        unassign_btn = QPushButton("הסר שיוך →", self)
        refresh_btn = QPushButton("רענן", self)
        close_btn = QPushButton("סגור", self)

        assign_btn.clicked.connect(self._assign_selected)
        unassign_btn.clicked.connect(self._unassign_selected)
        refresh_btn.clicked.connect(self.refresh)
        close_btn.clicked.connect(self.accept)

        controls.addWidget(refresh_btn)
        controls.addStretch(1)
        controls.addWidget(unassign_btn)
        controls.addWidget(assign_btn)
        controls.addStretch(1)
        controls.addWidget(close_btn)
        layout.addLayout(controls)

        self.refresh()

    def refresh(self) -> None:
        assigned, unassigned = self._service.movements_for_event(self._event)
        self._assigned = list(assigned)
        self._unassigned = list(unassigned)
        self._fill_table(self._assigned_table, self._assigned)
        self._fill_table(self._unassigned_table, self._unassigned)

    def _make_table(self, parent: QWidget) -> QTableWidget:
        t = QTableWidget(parent)
        t.setColumnCount(5)
        t.setHorizontalHeaderLabels(["תאריך", "סכום", "קטגוריה", "חשבון", "תיאור"])
        t.horizontalHeader().setStretchLastSection(True)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        return t

    def _fill_table(self, table: QTableWidget, items: List[BankMovement]) -> None:
        table.setRowCount(len(items))
        for row, m in enumerate(items):
            table.setItem(row, 0, QTableWidgetItem(str(m.date)))
            table.setItem(row, 1, QTableWidgetItem(str(m.amount)))
            table.setItem(row, 2, QTableWidgetItem(str(m.category)))
            table.setItem(row, 3, QTableWidgetItem(str(m.account_name)))
            table.setItem(
                row, 4, QTableWidgetItem(wrap_hebrew_rtl(m.description or ""))
            )
        try:
            table.resizeColumnsToContents()
        except Exception:
            pass

    def _selected_movement_id(
        self, table: QTableWidget, items: List[BankMovement]
    ) -> Optional[str]:
        try:
            row = table.currentRow()
        except Exception:
            return None
        if row < 0 or row >= len(items):
            return None
        return getattr(items[row], "id", None)

    def _assign_selected(self) -> None:
        movement_id = self._selected_movement_id(
            self._unassigned_table, self._unassigned
        )
        if not movement_id:
            return
        self._service.assign_movement(movement_id, self._event.id)
        self.refresh()

    def _unassign_selected(self) -> None:
        movement_id = self._selected_movement_id(self._assigned_table, self._assigned)
        if not movement_id:
            return
        self._service.assign_movement(movement_id, None)
        self.refresh()
