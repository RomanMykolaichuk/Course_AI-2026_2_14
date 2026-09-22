# Data Sources

This document is the registry for external datasets used or evaluated by the project.

**Last reviewed:** 2026-09-22

## Source roles

Sources are divided into four roles:

- **primary** — core historical attack dataset used to build the first analytical dataset;
- **enrichment** — additional variables joined to the primary data;
- **validation** — independent datasets used to check coverage or historical consistency;
- **reference** — GIS/reference layers used by ETL or the dashboard.

A source can be useful without being suitable as a training label. The project must preserve that distinction.

## Source registry

| Source | Role | Access | Coverage / granularity | Project status | Main limitations |
|---|---|---|---|---|---|
| Massive Missile Attacks on Ukraine — Petro Ivaniuk (Kaggle) | primary | Kaggle dataset / CSV | attack intervals; missile/UAV model-level rows; available from 2022-09-28 | **selected for MVP** | manually compiled from public reports; target field is not a clean oblast label; early 2022 is not covered; missing values can mean “unknown” |
| alerts.in.ua API | enrichment | REST JSON + personal token | current alerts and limited region alert history | candidate | historical API endpoint is not a complete multi-year archive; rate limits apply |
| Ukraine Alarm API | enrichment / validation | official API, access by application | current alerts; region history endpoint | candidate | API access must be requested; history endpoint is not intended as a complete research archive |
| ACLED | validation / possible backfill | API, CSV/JSON | geocoded conflict events | candidate | separate event ontology; terms restrict redistribution of raw licensed content; should not be treated as equivalent to Air Force reporting |
| UCDP GED / Candidate | validation | REST JSON / CSV / Excel | georeferenced organized-violence events | candidate | event inclusion requires direct fatalities, therefore it cannot represent all aerial attacks |
| ERA5 hourly single-level data | enrichment | Copernicus CDS/API | global, hourly, 0.25° atmospheric grid | candidate | large data volume; spatial/temporal join is required |
| geoBoundaries gbOpen | reference | REST metadata + GeoJSON/SHP | administrative boundaries, including ADM1 | **selected for GIS reference** | boundary vintage must be recorded and kept consistent across runs |
| Meteostat | optional enrichment | Python / CSV / JSON API | station/point weather observations | optional | provider-specific licensing and station coverage need to be preserved in metadata |

## 1. Primary dataset — Massive Missile Attacks on Ukraine

**Publisher/maintainer:** Petro Ivaniuk (Kaggle user `piterfm`)  
**URL:** https://www.kaggle.com/datasets/piterfm/massive-missile-attacks-on-ukraine  
**License:** CC BY-NC-SA 4.0  
**Project role:** primary historical source for MVP.

The dataset is manually compiled from public reports of the Air Force Command of the Armed Forces of Ukraine and the General Staff published on social media.

Important files:

- `missile_attacks_daily.csv` — historical attack records;
- `missiles_and_uavs.csv` — reference information about missile/UAV models.

The source Data Card documents fields including `affected_region`, but the actual KaggleHub snapshot acquired on 2026-09-22 does **not** contain that column. The acquisition pipeline therefore records the exact CSV headers in snapshot metadata and treats `affected_region` as optional.

Important fields observed/used in `missile_attacks_daily.csv` include:

- `time_start`, `time_end`;
- `model`;
- `launch_place`;
- `target`;
- `carrier`;
- `launched`;
- `destroyed`;
- `not_reach_goal`;
- `border_crossing`;
- `still_attacking`;
- source/provenance fields available in the dataset.

### Why it is selected

It is machine-readable, directly aligned with the analytical topic, contains a long historical series, and provides weapon/model counts that are useful for descriptive analytics and feature engineering.

### Known limitations

1. It is not a complete incident-level geospatial record.
2. `target` may contain a city, oblast, direction, multiple regions, or all of Ukraine.
3. One source row may describe an attack wave and weapon model rather than a single impact.
4. Null numerical values must remain null unless the source explicitly states zero.
5. The dataset starts after the beginning of the full-scale invasion and should not be presented as complete coverage from 2022-02-24.
6. License attribution, non-commercial and share-alike requirements must be respected when redistributing derived dataset artifacts.
7. The documented schema and the downloadable CSV schema can differ; transformation code must rely on the acquired snapshot schema, not only on the Data Card.
8. The 2026-09-22 snapshot lacks `affected_region`; oblast links for that build come only from conservative parsing of explicit administrative-region mentions in `target`.

