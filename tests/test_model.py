import importlib.util
from pathlib import Path
from datetime import date
from decimal import Decimal
import unittest

spec = importlib.util.spec_from_file_location("model", Path(__file__).parents[1] / "custom_components/stromtarif/model.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
TODAY = date(2026, 10, 11)


def data(**kwargs):
    return {"name": "Tarif A", "date": "2026-01-01", "reading": 1000,
            "price": 0.30, "monthly_fee": 12, "interval": 90, **kwargs}


class ModelTests(unittest.TestCase):
    def test_quarter(self):
        ledger = m.initial(data(), TODAY)
        m.add_reading(ledger, 1600, "2026-04-01", TODAY)
        self.assertEqual(m.totals(ledger), {"consumption":600, "energy_cost":180, "base_cost":36, "total_cost":216})
        self.assertEqual(m.due(ledger), date(2026,6,30))

    def test_tariff_boundary(self):
        ledger = m.initial(data(), TODAY)
        m.change_tariff(ledger, data(name="B", date="2026-04-01", reading=1600, price=.4, monthly_fee=15), TODAY)
        m.add_reading(ledger, 1900, "2026-05-01", TODAY)
        self.assertEqual(m.totals(ledger)["total_cost"], 351)
        self.assertEqual(ledger["tariffs"][0]["price"], "0.3")

    def test_same_day_change(self):
        ledger = m.initial(data(), TODAY)
        m.add_reading(ledger, 1600, "2026-04-01", TODAY)
        m.change_tariff(ledger, data(date="2026-04-01", reading=1600), TODAY)
        self.assertEqual(len(ledger["readings"]), 2)
        with self.assertRaisesRegex(ValueError,"cannot_undo"):
            m.undo_reading(ledger)

    def test_boundary_mismatch(self):
        ledger = m.initial(data(), TODAY)
        m.add_reading(ledger, 1600, "2026-04-01", TODAY)
        with self.assertRaisesRegex(ValueError,"boundary_mismatch"):
            m.change_tariff(ledger, data(date="2026-04-01", reading=1700), TODAY)

    def test_calendar_proration(self):
        self.assertEqual(m.fee("29",date(2024,2,1),date(2024,3,1)),Decimal(29))
        self.assertEqual(m.fee("31",date(2026,1,16),date(2026,2,1)),Decimal(16))

    def test_invalid_readings(self):
        ledger = m.initial(data(), TODAY)
        for reading, when, reason in [(900,"2026-02-01","reading_decreased"),(1100,"2026-01-01","date_order"),(1100,"2027-01-01","future_date")]:
            with self.assertRaisesRegex(ValueError,reason):
                m.add_reading(ledger,reading,when,TODAY)
        self.assertEqual(len(ledger["readings"]),1)

    def test_invalid_prices(self):
        for value in ["NaN","Infinity",-1,"nonsense"]:
            with self.assertRaises(ValueError):
                m.initial(data(price=value),TODAY)

    def test_undo(self):
        ledger = m.initial(data(), TODAY)
        m.add_reading(ledger,1200,"2026-02-01",TODAY)
        m.undo_reading(ledger)
        self.assertEqual(m.totals(ledger)["total_cost"],0)
        with self.assertRaises(ValueError):
            m.undo_reading(ledger)

    def test_tariff_date_order(self):
        ledger = m.initial(data(), TODAY)
        m.add_reading(ledger,1200,"2026-03-01",TODAY)
        with self.assertRaises(ValueError):
            m.change_tariff(ledger,data(date="2026-02-01",reading=1200),TODAY)


if __name__ == "__main__":
    unittest.main()
