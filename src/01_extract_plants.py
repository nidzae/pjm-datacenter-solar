"""
Phase 1 -- PJM gas-plant inventory.

Reads EIA-860 (Plant + Generator/Operable), filters to operating natural-gas combustion
units in the PJM balancing authority, classifies peaker vs CCGT precisely (the EIA 'CT'
gotcha, Spec section 7 Phase 1), and aggregates nameplate to the plant level.

Output: data/interim/pjm_gas_plants.csv
Run:    python src/01_extract_plants.py
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

EIA_DIR = C.DATA_RAW / "eia860_2024"
PLANT_XLSX = EIA_DIR / "2___Plant_Y2024.xlsx"
GEN_XLSX = EIA_DIR / "3_1_Generator_Y2024.xlsx"
EIA923_DIR = C.DATA_RAW / "eia923_2024"
EIA923_XLSX = EIA923_DIR / "EIA923_Schedules_2_3_4_5_M_12_2024_Final.xlsx"

# §11 validation anchors: named PJM plants expected in the fleet (paper Table S3).
EXPECTED_PLANTS = [
    "Aurora", "Bergen", "Bluegrass", "Chesterfield", "Doswell", "Gravel Neck",
    "Hopewell", "Ladysmith", "Marsh Run", "Moxie Freedom", "Potomac Energy Center",
    "Remington", "Kearny",
]


def _ensure_inputs() -> None:
    if PLANT_XLSX.exists() and GEN_XLSX.exists():
        return
    zip_path = C.DATA_RAW / "eia860_2024.zip"
    if not zip_path.exists():
        import requests
        print(f"Downloading EIA-860 {C.EIA860_VINTAGE} ...")
        r = requests.get(C.EIA860_ZIP_URL, timeout=300)
        r.raise_for_status()
        zip_path.write_bytes(r.content)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(EIA_DIR)


def _ensure_eia923() -> None:
    if EIA923_XLSX.exists():
        return
    zip_path = C.DATA_RAW / "eia923_2024.zip"
    if not zip_path.exists():
        import requests
        print(f"Downloading EIA-923 {C.EIA923_VINTAGE} ...")
        r = requests.get(C.EIA923_ZIP_URL, timeout=300)
        r.raise_for_status()
        zip_path.write_bytes(r.content)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(EIA923_DIR)


def load_gas_generation() -> pd.Series:
    """Per-plant 2024 natural-gas net generation (MWh) from EIA-923 Page 1, restricted to the
    same prime movers as our gas nameplate (GT/CT/CA/CS/CC) so CF = gen / (nameplate*8760) is
    apples-to-apples. Indexed by Plant Code."""
    _ensure_eia923()
    g = pd.read_excel(EIA923_XLSX, sheet_name="Page 1 Generation and Fuel Data", skiprows=5)
    g.columns = [str(c).replace("\n", " ").strip() for c in g.columns]
    g["Plant Id"] = pd.to_numeric(g["Plant Id"], errors="coerce")
    g["Reported Fuel Type Code"] = g["Reported Fuel Type Code"].astype(str).str.strip().str.upper()
    g["Reported Prime Mover"] = g["Reported Prime Mover"].astype(str).str.strip().str.upper()
    g["Net Generation (Megawatthours)"] = pd.to_numeric(
        g["Net Generation (Megawatthours)"], errors="coerce")
    m = (g["Reported Fuel Type Code"] == C.ENERGY_SOURCE_GAS) & \
        (g["Reported Prime Mover"].isin(C.PRIME_MOVERS_ALL))
    return (g.loc[m].groupby("Plant Id")["Net Generation (Megawatthours)"].sum()
            .rename("net_gen_MWh"))


def load_generators() -> pd.DataFrame:
    """Operable natural-gas combustion units in PJM-qualifying prime movers."""
    gen = pd.read_excel(GEN_XLSX, sheet_name="Operable", skiprows=1)
    gen = gen.dropna(subset=["Plant Code"])
    gen["Plant Code"] = gen["Plant Code"].astype(int)
    gen["Nameplate Capacity (MW)"] = pd.to_numeric(
        gen["Nameplate Capacity (MW)"], errors="coerce"
    )
    gen["Prime Mover"] = gen["Prime Mover"].astype(str).str.strip().str.upper()
    gen["Energy Source 1"] = gen["Energy Source 1"].astype(str).str.strip().str.upper()
    gen["Status"] = gen["Status"].astype(str).str.strip().str.upper()

    mask = (
        (gen["Energy Source 1"] == C.ENERGY_SOURCE_GAS)
        & (gen["Status"] == C.STATUS_OPERATING)
        & (gen["Prime Mover"].isin(C.PRIME_MOVERS_ALL))
    )
    gen = gen.loc[mask].copy()
    gen["class"] = np.where(
        gen["Prime Mover"].isin(C.PRIME_MOVERS_PEAKER), "peaker", "ccgt"
    )
    return gen


def load_plants() -> pd.DataFrame:
    plant = pd.read_excel(PLANT_XLSX, sheet_name="Plant", skiprows=1)
    plant = plant.dropna(subset=["Plant Code"])
    plant["Plant Code"] = plant["Plant Code"].astype(int)
    for col in ("Latitude", "Longitude"):
        plant[col] = pd.to_numeric(plant[col], errors="coerce")
    plant["Balancing Authority Code"] = (
        plant["Balancing Authority Code"].astype(str).str.strip().str.upper()
    )
    return plant[
        ["Plant Code", "Plant Name", "State", "Latitude", "Longitude",
         "Balancing Authority Code"]
    ]


def main() -> None:
    _ensure_inputs()
    gen = load_generators()
    plant = load_plants()

    # Restrict to the target region, then join units.
    if C.REGION_BA_CODE in (None, "US", "ALL"):
        pjm_plant = plant[~plant["State"].isin(C.EXCLUDE_STATES)].copy()   # all lower-48
    else:
        pjm_plant = plant[plant["Balancing Authority Code"] == C.REGION_BA_CODE].copy()
    gen_pjm = gen[gen["Plant Code"].isin(pjm_plant["Plant Code"])].copy()

    # Aggregate nameplate to plant level, keeping peaker vs CCGT split.
    agg = (
        gen_pjm.assign(
            nameplate_MW_peaker=lambda d: d["Nameplate Capacity (MW)"].where(d["class"] == "peaker", 0.0),
            nameplate_MW_ccgt=lambda d: d["Nameplate Capacity (MW)"].where(d["class"] == "ccgt", 0.0),
        )
        .groupby("Plant Code")
        .agg(
            nameplate_MW_total=("Nameplate Capacity (MW)", "sum"),
            nameplate_MW_peaker=("nameplate_MW_peaker", "sum"),
            nameplate_MW_ccgt=("nameplate_MW_ccgt", "sum"),
            n_units=("Generator ID", "count"),
        )
        .reset_index()
    )

    out = (
        pjm_plant.merge(agg, on="Plant Code", how="inner")
        .rename(
            columns={
                "Plant Code": "plant_code",
                "Plant Name": "name",
                "State": "state",
                "Latitude": "lat",
                "Longitude": "lon",
                "Balancing Authority Code": "ba",
            }
        )
        .dropna(subset=["lat", "lon"])
        .sort_values("nameplate_MW_total", ascending=False)
        .reset_index(drop=True)
    )

    # Actual gas capacity factor from EIA-923 net generation (context, not used in the screen).
    netgen = load_gas_generation()
    out["net_gen_MWh_2024"] = out["plant_code"].map(netgen)
    out["gas_cf"] = out["net_gen_MWh_2024"] / (out["nameplate_MW_total"] * C.HOURS_PER_YEAR)

    out_path = C.DATA_INTERIM / "pjm_gas_plants.csv"
    out.to_csv(out_path, index=False)

    # ---- Report + §11 validation ----
    total_gw = out["nameplate_MW_total"].sum() / 1000.0
    region = "US (lower-48)" if C.REGION_BA_CODE in (None, "US", "ALL") else C.REGION_BA_CODE
    print(f"\nWrote {out_path}")
    print(f"{region} operating gas plants: {len(out)}   total nameplate: {total_gw:,.1f} GW")
    print(f"  peaker (GT):   {out['nameplate_MW_peaker'].sum()/1000:,.1f} GW")
    print(f"  ccgt (CT/CA/CS/CC): {out['nameplate_MW_ccgt'].sum()/1000:,.1f} GW")
    gcf = out["gas_cf"]
    print(f"  actual gas CF (EIA-923 {C.EIA923_VINTAGE}): median {gcf.median():.2f}, mean "
          f"{gcf.mean():.2f}, {gcf.isna().sum()} missing, {(gcf>1.0).sum()} >100% (industrial/CHP "
          "nameplate under-report)")
    print("\nBy state (nameplate GW):")
    by_state = (out.groupby("state")["nameplate_MW_total"].sum() / 1000).sort_values(ascending=False)
    print(by_state.round(1).to_string())

    print("\n§11 name-match check (expected paper plants present in PJM fleet):")
    names_lc = out["name"].str.lower()
    for exp in EXPECTED_PLANTS:
        hit = out[names_lc.str.contains(exp.lower(), na=False)]
        if len(hit):
            row = hit.iloc[0]
            print(f"  [OK]   {exp:<24} -> {row['name']} ({row['state']}, {row['nameplate_MW_total']:.0f} MW)")
        else:
            print(f"  [MISS] {exp:<24} -> not found (may be non-PJM BA, retired, or renamed)")


if __name__ == "__main__":
    main()
