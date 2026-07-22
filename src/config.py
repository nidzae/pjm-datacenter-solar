"""
Shared configuration and locked parameters for the PJM gas-plant / solar / data-center land screen.

Every constant here is auditable and traceable to the build spec
(PJM_datacenter_solar_screen_SPEC.md, sections 3 and 4). Change values HERE, not inline
in the phase scripts, so the whole screen stays reproducible.
"""
from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
DATA_INTERIM = ROOT / "data" / "interim"
DATA_PROCESSED = ROOT / "data" / "processed"
CONFIG_DIR = ROOT / "config"
OUTPUTS = ROOT / "outputs"
for _p in (DATA_RAW, DATA_INTERIM, DATA_PROCESSED, CONFIG_DIR, OUTPUTS):
    _p.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------------------
# Data vintages (record exactly what was used; see README)
# --------------------------------------------------------------------------------------
EIA860_VINTAGE = 2024          # latest annual EIA-860 vintage available at build time
EIA860_ZIP_URL = "https://www.eia.gov/electricity/data/eia860/xls/eia8602024.zip"

# --------------------------------------------------------------------------------------
# Region filter (Spec section 4)
# --------------------------------------------------------------------------------------
REGION_BA_CODE = "PJM"          # EIA Balancing Authority Code

# PJM footprint bounding box (lon/lat, EPSG:4326) for NSRDB / exclusion extent.
# Generous box covering PJM states (IL/IN/OH/KY/WV/VA/NC-tip/MD/DE/NJ/PA/MI-lp/DC/TN-tip).
# Refined to the actual plant convex hull + buffer at runtime in Phase 5.
PJM_BBOX_4326 = (-91.5, 33.5, -73.5, 42.5)   # (min_lon, min_lat, max_lon, max_lat)

# --------------------------------------------------------------------------------------
# Prime-mover classification (Spec section 7, Phase 1) -- the known EIA gotcha.
# EIA code 'CT' is a COMBINED-CYCLE combustion-turbine component, NOT the paper's "CT" peaker.
# --------------------------------------------------------------------------------------
ENERGY_SOURCE_GAS = "NG"                        # Energy Source 1 == natural gas
STATUS_OPERATING = "OP"                          # Status == operating
PRIME_MOVERS_PEAKER = {"GT"}                     # simple-cycle peaker (paper's "CT")
PRIME_MOVERS_CCGT = {"CT", "CA", "CS", "CC"}     # combined cycle (paper's "CCGT")
PRIME_MOVERS_ALL = PRIME_MOVERS_PEAKER | PRIME_MOVERS_CCGT

# --------------------------------------------------------------------------------------
# Qualification math (Spec section 3)
# --------------------------------------------------------------------------------------
GAS_CAPS = (0.05, 0.10, 0.20)     # fraction of annual DC energy gas may supply; run all three
OVERBUILD = 1.3                    # required conservative multiplier (battery losses + low-sun ride-through)

# Power density: derived from a land-use assumption so it is auditable.
# power_density [MW/km2] = 1 / (acres_per_MW * km2_per_acre)
KM2_PER_ACRE = 0.00404686
ACRES_PER_MW = 7.0                 # fixed-tilt utility PV total-area, NREL ballpark (range 5-8)
POWER_DENSITY_MW_PER_KM2 = 1.0 / (ACRES_PER_MW * KM2_PER_ACRE)   # ~= 35.3 MW/km2

# Sensitivity band on acres/MW -> power density (Spec section 3)
ACRES_PER_MW_SENSITIVITY = (5.0, 7.0, 8.0)     # -> ~49.4, ~35.3, ~30.9 MW/km2

def power_density(acres_per_mw: float = ACRES_PER_MW) -> float:
    """MW/km2 for a given acres/MW land-use assumption."""
    return 1.0 / (acres_per_mw * KM2_PER_ACRE)

# Data-center parcel reserved out of developable land before the area test.
DC_LAND_ACRES = 150.0
DC_LAND_KM2 = DC_LAND_ACRES * KM2_PER_ACRE

# Regional sanity anchor for CF (Spec section 4); reV computes per-site value, this is only a check.
CF_REGIONAL_SANITY = 0.16

