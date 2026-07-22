"""
Phase 4 -- Supply-curve aggregation (developable capacity/area per supply-curve point).

Spec-literal intent: reV supply-curve-aggregation over a PJM exclusions .h5. We reproduce
its output directly from the per-plant developable masks (Phase 2): tile each plant's mask
into coarse supply-curve cells and, per cell, report centroid, developable area, capacity
(= area x power density), and mean CF. This yields the same per-supply-curve-point table
reV would, on the same 30 m exclusion basis, without an HSDS-aligned .h5.

Note: the authoritative per-plant buffer totals are computed pixel-exact in Phase 5; this
file provides the supply-curve deliverable (Spec section 9) and feeds the map.

Output: data/processed/pjm_supply_curve.csv
Run:    python src/04_run_rev_agg.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

CELL_M = 990.0  # supply-curve resolution: 33 x 33 NLCD pixels ~ 1 km cell
PX_KM2 = (C.EXCL_PIXEL_M / 1000.0) ** 2
_TR_TO_4326 = Transformer.from_crs(C.CRS_EQUAL_AREA, C.CRS_GEOGRAPHIC, always_xy=True)


def cells_for_plant(mask_path: Path, code: int, cf: float) -> pd.DataFrame:
    with rasterio.open(mask_path) as ds:
        dev = ds.read(1).astype("uint8")
        t = ds.transform
        h, w = dev.shape
    step = int(round(CELL_M / C.EXCL_PIXEL_M))  # pixels per cell edge
    recs = []
    for r0 in range(0, h, step):
        for c0 in range(0, w, step):
            block = dev[r0:r0 + step, c0:c0 + step]
            ndev = int(block.sum())
            if ndev == 0:
                continue
            area = ndev * PX_KM2
            # cell centroid in 5070 -> 4326
            cx = t.c + (c0 + block.shape[1] / 2.0) * t.a
            cy = t.f + (r0 + block.shape[0] / 2.0) * t.e
            lon, lat = _TR_TO_4326.transform(cx, cy)
            recs.append({
                "plant_code": code, "x_5070": cx, "y_5070": cy,
                "lon": lon, "lat": lat,
                "area_developable_km2": area,
                "capacity_MW": area * C.POWER_DENSITY_MW_PER_KM2,
                "mean_cf": cf,
            })
    return pd.DataFrame(recs)


def main() -> None:
    plants = pd.read_csv(C.DATA_INTERIM / "pjm_plants_cf.csv")
    frames = []
    for r in plants.itertuples(index=False):
        mp = C.EXCL_DIR / f"plant_{int(r.plant_code)}.tif"
        if not mp.exists():
            continue
        frames.append(cells_for_plant(mp, int(r.plant_code), float(r.cf_ac)))
    sc = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    out_path = C.DATA_PROCESSED / "pjm_supply_curve.csv"
    sc.to_csv(out_path, index=False)
    print(f"Wrote {out_path}: {len(sc):,} supply-curve cells across "
          f"{sc.plant_code.nunique() if len(sc) else 0} plants")
    if len(sc):
        print(f"  total developable capacity (cell sum, incl. overlap): "
              f"{sc.capacity_MW.sum()/1000:,.1f} GW")


if __name__ == "__main__":
    main()