## 2. Alert data

### alerts.in.ua

**Documentation:** https://devs.alerts.in.ua/  
**Access:** personal token; JSON REST API.

Useful fields include alert type, oblast/location identifiers, start/end time, and threat metadata. The API documentation includes a region-history endpoint, but its documented period is limited and has stricter request limits.

**Decision:** use as an enrichment source only when the project has a reproducible historical archive. Do not silently combine a short recent alert window with a multi-year strike dataset.

### Ukraine Alarm API

**Access request:** https://api.ukrainealarm.com/  
**API client documentation:** https://github.com/UkraineAlarm/UkraineAlarm-javascript/blob/master/docs/AlertsApi.md

This is the official API for information used by the “Повітряна тривога” application.

**Decision:** useful for validation/current collection. If the project begins collecting it, snapshots must be archived so that future experiments use reproducible historical data.

## 3. Independent conflict-event sources

### ACLED

**API documentation:** https://acleddata.com/acled-api-documentation  
**EULA:** https://acleddata.com/eula

ACLED provides geocoded conflict-event data and API output in JSON or CSV.

**Decision:** use for coverage checks, independent spatial comparison, and possible historical backfill experiments. Keep ACLED-derived tables separate from the primary source until an explicit ontology mapping has been documented.

Raw ACLED licensed content must not be redistributed from this repository unless the terms permit it.

### UCDP GED / Candidate

**Downloads:** https://ucdp.uu.se/downloads/  
**API:** https://ucdp.uu.se/apidocs/

UCDP provides georeferenced organized-violence events. Candidate releases are published monthly with low lag.

**Decision:** validation only for the first version. UCDP event inclusion is fatality-based, so absence of a UCDP event does not imply absence of an aerial attack.

## 4. Weather / environmental features

### ERA5

**Dataset:** https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels  
**License:** CC-BY.

ERA5 provides hourly global reanalysis data at 0.25° resolution for atmospheric single-level variables. Potential features include:

- wind speed/direction;
- precipitation;
- cloud cover;
- surface pressure;
- temperature.

**Decision:** preferred reproducible weather source for research experiments. Weather features must be joined by historical event time and an explicitly documented spatial aggregation rule.

### Meteostat

**Developer documentation:** https://dev.meteostat.net/  
**Hourly data:** https://dev.meteostat.net/api/point/hourly

Meteostat is easier to prototype with than ERA5.

**Decision:** optional prototype source. Record the underlying provider/license metadata for every extract used.

## 5. Administrative boundaries

### geoBoundaries

**API:** https://www.geoboundaries.org/api.html  
**Recommended product:** `gbOpen`  
**Current UKR ADM1 boundary ID:** `UKR-ADM1-14850775`  
**Boundary year represented:** 2017  
**Build date reported by API:** Dec 12, 2023  
**Layer license reported by API:** Open Data Commons Open Database License 1.0 (ODbL 1.0).

The general geoBoundaries API documentation describes `gbOpen` as the preferred open product, but the project records the license returned by the **specific acquired layer metadata** rather than assuming one license for every layer.

**Decision:** use the current UKR ADM1 layer as the canonical map geometry for retrospective dashboard aggregation. The 27 ADM1 features map 1:1 to the project's 27 canonical regions using `shapeISO` as the primary key and source name only as a fallback.

Record for every acquisition:

- `boundaryID`;
- boundary year represented;
- source/build date;
- acquisition timestamp;
- exact layer license and license source;
- geometry variant;
- SHA-256 checksum of the downloaded GeoJSON.

## Source acceptance checklist

Before a new source is promoted from `candidate` to `selected`, record:

- publisher/maintainer;
- public URL;
- access method;
- historical coverage;
- update frequency;
- geographic and temporal granularity;
- available fields;
- license / terms of use;
- known gaps or biases;
- mapping to the canonical schema;
- date checked;
- reproducible acquisition method.

## Data-source precedence for MVP

For the first implementation:

1. **Attack facts and weapon counts:** Massive Missile Attacks on Ukraine.
2. **Region geometry:** geoBoundaries ADM1.
3. **Weather enrichment:** ERA5 (optional for baseline, recommended for later experiments).
4. **Alert enrichment:** only after a reproducible historical alert archive is available.
5. **ACLED/UCDP:** validation/backfill layers, not automatic substitutes for the primary labels.

No external source should be ingested into the analytical dataset before its provenance, license, and transformation rules are documented.