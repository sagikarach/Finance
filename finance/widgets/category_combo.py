"""A category dropdown whose list is a collapsible tree.

It stays a normal ``QComboBox`` for everything else (items, data, current
index, ``activated``), so existing code keeps working; only the popup differs:
each parent category is one row with an expand arrow, and its subcategories are
shown only after the user presses the arrow. Clicking a parent's name selects
the parent itself (a parent-only category is valid). Items that are not in the
hierarchy (custom names, "add new…" entries) are listed as top-level rows.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..models.category_tree import CategoryTree, active_tree
from ..qt import (
    QApplication,
    QComboBox,
    QFrame,
    QIcon,
    QPixmap,
    QSize,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    Qt,
)
from ..utils.safe import QT_ERRORS

_INDEX_ROLE = Qt.ItemDataRole.UserRole + 1
_ARROW_PX = 14


def _is_dark() -> bool:
    app = QApplication.instance()
    try:
        return str(app.property("theme") or "light") == "dark" if app else False
    except QT_ERRORS:
        return False


def _icon(name: str) -> Any:
    from ..utils.icons import make_icon

    # rendered at 2x so it stays crisp on Retina screens
    return make_icon(name, size=_ARROW_PX * 2, is_dark=_is_dark())


def _blank_icon() -> Any:
    pm = QPixmap(_ARROW_PX * 2, _ARROW_PX * 2)
    pm.fill(Qt.GlobalColor.transparent)
    return QIcon(pm)


class _CategoryTree(QTreeWidget):
    """Tree with our own always-visible chevron (macOS hides native tree
    arrows until hover). Clicking the chevron toggles the category; clicking
    the name selects it."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._closed_icon = _icon(
            "disclosure_left" if self.layoutDirection() == Qt.LayoutDirection.RightToLeft
            or (parent is not None and parent.layoutDirection() == Qt.LayoutDirection.RightToLeft)
            else "disclosure_right"
        )
        self._open_icon = _icon("disclosure_down")
        self._toggled_on_press = False
        self.itemExpanded.connect(lambda it: it.setIcon(0, self._open_icon))
        self.itemCollapsed.connect(lambda it: it.setIcon(0, self._closed_icon))

    def decorate(self, item: Any) -> None:
        item.setIcon(0, self._open_icon if item.isExpanded() else self._closed_icon)

    def _on_arrow(self, item: Any, x: int) -> bool:
        if item is None or item.childCount() == 0:
            return False
        rect = self.visualItemRect(item)
        zone = _ARROW_PX + 14
        if self.layoutDirection() == Qt.LayoutDirection.RightToLeft:
            return x >= rect.right() - zone
        return x <= rect.left() + zone

    def mousePressEvent(self, event: Any) -> None:  # noqa: N802 (Qt naming)
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        item = self.itemAt(pos)
        if self._on_arrow(item, pos.x()):
            item.setExpanded(not item.isExpanded())
            self._toggled_on_press = True
            event.accept()
            return
        self._toggled_on_press = False
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: Any) -> None:  # noqa: N802 (Qt naming)
        if self._toggled_on_press:
            self._toggled_on_press = False
            event.accept()
            return
        super().mouseReleaseEvent(event)


class CategoryComboBox(QComboBox):
    def __init__(self, parent: Any = None, *, hierarchical: bool = True) -> None:
        super().__init__(parent)
        self._hierarchical = hierarchical
        self._popup: Optional[Any] = None
        self.tree_widget: Optional[Any] = None  # the open popup's tree (tests)

    # ── popup ──
    def showPopup(self) -> None:  # noqa: N802 (Qt naming)
        tree = active_tree() if self._hierarchical else None
        if not tree or not self._any_in_tree(tree):
            super().showPopup()
            return
        self.hidePopup()
        popup = QFrame(self, Qt.WindowType.Popup)
        popup.setObjectName("CategoryPopup")
        try:
            popup.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except QT_ERRORS:
            pass
        lay = QVBoxLayout(popup)
        lay.setContentsMargins(4, 4, 4, 4)
        tw = _CategoryTree(popup)
        tw.setHeaderHidden(True)
        tw.setRootIsDecorated(False)  # we draw our own chevrons (always visible)
        tw.setExpandsOnDoubleClick(False)  # only the arrow expands
        tw.setIndentation(22)
        tw.setIconSize(QSize(_ARROW_PX, _ARROW_PX))
        tw.setStyleSheet("QTreeWidget::item { padding: 5px 4px; }")
        try:
            tw.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except QT_ERRORS:
            pass
        self._build_items(tw, tree)
        tw.itemClicked.connect(lambda item, _col: self._choose(item))
        tw.itemActivated.connect(lambda item, _col: self._choose(item))
        lay.addWidget(tw)

        rows = tw.topLevelItemCount()
        row_h = max(26, tw.sizeHintForRow(0) if rows else 26)
        popup.resize(max(self.width(), 260), min(420, rows * row_h + 16))
        popup.move(self.mapToGlobal(self.rect().bottomLeft()))
        self._popup = popup
        self.tree_widget = tw
        popup.show()
        tw.setFocus()

    def hidePopup(self) -> None:  # noqa: N802 (Qt naming)
        if self._popup is not None:
            try:
                self._popup.close()
                self._popup.deleteLater()
            except QT_ERRORS:
                pass
            self._popup = None
            self.tree_widget = None
        super().hidePopup()

    # ── helpers ──
    def _any_in_tree(self, tree: CategoryTree) -> bool:
        return any(
            isinstance(self.itemData(i), str) and tree.by_name(self.itemData(i)) is not None
            for i in range(self.count())
        )

    def _build_items(self, tw: Any, tree: CategoryTree) -> None:
        parents: Dict[str, Any] = {}
        current = self.currentIndex()
        current_item = None
        for i in range(self.count()):
            data = self.itemData(i)
            name = data if isinstance(data, str) else None
            node = tree.by_name(name) if name else None
            label = node.name if node is not None else self.itemText(i).strip()
            parent_node = tree.parent_of(node.name) if node is not None else None
            if parent_node is not None and parent_node.name in parents:
                item = QTreeWidgetItem(parents[parent_node.name], [label])
            else:
                item = QTreeWidgetItem(tw, [label])
                if node is not None and not node.parent_id:
                    parents[node.name] = item
                    if tree.is_parent(node.name):
                        font = item.font(0)
                        font.setBold(True)
                        item.setFont(0, font)
            item.setData(0, _INDEX_ROLE, i)
            if item.parent() is None:
                # chevron later if it gets children; blank keeps names aligned
                item.setIcon(0, _blank_icon())
            if i == current:
                current_item = item
        for item in parents.values():
            if item.childCount():
                tw.decorate(item)
        if current_item is not None:
            # Highlight the current choice without expanding anything: a
            # selected subcategory is shown through its (collapsed) parent.
            shown = current_item.parent() or current_item
            tw.setCurrentItem(shown)

    def _choose(self, item: Any) -> None:
        try:
            index = int(item.data(0, _INDEX_ROLE))
        except (TypeError, ValueError):
            return
        self.hidePopup()
        self.setCurrentIndex(index)
        self.activated.emit(index)
