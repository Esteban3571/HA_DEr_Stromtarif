from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.util import dt as dt_util
from .const import DOMAIN
from .entity import LedgerEntity
from .model import due


async def async_setup_entry(hass, entry, async_add_entities):
    ledger=hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ReadingDue(ledger,"reading_due","Ablesung fällig"),SourceProblem(ledger,"source_problem","Zählersensor gestört")])


class ReadingDue(LedgerEntity, BinarySensorEntity):
    _attr_icon = "mdi:counter"

    @property
    def is_on(self):
        return dt_util.now().date() >= due(self.ledger.data)


class SourceProblem(LedgerEntity, BinarySensorEntity):
    _attr_icon="mdi:alert-circle-outline"

    @property
    def is_on(self):
        return bool(self.ledger.source_error)

    @property
    def extra_state_attributes(self):
        return {"fehler":self.ledger.source_error,"quelle":self.ledger.data.get("source")}
