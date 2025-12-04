from __future__ import annotations

from typing import Callable, Iterable, List, Optional, Tuple

from ..qt import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QSizePolicy,
    Qt,
)


class CollapsibleButtonList(QWidget):
    """
    Generic collapsible list with a header button and an arrow.

    - Header row: [toggle arrow] [title button]
    - Content: vertical list of item buttons
    - When collapsed, only the header is visible and no extra space is used.
    """

    def __init__(
        self,
        parent: QWidget,
        title: str,
        header_object_name: str,
        *,
        header_tooltip: Optional[str] = None,
    ) -> None:
        super().__init__(parent)

        self._expanded: bool = False
        self._items: List[Tuple[str, Callable[[], None]]] = []
        # Remember our position in the parent's layout for reliable insert/remove
        self._layout_index: Optional[int] = None

        # Root layout: no extra margins/spacing so this widget's height is
        # exactly the sum of its children (header + content when expanded).
        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

        # --- Header row: [toggle] [title] ---
        self._header = QWidget(self)
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)

        self._toggle_btn = QPushButton("▼", self._header)
        self._toggle_btn.setObjectName("SidebarNavToggle")
        self._toggle_btn.setFixedWidth(32)
        self._toggle_btn.setCheckable(True)
        try:
            self._toggle_btn.setSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred
            )
        except Exception:
            pass

        self._title_btn = QPushButton(title, self._header)
        self._title_btn.setObjectName(header_object_name)
        self._title_btn.setCheckable(True)
        if header_tooltip:
            self._title_btn.setToolTip(header_tooltip)
        try:
            self._title_btn.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
        except Exception:
            pass

        header_layout.addWidget(self._toggle_btn)
        header_layout.addWidget(self._title_btn)

        # --- Content container with items ---
        self._content = QWidget(self)
        self._content.setObjectName("SidebarSavingsList")
        try:
            self._content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass

        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 4)
        self._content_layout.setSpacing(4)

        self._root_layout.addWidget(self._header)
        self._root_layout.addWidget(self._content)

        self._apply_visibility()

        # Clicking either the arrow or the title toggles expansion
        self._toggle_btn.clicked.connect(self._on_header_clicked)  # type: ignore[arg-type]
        self._title_btn.clicked.connect(self._on_header_clicked)  # type: ignore[arg-type]

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def set_items(self, items: Iterable[Tuple[str, Callable[[], None]]]) -> None:
        """Replace all item buttons with given label/callback pairs."""
        # Clear old items
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        self._items = list(items)

        for label, callback in self._items:
            row = QWidget(self._content)
            row_layout = QHBoxLayout(row)
            # Match original savings list: small right margin so a potential
            # arrow column is slightly inside the visible edge.
            row_layout.setContentsMargins(0, 0, 8, 0)
            row_layout.setSpacing(0)

            # Left spacer so text appears visually centered between arrow and edge.
            left_spacer = QLabel("", row)
            left_spacer.setFixedWidth(24)

            btn = QPushButton(label, row)
            btn.setObjectName("SidebarNavSubButton")
            btn.setCheckable(False)
            try:
                btn.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Preferred,
                )
            except Exception:
                pass

            # Right "arrow" column (kept empty for now) so alignment matches
            # the original savings list exactly.
            right_arrow = QLabel("", row)
            right_arrow.setObjectName("SidebarNavSubArrow")
            right_arrow.setFixedWidth(20)
            right_arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)

            row_layout.addWidget(left_spacer, 0)
            row_layout.addWidget(btn, 1)
            row_layout.addWidget(right_arrow, 0)

            # Bind callback
            btn.clicked.connect(lambda _=False, cb=callback: cb())  # type: ignore[arg-type]

            self._content_layout.addWidget(row)

        self._apply_visibility()

    def set_expanded(self, expanded: bool) -> None:
        """Set expanded state and update visibility."""
        if self._expanded == expanded:
            return
        self._expanded = expanded
        self._apply_visibility()

    def toggle(self) -> None:
        """Toggle expanded/collapsed state."""
        self._expanded = not self._expanded
        self._apply_visibility()

    def is_expanded(self) -> bool:
        """Return whether the list is currently expanded."""
        return self._expanded

    def header_button(self) -> QPushButton:
        return self._title_btn

    def toggle_button(self) -> QPushButton:
        return self._toggle_btn

    def set_header_visible(self, visible: bool) -> None:
        """Show or hide the internal header row (arrow + title) and recompute layout."""
        self._header.setVisible(visible)
        # Re-apply visibility rules so height collapses correctly when the
        # header is hidden and the list is not expanded.
        self._apply_visibility()

    def refresh_theme(self) -> None:
        """Re-apply styling based on current theme and expanded/collapsed state."""
        has_items = bool(self._items)
        show_content = self._expanded and has_items

        if show_content:
            # Re-apply expanded styling
            self._apply_pressed_style()
        else:
            # Re-apply collapsed styling
            self._apply_collapsed_style()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _apply_visibility(self) -> None:
        has_items = bool(self._items)
        show_content = self._expanded and has_items

        # Show/hide only the content widget
        self._content.setVisible(show_content)

        # Arrow state
        self._toggle_btn.setChecked(self._expanded)
        self._toggle_btn.setText("▲" if show_content else "▼")

        # Header pressed state & bottom border
        self._title_btn.setChecked(self._expanded)
        if show_content:
            self._title_btn.setStyleSheet("border-bottom-color: transparent;")
        else:
            self._title_btn.setStyleSheet("")

        header_visible = self._header.isVisible()
        if header_visible:
            # Normal mode: header row is part of this widget.
            if show_content:
                # Header + rows take natural height.
                self.setMinimumHeight(0)
                self.setMaximumHeight(16777215)
                self.show()
                self._apply_pressed_style()
            else:
                # Collapse to just the header height.
                h = self._header.sizeHint().height()
                self.setMinimumHeight(0)
                self.setMaximumHeight(h)
                self._apply_collapsed_style()
                self.show()
        else:
            # Content-only mode (used under external header in sidebar).
            # When collapsed, remove the widget from the layout entirely to ensure
            # zero vertical space. When expanded, insert it back at the remembered position.
            parent = self.parentWidget()
            parent_layout = parent.layout() if parent is not None else None
            # Import here to avoid circulars
            try:
                from ..qt import QVBoxLayout as _QVBoxLayout  # type: ignore
            except Exception:  # pragma: no cover - very defensive
                _QVBoxLayout = None  # type: ignore

            if show_content:
                # Expanded: insert back into the parent layout if not already there
                if (
                    parent_layout is not None
                    and _QVBoxLayout is not None
                    and isinstance(parent_layout, _QVBoxLayout)
                ):
                    try:
                        idx_current = parent_layout.indexOf(self)  # type: ignore[arg-type]
                    except Exception:
                        idx_current = -1
                    if idx_current == -1:
                        # Insert at the remembered position, or at the end if not remembered
                        insert_at = (
                            self._layout_index
                            if self._layout_index is not None
                            else parent_layout.count()
                        )
                        try:
                            parent_layout.insertWidget(insert_at, self)  # type: ignore[arg-type]
                        except Exception:
                            pass

                # Allow natural height and show
                self.setMinimumHeight(0)
                self.setMaximumHeight(16777215)
                self.show()
                self.updateGeometry()
                self._apply_pressed_style()
            else:
                # Collapsed: remember position and remove from layout entirely
                if (
                    parent_layout is not None
                    and _QVBoxLayout is not None
                    and isinstance(parent_layout, _QVBoxLayout)
                ):
                    try:
                        idx_current = parent_layout.indexOf(self)  # type: ignore[arg-type]
                    except Exception:
                        idx_current = -1
                    # Remember the position for re-insertion
                    self._layout_index = idx_current if idx_current >= 0 else None
                    if idx_current != -1:
                        try:
                            parent_layout.removeWidget(self)  # type: ignore[arg-type]
                            # Force layout to recalculate and update immediately
                            parent_layout.invalidate()
                            parent_layout.activate()
                            if parent is not None:
                                parent.updateGeometry()
                                parent.update()
                                # Also trigger a repaint to ensure visual update
                                parent.repaint()
                        except Exception:
                            pass

                self._apply_collapsed_style()
                self.setFixedHeight(0)
                self.setMinimumHeight(0)
                self.setMaximumHeight(0)
                self.hide()
                self.updateGeometry()

    def _on_header_clicked(self) -> None:
        self.toggle()

    def _apply_pressed_style(self) -> None:
        try:
            from PySide6.QtWidgets import QApplication  # type: ignore
        except Exception:
            try:
                from PyQt6.QtWidgets import QApplication  # type: ignore
            except Exception:
                return

        app = QApplication.instance()
        if app is None:
            return

        theme = app.property("theme")
        is_dark = theme == "dark"
        if is_dark:
            container_bg = "#020617"
            border_css = (
                "border-top: none; "
                "border-bottom: none; "
                "border-left: none; "
                "border-right: none; "
            )
        else:
            container_bg = "#dcecff"
            border_color = "#a0bce2"
            border_css = (
                "border-top: none; "
                f"border-bottom: 2px solid {border_color}; "
                "border-left: none; "
                "border-right: none; "
            )

        self._content.setStyleSheet(
            f"QWidget#SidebarSavingsList {{ background: {container_bg}; {border_css}}}"
        )

    def _apply_collapsed_style(self) -> None:
        self._content.setStyleSheet("QWidget#SidebarSavingsList { background: transparent; }")
        self.setStyleSheet("background: transparent;")