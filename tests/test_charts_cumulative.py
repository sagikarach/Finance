from types import SimpleNamespace

from finance.models.charts import cumulative_daily_series


def _p(date_iso, amount):
    return SimpleNamespace(date_iso=date_iso, amount=amount)


def test_running_total_across_days():
    labels, values = cumulative_daily_series(
        [_p("2026-01-01", -100.0), _p("2026-01-02", -50.0)]
    )
    assert labels == ["01/01/26", "02/01/26"]
    assert values == [-100.0, -150.0]


def test_same_day_amounts_are_summed():
    _, values = cumulative_daily_series(
        [_p("2026-01-01", -100.0), _p("2026-01-01", -25.0)]
    )
    assert values == [-125.0]


def test_gap_days_carry_the_running_total():
    labels, values = cumulative_daily_series(
        [_p("2026-01-01", -10.0), _p("2026-01-04", -5.0)]
    )
    # every calendar day between first and last is present; gaps keep the total
    assert labels == ["01/01/26", "02/01/26", "03/01/26", "04/01/26"]
    assert values == [-10.0, -10.0, -10.0, -15.0]


def test_unsorted_input_is_ordered():
    labels, values = cumulative_daily_series(
        [_p("2026-01-03", -5.0), _p("2026-01-01", -10.0)]
    )
    assert labels[0] == "01/01/26" and labels[-1] == "03/01/26"
    assert values[-1] == -15.0


def test_empty_input_is_empty():
    assert cumulative_daily_series([]) == ([], [])
