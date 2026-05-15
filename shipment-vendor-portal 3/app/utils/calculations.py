"""Auto-calculation rules for shipments.

All functions are pure (no DB) so they're trivially testable. They return None
when inputs are missing rather than raise — keeps the UI calm.
"""
from datetime import date, datetime
from typing import Optional


def _to_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def days_between(start, end) -> Optional[int]:
    s, e = _to_date(start), _to_date(end)
    if s is None or e is None:
        return None
    return (e - s).days


def calc_payment_days(po_date, final_pay_date) -> Optional[int]:
    """PO date to final (balance) payment date."""
    return days_between(po_date, final_pay_date)


def calc_readiness_delay(planned, revised) -> Optional[int]:
    """Days between original OEM readiness date and the revised one.

    Negative values are clamped to 0 (no delay).
    """
    d = days_between(planned, revised)
    if d is None:
        return None
    return max(d, 0)


def calc_readiness_to_warehouse(readiness, gatein) -> Optional[int]:
    return days_between(readiness, gatein)


def calc_sailing_delay(committed, actual) -> Optional[int]:
    d = days_between(committed, actual)
    if d is None:
        return None
    return max(d, 0)


def calc_cc_delay(landing, clearance) -> Optional[int]:
    """Customs clearance delay = clearance date - landing date."""
    d = days_between(landing, clearance)
    if d is None:
        return None
    return max(d, 0)


def calc_total_clearance(landing, delivery) -> Optional[int]:
    return days_between(landing, delivery)


def derive_delay_status(shipment, threshold_days: int = 0) -> str:
    """Return 'Delayed' if any of the delay components exceed threshold,
    or if proposed ETA passed without delivery. Otherwise 'Non Delayed'."""
    delays = [
        shipment.readiness_delay_days or 0,
        shipment.sailing_delayed_days or 0,
        shipment.cc_delayed_days or 0,
    ]
    if any(d > threshold_days for d in delays):
        return "Delayed"

    eta = _to_date(shipment.proposed_eta_warehouse)
    delivered = _to_date(shipment.actual_delivery_date)
    if eta and not delivered and date.today() > eta:
        return "Delayed"
    if eta and delivered and (delivered - eta).days > threshold_days:
        return "Delayed"
    return "Non Delayed"


def recompute_shipment(shipment, threshold_days: int = 0) -> None:
    """Mutates the shipment in-place with all derived columns.

    Call this in the route just before db.session.commit().
    """
    shipment.payment_days = calc_payment_days(
        shipment.customer_po_date, shipment.balance_payment_date
    )
    shipment.readiness_delay_days = calc_readiness_delay(
        shipment.oem_readiness_date, shipment.revised_oem_readiness_date
    )
    shipment.readiness_to_warehouse_days = calc_readiness_to_warehouse(
        shipment.revised_oem_readiness_date or shipment.oem_readiness_date,
        shipment.warehouse_gatein_date,
    )
    shipment.sailing_delayed_days = calc_sailing_delay(
        shipment.committed_sailing_date, shipment.actual_sailing_date
    )
    shipment.cc_delayed_days = calc_cc_delay(
        shipment.india_port_landing_date, shipment.custom_clearance_date
    )
    shipment.total_clearance_days = calc_total_clearance(
        shipment.india_port_landing_date, shipment.actual_delivery_date
    )
    shipment.delay_status = derive_delay_status(shipment, threshold_days)
