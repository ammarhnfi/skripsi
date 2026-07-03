"""
Hitung Silhouette Coefficient per tahun per k untuk bab4.tex tabel SC.
Menggunakan STATIS Scenario1 (ACT Klasik) — sama dengan export_klaster.py statis_yr.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from export_klaster import load_excel, align, _run_statis, _JP_NAMES
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

EXCEL_PATH  = r"D:\Skripsi\my\data\Data Final.xlsx"
VARIABLES   = ["IPG","PPM","PDRB_ADHK","RLS","AHH_L","AHH_P","GK","PKKP","TPT","TPAK","GR"]
SHEETS      = ["2020","2021","2022","2023","2024"]
K_LIST      = [2, 3, 4, 5]
SCENARIO    = "scenario1"   # ACT Klasik

print("Membaca data ...", flush=True)
tables_raw, _ = load_excel(EXCEL_PATH, weight_var="JP")
arrays, obs = align(tables_raw, SHEETS, VARIABLES)

# Build jp_aligned
jp_aligned = {}
for yr in SHEETS:
    df = tables_raw[yr]
    jc = next((c for c in _JP_NAMES if c in df.columns), None)
    if jc:
        jp_aligned[yr] = {o: df.loc[o, jc] for o in obs if o in df.index}

print(f"OK — {len(obs)} wilayah, {len(arrays)} tahun\n")

print("Menjalankan STATIS scenario1 ...", flush=True)
res = _run_statis(arrays, SHEETS, jp_aligned, SCENARIO)
pyr = res["per_year_coords"]   # dict yr_str -> (n, 2) array
print("OK\n")

# --- Tabel SC per tahun per k ---
print(f"{'k':>3}  ", end="")
for yr in SHEETS:
    print(f"  SC({yr})", end="")
print()
print("-" * (5 + 9*len(SHEETS)))

for k in K_LIST:
    print(f"k={k}  ", end="")
    for yr in SHEETS:
        coords = pyr[str(yr)]
        labels = KMeans(n_clusters=k, random_state=42, n_init=10).fit_predict(coords)
        sc = silhouette_score(coords, labels)
        print(f"  {sc:.3f}  ", end="")
    print()

# --- SC untuk kompromi (dipakai AppSilhouetteAvg saat ini) ---
print("\n--- SC Kompromi (skor kompromi, k=3) ---")
scores = res["scores"]   # (n, 2) compromise scores
als    = res["alphas"]
# Sebenarnya AppSilhouetteAvg dihitung dari skor kompromi saja:
labels_comp = KMeans(n_clusters=3, random_state=42, n_init=10).fit_predict(scores)
sc_comp = silhouette_score(scores, labels_comp)
print(f"SC kompromi k=3 = {sc_comp:.4f}")
