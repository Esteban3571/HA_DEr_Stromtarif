"""UI for setup, readings and tariff changes."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .model import initial, add_reading, change_tariff, undo_reading


def numeric(unit, default=0):
    return selector.NumberSelector(selector.NumberSelectorConfig(
        min=0, max=1000000000, step=0.0001, mode=selector.NumberSelectorMode.BOX,
        unit_of_measurement=unit))


def tariff_schema(first=False):
    fields = {
        vol.Required("name"): selector.TextSelector(),
        vol.Required("date", default=dt_util.now().date().isoformat()): selector.DateSelector(),
        vol.Required("reading"): numeric("kWh"),
        vol.Required("price"): numeric("EUR/kWh"),
        vol.Required("monthly_fee"): numeric("EUR/Monat"),
    }
    if first:
        fields[vol.Required("interval", default=90)] = selector.NumberSelector(
            selector.NumberSelectorConfig(min=1, max=730, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="Tage"))
    return vol.Schema(fields)


class StromtarifConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                initial(user_input, dt_util.now().date())
            except ValueError as err:
                errors["base"] = str(err) if str(err) in ERRORS else "invalid_input"
            else:
                return self.async_create_entry(title=user_input["name"], data=user_input)
        return self.async_show_form(step_id="user", data_schema=tariff_schema(True), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return StromtarifOptionsFlow()


ERRORS = {"future_date", "date_order", "reading_decreased", "boundary_mismatch", "invalid_number", "cannot_undo"}


class StromtarifOptionsFlow(config_entries.OptionsFlow):
    @property
    def ledger(self):
        return self.hass.data[DOMAIN][self.config_entry.entry_id]

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(step_id="init", menu_options=["reading", "tariff", "interval", "undo"])

    async def commit(self, operation, step, schema, user_input):
        errors = {}
        if user_input is not None:
            try:
                await self.ledger.mutate(operation)
            except ValueError as err:
                errors["base"] = str(err) if str(err) in ERRORS else "invalid_input"
            else:
                return self.async_create_entry(title="", data={})
        return self.async_show_form(step_id=step, data_schema=schema, errors=errors)

    async def async_step_reading(self, user_input=None):
        schema = vol.Schema({vol.Required("date", default=dt_util.now().date().isoformat()): selector.DateSelector(),
                             vol.Required("reading"): numeric("kWh")})
        return await self.commit(lambda data: add_reading(data, user_input["reading"], user_input["date"], dt_util.now().date()), "reading", schema, user_input)

    async def async_step_tariff(self, user_input=None):
        return await self.commit(lambda data: change_tariff(data, user_input, dt_util.now().date()), "tariff", tariff_schema(), user_input)

    async def async_step_interval(self, user_input=None):
        schema = vol.Schema({vol.Required("interval", default=self.ledger.data["interval"]): selector.NumberSelector(
            selector.NumberSelectorConfig(min=1, max=730, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="Tage"))})
        def update(data):
            data["interval"] = int(user_input["interval"])
            data["notified_due"] = None
        return await self.commit(update, "interval", schema, user_input)

    async def async_step_undo(self, user_input=None):
        if user_input is not None and not user_input["confirm"]:
            return self.async_create_entry(title="", data={})
        return await self.commit(undo_reading, "undo", vol.Schema({vol.Required("confirm", default=False): selector.BooleanSelector()}), user_input)
