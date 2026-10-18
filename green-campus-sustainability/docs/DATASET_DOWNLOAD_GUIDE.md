# Dataset Download Guide

> [!WARNING]
> **No dataset downloaded by this project represents actual campus data.**
> External public datasets are referenced only as benchmark ranges for energy intensity.
> All data ingested into the audit pipeline is either user-provided campus measurements
> or clearly labelled synthetic demo data (`is_synthetic=True`).

---

## Synthetic Demo Data (Default — No Download Required)

The project ships with a fully self-contained demo data generator:

```powershell
# Windows
$env:PYTHONPATH="c:\Users\Dell\Downloads\EduNet\green-campus-sustainability"
python scripts/generate_demo_data.py
```

```bash
# Linux/macOS
PYTHONPATH=. python scripts/generate_demo_data.py
```

| File | Rows | Content |
|------|------|---------|
| `data/demo/electricity_demo.csv` | ≈885 | Daily kWh, 5 buildings, 6 months |
| `data/demo/water_demo.csv` | ≈900 | Daily litres, 5 buildings, 6 months |
| `data/demo/waste_demo.csv` | ≈130 | Monthly waste categories, 5 buildings |

All demo records carry `is_synthetic=True` in every row.

---

## UCI Machine Learning Repository Datasets

These are public datasets used **only for benchmark comparison**, never as campus data.

### Dataset 1: Individual Household Electric Power Consumption

| Attribute | Value |
|-----------|-------|
| **URL** | https://archive.ics.uci.edu/dataset/235/individual+household+electric+power+consumption |
| **Licence** | Creative Commons Attribution 4.0 (CC BY 4.0) |
| **Attribution** | Hebrail, G. & Berard, A. (2012). UCI Machine Learning Repository. |
| **Format** | ZIP → `.txt` (semicolon-separated) |
| **Size** | ~20 MB compressed / ~130 MB uncompressed |
| **Rows** | ~2,075,259 (1-minute readings, 2006–2010) |
| **Geography** | Sceaux, France — **single household** |

> [!CAUTION]
> This is household data from France, not Indian campus data.
> Do **not** import it into the campus audit pipeline as campus measurements.
> Use only for understanding energy consumption patterns at scale.

**Manual download steps:**
1. Visit https://archive.ics.uci.edu/dataset/235
2. Click **Download** → saves `individual+household+electric+power+consumption.zip`
3. Extract to `data/raw/uci_household_power/`
4. The extracted file is named `household_power_consumption.txt`

---

### Dataset 2: Appliances Energy Prediction

| Attribute | Value |
|-----------|-------|
| **URL** | https://archive.ics.uci.edu/dataset/374/appliances+energy+prediction |
| **Licence** | Creative Commons Attribution 4.0 (CC BY 4.0) |
| **Attribution** | Candanedo, L. (2017). UCI Machine Learning Repository. |
| **Format** | ZIP → CSV |
| **Size** | ~1 MB |
| **Rows** | ~19,735 (10-minute intervals, Jan–May 2016) |
| **Geography** | Stambruges, Belgium — **apartment** |

> [!CAUTION]
> Residential data from Belgium. Use only for appliance-level energy benchmarking.

---

### Dataset 3: Energy Efficiency

| Attribute | Value |
|-----------|-------|
| **URL** | https://archive.ics.uci.edu/dataset/242/energy+efficiency |
| **Licence** | Creative Commons Attribution 4.0 (CC BY 4.0) |
| **Attribution** | Tsanas, A. & Xifara, A. (2012). UCI Machine Learning Repository. |
| **Format** | ZIP → XLSX |
| **Size** | ~20 KB |
| **Rows** | 768 (simulated building configurations) |

> [!NOTE]
> Simulated data for building thermal load estimation, not measured readings.

---

## India Open Government Data

| Attribute | Value |
|-----------|-------|
| **Portal** | https://data.gov.in/ |
| **Licence** | National Data Sharing and Accessibility Policy (NDSAP) — Open Government Data Licence India |
| **Access** | Free registration required for some datasets |

**Useful search terms:**
- "electricity consumption education"
- "water supply campus"
- "municipal solid waste"
- "energy audit institution"

Always verify the specific dataset licence before use. Attribution is required under NDSAP.

---

## CPCB (Central Pollution Control Board)

| Attribute | Value |
|-----------|-------|
| **URL** | https://cpcb.nic.in/ |
| **Content** | Annual solid waste reports, water quality data, emission inventories |
| **Format** | PDF, Excel (manual download) |
| **API** | No bulk API — download individual reports |

CPCB publishes state-wise solid waste generation data in its annual reports. Useful for regional waste benchmarking.

---

## Automated Download Script

```powershell
$env:PYTHONPATH="c:\Users\Dell\Downloads\EduNet\green-campus-sustainability"
python scripts/download_datasets.py
```

This script:
- Attempts to download publicly available UCI datasets
- Validates file integrity where checksums are available
- Falls back gracefully when sources are unavailable (no internet required)
- Prints clear warnings for datasets requiring manual download
- Writes a manifest to `data/demo/demo_manifest.json`

> [!NOTE]
> The core application functions without any external dataset download.
> All UCI datasets are for optional reference use only.

---

## Emission Factor

The default emission factor is sourced from an official Indian government publication:

> **CEA CO2 Baseline Database for the Indian Power Sector, Version 18 (2022-23)**
> Central Electricity Authority, Ministry of Power, Government of India
> Factor: **0.716 kgCO2e/kWh** — Scope 2, national grid average

Configure in `.env`:
```
DEFAULT_EMISSION_FACTOR=0.716
EMISSION_FACTOR_SOURCE="CEA CO2 Baseline Database Version 18 (2022-23)"
EMISSION_FACTOR_UNIT="kgCO2e/kWh"
```

> [!IMPORTANT]
> This factor produces **estimates only**. It covers Scope 2 (purchased electricity) only.
> It does not include direct combustion, refrigerants, transport, waste, or water emissions.
> Update annually with the latest CEA publication.
> Not suitable for official GHG inventory reporting without professional verification.

---

## Import Templates

Blank CSV templates for user-provided campus measurements:

| Template | Path |
|----------|------|
| Electricity | `data/templates/electricity_template.csv` |
| Water | `data/templates/water_template.csv` |
| Waste | `data/templates/waste_template.csv` |

Upload these via the **Datasets** page in the UI (`/datasets`) or via the API:
- `POST /api/datasets/upload/electricity`
- `POST /api/datasets/upload/water`
- `POST /api/datasets/upload/waste`
