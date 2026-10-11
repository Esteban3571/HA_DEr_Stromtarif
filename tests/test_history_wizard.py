"""Historical drafts: independent invoices, missing data and safe adoption."""
import importlib.util
import sys
from types import ModuleType
from pathlib import Path
from copy import deepcopy
from datetime import date
import unittest
from test_model import m, data

package=ModuleType('wizard_test');package.__path__=[];package.model=m
sys.modules['wizard_test']=package
spec=importlib.util.spec_from_file_location('wizard_test.history_wizard',Path(__file__).parents[1]/'custom_components/stromtarif/history_wizard.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
TODAY=date(2026,10,11)

class HistoryWizardTests(unittest.TestCase):
 def ledger(self):
  ledger=m.migrate(m.initial(data(meter_number='M-123'),TODAY))
  m.add_reading(ledger,1600,'2026-04-01',TODAY)
  ledger['history_draft']=w.seed(ledger)
  return ledger
 def test_tariff_without_invoice_roundtrip(self):
  ledger=self.ledger();result=w.preview(ledger,TODAY)
  self.assertTrue(result['can_apply'],result['issues'])
  self.assertEqual(result['counts']['bills'],0)
  self.assertEqual(result['summary']['total_cost'],216)
 def test_invoice_dates_independent_from_tariffs(self):
  ledger=self.ledger()
  ledger['history_draft']['bills']=[{'tariff':'Lieferantenrechnung','start':'2026-01-15','until':'2026-03-15','invoice_total':'100','balance':'-5'}]
  result=w.preview(ledger,TODAY)
  self.assertTrue(result['can_apply'],result['issues'])
  self.assertEqual(result['_candidate']['bills'][0]['end'],'2026-03-16')
  self.assertEqual(result['_candidate']['tariffs'][0]['start'],'2026-01-01')
 def test_incomplete_draft_does_not_change_history(self):
  ledger=self.ledger();before={k:deepcopy(ledger[k]) for k in w.FIELDS}
  draft=deepcopy(ledger['history_draft']);draft['readings'].append({'date':'','value':''})
  w.save(ledger,draft)
  self.assertFalse(w.preview(ledger,TODAY)['can_apply'])
  with self.assertRaisesRegex(ValueError,'history_invalid'):w.adopt(ledger,TODAY)
  self.assertEqual(before,{k:ledger[k] for k in w.FIELDS})
  self.assertEqual(ledger['history_draft'],draft)
 def test_gap_unknown_cost_and_optional_estimates(self):
  ledger=self.ledger();draft=ledger['history_draft']
  draft['tariffs']=[{'name':'A','start':'2026-01-01','until':'2026-01-31','price':'.3','monthly_fee':'12'}, {'name':'B','start':'2026-03-01','price':'.4','monthly_fee':'12'}]
  blocked=w.preview(ledger,TODAY)
  self.assertFalse(blocked['can_apply']);self.assertTrue(any('Nachbarn:' in i['text'] for i in blocked['issues']))
  draft['allow_estimates']=True;result=w.preview(ledger,TODAY)
  self.assertTrue(result['can_apply'],result['issues'])
  self.assertEqual(result['summary']['consumption'],600)
  self.assertIsNone(result['summary']['total_cost'])
  self.assertEqual(len([r for r in result['_candidate']['readings'] if r['estimated']]),2)
  self.assertTrue(any(t.get('unknown') for t in result['_candidate']['tariffs']))
 def test_overlap_suggests_neighbor_boundary(self):
  ledger=self.ledger();ledger['history_draft']['tariffs']=[{'name':'A','start':'2026-01-01','until':'2026-03-01','price':'.3','monthly_fee':'12'},{'name':'B','start':'2026-02-01','price':'.4','monthly_fee':'12'}]
  result=w.preview(ledger,TODAY)
  self.assertFalse(result['can_apply'])
  self.assertTrue(any('Ende einschließlich 2026-01-31' in i['text'] for i in result['issues']))
 def test_stale_draft_rejected(self):
  ledger=self.ledger();ledger['tariffs'][0]['price']='0.5'
  self.assertFalse(w.preview(ledger,TODAY)['can_apply'])
  with self.assertRaises(ValueError):w.adopt(ledger,TODAY)
 def test_adopt_and_restore_preserve_payments(self):
  ledger=self.ledger();before={k:deepcopy(ledger[k]) for k in w.FIELDS}
  ledger['history_draft']['tariffs'][0]['price']='.4';ledger['source']='sensor.meter'
  w.adopt(ledger,TODAY)
  self.assertIsNone(ledger['source']);self.assertNotIn('history_draft',ledger)
  self.assertEqual(m.totals(ledger)['energy_cost'],240)
  ledger['payments'].append({'date':'2026-04-02','amount':'90'})
  w.restore(ledger)
  self.assertEqual(before,{k:ledger[k] for k in w.FIELDS});self.assertEqual(len(ledger['payments']),1)
 def test_unknown_price_is_not_zero(self):
  ledger=self.ledger();ledger['history_draft']['tariffs'][0]['price']=''
  result=w.preview(ledger,TODAY)
  self.assertTrue(result['can_apply'],result['issues']);self.assertIsNone(result['summary']['energy_cost'])
  self.assertEqual(result['summary']['base_cost'],36)
 def test_future_reading_is_rejected(self):
  ledger=self.ledger();ledger['history_draft']['readings'][1]['date']='2027-01-01'
  self.assertFalse(w.preview(ledger,TODAY)['can_apply'])
