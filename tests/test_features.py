import unittest
from datetime import date
from decimal import Decimal
from test_model import m,data,TODAY

class FeaturesTests(unittest.TestCase):
 def ledger(self):
  return m.migrate(m.initial(data(),TODAY))
 def test_migration_preserves(self):
  l=self.ledger();self.assertEqual(l['tariffs'][0]['price'],'0.3');self.assertEqual(l['billing_end'],'2027-01-01')
  l['payments'].append({'date':'2026-01-10','amount':'90'});m.migrate(l);self.assertEqual(len(l['payments']),1)
 def test_finances_separate_planned_paid(self):
  l=self.ledger();m.add_reading(l,1600,'2026-04-01',TODAY)
  m.configure_finances(l,'2026-01-01','2027-01-01',100,1)
  m.add_payment(l,100,'2026-01-01',TODAY)
  f=m.finances(l)
  self.assertEqual(f['paid'],100);self.assertEqual(f['planned'],1200)
  self.assertEqual(f['period_cost'],216);self.assertEqual(f['balance'],116)
  self.assertAlmostEqual(f['forecast_cost'],874);self.assertAlmostEqual(f['forecast_balance'],-326)
 def test_no_forecast_before_reading(self):
  self.assertIsNone(m.finances(self.ledger())['forecast_cost'])
 def test_payment_bounds_and_validation(self):
  l=self.ledger()
  for amount in [0,-1,'NaN']:
   with self.assertRaises(ValueError):m.add_payment(l,amount,'2026-02-01',TODAY)
  with self.assertRaises(ValueError):m.add_payment(l,90,'2027-02-01',TODAY)
  m.configure_finances(l,'2026-01-01','2026-04-01',90,1)
  m.add_payment(l,90,'2026-04-01',TODAY);self.assertEqual(m.finances(l)['paid'],0)
 def test_partial_period_flag(self):
  l=self.ledger();m.add_reading(l,1600,'2026-04-01',TODAY)
  m.configure_finances(l,'2026-01-01','2026-02-01',90,1)
  self.assertTrue(m.finances(l)['partial_period_estimate'])
 def test_calibration_updates_and_reset(self):
  l=self.ledger();m.configure_source(l,'sensor.energy',Decimal(50))
  m.ingest_source(l,Decimal(60),date(2026,1,2));self.assertEqual(l['readings'][-1]['value'],'1010')
  m.ingest_source(l,Decimal(65),date(2026,1,2));self.assertEqual(len(l['readings']),2);self.assertEqual(l['readings'][-1]['value'],'1015')
  with self.assertRaisesRegex(ValueError,'source_reset'):m.ingest_source(l,Decimal(0),date(2026,1,3))
  self.assertEqual(l['readings'][-1]['value'],'1015')
 def test_source_units_and_unavailable(self):
  attrs={'device_class':'energy','state_class':'total_increasing','unit_of_measurement':'Wh'}
  self.assertEqual(m.source_value('1500',attrs),Decimal('1.5'))
  for state in ['unavailable','unknown','NaN']:
   with self.assertRaises(ValueError):m.source_value(state,attrs)
  with self.assertRaises(ValueError):m.source_value(500,{**attrs,'unit_of_measurement':'W'})
 def test_manual_fallback_does_not_overwrite(self):
  l=self.ledger();m.configure_source(l,'sensor.energy',Decimal(50))
  self.assertFalse(m.ingest_source(l,Decimal(55),date(2026,1,1)))
  m.add_reading(l,1020,'2026-01-02',TODAY)
  with self.assertRaisesRegex(ValueError,'source_behind'):m.ingest_source(l,Decimal(60),date(2026,1,3))
  m.configure_source(l,None);self.assertIsNone(l['source'])
 def test_csv_injection_escaping(self):
  l=self.ledger();l['tariffs'][0]['name']='=HYPERLINK("bad")';m.add_payment(l,90,'2026-01-01',TODAY)
  text=m.csv_export(l)
  self.assertIn("'=HYPERLINK",text);self.assertIn('Zahlung;2026-01-01',text)
 def test_independent_billing_start(self):
  l=self.ledger();m.configure_finances(l,'2026-02-01','2027-01-01',90,31)
  self.assertEqual(l['billing_start'],'2026-02-01')
 def test_leap_billing_start(self):
  l=m.migrate(m.initial(data(date='2024-02-29'),TODAY));self.assertEqual(l['billing_end'],'2025-02-28')
