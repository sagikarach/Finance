"""Round-trip + resilience tests for the JSON file providers.

Each provider takes an explicit ``path=``, so these write to a pytest ``tmp_path``
and never touch the real workspace. They lock two things the app relies on:
save→list fidelity (models survive serialization), and graceful degradation on a
missing/corrupt file (return empty, never raise)."""

from finance.data.provider import JsonFileAccountsProvider
from finance.data.bank_movement_provider import JsonFileBankMovementProvider
from finance.data.mortgage_provider import JsonFileMortgageProvider
from finance.data.installment_plan_provider import JsonFileInstallmentPlanProvider
from finance.data.one_time_event_provider import JsonFileOneTimeEventProvider
from finance.data.notifications_provider import JsonFileNotificationsProvider
from finance.data.action_history_provider import JsonFileActionHistoryProvider

from finance.models.accounts import BankAccount, Savings, SavingsAccount
from finance.models.bank_movement import BankMovement, MovementType
from finance.models.installment_plan import InstallmentPlan
from finance.models.mortgage import (
    AmortizationType,
    AssetKind,
    Mortgage,
    MortgageTrack,
    TrackKind,
)
from finance.models.notifications import (
    Notification,
    NotificationRule,
    NotificationSeverity,
    NotificationStatus,
    NotificationType,
    RuleType,
)
from finance.models.one_time_event import OneTimeEvent, OneTimeEventStatus


# ── bank movements ───────────────────────────────────────────────────────
def _mv(amount, date, **kw):
    return BankMovement(
        amount=amount, date=date, account_name="בנק",
        category=kw.pop("category", "מזון"),
        type=kw.pop("type", MovementType.ONE_TIME), **kw,
    )


def test_bank_movements_round_trip(tmp_path):
    p = tmp_path / "mv.json"
    prov = JsonFileBankMovementProvider(movements_path=p)
    movs = [
        _mv(-100.0, "2026-01-05", description="קניות", is_transfer=False),
        _mv(5000.0, "2026-01-10", type=MovementType.MONTHLY, category="משכורת"),
    ]
    prov.save_movements(movs)
    assert JsonFileBankMovementProvider(movements_path=p).list_movements() == movs


def test_bank_movements_add_appends(tmp_path):
    p = tmp_path / "mv.json"
    prov = JsonFileBankMovementProvider(movements_path=p)
    prov.save_movements([_mv(-10.0, "2026-01-01")])
    prov.add_movement(_mv(-20.0, "2026-01-02"))
    assert len(prov.list_movements()) == 2


def test_bank_movements_missing_and_malformed(tmp_path):
    assert JsonFileBankMovementProvider(movements_path=tmp_path / "no.json").list_movements() == []
    bad = tmp_path / "bad.json"
    bad.write_text("{oops", encoding="utf-8")
    assert JsonFileBankMovementProvider(movements_path=bad).list_movements() == []


# ── mortgages ────────────────────────────────────────────────────────────
def _mortgage(name="דירה"):
    return Mortgage(
        name=name, kind=AssetKind.PURCHASE, property_price=2_000_000.0,
        start_date="2025-01-01",
        tracks=[
            MortgageTrack(
                name="קבועה", kind=TrackKind.FIXED_UNLINKED, principal=1_000_000.0,
                annual_rate=5.0, term_months=120, amortization=AmortizationType.SPITZER,
            )
        ],
    )


def test_mortgages_round_trip_upsert_delete(tmp_path):
    p = tmp_path / "m.json"
    prov = JsonFileMortgageProvider(path=p)
    m = _mortgage()
    prov.save_mortgages([m])
    assert prov.list_mortgages() == [m]

    # upsert replaces by id
    m2 = Mortgage(id=m.id, name="דירה חדשה", kind=AssetKind.PURCHASE,
                  property_price=2_500_000.0, start_date="2025-01-01", tracks=m.tracks)
    prov.upsert_mortgage(m2)
    got = prov.list_mortgages()
    assert len(got) == 1 and got[0].name == "דירה חדשה"

    prov.delete_mortgage(m.id)
    assert prov.list_mortgages() == []


def test_mortgages_missing_and_malformed(tmp_path):
    assert JsonFileMortgageProvider(path=tmp_path / "no.json").list_mortgages() == []
    bad = tmp_path / "bad.json"
    bad.write_text("nonsense", encoding="utf-8")
    assert JsonFileMortgageProvider(path=bad).list_mortgages() == []


# ── installment plans ────────────────────────────────────────────────────
def test_installment_plans_round_trip_upsert_delete(tmp_path):
    p = tmp_path / "i.json"
    prov = JsonFileInstallmentPlanProvider(path=p)
    plan = InstallmentPlan(name="ספה", vendor_query="ספה", account_name="בנק",
                           start_date="2026-01-01", payments_count=6, original_amount=6000.0)
    prov.save_plans([plan])
    assert prov.list_plans() == [plan]

    prov.upsert_plan(InstallmentPlan(id=plan.id, name="ספה גדולה", payments_count=12))
    got = prov.list_plans()
    assert len(got) == 1 and got[0].payments_count == 12

    prov.delete_plan(plan.id)
    assert prov.list_plans() == []


