from __future__ import annotations

from typing import Callable, Dict, Optional

from ..qt import QStackedWidget, QWidget


class Router:
    def __init__(self, stacked_widget: QStackedWidget) -> None:
        self._stack: QStackedWidget = stacked_widget
        self._route_name_to_factory: Dict[str, Callable[[], QWidget]] = {}
        self._route_name_to_index: Dict[str, int] = {}
        self._previous_route: Optional[str] = None

    def register(self, route_name: str, factory: Callable[[], QWidget]) -> None:
        self._route_name_to_factory[route_name] = factory

    def navigate(self, route_name: str) -> None:
        current = self.current_route()
        if current is not None and current != route_name:
            self._previous_route = current

        if route_name not in self._route_name_to_index:
            self._ensure_created(route_name)

        index = self._route_name_to_index[route_name]
        widget = self._stack.widget(index)
        if widget is not None and hasattr(widget, "on_route_activated"):
            try:
                widget.on_route_activated()
            except Exception:
                pass
        if widget is not None and hasattr(widget, "_sidebar"):
            try:
                sidebar = getattr(widget, "_sidebar", None)
                if sidebar is not None and hasattr(sidebar, "update_route"):
                    sidebar.update_route(route_name)
            except Exception:
                pass

        self._stack.setCurrentIndex(index)

    def previous_route(self) -> str:
        return self._previous_route or "home"

    def _ensure_created(self, route_name: str) -> None:
        factory = self._route_name_to_factory.get(route_name)
        if factory is None:
            raise KeyError(f"Route not registered: {route_name!r}")

        widget = factory()
        index = self._stack.addWidget(widget)
        self._route_name_to_index[route_name] = index

    def current_route(self) -> Optional[str]:
        current_index = self._stack.currentIndex()
        for name, idx in self._route_name_to_index.items():
            if idx == current_index:
                return name
        return None

    def reset(self) -> None:
        """Remove all instantiated page widgets from the stack so they are
        recreated fresh on next navigation.  Call this after a user/workspace
        switch so no page retains stale data from the previous user."""
        widgets = []
        for idx in self._route_name_to_index.values():
            try:
                widget = self._stack.widget(idx)
                if widget is not None:
                    widgets.append(widget)
            except Exception:
                pass
        for widget in widgets:
            try:
                self._stack.removeWidget(widget)
                widget.deleteLater()
            except Exception:
                pass
        self._route_name_to_index.clear()
        self._previous_route = None
