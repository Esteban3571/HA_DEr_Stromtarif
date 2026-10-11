from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.util import dt as dt_util
from .const import DOMAIN
from .entity import LedgerEntity
from .model import due


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([ReadingDue(hass.data[DOMAIN][entry.entry_id], "reading_due", "Ablesung fällig")])


class ReadingDue(LedgerEntity, BinarySensorEntity):
    _attr_icon = "mdi:counter"

    @property
    def is_on(self):
        return dt_util.now().date() >= due(self.ledger.data)
