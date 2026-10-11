"""Authenticated history/CSV API and a locally served dashboard card."""
from pathlib import Path
from copy import deepcopy
import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import callback
from .const import DOMAIN
from .model import finances, totals, csv_export, due, intervals, active, payment_schedule


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
    connection.send_result(msg["id"],{"title":ledger.entry.title,"ledger":deepcopy(ledger.data),"intervals":intervals(ledger.data),"totals":totals(ledger.data),"finances":finances(ledger.data),"due":due(ledger.data).isoformat() if active(ledger.data) else None,"schedule":payment_schedule(ledger.data),"reminder_error":ledger.reminders.error,"source_error":ledger.source_error})


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
    await hass.http.async_register_static_paths([StaticPathConfig("/stromtarif-card.js",str(Path(__file__).parent/"www"/"stromtarif-card.js"),False)])
    for command in (ws_list,ws_history,ws_export):
        websocket_api.async_register_command(hass,command)
    data["frontend_ready"]=True
