from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Tuple


@dataclass(frozen=True)
class SidebarItem:
    label: str
    on_click: Callable[[], None]

    def as_tuple(self) -> Tuple[str, Callable[[], None]]:
        return self.label, self.on_click


@dataclass
class SidebarSectionState:
    section_id: str
    title: str
    items: List[SidebarItem] = field(default_factory=list)
    expanded: bool = False

    @property
    def has_items(self) -> bool:
        return bool(self.items)

    def add_item(self, label: str, on_click: Callable[[], None]) -> None:
        self.items.append(SidebarItem(label=label, on_click=on_click))

    def as_collapsible_items(self) -> List[Tuple[str, Callable[[], None]]]:
        return [item.as_tuple() for item in self.items]
