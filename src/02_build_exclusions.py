"""
Phase 2 -- Developable-land exclusion mask, per plant.

Spec-literal intent: one PJM-wide 30 m exclusion HDF5 for reVX. Because buffers are only
10 km, we instead build a per-plant developable mask over a 24 km box around each plant
(covers the 10 km buffer + margin) at NLCD's native 30 m / EPSG:5070 grid. Identical
exclusion logic, orders of magnitude less data, and no reVX HSDS-aligned .h5 needed.

Layers (Spec section 7, all toggleable in config):
  * NLCD 2021 (MRLC WCS)        -> exclude water/ice, developed, wetlands, forest(default)
  * Slope from 3DEP DEM         -> exclude slope > SLOPE_MAX_PCT
  * PAD-US GAP status polygons  -> exclude managed/protected land (GAP 1,2,3)

Output per plant: data/processed/exclusions/plant_<code>.tif  (uint8: 1=developable, 0=excluded)
        plus a summary row appended to data/processed/exclusion_summary.csv
Run:    python src/02_build_exclusions.py            # all plants (idempotent/cached)
        python src/02_build_exclusions.py 62949      # one plant code (debug)
"""
from __future__ import annotations

import io
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

import json  # noqa: E402

_TR_TO_5070 = Transformer.from_crs(C.CRS_GEOGRAPHIC, C.CRS_EQUAL_AREA, always_xy=True)


def _http_get(url: str, timeout: int = 90, retries: int = 4) -> bytes:
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return r.read()
        except Exception:  # noqa: BLE001
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


def fetch_nlcd(xmin, ymin, xmax, ymax) -> tuple[np.ndarray, rasterio.Affine, dict]:
    """NLCD 2021 clip in EPSG:5070. Returns (array, transform, profile)."""
    q = {
        "service": "WCS", "version": "2.0.1", "request": "GetCoverage",
        "coverageId": C.NLCD_COVERAGE, "format": "image/geotiff",
        "subset": [f"X({xmin},{xmax})", f"Y({ymin},{ymax})"],
    }
    data = _http_get(C.NLCD_WCS + "?" + urllib.parse.urlencode(q, doseq=True))
    with rasterio.open(io.BytesIO(data)) as ds:
        arr = ds.read(1)
        return arr, ds.transform, ds.profile.copy()


def fetch_slope(transform, shape) -> np.ndarray:
    """Slope (%) on the NLCD grid, from 3DEP elevation exportImage aligned to it."""
    h, w = shape
    xmin = transform.c
    ymax = transform.f
    xmax = xmin + w * C.EXCL_PIXEL_M
    ymin = ymax - h * C.EXCL_PIXEL_M
    params = dict(
        bbox=f"{xmin},{ymin},{xmax},{ymax}", bboxSR=5070, imageSR=5070,
        size=f"{w},{h}", format="tiff", pixelType="F32",
        interpolation="RSP_BilinearInterpolation", f="image",
    )
    data = _http_get(C.DEM_IMAGESERVER + "/exportImage?" + urllib.parse.urlencode(params))
    with rasterio.open(io.BytesIO(data)) as ds:
        dem = ds.read(1, out_shape=(h, w)).astype("float32")
    dem[dem < -1e4] = np.nan
    gy, gx = np.gradient(dem, C.EXCL_PIXEL_M, C.EXCL_PIXEL_M)
    slope = np.hypot(gx, gy) * 100.0        # rise/run -> percent
    return np.nan_to_num(slope, nan=999.0)  # NaN (no data) -> treated as steep/excluded


def fetch_padus_mask(transform, shape, xmin, ymin, xmax, ymax) -> np.ndarray:
    """Boolean mask (True = protected) rasterized onto the NLCD grid."""
    q = dict(
        where="1=1", geometry=f"{xmin},{ymin},{xmax},{ymax}",
        geometryType="esriGeometryEnvelope", inSR=5070, outSR=5070,
        spatialRel="esriSpatialRelIntersects", outFields="GAP_Sts",
        returnGeometry="true", f="geojson",
    )
    try:
        raw = _http_get(C.PADUS_SERVICE + "/query?" + urllib.parse.urlencode(q), timeout=90)
        gj = json.loads(raw.decode())
    except Exception as e:  # noqa: BLE001
        print(f"    [warn] PAD-US fetch failed ({e!r}); treating box as unprotected")
        return np.zeros(shape, dtype=bool)
    shapes = []
    for feat in gj.get("features", []):
        gap = str(feat.get("properties", {}).get("GAP_Sts", "")).strip()
        if C.PADUS_GAP_EXCLUDE and gap and gap not in C.PADUS_GAP_EXCLUDE:
            continue
        geom = feat.get("geometry")
        if geom:
            shapes.append((geom, 1))
    if not shapes:
        return np.zeros(shape, dtype=bool)
    burned = rasterize(shapes, out_shape=shape, transform=transform,
                       fill=0, default_value=1, dtype="uint8")
    return burned.astype(bool)


