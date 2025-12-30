from __future__ import annotations

from typing import Any, List, Optional, Callable

from ..qt import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    Qt,
    QSizePolicy,
    QColor,
    QApplication,
    QStyledItemDelegate,
    QPainter,
    QTimer,
    QPalette,
)
from ..models.action_history import ActionHistory
from ..ui.action_history_details_dialog import ActionHistoryDetailsDialog


class ColoredItemDelegate:
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        self._row_colors: dict[int, QColor] = {}
        self._parent = parent

    def set_row_color(self, row: int, color: Optional[QColor]) -> None:
        if color is None:
            self._row_colors.pop(row, None)
        else:
            self._row_colors[row] = color

    def get_row_color(self, row: int) -> Optional[QColor]:
        return self._row_colors.get(row)

    def clear_colors(self) -> None:
        self._row_colors.clear()


if QStyledItemDelegate is not None and QPainter is not None:

    class ColoredItemDelegateImpl(QStyledItemDelegate):
        def __init__(self, parent: Optional[QWidget] = None) -> None:
            super().__init__(parent)
            self._row_colors: dict[int, QColor] = {}

        def set_row_color(self, row: int, color: Optional[QColor]) -> None:
            if color is None:
                self._row_colors.pop(row, None)
            else:
                self._row_colors[row] = color
            try:
                parent = self.parent()
                if parent is not None:
                    parent.viewport().update()  # type: ignore[attr-defined]
            except Exception:
                pass

        def paint(self, painter: Any, option: Any, index: Any) -> None:
            try:
                row = index.row()
                col = index.column()

                if col == 0 and row in self._row_colors:
                    color = self._row_colors[row]
                    try:
                        parent = self.parent()
                        if parent is not None:
                            viewport = parent.viewport()  # type: ignore[attr-defined]
                            if viewport is not None:
                                viewport_width = viewport.width()
                                full_rect = option.rect
                                full_rect.setLeft(0)
                                full_rect.setWidth(viewport_width)
                                painter.fillRect(full_rect, color)
                    except Exception:
                        painter.fillRect(option.rect, color)

                super().paint(painter, option, index)
            except Exception:
                try:
                    super().paint(painter, option, index)
                except Exception:
                    pass
else:
    ColoredItemDelegateImpl = None  # type: ignore


