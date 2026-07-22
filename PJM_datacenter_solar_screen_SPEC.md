# Build Spec — PJM Gas-Plant / Solar / Data-Center Land Screen

**For: Claude Code.** This is the authoritative build brief. Read it fully before writing code. Where it says *VERIFY*, confirm exact syntax against the installed library version rather than assuming — API schemas for NREL reV change across releases, and this spec gives conceptual requirements, not guaranteed-current config keys.

---

## 0. TL;DR — what you are building

A GIS pipeline that screens every natural-gas power plant in the PJM region and answers, per plant:

> Is there enough developable land within a short radius to build (a) a new data center and (b) enough solar to serve a flat 24/7 load equal to the plant's nameplate capacity, with the existing gas plant supplying only 5% / 10% / 20% backup?

Output: a ranked table + interactive map of qualifying sites, plus a PJM-wide summary of hostable "clean-ish" data-center load (GW) at each gas-backup level.

This is a **first-pass feasibility screen**, not a cost or dispatch model. No LCOE, no hourly optimization, no storage sizing. Those are explicitly deferred.

---

## 1. Goal and scope

**Goal.** Find existing PJM gas plants where a *new* data center could be built alongside enough new solar to run it on mostly carbon-free power, reusing the plant's existing grid connection and using the gas plant as non-coincident firm backup ("non-coincident" = the data center's backup need falls at different times than grid-wide peak demand, so the gas unit can serve both roles — see §2).

**Origin.** Adapted from Chojkiewicz et al., *Utilizing Noncoincident Needs to Site Data Centers with Solar+Storage at Existing Gas Plants* (Energy Institute at Haas WP 356, Feb 2026) and its predecessor (Paliwal/Chojkiewicz et al., GSPP *Surplus Interconnection*, 2024). Their published results are aggregate-only (no downloadable per-plant coordinates or land polygons), so the land screen is rebuilt here.

**Deliberate difference from the paper.** The paper filtered to plants near *already-proposed* data centers. This screen does the opposite: evaluate *all* PJM gas plants as candidates for *brand-new* data centers, and use land availability as the gating test. This is the paper's "nationwide potential" mode (its Figure 4), not its 68-site mode.

**In scope:** plant inventory, solar resource, land-exclusion screening, the land-sufficiency test, mapping, optional fiber/water flags.

**Out of scope (deferred):** transmission line capacity (use nameplate as the interconnection proxy — see §12), storage sizing, hourly dispatch, LCOE, emissions accounting, the grid-conflict analysis.

---

## 2. Core concepts and definitions

- **Nameplate capacity** — the generator's maximum rated continuous output in MW, as registered with EIA. Used here as (a) the size of the new data-center load and (b) a proxy for the existing interconnection capacity. Not the same as energy produced; a peaker rated 300 MW may run <10% of the year.
- **Flat load / constant load** — the data center is modeled as drawing a constant number of MW every hour, 24/7. This is the most demanding profile to serve from solar and the conservative choice.
- **Gas cap (g)** — the fraction of annual data-center energy the gas plant is allowed to supply. Run at g = 5%, 10%, 20%. Lower g = cleaner but more solar/land; higher g = less land but more emissions. This is the carbon-free ↔ carbon-reduced dial.
- **Solar-to-load ratio (R)** — MW of solar required per MW of data-center load. Derived from capacity factor (§3), not optimized.
- **Capacity factor (CF)** — a solar array's annual energy output ÷ its theoretical maximum if it ran at nameplate every hour. PJM fixed-tilt utility solar ≈ 0.15–0.18 AC (*moderate confidence*; reV computes it per site — use that).
- **Developable land** — land inside the buffer that survives the exclusion screen (§7, Phase 2): not water, wetland, developed, steep, or protected.
- **Non-coincident firm backup** — the gas plant is dispatchable ("firm") and the data center's need for it (winter nights, low-sun stretches) historically does not coincide with grid peak demand (summer afternoons), so one gas unit can back the data center *and* remain available to the grid. This screen does not model it; it is the rationale for why gas backup does not simply steal grid capacity.
- **Surplus interconnection service (SIS)** — the regulatory mechanism (FERC Order 845) that lets new generation/storage connect at an existing plant's interconnection point without a full new interconnection study. PJM has an SIS process; it is why PJM is a viable pilot region. Not modeled here; note it in the README as the enabling assumption.

---

## 3. Methodology — the qualification test

