from homeassistant.helpers.entity import Entity, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from .const import DOMAIN


class LedgerEntity(Entity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, ledger, key, name):
        self.ledger = ledger
        self._attr_unique_id = f"{ledger.entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, ledger.entry.entry_id)},
                                            name=ledger.entry.title, manufacturer="Stromtarif", model="Lokales Tarifbuch")

    async def async_added_to_hass(self):
        self.async_on_remove(async_dispatcher_connect(self.hass, self.ledger.signal, self.async_write_ha_state))
