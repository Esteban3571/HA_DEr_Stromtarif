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
    meter_number = str(data.get("meter_number", "")).strip()
    if "meter_number" in data and not meter_number:
        raise ValueError("invalid_meter")
    tariff["meter_id"] = "meter_1"
    return {"meters": [{"id": "meter_1", "number": meter_number}], "tariffs": [tariff], "readings": [
        {"date": tariff["start"], "value": tariff["reading"], "kind": "initial", "meter_id": "meter_1", "meter_number": meter_number}],
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
    ledger["readings"].append({"date": when, "value": value, "kind": "manual", "meter_id": last.get("meter_id", "meter_1"), "meter_number": last.get("meter_number", "")})
    ledger["notified_due"] = None


def change_tariff(ledger, data, today):
    tariff = make_tariff(data, today)
    last = ledger["readings"][-1]
    tariff["meter_id"] = last.get("meter_id", "meter_1")
    if tariff["start"] <= ledger["tariffs"][-1]["start"] or tariff["start"] < last["date"]:
        raise ValueError("date_order")
    if tariff["start"] == last["date"]:
        if Decimal(tariff["reading"]) != Decimal(last["value"]):
            raise ValueError("boundary_mismatch")
    else:
        add_reading(ledger, tariff["reading"], tariff["start"], today)
        ledger["readings"][-1]["kind"] = "tariff"
    old = ledger["tariffs"][-1]
    old["end_meter_id"] = last.get("meter_id", "meter_1")
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
    data.setdefault("meters", [{"id": "meter_1", "number": ""}])
    for reading in data["readings"]:
        reading.setdefault("meter_id", "meter_1")
        reading.setdefault("meter_number", next(m["number"] for m in data["meters"] if m["id"] == reading["meter_id"]))
    for tariff in data["tariffs"]:
        tariff.setdefault("meter_id", next(r["meter_id"] for r in data["readings"] if r["date"] == tariff["start"]))
        if tariff.get("end"):
            tariff.setdefault("end_meter_id", next(r["meter_id"] for r in reversed(data["readings"]) if r["date"] == tariff["end"]))
    data.setdefault("revision", 0)
    data.setdefault("show_panel", False)
    data.setdefault("payments", [])
    data.setdefault("monthly_installment", "0")
    data.setdefault("installment_changes", [])
    data.setdefault("payment_day", 1)
    data.setdefault("billing_start", data["readings"][0]["date"])
    start = date.fromisoformat(data["billing_start"])
    data.setdefault("billing_end", start.replace(year=start.year + 1, day=min(start.day, monthrange(start.year + 1, start.month)[1])).isoformat())
    data.setdefault("billing_cutoff", data["billing_end"][5:])
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
    if data["readings"][-1]["kind"] != "meter_start":
        data["readings"][-1]["kind"] = "final"
    tariff = data["tariffs"][-1]
    tariff.update(active=False, end=end, end_reading=data["readings"][-1]["value"], end_meter_id=data["readings"][-1]["meter_id"])
    if values.get("final_bill"):
        record_bill(data, values, tariff)
    data["notified_due"] = None


def rename_meter(data, meter_id, meter_number):
    meter_number = str(meter_number).strip()
    if not meter_number or any(m["number"] == meter_number and m["id"] != meter_id for m in data["meters"]):
        raise ValueError("invalid_meter")
    meter = next((m for m in data["meters"] if m["id"] == meter_id), None)
    if meter is None:
        raise ValueError("invalid_meter")
    meter["number"] = meter_number
    for reading in data["readings"]:
        if reading["meter_id"] == meter_id:
            reading["meter_number"] = meter_number


def replace_meter(data, values, today):
    when = valid_date(values["date"], today)
    meter_number = str(values["meter_number"]).strip()
    last = data["readings"][-1]
    if not active(data) or not last.get("meter_number") or not meter_number or any(m["number"] == meter_number for m in data["meters"]):
        raise ValueError("invalid_meter")
    if when < last["date"] or last["kind"] in {"meter_end", "meter_start", "final"} and when == last["date"]:
        raise ValueError("date_order")
    final = number(values["old_reading"])
    initial_value = number(values["new_reading"])
    if when == last["date"]:
        if Decimal(final) != Decimal(last["value"]):
            raise ValueError("boundary_mismatch")
    else:
        add_reading(data, final, when, today)
    data["readings"][-1]["kind"] = "meter_end"
    new_id = "meter_" + str(len(data["meters"]) + 1)
    data["meters"].append({"id": new_id, "number": meter_number})
    data["readings"].append({"date": when, "value": initial_value, "kind": "meter_start", "meter_id": new_id, "meter_number": meter_number})
    # A physical replacement needs a newly selected/calibrated source.
    data["source"] = None
    data["notified_due"] = None
    validate_history(data, today)


def installment_at(data, when):
    amount = data["monthly_installment"]
    for change in sorted(data.get("installment_changes", []), key=lambda row: row["date"]):
        if change["date"] <= when:
            amount = change["amount"]
    return amount


def change_installment(data, when, amount):
    when = date.fromisoformat(str(when)).isoformat()
    if when < data["readings"][0]["date"]:
        raise ValueError("billing_dates")
    amount = number(amount)
    changes = [r for r in data["installment_changes"] if r["date"] != when]
    changes.append({"date": when, "amount": amount})
    data["installment_changes"] = sorted(changes, key=lambda row: row["date"])


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
        amount = installment_at(data, when)
        if start.isoformat() <= when < end.isoformat() and Decimal(amount) > 0:
            rows[when] = {"key": when, "date": when, "amount": amount}
        cursor = cursor.replace(day=days) + timedelta(days=1)
    for key, override in data.get("payment_overrides", {}).items():
        rows.pop(key, None)
        if override and start.isoformat() <= override["date"] < end.isoformat():
            rows.pop(override["date"], None)
            rows[key] = {"key": key, **override}
    paid = {p.get("schedule_key") for p in data["payments"]}
    for row in rows.values():
        row["paid"] = row["key"] in paid
        row.setdefault("auto_pay", False)
    return sorted(rows.values(), key=lambda row: (row["date"], row["key"]))


def edit_planned_payment(data, key, when, amount, remove=False, auto_pay=False):
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
    data["payment_overrides"][key] = {"date": when, "amount": amount, "auto_pay": auto_pay}


def settle_payment(data, key, today, *, automatic=False):
    row = next((r for r in payment_schedule(data) if r["key"] == key), None)
    if row is None:
        raise ValueError("invalid_input")
    if row["paid"]:
        return
    when = row["date"] if automatic else min(row["date"], today.isoformat())
    add_payment(data, row["amount"], when, today)
    data["payments"][-1].update(schedule_key=key, automatic=automatic)


def auto_settle_payments(data, today):
    if active(data):
        for row in payment_schedule(data):
            if row["auto_pay"] and not row["paid"] and row["date"] <= today.isoformat():
                settle_payment(data, row["key"], today, automatic=True)


def delete_payment(data, index):
    payment = data["payments"].pop(index)
    key = payment.get("schedule_key")
    if key:
        row = next((r for r in payment_schedule(data) if r["key"] == key), None)
        if row:
            edit_planned_payment(data, key, row["date"], row["amount"], auto_pay=False)


def configure_finances(data, start, end, installment, payment_day, installment_from=None):
    start = date.fromisoformat(str(start))
    end = date.fromisoformat(str(end))
    if end <= start or start.isoformat() < data["readings"][0]["date"]:
        raise ValueError("billing_dates")
    day = int(payment_day)
    if day != float(payment_day) or not 0 <= day <= 31:
        raise ValueError("invalid_input")
    if installment_from is not None:
        change_installment(data, installment_from, installment)
        installment = data["monthly_installment"]
    data["billing_cutoff"] = end.strftime("%m-%d")
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
        if before.get("meter_id") != after.get("meter_id"):
            continue
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


def record_period_bill(data, values, today):
    """Record the supplier invoice without closing an ongoing contract."""
    start = valid_date(values["start"], today)
    end = valid_date(values["end"], today)
    if start < data["readings"][0]["date"] or end <= start:
        raise ValueError("billing_dates")
    if any(b.get("kind") == "period" and start < b["end"] and end > b["start"] for b in data["bills"]):
        raise ValueError("duplicate_bill")
    advance = values.get("advance", True)
    if not isinstance(advance, bool) or (advance and (start != data["billing_start"] or end != data["billing_end"])):
        raise ValueError("billing_dates")
    if values["balance_kind"] not in {"payment", "refund"}:
        raise ValueError("invalid_input")
    consumption, cost, estimated = period_cost(data, date.fromisoformat(start), date.fromisoformat(end))
    paid = sum(Decimal(p["amount"]) for p in data["payments"] if start <= p["date"] < end)
    balance = Decimal(number(values["invoice_balance"]))
    tariffs = [t["name"] for t in data["tariffs"] if t["start"] < end and t.get("end", "9999-12-31") > start]
    data["bills"].append({"kind": "period", "tariff": " / ".join(tariffs), "start": start, "end": end,
        "reading": "", "invoice_total": number(values["invoice_total"]),
        "balance": str(-balance if values["balance_kind"] == "refund" else balance),
        "paid_at_recording": str(paid), "consumption_at_recording": consumption,
        "cost_at_recording": cost, "estimated_at_recording": estimated})
    if advance:
        cutoff = date.fromisoformat(end)
        month, day = map(int, data["billing_cutoff"].split("-"))
        next_end = date(cutoff.year + 1, month, min(day, monthrange(cutoff.year + 1, month)[1]))
        data.update(billing_start=end, billing_end=next_end.isoformat())


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
    writer.writerow(["Typ","Datum","Name/Art","Zaehlerstand_kWh","Arbeitspreis_EUR_kWh","Grundgebuehr_EUR_Monat","Zahlung_EUR","Verbrauch_kWh","Arbeitspreiskosten_EUR","Grundgebuehr_EUR","Gesamtkosten_EUR","Zaehlernummer"])
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
        rows.append((bill["end"], ["Periodenabrechnung" if bill.get("kind") == "period" else "Endabrechnung", bill["end"], safe(bill["tariff"]), bill["reading"], "", "", "", "", "", "", bill["invoice_total"]]))
        rows.append((bill["end"], ["Abrechnungssaldo", bill["end"], "Nachzahlung positiv / Guthaben negativ", "", "", "", bill["balance"]]))
    for row in payment_schedule(data):
        rows.append((row["date"], ["Geplanter Abschlag", row["date"], "", "", "", "", row["amount"]]))
    for _,row in sorted(rows,key=lambda item:item[0]):
        writer.writerow((row+[""]*11)[:11]+[safe(next((r.get("meter_number", "") for r in data["readings"] if row[0] == "Ablesung" and r["date"] == row[1] and r["kind"] == row[2]), ""))])
    for i in intervals(data):
        writer.writerow(["Zeitraum",i["to"],safe(i["tariff"]),"","","","",i["consumption"],i["energy_cost"],i["base_cost"],i["total_cost"],safe(i.get("meter_number", ""))])
    return out.getvalue()


def intervals(data):
    result=[]
    for before,after in zip(data["readings"],data["readings"][1:]):
        if before.get("meter_id") != after.get("meter_id"):
            continue
        tariff=tariff_at(data,before["date"])
        used=Decimal(after["value"])-Decimal(before["value"])
        a, b = date.fromisoformat(before["date"]), date.fromisoformat(after["date"])
        stop = min(b, date.fromisoformat(tariff.get("end", b.isoformat())))
        covered = max((stop-a).days, 0)
        used = used * Decimal(covered) / Decimal((b-a).days)
        energy=used*Decimal(tariff["price"])
        base=fee(tariff["monthly_fee"], a, max(a,stop))
        result.append({"from":before["date"],"to":after["date"],"tariff":tariff["name"],"meter_number":before.get("meter_number", ""),"consumption":float(used),"energy_cost":float(energy),"base_cost":float(base),"total_cost":float(energy+base)})
    return result


def validate_history(data, today):
    """Ensure edited records still form ordered meter and tariff boundaries."""
    readings = data["readings"]
    if not readings:
        raise ValueError("cannot_undo")
    for i, reading in enumerate(readings):
        valid_date(reading["date"], today)
        number(reading["value"])
        if reading.get("meter_id") not in {m["id"] for m in data["meters"]}:
            raise ValueError("invalid_meter")
        if i:
            previous = readings[i-1]
            changed = reading["meter_id"] != previous["meter_id"]
            if changed:
                if reading["kind"] != "meter_start" or previous["kind"] != "meter_end" or reading["date"] != previous["date"]:
                    raise ValueError("meter_boundary")
            elif reading["date"] <= previous["date"]:
                raise ValueError("date_order")
            elif Decimal(reading["value"]) < Decimal(previous["value"]):
                raise ValueError("reading_decreased")
    by_date = {(r["date"], r["meter_id"]): r for r in readings}
    for i, tariff in enumerate(data["tariffs"]):
        if i and tariff["start"] <= data["tariffs"][i-1]["start"]:
            raise ValueError("date_order")
        if (tariff["start"],tariff["meter_id"]) not in by_date or Decimal(tariff["reading"]) != Decimal(by_date[(tariff["start"],tariff["meter_id"])]["value"]):
            raise ValueError("boundary_mismatch")
        if tariff.get("end"):
            if tariff["end"] < tariff["start"] or (tariff["end"],tariff.get("end_meter_id",tariff["meter_id"])) not in by_date:
                raise ValueError("boundary_mismatch")
            if i+1 < len(data["tariffs"]) and tariff["end"] > data["tariffs"][i+1]["start"]:
                raise ValueError("date_order")
    if data["billing_start"] < readings[0]["date"] or data["billing_end"] <= data["billing_start"]:
        raise ValueError("billing_dates")


def edit_reading(data, index, when, value, today):
    old = data["readings"][index]
    old_date = old["date"]
    when = valid_date(when, today)
    value = number(value)
    # Invoice dates are supplier facts. Correct the bill explicitly first.
    if when != old_date and any(old_date in {bill["start"], bill["end"]} for bill in data["bills"]):
        raise ValueError("invoice_boundary")
    partner = None
    if old["kind"] in {"meter_end", "meter_start"}:
        partner = data["readings"][index + (1 if old["kind"] == "meter_end" else -1)]
        partner["date"] = when
    old.update(date=when, value=value)
    if old["kind"] == "automatic":
        old["kind"] = "manual"
    for tariff in data["tariffs"]:
        if tariff["start"] == old_date and tariff.get("meter_id") == old.get("meter_id"):
            tariff.update(start=when, reading=value)
        if tariff.get("end") == old_date and tariff.get("end_meter_id", tariff.get("meter_id")) == old.get("meter_id"):
            tariff.update(end=when, end_reading=value)
    if partner and when != old_date:
        for tariff in data["tariffs"]:
            if tariff["start"] == old_date and tariff.get("meter_id") == partner["meter_id"]:
                tariff["start"] = when
            if tariff.get("end") == old_date and tariff.get("end_meter_id",tariff.get("meter_id")) == partner["meter_id"]:
                tariff["end"] = when
    for bill in data["bills"]:
        if bill["end"] == old_date and old["kind"] != "meter_start":
            bill["reading"] = value
    if index == 0 and data["billing_start"] == old_date:
        data["billing_start"] = when
    validate_history(data, today)
    data["notified_due"] = None


def delete_reading(data, index, today):
    reading = data["readings"][index]
    if index == 0 or reading["kind"] in {"meter_start", "meter_end"} or any(reading["date"] in {t["start"], t.get("end")} for t in data["tariffs"]):
        raise ValueError("cannot_undo")
    data["readings"].pop(index)
    validate_history(data, today)
    data["notified_due"] = None


def tariff_summary(data, index):
    tariff = data["tariffs"][index]
    start = date.fromisoformat(tariff["start"])
    end = min(date.fromisoformat(tariff.get("end", data["readings"][-1]["date"])), date.fromisoformat(data["readings"][-1]["date"]))
    consumption, cost, estimated = period_cost(data, start, end)
    return {"index": index, "name": tariff["name"], "start": start.isoformat(), "end": end.isoformat(),
            "consumption": consumption, "cost": cost, "estimated": estimated,
            "effective_price": cost / consumption if consumption > 0 else None}


def consumption_periods(data, unit="month", tariff_index=None):
    if unit not in {"month", "quarter", "year"}:
        raise ValueError("invalid_input")
    begin = date.fromisoformat(data["readings"][0]["date"])
    end = date.fromisoformat(data["readings"][-1]["date"])
    if tariff_index is not None:
        tariff = data["tariffs"][tariff_index]
        begin = date.fromisoformat(tariff["start"])
        end = min(end, date.fromisoformat(tariff.get("end", end.isoformat())))
    months = {"month": 1, "quarter": 3, "year": 12}[unit]
    cursor = begin.replace(month=((begin.month-1)//months)*months+1, day=1)
    rows = []
    while cursor < end:
        absolute = cursor.year*12 + cursor.month-1 + months
        stop = date(absolute//12, absolute%12+1, 1)
        left, right = max(begin,cursor), min(end,stop)
        consumption, cost, estimated = period_cost(data,left,right)
        # Missing unobserved days are not extrapolated into period totals.
        partial = left != cursor or right != stop
        label = str(cursor.year) if unit == "year" else f"{cursor.year} Q{(cursor.month-1)//3+1}" if unit == "quarter" else cursor.strftime("%Y-%m")
        rows.append({"label": label, "start": left.isoformat(), "end": right.isoformat(),
            "consumption": consumption, "cost": cost, "estimated": estimated, "partial": partial,
            "effective_price": cost/consumption if consumption > 0 else None})
        cursor = stop
    return rows
