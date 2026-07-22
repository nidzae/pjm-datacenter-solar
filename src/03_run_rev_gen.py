"""
Phase 3 -- Solar generation + capacity factor per plant.

Spec-literal intent: run reV generation (SAM PVWatts) over the PJM NSRDB resource for a
per-site AC capacity factor. On a throttled developer HSDS key, full-grid reV gen is
intractable (2M+ NSRDB points, ~90s per HSDS meta op, 1000 req/hr). We instead evaluate
the SAME SAM PVWatts engine (NREL-hosted, against NSRDB TMY at each coordinate) at each
plant location. Geometry matches Spec section 4 / Phase 3:
    array_type=0 (fixed open rack), tilt=latitude, azimuth=180, dc_ac_ratio=1.3, losses=14%.

CF definition: AC capacity factor = AC_energy / (AC_nameplate * 8760).
PVWatts reports capacity_factor on the DC nameplate, so
    AC_CF = reported_CF * dc_ac_ratio   (exact algebra; consistent with R in Spec section 3).

Output: data/interim/pjm_plants_cf.csv  (adds cf_ac per plant)
Run:    python src/03_run_rev_gen.py
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

PVWATTS_URL = C.NREL_API_BASE + "/pvwatts/v8.json"
CACHE = C.DATA_INTERIM / "pvwatts_cache.json"


def _load_cache() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text())
    return {}


def pvwatts_cf(lat: float, lon: float, tilt: float, key: str,
               cache: dict, retries: int = 4) -> dict:
    """Return dict with dc_cf, ac_cf, ac_annual_kwh for a site (cached)."""
    ckey = f"{lat:.4f},{lon:.4f},{tilt:.2f}"
    if ckey in cache:
        return cache[ckey]
    q = dict(
        api_key=key, system_capacity=1000.0, module_type=C.SAM_MODULE_TYPE,
        losses=C.SAM_LOSSES_PCT, array_type=C.SAM_ARRAY_TYPE, tilt=tilt,
        azimuth=C.SAM_AZIMUTH, dc_ac_ratio=C.SAM_DC_AC_RATIO, lat=lat, lon=lon,
        timeframe="hourly",
    )
    url = PVWATTS_URL + "?" + urllib.parse.urlencode(q)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                d = json.load(r)
            errs = d.get("errors") or []
            if errs:
                raise RuntimeError(f"PVWatts errors: {errs}")
            o = d["outputs"]
            dc_cf = o["capacity_factor"] / 100.0
            rec = {
                "dc_cf": dc_cf,
                "ac_cf": dc_cf * C.SAM_DC_AC_RATIO,
                "ac_annual_kwh": o["ac_annual"],
                "solrad_annual": o.get("solrad_annual"),
            }
            cache[ckey] = rec
            return rec
        except Exception as e:  # noqa: BLE001
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


def main() -> None:
    key = C.nrel_api_key()
    if not key:
        raise SystemExit("No NREL API key found (env NREL_API_KEY or ~/.hscfg).")

    plants = pd.read_csv(C.DATA_INTERIM / "pjm_gas_plants.csv")
    cache = _load_cache()
    recs = []
    t0 = time.time()
    for i, row in plants.iterrows():
        r = pvwatts_cf(row.lat, row.lon, row.lat, key, cache)
        recs.append(r)
        if (i + 1) % 25 == 0:
            CACHE.write_text(json.dumps(cache))
            print(f"  {i+1}/{len(plants)} plants  ({time.time()-t0:.0f}s)")
        time.sleep(0.15)  # polite pacing under 1000 req/hr
    CACHE.write_text(json.dumps(cache))

    cf = pd.DataFrame(recs)
    plants["cf_ac"] = cf["ac_cf"].values
    plants["cf_dc"] = cf["dc_cf"].values
    out_path = C.DATA_INTERIM / "pjm_plants_cf.csv"
    plants.to_csv(out_path, index=False)

    print(f"\nWrote {out_path}")
    print(f"AC capacity factor across {len(plants)} PJM plants:")
    print(f"  min {plants.cf_ac.min():.3f}  mean {plants.cf_ac.mean():.3f}  "
          f"max {plants.cf_ac.max():.3f}  (spec sanity ~{C.CF_REGIONAL_SANITY})")
    print("  by state (mean AC CF):")
    print((plants.groupby('state').cf_ac.mean().round(3)).sort_values(ascending=False).to_string())


if __name__ == "__main__":
    main()
