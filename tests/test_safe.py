import logging

import pytest

from finance.utils.safe import PARSE_ERRORS, QT_ERRORS, best_effort, swallow


def test_swallow_suppresses_named_type():
    with swallow(ValueError):
        int("not a number")  # raises ValueError → swallowed


def test_swallow_lets_other_types_propagate():
    with pytest.raises(KeyError):
        with swallow(ValueError):
            raise KeyError("boom")


def test_swallow_defaults_to_exception():
    with swallow():
        raise RuntimeError("anything")


def test_swallow_logs_at_given_level(caplog):
    with caplog.at_level(logging.WARNING, logger="finance.safe"):
        with swallow(ValueError, msg="parsing", level=logging.WARNING):
            int("x")
    assert any("parsing" in r.message for r in caplog.records)


def test_best_effort_returns_none_on_caught_error():
    @best_effort(ZeroDivisionError)
    def divide():
        return 1 / 0

    assert divide() is None


def test_best_effort_passes_through_return_value():
    @best_effort(ValueError)
    def double(x):
        return x * 2

    assert double(21) == 42


def test_best_effort_reraises_unlisted_type():
    @best_effort(ValueError)
    def boom():
        raise KeyError("nope")

    with pytest.raises(KeyError):
        boom()


def test_parse_errors_covers_common_malformed_data_types():
    for t in (ValueError, TypeError, KeyError, AttributeError, IndexError):
        assert t in PARSE_ERRORS


def test_qt_errors_covers_widget_failure_types_but_not_the_fatal_ones():
    # a deleted C++ object / None widget / bad arg — the routine Qt failures
    for t in (RuntimeError, AttributeError, TypeError, ValueError):
        assert t in QT_ERRORS
    # truly-fatal signals must NOT be caught at the Qt boundary
    for t in (KeyboardInterrupt, SystemExit, MemoryError):
        assert t not in QT_ERRORS
        assert not issubclass(t, QT_ERRORS)