def test_installment_plans_missing_and_malformed(tmp_path):
    assert JsonFileInstallmentPlanProvider(path=tmp_path / "no.json").list_plans() == []
    bad = tmp_path / "bad.json"
    bad.write_text("[oops", encoding="utf-8")
    assert JsonFileInstallmentPlanProvider(path=bad).list_plans() == []


# ── one-time events ──────────────────────────────────────────────────────
def test_one_time_events_round_trip_upsert_delete(tmp_path):
    p = tmp_path / "e.json"
    prov = JsonFileOneTimeEventProvider(path=p)
    ev = OneTimeEvent(name="חתונה", budget=50000.0, status=OneTimeEventStatus.ACTIVE,
                      start_date="2026-06-01", notes="הערה")
    prov.save_events([ev])
    got = prov.list_events()
    assert got == [ev] and got[0].status == OneTimeEventStatus.ACTIVE

    prov.upsert_event(OneTimeEvent(id=ev.id, name="חתונה", budget=60000.0,
                                   status=OneTimeEventStatus.FINISHED))
    got = prov.list_events()
    assert len(got) == 1 and got[0].status == OneTimeEventStatus.FINISHED

    prov.delete_event(ev.id)
    assert prov.list_events() == []


def test_one_time_events_missing_and_malformed(tmp_path):
    assert JsonFileOneTimeEventProvider(path=tmp_path / "no.json").list_events() == []
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    assert JsonFileOneTimeEventProvider(path=bad).list_events() == []


# ── accounts (bank + savings, two files) ─────────────────────────────────
def test_accounts_round_trip_both_kinds(tmp_path):
    bp, sp = tmp_path / "bank.json", tmp_path / "sav.json"
    prov = JsonFileAccountsProvider(bank_accounts_path=bp, savings_accounts_path=sp)
    prov.save_bank_accounts(
        [BankAccount(name="עו״ש", total_amount=1000.0, is_liquid=True,
                     active=True, baseline_amount=500.0)]
    )
    prov.save_savings_accounts(
        [SavingsAccount(name="קופה", total_amount=0.0, is_liquid=False,
                        savings=[Savings(name="חירום", amount=3000.0)])]
    )
    accts = JsonFileAccountsProvider(
        bank_accounts_path=bp, savings_accounts_path=sp
    ).list_accounts()
    by_name = {a.name: a for a in accts}

    bank = by_name["עו״ש"]
    assert isinstance(bank, BankAccount)
    assert bank.total_amount == 1000.0 and bank.active is True
    assert bank.baseline_amount == 500.0  # baseline survives the round-trip

    sav = by_name["קופה"]
    assert isinstance(sav, SavingsAccount)
    assert [s.name for s in sav.savings] == ["חירום"]
    assert sav.savings[0].amount == 3000.0


def test_accounts_missing_and_malformed(tmp_path):
    bp, sp = tmp_path / "bank.json", tmp_path / "sav.json"
    assert JsonFileAccountsProvider(bank_accounts_path=bp, savings_accounts_path=sp).list_accounts() == []
    bp.write_text("{bad", encoding="utf-8")
    sp.write_text("{bad", encoding="utf-8")
    assert JsonFileAccountsProvider(bank_accounts_path=bp, savings_accounts_path=sp).list_accounts() == []


# ── notifications (dict-shaped file: notifications + rules + settings) ────
def _notif(key="k1"):
    return Notification(
        id="n1", key=key, type=list(NotificationType)[0], title="כותרת",
        message="הודעה", severity=list(NotificationSeverity)[0],
        created_at="2026-01-01T00:00:00", status=NotificationStatus.UNREAD,
    )


def test_notifications_and_rules_round_trip(tmp_path):
    p = tmp_path / "notif.json"
    prov = JsonFileNotificationsProvider(path=p)
    prov.save_notifications([_notif("a"), _notif("b")])
    prov.save_rules([NotificationRule(id="r1", type=list(RuleType)[0])])

    prov2 = JsonFileNotificationsProvider(path=p)
    assert [n.key for n in prov2.list_notifications()] == ["a", "b"]
    assert [r.id for r in prov2.list_rules()] == ["r1"]

    prov2.delete(key="a")
    assert [n.key for n in JsonFileNotificationsProvider(path=p).list_notifications()] == ["b"]


def test_notifications_settings_and_malformed(tmp_path):
    p = tmp_path / "notif.json"
    prov = JsonFileNotificationsProvider(path=p)
    assert prov.is_enabled() is True  # default when absent
    prov.set_enabled(False)
    assert JsonFileNotificationsProvider(path=p).is_enabled() is False

    bad = tmp_path / "bad.json"
    bad.write_text("{oops", encoding="utf-8")
    prov_bad = JsonFileNotificationsProvider(path=bad)
    assert prov_bad.list_notifications() == [] and prov_bad.list_rules() == []


# ── action history (resilience — Action construction is exercised elsewhere)
def test_action_history_missing_and_malformed(tmp_path):
    assert JsonFileActionHistoryProvider(history_path=tmp_path / "no.json").list_history() == []
    bad = tmp_path / "bad.json"
    bad.write_text("not json at all", encoding="utf-8")
    assert JsonFileActionHistoryProvider(history_path=bad).list_history() == []
