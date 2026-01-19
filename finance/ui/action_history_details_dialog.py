from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from typing import List, Callable, Optional, Optional as Opt, Any

from ..qt import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    Qt,
)
from ..models.action_history import (
    ActionHistory,
    Action,
    UploadOutcomeFileAction,
    AddIncomeMovementAction,
    AddOutcomeMovementAction,
)
from ..models.bank_movement import MovementType
from ..models.bank_movement_service import BankMovementService
from .dialog_utils import wrap_hebrew_rtl, unwrap_rtl


class ActionHistoryDetailsDialog(QDialog):
    def __init__(
        self,
        entry: ActionHistory,
        parent: Optional[QDialog] = None,
        categories: Opt[List[str]] = None,
        movement_service: Opt[BankMovementService] = None,
        on_saved: Opt[Callable[[], None]] = None,
        history_provider: Opt[Any] = None,
    ) -> None:
        super().__init__(parent)
        self._entry = entry
        self._categories = categories or []
        self._movement_service = movement_service
        self._on_saved = on_saved
        self._history_provider = history_provider
        self._expenses_table: Opt[QTableWidget] = None
        self._original_expenses: List[dict] = []

        self.setWindowTitle("פרטי פעולה")
        self.setModal(True)
        try:
            self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        except Exception:
            pass

        try:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                self.setLayoutDirection(Qt.RightToLeft)
            except Exception:
                pass

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        self.setMinimumWidth(700)
        self.setMinimumHeight(400)

        title_label = QLabel("פרטי פעולה", self)
        title_label.setObjectName("HeaderTitle")
        try:
            title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass
        layout.addWidget(title_label)

        meta_layout = QVBoxLayout()

        date_label = QLabel(f"תאריך: {entry.timestamp}", self)

        action_name_map = {
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
            "add_one_time_event": "יצירת אירוע חד־פעמי",
            "edit_one_time_event": "עריכת אירוע חד־פעמי",
            "delete_one_time_event": "מחיקת אירוע חד־פעמי",
            "assign_movement_to_one_time_event": "שיוך תנועה לאירוע",
            "unassign_movement_from_one_time_event": "הסרת שיוך תנועה מאירוע",
            "add_installment_plan": "יצירת תשלומים",
            "edit_installment_plan": "עריכת תשלומים",
            "delete_installment_plan": "מחיקת תשלומים",
        }
        action_key = entry.action.action_name
        action_title = action_name_map.get(action_key, action_key)
        type_label = QLabel(f"סוג פעולה: {action_title}", self)

        meta_layout.addWidget(date_label)
        meta_layout.addWidget(type_label)

        layout.addLayout(meta_layout)

        action = entry.action
        details_layout = QVBoxLayout()

        if isinstance(action, UploadOutcomeFileAction):
            header = QLabel(
                f"ייבוא קובץ: {action.file_name} ({action.expenses_count} הוצאות, סכום כולל {action.total_amount})",
                self,
            )
            details_layout.addWidget(header)

            expenses_data: List[dict] = []
            if self._movement_service is not None and action.movement_ids:
                try:
                    all_movements = self._movement_service.list_movements()
                    movements_by_id = {m.id: m for m in all_movements}

                    for movement_id in action.movement_ids:
                        movement = movements_by_id.get(movement_id)
                        if movement:
                            expenses_data.append(
                                {
                                    "id": movement.id,
                                    "date": movement.date,
                                    "amount": str(movement.amount),
                                    "category": movement.category,
                                    "type": movement.type.value,
                                    "description": movement.description or "",
                                }
                            )
                except Exception:
                    expenses_data = []

            if expenses_data:
                self._original_expenses = [dict(exp) for exp in expenses_data]

                expenses_table = QTableWidget(self)
                self._expenses_table = expenses_table
                expenses_table.setColumnCount(5)
                expenses_table.setRowCount(len(expenses_data))

                rtl_direction = None
                try:
                    rtl_direction = Qt.LayoutDirection.RightToLeft
                except Exception:
                    try:
                        rtl_direction = Qt.RightToLeft
                    except Exception:
                        pass

                if rtl_direction:
                    expenses_table.setLayoutDirection(rtl_direction)
                    viewport = expenses_table.viewport()
                    if viewport:
                        viewport.setLayoutDirection(rtl_direction)

                headers = ["תאריך", "סכום", "קטגוריה", "סוג", "תיאור"]
                expenses_table.setHorizontalHeaderLabels(headers)

                header_view = expenses_table.horizontalHeader()
                if rtl_direction:
                    header_view.setLayoutDirection(rtl_direction)
                try:
                    header_view.setDefaultAlignment(
                        Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
                    )
                except Exception:
                    try:
                        header_view.setDefaultAlignment(Qt.AlignCenter)
                    except Exception:
                        pass

                for row, exp in enumerate(expenses_data):
                    try:
                        date = str(exp.get("date", ""))
                        amount = str(exp.get("amount", ""))
                        category = str(exp.get("category", ""))
                        etype = str(exp.get("type", ""))
                        desc = str(exp.get("description", ""))

                        desc_item = QTableWidgetItem(wrap_hebrew_rtl(desc))
                        amount_item = QTableWidgetItem(amount)
                        date_item = QTableWidgetItem(date)

                        try:
                            alignment = (
                                Qt.AlignmentFlag.AlignCenter
                                | Qt.AlignmentFlag.AlignVCenter
                            )
                        except Exception:
                            alignment = Qt.AlignCenter

                        desc_item.setTextAlignment(alignment)
                        amount_item.setTextAlignment(alignment)
                        date_item.setTextAlignment(alignment)

                        try:
                            amount_value = float(amount)
                        except (ValueError, TypeError):
                            amount_value = 0.0
                        is_income = amount_value > 0
                        filtered_categories = self._get_categories_for_movement(
                            is_income
                        )

                        category_combo = QComboBox(self)
                        category_combo.addItems(
                            filtered_categories if filtered_categories else [category]
                        )
                        if category in filtered_categories:
                            category_combo.setCurrentText(category)
                        elif category:
                            category_combo.addItem(category)
                            category_combo.setCurrentText(category)
                        category_combo.setEditable(False)
                        try:
                            category_combo.setLayoutDirection(
                                Qt.LayoutDirection.RightToLeft
                            )
                        except Exception:
                            try:
                                category_combo.setLayoutDirection(Qt.RightToLeft)
                            except Exception:
                                pass
                        expenses_table.setCellWidget(row, 2, category_combo)

                        type_combo = QComboBox(self)
                        type_options = [
                            wrap_hebrew_rtl(MovementType.MONTHLY.value),
                            wrap_hebrew_rtl(MovementType.YEARLY.value),
                            wrap_hebrew_rtl(MovementType.ONE_TIME.value),
                        ]
                        type_combo.addItems(type_options)
                        current_type = unwrap_rtl(etype)
                        for i, opt in enumerate(type_options):
                            unwrapped_opt = unwrap_rtl(opt)
                            if (
                                unwrapped_opt == current_type
                                or unwrapped_opt in current_type
                                or current_type in unwrapped_opt
                            ):
                                type_combo.setCurrentIndex(i)
                                break
                        else:
                            type_combo.setCurrentIndex(0)
                        type_combo.setEditable(False)
                        try:
                            type_combo.setLayoutDirection(
                                Qt.LayoutDirection.RightToLeft
                            )
                        except Exception:
                            try:
                                type_combo.setLayoutDirection(Qt.RightToLeft)
                            except Exception:
                                pass
                        expenses_table.setCellWidget(row, 3, type_combo)

                        expenses_table.setItem(row, 0, date_item)
                        expenses_table.setItem(row, 1, amount_item)
                        expenses_table.setItem(row, 4, desc_item)
                    except Exception:
                        continue

                expenses_table.setAlternatingRowColors(True)
                expenses_table.setSelectionBehavior(
                    QTableWidget.SelectionBehavior.SelectRows
                )
                expenses_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

                expenses_table.resizeColumnsToContents()

                expenses_table.setColumnWidth(
                    0, max(100, expenses_table.columnWidth(0))
                )
                expenses_table.setColumnWidth(1, max(80, expenses_table.columnWidth(1)))
                expenses_table.setColumnWidth(
                    2, max(100, expenses_table.columnWidth(2))
                )
                expenses_table.setColumnWidth(3, max(80, expenses_table.columnWidth(3)))
                expenses_table.setColumnWidth(
                    4, max(200, expenses_table.columnWidth(4))
                )

                row_height = (
                    expenses_table.rowHeight(0) if expenses_table.rowCount() > 0 else 30
                )
                max_rows = min(10, len(expenses_data))
                expenses_table.setMinimumHeight((max_rows + 1) * row_height + 50)
                expenses_table.setMaximumHeight((max_rows + 1) * row_height + 50)

                details_layout.addWidget(expenses_table)
        elif isinstance(action, (AddIncomeMovementAction, AddOutcomeMovementAction)):
            if self._movement_service is not None and action.movement_id:
                try:
                    all_movements = self._movement_service.list_movements()
                    movements_by_id = {m.id: m for m in all_movements}
                    movement = movements_by_id.get(action.movement_id)

                    if movement:
                        expenses_table = QTableWidget(1, 5, self)
                        expenses_table.setHorizontalHeaderLabels(
                            ["תאריך", "סכום", "קטגוריה", "סוג", "תיאור"]
                        )
                        expenses_table.setAlternatingRowColors(True)
                        expenses_table.setEditTriggers(
                            QTableWidget.EditTrigger.NoEditTriggers
                        )
                        expenses_table.setSelectionBehavior(
                            QTableWidget.SelectionBehavior.SelectRows
                        )

                        try:
                            expenses_table.setLayoutDirection(
                                Qt.LayoutDirection.RightToLeft
                            )
                        except Exception:
                            pass

                        header_view = expenses_table.horizontalHeader()
                        try:
                            header_view.setDefaultAlignment(
                                Qt.AlignmentFlag.AlignRight
                                | Qt.AlignmentFlag.AlignVCenter
                            )
                        except Exception:
                            pass

                        row = 0
                        expenses_table.setItem(row, 0, QTableWidgetItem(movement.date))
                        expenses_table.setItem(
                            row, 1, QTableWidgetItem(str(movement.amount))
                        )

                        is_income = movement.amount > 0
                        filtered_categories = self._get_categories_for_movement(
                            is_income
                        )

                        category_combo = QComboBox(self)
                        category_combo.addItems(
                            filtered_categories
                            if filtered_categories
                            else [movement.category]
                        )
                        if movement.category in filtered_categories:
                            category_combo.setCurrentText(movement.category)
                        elif movement.category:
                            category_combo.addItem(movement.category)
                            category_combo.setCurrentText(movement.category)
                        category_combo.setEditable(False)
                        try:
                            category_combo.setLayoutDirection(
                                Qt.LayoutDirection.RightToLeft
                            )
                        except Exception:
                            pass
                        expenses_table.setCellWidget(row, 2, category_combo)

                        type_combo = QComboBox(self)
                        type_options = [
                            wrap_hebrew_rtl(mt.value) for mt in MovementType
                        ]
                        type_combo.addItems(type_options)
                        for i, opt in enumerate(type_options):
                            if unwrap_rtl(opt) == movement.type.value:
                                type_combo.setCurrentIndex(i)
                                break
                        type_combo.setEditable(False)
                        try:
                            type_combo.setLayoutDirection(
                                Qt.LayoutDirection.RightToLeft
                            )
                        except Exception:
                            pass
                        expenses_table.setCellWidget(row, 3, type_combo)

                        expenses_table.setItem(
                            row, 4, QTableWidgetItem(movement.description or "")
                        )

                        for col in range(5):
                            item = expenses_table.item(row, col)
                            if item:
                                try:
                                    item.setTextAlignment(
                                        Qt.AlignmentFlag.AlignRight
                                        | Qt.AlignmentFlag.AlignVCenter
                                    )
                                except Exception:
                                    pass

                        self._original_expenses = [
                            {
                                "id": movement.id,
                                "date": movement.date,
                                "amount": str(movement.amount),
                                "category": movement.category,
                                "type": movement.type.value,
                                "description": movement.description or "",
                            }
                        ]
                        self._expenses_table = expenses_table

                        expenses_table.resizeColumnsToContents()
                        expenses_table.setColumnWidth(
                            0, max(100, expenses_table.columnWidth(0))
                        )
                        expenses_table.setColumnWidth(
                            1, max(80, expenses_table.columnWidth(1))
                        )
                        expenses_table.setColumnWidth(
                            2, max(100, expenses_table.columnWidth(2))
                        )
                        expenses_table.setColumnWidth(
                            3, max(80, expenses_table.columnWidth(3))
                        )
                        expenses_table.setColumnWidth(
                            4, max(200, expenses_table.columnWidth(4))
                        )

                        details_layout.addWidget(expenses_table)
                except Exception:
                    pass

            if not self._expenses_table:
                if self._movement_service is not None and action.movement_id:
                    try:
                        all_movements = self._movement_service.list_movements()
                        movements_by_id = {m.id: m for m in all_movements}
                        movement = movements_by_id.get(action.movement_id)
                        if movement and movement.account_name:
                            account_label = QLabel(
                                f"חשבון: {movement.account_name}", self
                            )
                            details_layout.addWidget(account_label)
                    except Exception:
                        pass
        elif isinstance(action, Action) and is_dataclass(action):
            field_labels = {
                "amount": "סכום",
                "source_name": "חשבון מקור",
                "target_name": "חשבון יעד",
                "source_type": "סוג מקור",
                "target_type": "סוג יעד",
                "account_name": "שם חשבון",
                "is_liquid": "נזיל",
                "old_name": "שם קודם",
                "new_name": "שם חדש",
                "old_is_liquid": "נזיל קודם",
                "new_is_liquid": "נזיל חדש",
                "account_total_amount": "סכום בחשבון",
                "saving_name": "שם חסכון",
                "saving_amount": "סכום חסכון",
                "old_amount": "סכום קודם",
                "new_amount": "סכום חדש",
                "starter_amount": "סכום התחלתי",
                "category": "קטגוריה",
                "type": "סוג",
                "description": "תיאור",
                "file_name": "שם קובץ",
                "expenses_count": "מספר הוצאות",
                "total_amount": "סכום כולל",
                "plan_id": "מזהה תכנית",
                "plan_name": "שם תכנית",
                "vendor_query": "חיפוש ספק",
                "start_date": "תאריך התחלה",
                "payments_count": "מספר תשלומים",
                "original_amount": "סכום מקורי",
                "old_vendor_query": "חיפוש ספק קודם",
                "new_vendor_query": "חיפוש ספק חדש",
                "old_account_name": "חשבון קודם",
                "new_account_name": "חשבון חדש",
                "old_start_date": "תאריך התחלה קודם",
                "new_start_date": "תאריך התחלה חדש",
                "old_payments_count": "מספר תשלומים קודם",
                "new_payments_count": "מספר תשלומים חדש",
                "old_original_amount": "סכום מקורי קודם",
                "new_original_amount": "סכום מקורי חדש",
                "old_archived": "בארכיון קודם",
                "new_archived": "בארכיון חדש",
            }
            for field_info in fields(action):
                name = field_info.name
                if name in ("action_name", "success", "error_message"):
                    continue
                # Hide raw IDs from the details UI as well; show meaningful fields instead.
                if name == "id" or name.endswith("_id") or name.endswith("_ids"):
                    continue
                value = getattr(action, name, None)
                if value is None:
                    continue
                label_text = field_labels.get(name, name)
                details_label = QLabel(f"{label_text}: {value}", self)
                details_layout.addWidget(details_label)

            if getattr(action, "error_message", None):
                error_label = QLabel(f"שגיאה: {action.error_message}", self)
                details_layout.addWidget(error_label)

        layout.addLayout(details_layout)

        buttons_row = QHBoxLayout()
        buttons_row.addStretch(1)

        save_btn = None
        action = self._entry.action
        if (
            (isinstance(action, UploadOutcomeFileAction) and action.movement_ids)
            or (
                isinstance(action, (AddIncomeMovementAction, AddOutcomeMovementAction))
                and action.movement_id
            )
        ) and self._movement_service is not None:
            save_btn = QPushButton("שמור שינויים", self)
            save_btn.clicked.connect(self._on_save_changes)
            buttons_row.addWidget(save_btn)

        close_btn = QPushButton("סגור", self)
        buttons_row.addWidget(close_btn)
        layout.addLayout(buttons_row)

        close_btn.clicked.connect(self.accept)

    def _get_categories_for_movement(self, is_income: bool) -> List[str]:
        if self._movement_service is None:
            return self._categories or []
        try:
            return self._movement_service.list_categories(is_income)
        except Exception:
            return self._categories or []

    def _on_save_changes(self) -> None:
        if not self._expenses_table or self._movement_service is None:
            return

        try:
            all_movements = self._movement_service.list_movements()

            action = self._entry.action

            if isinstance(action, (AddIncomeMovementAction, AddOutcomeMovementAction)):
                if not action.movement_id:
                    return

                movement = None
                movement_index = -1
                for i, m in enumerate(all_movements):
                    if m.id == action.movement_id:
                        movement = m
                        movement_index = i
                        break

                if movement is None:
                    return

                category_widget = self._expenses_table.cellWidget(0, 2)
                type_widget = self._expenses_table.cellWidget(0, 3)

                if not category_widget or not type_widget:
                    return

                if not isinstance(category_widget, QComboBox) or not isinstance(
                    type_widget, QComboBox
                ):
                    return

                new_category = category_widget.currentText()
                new_type_str = unwrap_rtl(type_widget.currentText())

                try:
                    new_type = MovementType(new_type_str)
                except Exception:
                    if "חודש" in new_type_str:
                        new_type = MovementType.MONTHLY
                    elif "שנת" in new_type_str:
                        new_type = MovementType.YEARLY
                    else:
                        new_type = MovementType.ONE_TIME

                updated_movement = replace(
                    movement,
                    category=new_category,
                    type=new_type,
                )
                all_movements[movement_index] = updated_movement

                if self._movement_service is not None:
                    self._movement_service.save_movements(
                        all_movements, changed_movements=[updated_movement]
                    )

                from ..qt import QDialog, QVBoxLayout, QLabel, QPushButton

                success_dlg = QDialog(self)
                success_dlg.setWindowTitle("שמירה")
                success_layout = QVBoxLayout(success_dlg)
                success_label = QLabel("השינויים נשמרו בהצלחה", success_dlg)
                success_btn = QPushButton("אישור", success_dlg)
                success_btn.clicked.connect(success_dlg.accept)
                success_layout.addWidget(success_label)
                success_layout.addWidget(success_btn)
                success_dlg.exec()

                if self._on_saved:
                    try:
                        self._on_saved()
                    except Exception:
                        pass

                return

            if not isinstance(action, UploadOutcomeFileAction):
                return

            account_name = action.account_name

            updated_count = 0
            for row in range(self._expenses_table.rowCount()):
                if row >= len(self._original_expenses):
                    continue

                original_exp = self._original_expenses[row]
                movement_id = original_exp.get("id")

                category_widget = self._expenses_table.cellWidget(row, 2)
                type_widget = self._expenses_table.cellWidget(row, 3)

                if not category_widget or not type_widget:
                    continue

                if not isinstance(category_widget, QComboBox) or not isinstance(
                    type_widget, QComboBox
                ):
                    continue

                category_combo = category_widget
                type_combo = type_widget

                new_category = category_combo.currentText()
                new_type_str = unwrap_rtl(type_combo.currentText())

                try:
                    new_type = MovementType(new_type_str)
                except Exception:
                    if "חודש" in new_type_str:
                        new_type = MovementType.MONTHLY
                    elif "שנת" in new_type_str:
                        new_type = MovementType.YEARLY
                    else:
                        new_type = MovementType.ONE_TIME

                movement_found = False
                for i, movement in enumerate(all_movements):
                    if movement_id and movement.id == movement_id:
                        updated_movement = replace(
                            movement,
                            category=new_category,
                            type=new_type,
                        )
                        all_movements[i] = updated_movement
                        updated_count += 1
                        movement_found = True
                        break
                    elif not movement_id:
                        orig_date = str(original_exp.get("date", ""))
                        orig_amount = float(original_exp.get("amount", 0.0))
                        orig_desc = str(original_exp.get("description", ""))

                        if (
                            movement.account_name == account_name
                            and movement.date == orig_date
                            and abs(movement.amount - orig_amount) < 0.01
                            and str(movement.description or "") == orig_desc
                        ):
                            updated_movement = replace(
                                movement,
                                category=new_category,
                                type=new_type,
                            )
                            all_movements[i] = updated_movement
                            updated_count += 1
                            movement_found = True
                            break

                if not movement_found:
                    pass

            if updated_count > 0:
                if self._movement_service is not None:
                    changed: List[Any] = []
                    try:
                        for m in all_movements:
                            if getattr(m, "account_name", None) == account_name:
                                changed.append(m)
                    except Exception:
                        changed = []
                    self._movement_service.save_movements(
                        all_movements, changed_movements=changed or None
                    )

                if self._on_saved:
                    try:
                        self._on_saved()
                    except Exception:
                        pass

                from ..qt import QDialog, QVBoxLayout, QLabel, QPushButton

                success_dlg = QDialog(self)
                success_dlg.setWindowTitle("שמירה")
                success_layout = QVBoxLayout(success_dlg)
                success_label = QLabel(
                    f"נשמרו {updated_count} הוצאות בהצלחה", success_dlg
                )
                success_btn = QPushButton("אישור", success_dlg)
                success_btn.clicked.connect(success_dlg.accept)
                success_layout.addWidget(success_label)
                success_layout.addWidget(success_btn)
                success_dlg.exec()

        except Exception as e:
            from ..qt import QDialog, QVBoxLayout, QLabel, QPushButton

            error_dlg = QDialog(self)
            error_dlg.setWindowTitle("שגיאה")
            error_layout = QVBoxLayout(error_dlg)
            error_label = QLabel(f"שגיאה בשמירה: {str(e)}", error_dlg)
            error_btn = QPushButton("אישור", error_dlg)
            error_btn.clicked.connect(error_dlg.accept)
            error_layout.addWidget(error_label)
            error_layout.addWidget(error_btn)
            error_dlg.exec()
