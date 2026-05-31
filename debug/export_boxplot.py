"""
export_boxplot.py
=================
Script standalone untuk menghasilkan ulang HANYA boxplot indikator (PNG)
dengan label sumbu yang diperbesar, tanpa menjalankan analisis STATIS penuh.

Cara pakai:
    cd d:/Skripsi/my
    python debug/export_boxplot.py --real
    python debug/export_boxplot.py --sampel

Requirements:
    pip install pandas openpyxl plotly kaleido
"""

import os
import sys
import json
import pandas as pd
import plotly.express as px

# ============================================================
# CONFIG & FLAG HANDLING
# ============================================================
DATA_PATH = r"d:\Skripsi\my\data\Data Final.xlsx"
OUT_DIR   = r"d:\Skripsi\my\output_real"

is_sample = "--sampel" in sys.argv
is_real   = "--real"   in sys.argv

config_path = None
if is_sample:
    config_path = r"d:\Skripsi\my\debug\export_sample.json"
elif is_real:
    config_path = r"d:\Skripsi\my\debug\export_real.json"

cfg = {}
if config_path and os.path.exists(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    DATA_PATH = cfg.get("excel_path", DATA_PATH)
    OUT_DIR   = cfg.get("output_dir",  OUT_DIR)
    print(f"  [CONFIG] Loaded: {config_path}")
else:
    print(f"  [INFO] Tidak ada config. Gunakan --real atau --sampel.")

_JP_NAMES = ['JP', 'Jumlah Penduduk', 'jumlah_penduduk', 'Penduduk', 'Total Penduduk']

# ============================================================
# LOAD DATA
# ============================================================
print("\n=== Memuat Data ===")
all_sheets = pd.read_excel(DATA_PATH, sheet_name=None)

available_years = sorted([str(k) for k in all_sheets if str(k).isdigit()])
selected_years  = cfg.get("sheets", available_years)
selected_vars   = cfg.get("variables", None)

tables = {}
ipm_col = None
for name, df in all_sheets.items():
    yr = str(name)
    if yr not in selected_years:
        continue
    try:
        df = df.set_index("Kabupaten/Kota")
        if "Provinsi" in df.columns:
            df = df.drop(columns=["Provinsi"])
        for c in df.columns:
            if df[c].dtype == 'object':
                df[c] = pd.to_numeric(
                    df[c].astype(str).str.replace(',', '.').str.strip(),
                    errors='coerce'
                )
        df = df.dropna(axis=1, how='all')
        tables[yr] = df
        if ipm_col is None:
            for c in df.columns:
                if "IPM" in c.upper() and "TOTAL" not in c.upper():
                    ipm_col = c
                    break
    except Exception as e:
        print(f"  Skip sheet '{name}': {e}")

if not tables:
    print("  [ERROR] Tidak ada sheet yang berhasil dimuat.")
    sys.exit(1)

first_year = sorted(tables.keys())[0]
if selected_vars is None:
    selected_vars = [c for c in tables[first_year].columns if c not in _JP_NAMES]

vars_for_boxplot = list(selected_vars)
if ipm_col and ipm_col not in vars_for_boxplot:
    vars_for_boxplot.append(ipm_col)

print(f"  Tahun      : {selected_years}")
print(f"  Indikator  : {vars_for_boxplot}")
print(f"  Output     : {OUT_DIR}")

os.makedirs(OUT_DIR, exist_ok=True)

# ============================================================
# HELPER: simpan PNG
# ============================================================
def save_png(fig, filename, out_dir, width=800, height=500):
    path = os.path.join(out_dir, filename)
    try:
        fig.update_layout(title_x=0.5)
        fig.write_image(path, width=width, height=height, scale=3)
        print(f"  [PNG] {filename}")
    except Exception as e:
        print(f"  [WARN] Gagal simpan {filename}: {e}")

# ============================================================
# GENERATE BOXPLOTS
# ============================================================
print("\n=== Membuat Boxplot ===")
for col in vars_for_boxplot:
    dfs_box = []
    for yr in selected_years:
        if yr not in tables:
            continue
        df_yr = tables[yr]
        if col not in df_yr.columns:
            print(f"  [SKIP] Kolom '{col}' tidak ada di tahun {yr}")
            continue
        df_temp = df_yr[[col]].copy()
        df_temp['Tahun'] = str(yr)
        dfs_box.append(df_temp)

    if not dfs_box:
        continue

    df_all = pd.concat(dfs_box)

    fig_box = px.box(
        df_all, x='Tahun', y=col, points='outliers',
        title=f"Distribusi {col} (Perbandingan Tahunan)",
        color='Tahun',
        color_discrete_sequence=px.colors.qualitative.Safe
    )
    fig_box.update_layout(
        template='plotly_white',
        height=500,
        showlegend=False,
        font=dict(size=16),
        title_font=dict(size=18),
        xaxis=dict(
            title='Tahun',
            title_font=dict(size=18),
            tickfont=dict(size=18),
        ),
        yaxis=dict(
            title=col,
            title_font=dict(size=18),
            tickfont=dict(size=16),
        ),
    )

    fname = col.replace('/', '-').replace(' ', '_').lower()
    if col in _JP_NAMES:
        fname = "jp"
    save_png(fig_box, f"boxplot_{fname}.png", OUT_DIR, width=800, height=500)

print(f"\n=== Selesai! {len(vars_for_boxplot)} boxplot disimpan ke: {OUT_DIR} ===")