For each plant `p` and each gas cap `g ∈ {0.05, 0.10, 0.20}`:

```
CF_p        = AC solar capacity factor at plant p           (from reV, fixed-tilt, fraction 0–1)
overbuild   = 1.3                                           (conservative multiplier, see note)
R           = overbuild * (1 - g) / CF_p                    (MW solar per MW load)
solar_req   = R * nameplate_MW_p                            (MW solar required)
land_req    = solar_req / power_density                     (km² of solar land required)
dc_land     = DC_LAND_ACRES (default 150) converted to km²  (parcel reserved for the data center)

developable_MW_p   = solar capacity that fits in developable land within buffer (from reV, see §7)
developable_area_p = developable land within buffer (km²)

qualifies_p,g = developable_MW_p >= solar_req
                AND developable_area_p >= (land_req + dc_land)
headroom_p,g  = developable_MW_p / solar_req
```

**Why R = (1 − g) / CF, times 1.3.** The `(1 − g) / CF` term is *energy parity*: size solar so its annual generation equals the annual load the solar must cover (everything not covered by gas). Example at CF = 0.16: g=5% → R≈5.9, g=10% → R≈5.6, g=20% → R≈5.0.

**The 1.3 multiplier is required and deliberate.** Energy parity understates real need because it ignores (a) battery round-trip losses and (b) the overbuild needed to ride through multi-day low-sun stretches while serving a flat load. The paper's optimized sunbelt ratio ran ~1.3× above energy parity. Applying 1.3 makes this screen *conservative* rather than optimistic. Keep it as a named constant `OVERBUILD = 1.3` so it can be tuned. (*Confidence: moderate that 1.3 is roughly right for PJM; it is a calibrated guess, not a derived value.*)

**Power density.** reV expresses developable capacity via a power density in MW/km². Derive it from a land-use assumption so it is auditable:

```
acres_per_MW = 7          # fixed-tilt utility PV total-area, NREL ballpark; range 5–8 (moderate confidence)
power_density = 1 / (acres_per_MW * 0.00404686)   # ≈ 35.3 MW/km² at 7 ac/MW
```

Sensitivity band: 5 ac/MW → ~49 MW/km²; 8 ac/MW → ~31 MW/km². Run the screen at the default and report how qualifying-site count moves across the band. *VERIFY reV's own default `power_density` and override it explicitly.*

**Data-center parcel.** Solar land dwarfs data-center land (thousands of acres vs ~150), so `dc_land` rarely changes the verdict, but reserve it so the output is defensible. Make `DC_LAND_ACRES` a config constant.

---

## 4. Locked parameters

| Parameter | Value | Notes |
|---|---|---|
| Region | PJM | Filter by EIA Balancing Authority Code = `PJM` |
| Gas caps `g` | 0.05, 0.10, 0.20 | Run all three |
| Overbuild multiplier | 1.3 | Named constant |
| Buffer radius | 10 km primary; 5 km sensitivity | Match source methodology; test tighter |
| Capacity factor | Per-site, from reV | Fixed-tilt AC; regional sanity ~0.16 |
| Solar geometry | Fixed tilt = latitude, azimuth 180° (south) | Matches paper |
| Power density | ~35 MW/km² (7 ac/MW) | Sensitivity 31–49 |
| DC parcel reserve | 150 acres | Configurable |
| Study years | 2016–2023 for CF, or a TMY for speed | Match paper if feasible; TMY acceptable first pass |

---

## 5. Data sources

All downloadable in your environment (it has internet). Cache raw files under `data/raw/`.

**Plants — EIA (high confidence).**
- EIA Form 860, latest annual vintage — `https://www.eia.gov/electricity/data/eia860/`. Use the **Plant** file (Plant Code, Name, State, Latitude, Longitude, Balancing Authority Code) and the **Generator** file, *Operable* tab (Plant Code, Generator ID, Nameplate Capacity MW, Prime Mover, Energy Source 1, Status).
- EIA Form 923 (optional, for actual capacity factor / "underutilized" framing) — `https://www.eia.gov/electricity/data/eia923/`. Page 1 net generation by month.

**Solar resource — NREL NSRDB (high confidence).**
- National Solar Radiation Database via reV/rex. Access through **HSDS** (`h5pyd`, needs a free NREL API key from `https://developer.nrel.gov/signup/`) or downloaded `.h5` tiles. *VERIFY current HSDS endpoint paths in the installed `rex` version.*

