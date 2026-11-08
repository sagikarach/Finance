from __future__ import annotations

import pytest

from finance.models import category_tree


@pytest.fixture(autouse=True)
def _no_real_category_tree():
    """Never let a test read the developer's real categories file through
    ``active_tree()``: start every test with the flat (empty) hierarchy.
    Tests that need a hierarchy set their own override."""
    category_tree.set_active_tree_override(category_tree.EMPTY_TREE)
    yield
    category_tree.set_active_tree_override(None)
