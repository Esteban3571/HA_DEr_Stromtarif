"""UI for setup, readings and tariff changes."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .model import (initial, add_reading, change_tariff, undo_reading,
                    configure_finances, add_payment, configure_source, source_value, close_tariff, edit_planned_payment, active, installment_at)
from .reminders import validate_targets


def numeric(unit, default=0):
    return selector.NumberSelector(selector.NumberSelectorConfig(
        min=0, max=1000000000, step="any", mode=selector.NumberSelectorMode.BOX,
        unit_of_measurement=unit))


def reminder_fields(data=None):
    data = data or {}
    fields = {}
    for domain, enum, features in (("calendar", "CalendarEntityFeature", ("CREATE_EVENT", "DELETE_EVENT")), ("todo", "TodoListEntityFeature", ("CREATE_TODO_ITEM", "DELETE_TODO_ITEM"))):
        fields[vol.Optional(domain, description={"suggested_value": data.get(domain)})] = selector.EntitySelector(
            selector.EntitySelectorConfig(filter={"domain": domain, "supported_features": [[f"{domain}.{enum}.{feature}" for feature in features]]}))
    return fields



def bill_fields():
    return {vol.Required("final_bill", default=False): selector.BooleanSelector(),
        vol.Optional("bill_start"): selector.DateSelector(),
        vol.Optional("invoice_total"): numeric("EUR"),
        vol.Optional("invoice_balance"): numeric("EUR"),
        vol.Required("balance_kind", default="payment"): selector.SelectSelector(selector.SelectSelectorConfig(options=[{"value":"payment", "label":"Nachzahlung"}, {"value":"refund", "label":"Guthaben"}]))}


def validate_bill(values):
    if values.get("final_bill") and any(values.get(key) is None for key in ("bill_start", "invoice_total", "invoice_balance")):
        raise ValueError("bill_required")


def tariff_schema(first=False, reminders=None):
    fields = {
        vol.Required("name"): selector.TextSelector(),
        vol.Required("date", default=dt_util.now().date().isoformat()): selector.DateSelector(),
        vol.Required("reading"): numeric("kWh"),
        vol.Required("price"): numeric("EUR/kWh"),
        vol.Required("monthly_fee"): numeric("EUR/Monat"),
    }
    if first:
        fields[vol.Required("meter_number")] = selector.TextSelector()
        fields[vol.Required("interval", default=90)] = selector.NumberSelector(
            selector.NumberSelectorConfig(min=1, max=730, step=1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="Tage"))
    fields.update(reminder_fields(reminders))
    if not first:
        fields.update(bill_fields())
    return vol.Schema(fields)


class StromtarifConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                validate_targets(self.hass, user_input)
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


ERRORS = {"future_date", "date_order", "reading_decreased", "boundary_mismatch", "invalid_number", "cannot_undo", "billing_dates", "invalid_source", "source_reset", "source_behind", "invalid_reminder_target", "bill_required", "duplicate_payment_date"}


class StromtarifOptionsFlow(config_entries.OptionsFlow):
    @property
    def ledger(self):
        return self.hass.data[DOMAIN][self.config_entry.entry_id]

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(step_id="init", menu_options=["reading", "tariff", "interval", "undo", "finances", "payment", "undo_payment", "source", "reminders", "status", "close", "planned_payment", "panel"])

    async def commit(self, operation, step, schema, user_input):
        errors = {}
        if user_input is not None:
            try:
                validate_bill(user_input)
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
        def update(data):
            validate_targets(self.hass, user_input)
            change_tariff(data, user_input, dt_util.now().date())
        return await self.commit(update, "tariff", tariff_schema(reminders=self.ledger.data["reminders"]), user_input)

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


    async def async_step_finances(self, user_input=None):
        data=self.ledger.data
        schema=vol.Schema({
            vol.Required("billing_start",default=data["billing_start"]):selector.DateSelector(),
            vol.Required("billing_end",default=data["billing_end"]):selector.DateSelector(),
            vol.Required("monthly_installment",default=float(installment_at(data,dt_util.now().date().isoformat()))):numeric("EUR/Monat"),
            vol.Optional("installment_from",default=dt_util.now().date().isoformat()):selector.DateSelector(),
            vol.Required("payment_day",default=data["payment_day"]):selector.NumberSelector(selector.NumberSelectorConfig(min=0,max=31,step=1,mode=selector.NumberSelectorMode.BOX)),
            vol.Required("schedule_mode", default=data["schedule_mode"]): selector.SelectSelector(selector.SelectSelectorConfig(options=[{"value":"monthly", "label":"Monatlich"}, {"value":"custom", "label":"Nur einzelne Termine"}]))})
        def update(data):
            configure_finances(data,user_input["billing_start"],user_input["billing_end"],user_input["monthly_installment"],user_input["payment_day"],user_input.get("installment_from"))
            data["schedule_mode"] = user_input.get("schedule_mode", "monthly")
        return await self.commit(update,"finances",schema,user_input)

    async def async_step_payment(self,user_input=None):
        schema=vol.Schema({vol.Required("date",default=dt_util.now().date().isoformat()):selector.DateSelector(),vol.Required("amount"):numeric("EUR")})
        return await self.commit(lambda data:add_payment(data,user_input["amount"],user_input["date"],dt_util.now().date()),"payment",schema,user_input)

    async def async_step_undo_payment(self,user_input=None):
        if user_input is not None and not user_input["confirm"]:
            return self.async_create_entry(title="",data={})
        def undo(data):
            if not data["payments"]:
                raise ValueError("cannot_undo")
            from .model import delete_payment
            delete_payment(data,-1)
        return await self.commit(undo,"undo_payment",vol.Schema({vol.Required("confirm",default=False):selector.BooleanSelector()}),user_input)

    async def async_step_source(self,user_input=None):
        schema=vol.Schema({vol.Required("enabled",default=bool(self.ledger.data["source"])):selector.BooleanSelector(),
            vol.Optional("entity_id"):selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor",device_class="energy"))})
        errors={}
        if user_input is not None:
            raw=None
            if user_input["enabled"]:
                state=self.hass.states.get(user_input.get("entity_id",""))
                try:
                    if state is None:
                        raise ValueError("invalid_source")
                    raw=source_value(state.state,state.attributes)
                except ValueError:
                    errors["base"]="invalid_source"
            if not errors:
                await self.ledger.mutate(lambda data:configure_source(data,user_input.get("entity_id") if user_input["enabled"] else None,raw))
                self.ledger.bind_source()
                return self.async_create_entry(title="",data={})
        return self.async_show_form(step_id="source",data_schema=schema,errors=errors)


    async def async_step_reminders(self, user_input=None):
        data = self.ledger.data["reminders"]
        fields = reminder_fields(data)
        fields.update({vol.Required("readings", default=data["readings"]): selector.BooleanSelector(),
            vol.Required("payments", default=data["payments"]): selector.BooleanSelector()})
        def update(ledger):
            validate_targets(self.hass, user_input)
            ledger["reminders"] = {key: user_input.get(key) or None for key in ("calendar", "todo")}
            ledger["reminders"].update(readings=user_input["readings"], payments=user_input["payments"])
        return await self.commit(update, "reminders", vol.Schema(fields), user_input)

    async def async_step_status(self, user_input=None):
        def update(data):
            if user_input["confirm"]:
                data["tariffs"][-1].update(active=False)
                data["tariffs"][-1].setdefault("end", data["readings"][-1]["date"])
                data["tariffs"][-1].setdefault("end_reading", data["readings"][-1]["value"])
                data["notified_due"] = None
        return await self.commit(update, "status", vol.Schema({vol.Required("confirm", default=False): selector.BooleanSelector()}), user_input)

    async def async_step_close(self, user_input=None):
        fields = {vol.Required("date", default=dt_util.now().date().isoformat()): selector.DateSelector(),
            vol.Required("reading", default=float(self.ledger.data["readings"][-1]["value"])): numeric("kWh")}
        fields.update(bill_fields())
        return await self.commit(lambda data: close_tariff(data, user_input, dt_util.now().date()), "close", vol.Schema(fields), user_input)

    async def async_step_planned_payment(self, user_input=None):
        fields = {vol.Required("key", default=dt_util.now().date().isoformat()): selector.DateSelector(),
            vol.Required("date", default=dt_util.now().date().isoformat()): selector.DateSelector(),
            vol.Required("amount", default=float(self.ledger.data["monthly_installment"])): numeric("EUR"),
            vol.Required("remove", default=False): selector.BooleanSelector()}
        return await self.commit(lambda data: edit_planned_payment(data, user_input["key"], user_input["date"], user_input["amount"], user_input["remove"]), "planned_payment", vol.Schema(fields), user_input)


    async def async_step_panel(self, user_input=None):
        result = await self.commit(lambda data: data.update(show_panel=user_input["show_panel"]), "panel",
            vol.Schema({vol.Required("show_panel",default=self.ledger.data["show_panel"]): selector.BooleanSelector()}),user_input)
        if result["type"] == "create_entry":
            from .frontend import async_update_panel
            await async_update_panel(self.hass)
        return result
