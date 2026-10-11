import unittest
from datetime import date
from test_model import m, data, TODAY

class SettlementTests(unittest.TestCase):
 def ledger(self):
  l=m.migrate(m.initial(data(),TODAY));m.configure_finances(l,'2026-01-01','2027-01-01',90,1);return l
 def test_click_links_and_does_not_duplicate(self):
  l=self.ledger();m.settle_payment(l,'2026-02-01',TODAY);m.settle_payment(l,'2026-02-01',TODAY)
  self.assertEqual(len(l['payments']),1);self.assertTrue(m.payment_schedule(l)[1]['paid']);self.assertEqual(m.finances(l)['paid'],90)
 def test_future_click_uses_today(self):
  l=self.ledger();m.settle_payment(l,'2026-12-01',TODAY)
  self.assertEqual(l['payments'][0]['date'],TODAY.isoformat())
 def test_automatic_optional_due_and_restart_idempotent(self):
  l=self.ledger();m.edit_planned_payment(l,'2026-02-01','2026-02-17',83,auto_pay=True)
  m.auto_settle_payments(l,date(2026,2,16));self.assertEqual(l['payments'],[])
  m.auto_settle_payments(l,date(2026,2,17));m.migrate(l);m.auto_settle_payments(l,TODAY)
  self.assertEqual(len(l['payments']),1);self.assertEqual(l['payments'][0]['amount'],'83');self.assertTrue(l['payments'][0]['automatic'])
 def test_edit_preserves_link_and_delete_disables_automatic(self):
  l=self.ledger();m.edit_planned_payment(l,'2026-02-01','2026-02-17',83,auto_pay=True);m.auto_settle_payments(l,TODAY)
  l['payments'][0].update(date='2026-02-18',amount='85');m.auto_settle_payments(l,TODAY);self.assertEqual(len(l['payments']),1)
  m.delete_payment(l,0);m.auto_settle_payments(l,TODAY);self.assertEqual(l['payments'],[]);self.assertFalse(m.payment_schedule(l)[1]['auto_pay'])
  m.settle_payment(l,'2026-02-01',TODAY);self.assertEqual(len(l['payments']),1)
 def test_inactive_and_removed_not_automatically_paid(self):
  l=self.ledger();m.edit_planned_payment(l,'2026-02-01','2026-02-17',83,auto_pay=True);l['tariffs'][-1]['active']=False
  m.auto_settle_payments(l,TODAY);self.assertEqual(l['payments'],[])
  l['tariffs'][-1]['active']=True;m.edit_planned_payment(l,'2026-02-01','2026-02-17',83,remove=True);m.auto_settle_payments(l,TODAY);self.assertEqual(l['payments'],[])
 def test_legacy_payments_and_plan_totals_preserved(self):
  l=self.ledger();m.add_payment(l,90,'2026-01-01',TODAY);before=m.planned_payments(l);m.settle_payment(l,'2026-02-01',TODAY)
  self.assertEqual(m.planned_payments(l),before);self.assertEqual(len(l['payments']),2)
