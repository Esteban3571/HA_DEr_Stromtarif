import unittest
from datetime import date
from test_model import m, data, TODAY

class InstallmentChangeTests(unittest.TestCase):
 def ledger(self):
  l=m.migrate(m.initial(data(),TODAY));m.configure_finances(l,'2026-01-01','2027-01-01',90,1);return l
 def test_flexible_cutoff_and_multiple_changes(self):
  l=self.ledger();m.change_installment(l,'2026-03-15',105);m.change_installment(l,'2026-07-01',115)
  rows=m.payment_schedule(l);self.assertEqual([r['amount'] for r in rows[:4]],['90','90','90','105']);self.assertEqual(rows[6]['amount'],'115')
  self.assertEqual(m.planned_payments(l),3*90+3*105+6*115)
 def test_paid_and_individual_exception_preserved(self):
  l=self.ledger();m.settle_payment(l,'2026-02-01',TODAY);m.edit_planned_payment(l,'2026-05-01','2026-05-17',83,auto_pay=True)
  m.change_installment(l,'2026-02-01',120)
  self.assertEqual(l['payments'][0]['amount'],'90');row=next(r for r in m.payment_schedule(l) if r['key']=='2026-05-01')
  self.assertEqual(row['amount'],'83');self.assertTrue(row['auto_pay'])
 def test_next_billing_period_uses_new_amount(self):
  l=self.ledger();m.change_installment(l,'2027-01-01',110)
  self.assertEqual(m.payment_schedule(l)[-1]['amount'],'90')
  m.record_period_bill(l,dict(start='2026-01-01',end='2027-01-01',invoice_total=1080,invoice_balance=0,balance_kind='payment',advance=True),date(2027,1,1))
  self.assertEqual(m.payment_schedule(l)[0]['amount'],'110')
 def test_edit_same_date_replaces_and_zero_pauses(self):
  l=self.ledger();m.change_installment(l,'2026-03-01',100);m.change_installment(l,'2026-03-01',0)
  self.assertEqual(len(l['installment_changes']),1);self.assertEqual(len(m.payment_schedule(l)),2)
  m.change_installment(l,'2026-06-01',110);self.assertEqual(len(m.payment_schedule(l)),9)
 def test_finance_form_effective_date_preserves_baseline(self):
  l=self.ledger();m.configure_finances(l,'2026-01-01','2027-01-01',120,1,'2026-04-01')
  self.assertEqual(l['monthly_installment'],'90');self.assertEqual(m.payment_schedule(l)[2]['amount'],'90');self.assertEqual(m.payment_schedule(l)[3]['amount'],'120')
 def test_invalid_dates_and_amounts(self):
  l=self.ledger()
  for when,amount in [('2025-12-31',100),('invalid',100),('2026-03-01',-1),('2026-03-01','nan')]:
   with self.assertRaises(ValueError):m.change_installment(l,when,amount)
