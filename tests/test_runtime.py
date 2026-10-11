"""Actual HA Core integration test; mock only host network discovery."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import shutil,tempfile,unittest
from unittest.mock import AsyncMock,Mock,patch
from types import SimpleNamespace
from homeassistant import loader
from homeassistant.bootstrap import async_from_config_dict
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import Unauthorized
from homeassistant.util import dt

class RuntimeTests(unittest.IsolatedAsyncioTestCase):
 async def test_complete_runtime(self):
  with tempfile.TemporaryDirectory() as directory:
   shutil.copytree(Path(__file__).parents[1]/'custom_components',Path(directory)/'custom_components')
   hass=HomeAssistant(directory);loader.async_setup(hass)
   try:
    with patch('homeassistant.components.http.async_get_source_ip',new=AsyncMock(return_value='127.0.0.1')):
     await async_from_config_dict({'homeassistant':{'time_zone':'Europe/Berlin'},'http':{},'websocket_api':{},'persistent_notification':{}},hass)
    today=dt.now().date();yesterday=today-timedelta(days=1)
    result=await hass.config_entries.flow.async_init('stromtarif',context={'source':'user'})
    self.assertEqual(result['type'],'form')
    data=result['data_schema']({'name':'Runtime','date':yesterday.isoformat(),'reading':1000,'price':.301234,'monthly_fee':12,'interval':1})
    result=await hass.config_entries.flow.async_configure(result['flow_id'],user_input=data)
    self.assertEqual(result['type'],'create_entry');entry=result['result']
    await hass.async_block_till_done();self.assertEqual(entry.state.value,'loaded')
    ledger=hass.data['stromtarif'][entry.entry_id]
    self.assertEqual(hass.states.get('sensor.runtime_zahlerstand').state,'1000.0')
    self.assertEqual(hass.states.get('binary_sensor.runtime_ablesung_fallig').state,'on')
    self.assertIsNotNone(ledger.data['notified_due'])
    for step in ['reading','tariff','interval','undo','finances','payment','undo_payment','source','reminders','status','close','planned_payment']:
     menu=await hass.config_entries.options.async_init(entry.entry_id)
     form=await hass.config_entries.options.async_configure(menu['flow_id'],user_input={'next_step_id':step})
     self.assertEqual(form['type'],'form',step);self.assertEqual(form['step_id'],step)
     hass.config_entries.options.async_abort(form['flow_id'])
    async def submit(step,fields):
     menu=await hass.config_entries.options.async_init(entry.entry_id)
     form=await hass.config_entries.options.async_configure(menu['flow_id'],user_input={'next_step_id':step})
     return await hass.config_entries.options.async_configure(form['flow_id'],user_input=form['data_schema'](fields))
    end=today.replace(year=today.year+1)
    self.assertEqual((await submit('finances',{'billing_start':yesterday.isoformat(),'billing_end':end.isoformat(),'monthly_installment':90,'payment_day':1}))['type'],'create_entry')
    self.assertEqual((await submit('payment',{'date':today.isoformat(),'amount':90}))['type'],'create_entry')
    await hass.async_block_till_done();self.assertEqual(hass.states.get('sensor.runtime_bezahlte_abschlage').state,'90.0')
    attrs={'device_class':'energy','state_class':'total_increasing','unit_of_measurement':'kWh'}
    hass.states.async_set('sensor.test_meter','100',attrs)
    self.assertEqual((await submit('source',{'enabled':True,'entity_id':'sensor.test_meter'}))['type'],'create_entry')
    hass.states.async_set('sensor.test_meter','110',attrs);await hass.async_block_till_done()
    self.assertEqual(ledger.data['readings'][-1]['value'],'1010.0')
    self.assertEqual(hass.states.get('sensor.runtime_zahlerstand').state,'1010.0')
    hass.states.async_set('sensor.test_meter','unavailable',attrs);await hass.async_block_till_done()
    self.assertEqual(hass.states.get('binary_sensor.runtime_zahlersensor_gestort').state,'on')
    self.assertEqual(ledger.data['readings'][-1]['value'],'1010.0')
    hass.states.async_set('sensor.test_meter','0',attrs);await hass.async_block_till_done()
    self.assertEqual(ledger.source_error,'source_reset')
    hass.states.async_set('sensor.test_meter','120',attrs);await hass.async_block_till_done()
    self.assertEqual(ledger.source_error,'source_reset');self.assertEqual(ledger.data['readings'][-1]['value'],'1010.0')
    self.assertEqual((await submit('source',{'enabled':False}))['type'],'create_entry')
    from custom_components.stromtarif.frontend import ws_history,ws_export
    conn=SimpleNamespace(user=SimpleNamespace(is_admin=True),send_result=Mock(),send_error=Mock())
    ws_history(hass,conn,{'id':1,'entry_id':entry.entry_id});history=conn.send_result.call_args.args[1]
    self.assertEqual(len(history['ledger']['payments']),1);self.assertEqual(history['intervals'][0]['consumption'],10)
    ws_export(hass,conn,{'id':2,'entry_id':entry.entry_id});self.assertIn('Zahlung;',conn.send_result.call_args.args[1]['csv'])
    denied=SimpleNamespace(user=SimpleNamespace(is_admin=False),send_result=Mock(),send_error=Mock())
    with self.assertRaises(Unauthorized):ws_export(hass,denied,{'id':3,'entry_id':entry.entry_id})
    denied.send_result.assert_not_called()
    # Exercise real HA Local Calendar and Local To-do entities, not service mocks.
    for domain,key,name in [('local_calendar','calendar_name','Tarife'),('local_calendar','calendar_name','Andere Tarife'),('local_todo','todo_list_name','Ablesungen'),('local_todo','todo_list_name','Andere Aufgaben')]:
     flow=await hass.config_entries.flow.async_init(domain,context={'source':'user'})
     result=await hass.config_entries.flow.async_configure(flow['flow_id'],user_input={key:name})
     self.assertEqual(result['type'],'create_entry');await hass.async_block_till_done()
     self.assertEqual(result['result'].state.value,'loaded')
    cal=hass.data['calendar'].get_entity('calendar.tarife')
    other=hass.data['calendar'].get_entity('calendar.andere_tarife')
    todo=hass.data['todo'].get_entity('todo.ablesungen')
    other_todo=hass.data['todo'].get_entity('todo.andere_aufgaben')
    start=dt.start_of_local_day(dt.now());stop=start+timedelta(days=800)
    # Foreign events must survive all cleanup.
    await cal.async_create_event(dtstart=today+timedelta(days=3),dtend=today+timedelta(days=4),summary='Privater Termin',description='Unverändert lassen')
    from homeassistant.components.todo import TodoItem
    from homeassistant.components.todo.const import TodoItemStatus
    await todo.async_create_todo_item(TodoItem(summary='Privat',status=TodoItemStatus.NEEDS_ACTION))
    self.assertEqual((await submit('reminders',{'calendar':'calendar.tarife','todo':'todo.ablesungen','readings':True,'payments':True}))['type'],'create_entry')
    self.assertIsNone(ledger.reminders.error)
    events=await cal.async_get_events(hass,start,stop)
    own=[event for event in events if (event.description or '').startswith('[DEr Stromtarif:')]
    self.assertGreater(len(own),1);self.assertTrue(all(event.all_day and event.end-event.start==timedelta(days=1) for event in own))
    self.assertEqual(len(todo.todo_items),2)
    count=len(events);uids={e.uid for e in events}
    await ledger.tick();await ledger.tick()
    self.assertEqual({e.uid for e in await cal.async_get_events(hass,start,stop)},uids)
    # Reload while reminders are active: preserve event IDs and task count.
    self.assertTrue(await hass.config_entries.async_reload(entry.entry_id));await hass.async_block_till_done()
    ledger=hass.data['stromtarif'][entry.entry_id]
    self.assertEqual({e.uid for e in await cal.async_get_events(hass,start,stop)},uids)
    self.assertEqual(len(todo.todo_items),2)
    # Completing an owned task must not recreate it hourly.
    task=next(item for item in todo.todo_items if item.summary!='Privat')
    task.status=TodoItemStatus.COMPLETED;await todo.async_update_todo_item(task)
    await ledger.tick();self.assertEqual(len(todo.todo_items),2)
    self.assertEqual(next(item for item in todo.todo_items if item.uid==task.uid).status,TodoItemStatus.COMPLETED)
    # Change the payment date independently of the next reading.
    original=next(row for row in ledger.reminders.desired().values() if row['summary'].startswith('Abschlag:'))['date'].isoformat()
    moved=(dt.parse_date(original)+timedelta(days=2)).isoformat()
    self.assertEqual((await submit('planned_payment',{'key':original,'date':moved,'amount':83,'remove':False}))['type'],'create_entry')
    events=await cal.async_get_events(hass,start,stop)
    self.assertTrue(any(e.start.isoformat()==moved and '83.00 EUR' in e.summary for e in events))
    self.assertFalse(any(e.start.isoformat()==original and e.summary.startswith('Abschlag:') for e in events))
    self.assertEqual((await submit('interval',{'interval':5}))['type'],'create_entry')
    self.assertTrue(any(e.start.isoformat()==moved and '83.00 EUR' in e.summary for e in await cal.async_get_events(hass,start,stop)))
    self.assertEqual((await submit('reminders',{'calendar':'calendar.andere_tarife','todo':'todo.andere_aufgaben','readings':True,'payments':True}))['type'],'create_entry')
    self.assertEqual([e.summary for e in await cal.async_get_events(hass,start,stop)],['Privater Termin'])
    self.assertEqual([item.summary for item in todo.todo_items],['Privat'])
    self.assertGreater(len(await other.async_get_events(hass,start,stop)),1);self.assertEqual(len(other_todo.todo_items),1)
    # Inactive tariff stops every future reminder and automatic source sampling.
    self.assertEqual((await submit('status',{'confirm':True}))['type'],'create_entry')
    self.assertEqual(await other.async_get_events(hass,start,stop),[]);self.assertEqual(other_todo.todo_items,[])
    await hass.async_block_till_done();self.assertEqual(hass.states.get('binary_sensor.runtime_ablesung_fallig').state,'off')
    self.assertEqual(hass.states.get('sensor.runtime_tarifstatus').state,'inaktiv')
    self.assertEqual(hass.states.get('sensor.runtime_nachste_ablesung').state,'unknown')
    self.assertEqual((await submit('tariff',{'name':'Neuer Tarif','date':today.isoformat(),'reading':1010,'price':.32,'monthly_fee':10,'final_bill':True,'bill_start':yesterday.isoformat(),'invoice_total':12,'invoice_balance':5,'balance_kind':'refund'}))['type'],'create_entry')
    self.assertFalse(ledger.data['tariffs'][0]['active']);self.assertTrue(ledger.data['tariffs'][-1]['active'])
    self.assertEqual(float(ledger.data['bills'][0]['balance']),-5);self.assertEqual(len(ledger.data['payments']),1)
    self.assertEqual(len(other_todo.todo_items),1)
    # Failed external target leaves ledger and notifications working.
    other._attr_available=False
    await ledger.tick(sample=False);self.assertIsNotNone(ledger.reminders.error)
    other._attr_available=True
    await ledger.tick(sample=False);self.assertIsNone(ledger.reminders.error)
    self.assertEqual((await submit('reminders',{'readings':True,'payments':True}))['type'],'create_entry')
    self.assertEqual(await other.async_get_events(hass,start,stop),[]);self.assertEqual(other_todo.todo_items,[])
    # Optional targets also work directly in the initial config flow.
    flow=await hass.config_entries.flow.async_init('stromtarif',context={'source':'user'})
    created=await hass.config_entries.flow.async_configure(flow['flow_id'],user_input=flow['data_schema']({'name':'Setup','date':yesterday.isoformat(),'reading':50,'price':.3,'monthly_fee':10,'interval':30,'calendar':'calendar.tarife','todo':'todo.ablesungen'}))
    self.assertEqual(created['type'],'create_entry');await hass.async_block_till_done()
    setup=hass.data['stromtarif'][created['result'].entry_id]
    self.assertIsNone(setup.reminders.error);self.assertEqual(setup.data['reminders']['calendar'],'calendar.tarife')
    self.assertEqual(len(todo.todo_items),2)
    saved=deepcopy(ledger.data)
    self.assertTrue(await hass.config_entries.async_reload(entry.entry_id));await hass.async_block_till_done()
    self.assertEqual(hass.data['stromtarif'][entry.entry_id].data,saved)
   finally:await hass.async_stop()
