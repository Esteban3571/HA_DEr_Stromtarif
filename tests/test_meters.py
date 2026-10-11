import unittest,csv,io
from copy import deepcopy
from test_model import m,data,TODAY

class MeterTests(unittest.TestCase):
 def ledger(self):return m.migrate(m.initial(dict(data(),meter_number='OLD-001'),TODAY))
 def swap(self,l,when='2026-02-01',final=1200,initial=10,number='NEW-002'):
  m.replace_meter(l,dict(date=when,old_reading=final,new_reading=initial,meter_number=number),TODAY)
 def test_reset_meter_consumption_cost_and_period(self):
  l=self.ledger();start,end=l['billing_start'],l['billing_end'];self.swap(l);m.add_reading(l,410,'2026-04-01',TODAY)
  self.assertEqual(m.totals(l)['consumption'],600);self.assertEqual(m.totals(l)['total_cost'],216)
  self.assertEqual((l['billing_start'],l['billing_end']),(start,end));self.assertEqual(len(l['tariffs']),1)
  self.assertEqual(m.finances(l)['period_consumption'],600);self.assertEqual(sum(p['consumption'] for p in m.consumption_periods(l)),600)
  self.assertEqual([r['meter_number'] for r in l['readings']],['OLD-001','OLD-001','NEW-002','NEW-002'])
 def test_multiple_replacements_and_tariff_same_day(self):
  l=self.ledger();self.swap(l);m.change_tariff(l,data(name='B',date='2026-02-01',reading=10,price='.4'),TODAY)
  self.swap(l,'2026-03-01',110,0,'NEW-003');m.add_reading(l,300,'2026-04-01',TODAY);m.validate_history(l,TODAY)
  self.assertEqual(m.totals(l)['consumption'],600)
  self.assertEqual(m.tariff_summary(l,0)['consumption'],200);self.assertEqual(m.tariff_summary(l,1)['consumption'],400)
 def test_tariff_before_same_day_replacement(self):
  l=self.ledger();m.change_tariff(l,data(name='B',date='2026-02-01',reading=1200),TODAY);self.swap(l)
  m.add_reading(l,410,'2026-04-01',TODAY);m.validate_history(l,TODAY);self.assertEqual(m.totals(l)['consumption'],600)
 def test_edit_boundaries_and_prevent_delete(self):
  l=self.ledger();self.swap(l);m.add_reading(l,410,'2026-04-01',TODAY)
  m.edit_reading(l,1,'2026-02-02',1300,TODAY);self.assertEqual(l['readings'][2]['date'],'2026-02-02')
  m.edit_reading(l,2,'2026-02-02',20,TODAY);self.assertEqual(m.totals(l)['consumption'],690)
  for i in [1,2]:
   with self.assertRaisesRegex(ValueError,'cannot_undo'):m.delete_reading(l,i,TODAY)
 def test_source_disabled_rename_and_csv(self):
  l=self.ledger();m.configure_source(l,'sensor.old',m.Decimal(1000));self.swap(l);self.assertIsNone(l['source'])
  m.rename_meter(l,'meter_1','=OLD');rows=list(csv.reader(io.StringIO(m.csv_export(l)),delimiter=';'))
  self.assertEqual(rows[0][-1],'Zaehlernummer');self.assertTrue(any(row[0]=='Ablesung' and row[-1]=="'=OLD" for row in rows))
  self.assertTrue(any(row[-1]=='NEW-002' for row in rows));self.assertTrue(all(len(row)==12 for row in rows))
 def test_invalid_new_number_and_endstand(self):
  for number,final in [('OLD-001',1200),('',1200),('NEW',900)]:
   with self.assertRaises(ValueError):self.swap(self.ledger(),number=number,final=final)
 def test_legacy_migration_and_number_backfill(self):
  l=m.initial(data(),TODAY);l.pop('meters');l['readings'][0].pop('meter_id');l['readings'][0].pop('meter_number');l['tariffs'][0].pop('meter_id')
  m.migrate(l);m.rename_meter(l,'meter_1','Known');self.assertEqual(l['readings'][0]['meter_number'],'Known');self.swap(l)
 def test_source_new_meter_calibration(self):
  l=self.ledger();self.swap(l);m.configure_source(l,'sensor.new',m.Decimal(10));m.ingest_source(l,m.Decimal(110),TODAY)
  self.assertEqual(l['readings'][-1]['meter_number'],'NEW-002');self.assertEqual(m.totals(l)['consumption'],300)
