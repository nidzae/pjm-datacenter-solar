# US Gas-Plant / Solar / Data-Center Land Screen

### 🌐 Live interactive map → **https://nidzae.github.io/pjm-datacenter-solar/**

Click any plant to shade its developable solar land; toggle satellite imagery; search a place
or coordinates; filter by region (ISO/RTO) and by hostable data-center load.
See [Interactive map](#interactive-map-outputspjm_maphtml) below.

A first-pass GIS **feasibility screen** over **every operating natural-gas power plant in the
lower-48 US** (1,277 plants, ~476 GW): is there enough developable land within a short radius
to build (a) a new data center and (b) enough new solar to serve a flat 24/7 load equal to the
plant's nameplate capacity, with the existing gas plant supplying only **5% / 10% / 20%**
backup? *(Started as a PJM-only screen — hence the repo name — now nationwide.)*

Adapted from Chojkiewicz et al., *Utilizing Noncoincident Needs to Site Data Centers with
Solar+Storage at Existing Gas Plants* (Energy Institute at Haas **WP 356**, Feb 2026 —
[read the paper](https://haas.berkeley.edu/wp-content/uploads/archive/WP356.pdf)). The
paper's per-plant coordinates/land polygons are not published, so the land screen is rebuilt
here. **Deliberate difference from the paper:** we evaluate *all* US gas plants as candidates
for *brand-new* data centers (the paper's "nationwide potential" mode, its Fig. 4), not the
68 sites near already-proposed data centers.

This is a plausibility screen — **not** a cost or dispatch model. No LCOE, no hourly
optimization, no storage sizing (all deferred by design).

---

## Results at a glance

Fleet: **1,277 operating US (lower-48) gas plants, 476 GW** (153 GW simple-cycle peakers, 323 GW
combined-cycle), across 48 states and 50 balancing authorities. Qualifying plants and hostable
data-center load at 10 km buffer, 7 ac/MW:

| Gas cap | Forest EXCLUDED (conservative) | Forest INCLUDED (less aggressive) |
|---|---|---|
| 5%  | 734 plants · 127 GW | 873 plants · 178 GW |
| 10% | 744 plants · 132 GW | 885 plants · 186 GW |
| 20% | 773 plants · 146 GW | 922 plants · 206 GW |

(PJM subset for reference: 79 plants / 13 GW at 10%, forest-excluded.) Nationally the hit-rate is
higher than PJM — sunnier states need less solar per MW of load, and Western/rural plants have more
open land.

**Whole-plant vs partial opportunity.** The counts above require a plant to host a *full-nameplate*
data center. But a plant that can't fit the full load can still host a *smaller* one matched to its
available solar land (hostable load = `min(nameplate, headroom × nameplate)`). Summing those partials,
total **solar-limited hostable data-center load rises from ~132 GW (whole-plant, 10%) to ~240 GW** —
the map's popups and its hostable-load slider expose this per plant.

**Forest exclusion is the dominant sensitivity** (heavily-forested Eastern plants lose the most).
For the PJM subset the by-state qualifying nameplate lands in the same order of magnitude as the
paper's Fig. 4 (PA/OH/IL/VA/NJ) — see `outputs/summary.md` for the live comparison. Note Fig. 4
measures a solar/load potential, not qualifying gas nameplate (its IL value, 16 GW, even exceeds
IL's whole gas fleet), so an exact match isn't expected. See `outputs/summary.md`,
`outputs/pjm_sites.csv`, `outputs/pjm_map.html`.

---

## The qualification test (Spec §3 — implemented exactly)

For each plant `p` and gas cap `g ∈ {0.05, 0.10, 0.20}`:

```
R            = OVERBUILD * (1 - g) / CF_p            # MW solar per MW load; OVERBUILD = 1.3
solar_req    = R * nameplate_MW                       # MW solar required
land_req     = solar_req / power_density              # mi² of solar land
usable_solar = max(0, developable_area - dc_parcel) * power_density   # solar after the DC parcel
qualifies    = usable_solar >= solar_req              # ⟺ developable_area >= land_req + dc_parcel
headroom     = usable_solar / solar_req               # ≥ 1  ⟺  qualifies (exactly)
hostable     = min(nameplate, headroom * nameplate)   # data-center load the land can power
```

`CF_p` is the PVWatts capacity_factor (AC energy ÷ DC nameplate, ~0.11–0.22, the spec's "AC CF"
≈ 0.16) — used in `R` directly, **not** multiplied by the inverter ratio. `power_density` (7 ac/MW)
is on the same DC/panel basis, so `area × power_density` and `R` are consistent.

**Locked parameters** (`src/config.py`):

| Parameter | Value |
|---|---|
| Region | **US lower-48** (all balancing authorities; AK/HI excluded) |
| Gas caps `g` | 0.05, 0.10, 0.20 |
| Overbuild multiplier | **1.3** (battery losses + low-sun ride-through; calibrated, not derived) |
| Buffer radius | 10 km primary, 5 km sensitivity |
| Power density | 91 MW/mi² (7 ac/MW); sensitivity 128 (5 ac) / 80 (8 ac). Areas reported in mi². |
| DC parcel reserve | 150 acres |
| Solar geometry | fixed tilt = latitude, azimuth 180°, DC:AC 1.3, 14% losses |
| Capacity factor | per-plant AC, from SAM PVWatts on NSRDB TMY |

---

## Pipeline

| Phase | Script | Output |
|---|---|---|
| 1 Plant inventory | `01_extract_plants.py` | `data/interim/pjm_gas_plants.csv` |
| 3 Solar CF | `03_run_rev_gen.py` | `data/interim/pjm_plants_cf.csv` |
| 2 Exclusion masks | `02_build_exclusions.py` | `data/processed/exclusions/plant_*.tif` |
| 4 Supply curve | `04_run_rev_agg.py` | `data/processed/pjm_supply_curve.csv` |
| 5 Buffer aggregate | `05_buffer_aggregate.py` | `data/processed/pjm_plants_with_land.csv` |
| 6 Qualification | `06_qualify.py` | `outputs/pjm_sites.csv`, `outputs/pjm_sites_sensitivity.csv` |
| 7 Map + summary | `make_developable_geojson.py`, `07_map.py` | `outputs/pjm_map.html` (+ `outputs/dev_tiles/`), `outputs/summary.md` |
| 8 Flags (optional) | `08_flags.py` | `outputs/pjm_sites_flags.csv` |

Run order: `01 → 03 → 02 → 04 → 05 → 06 → 07 → 08`.

---

## Interactive map (`outputs/pjm_map.html`)

A self-contained Leaflet page (base HTML ~0.4 MB embedding 1,277 plants; open it in any browser —
needs internet for the base tiles). Keep the `outputs/dev_tiles/` folder next to it.

- **Search** (top center) — type a place name (geocoded via OpenStreetMap Nominatim) or raw
  `lat, lon` to drop a pin and zoom there.
- **Markers** — every US gas plant, drawn as a gauge: **outline ring = full nameplate**, **filled
  core = hostable data-center load** (core area ∝ hostable ÷ nameplate). **Green = full nameplate
  qualifies** (10% gas cap), **orange = only a partial data center fits**;
  **size ∝ nameplate MW**. Click for a popup (nameplate, AC CF, developable MW/mi², headroom
  per gas cap).
- **Click-to-hatch** — clicking a plant draws its 10 km buffer and shades the **developable
  solar land** with a thin diagonal hatch. Rendered at full **30 m fidelity with ~1.6k interior
  holes**, so lakes, developed parcels, roads, wetlands, steep slope, forest, and protected
  areas are cut out, not filled over. Each plant's polygon lazy-loads from
  `dev_tiles/plant_<code>.js` on click (via injected `<script>`, so it works from `file://`).
- **Street / Satellite toggle** (top-right) — flip to Esri World Imagery to see what's actually
  on the shaded land.
- **Popup** — for each plant: nameplate (= the 24/7 load), AC CF, solar that *fits* vs solar
  *needed*, and the **hostable DC load** (the solar-limited data-center size it can actually
  power — full nameplate for green, partial for orange), plus headroom per gas cap.
- **Hostable-load range slider** (top-left) — filter to plants that can host a data center in a
  given MW band, using the **solar-limited hostable load** (partial capacity), not full
  nameplate; *reset* restores the full range.
- **ⓘ Guide sidebar** (top-left) — a slide-in panel explaining every symbol, the glossary, the
  test, and the caveats; parameters and result counts are injected live from the data.

---

## How this implementation adapts the spec (important)

The spec (§0, §8) says to *VERIFY* library specifics and adapt, because it gives conceptual
requirements, not guaranteed-current config. Three adaptations were **forced by
infrastructure** and are documented here for reproducibility. **The qualification math is
exactly the spec; only the data-plumbing differs, and results are equivalent and defensible.**

1. **NREL API domain migrated.** `developer.nrel.gov` was retired 2026-05-29; all NREL/HSDS
   access now uses **`developer.nlr.gov`** (verified genuine — fronted by the federal
   `api.data.gov` / `api-umbrella` gateway on `cloud.gov`, not a look-alike). Key stored in
   `~/.hscfg`.

2. **Capacity factor via SAM PVWatts per plant, not full-grid reV-over-HSDS.** The current
   NSRDB on HSDS (`/nrel/nsrdb/GOES/conus/v4.0.0/`) is 2.8M points × 105k 5-min steps;
   a single nearest-point meta op over the throttled developer key (1000 req/hr) takes
   ~90 s. Running reV *generation* over the full PJM grid there is an HPC/local-`.h5` job,
   not tractable on this key. We evaluate the **same SAM PVWatts engine** (NREL-hosted,
   NSRDB TMY, identical fixed-tilt geometry) at each plant → `CF_p` directly. CF is defined
   AC-consistently with `R`: `AC_CF = PVWatts_CF × dc_ac_ratio`. PJM values land 0.17–0.21
   (mean 0.19), slightly above the spec's 0.16 anchor because of the 1.3 ILR — mildly
   optimistic; see caveats.

3. **Developable land via per-plant raster exclusion, not a PJM-wide reVX `.h5`.** Buffers
   are only 10 km, so exclusion data is fetched **within ~12 km of each plant** at NLCD's
   native 30 m / EPSG:5070 grid, instead of a multi-GB CONUS raster + HSDS-aligned
   exclusions `.h5`. Same exclusion logic, same `area × power_density`, exact required
   outputs. A "true reV/reVX on HPC with local NSRDB `.h5` tiles" variant is a drop-in
   replacement for Phases 3–5 if that environment is available.

---

## Data sources & vintages

| Layer | Source | Vintage |
|---|---|---|
| Plants | EIA-860 Plant + Generator (Operable) | **2024** |
| Gas generation / actual CF | EIA-923 Page 1 net generation | **2024** |
| Solar resource | NREL NSRDB via SAM PVWatts (`developer.nlr.gov`) | TMY (GOES v4.0.0) |
| Land cover | NLCD (MRLC WCS, `NLCD_2021_Land_Cover_L48`) | **2021** |
| Slope | USGS 3DEP Elevation ImageServer (30 m) → gradient | current |
| Protected areas | PAD-US 4.0 "Protection Status by GAP Status" FeatureServer | 4.0 |

**Exclusion rules** (all toggleable in `config.py`): NLCD open water, ice/snow, developed
(all), wetlands, and **forest (default on — conservative)**; slope > **10%** (test 5%);
PAD-US GAP status 1/2/3. Developable = barren, shrub, grassland, pasture, cultivated crops.

---

## Caveats & known biases (Spec §12)

- **`R` is a heuristic, optimistic before the 1.3× fix.** Energy parity ignores storage
  losses and low-sun overbuild; 1.3× is a calibrated correction, not a derived value.
  Results are a plausibility screen, not a feasibility guarantee.
- **Aggregate GW can double-count shared land.** Each plant is screened against the land within
  its *own* 10 km buffer, independently. 67% of US plants have a neighbor within 20 km, so their
  buffers overlap and the same acreage may count toward two or more plants. **Per-plant verdicts
  and hostable loads (the map popups) are unaffected and valid**, but the national roll-ups
  (~160 GW whole-plant, ~268 GW with partials at 10%) are an **upper bound**, not a strictly
  additive potential. De-duplicating overlapping buffers would lower the aggregate.
- **Capacity factor** is the PVWatts `capacity_factor` (0.11–0.22, mean ~0.17, Southwest highest;
  the spec's ~0.16 "AC CF" used in `R` directly, **not** ×ILR). It is snapped to a 0.25° (~17 mi)
  grid for the national run (per-plant error ≲0.01, negligible). Fixed-tilt is assumed; single-axis
  tracking would raise CF, lower `R`, and expand the qualifying set.
- **Presence ≠ headroom** for fiber and water (Phase 8 flags never gate qualification).
- **Transmission line capacity is out of scope** — nameplate is the interconnection proxy,
  consistent with the paper. Enabling mechanism = **surplus interconnection service (SIS)**;
  PJM has an SIS process (FERC Order 845), rules moving in 2024–2026. Verify live.
- **No storage, dispatch, LCOE, or emissions.** This answers only "is the land physically
  there."
- **Fixed-tilt assumed** to match the paper. Single-axis tracking would raise CF, lower `R`,
  and expand the qualifying set — offered as a future variant.
- **Exclusion rules are conservative toggles.** Excluding all forest is aggressive; it is a
  switch and reported as sensitivity.

---

## Environment

Python 3.11 in the `pjm` conda env. `pip install -r requirements.txt`. NREL key in
`~/.hscfg` (`hs_endpoint = https://developer.nlr.gov/api/hsds`, `hs_api_key = ...`) and/or
`NREL_API_KEY`. All distance/area math in EPSG:5070; lat/lon reported in EPSG:4326.
