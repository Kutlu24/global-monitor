"""FAOSTAT and UNCTADstat parsing, on small in-memory tables (no network)."""
import pandas as pd

from global_monitor.ingestion import fao, unctad
from global_monitor.ingestion._m49 import M49_TO_ISO3


def test_m49_maps_countries_and_leaves_regions_out():
    assert M49_TO_ISO3[840] == "USA" and M49_TO_ISO3[792] == "TUR"
    assert 0 not in M49_TO_ISO3 and 5100 not in M49_TO_ISO3


def _fao_table():
    item = fao.ITEMS["food_insecurity_pct"]
    rows = []
    for m49, area in (("'76", "Brazil"), ("'840", "United States of America")):
        for element, value in (("Value", 9.6), ("Confidence interval: Lower bound", 9.4),
                               ("Confidence interval: Upper bound", 9.8)):
            for year in ("2022-2024", "2023-2025"):
                rows.append({"Area Code (M49)": m49, "Area": area, "Item": item, "Element": element,
                             "Year": year, "Value": value})
    return pd.DataFrame(rows)


def test_fao_takes_the_value_not_the_confidence_bounds_and_one_window(monkeypatch):
    monkeypatch.setattr(fao, "_read_table", _fao_table)
    monkeypatch.setattr(fao, "_MIN_COVERAGE", 1)
    out = fao.fetch(["BRA", "USA"])
    assert sorted((o.iso3, o.period, o.value) for o in out) == [("BRA", "2023-2025", 9.6), ("USA", "2023-2025", 9.6)]


def test_unctad_reads_inward_stock_in_dollars_not_millions(monkeypatch):
    table = pd.DataFrame([
        {"Year": 2024, "Economy": "0840", "Flow": 9, "Direction": 1, "Millions of US$ at current prices": 100.0},
        {"Year": 2024, "Economy": "0840", "Flow": 8, "Direction": 1, "Millions of US$ at current prices": 7.0},
        {"Year": 2024, "Economy": "0840", "Flow": 9, "Direction": 2, "Millions of US$ at current prices": 999.0},
        {"Year": 2024, "Economy": "0000", "Flow": 9, "Direction": 1, "Millions of US$ at current prices": 5.0},
    ])
    monkeypatch.setattr(unctad, "_read_table", lambda: table)
    monkeypatch.setattr(unctad, "_MIN_COVERAGE", 1)
    out = {o.metric_id: o for o in unctad.fetch(["USA"])}
    assert out["fdi_inward_stock_usd"].value == 100.0 * 1e6
    assert out["fdi_inward_flow_usd"].value == 7.0 * 1e6 and len(out) == 2
