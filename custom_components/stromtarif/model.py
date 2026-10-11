"""Pure, testable ledger. Dates describe midnight boundaries; end is exclusive."""
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import csv
import io


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
            "reading": number(data["reading"]), "active": True}


def initial(data, today):
    tariff = make_tariff(data, today)
    return {"tariffs": [tariff], "readings": [
        {"date": tariff["start"], "value": tariff["reading"], "kind": "initial"}],
        "interval": int(data["interval"]), "notified_due": None,
        "reminders": {k: data.get(k) for k in ("calendar", "todo")},}


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
    old = ledger["tariffs"][-1]
    old["active"] = False
    old.setdefault("end", tariff["start"])
    old.setdefault("end_reading", last["value"] if old["end"] == last["date"] else tariff["reading"])
    if data.get("final_bill"):
        record_bill(ledger, data, old)
    ledger["tariffs"].append(tariff)
    for key in ("calendar", "todo"):
        if key in data:
            ledger["reminders"][key] = data[key] or None
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
    rows = intervals(ledger)
    return {key: sum(row[key] for row in rows) for key in ("consumption", "energy_cost", "base_cost", "total_cost")}


def due(ledger):
    return date.fromisoformat(ledger["readings"][-1]["date"]) + timedelta(days=ledger["interval"])


def migrate(data):
    """Add fields without discarding old tariff or reading data."""
    data.setdefault("payments", [])
    data.setdefault("monthly_installment", "0")
    data.setdefault("payment_day", 1)
    data.setdefault("billing_start", data["readings"][0]["date"])
    start = date.fromisoformat(data["billing_start"])
    data.setdefault("billing_end", start.replace(year=start.year + 1, day=min(start.day, monthrange(start.year + 1, start.month)[1])).isoformat())
    data.setdefault("source", None)
    for i, tariff in enumerate(data["tariffs"]):
        tariff.setdefault("active", i == len(data["tariffs"]) - 1)
        if i + 1 < len(data["tariffs"]):
            tariff.setdefault("end", data["tariffs"][i + 1]["start"])
    data.setdefault("bills", [])
    data.setdefault("schedule_mode", "monthly")
    data.setdefault("payment_overrides", {})
    data.setdefault("reminders", {})
    for key, default in {"calendar": None, "todo": None, "readings": True, "payments": True}.items():
        data["reminders"].setdefault(key, default)
    data.setdefault("reminder_targets", [])
    return data


def active(data):
    return data["tariffs"][-1].get("active", True)


def record_bill(data, values, tariff):
    start = date.fromisoformat(str(values["bill_start"]))
    end = date.fromisoformat(tariff["end"])
    if not date.fromisoformat(tariff["start"]) <= start < end:
        raise ValueError("billing_dates")
    amount = number(values["invoice_total"])
    balance = number(values["invoice_balance"])
    if values.get("balance_kind", "payment") == "refund":
        balance = str(-Decimal(balance))
    data["bills"].append({"tariff": tariff["name"], "start": start.isoformat(),
        "end": end.isoformat(), "reading": tariff.get("end_reading", data["readings"][-1]["value"]),
        "invoice_total": amount, "balance": balance})


def close_tariff(data, values, today):
    end = valid_date(values["date"], today)
    if end <= data["tariffs"][-1]["start"] or end < data["readings"][-1]["date"]:
        raise ValueError("date_order")
    if end == data["readings"][-1]["date"]:
        if Decimal(number(values["reading"])) != Decimal(data["readings"][-1]["value"]):
            raise ValueError("boundary_mismatch")
    else:
        add_reading(data, values["reading"], end, today)
    data["readings"][-1]["kind"] = "final"
    tariff = data["tariffs"][-1]
    tariff.update(active=False, end=end, end_reading=data["readings"][-1]["value"])
    if values.get("final_bill"):
        record_bill(data, values, tariff)
    data["notified_due"] = None


