"""Saving the mortgage editor changes only what it edits (name, search text,
start date, tracks) and keeps every other field of the asset."""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from finance.models.mortgage import (  # noqa: E402
    AssetKind,
    CostItem,
    FundingKind,
    FundingSource,
    Mortgage,
)
from finance.pages.mortgage_page import MortgageDialog  # noqa: E402
from finance.qt import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_saving_keeps_yearly_costs_and_all_other_fields(app):
    house = Mortgage(
        id="h1", name="דירה", vendor_query="משכנתא", start_date="2024-01-01",
        property_price=1_500_000.0, price_query="מוכר",
        one_time_costs=[CostItem(name="עו״ד", amount=8000.0)],
        monthly_costs=[CostItem(name="ועד", query="ועד בית", excluded_movement_ids=["x1"])],
        yearly_costs=[CostItem(name="ביטוח מבנה", query="ביטוח מבנה", renewal_month=3)],
        funding_sources=[FundingSource(name="חסכון", kind=FundingKind.ACCOUNT, amount=100.0)],
        excluded_movement_ids=["m9"], prepayment_movement_ids=["p1"],
        sold=True, sale_price=2_000_000.0, sale_date="2026-01-01",
        expense_category="רכב", expense_categories=["דלק"], kind=AssetKind.PURCHASE,
    )
    dlg = MortgageDialog(accounts=[], mortgage=house)
    dlg._name.setText("דירה חדשה")
    dlg._on_save()
    saved = dlg.get_mortgage()
    assert saved is not None and saved.name == "דירה חדשה"
    for field in ("yearly_costs", "monthly_costs", "one_time_costs", "funding_sources",
                  "excluded_movement_ids", "prepayment_movement_ids", "property_price",
                  "price_query", "sold", "sale_price", "sale_date", "expense_category",
                  "expense_categories", "kind", "id"):
        assert getattr(saved, field) == getattr(house, field), field


def test_new_mortgage_is_a_purchase(app):
    dlg = MortgageDialog(accounts=[], mortgage=None)
    dlg._name.setText("חדשה")
    dlg._on_save()
    m = dlg.get_mortgage()
    assert m is not None and m.kind == AssetKind.PURCHASE and m.yearly_costs == []