class ActionHistoryTable(QWidget):
    HOVER_COLOR_LIGHT = "#c6defd"
    PRESS_COLOR_LIGHT = "#dcecff"
    DEFAULT_COLOR_LIGHT = "#bfdbfe"
    ALTERNATE_COLOR_LIGHT = "#f8fafc"

    HOVER_COLOR_DARK = "#1f2937"
    PRESS_COLOR_DARK = "#020617"
    DEFAULT_COLOR_DARK = "#111827"
    ALTERNATE_COLOR_DARK = "#020617"

    def __init__(
        self,
        history: Optional[List[ActionHistory]] = None,
        max_rows: int = 10,
        parent: Optional[QWidget] = None,
        categories: Optional[List[str]] = None,
        movement_provider: Optional[object] = None,
        on_saved: Optional[Callable[[], None]] = None,
        history_provider: Optional[object] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ActionHistoryTable")
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        self._history: List[ActionHistory] = list(history or [])
        self._max_rows = max_rows
        self._row_base_bg: dict[int, QColor] = {}
        self._categories = categories or []
        self._movement_provider = movement_provider
        self._on_saved = on_saved
        self._history_provider = history_provider

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 0)
        layout.setSpacing(12)

        title_label = QLabel("היסטוריית פעולות", self)
        title_label.setObjectName("Subtitle")
        try:
            title_label.setAlignment(
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            )
        except Exception:
            pass
        layout.addWidget(title_label, 0)

        self._table = QTableWidget(self)
        self._table.setObjectName("ActionHistoryTableWidget")

        try:
            self._table.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self._table.setAutoFillBackground(False)
            self._table.setStyleSheet(
                "QTableWidget#ActionHistoryTableWidget { background: transparent; }"
            )
            self._table.setContentsMargins(0, 8, 0, 0)
        except Exception:
            pass

        self._table.setColumnCount(2)
        self._table.setRowCount(0)
        self._table.horizontalHeader().setVisible(False)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._table.setMouseTracking(True)

        try:
            v_header = self._table.verticalHeader()
            v_header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
            v_header.setDefaultSectionSize(40)
        except Exception:
            pass

        if ColoredItemDelegateImpl is not None:
            self._delegate = ColoredItemDelegateImpl(self._table)
            self._table.setItemDelegate(self._delegate)

        try:
            self._table.setHorizontalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )
            self._table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        except Exception:
            pass

        try:
            header = self._table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setStretchLastSection(False)
        except Exception:
            pass

        self._hovered_row = -1
        self._pressed_row = -1

        try:
            self._table.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
        except Exception:
            pass

        try:
            self._table.itemEntered.connect(self._on_item_entered)
            self._table.itemPressed.connect(self._on_item_pressed)
            self._table.itemClicked.connect(self._on_item_clicked)
            self._table.installEventFilter(self)
        except Exception:
            pass

        layout.addWidget(self._table, 1)

        self._update_table()

    def _is_dark_theme(self) -> bool:
        app = QApplication.instance()
        if app is None:
            return False
        try:
            theme_value = app.property("theme")
            if isinstance(theme_value, str):
                return theme_value.lower() == "dark"
        except Exception:
            pass
        try:
            palette = app.palette()  # type: ignore[attr-defined]
            try:
                window_color = palette.color(QPalette.ColorRole.Window)
            except Exception:
                try:
                    window_color = palette.window().color()
                except Exception:
                    return False
            try:
                return getattr(window_color, "lightness", lambda: 255)() < 128
            except Exception:
                return False
        except Exception:
            return False

    def set_history(self, history: List[ActionHistory]) -> None:
        self._history = history
        self._update_table()

    def _on_item_entered(self, item: QTableWidgetItem) -> None:
        try:
            if item is None:
                if self._hovered_row >= 0:
                    self._update_row_hover(self._hovered_row, False)
                    self._hovered_row = -1
                return
            new_row = item.row()
            if new_row != self._hovered_row:
                self._update_row_hover(self._hovered_row, False)
                self._hovered_row = new_row
                self._update_row_hover(self._hovered_row, True)
        except Exception:
            pass

    def _on_item_pressed(self, item: QTableWidgetItem) -> None:
        if item is not None:
            self._handle_row_press(item.row())

    def _on_item_clicked(self, item: QTableWidgetItem) -> None:
        if item is None:
            return
        row = item.row()
        self._handle_row_press(row)
        try:
            entry = item.data(Qt.ItemDataRole.UserRole)
            if not isinstance(entry, ActionHistory):
                return

            dialog = ActionHistoryDetailsDialog(
                entry,
                None,
                categories=self._categories,
                movement_provider=self._movement_provider,
                on_saved=self._on_saved,
                history_provider=self._history_provider,
            )
            dialog.exec()
        except Exception:
            pass

    def _handle_row_press(self, row: int) -> None:
        if row < 0 or row >= self._table.rowCount():
            return

        try:
            was_hovered = row == self._hovered_row
            self._pressed_row = row

            self._update_row_hover(row, was_hovered, True)
            QApplication.processEvents()
            self._table.viewport().update()
            self._table.viewport().repaint()

            def restore_color() -> None:
                try:
                    self._pressed_row = -1
                    self._update_row_hover(row, was_hovered, False)
                    self._table.viewport().update()
                    self._table.viewport().repaint()
                except Exception:
                    pass

            if QTimer is not None:
                timer = QTimer(self)
                timer.setSingleShot(True)
                timer.timeout.connect(restore_color)
                timer.start(400)
            else:
                restore_color()
        except Exception:
            pass

    def eventFilter(self, source: Any, event: Any) -> bool:
        try:
            if source == self._table:
                event_type = getattr(event, "type", lambda: None)()
                if hasattr(Qt, "EventType"):
                    if event_type == getattr(Qt.EventType, "Leave", None):
                        if self._hovered_row >= 0:
                            self._update_row_hover(self._hovered_row, False)
                            self._hovered_row = -1
        except Exception:
            pass
        return super().eventFilter(source, event)

    def _update_row_hover(
        self, row: int, is_hovered: bool, is_selected: Optional[bool] = None
    ) -> None:
        if row < 0 or row >= self._table.rowCount():
            return

        try:
            is_dark = self._is_dark_theme()

            if row == self._pressed_row:
                bg = QColor(
                    self.PRESS_COLOR_DARK if is_dark else self.PRESS_COLOR_LIGHT
                )
            elif is_hovered:
                bg = QColor(
                    self.HOVER_COLOR_DARK if is_dark else self.HOVER_COLOR_LIGHT
                )
            else:
                base = self._row_base_bg.get(row)
                if base is not None:
                    bg = base
                else:
                    alternate_bg = QColor(
                        self.ALTERNATE_COLOR_DARK
                        if is_dark
                        else self.ALTERNATE_COLOR_LIGHT
                    )
                    default_bg = QColor(
                        self.DEFAULT_COLOR_DARK if is_dark else self.DEFAULT_COLOR_LIGHT
                    )
                    bg = alternate_bg if row % 2 == 1 else default_bg

            if self._delegate is not None:
                self._delegate.set_row_color(row, bg)
                for col in range(self._table.columnCount()):
                    item = self._table.item(row, col)
                    if item is not None:
                        item.setBackground(QColor(0, 0, 0, 0))
                self._table.viewport().update()
                self._table.viewport().repaint()
            else:
                for col in range(self._table.columnCount()):
                    item = self._table.item(row, col)
                    if item is not None:
                        item.setBackground(bg)
        except Exception:
            pass

    def _update_table(self) -> None:
        if not self._history:
            self._table.setRowCount(0)
            return

        latest_history = list(reversed(self._history[-self._max_rows :]))
        self._table.setRowCount(len(latest_history))
        self._row_base_bg.clear()

        action_name_map: dict[str, str] = {
            "transfer": "העברת כסף",
            "add_savings_account": "הוספת חסכון",
            "edit_savings_account": "עריכת חסכון",
            "delete_savings_account": "מחיקת חסכון",
            "add_saving": "הוספת סוג חסכון",
            "edit_saving": "עריכת סוג חסכון",
            "delete_saving": "מחיקת סוג חסכון",
            "activate_bank_account": "הפעלת חשבון",
            "deactivate_bank_account": "ביטול חשבון",
            "set_starter_amount": "הגדרת סכום התחלתי",
            "add_income_movement": "הוספת הכנסה",
            "add_outcome_movement": "הוספת הוצאה",
            "delete_movement": "מחיקת תנועה",
            "upload_outcome_file": "ייבוא קובץ הוצאות",
            "add_one_time_event": "יצירת אירוע חד־פעמי",
            "edit_one_time_event": "עריכת אירוע חד־פעמי",
            "delete_one_time_event": "מחיקת אירוע חד־פעמי",
            "assign_movement_to_one_time_event": "שיוך תנועה לאירוע",
            "unassign_movement_from_one_time_event": "הסרת שיוך תנועה מאירוע",
        }

        try:
            is_dark = self._is_dark_theme()
            default_bg = QColor(
                self.DEFAULT_COLOR_DARK if is_dark else self.DEFAULT_COLOR_LIGHT
            )
        except Exception:
            default_bg = QColor(self.DEFAULT_COLOR_LIGHT)

        for row, entry in enumerate(latest_history):
            action_name = action_name_map.get(
                entry.action.action_name, entry.action.action_name
            )
            date_str = entry.timestamp

            action_item = QTableWidgetItem(action_name)
            action_item.setData(Qt.ItemDataRole.UserRole, entry)
            try:
                action_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
            except Exception:
                pass

            date_item = QTableWidgetItem(date_str)
            date_item.setData(Qt.ItemDataRole.UserRole, entry)
            try:
                date_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
            except Exception:
                pass

            self._table.setItem(row, 0, action_item)
            self._table.setItem(row, 1, date_item)

            row_bg = default_bg
            self._row_base_bg[row] = row_bg

            if self._delegate is not None:
                self._delegate.set_row_color(row, row_bg)
                try:
                    action_item.setBackground(QColor(0, 0, 0, 0))
                    date_item.setBackground(QColor(0, 0, 0, 0))
                except Exception:
                    pass
            else:
                try:
                    action_item.setBackground(row_bg)
                    date_item.setBackground(row_bg)
                except Exception:
                    try:
                        action_item.setBackground(row_bg)
                    except Exception:
                        pass
                    try:
                        date_item.setBackground(row_bg)
                    except Exception:
                        pass