def payment_schedule(data):
    start, end = date.fromisoformat(data["billing_start"]), date.fromisoformat(data["billing_end"])
    if not active(data) and data["tariffs"][-1].get("end"):
        end = min(end, date.fromisoformat(data["tariffs"][-1]["end"]))
    rows = {}
    cursor = start.replace(day=1)
    while data.get("schedule_mode", "monthly") == "monthly" and cursor < end:
        days = monthrange(cursor.year, cursor.month)[1]
        day = days if data["payment_day"] == 0 else min(data["payment_day"], days)
        when = cursor.replace(day=day).isoformat()
        if start.isoformat() <= when < end.isoformat() and Decimal(data["monthly_installment"]) > 0:
            rows[when] = {"key": when, "date": when, "amount": data["monthly_installment"]}
        cursor = cursor.replace(day=days) + timedelta(days=1)
    for key, override in data.get("payment_overrides", {}).items():
        rows.pop(key, None)
        if override and start.isoformat() <= override["date"] < end.isoformat():
            rows.pop(override["date"], None)
            rows[key] = {"key": key, **override}
    return sorted(rows.values(), key=lambda row: (row["date"], row["key"]))


def edit_planned_payment(data, key, when, amount, remove=False):
    date.fromisoformat(str(key))
    if remove:
        data["payment_overrides"][key] = None
        return
    when = date.fromisoformat(str(when)).isoformat()
    amount = number(amount)
    if not data["billing_start"] <= when < data["billing_end"] or Decimal(amount) <= 0:
        raise ValueError("billing_dates")
    if any(row["date"] == when and row["key"] != key for row in payment_schedule(data)):
        raise ValueError("duplicate_payment_date")
    data["payment_overrides"][key] = {"date": when, "amount": amount}


def configure_finances(data, start, end, installment, payment_day):
    start = date.fromisoformat(str(start))
    end = date.fromisoformat(str(end))
    if end <= start or start.isoformat() < data["readings"][0]["date"]:
        raise ValueError("billing_dates")
    day = int(payment_day)
    if not 0 <= day <= 31:
        raise ValueError("invalid_input")
    data.update(billing_start=start.isoformat(), billing_end=end.isoformat(),
                monthly_installment=number(installment), payment_day=day)


def add_payment(data, amount, when, today):
    amount = number(amount)
    if Decimal(amount) <= 0:
        raise ValueError("invalid_number")
    data["payments"].append({"date": valid_date(when, today), "amount": amount})


def period_cost(data, start, end):
    """Apportion boundary-crossing readings by days; flag estimates."""
    energy = Decimal(0)
    base = Decimal(0)
    consumption = Decimal(0)
    estimated = False
    for before, after in zip(data["readings"], data["readings"][1:]):
        a, b = date.fromisoformat(before["date"]), date.fromisoformat(after["date"])
        tariff = tariff_at(data, before["date"])
        cutoff = date.fromisoformat(tariff.get("end", b.isoformat()))
        left, right = max(a,start), min(b,end,cutoff)
        if right <= left:
            continue
        estimated |= left != a or right != b
        used = (Decimal(after["value"]) - Decimal(before["value"])) * Decimal((right-left).days) / Decimal((b-a).days)
        tariff = tariff_at(data,before["date"])
        consumption += used
        energy += used * Decimal(tariff["price"])
        base += fee(tariff["monthly_fee"],left,right)
    return float(consumption), float(energy+base), estimated


def planned_payments(data):
    return sum(float(row["amount"]) for row in payment_schedule(data))


def finances(data):
    start, end = date.fromisoformat(data["billing_start"]), date.fromisoformat(data["billing_end"])
    if not active(data):
        end = min(end, date.fromisoformat(data["tariffs"][-1].get("end", data["readings"][-1]["date"])))
    last = date.fromisoformat(data["readings"][-1]["date"])
    observed_end = min(last,end)
    consumption, observed_cost, estimated = period_cost(data,start,observed_end)
    paid = sum(float(p["amount"]) for p in data["payments"] if start.isoformat() <= p["date"] < end.isoformat())
    planned = planned_payments(data)
    forecast = None
    if observed_end > start:
        remaining = max((end-observed_end).days,0)
        tariff = data["tariffs"][-1]
        forecast = observed_cost + consumption / (observed_end-start).days * remaining * float(tariff["price"]) + float(fee(tariff["monthly_fee"],observed_end,end))
    return {"period_consumption": consumption, "period_cost": observed_cost,
            "paid": paid, "balance": observed_cost-paid, "planned": planned,
            "forecast_cost": forecast, "forecast_balance": None if forecast is None else forecast-planned,
            "partial_period_estimate": estimated, "observed_until": observed_end.isoformat() if observed_end >= start else None}


