"""
Phase 5 -- Per-plant buffer aggregation (the plant-centric custom step).

For each plant, read its developable mask (Phase 2), and sum developable land within a
10 km (primary) and 5 km (sensitivity) radius of the plant. Capacity = developable area x
power density. CF_p is the per-plant AC capacity factor from Phase 3 (constant over the
small buffer; area-weighting is a no-op at this resolution).

Masks are pixel-exact (30 m) and centered on the plant, so the buffer is simply the set of
developable pixels whose centroid lies within R of the plant point.

Output: data/processed/pjm_plants_with_land.csv
        adds developable_area_km2 and developable_MW at 10 km and 5 km.
Run:    python src/05_buffer_aggregate.py
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

_TR = Transformer.from_crs(C.CRS_GEOGRAPHIC, C.CRS_EQUAL_AREA, always_xy=True)
PX_KM2 = (C.EXCL_PIXEL_M / 1000.0) ** 2


def developable_area_within(mask_path: Path, lat: float, lon: float,
                            radius_km: float) -> dict[str, float]:
    """km2 of developable land within radius_km, for both mask bands.
    band 1 = forest excluded (conservative), band 2 = forest included."""
    px, py = _TR.transform(lon, lat)
    with rasterio.open(mask_path) as ds:
        b1 = ds.read(1).astype(bool)
        b2 = ds.read(2).astype(bool) if ds.count >= 2 else b1
        t = ds.transform
        h, w = b1.shape
    xs = t.c + (np.arange(w) + 0.5) * t.a
    ys = t.f + (np.arange(h) + 0.5) * t.e
    dx = xs[None, :] - px
    dy = ys[:, None] - py
    within = (dx * dx + dy * dy) <= (radius_km * 1000.0) ** 2
    return {
        "excl_forest": float((b1 & within).sum()) * PX_KM2,
        "incl_forest": float((b2 & within).sum()) * PX_KM2,
    }


def main() -> None:
    plants = pd.read_csv(C.DATA_INTERIM / "pjm_plants_cf.csv")
    rows = []
    for r in plants.itertuples(index=False):
        mp = C.EXCL_DIR / f"plant_{int(r.plant_code)}.tif"
        rec = {"plant_code": int(r.plant_code)}
        if not mp.exists():
            rec["mask_missing"] = True
            for b in C.BUFFERS_KM:
                for fk in ("excl_forest", "incl_forest"):
                    rec[f"developable_area_km2_{int(b)}km_{fk}"] = np.nan
                    rec[f"developable_MW_{int(b)}km_{fk}"] = np.nan
        else:
            for b in C.BUFFERS_KM:
                areas = developable_area_within(mp, r.lat, r.lon, b)
                for fk, area in areas.items():
                    rec[f"developable_area_km2_{int(b)}km_{fk}"] = area
                    rec[f"developable_MW_{int(b)}km_{fk}"] = area * C.POWER_DENSITY_MW_PER_KM2
        rows.append(rec)

    land = pd.DataFrame(rows)
    out = plants.merge(land, on="plant_code", how="left")
    out_path = C.DATA_PROCESSED / "pjm_plants_with_land.csv"
    out.to_csv(out_path, index=False)

    b = int(C.BUFFER_KM_PRIMARY)
    col_x = f"developable_MW_{b}km_excl_forest"
    col_i = f"developable_MW_{b}km_incl_forest"
    have = out[col_x].notna().sum()
    print(f"Wrote {out_path}  ({have}/{len(out)} plants with masks)")
    print(f"Developable capacity within {b} km (MW), forest EXCLUDED:  "
          f"median {out[col_x].median():,.0f}   max {out[col_x].max():,.0f}")
    print(f"Developable capacity within {b} km (MW), forest INCLUDED:  "
          f"median {out[col_i].median():,.0f}   max {out[col_i].max():,.0f}")


if __name__ == "__main__":
    main()
