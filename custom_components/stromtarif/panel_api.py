"""Validated panel operations; all writes use the ledger's revision and lock."""
from . import model as m
from .reminders import validate_targets

ERRORS = {
    "history_invalid": "Bitte die Hinweise im Assistenten prüfen. Der Entwurf bleibt erhalten; die aktive Historie wurde nicht verändert.",
    "invalid_meter": "Bitte eine eindeutige Zählernummer angeben; beim Altbestand zuerst die bisherige Nummer hinterlegen.",
    "meter_boundary": "Zählerwechsel benötigt Endstand und Anfangsstand am selben Datum.",
    "duplicate_bill": "Für diesen Zeitraum wurde bereits eine Periodenabrechnung erfasst.",
    "stale_data": "Die Daten wurden inzwischen geändert. Bitte neu laden und die Änderung erneut prüfen.",
    "future_date": "Das Ablesedatum darf nicht in der Zukunft liegen.",
    "date_order": "Die Daten müssen zwischen den benachbarten Ablesungen bzw. Tarifgrenzen liegen.",
    "reading_decreased": "Der Zählerstand darf gegenüber der vorherigen Ablesung nicht sinken oder die nächste überschreiten.",
    "boundary_mismatch": "Tarifgrenzen müssen zu den erfassten Ablesungen passen.",
    "invoice_boundary": "An dieser Datumsgrenze liegt eine Endabrechnung. Deren Zeitraum zuerst korrigieren oder entfernen.",
    "cannot_undo": "Anfangsstände und Tarifgrenzen können korrigiert, aber nicht gelöscht werden.",
    "invalid_number": "Bitte eine endliche, nicht negative Zahl eingeben.",
    "billing_dates": "Bitte den Abrechnungszeitraum und die darin liegenden Termine prüfen.",
    "duplicate_payment_date": "An diesem Datum gibt es bereits einen geplanten Abschlag.",
    "invalid_reminder_target": "Das Ziel muss verfügbar sein und Einträge erstellen sowie löschen können.",
    "invalid_source": "Bitte einen verfügbaren kumulativen Wh-/kWh-Energiesensor auswählen.",
    "closed_tariff": "Ein abgerechneter oder historischer Tarif kann nicht reaktiviert werden. Bitte einen neuen Tarif anlegen.",
    "invalid_input": "Bitte die Eingaben prüfen.",
}


def index(values, data, collection):
    value = values["index"]
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < len(data[collection]):
        raise ValueError("invalid_input")
    return value


def boolean(values, key):
    if not isinstance(values[key], bool):
        raise ValueError("invalid_input")
    return values[key]


