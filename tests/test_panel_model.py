import unittest
from datetime import date
from test_model import m,data,TODAY

class PanelModelTests(unittest.TestCase):
 def ledger(self):
  l=m.migrate(m.initial(data(),TODAY));m.add_reading(l,1200,'2026-02-01',TODAY);m.add_reading(l,1600,'2026-04-01',TODAY);return l
 def test_each_reading_edit_recalculates(self):
  l=self.ledger();m.edit_reading(l,1,'2026-02-10',1300,TODAY)
  self.assertEqual(l['readings'][1]['value'],'1300');self.assertEqual(m.totals(l)['total_cost'],216)
  m.edit_reading(l,0,'2026-01-01',900,TODAY)
  self.assertEqual(l['tariffs'][0]['reading'],'900');self.assertEqual(m.totals(l)['consumption'],700)
 def test_invalid_neighbour_and_date(self):
  for when,value in [('2026-01-01',1300),('2026-03-01',1700),('2026-03-01',900)]:
   with self.assertRaises(ValueError):m.edit_reading(self.ledger(),1,when,value,TODAY)
 def test_tariff_boundary_value_and_date(self):
  l=self.ledger();m.change_tariff(l,data(name='B',date='2026-04-01',reading=1600),TODAY)
  m.edit_reading(l,2,'2026-04-02',1700,TODAY)
  self.assertEqual(l['tariffs'][1]['start'],'2026-04-02');self.assertEqual(l['tariffs'][1]['reading'],'1700')
  self.assertEqual(l['tariffs'][0]['end'],'2026-04-02');self.assertEqual(l['tariffs'][0]['end_reading'],'1700')
 def test_invoice_boundary_guard(self):
  l=self.ledger();m.close_tariff(l,{'date':'2026-04-01','reading':1600,'final_bill':True,'bill_start':'2026-01-01','invoice_total':210,'invoice_balance':10},TODAY)
  with self.assertRaisesRegex(ValueError,'invoice_boundary'):m.edit_reading(l,2,'2026-04-02',1600,TODAY)
  m.edit_reading(l,2,'2026-04-01',1700,TODAY);self.assertEqual(l['bills'][0]['reading'],'1700')
 def test_delete_preserves_boundaries(self):
  l=self.ledger();m.delete_reading(l,1,TODAY);self.assertEqual(len(l['readings']),2)
  with self.assertRaises(ValueError):m.delete_reading(l,0,TODAY)
 def test_price_and_zero_consumption(self):
  l=self.ledger();self.assertAlmostEqual(m.tariff_summary(l,0)['effective_price'],.36)
  l['readings'][-1]['value']='1200';l['readings'][1]['value']='1000'
  self.assertAlmostEqual(m.tariff_summary(l,0)['effective_price'],.48)
  l['readings'][-1]['value']='1000';self.assertIsNone(m.tariff_summary(l,0)['effective_price'])
 def test_periods_conserve_consumption_and_mark_estimates(self):
  l=self.ledger()
  month=m.consumption_periods(l,'month');quarter=m.consumption_periods(l,'quarter');year=m.consumption_periods(l,'year')
  self.assertEqual(len(month),3);self.assertTrue(month[1]['estimated']);self.assertFalse(month[0]['estimated'])
  for rows in [month,quarter,year]:self.assertAlmostEqual(sum(p['consumption'] for p in rows),600);self.assertAlmostEqual(sum(p['cost'] for p in rows),216)
  self.assertFalse(quarter[0]['partial']);self.assertTrue(year[0]['partial'])
 def test_tariff_filter_and_leap_year(self):
  l=m.migrate(m.initial(data(date='2024-01-01'),TODAY));m.change_tariff(l,data(name='B',date='2024-03-01',reading=1600),TODAY);m.add_reading(l,1900,'2024-04-01',TODAY)
  rows=m.consumption_periods(l,'month',0);self.assertEqual(len(rows),2);self.assertAlmostEqual(rows[1]['consumption'],290)
  self.assertEqual(m.consumption_periods(l,'quarter',1)[0]['consumption'],300)
 def test_unobserved_period_empty(self):
  l=m.migrate(m.initial(data(),TODAY));self.assertEqual(m.consumption_periods(l),[])
