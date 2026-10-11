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
    for step in ['reading','tariff','interval','undo','finances','payment','undo_payment','source']:
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
    saved=deepcopy(ledger.data)
    self.assertTrue(await hass.config_entries.async_reload(entry.entry_id));await hass.async_block_till_done()
    self.assertEqual(hass.data['stromtarif'][entry.entry_id].data,saved)
   finally:await hass.async_stop()
