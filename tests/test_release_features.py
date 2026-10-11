"""Regression cases for independent schedules and tariff closure."""
import unittest
from datetime import date
from decimal import Decimal
from test_model import m, data, TODAY

class ReleaseFeaturesTests(unittest.TestCase):
 def ledger(self):
  return m.migrate(m.initial(data(),TODAY))
 def test_day31_and_month_end(self):
  l=self.ledger();m.configure_finances(l,'2026-01-15','2026-05-01',90,31)
  self.assertEqual([p['date'] for p in m.payment_schedule(l)],['2026-01-31','2026-02-28','2026-03-31','2026-04-30'])
  m.configure_finances(l,'2026-01-15','2026-05-01',90,0)
  self.assertEqual(m.planned_payments(l),360)
 def test_leap_payment(self):
  l=m.migrate(m.initial(data(date='2024-01-01'),TODAY));m.configure_finances(l,'2024-01-01','2024-03-01',90,31)
  self.assertEqual(m.payment_schedule(l)[1]['date'],'2024-02-29')
 def test_persistent_move_delete_add_and_collision(self):
  l=self.ledger();m.configure_finances(l,'2026-01-01','2026-04-01',100,1)
  m.edit_planned_payment(l,'2026-02-01','2026-02-17',85)
  m.edit_planned_payment(l,'2026-03-01','2026-03-01',100,True)
  m.edit_planned_payment(l,'2026-03-20','2026-03-20',70)
  self.assertEqual(m.planned_payments(l),255)
  m.add_reading(l,1100,'2026-02-02',TODAY);l['interval']=5
  self.assertEqual(m.planned_payments(l),255)
  m.configure_finances(l,'2026-01-01','2026-04-01',200,1)
  self.assertEqual(m.planned_payments(l),355)
  with self.assertRaisesRegex(ValueError,'duplicate_payment_date'):m.edit_planned_payment(l,'2026-02-02','2026-02-17',20)
 def test_custom_dates_independent_of_reading(self):
  l=self.ledger();m.configure_finances(l,'2026-01-15','2026-07-01',100,1);l['schedule_mode']='custom'
  for when,amount in [('2026-01-27',55),('2026-05-09',102)]:m.edit_planned_payment(l,when,when,amount)
  self.assertEqual(m.planned_payments(l),157);self.assertEqual(len(l['readings']),1)
 def test_closure_bill_not_payment(self):
  l=self.ledger();m.configure_finances(l,'2026-01-01','2027-01-01',100,1);m.add_payment(l,100,'2026-01-01',TODAY)
  m.close_tariff(l,{'date':'2026-04-01','reading':1600,'final_bill':True,'bill_start':'2026-01-01','invoice_total':210,'invoice_balance':10,'balance_kind':'refund'},TODAY)
  self.assertFalse(m.active(l));self.assertEqual(l['bills'][0]['balance'],'-10');self.assertEqual(len(l['payments']),1)
  self.assertEqual(m.finances(l)['forecast_cost'],216);self.assertEqual(m.planned_payments(l),300)
  m.configure_source(l,'sensor.energy',Decimal(100));self.assertFalse(m.ingest_source(l,Decimal(200),TODAY));self.assertEqual(l['readings'][-1]['value'],'1600')
  self.assertIn('Endabrechnung;',m.csv_export(l))
 def test_change_closes_old_keeps_new_active(self):
  l=self.ledger();m.change_tariff(l,data(name='B',date='2026-04-01',reading=1600,final_bill=True,bill_start='2026-01-01',invoice_total=216,invoice_balance=116),TODAY)
  self.assertFalse(l['tariffs'][0]['active']);self.assertTrue(m.active(l));self.assertEqual(len(l['bills']),1)
  m.migrate(l);self.assertFalse(l['tariffs'][0]['active']);self.assertTrue(m.active(l))
 def test_collision_after_recurring_day_change(self):
  l=self.ledger();m.configure_finances(l,'2026-01-01','2026-03-01',100,1)
  m.edit_planned_payment(l,'2026-02-01','2026-02-17',80)
  m.configure_finances(l,'2026-01-01','2026-03-01',100,17)
  self.assertEqual([p['date'] for p in m.payment_schedule(l)],['2026-01-17','2026-02-17'])
  self.assertEqual(m.planned_payments(l),180)

 def test_inactive_gap_not_charged_to_old_tariff(self):
  l=self.ledger();m.close_tariff(l,{'date':'2026-04-01','reading':1600},TODAY)
  m.change_tariff(l,data(name='B',date='2026-06-01',reading=1800),TODAY)
  m.add_reading(l,1900,'2026-07-01',TODAY)
  self.assertEqual(l['tariffs'][0]['end'],'2026-04-01')
  self.assertEqual(m.totals(l)['total_cost'],258)
  self.assertEqual(m.totals(l)['consumption'],700)
