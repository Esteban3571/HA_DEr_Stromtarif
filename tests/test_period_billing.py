import unittest
from datetime import date
from test_model import m, data

class PeriodBillingTests(unittest.TestCase):
 def ledger(self):
  l=m.migrate(m.initial(data(date='2024-01-01'),date(2026,5,1)))
  m.configure_finances(l,'2024-01-01','2024-02-29',90,1)
  return l
 def values(self,**changes):
  return dict(start='2024-01-01',end='2024-02-29',invoice_total=180,invoice_balance=15,balance_kind='refund',advance=True,**changes)
 def test_record_active_invoice_and_advance_stable_leap_cutoff(self):
  l=self.ledger();m.add_payment(l,90,'2024-02-01',date(2026,5,1))
  m.record_period_bill(l,self.values(),date(2026,5,1))
  self.assertTrue(m.active(l));self.assertEqual(l['bills'][0]['balance'],'-15');self.assertEqual(l['bills'][0]['paid_at_recording'],'90')
  self.assertEqual(l['billing_start'],'2024-02-29');self.assertEqual(l['billing_end'],'2025-02-28')
  for start,end in [('2024-02-29','2025-02-28'),('2025-02-28','2026-02-28')]:
   v=self.values();v.update(start=start,end=end);m.record_period_bill(l,v,date(2026,5,1))
  self.assertEqual(l['billing_end'],'2027-02-28');self.assertEqual(l['billing_cutoff'],'02-29')
 def test_historical_invoice_without_rollover(self):
  l=self.ledger();v=self.values();v['advance']=False;m.record_period_bill(l,v,date(2026,5,1));self.assertEqual(l['billing_start'],'2024-01-01')
  self.assertEqual(l['payments'],[])
 def test_duplicate_overlap_and_invalid_range_rejected(self):
  l=self.ledger();v=self.values();v['advance']=False;m.record_period_bill(l,v,date(2026,5,1))
  with self.assertRaisesRegex(ValueError,'duplicate_bill'):m.record_period_bill(l,v,date(2026,5,1))
  v.update(start='2024-02-01',end='2024-04-01')
  with self.assertRaisesRegex(ValueError,'duplicate_bill'):m.record_period_bill(l,v,date(2026,5,1))
 def test_future_and_wrong_current_period_rejected(self):
  l=self.ledger()
  with self.assertRaisesRegex(ValueError,'future_date'):m.record_period_bill(l,self.values(),date(2024,2,1))
  v=self.values();v['end']='2024-02-28'
  with self.assertRaisesRegex(ValueError,'billing_dates'):m.record_period_bill(l,v,date(2026,5,1))
 def test_new_schedule_and_payment_history(self):
  l=self.ledger();m.settle_payment(l,'2024-02-01',date(2026,5,1));m.record_period_bill(l,self.values(),date(2026,5,1))
  self.assertEqual(len(l['payments']),1);self.assertEqual(m.finances(l)['paid'],0)
  self.assertEqual(m.payment_schedule(l)[0]['date'],'2024-03-01')