def apply(hass, data, operation, values, today):
    if operation.startswith("history_"):
        from . import history_wizard as w
        if operation == "history_start":data["history_draft"]=w.seed(data)
        elif operation == "history_save":w.save(data,values["draft"])
        elif operation == "history_apply":
            if not boolean(values,"confirm"):raise ValueError("invalid_input")
            w.adopt(data,today)
        elif operation == "history_restore":
            if not boolean(values,"confirm"):raise ValueError("invalid_input")
            w.restore(data)
        else:raise ValueError("invalid_input")
    elif operation == "reading_add":
        m.add_reading(data, values["reading"], values["date"], today)
    elif operation == "meter_rename":
        m.rename_meter(data,values["meter_id"],values["meter_number"])
    elif operation == "meter_replace":
        m.replace_meter(data,values,today)
    elif operation == "reading_edit":
        m.edit_reading(data, index(values,data,"readings"), values["date"], values["reading"], today)
    elif operation == "reading_delete":
        m.delete_reading(data, index(values,data,"readings"), today)
    elif operation == "undo":
        m.undo_reading(data)
    elif operation == "tariff_add":
        validate_targets(hass,values)
        m.change_tariff(data,values,today)
    elif operation == "tariff_edit":
        i = index(values,data,"tariffs")
        tariff = data["tariffs"][i]
        name = str(values["name"]).strip()
        if not name:
            raise ValueError("invalid_input")
        for bill in data["bills"]:
            if bill["tariff"] == tariff["name"] and tariff["start"] <= bill["start"] < tariff.get("end","9999-12-31"):
                bill["tariff"] = name
        tariff.update(name=name, price=m.number(values["price"]), monthly_fee=m.number(values["monthly_fee"]))
        if "active" in values and boolean(values,"active") != tariff["active"]:
            if i != len(data["tariffs"])-1:
                raise ValueError("closed_tariff")
            if values["active"]:
                if data["readings"][-1]["kind"] == "final" or any(b["end"] == tariff.get("end") and b["tariff"] == tariff["name"] for b in data["bills"]):
                    raise ValueError("closed_tariff")
                tariff["active"] = True
                tariff.pop("end",None);tariff.pop("end_reading",None)
            else:
                tariff.update(active=False, end=data["readings"][-1]["date"], end_reading=data["readings"][-1]["value"], end_meter_id=data["readings"][-1]["meter_id"])
            data["notified_due"] = None
    elif operation == "close":
        m.close_tariff(data,values,today)
    elif operation == "interval":
        interval = int(values["interval"])
        if interval != float(values["interval"]) or not 1 <= interval <= 730:
            raise ValueError("invalid_input")
        data.update(interval=interval,notified_due=None)
    elif operation == "finances":
        if values["schedule_mode"] not in {"monthly","custom"}:
            raise ValueError("invalid_input")
        m.configure_finances(data,values["billing_start"],values["billing_end"],values["monthly_installment"],values["payment_day"],values.get("installment_from"))
        data["schedule_mode"] = values["schedule_mode"]
    elif operation == "installment_change":
        if "index" in values:
            i = index(values,data,"installment_changes")
            if boolean(values,"remove"):
                data["installment_changes"].pop(i)
                return
            old_date = data["installment_changes"][i]["date"]
            if old_date != values["date"]:
                if any(r["date"] == values["date"] for r in data["installment_changes"]):
                    raise ValueError("invalid_input")
                data["installment_changes"].pop(i)
        m.change_installment(data,values["date"],values["amount"])
    elif operation == "payment_add":
        m.add_payment(data,values["amount"],values["date"],today)
    elif operation == "payment_edit":
        i=index(values,data,"payments")
        amount=m.number(values["amount"])
        if float(amount)<=0:
            raise ValueError("invalid_number")
        data["payments"][i].update(date=m.valid_date(values["date"],today),amount=amount)
    elif operation == "payment_delete":
        m.delete_payment(data,index(values,data,"payments"))
    elif operation == "undo_payment":
        if not data["payments"]:
            raise ValueError("cannot_undo")
        m.delete_payment(data,-1)
    elif operation == "payment_settle":
        m.settle_payment(data,values["key"],today)
    elif operation == "planned_payment":
        m.edit_planned_payment(data,values["key"],values["date"],values["amount"],boolean(values,"remove"), boolean(values,"auto_pay") if "auto_pay" in values else False)
    elif operation == "bill_add":
        m.record_period_bill(data,values,today)
    elif operation == "bill_edit":
        i=index(values,data,"bills")
        start=m.valid_date(values["start"],today);end=m.valid_date(values["end"],today)
        if start>=end:
            raise ValueError("billing_dates")
        if data["bills"][i].get("kind") == "period" and any(j != i and b.get("kind") == "period" and start < b["end"] and end > b["start"] for j,b in enumerate(data["bills"])):
            raise ValueError("duplicate_bill")
        balance=m.number(values["invoice_balance"])
        if values["balance_kind"] not in {"payment","refund"}:
            raise ValueError("invalid_input")
        bill=data["bills"][i]
        bill.update(start=start,end=end,invoice_total=m.number(values["invoice_total"]),balance=str(-m.Decimal(balance)) if values["balance_kind"]=="refund" else balance)
    elif operation == "bill_delete":
        data["bills"].pop(index(values,data,"bills"))
    elif operation == "source":
        entity_id=values.get("entity_id") if boolean(values,"enabled") else None
        raw=None
        if entity_id:
            state=hass.states.get(entity_id)
            if state is None:
                raise ValueError("invalid_source")
            raw=m.source_value(state.state,state.attributes)
        elif values["enabled"]:
            raise ValueError("invalid_source")
        m.configure_source(data,entity_id,raw)
    elif operation == "reminders":
        validate_targets(hass,values)
        data["reminders"] = {key:values.get(key) or None for key in ("calendar","todo")}
        data["reminders"].update(readings=boolean(values,"readings"), payments=boolean(values,"payments"))
    elif operation == "panel":
        data["show_panel"] = boolean(values,"show_panel")
    else:
        raise ValueError("invalid_input")
