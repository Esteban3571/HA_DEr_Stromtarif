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


def migrate(data):
    """Add fields without discarding old tariff or reading data."""
    data.setdefault("payments", [])
    data.setdefault("monthly_installment", "0")
    data.setdefault("payment_day", 1)
    data.setdefault("billing_start", data["readings"][0]["date"])
    start = date.fromisoformat(data["billing_start"])
    data.setdefault("billing_end", start.replace(year=start.year + 1, day=min(start.day, monthrange(start.year + 1, start.month)[1])).isoformat())
    data.setdefault("source", None)
    return data


def configure_finances(data, start, end, installment, payment_day):
    start = date.fromisoformat(str(start))
    end = date.fromisoformat(str(end))
    if end <= start or start.isoformat() not in {r["date"] for r in data["readings"]}:
        raise ValueError("billing_dates")
    day = int(payment_day)
    if not 1 <= day <= 28:
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
        left, right = max(a,start), min(b,end)
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
    start, end = date.fromisoformat(data["billing_start"]), date.fromisoformat(data["billing_end"])
    cursor = start.replace(day=1)
    count = 0
    while cursor < end:
        if start <= cursor.replace(day=data["payment_day"]) < end:
            count += 1
        cursor = cursor.replace(day=monthrange(cursor.year,cursor.month)[1]) + timedelta(days=1)
    return count * float(data["monthly_installment"])


def finances(data):
    start, end = date.fromisoformat(data["billing_start"]), date.fromisoformat(data["billing_end"])
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
        energy=used*Decimal(tariff["price"])
        base=fee(tariff["monthly_fee"],date.fromisoformat(before["date"]),date.fromisoformat(after["date"]))
        result.append({"from":before["date"],"to":after["date"],"tariff":tariff["name"],"consumption":float(used),"energy_cost":float(energy),"base_cost":float(base),"total_cost":float(energy+base)})
    return result