**Land exclusions — USGS (moderate-high confidence).**
- NLCD land cover — `https://www.mrlc.gov/` (exclude water, wetlands, developed, optionally forest).
- Slope from USGS 3DEP / SRTM DEM — `https://www.usgs.gov/3d-elevation-program` (exclude slope > 5–10%).
- PAD-US protected areas — `https://www.usgs.gov/programs/gap-analysis-project/science/pad-us-data-download` (exclude parks, wilderness, military, protected).

**Optional fiber/water flags (§10).**
- Fiber long-haul: InterTubes dataset via IMPACT Cyber Trust (`https://www.impactcybertrust.org/`, dataset 521) — presence only, ~2014 vintage, no capacity.
- Fiber access: FCC National Broadband Map — `https://broadbandmap.fcc.gov/` — service-availability proxy.
- Water stress: WRI Aqueduct 4.0 (CC BY 4.0) — `https://www.wri.org/aqueduct` / Google Earth Engine `WRI/Aqueduct_Water_Risk/V4`.
- Water presence/withdrawals: USGS NHD + NWIS Water Use — `https://waterdata.usgs.gov/nwis/wu`.

**Cross-check only (not a data source).**
- ScarcityToSurplus thermal dashboard — `https://www.scarcitytosurplus.com/thermal/dashboard`. Per-plant "solar integration potential (MW)" is viewable one plant at a time; no bulk export. Use for manual spot-checks of a few PJM plants against your reV output.

---

## 6. Environment setup

- Python 3.10 or 3.11 in a fresh venv/conda env.
- Core: `NREL-reV`, `NREL-rex`, `NREL-reVX`, `geopandas`, `rasterio`, `shapely`, `pyproj`, `pandas`, `numpy`, `requests`, `openpyxl`.
- Mapping: `folium` (or `plotly`) for the interactive HTML map; `matplotlib` for static figures.
- Set `NREL_API_KEY` env var for NSRDB/HSDS. *VERIFY reV/rex install works against HSDS with a trivial test query before running the full pipeline.*
- Use a projected CRS for all buffering and area math: **US Albers Equal Area, EPSG:5070**. Reproject plant points and exclusion layers into 5070 before any distance/area operation; report lat/long in EPSG:4326.

---

## 7. Pipeline — phase by phase

