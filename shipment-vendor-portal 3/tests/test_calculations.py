"""Unit tests for the auto-calculation rules. No DB needed."""
from datetime import date, timedelta
from types import SimpleNamespace

from app.utils.calculations import (
    calc_payment_days, calc_readiness_delay, calc_sailing_delay,
    calc_cc_delay, calc_total_clearance, derive_delay_status,
    recompute_shipment,
)


def test_payment_days_basic():
    assert calc_payment_days(date(2026, 1, 1), date(2026, 1, 11)) == 10


def test_payment_days_missing():
    assert calc_payment_days(None, date.today()) is None


def test_readiness_delay_clamped_to_zero():
    # Revised earlier than original = no delay
    assert calc_readiness_delay(date(2026, 5, 10), date(2026, 5, 5)) == 0


def test_sailing_delay_positive():
    assert calc_sailing_delay(date(2026, 5, 1), date(2026, 5, 6)) == 5


def test_cc_delay_basic():
    assert calc_cc_delay(date(2026, 5, 1), date(2026, 5, 4)) == 3


def test_total_clearance_basic():
    assert calc_total_clearance(date(2026, 5, 1), date(2026, 5, 9)) == 8


def test_derive_delay_status_eta_passed_undelivered():
    s = SimpleNamespace(
        readiness_delay_days=0, sailing_delayed_days=0, cc_delayed_days=0,
        proposed_eta_warehouse=date.today() - timedelta(days=2),
        actual_delivery_date=None,
    )
    assert derive_delay_status(s) == "Delayed"


def test_derive_delay_status_clean():
    s = SimpleNamespace(
        readiness_delay_days=0, sailing_delayed_days=0, cc_delayed_days=0,
        proposed_eta_warehouse=date.today() + timedelta(days=10),
        actual_delivery_date=None,
    )
    assert derive_delay_status(s) == "Non Delayed"


def test_recompute_in_place():
    s = SimpleNamespace(
        customer_po_date=date(2026, 1, 1),
        balance_payment_date=date(2026, 2, 1),
        oem_readiness_date=date(2026, 3, 1),
        revised_oem_readiness_date=date(2026, 3, 5),
        warehouse_gatein_date=date(2026, 3, 10),
        committed_sailing_date=date(2026, 3, 15),
        actual_sailing_date=date(2026, 3, 20),
        india_port_landing_date=date(2026, 4, 1),
        custom_clearance_date=date(2026, 4, 5),
        actual_delivery_date=date(2026, 4, 12),
        proposed_eta_warehouse=date(2026, 4, 8),
        # placeholders to be set
        payment_days=None, readiness_delay_days=None,
        readiness_to_warehouse_days=None, sailing_delayed_days=None,
        cc_delayed_days=None, total_clearance_days=None,
        delay_status=None,
    )
    recompute_shipment(s)
    assert s.payment_days == 31
    assert s.readiness_delay_days == 4
    assert s.sailing_delayed_days == 5
    assert s.cc_delayed_days == 4
    assert s.total_clearance_days == 11
    assert s.delay_status == "Delayed"  # delivery 4 days past ETA
