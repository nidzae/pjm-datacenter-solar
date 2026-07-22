"""
Phase 8 (OPTIONAL) -- fiber / water context flags.

CRITICAL FRAMING (Spec section 10): open data establishes PRESENCE, never available
capacity for a new load. A nearby fiber route or unstressed basin does NOT prove surplus
fiber or surplus water exists for a new data center. So these are appended as ranking
*flags only* and qualification (Phase 6) never depends on them.

Implemented here (no-auth, tractable):
  * dist_to_water_km   -- distance from the plant to the nearest NHD surface-water feature
                          (USGS NHD MapServer). Presence proxy only.
Documented-but-deferred (need registration / heavy downloads; add later as flags):
  * fiber_longhaul_km  -- InterTubes (IMPACT Cyber Trust dataset 521, login required)
  * fcc_broadband      -- FCC National Broadband Map service-availability proxy
  * water_stress_cat   -- WRI Aqueduct 4.0 basin category (GEE / shapefile)

Output: outputs/pjm_sites_flags.csv  (pjm_sites.csv + flag columns)
Run:    python src/08_flags.py
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

# USGS NHD (National Hydrography Dataset) MapServer — public, no auth.
NHD_SERVICE = "https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer"
NHD_WATERBODY_LAYER = 10  # NHDWaterbody (lakes/ponds/reservoirs) in the published NHD service


def nearest_water_km(lat: float, lon: float, search_km: float = 15.0) -> float | None:
    """Distance (km) to nearest NHD waterbody within search_km, else None."""
    q = dict(
        geometry=f"{lon},{lat}", geometryType="esriGeometryPoint", inSR=4326,
        distance=search_km * 1000.0, units="esriSRUnit_Meter",
        spatialRel="esriSpatialRelIntersects", returnGeometry="true",
        outSR=5070, outFields="OBJECTID", f="geojson",
    )
    url = f"{NHD_SERVICE}/{NHD_WATERBODY_LAYER}/query?" + urllib.parse.urlencode(q)
    try:
        raw = urllib.request.urlopen(url, timeout=45).read()
        gj = json.loads(raw.decode())
    except Exception:  # noqa: BLE001
        return None
    from pyproj import Transformer
    from shapely.geometry import shape, Point
    tr = Transformer.from_crs(4326, 5070, always_xy=True)
    px, py = tr.transform(lon, lat)
    pt = Point(px, py)
    best = None
    for feat in gj.get("features", []):
        try:
            d = shape(feat["geometry"]).distance(pt) / 1000.0
        except Exception:  # noqa: BLE001
            continue
        best = d if best is None else min(best, d)
    return best


def main() -> None:
    sites = pd.read_csv(C.OUTPUTS / "pjm_sites.csv")
    dists = []
    for i, r in enumerate(sites.itertuples(index=False)):
        dists.append(nearest_water_km(r.lat, r.lon))
        time.sleep(0.1)
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(sites)} water-distance flags")
    sites["dist_to_water_km"] = dists
    # documented-deferred flags (never gate qualification)
    sites["fiber_longhaul_km"] = pd.NA
    sites["fcc_broadband"] = pd.NA
    sites["water_stress_cat"] = pd.NA
    out = C.OUTPUTS / "pjm_sites_flags.csv"
    sites.to_csv(out, index=False)
    got = sites["dist_to_water_km"].notna().sum()
    print(f"Wrote {out}. Nearest-water flag populated for {got}/{len(sites)} plants "
          f"(flags are presence-only and do NOT affect qualification).")


if __name__ == "__main__":
    main()