def build_plant_mask(code: int, lat: float, lon: float, force: bool = False) -> dict:
    """Write a 2-band developable mask: band 1 = forest EXCLUDED (conservative default),
    band 2 = forest INCLUDED (less aggressive). Enables the forest sensitivity (Spec §12)."""
    out_tif = C.EXCL_DIR / f"plant_{code}.tif"
    px_km2 = (C.EXCL_PIXEL_M / 1000.0) ** 2
    if out_tif.exists() and not force:
        with rasterio.open(out_tif) as ds:
            if ds.count >= 2:
                dev = ds.read(1)
                return {"plant_code": code, "cached": True,
                        "developable_km2_box": float(dev.sum()) * px_km2}

    x, y = _TR_TO_5070.transform(lon, lat)
    h = C.EXCL_BOX_HALF_M
    xmin, xmax, ymin, ymax = x - h, x + h, y - h, y + h

    nlcd, transform, profile = fetch_nlcd(xmin, ymin, xmax, ymax)
    shape = nlcd.shape
    axmin, aymax = transform.c, transform.f
    axmax = axmin + shape[1] * C.EXCL_PIXEL_M
    aymin = aymax - shape[0] * C.EXCL_PIXEL_M

    slope = fetch_slope(transform, shape)
    protected = fetch_padus_mask(transform, shape, axmin, aymin, axmax, aymax)

    excl_common = (np.isin(nlcd, list(C.NLCD_EXCLUDE_ALWAYS))
                   | (slope > C.SLOPE_MAX_PCT) | protected | (nlcd == 0))
    forest = np.isin(nlcd, list(C.NLCD_FOREST))
    dev_excl_forest = (~(excl_common | forest)).astype("uint8")   # band 1
    dev_incl_forest = (~excl_common).astype("uint8")              # band 2

    prof = profile
    prof.update(dtype="uint8", count=2, nodata=0, compress="lzw")
    with rasterio.open(out_tif, "w", **prof) as ds:
        ds.write(dev_excl_forest, 1)
        ds.write(dev_incl_forest, 2)
        ds.update_tags(1, layer="developable_forest_excluded")
        ds.update_tags(2, layer="developable_forest_included")

    return {
        "plant_code": code, "cached": False,
        "developable_km2_box": float(dev_excl_forest.sum()) * px_km2,
        "developable_km2_box_incl_forest": float(dev_incl_forest.sum()) * px_km2,
        "frac_excl_slope": float((slope > C.SLOPE_MAX_PCT).mean()),
        "frac_excl_protected": float(protected.mean()),
        "frac_forest": float(forest.mean()),
    }


def _worker(args):
    i, n, code, name, state, lat, lon, force = args
    try:
        info = build_plant_mask(code, lat, lon, force=force)
    except Exception as e:  # noqa: BLE001
        info = {"plant_code": code, "error": repr(e)}
    info["name"], info["state"] = name, state
    dev = info.get("developable_km2_box")
    tag = "cache" if info.get("cached") else ("ERR " if "error" in info else "built")
    msg = (f"  [{i+1}/{n}] {tag} {code} {name[:28]:<28} dev={dev:.1f} km2"
           if dev is not None else f"  [{i+1}/{n}] {tag} {code} {name[:28]} {info.get('error','')[:40]}")
    return info, msg


def main() -> None:
    from concurrent.futures import ThreadPoolExecutor

    force = "--force" in sys.argv
    argv = [a for a in sys.argv[1:] if a != "--force"]
    plants = pd.read_csv(C.DATA_INTERIM / "pjm_plants_cf.csv")
    if argv:
        codes = {int(a) for a in argv}
        plants = plants[plants.plant_code.isin(codes)]

    n = len(plants)
    tasks = [(i, n, int(r.plant_code), r.name, r.state, float(r.lat), float(r.lon), force)
             for i, r in enumerate(plants.itertuples(index=False))]
    rows = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=8) as ex:
        for info, msg in ex.map(_worker, tasks):
            rows.append(info)
            print(msg)
            sys.stdout.flush()

    summ = pd.DataFrame(rows)
    summ_path = C.DATA_PROCESSED / "exclusion_summary.csv"
    summ.to_csv(summ_path, index=False)
    ok = summ["developable_km2_box"].notna().sum() if "developable_km2_box" in summ else 0
    print(f"\nWrote {summ_path}. Built/loaded {ok}/{len(summ)} plant masks "
          f"in {time.time()-t0:.0f}s. Masks -> {C.EXCL_DIR}")


if __name__ == "__main__":
    main()
