from __future__ import annotations

from typing import List, Optional

from ..qt import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    Qt,
)
from ..models.notifications import Notification, NotificationStatus
from ..models.notifications_service import NotificationsService
from .dialog_utils import setup_standard_rtl_dialog, wrap_hebrew_rtl


class NotificationsDialog(QDialog):
    def __init__(
        self,
        *,
        service: NotificationsService,
        parent: Optional[QDialog] = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._items: List[Notification] = []

        layout = setup_standard_rtl_dialog(
            self, title="התראות", margins=(24, 20, 24, 20), spacing=12
        )
        self.setMinimumWidth(760)
        self.setMinimumHeight(520)

        header = QLabel("התראות", self)
        header.setObjectName("HeaderTitle")
        try:
            header.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass
        layout.addWidget(header)

        self._table = QTableWidget(self)
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["תאריך", "כותרת", "סטטוס", "הודעה"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.cellDoubleClicked.connect(self._on_double_clicked)
        layout.addWidget(self._table, 1)

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(12)

        dismiss_btn = QPushButton("התעלם", self)
        read_btn = QPushButton("סמן כנקרא", self)
        close_btn = QPushButton("סגור", self)

        dismiss_btn.clicked.connect(self._dismiss_selected)
        read_btn.clicked.connect(self._mark_selected_read)
        close_btn.clicked.connect(self.accept)

        buttons_row.addWidget(dismiss_btn)
        buttons_row.addWidget(read_btn)
        buttons_row.addStretch(1)
        buttons_row.addWidget(close_btn)
        layout.addLayout(buttons_row)

        self.refresh()

    def refresh(self) -> None:
        self._service.refresh()
        self._items = list(self._service.list_notifications())
        self._items.sort(key=lambda n: (n.created_at or ""), reverse=True)
        self._render()

    def _render(self) -> None:
        self._table.setRowCount(len(self._items))
        for row, n in enumerate(self._items):
            date_item = QTableWidgetItem(str(n.created_at or ""))
            title_item = QTableWidgetItem(wrap_hebrew_rtl(n.title))
            status_item = QTableWidgetItem(
                wrap_hebrew_rtl(self._status_label(n.status))
            )
            msg_item = QTableWidgetItem(wrap_hebrew_rtl(n.message))

            if n.status == NotificationStatus.UNREAD:
                font = title_item.font()
                try:
                    font.setBold(True)
                    title_item.setFont(font)
                    msg_item.setFont(font)
                except Exception:
                    pass

            self._table.setItem(row, 0, date_item)
            self._table.setItem(row, 1, title_item)
            self._table.setItem(row, 2, status_item)
            self._table.setItem(row, 3, msg_item)

        try:
            self._table.resizeColumnsToContents()
        except Exception:
            pass

    def _selected_index(self) -> Optional[int]:
        try:
            row = self._table.currentRow()
        except Exception:
            return None
        if row is None or row < 0 or row >= len(self._items):
            return None
        return int(row)

    def _mark_selected_read(self) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        n = self._items[idx]
        if n.status == NotificationStatus.UNREAD:
            self._service.mark_read(n.key)
        self.refresh()

    def _dismiss_selected(self) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        n = self._items[idx]
        self._service.dismiss(n.key)
        self.refresh()

    def _on_double_clicked(self, row: int, _col: int) -> None:
        if row < 0 or row >= len(self._items):
            return
        n = self._items[row]
        if n.status == NotificationStatus.UNREAD:
            self._service.mark_read(n.key)
            self.refresh()

    @staticmethod
    def _status_label(status: NotificationStatus) -> str:
        if status == NotificationStatus.UNREAD:
            return "לא נקרא"
        if status == NotificationStatus.READ:
            return "נקרא"
        if status == NotificationStatus.DISMISSED:
            return "הוסר"
        if status == NotificationStatus.RESOLVED:
            return "נפתר"
        return str(status.value)
