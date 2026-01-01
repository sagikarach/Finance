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
from ..models.notifications import Notification, NotificationStatus, NotificationType
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

        read_btn = QPushButton("סמן כנקרא", self)
        unread_btn = QPushButton("סמן כלא נקרא", self)
        resolve_btn = QPushButton("סמן כטופל", self)
        close_btn = QPushButton("סגור", self)

        read_btn.clicked.connect(self._mark_selected_read)
        unread_btn.clicked.connect(self._mark_selected_unread)
        resolve_btn.clicked.connect(self._resolve_selected)
        close_btn.clicked.connect(self.accept)

        buttons_row.addWidget(read_btn)
        buttons_row.addWidget(unread_btn)
        buttons_row.addWidget(resolve_btn)
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

    def _mark_selected_unread(self) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        n = self._items[idx]
        if n.status != NotificationStatus.UNREAD:
            self._service.mark_unread(n.key)
        self.refresh()

    def _resolve_selected(self) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        n = self._items[idx]
        self._service.resolve(n.key)
        self.refresh()

    def _open_selected_details(self) -> bool:
        idx = self._selected_index()
        if idx is None:
            return False
        n = self._items[idx]
        ctx = dict(getattr(n, "context", {}) or {})

        movement_id = str(ctx.get("movement_id", "") or "").strip()
        movement_ids = ctx.get("movement_ids", None)
        if isinstance(movement_ids, list):
            ids_list = [
                str(x or "").strip() for x in movement_ids if str(x or "").strip()
            ]
        else:
            ids_list = []

        if movement_id:
            m = self._service.get_movement_by_id(movement_id)
            if m is None:
                dlg = QDialog(self)
                lay = setup_standard_rtl_dialog(
                    dlg, title="פרטי הוצאה", margins=(24, 20, 24, 20), spacing=12
                )
                lay.addWidget(QLabel("לא נמצא פירוט הוצאה (ייתכן שנמחקה).", dlg))
                close_btn = QPushButton("סגור", dlg)
                close_btn.clicked.connect(dlg.accept)
                row = QHBoxLayout()
                row.addStretch(1)
                row.addWidget(close_btn)
                lay.addLayout(row)
                dlg.exec()
                return True

            dlg = QDialog(self)
            lay = setup_standard_rtl_dialog(
                dlg, title="פרטי הוצאה", margins=(24, 20, 24, 20), spacing=10
            )

            def add_line(label: str, value: str) -> None:
                row = QHBoxLayout()
                row.setSpacing(10)
                label_widget = QLabel(f"{label}:", dlg)
                label_widget.setObjectName("Subtitle")
                v = QLabel(wrap_hebrew_rtl(value), dlg)
                v.setWordWrap(True)
                row.addWidget(label_widget, 0)
                row.addWidget(v, 1)
                lay.addLayout(row)

            add_line("מזהה", str(getattr(m, "id", "") or ""))
            add_line("תאריך", str(getattr(m, "date", "") or ""))
            add_line("חשבון", str(getattr(m, "account_name", "") or ""))
            add_line("סכום", str(getattr(m, "amount", "") or ""))
            add_line("קטגוריה", str(getattr(m, "category", "") or ""))
            try:
                t = getattr(m, "type", None)
                t_str = str(getattr(t, "value", t) or "")
            except Exception:
                t_str = ""
            add_line("סוג", t_str)
            add_line("תיאור", str(getattr(m, "description", "") or ""))
            add_line("העברה", "כן" if bool(getattr(m, "is_transfer", False)) else "לא")
            add_line("אירוע", str(getattr(m, "event_id", "") or ""))

            close_btn = QPushButton("סגור", dlg)
            close_btn.clicked.connect(dlg.accept)
            row = QHBoxLayout()
            row.addStretch(1)
            row.addWidget(close_btn)
            lay.addLayout(row)
            dlg.exec()
            return True

        if n.type == NotificationType.MISSING_MONTHLY_UPLOAD:
            try:
                y = int(ctx.get("year", 0) or 0)
            except Exception:
                y = 0
            try:
                mth = int(ctx.get("month", 0) or 0)
            except Exception:
                mth = 0
            ym = f"{y:04d}-{mth:02d}" if y and mth else ""

            dlg = QDialog(self)
            lay = setup_standard_rtl_dialog(
                dlg, title="פרטי התראה", margins=(24, 20, 24, 20), spacing=12
            )
            msg = (
                f"לא הועלה קובץ הוצאות עבור החודש: {ym}"
                if ym
                else "לא הועלה קובץ הוצאות עבור חודש כלשהו."
            )
            lbl = QLabel(wrap_hebrew_rtl(msg), dlg)
            lbl.setWordWrap(True)
            lay.addWidget(lbl)
            close_btn = QPushButton("סגור", dlg)
            close_btn.clicked.connect(dlg.accept)
            row = QHBoxLayout()
            row.addStretch(1)
            row.addWidget(close_btn)
            lay.addLayout(row)
            dlg.exec()
            return True

        if n.type == NotificationType.EVENT_OVER_BUDGET:
            name = str(ctx.get("event_name", "") or "").strip()
            try:
                budget = float(ctx.get("budget", 0.0) or 0.0)
            except Exception:
                budget = 0.0
            try:
                spent = float(ctx.get("spent", 0.0) or 0.0)
            except Exception:
                spent = 0.0
            try:
                over = float(ctx.get("over", 0.0) or 0.0)
            except Exception:
                over = max(0.0, spent - budget)

            dlg = QDialog(self)
            lay = setup_standard_rtl_dialog(
                dlg, title="פרטי התראה", margins=(24, 20, 24, 20), spacing=12
            )

            def add_line(label: str, value: str) -> None:
                row = QHBoxLayout()
                row.setSpacing(10)
                label_widget = QLabel(f"{label}:", dlg)
                label_widget.setObjectName("Subtitle")
                v = QLabel(wrap_hebrew_rtl(value), dlg)
                v.setWordWrap(True)
                row.addWidget(label_widget, 0)
                row.addWidget(v, 1)
                lay.addLayout(row)

            add_line("אירוע", name or "אירוע")
            add_line("תקציב", f"{budget:,.0f}")
            add_line("הוצאות", f"{spent:,.0f}")
            add_line("חריגה", f"{over:,.0f}")

            close_btn = QPushButton("סגור", dlg)
            close_btn.clicked.connect(dlg.accept)
            row = QHBoxLayout()
            row.addStretch(1)
            row.addWidget(close_btn)
            lay.addLayout(row)
            dlg.exec()
            return True

        if ids_list:
            moves = self._service.get_movements_by_ids(ids_list)
            dlg = QDialog(self)
            lay = setup_standard_rtl_dialog(
                dlg, title="פרטי הוצאות", margins=(24, 20, 24, 20), spacing=10
            )
            if not moves:
                lay.addWidget(QLabel("לא נמצאו הוצאות.", dlg))
            else:
                for m in moves:
                    line = (
                        f"{getattr(m, 'date', '')} | {getattr(m, 'account_name', '')} | "
                        f"{getattr(m, 'amount', '')} | {getattr(m, 'category', '')} | "
                        f"{getattr(m, 'description', '')}"
                    )
                    lbl = QLabel(wrap_hebrew_rtl(str(line)), dlg)
                    lbl.setWordWrap(True)
                    lay.addWidget(lbl)
            close_btn = QPushButton("סגור", dlg)
            close_btn.clicked.connect(dlg.accept)
            row = QHBoxLayout()
            row.addStretch(1)
            row.addWidget(close_btn)
            lay.addLayout(row)
            dlg.exec()
            return True

        return False

    def _on_double_clicked(self, row: int, _col: int) -> None:
        if row < 0 or row >= len(self._items):
            return
        try:
            self._table.setCurrentCell(row, 0)
        except Exception:
            pass
        opened = False
        try:
            opened = bool(self._open_selected_details())
        except Exception:
            opened = False
        if opened:
            return
        try:
            n = self._items[row]
            if n.status == NotificationStatus.UNREAD:
                self._service.mark_read(n.key)
                self.refresh()
        except Exception:
            pass

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
