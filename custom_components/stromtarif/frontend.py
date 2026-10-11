"""Authenticated history/CSV API and a locally served dashboard card."""
from pathlib import Path
from copy import deepcopy
import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import callback
from .const import DOMAIN
from .model import finances, totals, csv_export, due, intervals, active, payment_schedule, tariff_summary, consumption_periods


@websocket_api.websocket_command({vol.Required("type"):"stromtarif/list"})
@websocket_api.require_admin
@callback
def ws_list(hass, connection, msg):
    connection.send_result(msg["id"],[{"entry_id":ledger.entry.entry_id,"title":ledger.entry.title} for key,ledger in hass.data.get(DOMAIN,{}).items() if key!="frontend_ready"])


@websocket_api.websocket_command({vol.Required("type"):"stromtarif/history",vol.Required("entry_id"):str})
@websocket_api.require_admin
@callback
def ws_history(hass, connection, msg):
    ledger=hass.data.get(DOMAIN,{}).get(msg["entry_id"])
    if ledger is None or msg["entry_id"]=="frontend_ready":
        connection.send_error(msg["id"],"not_found","Tarifbuch nicht geladen")
        return
    connection.send_result(msg["id"],{"title":ledger.entry.title,"ledger":deepcopy(ledger.data),"intervals":intervals(ledger.data),"totals":totals(ledger.data),"finances":finances(ledger.data),"due":due(ledger.data).isoformat() if active(ledger.data) else None,"schedule":payment_schedule(ledger.data),"reminder_error":ledger.reminders.error,"source_error":ledger.source_error,"tariff_summaries":[tariff_summary(ledger.data,i) for i in range(len(ledger.data["tariffs"]))]})


@websocket_api.websocket_command({vol.Required("type"):"stromtarif/export",vol.Required("entry_id"):str})
@websocket_api.require_admin
@callback
def ws_export(hass, connection, msg):
    ledger=hass.data.get(DOMAIN,{}).get(msg["entry_id"])
    if ledger is None or msg["entry_id"]=="frontend_ready":
        connection.send_error(msg["id"],"not_found","Tarifbuch nicht geladen")
        return
    connection.send_result(msg["id"],{"filename":"stromtarif.csv","csv":csv_export(ledger.data)})


async def async_setup_frontend(hass):
    data=hass.data.setdefault(DOMAIN,{})
    if data.get("frontend_ready"):
        return
    await hass.http.async_register_static_paths([StaticPathConfig("/stromtarif-card.js",str(Path(__file__).parent/"www"/"stromtarif-card.js"),False),
        StaticPathConfig("/stromtarif-panel.js", str(Path(__file__).parent/"www"/"stromtarif-panel.js"),False)])
    for command in (ws_list,ws_history,ws_export,ws_update,ws_periods):
        websocket_api.async_register_command(hass,command)
    data["frontend_ready"]=True


@websocket_api.websocket_command({vol.Required("type"): "stromtarif/update", vol.Required("entry_id"): str,
    vol.Required("revision"): vol.All(int, vol.Range(min=0)), vol.Required("operation"): str, vol.Required("values"): dict})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_update(hass, connection, msg):
    from homeassistant.util import dt as dt_util
    from .panel_api import apply, ERRORS
    ledger=hass.data.get(DOMAIN,{}).get(msg["entry_id"])
    if not hasattr(ledger,"mutate"):
        connection.send_error(msg["id"],"not_found","Tarifbuch nicht geladen")
        return
    try:
        await ledger.mutate(lambda data: apply(hass,data,msg["operation"],msg["values"],dt_util.now().date()), expected_revision=msg["revision"])
    except (ValueError,KeyError,TypeError,IndexError,OverflowError) as err:
        code=str(err) if str(err) in ERRORS else "invalid_input"
        connection.send_error(msg["id"],code,ERRORS[code])
        return
    if msg["operation"]=="source":
        ledger.bind_source()
    if msg["operation"]=="panel":
        await async_update_panel(hass)
    connection.send_result(msg["id"],{"revision":ledger.data["revision"]})


@websocket_api.websocket_command({vol.Required("type"): "stromtarif/periods", vol.Required("entry_id"): str,
    vol.Required("unit"): vol.In(["month","quarter","year"]), vol.Optional("tariff_index"): vol.All(int,vol.Range(min=0))})
@websocket_api.require_admin
@callback
def ws_periods(hass, connection, msg):
    ledger=hass.data.get(DOMAIN,{}).get(msg["entry_id"])
    if not hasattr(ledger,"data"):
        connection.send_error(msg["id"],"not_found","Tarifbuch nicht geladen")
        return
    try:
        rows=consumption_periods(ledger.data,msg["unit"],msg.get("tariff_index"))
    except (ValueError,IndexError):
        connection.send_error(msg["id"],"invalid_input","Tarif oder Zeitraum ungültig")
        return
    connection.send_result(msg["id"],rows)


async def async_update_panel(hass):
    from homeassistant.components import frontend, panel_custom
    ledgers=[value for value in hass.data.get(DOMAIN,{}).values() if hasattr(value,"entry")]
    frontend.async_remove_panel(hass,"stromtarif",warn_if_unknown=False)
    if ledgers:
        await panel_custom.async_register_panel(hass,frontend_url_path="stromtarif",webcomponent_name="stromtarif-panel",
            sidebar_title="DEr Stromtarif" if any(ledger.data["show_panel"] for ledger in ledgers) else None,
            sidebar_icon="mdi:transmission-tower",module_url="/stromtarif-panel.js?v=0.4.0",require_admin=True)