# --------------------------------------------------------------------------------------
# Exclusion screen (Spec section 7, Phase 2) -- all rules toggleable.
# --------------------------------------------------------------------------------------
# Per-plant fetch box half-width (m) in EPSG:5070: must exceed the largest buffer (10 km)
# with margin so the buffer circle is fully covered.
EXCL_BOX_HALF_M = 12000.0
EXCL_PIXEL_M = 30.0               # NLCD native resolution

# NLCD land-cover classes.
NLCD_EXCLUDE_ALWAYS = {
    11, 12,          # open water, perennial ice/snow
    21, 22, 23, 24,  # developed (all intensities)
    90, 95,          # woody + emergent herbaceous wetlands
}
NLCD_FOREST = {41, 42, 43}        # deciduous/evergreen/mixed forest -- excluded by default (toggle)
NLCD_DEVELOPABLE = {31, 51, 52, 71, 72, 73, 74, 81, 82}  # barren/shrub/herbaceous/pasture/crops

EXCLUDE_FOREST = True             # conservative default; expose as switch (Spec sections 7, 12)
SLOPE_MAX_PCT = 10.0              # exclude slope > this; test 5.0 (Spec section 7)
SLOPE_MAX_PCT_SENSITIVITY = 5.0

# PAD-US GAP status codes to exclude (1,2 = strict; 3 = multiple-use managed; 4 = unprotected).
# Conservative default excludes managed protected lands (1,2,3).
PADUS_GAP_EXCLUDE = {"1", "2", "3"}
PADUS_SERVICE = (
    "https://services.arcgis.com/v01gqwM5QqNysAAi/arcgis/rest/services/"
    "PADUS_Protection_Status_by_GAP_Status_Code/FeatureServer/0"
)
NLCD_WCS = "https://www.mrlc.gov/geoserver/wcs"
NLCD_COVERAGE = "mrlc_download__NLCD_2021_Land_Cover_L48"
NLCD_VINTAGE = 2021
DEM_IMAGESERVER = (
    "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer"
)

EXCL_DIR = DATA_PROCESSED / "exclusions"   # per-plant developable-mask GeoTIFFs
EXCL_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------------------
# Buffer radii (Spec section 4)
# --------------------------------------------------------------------------------------
BUFFER_KM_PRIMARY = 10.0
BUFFER_KM_SENSITIVITY = 5.0
BUFFERS_KM = (BUFFER_KM_PRIMARY, BUFFER_KM_SENSITIVITY)

# --------------------------------------------------------------------------------------
# Projections (Spec section 6)
# --------------------------------------------------------------------------------------
CRS_GEOGRAPHIC = "EPSG:4326"      # report lat/lon in this
CRS_EQUAL_AREA = "EPSG:5070"      # US Albers Equal Area: ALL distance/area math in this

# --------------------------------------------------------------------------------------
# Solar geometry / SAM PVWatts (Spec section 4 & 7 Phase 3)
# --------------------------------------------------------------------------------------
SAM_ARRAY_TYPE = 0                # 0 = fixed open rack
SAM_AZIMUTH = 180                 # due south
SAM_DC_AC_RATIO = 1.3
SAM_LOSSES_PCT = 14.0             # standard; set 0 to replicate paper's zero-loss-then-apply
SAM_TILT_MODE = "latitude"        # tilt = site latitude per §4
SAM_MODULE_TYPE = 0               # standard
# tilt is set per-site = latitude at runtime.

# NSRDB study years (Spec section 4). Multi-year if compute allows, else a single TMY.
NSRDB_YEARS = tuple(range(2016, 2024))   # 2016-2023 inclusive
NSRDB_TMY_YEAR = "tmy"                     # fallback single-year label

# --------------------------------------------------------------------------------------
# NREL API / HSDS (domain migrated developer.nrel.gov -> developer.nlr.gov, retired 2026-05-29)
# --------------------------------------------------------------------------------------
NREL_HSDS_ENDPOINT = "https://developer.nlr.gov/api/hsds"
NREL_API_BASE = "https://developer.nlr.gov/api"


def nrel_api_key() -> str | None:
    """Resolve the NREL API key from env, then ~/.hscfg."""
    key = os.environ.get("NREL_API_KEY")
    if key:
        return key.strip()
    hscfg = Path.home() / ".hscfg"
    if hscfg.exists():
        for line in hscfg.read_text().splitlines():
            if line.strip().startswith("hs_api_key"):
                return line.split("=", 1)[1].strip()
    return None
