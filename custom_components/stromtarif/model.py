"""Pure, testable ledger. Dates describe midnight boundaries; end is exclusive."""
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation


def number(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("invalid_number") from None
    if not result.is_finite() or result < 0:
        raise ValueError("invalid_number")
    return str(result)


def valid_date(value, today):
    parsed = date.fromisoformat(str(value))
    if parsed > today:
        raise ValueError("future_date")
    return parsed.isoformat()


def make_tariff(data, today):
    return {"name": str(data["name"]).strip(),
            "start": valid_date(data["date"], today),
            "price": number(data["price"]),
            "monthly_fee": number(data["monthly_fee"]),
            "reading": number(data["reading"])}


def initial(data, today):
    tariff = make_tariff(data, today)
    return {"tariffs": [tariff], "readings": [
        {"date": tariff["start"], "value": tariff["reading"], "kind": "initial"}],
        "interval": int(data["interval"]), "notified_due": None}


def add_reading(ledger, value, when, today):
    when = valid_date(when, today)
    value = number(value)
    last = ledger["readings"][-1]
    if when <= last["date"]:
        raise ValueError("date_order")
    if Decimal(value) < Decimal(last["value"]):
        raise ValueError("reading_decreased")
    ledger["readings"].append({"date": when, "value": value, "kind": "manual"})
    ledger["notified_due"] = None


def change_tariff(ledger, data, today):
    tariff = make_tariff(data, today)
    last = ledger["readings"][-1]
    if tariff["start"] <= ledger["tariffs"][-1]["start"] or tariff["start"] < last["date"]:
        raise ValueError("date_order")
    if tariff["start"] == last["date"]:
        if Decimal(tariff["reading"]) != Decimal(last["value"]):
            raise ValueError("boundary_mismatch")
    else:
        add_reading(ledger, tariff["reading"], tariff["start"], today)
        ledger["readings"][-1]["kind"] = "tariff"
    ledger["tariffs"].append(tariff)
    ledger["notified_due"] = None


def undo_reading(ledger):
    if len(ledger["readings"]) < 2 or ledger["readings"][-1]["kind"] != "manual":
        raise ValueError("cannot_undo")
    if ledger["readings"][-1]["date"] <= ledger["tariffs"][-1]["start"]:
        raise ValueError("cannot_undo")
    ledger["readings"].pop()
    ledger["notified_due"] = None


def fee(monthly, start, end):
    """Calendar-month proration, including leap years."""
    total = Decimal("0")
    while start < end:
        days = monthrange(start.year, start.month)[1]
        next_month = start.replace(day=days) + timedelta(days=1)
        stop = min(end, next_month)
        total += Decimal(monthly) * Decimal((stop - start).days) / Decimal(days)
        start = stop
    return total


def tariff_at(ledger, when):
    return next(t for t in reversed(ledger["tariffs"]) if t["start"] <= when)


def totals(ledger):
    energy = Decimal("0")
    base = Decimal("0")
    for before, after in zip(ledger["readings"], ledger["readings"][1:]):
        tariff = tariff_at(ledger, before["date"])
        energy += (Decimal(after["value"]) - Decimal(before["value"])) * Decimal(tariff["price"])
        base += fee(tariff["monthly_fee"], date.fromisoformat(before["date"]), date.fromisoformat(after["date"]))
    consumption = Decimal(ledger["readings"][-1]["value"]) - Decimal(ledger["readings"][0]["value"])
    return {"consumption": float(consumption), "energy_cost": float(energy),
            "base_cost": float(base), "total_cost": float(energy + base)}


def due(ledger):
    return date.fromisoformat(ledger["readings"][-1]["date"]) + timedelta(days=ledger["interval"])