### Phase 1 — Plant inventory (`01_extract_plants.py`)
Inputs: EIA-860 Plant + Generator files (and 923 if doing actual CF).
Steps:
1. Load Generator (Operable). Filter: `Energy Source 1 == 'NG'`, `Status == 'OP'`, `Prime Mover in {GT, CT, CA, CS, CC}`.
2. **Classify prime movers precisely (this is a known EIA gotcha):**
   - Simple-cycle peaker (paper's "CT") = prime mover **`GT`**.
   - Combined cycle (paper's "CCGT") = prime movers **`CT`, `CA`, `CS`, `CC`**.
   - Do not confuse EIA code `CT` (a combined-cycle component) with the paper's word "CT" (a peaker). Map explicitly.
3. Join to Plant file on Plant Code. Filter `Balancing Authority Code == 'PJM'`.
4. Aggregate nameplate to plant level: total gas MW = sum of all qualifying units; also keep the peaker-vs-CCGT split for reporting. Load target = total gas MW.
5. (Optional) Join EIA-923 net generation → actual capacity factor per plant, for the "underutilized" narrative.
Output: `data/interim/pjm_gas_plants.csv` with plant_code, name, state, lat, lon, ba, nameplate_MW_total, nameplate_MW_peaker, nameplate_MW_ccgt, (actual_CF optional).

### Phase 2 — Exclusion layer (`02_build_exclusions.py`)
Build the developable-land mask over the PJM bounding box.
1. Assemble rasters aligned to a common grid (30 m if feasible, matching the source's parcel resolution; coarser acceptable first pass): NLCD land cover, slope (derived from DEM via `gdaldem slope` or `richdem`), PAD-US rasterized.
2. Exclusion rules (start conservative, make each toggleable):
   - Exclude NLCD open water, wetlands, developed (all intensities), perennial ice/snow. Forest: exclude by default, flag as a toggle (excluding forest is conservative).
   - Exclude slope > 10% (test 5%).
   - Exclude all PAD-US protected/park/wilderness/military.
3. Compile into a reV/reVX exclusions HDF5. *VERIFY the current reVX `ExclusionsConverter` / layer-config syntax; build the `.h5` with one dataset per exclusion layer plus an `include`/`exclude` rule set.*
Output: `data/processed/exclusions.h5`.

### Phase 3 — Solar generation + CF (`03_run_rev_gen.py`)
Run reV generation (SAM PVWatts) over the PJM NSRDB resource.
- SAM PVWatts config: `array_type = 0` (fixed open rack), `tilt = latitude` per site, `azimuth = 180`, `dc_ac_ratio ≈ 1.3`, `losses ≈ 14%` (standard). To replicate the paper's zero-loss-then-apply approach, set losses = 0 and note it; either way keep the CF definition (AC) consistent with R. *VERIFY PVWatts version and param names in installed reV.*
- Run for 2016–2023 (multi-year) if compute allows, else a single TMY for the first pass.
Output: per-resource-gridpoint mean AC capacity factor + (optionally) generation profiles.

### Phase 4 — Supply-curve aggregation (`04_run_rev_agg.py`)
Run reV supply-curve aggregation to convert exclusions + resource into developable capacity.
- Apply `exclusions.h5`, set `power_density` per §3 (~35 MW/km², explicit), choose an aggregation `resolution`.
- Output per supply-curve point: centroid lat/lon, `area_developable_km2` (or available area), `capacity_MW`, `mean_cf`.
Output: `data/processed/pjm_supply_curve.csv` (or gpkg).

### Phase 5 — Per-plant buffer aggregation (`05_buffer_aggregate.py`)
This is the custom step that makes the screen plant-centric (reV aggregates by region, not by plant).
1. Reproject plants and supply-curve points to EPSG:5070.
2. For each plant, buffer 10 km (and 5 km). Sum `capacity_MW` of supply-curve points whose centroid falls in the buffer → `developable_MW`. Sum area → `developable_area_km2`. Area-weight `mean_cf` → `CF_p`.
3. Subtract `dc_land` from `developable_area_km2` before the area comparison in Phase 6.
Output: `data/processed/pjm_plants_with_land.csv` adding CF_p, developable_MW, developable_area_km2, at 10 km and 5 km.

### Phase 6 — Qualification (`06_qualify.py`)
Apply §3 math for each plant × gas cap × buffer × power-density-sensitivity.
Output: `outputs/pjm_sites.csv` with, per plant: identity, nameplate, CF_p, developable_MW, and for each g: R, solar_req_MW, land_req_km2, qualifies (bool), headroom. Also a `qualifying_any` flag.

### Phase 7 — Map + summary (`07_map.py`)
- Interactive map (`folium`/`plotly`, saved as `outputs/pjm_map.html`): plot PJM gas plants, marker size ∝ nameplate, color ∝ qualification (e.g., qualifies at 10% cap) or headroom. Popup: name, nameplate, CF, developable_MW, headroom at each g.
- Summary (`outputs/summary.md`): count of qualifying plants and sum of nameplate (= hostable data-center load, GW) at each g and each buffer; roll-up by state.

### Phase 8 — Optional fiber/water flags (`08_flags.py`)
Add as **flags, not pass/fail** (open data gives presence, never headroom — see §10). For each plant: distance to nearest InterTubes long-haul route, FCC broadband availability at the point, Aqueduct water-stress category, distance to NHD surface water. Append columns; do not gate qualification on them.

---

## 8. reV configuration requirements (conceptual)

reV runs as a multi-module pipeline (generation → collect/multi-year → supply-curve-aggregation → supply-curve). For this screen you need **generation** (Phase 3) and **supply-curve-aggregation** (Phase 4); the supply-curve and rep-profiles modules are optional. Because exact config-JSON keys and the CLI (`reV`, or the `gaps`-based pipeline) differ by version, **do not hardcode config from memory** — generate configs from the installed version's example templates (`reV` ships examples; check the repo's `examples/` and `--help`) and adapt. Keep every reV config file under `config/` and commit it.

Minimum you must get right regardless of version:
- Resource = NSRDB, PJM bounding box.
- SAM = PVWatts, fixed-tilt geometry per §7 Phase 3.
- Exclusions = your `exclusions.h5`, with `power_density` set explicitly per §3.
- Output fields include mean capacity factor and developable capacity/area per supply-curve point.

---

## 9. Outputs (deliverables)

1. `outputs/pjm_sites.csv` — the master per-plant qualification table.
2. `outputs/pjm_map.html` — interactive map.
3. `outputs/summary.md` — qualifying-site counts and hostable-load GW by gas cap, buffer, and state.
4. `config/` — all reV/SAM/exclusion configs, committed for reproducibility.
5. `README.md` — restate goal, parameters, §12 caveats, and the exact data vintages used.

---

## 10. Fiber and water — treat as flags only

Open data establishes **presence**, never **available capacity for a new load**. A nearby fiber route or an unstressed basin does not prove there is surplus fiber or surplus water for a new data center — that is proprietary carrier data and state water-permitting, respectively. So Phase 8 outputs *flags and rankings*, and qualification never depends on them. Document this limitation in the README; it is the same gap the source paper leaves open (it assumed adequacy from a neighboring project and never verified headroom).

---

## 11. Validation and cross-checks

- **Order-of-magnitude vs paper (Figure 4 state potentials, GW):** PA 17, OH 12, IL 16, VA 10, NJ 6. Your qualifying-nameplate roll-up by state should land in this range; large deviations mean a bug in exclusions, power density, or the BA filter.
- **Paper PJM LCOE tier** (~$119/MWh, n=14) is a cost anchor for later, not this screen.
- **Named PJM plants** to expect in the fleet (paper Table S3): Aurora (IL), Bergen (NJ), Bluegrass (KY), Chesterfield (VA), Doswell (VA), Gravel Neck (VA), Hopewell (VA), Ladysmith (VA), Marsh Run (VA), Moxie Freedom (PA), Potomac Energy Center (VA), Remington (VA), plus Kearny Station (NJ). Use for name-matching sanity.
- **Dashboard spot-check:** for 3–5 PJM plants, compare your `developable_MW` to the dashboard's per-plant solar integration potential (manual lookup).

---

## 12. Caveats and known biases (put these in the README)

- **R is a heuristic, biased optimistic before the 1.3× fix.** Energy parity ignores storage losses and low-sun overbuild; 1.3× is a calibrated correction, not a derived value. Results are a plausibility screen, not a feasibility guarantee.
- **Presence ≠ headroom** for fiber and water (§10).
- **Transmission line capacity is out of scope.** Line thermal ratings and available transfer capability are largely non-public (Critical Energy Infrastructure Information). Nameplate is used as the interconnection-capacity proxy, consistent with the paper. The enabling mechanism is surplus interconnection service; PJM has an SIS process (verify current PJM SIS rules live — they are moving in 2024–2026).
- **No storage, dispatch, LCOE, or emissions.** This screen answers "is the land physically there," nothing more.
- **Fixed-tilt assumed** to match the paper. Single-axis tracking would raise CF and lower R, expanding the qualifying set — offer as a variant.
- **Exclusion rules are conservative toggles.** Excluding all forest is aggressive; expose it as a switch and report sensitivity.

---

## 13. Suggested repo structure

```
pjm-datacenter-solar/
  README.md                      # goal, params, caveats, data vintages
  SPEC.md                        # this file
  config/                        # reV, SAM, exclusion configs (committed)
  data/
    raw/                         # EIA, NLCD, DEM, PAD-US, NSRDB cache
    interim/                     # pjm_gas_plants.csv
    processed/                   # exclusions.h5, supply_curve, plants_with_land
  src/
    01_extract_plants.py
    02_build_exclusions.py
    03_run_rev_gen.py
    04_run_rev_agg.py
    05_buffer_aggregate.py
    06_qualify.py
    07_map.py
    08_flags.py                  # optional
  outputs/
    pjm_sites.csv
    pjm_map.html
    summary.md
```

---

## 14. Build order / checklist

1. [ ] Env + reV/rex install; confirm HSDS query works with `NREL_API_KEY`.
2. [ ] Phase 1 — PJM gas fleet table (validate names against §11 list).
3. [ ] Phase 2 — exclusions.h5 (start with water/wetland/developed/slope/protected).
4. [ ] Phase 3 — reV generation → per-site CF.
5. [ ] Phase 4 — reV aggregation → developable MW/area per supply-curve point.
6. [ ] Phase 5 — buffer-and-sum per plant (10 km, then 5 km).
7. [ ] Phase 6 — qualification table (3 gas caps × 2 buffers × power-density band).
8. [ ] Phase 7 — map + summary; validate roll-up vs §11.
9. [ ] Phase 8 — optional fiber/water flags.
10. [ ] README with caveats and exact data vintages.

Start at step 1 and do not skip the §11 validation after step 8 — an unchecked exclusion or BA-filter error silently produces a plausible-looking but wrong map.
