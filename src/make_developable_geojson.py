"""
Helper for Phase 7 map: vectorize each plant's developable solar land within the 10 km
buffer into a HIGH-FIDELITY per-plant GeoJSON "tile", for the click-to-hatch overlay.

Full 30 m resolution with interior holes preserved, so lakes / developed parcels / roads
(anything excluded in the mask) show as gaps in the hatch -- not filled over. A light
simplify (45 m) removes pixel stair-steps without distorting or filling exclusions.

Tiles are loaded on demand by the map (one plant per click), so total footprint on disk is
fine even though the full set would be ~50 MB embedded.

band 1 = developable forest-EXCLUDED (default). Pass --incl-forest for band 2.

Outputs:
  outputs/dev_tiles/plant_<code>.js   -- each calls  DEVCB(<code>, <GeoJSON geometry>)
  outputs/dev_tiles/manifest.json     -- list of plant codes that have a tile
Run:  python src/make_developable_geojson.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape, mapping, Point
from shapely.ops import transform as shp_transform, unary_union
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

SIMPLIFY_M = 45.0    # smooth 30 m pixel stair-steps; small enough to keep roads/ponds as holes
MIN_KM2 = 0.02       # drop developable slivers smaller than ~2 ha
NDIG = 5             # ~1 m coordinate precision (keeps hole boundaries crisp)
TILE_DIR = C.OUTPUTS / "dev_tiles"

_to5070 = Transformer.from_crs(C.CRS_GEOGRAPHIC, C.CRS_EQUAL_AREA, always_xy=True)
_to4326 = Transformer.from_crs(C.CRS_EQUAL_AREA, C.CRS_GEOGRAPHIC, always_xy=True)


def _round(o, nd=NDIG):
    if isinstance(o, (list, tuple)):
        if o and isinstance(o[0], (int, float)):
            return [round(o[0], nd), round(o[1], nd)]
        return [_round(x, nd) for x in o]
    return o


def vectorize(code: int, lat: float, lon: float, band: int = 1,
              radius_km: float = C.BUFFER_KM_PRIMARY):
    mp = C.EXCL_DIR / f"plant_{code}.tif"
    with rasterio.open(mp) as ds:
        arr = ds.read(band)
        t = ds.transform
    polys = [shape(g) for g, v in shapes(arr, mask=(arr == 1), transform=t) if v == 1]
    if not polys:
        return None
    dev = unary_union(polys)                       # holes (lakes/developed) preserved natively
    px, py = _to5070.transform(lon, lat)
    dev = dev.intersection(Point(px, py).buffer(radius_km * 1000.0))
    if SIMPLIFY_M:
        dev = dev.simplify(SIMPLIFY_M)             # keeps holes; only removes stair-steps
    geoms = [dev] if dev.geom_type == "Polygon" else list(getattr(dev, "geoms", []))
    geoms = [g for g in geoms if g.area >= MIN_KM2 * 1e6]
    if not geoms:
        return None
    dev = unary_union(geoms).buffer(0)
    if dev.is_empty:
        return None
    dev4326 = shp_transform(lambda x, y, z=None: _to4326.transform(x, y), dev)
    gj = mapping(dev4326)
    gj["coordinates"] = _round(gj["coordinates"])
    return gj


def main() -> None:
    band = 2 if "--incl-forest" in sys.argv else 1
    TILE_DIR.mkdir(parents=True, exist_ok=True)
    for f in TILE_DIR.glob("plant_*.js"):
        f.unlink()
    plants = pd.read_csv(C.DATA_INTERIM / "pjm_plants_cf.csv")
    have = []
    total_bytes = 0
    for i, r in enumerate(plants.itertuples(index=False)):
        code = int(r.plant_code)
        try:
            gj = vectorize(code, float(r.lat), float(r.lon), band=band)
        except Exception as e:  # noqa: BLE001
            print(f"  [warn] {code} {r.name}: {e!r}")
            gj = None
        if gj is not None:
            payload = f"DEVCB({code},{json.dumps(gj, separators=(',', ':'))});\n"
            (TILE_DIR / f"plant_{code}.js").write_text(payload)
            have.append(code)
            total_bytes += len(payload)
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(plants)}")
    (TILE_DIR / "manifest.json").write_text(json.dumps(have, separators=(",", ":")))
    band_tag = "forest-included" if band == 2 else "forest-excluded"
    print(f"Wrote {len(have)} tiles ({band_tag}) to {TILE_DIR}  "
          f"[{total_bytes/1e6:.1f} MB total on disk, loaded one-per-click]")


if __name__ == "__main__":
    main()
