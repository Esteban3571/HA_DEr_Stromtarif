"""Local electricity tariff ledger."""
import asyncio
from copy import deepcopy
from datetime import timedelta

from homeassistant.components import persistent_notification
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import dt as dt_util

from .const import DOMAIN, PLATFORMS
from .model import initial, due


class Ledger:
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self.store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
        self.data = None
        self.lock = asyncio.Lock()
        self.signal = f"{DOMAIN}.{entry.entry_id}.updated"
        self.notification_id = f"{DOMAIN}_{entry.entry_id}"

    async def load(self):
        self.data = await self.store.async_load()
        if self.data is None:
            self.data = initial(self.entry.data, dt_util.now().date())
            await self.store.async_save(self.data)

    async def mutate(self, operation):
        async with self.lock:
            updated = deepcopy(self.data)
            operation(updated)
            await self.store.async_save(updated)
            self.data = updated
        persistent_notification.async_dismiss(self.hass, self.notification_id)
        await self.tick()

    async def tick(self, _now=None):
        async with self.lock:
            deadline = due(self.data)
            if dt_util.now().date() >= deadline and self.data.get("notified_due") != deadline.isoformat():
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
        async_dispatcher_send(self.hass, self.signal)


async def async_setup_entry(hass, entry):
    ledger = Ledger(hass, entry)
    await ledger.load()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = ledger
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(async_track_time_interval(hass, ledger.tick, timedelta(hours=1)))
    await ledger.tick()
    return True


async def async_unload_entry(hass, entry):
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        return True
    return False


async def async_remove_entry(hass, entry):
    await Store(hass, 1, f"{DOMAIN}.{entry.entry_id}").async_remove()
    persistent_notification.async_dismiss(hass, f"{DOMAIN}_{entry.entry_id}")
