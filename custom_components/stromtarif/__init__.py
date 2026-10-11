"""Local electricity tariff ledger."""
import asyncio
from copy import deepcopy
from datetime import timedelta

from homeassistant.components import persistent_notification
from homeassistant.helpers.event import async_track_time_interval, async_track_state_change_event
from homeassistant.helpers.storage import Store
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from .const import DOMAIN, PLATFORMS
from .model import initial, due, migrate, source_value, ingest_source, active


class Ledger:
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self.store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
        self.data = None
        self.lock = asyncio.Lock()
        self.signal = f"{DOMAIN}.{entry.entry_id}.updated"
        from .reminders import ReminderManager
        self.reminders = ReminderManager(self)
        self.source_error = None
        self.source_unsub = None
        self.notification_id = f"{DOMAIN}_{entry.entry_id}"

    async def load(self):
        self.data = await self.store.async_load()
        if self.data is None:
            self.data = initial(self.entry.data, dt_util.now().date())
            await self.store.async_save(self.data)
        migrate(self.data)
        await self.store.async_save(self.data)

    async def mutate(self, operation, *, expected_revision=None):
        async with self.lock:
            if expected_revision is not None and expected_revision != self.data["revision"]:
                raise ValueError("stale_data")
            updated = deepcopy(self.data)
            operation(updated)
            if updated == self.data:
                return
            updated["revision"] = self.data["revision"] + 1
            await self.store.async_save(updated)
            self.data = updated
        if not active(self.data) or self.data.get("notified_due") is None or due(self.data)>dt_util.now().date():
            persistent_notification.async_dismiss(self.hass, self.notification_id)
        await self.tick(sample=False)

    async def tick(self, _now=None, *, sample=True):
        if sample:
            await self.update_source()
        async with self.lock:
            deadline = due(self.data)
            if active(self.data) and dt_util.now().date() >= deadline and self.data.get("notified_due") != deadline.isoformat():
                # Notification and marker survive restarts; no repeat every hour.
                persistent_notification.async_create(
                    self.hass,
                    f"Bitte einen Zählerstand für {self.entry.title} erfassen. "
                    f"Die Ablesung ist seit {deadline.isoformat()} fällig. "
                    "Einstellungen → Geräte & Dienste → Stromtarif → Konfigurieren → Ablesung erfassen.",
                    title="Stromzähler ablesen", notification_id=self.notification_id)
                updated = deepcopy(self.data)
                updated["notified_due"] = deadline.isoformat()
                await self.store.async_save(updated)
                self.data = updated
        await self.reminders.sync()
        async_dispatcher_send(self.hass, self.signal)


    def bind_source(self):
        if self.source_unsub:
            self.source_unsub()
            self.source_unsub = None
        self.source_error = None
        if self.data["source"]:
            async def changed(event):
                await self.update_source()
            self.source_unsub = async_track_state_change_event(self.hass,self.data["source"]["entity_id"],changed)

    def unbind_source(self):
        if self.source_unsub:
            self.source_unsub()
            self.source_unsub = None

    async def update_source(self):
        source=self.data["source"]
        if not source or not active(self.data):
            return
        state=self.hass.states.get(source["entity_id"])
        try:
            if state is None:
                raise ValueError("invalid_source")
            raw=source_value(state.state,state.attributes)
            # Mutation uses a locked fresh copy: concurrent sensor events cannot
            # lose history or overwrite a simultaneous manual reading.
            await self.mutate(lambda data:ingest_source(data,raw,dt_util.now().date()))
            self.source_error=None
        except ValueError as err:
            self.source_error=str(err)
            if self.source_error=="source_reset" and not self.data["source"].get("reset_detected"):
                await self.mutate(lambda data:data["source"].update(reset_detected=True))
        async_dispatcher_send(self.hass,self.signal)


async def async_setup_entry(hass, entry):
    ledger = Ledger(hass, entry)
    await ledger.load()
    from .frontend import async_setup_frontend
    await async_setup_frontend(hass)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = ledger
    from .frontend import async_update_panel
    await async_update_panel(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(async_track_time_interval(hass, ledger.tick, timedelta(hours=1)))
    ledger.bind_source()
    entry.async_on_unload(ledger.unbind_source)
    await ledger.tick()
    return True


async def async_unload_entry(hass, entry):
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        from .frontend import async_update_panel
        await async_update_panel(hass)
        return True
    return False


async def async_remove_entry(hass, entry):
    ledger = Ledger(hass, entry)
    await ledger.load()
    ledger.data["reminders"].update(calendar=None, todo=None)
    await ledger.reminders.sync()
    if ledger.reminders.error:
        persistent_notification.async_create(hass,
            "Das Tarifbuch wurde entfernt, aber eigene Kalender-/To-do-Erinnerungen konnten nicht vollständig gelöscht werden. " + ledger.reminders.error,
            title="DEr Stromtarif: Erinnerungen prüfen", notification_id=f"{DOMAIN}_cleanup_{entry.entry_id}")
    await Store(hass, 1, f"{DOMAIN}.{entry.entry_id}").async_remove()
    persistent_notification.async_dismiss(hass, f"{DOMAIN}_{entry.entry_id}")
