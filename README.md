# PJM Gas-Plant / Solar / Data-Center Land Screen

### 🌐 Live interactive map → **https://nidzae.github.io/pjm-datacenter-solar/**

Click any plant to shade its developable solar land; toggle satellite imagery; search a place
or coordinates; filter by hostable data-center load. See [Interactive map](#interactive-map-outputspjm_maphtml) below.

A first-pass GIS **feasibility screen**: for every operating natural-gas power plant in the
PJM region, is there enough developable land within a short radius to build (a) a new data
center and (b) enough new solar to serve a flat 24/7 load equal to the plant's nameplate
capacity, with the existing gas plant supplying only **5% / 10% / 20%** backup?

Adapted from Chojkiewicz et al., *Utilizing Noncoincident Needs to Site Data Centers with
Solar+Storage at Existing Gas Plants* (Energy Institute at Haas **WP 356**, Feb 2026 —
[read the paper](https://haas.berkeley.edu/wp-content/uploads/archive/WP356.pdf)). The
paper's per-plant coordinates/land polygons are not published, so the land screen is rebuilt
here. **Deliberate difference from the paper:** we evaluate *all* PJM gas plants as
candidates for *brand-new* data centers (the paper's "nationwide potential" mode, its
Fig. 4), not the 68 sites near already-proposed data centers.

This is a plausibility screen — **not** a cost or dispatch model. No LCOE, no hourly
optimization, no storage sizing (all deferred by design).

---

## Results at a glance

Fleet: **199 operating PJM gas plants, 94.4 GW** (30.5 GW simple-cycle peakers, 64.0 GW
combined-cycle). Qualifying plants and hostable data-center load at 10 km buffer, 7 ac/MW:

| Gas cap | Forest EXCLUDED (conservative) | Forest INCLUDED (less aggressive) |
|---|---|---|
| 5%  | 90 plants · 17.5 GW | 130 plants · 32.4 GW |
| 10% | 91 plants · 17.8 GW | 131 plants · 33.4 GW |
| 20% | 93 plants · 18.8 GW | 135 plants · 37.9 GW |

**Whole-plant vs partial opportunity.** The counts above require a plant to host a *full-nameplate*
data center. But a plant that can't fit the full load can still host a *smaller* one matched to its
available solar land (hostable load = `min(nameplate, headroom × nameplate)`). Summing those partials,
total **solar-limited hostable data-center load rises from ~17.8 GW (whole-plant, 10%) to ~44 GW** —
the map's popups and its hostable-load slider expose this per plant.

**Forest exclusion is the dominant sensitivity** (heavily-forested VA/PA lose the most).
By-state, the **forest-included** screen aligns with paper Fig. 4 (VA 8.0 vs 10, OH 7.3 vs
12 GW); totals are the same order of magnitude but lower, as expected — Fig. 4 measures a
solar/load potential, not qualifying gas nameplate (its IL value, 16 GW, even exceeds IL's
whole gas fleet here). See `outputs/summary.md`, `outputs/pjm_sites.csv`, `outputs/pjm_map.html`.

---

## The qualification test (Spec §3 — implemented exactly)

For each plant `p` and gas cap `g ∈ {0.05, 0.10, 0.20}`:

```
R          = OVERBUILD * (1 - g) / CF_p           # MW-AC solar per MW load; OVERBUILD = 1.3
solar_req  = R * nameplate_MW                      # MW-AC solar required
land_req   = solar_req / power_density             # km² of solar land
dev_MW     = developable_area * power_density       # from the land screen
qualifies  = dev_MW >= solar_req AND developable_area >= land_req + dc_land
headroom   = dev_MW / solar_req
```

**Locked parameters** (`src/config.py`):

| Parameter | Value |
|---|---|
| Region | EIA Balancing Authority Code = `PJM` |
| Gas caps `g` | 0.05, 0.10, 0.20 |
| Overbuild multiplier | **1.3** (battery losses + low-sun ride-through; calibrated, not derived) |
| Buffer radius | 10 km primary, 5 km sensitivity |
| Power density | 35.3 MW/km² (7 ac/MW); sensitivity 49.4 (5 ac) / 30.9 (8 ac) |
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

A self-contained Leaflet page (base HTML ~55 KB; open it in any browser — needs internet for
the base tiles). Keep the `outputs/dev_tiles/` folder next to it.

- **Search** (top center) — type a place name (geocoded via OpenStreetMap Nominatim) or raw
  `lat, lon` to drop a pin and zoom there.
- **Markers** — every PJM gas plant. **Green = qualifies** (10% gas cap), **red = does not**;
  **size ∝ nameplate MW**. Click for a popup (nameplate, AC CF, developable MW/km², headroom
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
  power — full nameplate for green, partial for red), plus headroom per gas cap.
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
- **CF is mildly optimistic** here (~0.19 AC vs spec's 0.16 anchor) due to the 1.3 ILR
  definition; lower CF would raise `R` ~15–20% and shrink the qualifying set. Reported as
  a sensitivity axis.
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
