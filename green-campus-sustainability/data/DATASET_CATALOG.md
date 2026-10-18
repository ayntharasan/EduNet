# Dataset Catalog — Green Campus Sustainability Auditor

This catalog documents all data sources used or referenced by this project, including licence, attribution, provenance, and intended use.

> [!IMPORTANT]
> No external dataset is presented as actual campus measurement data.
> External datasets are used only for reference benchmarking.
> Campus audit data is either user-provided or synthetic demo data.

---

## 1. Synthetic Demo Data

| Attribute | Value |
|-----------|-------|
| **Name** | Green Valley University Demo Dataset |
| **Type** | Synthetic — algorithmically generated |
| **Generator** | `scripts/generate_demo_data.py` |
| **Reproducibility seed** | 42 |
| **Files** | `data/demo/electricity_demo.csv`, `water_demo.csv`, `waste_demo.csv` |
| **Total rows** | ~1,915 |
| **Synthetic flag** | `is_synthetic=True` on every row |
| **Licence** | N/A — generated data, no external licence |
| **Purpose** | Demonstrate the audit pipeline without requiring real campus data |

> [!CAUTION]
> Synthetic data must not be cited as empirical evidence of any real institution's performance.

### Schema — electricity_demo.csv

| Column | Type | Unit | Notes |
|--------|------|------|-------|
| `timestamp` | date | YYYY-MM-DD | Daily reading |
| `building_id` | int | — | 1–5 |
| `building_name` | str | — | Demo name |
| `consumption_kwh` | float | kWh | Daily total |
| `occupancy_count` | int | persons | Approximate |
| `floor_area_m2` | float | m² | Building area |
| `source_type` | str | — | Always `"demo"` |
| `is_synthetic` | bool | — | Always `True` |

### Schema — water_demo.csv

| Column | Type | Unit | Notes |
|--------|------|------|-------|
| `measurement_date` | date | YYYY-MM-DD | Daily reading |
| `building_id` | int | — | 1–5 |
| `building_name` | str | — | Demo name |
| `consumption_litres` | float | litres | Daily total |
| `occupancy_count` | int | persons | Approximate |
| `source_type` | str | — | Always `"demo"` |
| `is_synthetic` | bool | — | Always `True` |

### Schema — waste_demo.csv

| Column | Type | Unit | Notes |
|--------|------|------|-------|
| `measurement_date` | date | YYYY-MM-DD | Monthly reading |
| `building_id` | int | — | 1–5 |
| `building_name` | str | — | Demo name |
| `wet_waste_kg` | float | kg | Organic/wet waste |
| `dry_recyclable_kg` | float | kg | Recyclable dry waste |
| `residual_waste_kg` | float | kg | Non-recyclable residual |
| `special_waste_kg` | float | kg | Hazardous / e-waste |
| `total_waste_kg` | float | kg | Sum of all categories |
| `source_type` | str | — | Always `"demo"` |
| `is_synthetic` | bool | — | Always `True` |

---

## 2. UCI Household Electric Power Consumption

| Attribute | Value |
|-----------|-------|
| **Name** | Individual household electric power consumption |
| **Source** | UCI Machine Learning Repository |
| **Dataset ID** | 235 |
| **URL** | https://archive.ics.uci.edu/dataset/235 |
| **Attribution** | Hebrail, G. & Berard, A. (2012). UCI Machine Learning Repository. https://doi.org/10.24432/C58K54 |
| **Licence** | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| **Geography** | Sceaux, France — **single residential household** |
| **Period** | December 2006 – November 2010 |
| **Granularity** | 1-minute intervals |
| **Rows** | ~2,075,259 |
| **Format** | ZIP → `.txt` (semicolon-separated) |
| **Download required** | Manual (see `docs/DATASET_DOWNLOAD_GUIDE.md`) |
| **Campus use** | **BENCHMARK ONLY** — not campus data |
| **Warning** | French household data. Not representative of Indian campus energy patterns. |

---

## 3. UCI Appliances Energy Prediction

| Attribute | Value |
|-----------|-------|
| **Name** | Appliances energy prediction |
| **Source** | UCI Machine Learning Repository |
| **Dataset ID** | 374 |
| **URL** | https://archive.ics.uci.edu/dataset/374 |
| **Attribution** | Candanedo, L. (2017). UCI Machine Learning Repository. https://doi.org/10.24432/C5VC8G |
| **Licence** | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| **Geography** | Stambruges, Belgium — residential apartment |
| **Period** | January–May 2016 |
| **Granularity** | 10-minute intervals |
| **Rows** | ~19,735 |
| **Format** | ZIP → CSV |
| **Campus use** | **BENCHMARK ONLY** — appliance-level energy patterns |
| **Warning** | Belgian residential data. Not representative of Indian campus conditions. |

---

## 4. UCI Energy Efficiency

| Attribute | Value |
|-----------|-------|
| **Name** | Energy efficiency |
| **Source** | UCI Machine Learning Repository |
| **Dataset ID** | 242 |
| **URL** | https://archive.ics.uci.edu/dataset/242 |
| **Attribution** | Tsanas, A. & Xifara, A. (2012). UCI Machine Learning Repository. https://doi.org/10.24432/C51307 |
| **Licence** | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| **Rows** | 768 (simulated building configurations) |
| **Format** | ZIP → XLSX |
| **Campus use** | **BENCHMARK ONLY** — building thermal efficiency reference |
| **Warning** | Simulated dataset for building configuration analysis, not measured data. |

---

## 5. Emission Factor

| Attribute | Value |
|-----------|-------|
| **Name** | India CEA Grid Emission Factor |
| **Value** | 0.716 kgCO2e/kWh |
| **Scope** | Scope 2 — indirect, purchased electricity |
| **Source** | CEA CO2 Baseline Database for the Indian Power Sector, Version 18 (2022-23) |
| **Publisher** | Central Electricity Authority, Ministry of Power, Government of India |
| **URL** | https://cea.nic.in/cdm-co2-baseline-database/ |
| **Coverage** | National grid average, India |
| **Update frequency** | Annual — use latest version for reporting |
| **Disclaimer** | Estimates only. Scope 2 electricity emissions only. Does not cover direct combustion, refrigerants, transport, waste, or water. Not suitable for official GHG inventory without professional verification. |

---

## 6. Import Templates

Blank CSV templates for user-provided campus data:

| Template | Path | Required columns |
|----------|------|-----------------|
| Electricity | `data/templates/electricity_template.csv` | `timestamp`, `building_id`, `consumption_kwh` |
| Water | `data/templates/water_template.csv` | `measurement_date`, `building_id`, `consumption_litres` |
| Waste | `data/templates/waste_template.csv` | `measurement_date`, `building_id`, `total_waste_kg` |

---

*Last updated: October 2026*