def source_value(state, attributes):
    if attributes.get("device_class") != "energy" or attributes.get("state_class") not in {"total", "total_increasing"}:
        raise ValueError("invalid_source")
    unit = attributes.get("unit_of_measurement")
    if unit not in {"Wh", "kWh"}:
        raise ValueError("invalid_source")
    try:
        value = Decimal(number(state))
    except ValueError:
        raise ValueError("invalid_source") from None
    return value / 1000 if unit == "Wh" else value


def configure_source(data, entity_id, raw=None):
    if not entity_id:
        data["source"] = None
        return
    data["source"] = {"entity_id": entity_id, "offset": str(Decimal(data["readings"][-1]["value"])-raw), "last_raw": str(raw), "reset_detected": False}


def ingest_source(data, raw, today):
    if not active(data):
        return False
    source = data["source"]
    if source.get("reset_detected") or raw < Decimal(source["last_raw"]):
        raise ValueError("source_reset")
    value = raw + Decimal(source["offset"])
    last = data["readings"][-1]
    if value < Decimal(last["value"]):
        raise ValueError("source_behind")
    if today.isoformat() < last["date"]:
        raise ValueError("date_order")
    if today.isoformat() == last["date"]:
        if last["kind"] != "automatic":
            return False
        last["value"] = str(value)
    else:
        add_reading(data,value,today.isoformat(),today)
        data["readings"][-1]["kind"] = "automatic"
    source["last_raw"] = str(raw)
    return True


def csv_export(data):
    """Single tidy ledger export; neutralize formula injection in text fields."""
    out=io.StringIO(newline="")
    writer=csv.writer(out,delimiter=";")
    writer.writerow(["Typ","Datum","Name/Art","Zaehlerstand_kWh","Arbeitspreis_EUR_kWh","Grundgebuehr_EUR_Monat","Zahlung_EUR","Verbrauch_kWh","Arbeitspreiskosten_EUR","Grundgebuehr_EUR","Gesamtkosten_EUR"])
    def safe(value):
        text=str(value)
        return "'"+text if text.lstrip().startswith(("=","+","-","@")) else text
    rows=[]
    for t in data["tariffs"]:
        rows.append((t["start"],["Tarif",t["start"],safe(t["name"]),t["reading"],t["price"],t["monthly_fee"],""]))
    for r in data["readings"]:
        rows.append((r["date"],["Ablesung",r["date"],r["kind"],r["value"],"","",""]))
    for p in data["payments"]:
        rows.append((p["date"],["Zahlung",p["date"],"","","","",p["amount"]]))
    for bill in data.get("bills", []):
        rows.append((bill["end"], ["Endabrechnung", bill["end"], safe(bill["tariff"]), bill["reading"], "", "", "", "", "", "", bill["invoice_total"]]))
        rows.append((bill["end"], ["Abrechnungssaldo", bill["end"], "Nachzahlung positiv / Guthaben negativ", "", "", "", bill["balance"]]))
    for row in payment_schedule(data):
        rows.append((row["date"], ["Geplanter Abschlag", row["date"], "", "", "", "", row["amount"]]))
    for _,row in sorted(rows,key=lambda item:item[0]):
        writer.writerow(row+["","","",""])
    for i in intervals(data):
        writer.writerow(["Zeitraum",i["to"],safe(i["tariff"]),"","","","",i["consumption"],i["energy_cost"],i["base_cost"],i["total_cost"]])
    return out.getvalue()


def intervals(data):
    result=[]
    for before,after in zip(data["readings"],data["readings"][1:]):
        tariff=tariff_at(data,before["date"])
        used=Decimal(after["value"])-Decimal(before["value"])
        a, b = date.fromisoformat(before["date"]), date.fromisoformat(after["date"])
        stop = min(b, date.fromisoformat(tariff.get("end", b.isoformat())))
        covered = max((stop-a).days, 0)
        used = used * Decimal(covered) / Decimal((b-a).days)
        energy=used*Decimal(tariff["price"])
        base=fee(tariff["monthly_fee"], a, max(a,stop))
        result.append({"from":before["date"],"to":after["date"],"tariff":tariff["name"],"consumption":float(used),"energy_cost":float(energy),"base_cost":float(base),"total_cost":float(energy+base)})
    return result
