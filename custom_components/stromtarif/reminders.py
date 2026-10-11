"""Reconcile only integration-owned calendar events and to-do items."""
import asyncio
from datetime import datetime, time, timedelta
from homeassistant.components.calendar.const import CalendarEntityFeature
from homeassistant.components.todo import TodoItem
from homeassistant.components.todo.const import TodoListEntityFeature, TodoItemStatus
from homeassistant.util import dt as dt_util
from .model import active, due, payment_schedule


def target_entity(hass, entity_id):
    if not entity_id:
        return None
    component = hass.data.get(entity_id.split('.')[0])
    return component.get_entity(entity_id) if component else None


def validate_targets(hass, values):
    for domain, features in (("calendar", CalendarEntityFeature.CREATE_EVENT | CalendarEntityFeature.DELETE_EVENT),
                             ("todo", TodoListEntityFeature.CREATE_TODO_ITEM | TodoListEntityFeature.DELETE_TODO_ITEM)):
        entity_id = values.get(domain)
        if not entity_id:
            continue
        entity = target_entity(hass, entity_id)
        if not entity_id.startswith(domain + '.') or entity is None or not entity.available or entity.supported_features & features != features:
            raise ValueError("invalid_reminder_target")


class ReminderManager:
    def __init__(self, ledger):
        self.ledger = ledger
        self.lock = asyncio.Lock()
        self.error = None

    def desired(self):
        data = self.ledger.data
        options = data["reminders"]
        rows = {}
        if not active(data):
            return rows
        name = data["tariffs"][-1]["name"]
        if options["readings"]:
            rows["reading:" + due(data).isoformat()] = {"date": due(data), "summary": f"Zähler ablesen: {name}", "description": "Zählerstand in DEr Stromtarif erfassen."}
        if options["payments"]:
            for payment in payment_schedule(data):
                when = dt_util.parse_date(payment["date"])
                if when >= dt_util.now().date():
                    rows["payment:" + payment["key"]] = {"date": when, "summary": f"Abschlag: {name} ({float(payment['amount']):.2f} EUR)", "description": "Geplanter Abschlag; keine gebuchte Zahlung."}
        return rows

    async def sync(self):
        async with self.lock:
            try:
                await self._sync()
                self.error = None
            except Exception as err:
                # A temporarily unavailable target must not prevent ledger use.
                self.error = f"{type(err).__name__}: {err}"

    async def _sync(self):
        ledger = self.ledger
        options = ledger.data["reminders"]
        wanted = self.desired()
        marker = f"[DEr Stromtarif:{ledger.entry.entry_id}:"
        targets = list(ledger.data["reminder_targets"])
        for domain in ("calendar", "todo"):
            entity_id = options[domain]
            if entity_id and entity_id not in targets:
                targets.append(entity_id)
        # Persist targets before remote creation: restart after a failed save
        # still discovers the tagged objects and cannot duplicate them.
        if targets != ledger.data["reminder_targets"]:
            async with ledger.lock:
                ledger.data["reminder_targets"] = targets
                await ledger.store.async_save(ledger.data)
        errors = []
        for entity_id in targets:
            try:
                entity = target_entity(ledger.hass, entity_id)
                if entity is None or not entity.available:
                    raise ValueError(f"Erinnerungsziel nicht verfügbar: {entity_id}")
                domain = entity_id.split('.')[0]
                desired = wanted if options[domain] == entity_id else {}
                if domain == "calendar":
                    await self.calendar(entity, desired, marker)
                else:
                    # Tasks are reading reminders; payments are calendar entries.
                    await self.todo(entity, {key: row for key, row in desired.items() if key.startswith('reading:')}, marker)
            except Exception as err:
                errors.append(f"{entity_id}: {type(err).__name__}: {err}")
        if errors:
            raise ValueError("; ".join(errors))

    async def calendar(self, entity, desired, marker):
        data = self.ledger.data
        start = dt_util.start_of_local_day(datetime.combine(dt_util.parse_date(data["readings"][0]["date"]), time()))
        latest = max([dt_util.parse_date(data["billing_end"]), due(data), dt_util.now().date()] + [row['date'] for row in desired.values()])
        end = dt_util.start_of_local_day(datetime.combine(latest + timedelta(days=731), time()))
        # Preserve previously planned range when shortening a billing period.
        range_end = max(data.get("reminder_range_end", ""), end.isoformat())
        async with self.ledger.lock:
            self.ledger.data["reminder_range_end"] = range_end
            await self.ledger.store.async_save(self.ledger.data)
        events = await entity.async_get_events(self.ledger.hass, start, datetime.fromisoformat(range_end))
        found = {}
        for event in events:
            description = event.description or ''
            if not description.startswith(marker):
                continue
            key = description[len(marker):].split(']', 1)[0]
            row = desired.get(key)
            expected = f"{marker}{key}]\n{row['description']}" if row else None
            if key not in found and row and event.start == row['date'] and event.end == row['date'] + timedelta(days=1) and event.summary == row['summary'] and description == expected:
                found[key] = True
                continue
            # Past appointments are historical records, not future reminders.
            if key.startswith("payment:") and event.start_datetime_local.date() < dt_util.now().date() and key not in desired:
                continue
            if not event.uid:
                raise ValueError("Kalender liefert keine Termin-ID; Änderung nicht möglich")
            await entity.async_delete_event(event.uid)
        for key, row in desired.items():
            if key in found:
                continue
            await entity.async_create_event(dtstart=row['date'], dtend=row['date'] + timedelta(days=1), summary=row['summary'], description=f"{marker}{key}]\n{row['description']}")
        entity.async_write_ha_state()

    async def todo(self, entity, desired, marker):
        await entity.async_update()
        found = set()
        descriptions = bool(entity.supported_features & TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM)
        for item in entity.todo_items or []:
            summary = item.summary or ''
            ownership = (item.description or '') if descriptions else summary
            if not ownership.startswith(marker):
                continue
            key = ownership[len(marker):].split(']', 1)[0]
            row = desired.get(key)
            expected = (row['summary'] if descriptions else f"{marker}{key}] {row['summary']}") if row else None
            if row and key not in found and summary == expected:
                found.add(key)  # Completed tasks stay completed until the next reading.
            elif item.uid:
                await entity.async_delete_todo_items([item.uid])
            else:
                raise ValueError("To-do-Liste liefert keine Aufgaben-ID")
        for key, row in desired.items():
            if key not in found:
                await entity.async_create_todo_item(TodoItem(summary=row["summary"] if descriptions else f"{marker}{key}] {row['summary']}", description=f"{marker}{key}]" if descriptions else None, status=TodoItemStatus.NEEDS_ACTION,
                    due=row['date'] if entity.supported_features & TodoListEntityFeature.SET_DUE_DATE_ON_ITEM else None))
        await entity.async_update()
        entity.async_write_ha_state()
