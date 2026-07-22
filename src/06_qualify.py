"""
Phase 6 -- Qualification test (Spec section 3).

For each plant x gas cap g x buffer x power-density sensitivity:
    R          = OVERBUILD * (1 - g) / CF_p
    solar_req  = R * nameplate_MW                       (MW-AC solar)
    land_req   = solar_req / power_density              (km2 of solar land)
    dev_MW     = developable_area * power_density        (from Phase 5)
    qualifies  = dev_MW >= solar_req AND developable_area >= land_req + dc_land
    headroom   = dev_MW / solar_req

Output: outputs/pjm_sites.csv  (long-ish: one row per plant, columns per g at primary
        buffer + primary power density, plus a qualifying_any flag; full sensitivity grid
        in outputs/pjm_sites_sensitivity.csv)
Run:    python src/06_qualify.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402


def main() -> None:
    p = pd.read_csv(C.DATA_PROCESSED / "pjm_plants_with_land.csv")

    long_rows = []
    for r in p.itertuples(index=False):
        for buf in C.BUFFERS_KM:
            for forest in ("excl_forest", "incl_forest"):
                area = getattr(r, f"developable_area_km2_{int(buf)}km_{forest}")
                if pd.isna(area):
                    continue
                for apm in C.ACRES_PER_MW_SENSITIVITY:
                    pd_mw = C.power_density(apm)
                    dev_mw = area * pd_mw
                    for g in C.GAS_CAPS:
                        R = C.OVERBUILD * (1 - g) / r.cf_ac
                        solar_req = R * r.nameplate_MW_total
                        land_req = solar_req / pd_mw
                        qual = (dev_mw >= solar_req) and (area >= land_req + C.DC_LAND_KM2)
                        long_rows.append({
                            "plant_code": r.plant_code, "name": r.name, "state": r.state,
                            "lat": r.lat, "lon": r.lon, "nameplate_MW": r.nameplate_MW_total,
                            "cf_ac": r.cf_ac, "buffer_km": buf, "forest": forest,
                            "acres_per_MW": apm, "power_density_MW_km2": pd_mw, "gas_cap": g,
                            "R": R, "solar_req_MW": solar_req, "land_req_km2": land_req,
                            "developable_area_km2": area, "developable_MW": dev_mw,
                            "qualifies": qual,
                            "headroom": dev_mw / solar_req if solar_req > 0 else np.nan,
                        })
    long = pd.DataFrame(long_rows)
    long.to_csv(C.OUTPUTS / "pjm_sites_sensitivity.csv", index=False)

    # Master table: primary buffer + primary power density + default forest setting.
    default_forest = "excl_forest" if C.EXCLUDE_FOREST else "incl_forest"
    base = long[(long.buffer_km == C.BUFFER_KM_PRIMARY) &
                (np.isclose(long.acres_per_MW, C.ACRES_PER_MW)) &
                (long.forest == default_forest)].copy()
    wide = base.pivot_table(
        index=["plant_code", "name", "state", "lat", "lon", "nameplate_MW", "cf_ac",
               "developable_area_km2", "developable_MW"],
        columns="gas_cap",
        values=["R", "solar_req_MW", "land_req_km2", "qualifies", "headroom"],
    )
    wide.columns = [f"{a}_g{int(b*100)}" for a, b in wide.columns]
    wide = wide.reset_index()
    qual_cols = [c for c in wide.columns if c.startswith("qualifies_")]
    wide["qualifying_any"] = wide[qual_cols].any(axis=1)
    wide = wide.sort_values(["qualifying_any", "nameplate_MW"], ascending=[False, False])
    wide.to_csv(C.OUTPUTS / "pjm_sites.csv", index=False)

    # ---- report ----
    print(f"Wrote outputs/pjm_sites.csv ({len(wide)} plants) and "
          f"outputs/pjm_sites_sensitivity.csv ({len(long)} rows)")
    for forest in ("excl_forest", "incl_forest"):
        tag = "forest EXCLUDED (conservative default)" if forest == "excl_forest" else "forest INCLUDED (less aggressive)"
        print(f"\nQualifying plants & hostable load (10km, 7 ac/MW) -- {tag}:")
        fsub = long[(long.buffer_km == C.BUFFER_KM_PRIMARY) &
                    (np.isclose(long.acres_per_MW, C.ACRES_PER_MW)) & (long.forest == forest)]
        for g in C.GAS_CAPS:
            sub = fsub[fsub.gas_cap == g]
            q = sub[sub.qualifies]
            print(f"  g={int(g*100):>2}% : {len(q):>3} plants qualify   "
                  f"hostable load = {q.nameplate_MW.sum()/1000:5.1f} GW "
                  f"of {sub.nameplate_MW.sum()/1000:.1f} GW fleet")


if __name__ == "__main__":
    main()
