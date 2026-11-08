from __future__ import annotations

from typing import Callable, List, Optional

from ...models.bank_movement_service import BankMovementService
from ...models.category_tree import active_tree
from ...models.description_categories import group_expense_descriptions
from ...qt import QLabel, QPushButton, QVBoxLayout, QWidget, Qt
from ...utils.safe import QT_ERRORS


class CategoriesCard(QWidget):
    """Settings section: summary of how expense descriptions are classified,
    and the entry to the bulk "סיווג תיאורי הוצאות" window."""

    def __init__(
        self,
        *,
        parent: QWidget,
        movement_service: BankMovementService,
        categories_getter: Callable[[], List[str]],
        on_saved: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("ContentPanel")
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except QT_ERRORS:
            pass
        self._service = movement_service
        self._categories_getter = categories_getter
        self._on_saved = on_saved

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        title = QLabel("קטגוריות", self)
        try:
            title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except QT_ERRORS:
            pass
        layout.addWidget(title)

        explain = QLabel(
            "כל תיאור הוצאה מופיע פעם אחת. סמנו תיאורים, בחרו קטגוריה ושמרו — "
            "הקטגוריה תעודכן בכל התנועות עם אותו תיאור (סכומים, תאריכים וחשבונות "
            "לא משתנים).",
            self,
        )
        explain.setWordWrap(True)
        explain.setObjectName("Subtitle")
        layout.addWidget(explain)

        self._summary = QLabel(self)
        self._summary.setObjectName("Subtitle")
        layout.addWidget(self._summary)

        btn = QPushButton("סיווג תיאורי הוצאות…", self)
        btn.setObjectName("SaveButton")
        btn.clicked.connect(self._open)
        layout.addWidget(btn)
        layout.addStretch(1)
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        try:
            groups = group_expense_descriptions(self._service.list_movements())
        except QT_ERRORS:
            self._summary.setText("")
            return
        tree = active_tree()
        uncl = sum(1 for g in groups if g.is_unclassified())
        parent = sum(1 for g in groups if g.is_parent_only(tree))
        self._summary.setText(
            f"{len(groups)} תיאורים ייחודיים · {uncl} בטרם סווג · "
            f"{parent} בקטגוריה ראשית בלבד"
        )

    def _rebuild_training(self) -> None:
        """Teach the import classifier the new categories now (one rebuild per
        save, ~0.1 s), instead of waiting for the next sync."""
        try:
            from ...models.workspace_ml_trainer import WorkspaceMLTrainer

            classifier = getattr(self._service, "classifier", None)
            if classifier is None:
                return
            WorkspaceMLTrainer().rebuild_training_file(
                movements=list(self._service.list_movements()), classifier=classifier
            )
        except QT_ERRORS:
            pass

    def _open(self) -> None:
        from ...ui.expense_descriptions_dialog import ExpenseDescriptionsDialog

        def saved() -> None:
            self._refresh_summary()
            self._rebuild_training()
            if self._on_saved is not None:
                self._on_saved()

        try:
            categories = list(self._categories_getter())
        except QT_ERRORS:
            categories = []
        dlg = ExpenseDescriptionsDialog(
            movement_service=self._service,
            categories=categories,
            parent=self,
            on_saved=saved,
        )
        dlg.exec()
