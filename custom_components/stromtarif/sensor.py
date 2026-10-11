from datetime import datetime, time
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.util import dt as dt_util
from .const import DOMAIN
from .entity import LedgerEntity
from .model import totals, due, fee, finances

SENSORS = [
    ("tariff_name", "Aktueller Tarif", None),
    ("period_cost", "Kosten Abrechnungsperiode", "EUR"),
    ("paid", "Bezahlte Abschläge", "EUR"),
    ("planned", "Geplante Abschläge", "EUR"),
    ("balance", "Saldo erfasste Kosten minus Zahlungen", "EUR"),
    ("forecast_cost", "Kostenprognose Abrechnungsperiode", "EUR"),
    ("forecast_balance", "Prognose Nachzahlung oder Guthaben", "EUR"),
    ("reading", "Zählerstand", "kWh"),
    ("consumption", "Verbrauch erfasst", "kWh"),
    ("energy_cost", "Arbeitspreiskosten erfasst", "EUR"),
    ("base_cost", "Grundgebühr erfasst", "EUR"),
    ("total_cost", "Gesamtkosten erfasst", "EUR"),
    ("price", "Arbeitspreis", "EUR/kWh"),
    ("monthly_fee", "Monatliche Grundgebühr", "EUR"),
    ("pending_fee", "Grundgebühr seit letzter Ablesung", "EUR"),
    ("last_reading", "Letzte Ablesung", None),
    ("next_reading", "Nächste Ablesung", None),
]

async def async_setup_entry(hass, entry, async_add_entities):
    ledger = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([LedgerSensor(ledger, *definition) for definition in SENSORS])


class LedgerSensor(LedgerEntity, SensorEntity):
    def __init__(self, ledger, key, name, unit):
        super().__init__(ledger, key, name)
        self.key = key
        self._attr_native_unit_of_measurement = unit
        if key in {"last_reading", "next_reading"}:
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        elif unit == "kWh":
            self._attr_device_class = SensorDeviceClass.ENERGY
        elif unit == "EUR":
            self._attr_device_class = SensorDeviceClass.MONETARY
        # Deliberately no statistic state_class: manual dated entries must not
        # appear as consumption at the moment they are entered in Energy.

    @property
    def native_value(self):
        data = self.ledger.data
        if self.key == "tariff_name":
            return data["tariffs"][-1]["name"]
        if self.key in {"period_cost", "paid", "planned", "balance", "forecast_cost", "forecast_balance"}:
            value=finances(data)[self.key]
            return None if value is None else round(value,2)
        if self.key == "reading":
            return float(data["readings"][-1]["value"])
        if self.key in {"price", "monthly_fee"}:
            return float(data["tariffs"][-1][self.key])
        if self.key in {"last_reading", "next_reading"}:
            when = datetime.fromisoformat(data["readings"][-1]["date"]).date() if self.key == "last_reading" else due(data)
            return datetime.combine(when, time(), tzinfo=dt_util.DEFAULT_TIME_ZONE)
        if self.key == "pending_fee":
            return round(float(fee(data["tariffs"][-1]["monthly_fee"],
                                   datetime.fromisoformat(data["readings"][-1]["date"]).date(), dt_util.now().date())), 2)
        return round(totals(data)[self.key], 4 if self.key == "consumption" else 2)

    @property
    def extra_state_attributes(self):
        data = self.ledger.data
        if self.key in {"forecast_cost", "forecast_balance", "period_cost", "balance"}:
            return {**finances(data), "prognose": self.key.startswith("forecast"), "positiver_saldo": "Nachzahlung", "negativer_saldo": "Guthaben"}
        if self.key == "total_cost":
            return {"abgerechnet_bis": data["readings"][-1]["date"],
                    "tarife": data["tariffs"], "ablesungen": data["readings"],
                    "berechnung": "Grundgebühr kalendergenau; Enddatum exklusiv"}
        return None
