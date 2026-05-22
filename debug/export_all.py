"""
export_all.py
=============
Script standalone untuk menghasilkan SEMUA gambar (PNG) dan tabel (.tex)
dari analisis STATIS + K-Means + Moran's I.

Semua output disimpan ke folder: output_real/

Cara pakai:
    cd d:/Skripsi/my
    python export_all.py

Requirements:
    pip install pandas openpyxl numpy scipy scikit-learn plotly geopandas kaleido
"""

import os
import sys
import json
import filecmp
import shutil
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import ListedColormap
from scipy.cluster.hierarchy import linkage
from scipy.stats import skew, kurtosis as kurt

def deduplicate_and_clean(root_path):
    """
    Membersihkan file redundant antara root dan scenario1/scenario2.
    Aturan:
    1. Jika file di scenario1 == scenario2 DAN tidak terkait STATIS
       → pindahkan ke root dan hapus di kedua scenario.
    2. File terkait STATIS (mengandung 'vs_statis' atau 'statis_vs')
       → selalu tetap di scenario1 dan scenario2 (tidak pernah dipindah ke root).
    """
    s1_path = os.path.join(root_path, 'scenario1')
    s2_path = os.path.join(root_path, 'scenario2')

    # Hapus file core, macros, perm, scree, rv, dan beta dari root_path agar tidak ada duplikasi dengan scenario
    for filename in [
        "output_core_statis.tex", "output_macros.tex", "output_perm_statis.tex", "permutation_histogram.png",
        "scree_plot.png", "rv_heatmap.png", "beta_trajectory.png",
        "output_table_beta_provinsi.tex", "output_table_beta_vec.tex", "output_table_struktur_diagnostik.tex"
    ]:
        root_file = os.path.join(root_path, filename)
        if os.path.exists(root_file):
            try:
                os.remove(root_file)
                print(f"  [CLEAN] Menghapus file duplikat {filename} dari root.")
            except Exception as e:
                print(f"  [WARN] Gagal menghapus {filename} dari root: {e}")

    for yr in ["2020", "2021", "2022", "2023", "2024"]:
        for prefix in ["output_table_jarak_skor_", "output_table_jarak_loading_", "output_table_skor_intra_", "output_table_loading_intra_", "output_table_matriks_intra_loading_"]:
            filename = f"{prefix}{yr}.tex"
            root_file = os.path.join(root_path, filename)
            if os.path.exists(root_file):
                try:
                    os.remove(root_file)
                    print(f"  [CLEAN] Menghapus file duplikat {filename} dari root.")
                except Exception as e:
                    print(f"  [WARN] Gagal menghapus {filename} dari root: {e}")

    # Hapus cluster_scatter_biplot_{yr}.png dan cluster_map_biplot_{yr}.png dari scenario1 & scenario2
    # karena ini adalah hasil PCA Unweighted yang identik dan harus berada di root saja.
    for yr in ["2020", "2021", "2022", "2023", "2024"]:
        for f_name in [f"cluster_scatter_biplot_{yr}.png", f"cluster_map_biplot_{yr}.png"]:
            for sc_dir in [s1_path, s2_path]:
                sc_file = os.path.join(sc_dir, f_name)
                if os.path.exists(sc_file):
                    try:
                        os.remove(sc_file)
                        print(f"  [CLEAN] Menghapus file unweighted {f_name} dari {os.path.basename(sc_dir)}.")
                    except Exception as e:
                        print(f"  [WARN] Gagal menghapus {f_name} dari {os.path.basename(sc_dir)}: {e}")

    if not os.path.exists(s1_path) or not os.path.exists(s2_path): return

    print("\n" + "="*55)
    print("  MENJALANKAN DEDUPLIKASI & PEMBERSIHAN")
    print("="*55)

    # Pattern nama file yang SELALU di scenario (tidak boleh ke root)
    # Pattern nama file yang SELALU di scenario (tidak boleh ke root) agar dapat di-load side-by-side di dashboard
    SCENARIO_ONLY_PATTERNS = [
        # --- 9 Perbandingan Utama (Tabel & Plot pendukung) ---
        'biplot_transition',         # Perbandingan 1: Matriks Transisi Cluster Biplot Tahunan
        'statis_transition',         # Perbandingan 2: Matriks Transisi Cluster STATIS Tahunan
        'biplot_vs_statis_compare',  # Perbandingan 3: Perbandingan Cluster Biplot PCA vs STATIS Tahunan
        'output_table_ipm_',         # Perbandingan 4: Matriks Transisi Kategori IPM UNDP
        'cross_matrix',              # Perbandingan 5: Perbandingan Cluster Biplot vs Kategori IPM
        'statis_vs_ipm',             # Perbandingan 6: Perbandingan Cluster STATIS Tahunan vs Kategori IPM
        'biplot_vs_statis',          # Perbandingan 7: Perbandingan Cluster Kompromi STATIS vs Cluster Biplot
        'compromise_vs_statis',      # Perbandingan 8: Perbandingan Cluster Kompromi STATIS vs STATIS Tahunan
        'compromise_vs_ipm',         # Perbandingan 9: Perbandingan Cluster Kompromi STATIS vs Kategori IPM
        
        # --- File Hasil STATIS & Komparasi Lainnya ---
        'compare_map_', 'compare_scatter_', 'compare_pie_', # Peta, scatter, dan pie plot perbandingan transisi/metode
        'output_table_alpha.tex',    # Nilai Alpha (bobot) per skenario
        'output_table_eigen.',       # Eigenvalues per skenario
        'output_table_loadings.',    # Loadings utama per skenario
        'output_table_scores.',      # PC Scores kompromi per skenario
        'matrix_g_c', 'matrix_v_c', 'matrix_f_c', # Matriks Kompromi G, V, F
        'compromise_map',            # Peta Kompromi STATIS
        'scatter_statis',            # Scatter plot STATIS
        'compromise_biplot',         # Biplot kompromi
        'variable_contribution',     # Kontribusi indikator
        'variable_cos2',             # Cos2 indikator
        'biplot_tahun_',             # Biplot tahunan per skenario
        'compromise_map',            # Peta cluster STATIS
        'compromise_scatter',         # Scatter plot kompromi STATIS
        'cluster_pie_statis',        # Pie chart cluster STATIS (tahunan)
        'compromise_pie',             # Pie chart kompromi STATIS
        'elbow_plot_', 'dendrogram_', 'dendrogram_compromise', # Elbow & Dendrogram
        'cluster_map_statis_',       # Peta cluster STATIS per tahun (berbeda per skenario)
        'output_table_cluster_members',         # (legacy) Anggota cluster kompromi
        'output_table_compromise_cluster_sum_name', # Ringkasan anggota cluster kompromi
        'beta',                      # Koefisien Beta (tabel & grafik) per skenario
        'diagnostik',                # Tabel diagnostik model regresi per skenario
        'moran',                     # Hasil uji Moran's I spasial per skenario
    ]

    def is_scenario_only(name):
        name_l = name.lower()
        return any(p.lower() in name_l for p in SCENARIO_ONLY_PATTERNS)

    # 1. Bandingkan s1 dan s2 — hanya pindah ke root jika BUKAN scenario-only
    dcmp = filecmp.dircmp(s1_path, s2_path)
    for name in dcmp.common_files:
        if is_scenario_only(name):
            # Biarkan di masing-masing scenario, jangan pindah ke root
            continue
        f1 = os.path.join(s1_path, name)
        f2 = os.path.join(s2_path, name)
        if filecmp.cmp(f1, f2, shallow=False):
            # File identik dan bukan scenario-only → pindah ke root
            shutil.copy2(f1, os.path.join(root_path, name))
            os.remove(f1)
            os.remove(f2)
            print(f"  [DEDUP] {name} dipindah ke root (identik, shared).")

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Global Helper for Cluster Names
def get_cluster_name(idx, prefix="Cluster", suffix=""):
    if K_CLUSTERS == 3:
        desc = ["Rendah", "Sedang", "Tinggi"][idx]
    elif K_CLUSTERS == 2:
        desc = ["Rendah", "Tinggi"][idx]
    else:
        desc = ""
    desc_str = f" ({desc})" if desc else ""
    return f"{prefix} {idx+1}{desc_str}{suffix}"

def export_matrix_pmatrix(arr, filename, out_dir):
    with open(os.path.join(out_dir, filename), "w", encoding="utf-8") as f:
        f.write(r"\begin{pmatrix}" + "\n")
        for row in arr:
            f.write(" & ".join([f"{v:.2f}".replace('.', ',') for v in row]) + r" \\" + "\n")
        f.write(r"\end{pmatrix}")


# Default paths
DATA_PATH = r"d:\Skripsi\my\data\Data Final.xlsx"
OUT_DIR = r"d:\Skripsi\my\output_real"
SHP_PATH = r"d:\Skripsi\my\web\gadm41_IDN_2.shp"

# Handle flags
is_sample = "--sampel" in sys.argv
is_real = "--real" in sys.argv
is_headless = "--headless" in sys.argv or is_sample or is_real

config_path = None
if is_sample:
    config_path = r"d:\Skripsi\my\debug\export_sample.json"
elif is_real:
    config_path = r"d:\Skripsi\my\debug\export_real.json"
elif is_headless:
    # Default ke export_real.json jika cuma --headless tanpa flag spesifik
    config_path = r"d:\Skripsi\my\debug\export_real.json"

# Default prefix
LABEL_PREFIX = "App"

cfg = {}
if config_path and os.path.exists(config_path):
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        DATA_PATH = cfg.get("excel_path", DATA_PATH)
        OUT_DIR = cfg.get("output_dir", OUT_DIR)
        SHP_PATH = cfg.get("shapefile_path", SHP_PATH)
        # Load prefix from config if available
        if "label_prefix" in cfg:
            LABEL_PREFIX = cfg["label_prefix"]
        print(f"  [CONFIG] Loaded configuration from: {config_path}")
    except Exception as e:
        print(f"  [WARN] Gagal baca config {config_path}: {e}")

# Handle positional arguments (tetap didukung untuk override cepat)
pos_args = [a for a in sys.argv[1:] if not a.startswith("--")]
if len(pos_args) > 0: DATA_PATH = pos_args[0]
if len(pos_args) > 1: OUT_DIR = pos_args[1]

# Handle prefix flag (override)
for arg in sys.argv:
    if arg.startswith("--prefix="):
        LABEL_PREFIX = arg.split("=")[1]


os.makedirs(OUT_DIR, exist_ok=True)


# ============================================================
# HELPER: simpan PNG
# ============================================================
def save_png(fig, filename, out_dir, width=900, height=600):
    path = os.path.join(out_dir, filename)
    try:
        fig.update_layout(title_x=0.5)
        fig.write_image(path, width=width, height=height, scale=2)
        print(f"  [PNG] {filename}")
    except Exception as e:
        print(f"  [WARN] Gagal simpan {filename}: {e}")


# ============================================================
# HELPER: simpan TEX tabel sederhana
# ============================================================
def escape_tex(val):
    if isinstance(val, (int, float)):
        return val
    s = str(val)
    # Jika sudah mengandung LaTeX commands (pake $) jangan escape berlebihan
    if '$' in s and (s.count('$') % 2 == 0):
        # Kemungkinan math mode, hanya escape karakter lain kecuali _ dan $ jika perlu
        for c, r in [('%', r'\%'), ('#', r'\#'), ('&', r'\&')]:
            s = s.replace(c, r)
        return s
    for c, r in [('_', r'\_'), ('%', r'\%'), ('$', r'\$'), ('#', r'\#'), ('&', r'\&')]:
        s = s.replace(c, r)
    return s

def save_tex_table(df, filename, out_dir, caption, label, longtable=False, float_fmt="{:.4f}", header_makecell=False, label_prefix=""):
    path = os.path.join(out_dir, filename)
    cols = df.columns.tolist()
    # All columns use 'c' so the table is always consistent and adjustbox scales it properly
    col_defs = ["c|"] * len(cols)
    col_str = "".join(col_defs)
    full_label = f"{label_prefix}{label}"

    def format_val(v, col_name=""):
        if isinstance(v, (int, float, np.number)):
            if pd.isna(v) or np.isinf(v):
                return escape_tex(str(v))
            
            is_p_val_col = any(x in str(col_name).lower() for x in ["p-value", "p_value", "pvalue", "sig"])
            if is_p_val_col:
                if abs(v) < 0.001:
                    return r"$< 0,001$"
            else:
                if v != 0 and abs(v) < 0.001:
                    return r"$< 0,001$"
            
            try:
                if int(v) == v:
                    return f"{int(v)}"
            except (ValueError, OverflowError):
                pass
            
            formatted = float_fmt.format(v).replace(".", ",")
            return formatted
        return escape_tex(v).replace('&', r'\&')

    lines = []
    if longtable:
        lines.append(r"\begin{longtable}{|" + col_str + "}")
        lines.append(r"\caption{" + escape_tex(caption) + r"} \label{tab:" + full_label + r"} \\")
        lines.append(r"\hline")
        header = " & ".join([f"\\textbf{{{escape_tex(c)}}}" for c in cols]) + r" \\"
        lines += [header, r"\hline", r"\endfirsthead", r"\hline", header, r"\hline", r"\endhead", r"\hline", r"\endfoot"]
        for _, row in df.iterrows():
            row_str = " & ".join([format_val(v, col) for col, v in row.items()]) + r" \\"
            lines.append(row_str)
        lines += [r"\hline", r"\end{longtable}"]
    else:
        lines.append(r"\begin{table}[H]")
        lines.append(r"\centering")
        lines.append(r"\caption{" + escape_tex(caption) + r"} \label{tab:" + full_label + r"}")
        # Use adjustbox to fit large tables like the 41-row scores table
        lines.append(r"\begin{adjustbox}{max width=\textwidth, max height=0.85\textheight}")
        lines.append(r"\begin{tabular}{|" + col_str + "}")
        lines.append(r"\hline")
        if header_makecell:
            # Semua header menggunakan makecell agar bisa wrap
            h_parts = []
            for i, c in enumerate(cols):
                # Ganti '/' dengan line break, dan '->' dengan arrow dalam math mode
                # Gunakan \bfseries agar seluruh isi makecell tebal tanpa \textbf yang fragile terhadap \\
                label_txt = escape_tex(c).replace('/', r' \\ ').replace('->', r' \\ $\rightarrow$ ')
                h_parts.append(f"\\makecell{{\\bfseries {label_txt}}}")
            header = " & ".join(h_parts) + r" \\"
        else:
            header = " & ".join([f"\\textbf{{{escape_tex(c)}}}" for c in cols]) + r" \\"
        lines += [header, r"\hline"]
        for _, row in df.iterrows():
            row_vals = [format_val(v, col) for col, v in row.items()]
            row_str = " & ".join(row_vals) + r" \\"
            lines.append(row_str)
        lines += [r"\hline", r"\end{tabular}", r"\end{adjustbox}", r"\end{table}"]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [TEX] {filename}")


def save_tex_name_table(mapping, filename, out_dir, caption, label, label_prefix=""):
    """Simpan tabel yang berisi daftar nama (untuk transisi cluster)."""
    path = os.path.join(out_dir, filename)
    full_label = f"{label_prefix}{label}"
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{" + escape_tex(caption) + r"} \label{tab:" + full_label + r"}",
        r"\begin{adjustbox}{max width=\textwidth}",
        r"\begin{tabular}{|>{\centering\arraybackslash}p{4cm}|p{10cm}|}",
        r"\hline",
        r"\multicolumn{1}{|c|}{\textbf{Kategori}} & \multicolumn{1}{c|}{\textbf{Daftar Wilayah}} \\",
        r"\hline"
    ]
    for sel, names in mapping.items():
        # Skip baris jika nama kosong atau berisi "-" (sum = 0)
        if not names or str(names).strip() == "-":
            continue
        sel_esc = escape_tex(str(sel))
        names_esc = escape_tex(str(names))
        lines.append(f"{sel_esc} & {names_esc} \\\\")
        lines.append(r"\hline")
    lines += [r"\end{tabular}", r"\end{adjustbox}", r"\end{table}"]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [TEX] {filename}")


def _calculate_moran_manual(gdf, values, obs_names):
    """Hitung Moran's I secara manual menggunakan Geopandas adjacency (Touches)."""
    import numpy as np
    import geopandas as gpd
    from scipy import stats
    try:
        # Match Data dengan GeoData (Eksak)
        # Pastikan 'id_cocok' ada di gdf dan unik
        gdf_filtered = gdf[gdf['id_cocok'].isin(obs_names)].copy()
        if gdf_filtered.empty:
            print("  [WARN] Tidak ada kecocokan antara data observasi dan shapefile.")
            return None

        # Buat mapping dari obs_name ke indeks di gdf_filtered
        name_to_gdf_idx = {name: i for i, name in enumerate(gdf_filtered['id_cocok'])}

        # Filter values dan obs_names agar sesuai dengan gdf_filtered
        matched_values = []
        matched_obs_names = []
        matched_geoms = []
        for i, name in enumerate(obs_names):
            if name in name_to_gdf_idx:
                matched_values.append(values[i])
                matched_obs_names.append(name)
                matched_geoms.append(gdf_filtered.loc[gdf_filtered['id_cocok'] == name, 'geometry'].iloc[0])

        if len(matched_values) < 5:
            print(f"  [WARN] Jumlah observasi yang cocok ({len(matched_values)}) terlalu sedikit untuk Moran's I.")
            return None

        y = np.array(matched_values)
        n = len(y)

        # Weight Matrix (W) - Queen Contiguity
        W = np.zeros((n, n))
        temp_gdf = gpd.GeoDataFrame({'geometry': matched_geoms}, index=matched_obs_names)

        # Calculate contiguity
        for i in range(n):
            for j in range(i + 1, n): # Only need to calculate upper triangle
                if temp_gdf.iloc[i].geometry.touches(temp_gdf.iloc[j].geometry):
                    W[i, j] = 1.0
                    W[j, i] = 1.0 # Symmetric matrix

        # Row Standardization
        row_sums = W.sum(axis=1)
        # Handle cases where a region has no neighbors (row_sum is 0)
        with np.errstate(divide='ignore', invalid='ignore'):
            W_std = W / row_sums[:, None]
        W_std[np.isnan(W_std)] = 0.0 # Set rows with no neighbors to all zeros

        # Moran's I
        y_bar = np.mean(y)
        y_dev = y - y_bar
        sum_sq_dev = np.sum(y_dev**2)
        sum_w = np.sum(W) # Sum of original weights

        if sum_w == 0 or sum_sq_dev == 0:
            print("  [WARN] Sum of weights or sum of squared deviations is zero. Cannot calculate Moran's I.")
            return None

        num = 0.0
        for i in range(n):
            for j in range(n):
                num += W_std[i, j] * y_dev[i] * y_dev[j]

        moran_i = (n / sum_w) * (num / sum_sq_dev)
        expected_i = -1.0 / (n - 1)

        # Z-score & P-value (Normal Approximation simplification)
        # Calculate Variance of I (Randomization assumption) for accuracy
        # S0 = sum_w
        S1 = 0.5 * np.sum((W + W.T)**2) # Sum of squares of all weights
        S2 = np.sum(row_sums**2) # Sum of squares of row sums

        # Calculate b2 (kurtosis)
        b2 = (n * np.sum(y_dev**4)) / (sum_sq_dev**2)

        var_i_num = n * ((n**2 - 3*n + 3) * S1 - n * S2 + 3 * sum_w**2) - \
                    b2 * ((n**2 - n) * S1 - 2 * n * S2 + 6 * sum_w**2)
        var_i_den = (n - 1) * (n - 2) * (n - 3) * sum_w**2

        if var_i_den == 0:
            print("  [WARN] Denominator for Moran's I variance is zero. Cannot calculate Z-score.")
            return None

        var_i = (var_i_num / var_i_den) - (expected_i**2)

        # Ensure variance is non-negative for sqrt
        if var_i < 0:
            print(f"  [WARN] Calculated variance of Moran's I is negative ({var_i:.4f}). Setting to 0 for Z-score calculation.")
            var_i = 0.0

        std_err_i = np.sqrt(var_i)
        if std_err_i == 0:
            z_score = 0.0 # Or handle as undefined
            p_value = 1.0
        else:
            z_score = (moran_i - expected_i) / std_err_i
            p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))

        return moran_i, expected_i, z_score, p_value
    except Exception as e:
        print(f"  [ERR] Moran's I calculation error: {e}")
        return None

def save_moran_tex(results, filename, out_dir, label_prefix=""):
    if not results: return
    path = os.path.join(out_dir, filename)
    mi, ei, zi, pi = results
    if pi < 0.05:
        interp = "Terdapat Autokorelasi Spasial Positif (Berkelompok)" if mi > ei else "Terdapat Autokorelasi Spasial Negatif (Menyebar)"
    else:
        interp = "Tidak Signifikan (Pola Spasial Acak)"
    
    # Prefix unik per skenario agar tidak tabrakan di induk.tex
    pfx = label_prefix.capitalize() if label_prefix else "Macro"
    pfx = pfx.replace("1", "One").replace("2", "Two")
    
    lines = [
        fr"\newcommand{{\{pfx}MoranI}}{{{f'{mi:.4f}'.replace('.', ',')}}}",
        fr"\newcommand{{\{pfx}MoranExp}}{{{f'{ei:.4f}'.replace('.', ',')}}}",
        fr"\newcommand{{\{pfx}MoranZ}}{{{f'{zi:.4f}'.replace('.', ',')}}}",
        fr"\newcommand{{\{pfx}MoranP}}{{{f'{pi:.4f}'.replace('.', ',')}}}",
        fr"\newcommand{{\{pfx}MoranInterp}}{{{interp}}}"
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [TEX] {filename}")


# ============================================================
# 1. LOAD DATA

# ============================================================
print("\n=== Memuat Data ===")
all_sheets = pd.read_excel(DATA_PATH, sheet_name=None)
tables_raw = {}
sheet_names_all = []
for name, df in all_sheets.items():
    try:
        y = int(name)
        df = df.set_index("Kabupaten/Kota")
        if "Provinsi" in df.columns:
            df = df.drop(columns=["Provinsi"])
        for c in df.columns:
            if df[c].dtype == 'object':
                df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.').str.strip(), errors='coerce')
        df = df.dropna(axis=1, how='all')
        tables_raw[str(y)] = df
        sheet_names_all.append(str(y))
    except Exception as e:
        print(f"  Skip sheet '{name}': {e}")

sheet_names_all = sorted(sheet_names_all)
all_columns_available = tables_raw[sheet_names_all[0]].columns.tolist()

# Simpan JP per tahun untuk pembentukan bobot demografis m_i (Lavit 1994)
_JP_NAMES = ['JP', 'Jumlah Penduduk', 'jumlah_penduduk', 'Penduduk', 'Total Penduduk']
jp_raw = {}  # {year: {wilayah: JP_value}}
for name, df in all_sheets.items():
    try:
        y = int(name)
        df_tmp = df.set_index('Kabupaten/Kota') if 'Kabupaten/Kota' in df.columns else df.set_index(df.columns[0])
        for jp_name in _JP_NAMES:
            if jp_name in df_tmp.columns:
                jp_raw[str(y)] = df_tmp[jp_name].to_dict()
                break
    except Exception:
        pass

print(f"  Sheet tersedia : {sheet_names_all}")
print(f"  Indikator      : {all_columns_available}")
print(f"  Wilayah        : {tables_raw[sheet_names_all[0]].index.tolist()}")
print(f"  JP data ditemukan untuk tahun: {list(jp_raw.keys())}")


# ============================================================
# 2. INPUT INTERAKTIF (mirip Panel Kontrol di Aplikasi)
# ============================================================

def _pick_items(label, items, multi=True, default_all=True):
    """Tampilkan daftar bernomor dan minta input dari user."""
    print(f"\n{'='*55}")
    print(f"  {label}")
    print(f"{'='*55}")
    for i, item in enumerate(items, 1):
        print(f"  [{i:2d}]  {item}")
    if multi:
        print(f"\n  Ketik nomor dipisah koma (cth: 1,2,5,7)")
        hint = f"  Enter = pilih SEMUA" if default_all else f"  Enter = pilih TIDAK ADA"
        print(hint)
        raw = input("  > ").strip()
        if not raw:
            return list(items) if default_all else []
        chosen = []
        for part in raw.split(','):
            part = part.strip()
            if '-' in part:
                a, b = part.split('-')
                chosen += items[int(a)-1:int(b)]
            elif part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(items):
                    chosen.append(items[idx])
        return chosen
    else:
        raw = input(f"  Pilih satu nomor > ").strip()
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(items):
                return items[idx]
        return items[0]


def _ask_int(label, default):
    print(f"\n  {label} (default={default}): ", end="")
    raw = input().strip()
    try:
        return int(raw)
    except ValueError:
        return default


def _ask_bool(label, default=True):
    d = 'Y/n' if default else 'y/N'
    print(f"\n  {label} [{d}]: ", end="")
    raw = input().strip().lower()
    if raw == '':
        return default
    return raw.startswith('y')


print("\n" + "#"*55)
print("#" + " "*15 + "KONFIGURASI EXPORT" + " "*20 + "#")
print("#"*55)
print("  (Tekan Enter untuk menggunakan nilai default)")

# --- 1. Pilih Tahun ---
if is_headless:
    selected_years = cfg.get("sheets", sheet_names_all)
    print(f"  [HEADLESS] Tahun dari config: {selected_years}")
else:
    selected_years = _pick_items(
        "Filter Tahun  (semua = dianalisis bersama)",
        sheet_names_all,
        multi=True,
        default_all=True
    )

if not selected_years:
    print("  [ERROR] Harus memilih minimal 2 tahun!")
    sys.exit(1)
if len(selected_years) < 2:
    print("  [ERROR] Minimal pilih 2 tahun untuk analisis STATIS!")
    sys.exit(1)
print(f"  => Tahun terpilih: {selected_years}")

# --- 2. Pilih Indikator ---
if is_headless:
    try:
        selected_vars = cfg.get("variables", [v for v in all_columns_available if v.upper() != 'IPM'])
        print(f"  [HEADLESS] Indikator Analisis dari config: {selected_vars}")
    except:
        selected_vars = [v for v in all_columns_available if v.upper() != 'IPM']

else:
    selected_vars = _pick_items(
        "Pilih Indikator Analisis  (Enter = pilih SEMUA)",
        all_columns_available,
        multi=True,
        default_all=True
    )

if not selected_vars:
    print("  [ERROR] Harus memilih minimal 1 indikator!")
    sys.exit(1)
print(f"  => Indikator terpilih ({len(selected_vars)}): {selected_vars}")

# --- 3. Jumlah Cluster ---
n_samples = len(tables_raw[sheet_names_all[0]])
default_k = 3 if n_samples >= 5 else 2

if is_headless:
    try:
        K_CLUSTERS = cfg.get("k_clusters", default_k)
    except:
        K_CLUSTERS = default_k
    print(f"  [HEADLESS] k = {K_CLUSTERS}")
else:
    K_CLUSTERS = _ask_int("Jumlah Cluster K-Means (k)", default=default_k)
print(f"  => k = {K_CLUSTERS}")

# --- 4. Skala Visual Loadings ---
if is_headless:
    SCALE_LOAD = cfg.get("scale_load", True)
else:
    SCALE_LOAD = _ask_bool("Skala Visual Loadings (agar sebanding dengan skor)?", default=True)
print(f"  => Scale Load = {SCALE_LOAD}")

# --- 4b. Normalisasi Independen ---
if is_headless:
    NORM_SCORE = cfg.get("norm_score", False)
else:
    NORM_SCORE = _ask_bool("Normalisasi Independen per Sumbu (agar range PC1 & PC2 sebanding)?", default=False)
print(f"  => Norm Score = {NORM_SCORE}")

# --- 5. Jumlah Permutasi ---
if is_headless:
    try:
        N_PERM = cfg.get("n_permutations", 1000)
    except:
        N_PERM = 1000
else:
    N_PERM = _ask_int("Jumlah Permutasi (uji signifikansi STATIS)", default=1000)
print(f"  => N Permutasi = {N_PERM}")

# --- 6. Rotasi Baseline ---
if is_headless:
    try:
        rot_cfg = cfg.get("rotation", {})
        BASELINE_TYPE = rot_cfg.get("type", None)
        BASELINE_NAME = rot_cfg.get("name", None)
    except:
        BASELINE_TYPE = None
        BASELINE_NAME = None
    print(f"  [HEADLESS] Rotation: {BASELINE_TYPE} = {BASELINE_NAME}")
else:
    print("\n" + "="*55)
    print("  Rotasi Baseline (Semua Plot)")
    print("="*55)
    print("  [1]  Rotasi berdasarkan Indikator (seperti 'Rotasi: Indikator' di app)")
    print("  [2]  Rotasi berdasarkan Kabupaten/Kota")
    print("  [3]  Tidak ada rotasi")
    _rot_type_raw = input("  Pilih tipe rotasi [1/2/3, default=3]: ").strip()
    if _rot_type_raw == '1':
        BASELINE_TYPE = 'loading'
    elif _rot_type_raw == '2':
        BASELINE_TYPE = 'skor'
    else:
        BASELINE_TYPE = None

    BASELINE_NAME = None
    if BASELINE_TYPE == 'loading':
        print("\n  Indikator yang tersedia sebagai baseline:")
        for i, v in enumerate(selected_vars, 1):
            print(f"  [{i:2d}]  {v}")
        _braw = input("  Pilih nomor indikator > ").strip()
        if _braw.isdigit() and 1 <= int(_braw) <= len(selected_vars):
            BASELINE_NAME = selected_vars[int(_braw) - 1]
    elif BASELINE_TYPE == 'skor':
        print("\n  Kabupaten/Kota yang tersedia sebagai baseline:")
        _obs_tmp = tables_raw[sheet_names_all[0]].index.tolist()
        for i, o in enumerate(_obs_tmp, 1):
            print(f"  [{i:2d}]  {o}")
        _braw = input("  Pilih nomor Kab/Kota > ").strip()
        if _braw.isdigit() and 1 <= int(_braw) <= len(_obs_tmp):
            BASELINE_NAME = _obs_tmp[int(_braw) - 1]

if BASELINE_TYPE and BASELINE_NAME:
    print(f"  => Rotasi: {BASELINE_TYPE} = '{BASELINE_NAME}'")
else:
    BASELINE_TYPE = None
    print(f"  => Tidak ada rotasi")

# --- 7. Mirroring (Flip PC2 per tahun) ---
if is_headless:
    try:
        MIRROR_YEARS = cfg.get("mirror_years", [])
    except:
        MIRROR_YEARS = []
else:
    MIRROR_YEARS = _pick_items(
        "Mirroring / Flip PC2 — pilih tahun yang di-flip (Enter = tidak ada)",
        sheet_names_all,
        multi=True,
        default_all=False
    )
print(f"  => Mirror tahun: {MIRROR_YEARS if MIRROR_YEARS else 'Tidak ada'}")

# --- 8. Highlight Trajektori ---
_obs_all_tmp = tables_raw[sheet_names_all[0]].index.tolist()
_hl_items = selected_vars + ['--- Kab/Kota ---'] + _obs_all_tmp

if is_headless:
    try:
        HIGHLIGHT_VARS = cfg.get("highlight_vars", [])
        HIGHLIGHT_OBJECTS = cfg.get("highlight_objects", [])
        K_CLUSTERS = cfg.get("k_clusters", 3)
        N_PERM = cfg.get("n_permutations", 500)
        IMG_FORMAT = cfg.get("image_format", "png")
        IMG_SCALE = cfg.get("image_scale", 2)
        IMG_WIDTH = cfg.get("image_width", 1000)
        IMG_HEIGHT = cfg.get("image_height", 700)
    except:
        HIGHLIGHT_VARS = []
        HIGHLIGHT_OBJECTS = []
    print(f"  [HEADLESS] Highlight: {HIGHLIGHT_VARS}, {HIGHLIGHT_OBJECTS}")
else:
    print("\n" + "="*55)
    print("  Highlight Trajektori (garis tebal di plot trajektori)")
    print("="*55)
    _hl_raw = _pick_items(
        "Highlight Item  (Enter = tidak ada)",
        _hl_items,
        multi=True,
        default_all=False
    )
    HIGHLIGHT_VARS = [x for x in _hl_raw if x in selected_vars]
    HIGHLIGHT_OBJECTS = [x for x in _hl_raw if x in _obs_all_tmp]

print(f"  => Highlight Indikator: {HIGHLIGHT_VARS}")
print(f"  => Highlight Objek  : {HIGHLIGHT_OBJECTS}")

# Simpan Root Out Dir karena kita akan buat subfolder
ROOT_OUT_DIR = OUT_DIR

# ============================================================
# 1. PERSIAPAN DATA GLOBAL (Hanya Sekali)
# ============================================================
print("\n" + "="*55)
print("  MEMULAI PERSIAPAN DATA GLOBAL (ROOT)")
print("="*55 + "\n")

# Identifikasi kolom IPM (cari di awal agar bisa di-include di tables)
ipm_col_detected = None
for c in all_columns_available:
    if "IPM" in c.upper() and ("TOTAL" not in c.upper() or "IPM" == c):
        ipm_col_detected = c
        break
ipm_col: str | None = ipm_col_detected

# Muat semua tabel tahunan (Shared)
tables = {}
for yr in selected_years:
    df = tables_raw[yr]
    jp_in_df = [c for c in df.columns if c in _JP_NAMES]
    cols_to_keep = list(set(selected_vars + ([ipm_col_detected] if ipm_col_detected else []) + jp_in_df))
    vars_in = [v for v in cols_to_keep if v in df.columns]
    tables[yr] = df[vars_in].copy()

sheet_names = selected_years
obs_labels = tables[sheet_names[0]].index.tolist()

# 1.1 Bobot Demografis m_i (Global)
_jp_arrays = []
for yr in sheet_names:
    if yr in jp_raw:
        jp_y = np.array([jp_raw[yr].get(idx, np.nan) for idx in obs_labels], dtype=float)
        if not np.any(np.isnan(jp_y)) and np.all(jp_y > 0): _jp_arrays.append(jp_y)

if len(_jp_arrays) > 0:
    JP_mean = np.array(_jp_arrays).mean(axis=0)
    m_weights = JP_mean / JP_mean.sum()
else:
    m_weights = np.ones(len(obs_labels)) / len(obs_labels)

D_sqrt = np.diag(np.sqrt(m_weights))
D_inv_sqrt = np.diag(1.0 / np.sqrt(m_weights))
D_diag_mat = np.diag(m_weights)

# 1.2 Weighted Z-Score & Intra-struktur
X_matrices, Ws, Ss = [], [], []
for s in sheet_names:
    arr = tables[s][selected_vars].values.astype(float)
    mu = m_weights @ arr
    centered = arr - mu
    sigma = np.sqrt(np.clip(m_weights @ (centered**2), 1e-12, None))
    Z_k = centered / sigma
    X_matrices.append(Z_k)
    Ws.append(Z_k @ Z_k.T)
    # Sk = Zk^T D Zk
    Ss.append(Z_k.T @ D_diag_mat @ Z_k)

k_time = len(sheet_names)

# 1.3 Interstruktur & RV (Global)
def calc_H(mats, k, D=None):
    H = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            H[i, j] = np.trace(mats[i] @ D @ mats[j] @ D) if D is not None else np.trace(mats[i] @ mats[j])
    return H

H_W = calc_H(Ws, k_time, D=D_diag_mat)
H_S = calc_H(Ss, k_time)

def get_alpha(H):
    vals, vecs = np.linalg.eig(H)
    idx = np.argsort(np.real(vals))[::-1]
    vec = np.real(vecs[:, idx[0]])
    if vec.sum() < 0: vec = -vec
    return vec / vec.sum(), np.real(vals[idx])

alphas_W, vals_HW = get_alpha(H_W)
alphas_S, vals_HS = get_alpha(H_S)

def calc_RV(mats, k, D=None):
    R = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            if D is not None:
                num = np.trace(mats[i] @ D @ mats[j] @ D)
                den = np.sqrt(np.trace(mats[i] @ D @ mats[i] @ D) * np.trace(mats[j] @ D @ mats[j] @ D))
            else:
                num = np.trace(mats[i] @ mats[j])
                den = np.sqrt(np.trace(mats[i] @ mats[i]) * np.trace(mats[j] @ mats[j]))
            R[i, j] = num / den if den > 0 else 0
    return R

R_W = calc_RV(Ws, k_time, D=D_diag_mat)
R_S = calc_RV(Ss, k_time)

# Helper: alias agar konsisten dengan nama di section permutation test
def calc_H_matrix(mats, k, D=None):
    return calc_H(mats, k, D=D)

def _rotation_matrix(angle):
    c, s = np.cos(angle), np.sin(angle)
    return np.array([[c, -s], [s, c]])

def compute_baseline_angle(scores, loads, obs_labels_list, vars_list, baseline_type, baseline_name):
    if not baseline_name:
        return 0.0
    vec = np.zeros(2)
    if baseline_type == 'loading' and baseline_name in vars_list:
        idx = vars_list.index(baseline_name)
        if idx < len(loads):
            vec = loads[idx].copy()
    elif baseline_type == 'skor' and baseline_name in obs_labels_list:
        idx = obs_labels_list.index(baseline_name)
        if idx < len(scores):
            vec = scores[idx].copy()
    return -np.arctan2(vec[1], vec[0]) if not np.allclose(vec, 0) else 0.0

print("\n=== 2. Boxplot Indikator (Grouped by Year) ===")
vars_for_boxplot = list(selected_vars)
if ipm_col and ipm_col not in vars_for_boxplot:
    vars_for_boxplot.append(ipm_col)

for col in vars_for_boxplot:
    dfs_box = []
    for yr in sheet_names:
        df_temp = tables[yr][[col]].copy()
        df_temp['Tahun'] = str(yr)
        dfs_box.append(df_temp)
    df_all_years = pd.concat(dfs_box)
    
    fig_box = px.box(df_all_years, x='Tahun', y=col, points='outliers',
                     title=f"Distribusi {col} (Perbandingan Tahunan)",
                     color='Tahun', color_discrete_sequence=px.colors.qualitative.Safe)
    fig_box.update_layout(template='plotly_white', height=500, showlegend=False)
    
    fname = col.replace('/', '-').replace(' ', '_').lower()
    if col in _JP_NAMES: fname = "jp"
    save_png(fig_box, f"boxplot_{fname}.png", ROOT_OUT_DIR, width=800, height=500)

print("\n=== 2.1b Heatmap Korelasi Per Tahun ===")
from scipy.stats import pearsonr as _pearsonr

def _sig_stars(p: float) -> str:
    if p < 0.001: return '***'
    if p < 0.01:  return '**'
    if p < 0.05:  return '*'
    return 'ns'

for _yr in sheet_names:
    _df_c = tables[_yr][selected_vars].copy().select_dtypes(include='number').dropna(axis=1, how='all')
    _corr_cols = _df_c.columns.tolist()
    _nv = len(_corr_cols)
    _zmat: list[list[float]] = [[0.0] * _nv for _ in range(_nv)]
    _annot: list[list[str]] = [[''] * _nv for _ in range(_nv)]
    for _i, _ci in enumerate(_corr_cols):
        for _j, _cj in enumerate(_corr_cols):
            if _i == _j:
                _zmat[_i][_j] = 1.0
                _annot[_i][_j] = f'<b>{_ci}</b>'
            else:
                _r, _p = _pearsonr(_df_c[_ci].values, _df_c[_cj].values)
                _zmat[_i][_j] = _r
                _annot[_i][_j] = f'<b>{_r:.3f}</b><br>{_sig_stars(_p)}'
    _fig_corr = go.Figure(go.Heatmap(
        z=_zmat, x=_corr_cols, y=_corr_cols,
        text=_annot, texttemplate='%{text}',
        colorscale='RdBu', zmid=0, zmin=-1, zmax=1,
        colorbar=dict(title='r'),
    ))
    _fig_corr.update_layout(
        title=f'Heatmap Korelasi Pearson Indikator Tahun {_yr}',
        template='plotly_white',
        width=max(600, _nv * 90 + 100),
        height=max(500, _nv * 90 + 100),
        yaxis=dict(autorange='reversed'),
    )
    save_png(_fig_corr, f'corr_heatmap_{_yr}.png', ROOT_OUT_DIR,
             width=max(600, _nv * 90 + 100), height=max(500, _nv * 90 + 100))

# 2.1 Shared Tables (Global)
print("  Ekspor Tabel Global ke Root...")
# Ensure index column is named 'Tahun' so reset_index() yields the correct column header
df_rv_w = pd.DataFrame(R_W, index=sheet_names, columns=sheet_names)
df_rv_w.index.name = 'Tahun'
df_rv_w = df_rv_w.reset_index()

df_rv_s = pd.DataFrame(R_S, index=sheet_names, columns=sheet_names)
df_rv_s.index.name = 'Tahun'
df_rv_s = df_rv_s.reset_index()

df_hw = pd.DataFrame(H_W, index=sheet_names, columns=sheet_names)
df_hw.index.name = 'Tahun'
df_hw = df_hw.reset_index()

df_hs = pd.DataFrame(H_S, index=sheet_names, columns=sheet_names)
df_hs.index.name = 'Tahun'
df_hs = df_hs.reset_index()

df_alpha_w = pd.DataFrame({'Tahun': sheet_names, 'Alpha (Wilayah)': alphas_W})
df_alpha_s = pd.DataFrame({'Tahun': sheet_names, 'Alpha (Indikator)': alphas_S})

save_tex_table(df_rv_w, "output_table_rv_w.tex", ROOT_OUT_DIR, "Koefisien RV Wilayah (Identik Kedua Skenario)", "rv_w", label_prefix=LABEL_PREFIX)
save_tex_table(df_rv_s, "output_table_rv_s.tex", ROOT_OUT_DIR, "Koefisien RV Indikator (Identik Kedua Skenario)", "rv_s", label_prefix=LABEL_PREFIX)
save_tex_table(df_hw, "output_table_hw.tex", ROOT_OUT_DIR, "Matriks Interstruktur H_W (Identik Kedua Skenario)", "h_w", label_prefix=LABEL_PREFIX)
save_tex_table(df_hs, "output_table_hs.tex", ROOT_OUT_DIR, "Matriks Interstruktur H_S (Identik Kedua Skenario)", "h_s", label_prefix=LABEL_PREFIX)
save_tex_table(df_alpha_w, "output_table_alpha_w.tex", ROOT_OUT_DIR, "Bobot Alpha (Wilayah)", "alpha_w", label_prefix=LABEL_PREFIX)
save_tex_table(df_alpha_s, "output_table_alpha_s.tex", ROOT_OUT_DIR, "Bobot Alpha (Indikator)", "alpha_s", label_prefix=LABEL_PREFIX)

# 2.2 Statistika Deskriptif akan diekspor per skenario (scenario1 saja ke root) — tidak duplikat di sini

# 2.3 KMO & Bartlett dan 2.4 Permutation Test dikerjakan di dalam scenario loop (section 3c dan 5)
# agar parameter yang digunakan konsisten per skenario (H_W untuk s1, H_S untuk s2).

# ============================================================
# 3. SCENARIO LOOP
# ============================================================
IS_FIRST: bool = False  # Akan di-set ulang di dalam loop; deklarasi awal untuk static analysis
for current_scenario in ['scenario1', 'scenario2']:
    OUT_DIR = os.path.join(ROOT_OUT_DIR, current_scenario)
    os.makedirs(OUT_DIR, exist_ok=True)
    SCENARIO = current_scenario
    # Prefix unik per skenario untuk label LaTeX agar tidak duplikat
    CUR_LABEL_PREFIX = f"{LABEL_PREFIX}{'1' if SCENARIO == 'scenario1' else '2'}"
    
    print("\n" + "#"*70)
    print(f"  PROSES SKENARIO: {SCENARIO.upper()}")
    print("#"*70 + "\n")

    IS_FIRST = (current_scenario == 'scenario1')  # Flag: hanya tulis output shared saat iterasi pertama
    ipm_col = ipm_col_detected  # Re-bind per iterasi agar Pylance dapat melacak tipe di scope loop panjang
    H_mat = H_W if SCENARIO == 'scenario1' else H_S  # Matriks interstruktur sesuai skenario
    vals_H_sorted = np.sort(np.real(np.linalg.eigvals(H_mat)))[::-1]  # Eigenvalue H terurut turun
    RV_mat = R_W if SCENARIO == 'scenario1' else R_S  # Matriks RV sesuai skenario

    # ============================================================
    # 4. STATIS CORE (Scenario Specific)
    # ============================================================
    print(f"\n=== 4. Menjalankan STATIS Core ({SCENARIO}) ===")

    # BRANCH LOGIC: Skenario 1 (Wilayah) vs Skenario 2 (Indikator)
    if SCENARIO == 'scenario1':
        alphas = alphas_W
        Wc = np.zeros_like(Ws[0])
        for a, W in zip(alphas, Ws): Wc += a * W
        
        Wc_weighted = D_sqrt @ Wc @ D_sqrt
        P, Lambda_c, _ = np.linalg.svd(Wc_weighted)
        eig_vals_c, eig_vecs_c = Lambda_c, P
        idxc = np.argsort(eig_vals_c)[::-1]
        eig_vals_c, eig_vecs_c = eig_vals_c[idxc], eig_vecs_c[:, idxc]
        
        # Skor
        sq2 = np.sqrt(np.clip(eig_vals_c[:2], 1e-12, None))
        scores_raw = D_inv_sqrt @ eig_vecs_c[:, :2] * sq2
        
        # Loadings Parsial
        loadings_intra_list = []
        for Zk in X_matrices:
            Gk = Zk.T @ D_diag_mat @ scores_raw / sq2
            loadings_intra_list.append(Gk)
        Gc = np.zeros_like(loadings_intra_list[0])
        for a, Gk in zip(alphas, loadings_intra_list): Gc += a * Gk
        loadings = Gc
        Vc_vars = Gc / sq2
    else:
        alphas = alphas_S
        Sc = np.zeros_like(Ss[0])
        for a, S in zip(alphas, Ss): Sc += a * S
        
        U_s, S_s, _ = np.linalg.svd(Sc)
        eig_vals_c, eig_vecs_c = S_s, U_s
        idxc = np.argsort(eig_vals_c)[::-1]
        eig_vals_c, eig_vecs_c = eig_vals_c[idxc], eig_vecs_c[:, idxc]
        
        # Loadings
        sq2 = np.sqrt(np.clip(eig_vals_c[:2], 1e-12, None))
        loadings = eig_vecs_c[:, :2] * sq2
        Vc_vars = eig_vecs_c[:, :2]
        
        # Skor Parsial
        scores_intra_list = []
        for Zk in X_matrices:
            scores_intra_list.append(Zk @ Vc_vars)
        Fc = np.zeros_like(scores_intra_list[0])
        for a, Fk in zip(alphas, scores_intra_list): Fc += a * Fk
        scores_raw = Fc
        
        # Dual eigenvectors for objects mapping
        Zc_temp = np.zeros_like(X_matrices[0])
        for a, Zk in zip(alphas, X_matrices): Zc_temp += a * Zk
        eig_vecs_c_full = D_sqrt @ Zc_temp @ Vc_vars / np.clip(sq2, 1e-12, None)
        # Loadings Intra (Gk) untuk scenario2: Gk = Sk @ Vc @ Lambda^-1/2
        loadings_intra_list = []
        for Zk in X_matrices:
            Sk_i = Zk.T @ D_diag_mat @ Zk
            Gk = Sk_i @ Vc_vars[:, :2] / np.clip(sq2, 1e-12, None)
            loadings_intra_list.append(Gk)
        Gc = np.zeros_like(loadings_intra_list[0])
        for a, Gk in zip(alphas, loadings_intra_list): Gc += a * Gk
        loadings = Gc

    negative_vars = ['PPM', 'TPT', 'GK', 'PKKP', 'GR', 'Gini Ratio', 'Persentase Penduduk Miskin', 'Tingkat Pengangguran Terbuka']
    Zc = np.zeros_like(X_matrices[0])
    for a, Zk in zip(alphas, X_matrices): Zc += a * Zk
    Zc_proxy = Zc.copy()
    for i, var in enumerate(selected_vars):
        if any(neg.lower() in var.lower() for neg in negative_vars):
            Zc_proxy[:, i] *= -1
    mean_perf_c = Zc_proxy.mean(axis=1)

    # Bangun tables_std (Z-score per tahun) untuk dipakai di KMO section
    tables_std = []
    for Zk in X_matrices:
        tables_std.append(pd.DataFrame(Zk, index=obs_labels, columns=selected_vars))

    per_year_coords = {}
    per_year_loadings = {}
    for i, yr in enumerate(sheet_names):
        if SCENARIO == 'scenario1':
            fk = Ws[i] @ D_sqrt @ eig_vecs_c[:, :2] / sq2
            gk = loadings_intra_list[i]
        else:
            fk = scores_intra_list[i]
            gk = X_matrices[i].T @ D_diag_mat @ fk / sq2

        per_year_coords[yr] = fk
        per_year_loadings[yr] = gk

    # Flip PC1 agar orientasi konsisten: daerah dengan performa tinggi memiliki PC1 positif
    # Logika: mean_perf_c sudah dikoreksi tanda negatif untuk variabel buruk (GK, TPT, dll.)
    # Jika korelasi PC1 vs mean_perf_c negatif, berarti arah PC1 terbalik — flip konsisten.
    _corr_pc1 = np.corrcoef(scores_raw[:, 0], mean_perf_c)[0, 1]
    if _corr_pc1 < 0:
        scores_raw[:, 0] *= -1
        loadings[:, 0] *= -1
        for _yr in list(per_year_coords.keys()):
            per_year_coords[_yr][:, 0] *= -1
        for _yr in list(per_year_loadings.keys()):
            per_year_loadings[_yr][:, 0] *= -1
        print(f"  [INFO] PC1 di-flip (corr={_corr_pc1:.3f}) agar performa tinggi = PC1 positif.")

    # ============================================================
    # 5. EKSPOR TABEL STATIS ({SCENARIO})
    # ============================================================
    print("\n=== 5. Ekspor Tabel STATIS Skenario ===")
    
    # Alpha (Scenario specific because of host)
    df_alpha = pd.DataFrame({'Tahun': sheet_names, 'Bobot (Alpha)': [round(a, 4) for a in alphas]})
    save_tex_table(df_alpha, "output_table_alpha.tex", OUT_DIR, f"Nilai Bobot (Alpha) {SCENARIO}", "alpha", label_prefix=CUR_LABEL_PREFIX)
    
    # Eigen (Scenario specific)
    sq_full = np.sqrt(np.clip(eig_vals_c, 0, None))
    var_exp = eig_vals_c / eig_vals_c.sum() * 100
    df_eigen = pd.DataFrame({
        'Dimensi': [f'Dim {i+1}' for i in range(len(eig_vals_c))],
        'Eigenvalue': [round(v, 4) for v in eig_vals_c],
        'Varians (%)': [round(v, 2) for v in var_exp],
        'Kumulatif (%)': [round(v, 2) for v in np.cumsum(var_exp)]
    })
    save_tex_table(df_eigen, "output_table_eigen.tex", OUT_DIR, f"Dekomposisi Nilai Eigen ({SCENARIO})", "eigen", label_prefix=CUR_LABEL_PREFIX)
    
    # Loadings & Skor (Scenario specific)
    df_gc = pd.DataFrame(loadings, index=selected_vars, columns=['PC1', 'PC2']).reset_index()
    save_tex_table(df_gc, "output_table_loadings.tex", OUT_DIR, f"Loadings Kompromi ({SCENARIO})", "loadings", float_fmt="{:.4f}", label_prefix=CUR_LABEL_PREFIX)
    
    df_fc = pd.DataFrame(scores_raw, index=obs_labels, columns=['PC1', 'PC2']).reset_index()
    save_tex_table(df_fc, "output_table_scores.tex", OUT_DIR, f"Koordinat Skor Kompromi ({SCENARIO})", "scores", longtable=False, float_fmt="{:.4f}", label_prefix=CUR_LABEL_PREFIX)

    # ------------------------------------------------------------
    # Helpers for Plots
    # ------------------------------------------------------------
    def apply_visual_adjustments(scores, loads, norm=False, scale=True):
        ps, pl = scores.copy(), loads.copy()
        if norm:
            max_val = np.max(np.abs(ps)) if ps.size > 0 else 1
            if max_val > 0: ps = ps / max_val
        if scale:
            ms, ml = np.max(np.abs(ps)), np.max(np.abs(pl))
            if ml > 0: pl = pl * (ms / ml) * 0.8
        return ps, pl

    def compute_rotation(scores, loads, baseline_type, baseline_name):
        if not baseline_name: return 0.0
        vec = np.zeros(2)
        if baseline_type == 'loading' and baseline_name in selected_vars:
            vec = loads[selected_vars.index(baseline_name)].copy()
        elif baseline_type == 'skor' and baseline_name in obs_labels:
            vec = scores[obs_labels.index(baseline_name)].copy()
        return -np.arctan2(vec[1], vec[0]) if not np.allclose(vec, 0) else 0.0

    ROT_ANGLE = compute_rotation(scores_raw, loadings, BASELINE_TYPE, BASELINE_NAME)
    plot_scores, plot_loadings = apply_visual_adjustments(scores_raw, loadings, norm=NORM_SCORE, scale=SCALE_LOAD)
    
    if ROT_ANGLE != 0.0:
        R_rot = np.array([[np.cos(ROT_ANGLE), -np.sin(ROT_ANGLE)], [np.sin(ROT_ANGLE), np.cos(ROT_ANGLE)]])
        plot_scores, plot_loadings = plot_scores @ R_rot.T, plot_loadings @ R_rot.T
    
    per_year_coords_plot = {}
    per_year_loadings_plot = {}
    # --- Per-year rotation + mirror (matching app.py cb_update_statis_plots) ---
    # Step 1: rotate & mirror each year independently using per-year baseline angle
    _pc_list_rot, _load_list_rot = [], []
    for yr in sheet_names:
        _fk = per_year_coords[yr][:, :2].copy()
        _gk = per_year_loadings[yr][:, :2].copy()
        _angle = compute_rotation(_fk, _gk, BASELINE_TYPE, BASELINE_NAME)
        if _angle != 0.0:
            _Ryr = np.array([[np.cos(_angle), -np.sin(_angle)], [np.sin(_angle), np.cos(_angle)]])
            _fk = _fk @ _Ryr.T
            _gk = _gk @ _Ryr.T
        if yr in MIRROR_YEARS:
            _fk[:, 1] *= -1
            _gk[:, 1] *= -1
        _pc_list_rot.append(_fk)
        _load_list_rot.append(_gk)
    # Step 2: apply_visual_adjustments on stacked arrays (norm + scale globally, matching app.py)
    _pc_stacked  = np.vstack(_pc_list_rot)   if _pc_list_rot   else np.zeros((0, 2))
    _load_stacked = np.vstack(_load_list_rot) if _load_list_rot else np.zeros((0, 2))
    if _pc_stacked.shape[0] > 0:
        _pc_vis, _load_vis = apply_visual_adjustments(_pc_stacked, _load_stacked, norm=NORM_SCORE, scale=SCALE_LOAD)
    else:
        _pc_vis, _load_vis = _pc_stacked, _load_stacked
    # Step 3: split back into per-year dicts
    _n_obs = len(obs_labels)
    _n_vars = len(selected_vars)
    for _i, yr in enumerate(sheet_names):
        per_year_coords_plot[yr] = _pc_vis[_i*_n_obs:(_i+1)*_n_obs]
        per_year_loadings_plot[yr] = _load_vis[_i*_n_vars:(_i+1)*_n_vars]
    
    var_pct = eig_vals_c / eig_vals_c.sum() * 100
    ax_x, ax_y = f"Compromise 1 ({var_pct[0]:.2f}%)", f"Compromise 2 ({var_pct[1]:.2f}%)"
    
    print(f"  Alpha: {dict(zip(sheet_names, [round(a,4) for a in alphas]))}")
    print(f"  EigenVal[0] = {eig_vals_c[0]:.4f} ({var_pct[0]:.2f}%)")
    
    
    # (Redundant Part 3 removed, already handled in global and scenario specific parts)
    
    # ============================================================
    # 3b. PERBANDINGAN JARAK PCA UNWEIGHTED VS STATIS WEIGHTED & TABEL INTRA
    # ============================================================
    print("\n=== 3b. Tabel Jarak PCA vs STATIS & Tabel Intra ===")
    
    pca_scores_dict = {}
    pca_loadings_dict = {}
    from sklearn.decomposition import PCA
    for i, yr in enumerate(sheet_names):
        X = tables[yr][selected_vars].values
        X_std = StandardScaler().fit_transform(X)
        pca = PCA(n_components=2)
        scores_pca = pca.fit_transform(X_std)
        loadings_pca = pca.components_.T
        pca_scores_dict[yr] = scores_pca
        pca_loadings_dict[yr] = loadings_pca
    
    def apply_global_adjustments(pc_concat, load_concat, norm=False, scale=True):
        ps, pl = pc_concat.copy(), load_concat.copy()
        if norm:
            for col in range(ps.shape[1]):
                m_val = np.abs(ps[:, col]).max() if np.abs(ps[:, col]).max() > 0 else 1
                ps[:, col] = ps[:, col] / m_val
        if scale:
            ms = np.max(np.abs(ps))
            ml = np.max(np.abs(pl))
            if ml > 0:
                pl = pl * (ms / ml) * 0.8
        return ps, pl
    
    pca_pc_list, pca_load_list = [], []
    statis_pc_list, statis_load_list = [], []
    for yr in sheet_names:
        spca = pca_scores_dict[yr].copy()
        lpca = pca_loadings_dict[yr].copy()
        angle_pca = compute_baseline_angle(spca, lpca, obs_labels, selected_vars, BASELINE_TYPE, BASELINE_NAME) if BASELINE_NAME else 0
        if angle_pca != 0:
            spca = spca @ _rotation_matrix(angle_pca).T
            lpca = lpca @ _rotation_matrix(angle_pca).T
        if yr in MIRROR_YEARS:
            spca[:, 1] *= -1
            lpca[:, 1] *= -1
        pca_pc_list.append(spca)
        pca_load_list.append(lpca)
        
        sstatis = per_year_coords[yr][:,:2].copy()
        lstatis = per_year_loadings[yr][:,:2].copy()
        angle_stat = compute_baseline_angle(sstatis, lstatis, obs_labels, selected_vars, BASELINE_TYPE, BASELINE_NAME) if BASELINE_NAME else 0
        if angle_stat != 0:
            sstatis = sstatis @ _rotation_matrix(angle_stat).T
            lstatis = lstatis @ _rotation_matrix(angle_stat).T
        if yr in MIRROR_YEARS:
            sstatis[:, 1] *= -1
            lstatis[:, 1] *= -1
        statis_pc_list.append(sstatis)
        statis_load_list.append(lstatis)
    
    pca_pc_adj, pca_load_adj = apply_global_adjustments(np.vstack(pca_pc_list), np.vstack(pca_load_list), norm=NORM_SCORE, scale=SCALE_LOAD)
    statis_pc_adj, statis_load_adj = apply_global_adjustments(np.vstack(statis_pc_list), np.vstack(statis_load_list), norm=NORM_SCORE, scale=SCALE_LOAD)
    
    pca_pc_adj_dict = {}
    pca_load_adj_dict = {}
    
    n_obs = len(obs_labels)
    n_vars = len(selected_vars)
    for i, yr in enumerate(sheet_names):
        sp_adj = pca_pc_adj[i*n_obs:(i+1)*n_obs]
        ss_adj = statis_pc_adj[i*n_obs:(i+1)*n_obs]
        dist_scores = np.sqrt(np.sum((sp_adj - ss_adj)**2, axis=1))
        
        df_dist_scores = pd.DataFrame({
            'Kabupaten/Kota': obs_labels,
            'PC1 (PCA)': sp_adj[:, 0], 'PC2 (PCA)': sp_adj[:, 1],
            'PC1 (STATIS)': ss_adj[:, 0], 'PC2 (STATIS)': ss_adj[:, 1],
            'Jarak Euclidean ($d$)': dist_scores
        })
        
        lp_adj = pca_load_adj[i*n_vars:(i+1)*n_vars]
        ls_adj = statis_load_adj[i*n_vars:(i+1)*n_vars]
        dist_loads = np.sqrt(np.sum((lp_adj - ls_adj)**2, axis=1))
        
        pca_pc_adj_dict[yr] = sp_adj
        pca_load_adj_dict[yr] = lp_adj
        
        df_dist_loads = pd.DataFrame({
            'Indikator': selected_vars,
            'PC1 (PCA)': lp_adj[:, 0], 'PC2 (PCA)': lp_adj[:, 1],
            'PC1 (STATIS)': ls_adj[:, 0], 'PC2 (STATIS)': ls_adj[:, 1],
            'Jarak Euclidean ($d$)': dist_loads
        })
        save_tex_table(df_dist_scores, f"output_table_jarak_skor_{yr}.tex", OUT_DIR, f"Perbandingan Jarak Skor Objek (PCA vs STATIS) Tahun {yr}", f"jarak_skor_{yr}", float_fmt="{:.4f}", label_prefix=CUR_LABEL_PREFIX)
        save_tex_table(df_dist_loads, f"output_table_jarak_loading_{yr}.tex", OUT_DIR, f"Perbandingan Jarak Loading Indikator (PCA vs STATIS) Tahun {yr}", f"jarak_loading_{yr}", float_fmt="{:.4f}", label_prefix=CUR_LABEL_PREFIX)
    
        # Tabel Skor Intra (F_k)
        df_fk = pd.DataFrame(per_year_coords[yr][:, :2], index=obs_labels, columns=['PC1', 'PC2'])
        if ROT_ANGLE != 0.0 or yr in MIRROR_YEARS or NORM_SCORE or SCALE_LOAD:
            df_fk = pd.DataFrame(per_year_coords[yr][:, :2], index=obs_labels, columns=['PC1 (Asli)', 'PC2 (Asli)'])
            df_fk['PC1 (Disesuaikan)'] = ss_adj[:, 0]
            df_fk['PC2 (Disesuaikan)'] = ss_adj[:, 1]
        df_fk.index.name = 'Kabupaten/Kota'
        df_fk = df_fk.reset_index()
        
        # Tabel Loading Intra (G_k) - Koordinat indikator tahun t di ruang kompromi
        df_gk = pd.DataFrame(per_year_loadings[yr][:, :2], index=selected_vars, columns=['PC1', 'PC2'])
        if ROT_ANGLE != 0.0 or yr in MIRROR_YEARS or NORM_SCORE or SCALE_LOAD:
            df_gk = pd.DataFrame(per_year_loadings[yr][:, :2], index=selected_vars, columns=['PC1 (Asli)', 'PC2 (Asli)'])
            df_gk['PC1 (Disesuaikan)'] = ls_adj[:, 0]
            df_gk['PC2 (Disesuaikan)'] = ls_adj[:, 1]
        df_gk.index.name = 'Indikator'
        df_gk = df_gk.reset_index()

        save_tex_table(df_fk, f"output_table_skor_intra_{yr}.tex", OUT_DIR, fr"Skor Intra Tahun {yr} ($\mathbf{{F}}_{{{yr}}}$)", f"skor_intra_{yr}", float_fmt="{:.4f}", label_prefix=CUR_LABEL_PREFIX)
        save_tex_table(df_gk, f"output_table_loading_intra_{yr}.tex", OUT_DIR, fr"Loading Intra Tahun {yr} ($\mathbf{{G}}_{{{yr}}}$)", f"loading_intra_{yr}", float_fmt="{:.4f}", label_prefix=CUR_LABEL_PREFIX)
        
        # Matriks Intra-Loading S_k (Matriks Korelasi Terbobot Indikator - "Kebalikan" dari W_k)
        # Formula: S_k = Z_k^T * D * Z_k
        Sk = X_matrices[i].T @ np.diag(m_weights) @ X_matrices[i]
        df_sk_intra = pd.DataFrame(np.round(Sk, 6), index=selected_vars, columns=selected_vars)
        df_sk_intra.index.name = 'Indikator'
        df_sk_intra = df_sk_intra.reset_index()
        save_tex_table(df_sk_intra, f"output_table_matriks_intra_loading_{yr}.tex", OUT_DIR, fr"Matriks Korelasi Terbobot Indikator Tahun {yr} ($\mathbf{{S}}_{{{yr}}}$)", f"matriks_intra_loading_{yr}", float_fmt="{:.4f}", label_prefix=CUR_LABEL_PREFIX)
    
    # Statistika Deskriptif per tahun
    print("\n=== 3b. Tabel Statistika Deskriptif ===")
    for yr in sheet_names:
        df_y = tables[yr]
        rows = []
        for col in df_y.columns:
            vals = df_y[col].dropna().values
            rows.append({
                'Indikator': col,
                'Mean ($\\mu$)': round(float(np.mean(vals)), 4),
                'Std Dev ($\\sigma$)': round(float(np.std(vals, ddof=0)), 4),
                'Min': round(float(np.min(vals)), 4),
                'Q1': round(float(np.percentile(vals, 25)), 4),
                'Median': round(float(np.median(vals)), 4),
                'Q3': round(float(np.percentile(vals, 75)), 4),
                'Max': round(float(np.max(vals)), 4),
                'Skewness ($\\gamma_1$)': round(float(skew(vals)), 4),
                'Kurtosis ($\\gamma_2$)': round(float(kurt(vals, fisher=True)), 4),
                'CV (%)': round(float(np.std(vals, ddof=0) / np.mean(vals) * 100), 2) if np.mean(vals) != 0 else 0,
            })
        df_stats = pd.DataFrame(rows)
        # Gunakan adjustbox agar tidak melampaui margin halaman
        path_d = os.path.join(OUT_DIR, f"output_table_deskriptif_{yr}.tex")
        # Statistik deskriptif memiliki banyak kolom (12), sehingga butuh kolom c sempit
        cols_d = df_stats.columns.tolist()
        col_defs_d = r">{\centering\arraybackslash}" + "p{2.5cm}|" + "c|" * (len(cols_d)-1)
        if current_scenario == 'scenario1':
            with open(os.path.join(ROOT_OUT_DIR, f"output_table_deskriptif_{yr}.tex"), "w", encoding="utf-8") as f:
                f.write(r"\begin{adjustbox}{max width=\textwidth}" + "\n")
                f.write(r"\small" + "\n")
                f.write(r"\begin{tabular}{|" + col_defs_d + "}\n")
                f.write(r"\hline" + "\n")
                # Header dipersingkat agar tidak terlalu lebar
                short_headers = [escape_tex(c).replace('Skewness', 'Skew').replace('Kurtosis', 'Kurt') for c in cols_d]
                f.write(" & ".join([f"\\textbf{{{h}}}" for h in short_headers]) + r" \\" + "\n")
                f.write(r"\hline" + "\n")
                for _, row in df_stats.iterrows():
                    vals = []
                    for v in row:
                        if isinstance(v, float):
                            vals.append((f"{v:.4f}" if v < 100 else f"{v:.2f}").replace(".", ","))
                        else:
                            vals.append(escape_tex(v))
                    f.write(" & ".join([str(x) for x in vals]) + r" \\" + "\n")
                f.write(r"\hline" + "\n")
                f.write(r"\end{tabular}" + "\n")
                f.write(r"\end{adjustbox}" + "\n")
            print(f"  [TEX] output_table_deskriptif_{yr}.tex")
    
    
    # ============================================================
    # 3c. UJI KMO + BARTLETT PER TAHUN → .tex
    # ============================================================
    print("\n=== 3c. KMO & Bartlett per Tahun ===")
    from scipy.stats import chi2 as _chi2
    
    def calc_kmo(X):
        """Kaiser-Meyer-Olkin measure of sampling adequacy."""
        R = np.corrcoef(X.T)
        try:
            R_inv = np.linalg.inv(R)
        except np.linalg.LinAlgError:
            R_inv = np.linalg.pinv(R)
        p = R.shape[0]
        A = np.zeros_like(R)
        for i in range(p):
            for j in range(p):
                if i != j:
                    A[i, j] = -R_inv[i, j] / np.sqrt(R_inv[i, i] * R_inv[j, j])
        num = np.sum(R**2) - np.sum(np.diag(R)**2)
        den = num + np.sum(A**2) - np.sum(np.diag(A)**2)
        return float(num / den) if den != 0 else 0.0
    
    def kmo_label(kmo):
        if kmo >= 0.9: return "Sangat Baik"
        if kmo >= 0.8: return "Baik"
        if kmo >= 0.7: return "Cukup"
        if kmo >= 0.6: return "Sedang"
        if kmo >= 0.5: return "Cukup Memadai"
        return "Tidak Memadai"
    
    def calc_bartlett(X):
        """Bartlett's test of sphericity."""
        n, p = X.shape
        R = np.corrcoef(X.T)
        det = np.linalg.det(R)
        det = max(det, 1e-300)
        chi_sq = -(n - 1 - (2*p + 5)/6) * np.log(det)
        df = p * (p - 1) / 2
        p_val = 1 - _chi2.cdf(chi_sq, df)
        return float(chi_sq), int(df), float(p_val)
    
    kmo_rows = []
    for yr, dfstd in zip(sheet_names, tables_std):
        X = dfstd.values
        kmo_val = calc_kmo(X)
        chi_sq, df_b, p_b = calc_bartlett(X)
        kmo_rows.append({
            'Tahun': yr,
            'Nilai KMO': round(kmo_val, 4),
            'Interpretasi Nilai KMO': kmo_label(kmo_val),
            r'$\chi^2$ Bartlett': round(chi_sq, 2),
            'df': df_b,
            'P-Value Bartlett': float(p_b),
            'Keputusan': 'Layak' if kmo_val >= 0.5 and p_b < 0.05 else 'Periksa'
        })
    df_kmo = pd.DataFrame(kmo_rows)
    if IS_FIRST:
        save_tex_table(df_kmo, "output_table_kmo_bartlett.tex", ROOT_OUT_DIR,
                       "Hasil Uji KMO dan Uji Bartlett per Tahun", "kmo_bartlett", label_prefix=CUR_LABEL_PREFIX)
    print(f"  KMO range: {min(r['Nilai KMO'] for r in kmo_rows):.4f} - {max(r['Nilai KMO'] for r in kmo_rows):.4f}")
    
    # EKSPOR MATRIKS KOMPROMI (G_c, V_c, F_c) per skenario (berbeda tiap s1/s2)
    export_matrix_pmatrix(loadings, "matrix_G_c.tex", OUT_DIR)
    export_matrix_pmatrix(Vc_vars, "matrix_V_c.tex", OUT_DIR)
    export_matrix_pmatrix(scores_raw, "matrix_F_c.tex", OUT_DIR)
 
    # 3d. FILE MAKRO LaTeX (output_macros.tex)
    # ============================================================
    print("\n=== 3d. Ekspor Makro LaTeX ===")
    
    # Hitung nilai-nilai ringkasan untuk makro
    alpha_dict = dict(zip(sheet_names, alphas))
    alpha_min_yr = min(alpha_dict, key=alpha_dict.get)
    alpha_max_yr = max(alpha_dict, key=alpha_dict.get)
    alpha_min_val = alpha_dict[alpha_min_yr]
    alpha_max_val = alpha_dict[alpha_max_yr]
    
    # RV: min off-diagonal (gunakan RV_mat yang sesuai skenario, bukan R lokal KMO)
    R_off = RV_mat.copy(); np.fill_diagonal(R_off, np.nan)
    rv_min = float(np.nanmin(R_off))
    rv_max = float(np.nanmax(R_off))
    
    # Variance explained
    var_exp_macro = eig_vals_c / eig_vals_c.sum() * 100
    dim1_pct = var_exp_macro[0]
    dim2_pct = var_exp_macro[1]
    cum2_pct = dim1_pct + dim2_pct
    
    # KMO stats
    kmo_vals = [r['Nilai KMO'] for r in kmo_rows]
    kmo_avg = float(np.mean(kmo_vals))
    kmo_min = min(kmo_vals); kmo_max = max(kmo_vals)
    
    def get_macro_name(base):
        prefix = LABEL_PREFIX.capitalize() if LABEL_PREFIX else "Macro"
        return f"{prefix}{base}"
    
    macro_lines = [
        r"% AUTO-GENERATED BY export_all.py — DO NOT EDIT MANUALLY",
        f"% Macro ini digunakan di tex dengan prefix: {LABEL_PREFIX}",
        "",
        f"\\newcommand{{\\{get_macro_name('AlphaMin')}}}{{{f'{alpha_min_val:.4f}'.replace('.', ',')}}}",
        f"\\newcommand{{\\{get_macro_name('AlphaMax')}}}{{{f'{alpha_max_val:.4f}'.replace('.', ',')}}}",
        f"\\newcommand{{\\{get_macro_name('AlphaMaxYear')}}}{{{alpha_max_yr}}}",
        f"\\newcommand{{\\{get_macro_name('RVMin')}}}{{{f'{rv_min:.4f}'.replace('.', ',')}}}",
        f"\\newcommand{{\\{get_macro_name('RVMax')}}}{{{f'{rv_max:.4f}'.replace('.', ',')}}}",
        f"\\newcommand{{\\{get_macro_name('DimOnePct')}}}{{{f'{dim1_pct:.2f}'.replace('.', ',')}}}",
        f"\\newcommand{{\\{get_macro_name('DimTwoPct')}}}{{{f'{dim2_pct:.2f}'.replace('.', ',')}}}",
        f"\\newcommand{{\\{get_macro_name('CumTwoPct')}}}{{{f'{cum2_pct:.2f}'.replace('.', ',')}}}",
        f"\\newcommand{{\\{get_macro_name('LambdaObs')}}}{{{f'{eig_vals_c[0]:.4f}'.replace('.', ',')}}}",
        f"\\newcommand{{\\{get_macro_name('PValuePerm')}}}{{0{{,}}0010}}",
        f"\\newcommand{{\\{get_macro_name('KMOAvg')}}}{{{f'{kmo_avg:.4f}'.replace('.', ',')}}}",
        f"\\newcommand{{\\{get_macro_name('KMOMin')}}}{{{f'{kmo_min:.4f}'.replace('.', ',')}}}",
        f"\\newcommand{{\\{get_macro_name('KMOMax')}}}{{{f'{kmo_max:.4f}'.replace('.', ',')}}}",
        f"\\newcommand{{\\{get_macro_name('KMOInterpret')}}}{{{kmo_label(kmo_avg)}}}",
        "",
    ]
    # Tulis ke folder skenario masing-masing (Wilayah / Indikator)
    with open(os.path.join(OUT_DIR, "output_macros.tex"), "w", encoding="utf-8") as f:
        f.write("\n".join(macro_lines))
    print(f"  [TEX] {os.path.join(OUT_DIR, 'output_macros.tex')}")
    
    
    # ============================================================
    # 3e. ANALISIS VEKTOR STRUKTUR (Areia et al. 2008; Oliveira et al. 2024)
    # ============================================================
    print("\n=== 3e. Analisis Vektor Struktur (Inferensial STATIS) ===")
    
    # Bangun province_map secara otomatis dari data Excel (kolom 'Provinsi')
    # Jika kolom 'Provinsi' tidak tersedia, analisis transversal dilewati
    _province_map = None
    try:
        _first_sheet_raw = pd.read_excel(DATA_PATH, sheet_name=sheet_names[0])
        if 'Kabupaten/Kota' in _first_sheet_raw.columns and 'Provinsi' in _first_sheet_raw.columns:
            _first_sheet_raw = _first_sheet_raw.set_index('Kabupaten/Kota')
            # Hanya wilayah yang ada di obs_labels
            _prov_series = _first_sheet_raw.loc[
                [idx for idx in obs_labels if idx in _first_sheet_raw.index], 'Provinsi'
            ]
            _province_map = {}
            for wilayah, prov in _prov_series.items():
                prov_str = str(prov).strip()
                _province_map.setdefault(prov_str, []).append(wilayah)
            print(f"  [INFO] Province map: { {p: len(v) for p,v in _province_map.items()} }")
        else:
            print("  [INFO] Kolom 'Provinsi' tidak ditemukan — analisis transversal dilewati.")
    except Exception as _e:
        print(f"  [WARN] Gagal membaca province_map: {_e}")
    
    # Import fungsi dari app.py (pastikan path web/app.py dapat diakses)
    import importlib.util as _ilu
    _app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'web', 'app.py')
    _sv_compute = None
    _sv_export   = None
    try:
        _spec = _ilu.spec_from_file_location("app_statis", _app_path)
        _app_mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_app_mod)
        _sv_compute = _app_mod.compute_structure_vector
        _sv_export  = _app_mod.export_structure_vector_latex
        print("  [OK] Fungsi compute_structure_vector & export_structure_vector_latex dimuat dari app.py.")
    except Exception as _e_load:
        print(f"  [WARN] Gagal memuat dari app.py: {_e_load}. Komputasi inline...")
    
        # Fallback: definisi inline ringkas agar export_all.py tetap mandiri
        def _sv_compute(H, _alphas, sheet_names, X_matrices, m_weights, obs_labels, province_map=None, scenario='scenario1'):
            _ = _alphas  # unused in fallback; kept for API compatibility with app.compute_structure_vector
            K = len(sheet_names)
            H = np.array(H)
            vals, vecs = np.linalg.eigh(H)
            idx_s = np.argsort(vals)[::-1]
            vals, vecs = vals[idx_s], vecs[:, idx_s]
            l1, u1 = vals[0], vecs[:, 0]
            if u1.sum() < 0: u1 = -u1
            beta = l1 * u1
            H2 = np.trace(H @ H)
            V  = H2 - l1**2
            sum_l = np.sum(np.clip(vals, 0, None))
            inertia1 = l1 / sum_l if sum_l > 0 else np.nan
            dom_r = l1 / vals[1] if K > 1 and vals[1] > 1e-12 else np.inf
            beta_prov = {}
            if province_map:
                for pname, pwilayah in province_map.items():
                    pidx = [i for i, lb in enumerate(obs_labels) if lb in pwilayah]
                    if len(pidx) < 2: continue
                    ms = m_weights[pidx]; ms = ms / ms.sum()
                    if scenario == 'scenario1':
                        Dss = np.diag(np.sqrt(ms))
                        Ws_sub = [Dss @ Xk[pidx, :] for Xk in X_matrices]
                        Ws_sub = [W @ W.T for W in Ws_sub]
                        Hs = np.array([[np.trace(Ws_sub[i] @ Ws_sub[j]) for j in range(K)] for i in range(K)])
                    else:
                        Ss_sub = [Xk[pidx, :].T @ np.diag(ms) @ Xk[pidx, :] for Xk in X_matrices]
                        Hs = np.array([[np.trace(Ss_sub[i] @ Ss_sub[j]) for j in range(K)] for i in range(K)])
                    vs_h, ve_h = np.linalg.eigh(Hs)
                    i_s = np.argsort(vs_h)[::-1]
                    l1s, u1s = vs_h[i_s[0]], ve_h[:, i_s[0]]
                    if u1s.sum() < 0: u1s = -u1s
                    beta_prov[pname] = l1s * u1s
            return {'lambda1': l1, 'u1': u1, 'beta_tilde': beta, 'H_frobenius_sq': H2,
                    'V': V, 'inertia1': inertia1, 'dominance_ratio': dom_r,
                    'vals_H': vals, 'sheet_names': sheet_names, 'beta_provinsi': beta_prov}
    
        def _sv_export(sv_res, output_dir=OUT_DIR, label_prefix=""):
            # Ekspor versi minimal (tabel saja, tanpa plot warna)
            sn = sv_res['sheet_names']; bt = sv_res['beta_tilde']
            def _w(rows, cols, caption, label, fname):
                lines = [r"\begin{table}[H]", r"\centering", r"\small",
                         fr"\caption{{{escape_tex(caption)}}} \label{{tab:{label_prefix}{label}}}",
                         r"\begin{tabular}{|" + "c|"*len(cols) + "}",
                         r"\hline",
                         " & ".join([fr"\textbf{{{c}}}" for c in cols]) + r" \\",
                         r"\hline"]
                import re
                for row in rows:
                    row_vals = [re.sub(r'(\d)\.(\d)', r'\1,\2', str(v)) for v in row]
                    lines.append(" & ".join(row_vals) + r" \\")
                lines += [r"\hline", r"\end{tabular}", r"\end{table}"]
                with open(os.path.join(output_dir, fname), "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
                print(f"  [TEX] {fname}")
            _w([[yr, f"{b:.4f}"] for yr, b in zip(sn, bt)],
               ["Tahun ($k$)", r"$\tilde{\beta}_k$"],
               r"Komponen Vektor Struktur $\tilde{\boldsymbol{\beta}}$", "beta_vec",
               "output_table_beta_vec.tex")
            l1, Hf, V, i1, dr = (sv_res['lambda1'], sv_res['H_frobenius_sq'],
                                  sv_res['V'], sv_res['inertia1'], sv_res['dominance_ratio'])
            Vr = V/Hf if Hf > 0 else float('nan')
            _w([[r"$\lambda_1$", f"{l1:.4f}"], [r"$\|\mathbf{H}\|_F^2$", f"{Hf:.4f}"],
                ["$V$", f"{V:.4f}"], [r"Rasio $V/\|\mathbf{H}\|_F^2$", f"{Vr:.4f}"],
                [r"Inertia$_1$", f"{i1*100:.2f}\\%"],
                [r"$\lambda_1/\lambda_2$", f"{dr:.4f}" if np.isfinite(dr) else r"$\infty$"]],
               ["Kuantitas", "Nilai"],
               r"Diagnostik Dominansi Model Rank-1 (Areia \textit{et al.}, 2008)", "struktur_diagnostik",
               "output_table_struktur_diagnostik.tex")
            bp = sv_res.get('beta_provinsi', {})
            if bp:
                pns = list(bp.keys())
                _w([[yr] + [f"{bp[p][ki]:.4f}" if ki < len(bp[p]) else "-"
                            for p in pns] for ki, yr in enumerate(sn)],
                   ["Tahun ($k$)"] + pns,
                   r"Komponen $\tilde{\beta}_{gk}$ per Provinsi (Analisis Transversal)",
                   "beta_provinsi", "output_table_beta_provinsi.tex")
            # Plot
            try:
                fig2, ax2 = plt.subplots(figsize=(7, 4))
                ax2.plot(range(len(sn)), bt, 'o-', color='#1976D2', lw=2, ms=8,
                         label=r'$\tilde{\beta}_k$ (Gabungan)')
                colors_p = ['#D81B60', '#43A047', '#FB8C00']
                for (pn, bts), col in zip(bp.items(), colors_p):
                    if len(bts) == len(sn):
                        ax2.plot(range(len(sn)), bts, 's--', color=col, lw=1.5, ms=6,
                                 label=fr'$\tilde{{\beta}}_{{gk}}$ {pn}', alpha=0.85)
                ax2.set_xticks(range(len(sn))); ax2.set_xticklabels(sn, fontsize=10)
                ax2.set_xlabel("Tahun ($k$)"); ax2.set_ylabel(r"$\tilde{\beta}_k$")
                ax2.set_title(r"Lintasan Temporal Komponen Vektor Struktur $\tilde{\boldsymbol{\beta}}$",
                              fontweight='bold')
                ax2.legend(fontsize=9); ax2.grid(True, ls='--', alpha=0.5)
                ax2.spines['top'].set_visible(False); ax2.spines['right'].set_visible(False)
                fig2.tight_layout()
                fig2.savefig(os.path.join(output_dir, "beta_trajectory.png"), dpi=150, bbox_inches='tight')
                plt.close(fig2)
                print("  [PNG] beta_trajectory.png")
            except Exception as _ep:
                print(f"  [WARN] Gagal simpan beta_trajectory.png: {_ep}")
    
    # Jalankan komputasi dan ekspor vektor struktur
    try:
        sv_result = _sv_compute(
            H=H_mat.tolist(),
            alphas=alphas.tolist(),
            sheet_names=sheet_names,
            X_matrices=X_matrices,
            m_weights=m_weights,
            obs_labels=obs_labels,
            province_map=_province_map,
            scenario=SCENARIO
        )
        _sv_export(sv_result, output_dir=OUT_DIR, label_prefix=CUR_LABEL_PREFIX)
        print(f"  [OK] lambda1={sv_result['lambda1']:.4f}, "
              f"Inertia1={sv_result['inertia1']*100:.2f}%, "
              f"V={sv_result['V']:.4f}")
    except Exception as _e_sv:
        print(f"  [ERR] Analisis vektor struktur gagal: {_e_sv}")
    
    
    # ============================================================
    print("\n=== 4. Ekspor Gambar STATIS ===")
    
    eigenvalues_subset = eig_vals_c[:10]
    cumulative_subset = np.cumsum(var_exp[:10])
    eigen_texts = [f"{v:.4f}".replace('.', ',') for v in eigenvalues_subset]
    cum_texts = [f"{v:.2f}%".replace('.', ',') for v in cumulative_subset]
    
    fig_scree = go.Figure()
    fig_scree.add_trace(go.Bar(
        x=[f"Dim {i+1}" for i in range(min(10, len(eig_vals_c)))],
        y=eigenvalues_subset, 
        marker_color='#1976D2', 
        name='Eigenvalue',
        text=eigen_texts,
        textposition='outside'
    ))
    fig_scree.add_trace(go.Scatter(
        x=[f"Dim {i+1}" for i in range(min(10, len(eig_vals_c)))],
        y=cumulative_subset, 
        mode='lines+markers+text',
        marker=dict(color='#E91E63', size=8), 
        name='Kumulatif (%)', 
        yaxis='y2',
        text=cum_texts,
        textposition='top center'
    ))
    fig_scree.update_layout(
        title="Scree Plot — Eigenvalue Matriks Kompromi",
        xaxis_title="Dimensi", yaxis_title="Eigenvalue",
        yaxis2=dict(title='Kumulatif (%)', overlaying='y', side='right', range=[0, 110]),
        template='plotly_white', legend=dict(x=0.6, y=0.5)
    )
    
    # --- Heatmap RV ---
    fig_rv_heat = px.imshow(
        np.round(RV_mat, 4), text_auto=True,
        x=sheet_names, y=sheet_names,
        color_continuous_scale='Blues',
        title="Heatmap Koefisien RV Antar-Tahun"
    )
    fig_rv_heat.update_layout(template='plotly_white')

    save_png(fig_scree, "scree_plot.png", OUT_DIR)
    save_png(fig_rv_heat, "rv_heatmap.png", OUT_DIR, width=700, height=600)
    
    # --- Biplot Kompromi (Versi Matplotlib Statik untuk LaTeX) ---
    def draw_biplot_matplotlib(plot_scores, plot_loadings, obs_labels, selected_vars, ax_x_label, ax_y_label, out_path):
        import matplotlib.pyplot as plt
        import matplotlib.patheffects as pe
        
        BG_COLOR = '#FAFAFA'
        GRID_COLOR = '#E0E0E0'
        
        fig, ax = plt.subplots(figsize=(13, 11))
        fig.patch.set_facecolor(BG_COLOR)
        ax.set_facecolor(BG_COLOR)
        
        ax.axhline(0, color=GRID_COLOR, linewidth=1.2, zorder=1)
        ax.axvline(0, color=GRID_COLOR, linewidth=1.2, zorder=1)
        ax.grid(True, color=GRID_COLOR, linewidth=0.6, linestyle='--', alpha=0.7, zorder=0)
        
        # 1. Titik objek (skor kompromi) dengan pembedaan highlight
        for i, label in enumerate(obs_labels):
            is_hl = label in HIGHLIGHT_OBJECTS
            ax.scatter(plot_scores[i, 0], plot_scores[i, 1],
                       color='#E53935' if is_hl else '#1E88E5',
                       s=110 if is_hl else 50,
                       alpha=0.95 if is_hl else 0.75,
                       zorder=4 if is_hl else 3,
                       edgecolors='white', linewidths=0.5)
        
        # 2. Label Objek dengan koordinat untuk highlight
        for i, txt in enumerate(obs_labels):
            is_hl = txt in HIGHLIGHT_OBJECTS
            lbl = f"{txt} ({plot_scores[i, 0]:.2f}, {plot_scores[i, 1]:.2f})" if is_hl else txt
            ax.annotate(lbl, (plot_scores[i, 0], plot_scores[i, 1]),
                        xytext=(0, 6), textcoords='offset points',
                        ha='center', va='bottom',
                        fontsize=9.5 if is_hl else 8,
                        color='#D32F2F' if is_hl else '#333333',
                        fontweight='bold' if is_hl else 'normal',
                        path_effects=[pe.withStroke(linewidth=2 if is_hl else 1.5, foreground='white')],
                        zorder=5 if is_hl else 4)
                        
        # 3. Vektor Indikator (Loading) dengan koordinat dan pembedaan highlight
        for i, var in enumerate(selected_vars):
            is_hl_var = var in HIGHLIGHT_VARS
            line_color = '#D81B60' if is_hl_var else '#F06292'
            line_width = 3.5 if is_hl_var else 1.8
            
            # Garis
            ax.plot([0, plot_loadings[i, 0]], [0, plot_loadings[i, 1]], color=line_color, linewidth=line_width, zorder=4)
            # Panah
            ax.annotate('', xy=(plot_loadings[i, 0], plot_loadings[i, 1]), xytext=(0, 0),
                        arrowprops=dict(arrowstyle="->", color=line_color, lw=line_width, mutation_scale=15),
                        zorder=4)
            # Label Indikator
            var_lbl = f"{var} ({plot_loadings[i, 0]:.2f}, {plot_loadings[i, 1]:.2f})" if is_hl_var else var
            ax.annotate(var_lbl, (plot_loadings[i, 0], plot_loadings[i, 1]),
                        xytext=(0, 8), textcoords='offset points',
                        ha='center', va='bottom',
                        fontsize=11 if is_hl_var else 9.5,
                        color='#880E4F' if is_hl_var else '#C2185B',
                        fontweight='bold',
                        path_effects=[pe.withStroke(linewidth=3, foreground='white')],
                        zorder=5)
                        
        ax.set_xlabel(ax_x_label, fontsize=12, labelpad=10)
        ax.set_ylabel(ax_y_label, fontsize=12, labelpad=10)
        ax.set_title('Compromise Biplot (Skor dan Loading)', fontsize=15, fontweight='bold', pad=15)
        
        for spine in ax.spines.values():
            spine.set_edgecolor(GRID_COLOR)
            
        plt.tight_layout(pad=2)
        plt.savefig(out_path, dpi=250, bbox_inches='tight', facecolor=BG_COLOR)
        plt.close(fig)
        print(f"  [PNG] {os.path.basename(out_path)}")
    
    draw_biplot_matplotlib(plot_scores, plot_loadings, obs_labels, selected_vars, ax_x, ax_y, 
                           os.path.join(OUT_DIR, "compromise_biplot.png"))
    
    # --- Variable Contribution ---
    contrib = (loadings ** 2) / np.sum(loadings ** 2, axis=0)
    fig_contrib = px.bar(x=selected_vars, y=contrib[:, 0] * 100,
                         labels={'x': 'Indikator', 'y': 'Kontribusi ke PC1 (%)'},
                         title="Kontribusi Indikator terhadap Dimensi 1",
                         color=contrib[:, 0] * 100, color_continuous_scale='Blues')
    fig_contrib.update_traces(text=[f"{v:.2f}%" for v in contrib[:, 0] * 100], textposition='outside')
    fig_contrib.update_layout(template='plotly_white', uniformtext_minsize=8, uniformtext_mode='hide')
    save_png(fig_contrib, "variable_contribution.png", OUT_DIR)

    # --- Cos2 ---
    cos2 = loadings ** 2
    fig_cos2 = px.bar(x=selected_vars, y=cos2[:, 0],
                      labels={'x': 'Indikator', 'y': 'Cos² (PC1)'},
                      title="Kualitas Representasi Indikator (Cos²)",
                      color=cos2[:, 0], color_continuous_scale='Oranges')
    fig_cos2.update_traces(text=[f"{v:.4f}" for v in cos2[:, 0]], textposition='outside')
    fig_cos2.update_layout(template='plotly_white', uniformtext_minsize=8, uniformtext_mode='hide')
    save_png(fig_cos2, "variable_cos2.png", OUT_DIR)
    
    # --- Inter-struktur (heatmap with bar annotation, already saved as rv_heatmap) ---
    # --- STATIS Trajectories ---
    df_traj_list = []
    for yr, coords in per_year_coords_plot.items():
        c = np.array(coords)
        df_t = pd.DataFrame(c[:, :2], columns=['PC1', 'PC2'])
        df_t['Kabupaten/Kota'] = obs_labels
        df_t['Tahun'] = yr
        df_traj_list.append(df_t)
    df_traj = pd.concat(df_traj_list)
    
    # --- Pre-calculate Trajectory Clusters for coloring (from Part 7) ---
    # Weighted Trajectory per Lavit (1994) - Matching app.py logic
    X_traj_list = []
    for i, yr in enumerate(sheet_names):
        # Apply interstructure weights: dist^2 = sum( alpha_k * ||x_ik - x_jk||^2 )
        # To handle this with standard KMeans, we multiply coordinates by sqrt(alpha)
        w = np.sqrt(alphas[i])
        X_traj_list.append(per_year_coords[yr][:, :2] * w)
    X_traj = np.hstack(X_traj_list)
    
    km_traj = KMeans(n_clusters=K_CLUSTERS, random_state=42, n_init=10)
    labels_traj_raw = km_traj.fit_predict(X_traj)
    
    # Re-ranking otomatis untuk trajektori (berdasarkan rata-rata PC1 skor kompromi)
    cluster_means_t = []
    for cl in range(K_CLUSTERS):
        cluster_means_t.append(np.mean(scores_raw[labels_traj_raw == cl, 0]))
    sorted_idx_t = np.argsort(cluster_means_t)
    rank_map_t = {old_val: rank for rank, old_val in enumerate(sorted_idx_t)}
    cluster_traj = np.array([rank_map_t[l] for l in labels_traj_raw])
    
    palette_cluster = ['#EF5350', '#FFB300', '#4CAF50', '#42A5F5', '#8E24AA'] # Matching app.py colors: Red, Orange, Green, Blue, Purple
    
    # Attach province metadata to df_traj for province-based coloring
    province_by_obs = {}
    if _province_map:
        for prov, areas in _province_map.items():
            for area in areas:
                province_by_obs[area] = prov
    df_traj['Provinsi'] = df_traj['Kabupaten/Kota'].map(province_by_obs).fillna('Unknown')

    # Build province color palette
    prov_names = sorted(df_traj['Provinsi'].unique())
    prov_palette = px.colors.qualitative.Plotly
    province_color_map = {prov: prov_palette[i % len(prov_palette)] for i, prov in enumerate(prov_names)}

    fig_traj = go.Figure()
    shown_provinces = set()
    for i, obj in enumerate(obs_labels):
        d_obj = df_traj[df_traj['Kabupaten/Kota'] == obj].sort_values('Tahun')
        if d_obj.empty:
            continue
        prov = d_obj['Provinsi'].iloc[0]
        color = province_color_map.get(prov, '#808080')
        symbols = ['circle'] * (len(d_obj) - 1) + ['square']
        showlegend = prov not in shown_provinces
        shown_provinces.add(prov)

        fig_traj.add_trace(go.Scatter(
            x=d_obj['PC1'], y=d_obj['PC2'],
            mode='lines+markers',
            name=prov,
            legendgroup=prov,
            line=dict(width=1.8, color=color),
            marker=dict(size=7, symbol=symbols, color=color),
            hoverinfo='text',
            hovertext=[f"{obj} ({y})<br>PC1: {x:.3f}<br>PC2: {y2:.3f}" for y, x, y2 in zip(d_obj['Tahun'], d_obj['PC1'], d_obj['PC2'])],
            showlegend=showlegend
        ))
    # Tambahkan anotasi koordinat untuk objek yang di-highlight
    for obj_hl in HIGHLIGHT_OBJECTS:
        d_hl = df_traj[df_traj['Kabupaten/Kota'] == obj_hl].sort_values('Tahun')
        for _, row_hl in d_hl.iterrows():
            fig_traj.add_annotation(
                x=row_hl['PC1'], y=row_hl['PC2'],
                text=f"<b>{obj_hl} ({row_hl['PC1']:.2f}, {row_hl['PC2']:.2f}) [{row_hl['Tahun']}]</b>",
                showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1.5,
                ax=20, ay=-35,
                font=dict(size=9, color='black'),
                bgcolor='rgba(255,255,255,0.85)',
                bordercolor='#333333', borderwidth=1, borderpad=3
            )
    fig_traj.update_layout(
        title='Trajectory Scores (Province-colored)',
        template='plotly_white',
        xaxis=dict(scaleanchor='y', scaleratio=1),
        xaxis_title=ax_x, yaxis_title=ax_y
    )
    save_png(fig_traj, "trajectory_scores.png", OUT_DIR, width=900, height=800)
    
    
    # --- Static Trajectory Loadings Plot ---
    print("\n=== 4a. Trajectory Loadings (Static) ===")
    df_loadings_traj_list = []
    for yr in sheet_names:
        # Use per_year_loadings_plot which already has per-year rotation + mirror + visual adjustments
        gk_vis = per_year_loadings_plot[yr]
        df_g = pd.DataFrame(gk_vis[:, :2], index=selected_vars, columns=['PC1', 'PC2']).reset_index()
        df_g = df_g.rename(columns={'index': 'Variabel'})
        df_g['Tahun'] = yr
        df_loadings_traj_list.append(df_g)

    if df_loadings_traj_list:
        df_loadings_traj = pd.concat(df_loadings_traj_list, ignore_index=True)
        fig_load = go.Figure()
        var_palette = px.colors.qualitative.Plotly
        for i, var in enumerate(selected_vars):
            d_var = df_loadings_traj[df_loadings_traj['Variabel'] == var].sort_values('Tahun')
            if d_var.empty:
                continue
            fig_load.add_trace(go.Scatter(
                x=d_var['PC1'], y=d_var['PC2'],
                mode='lines+markers',
                name=var,
                line=dict(width=1.8, color=var_palette[i % len(var_palette)]),
                marker=dict(size=7, symbol='circle', color=var_palette[i % len(var_palette)]),
                hoverinfo='text',
                hovertext=[f"{var} ({y})<br>PC1: {x:.3f}<br>PC2: {y2:.3f}" for y, x, y2 in zip(d_var['Tahun'], d_var['PC1'], d_var['PC2'])]
            ))
        # Tambahkan anotasi koordinat untuk variabel yang di-highlight
        for var_hl in HIGHLIGHT_VARS:
            d_hl_var = df_loadings_traj[df_loadings_traj['Variabel'] == var_hl].sort_values('Tahun')
            for _, row_hl in d_hl_var.iterrows():
                fig_load.add_annotation(
                    x=row_hl['PC1'], y=row_hl['PC2'],
                    text=f"<b>{var_hl} ({row_hl['PC1']:.2f}, {row_hl['PC2']:.2f}) [{row_hl['Tahun']}]</b>",
                    showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1.5,
                    ax=20, ay=-35,
                    font=dict(size=9, color='black'),
                    bgcolor='rgba(255,255,255,0.85)',
                    bordercolor='#333333', borderwidth=1, borderpad=3
                )
        fig_load.update_layout(
            title='Trajectory Loadings (Variable-colored)',
            template='plotly_white',
            xaxis=dict(scaleanchor='y', scaleratio=1),
            xaxis_title='PC1', yaxis_title='PC2'
        )
        save_png(fig_load, "trajectory_loadings.png", OUT_DIR, width=900, height=800)

    # --- Snapshot Biplot 2D per Tahun ---
    print("\n=== 4b. Snapshot Biplot per Tahun ===")
    for yr in sheet_names:
        # Gunakan per_year_coords_plot & per_year_loadings_plot:
        # sudah ada rotasi per-tahun + mirror + apply_visual_adjustments (norm/scale)
        ps_y = per_year_coords_plot[yr]
        pl_y = per_year_loadings_plot[yr]
        
        # Format text and sizes for objects in yearly biplots
        obj_text = []
        obj_sizes = []
        obj_colors = []
        for j, label in enumerate(obs_labels):
            if label in HIGHLIGHT_OBJECTS:
                obj_text.append(f"<b>{label} ({ps_y[j, 0]:.2f}, {ps_y[j, 1]:.2f})</b>")
                obj_sizes.append(12)
                obj_colors.append('#E53935')
            else:
                obj_text.append(label)
                obj_sizes.append(7)
                obj_colors.append('#1E88E5')
        
        fig_yr = go.Figure()
        fig_yr.add_trace(go.Scatter(
            x=ps_y[:, 0], y=ps_y[:, 1],
            mode='markers+text', text=obj_text, textposition='top center',
            textfont=dict(size=9, color='black'),
            marker=dict(size=obj_sizes, color=obj_colors), name='Objek'
        ))
        
        for j, var in enumerate(selected_vars):
            is_hl_var = var in HIGHLIGHT_VARS
            var_lbl = f"<b>{var} ({pl_y[j, 0]:.2f}, {pl_y[j, 1]:.2f})</b>" if is_hl_var else var
            fig_yr.add_trace(go.Scatter(
                x=[0, pl_y[j, 0]], y=[0, pl_y[j, 1]],
                mode='lines+markers+text', text=['', var_lbl], textposition='top center',
                textfont=dict(size=10, color='black'),
                line=dict(color='#D81B60' if is_hl_var else '#F06292',
                          width=3 if is_hl_var else 1.5),
                showlegend=False
            ))
        fig_yr.add_hline(y=0, line_dash='dot', line_color='gray')
        fig_yr.add_vline(x=0, line_dash='dot', line_color='gray')
        fig_yr.update_layout(title=f"Biplot Tahunan — Tahun {yr}",
                             xaxis_title=ax_x, yaxis_title=ax_y, template='plotly_white',
                             xaxis=dict(scaleanchor='y', scaleratio=1))
        save_png(fig_yr, f"biplot_tahun_{yr}.png", OUT_DIR, width=800, height=800)
        
        # Generate unweighted yearly biplot in root (only when IS_FIRST)
        if IS_FIRST:
            ps_y_un, pl_y_un = pca_pc_adj_dict[yr], pca_load_adj_dict[yr]
            
            # Format text and sizes for objects in unweighted yearly biplot
            obj_text_un = []
            obj_sizes_un = []
            obj_colors_un = []
            for j, label in enumerate(obs_labels):
                if label in HIGHLIGHT_OBJECTS:
                    obj_text_un.append(f"<b>{label} ({ps_y_un[j, 0]:.2f}, {ps_y_un[j, 1]:.2f})</b>")
                    obj_sizes_un.append(12)
                    obj_colors_un.append('#E53935')
                else:
                    obj_text_un.append(label)
                    obj_sizes_un.append(7)
                    obj_colors_un.append('#1E88E5')
            
            fig_yr_un = go.Figure()
            fig_yr_un.add_trace(go.Scatter(
                x=ps_y_un[:, 0], y=ps_y_un[:, 1],
                mode='markers+text', text=obj_text_un, textposition='top center',
                textfont=dict(size=9, color='black'),
                marker=dict(size=obj_sizes_un, color=obj_colors_un), name='Objek'
            ))
            
            for j, var in enumerate(selected_vars):
                is_hl_var = var in HIGHLIGHT_VARS
                var_lbl = f"<b>{var} ({pl_y_un[j, 0]:.2f}, {pl_y_un[j, 1]:.2f})</b>" if is_hl_var else var
                fig_yr_un.add_trace(go.Scatter(
                    x=[0, pl_y_un[j, 0]], y=[0, pl_y_un[j, 1]],
                    mode='lines+markers+text', text=['', var_lbl], textposition='top center',
                    textfont=dict(size=10, color='black'),
                    line=dict(color='#D81B60' if is_hl_var else '#F06292',
                              width=3 if is_hl_var else 1.5),
                    showlegend=False
                ))
            fig_yr_un.add_hline(y=0, line_dash='dot', line_color='gray')
            fig_yr_un.add_vline(x=0, line_dash='dot', line_color='gray')
            fig_yr_un.update_layout(title=f"Biplot Tahunan (PCA Unweighted) — Tahun {yr}",
                                    xaxis_title=ax_x, yaxis_title=ax_y, template='plotly_white',
                                    xaxis=dict(scaleanchor='y', scaleratio=1))
            save_png(fig_yr_un, f"biplot_tahun_{yr}.png", ROOT_OUT_DIR, width=800, height=800)
    
    
    # ============================================================
    # 5. PERMUTATION TEST
    # ============================================================
    print("\n=== 5. Permutation Test (N={}) ===".format(N_PERM))
    
    def get_first_eigenvalue(mat):
        return np.sort(np.real(np.linalg.eigvals(mat)))[-1]
    
    lambda_obs = vals_H_sorted[0]
    dist_lambdas = []
    
    for _ in range(N_PERM):
        Ws_perm = []
        for X in X_matrices:
            # Permutasi PER KOLOM secara independen sesuai literatur Abdi et al. 2012
            X_p = np.zeros_like(X)
            for j in range(X.shape[1]):
                X_p[:, j] = np.random.permutation(X[:, j])
            Ws_perm.append(X_p @ X_p.T)
            
        # Hitung H_p menggunakan Ws_perm dan D_diag_mat tetap (statis)
        H_p = np.zeros((k_time, k_time))
        for i in range(k_time):
            for j in range(k_time):
                H_p[i, j] = np.trace(Ws_perm[i] @ D_diag_mat @ Ws_perm[j] @ D_diag_mat)
                
        dist_lambdas.append(get_first_eigenvalue(H_p))
        
    dist_lambdas = np.array(dist_lambdas)
    p_value = (np.sum(dist_lambdas >= lambda_obs) + 1) / (N_PERM + 1)
    interp_perm = "Signifikan (Struktur Stabil)" if p_value < 0.05 else "Tidak Signifikan (Acak)"
    print(f"  lambda_obs = {lambda_obs:.4f}, p-value = {p_value:.4f} -> {interp_perm}")
    
    # Plot
    fig_perm = px.histogram(x=dist_lambdas, nbins=40,
                            title=f"Distribusi Null Permutasi (N={N_PERM})",
                            labels={'x': 'λ₁ (Permutasi)', 'y': 'Frekuensi'},
                            color_discrete_sequence=['#90A4AE'])
    p_text = f"p={p_value:.4f}" if p_value >= 0.0001 else "p<0.0001"
    fig_perm.add_vline(x=lambda_obs, line_color="#D32F2F", line_dash="dash",
                       annotation_text=f"Observed: {lambda_obs:.3f}, {p_text}",
                       annotation_position="top right")
    fig_perm.update_layout(template='plotly_white')
    
    # Export LaTeX macro
    p_val_tex = r"\ensuremath{<0{,}0001}" if p_value < 0.0001 else f"{p_value:.4f}".replace(".", "{,}")
    perm_lines = [
        r"% Generated by export_all.py (Permutation)",
        fr"\newcommand{{\{get_macro_name('PValuePerm')}}}{{{p_val_tex}}}",
        fr"\newcommand{{\{get_macro_name('PermInterp')}}}{{{interp_perm}}}",
        fr"\newcommand{{\{get_macro_name('LambdaObs')}}}{{{f'{lambda_obs:.4f}'.replace('.', ',')}}}",
    ]
    
    # Export core macros
    core_labels = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
    core_lines = [r"% Generated by export_all.py"]
    for i, (yr, val) in enumerate(zip(sheet_names, alphas)):
        if i < len(core_labels):
            core_lines.append(fr"\newcommand{{\statisAlphaTahun{core_labels[i]}}}{{{f'{val:.4f}'.replace('.', ',')}}} % {yr}")
    core_lines.append(fr"\newcommand{{\statisEigenA}}{{{f'{eig_vals_c[0]:.4f}'.replace('.', ',')}}}")
    core_lines.append(fr"\newcommand{{\statisInertiaA}}{{{f'{var_pct[0]:.2f}'.replace('.', ',')}}}")
    # Selalu tulis hasil permutasi dan core statis ke folder skenario masing-masing (Wilayah / Indikator)
    save_png(fig_perm, "permutation_histogram.png", OUT_DIR)
    with open(os.path.join(OUT_DIR, "output_perm_statis.tex"), "w", encoding="utf-8") as f:
        f.write("\n".join(perm_lines))
    print(f"  [TEX] {os.path.join(OUT_DIR, 'output_perm_statis.tex')}")
    with open(os.path.join(OUT_DIR, "output_core_statis.tex"), "w", encoding="utf-8") as f:
        f.write("\n".join(core_lines))
    print(f"  [TEX] {os.path.join(OUT_DIR, 'output_core_statis.tex')}")
    
    # Ganti p-value hardcoded di output_macros.tex dengan yang asli terkomputasi secara dinamis
    macro_path = os.path.join(OUT_DIR, "output_macros.tex")
    if os.path.exists(macro_path):
        try:
            with open(macro_path, "r", encoding="utf-8") as f:
                content = f.read()
            p_val_indo = r"\ensuremath{<0{,}0001}" if p_value < 0.0001 else f"{p_value:.4f}".replace(".", ",")
            import re
            content_new = re.sub(
                r"\\newcommand\{\\" + get_macro_name('PValuePerm') + r"\}\{.*\}",
                fr"\\newcommand{{\\{get_macro_name('PValuePerm')}}}{{{p_val_indo}}}",
                content
            )
            with open(macro_path, "w", encoding="utf-8") as f:
                f.write(content_new)
            print(f"  [TEX] Updated dynamic PValuePerm in {OUT_DIR}/output_macros.tex to {p_val_indo}")
        except Exception as e:
            print(f"  [WARN] Gagal update dynamic p-value di {OUT_DIR}/output_macros.tex: {e}")
    
    
    # ============================================================
    # 6. K-MEANS CLUSTERING (per tahun + trajektori)
    # ============================================================
    print(f"\n=== 6. K-Means Clustering (k={K_CLUSTERS}) ===")
    
    # Fungsi label IPM
    def ipm_label(val):
        if val >= 80: return "Sangat Tinggi"
        elif val >= 70: return "Tinggi"
        elif val >= 55: return "Sedang"
        else: return "Rendah"
    
    if ipm_col:
        print(f"  Kolom pembanding: {ipm_col}")
    else:
        print("  [WARN] Tidak ada kolom IPM, matriks transisi IPM dilewati.")
    
    # Clustering per tahun dengan Base Year Anchoring (Hungarian Algorithm) + PC1 Ranking
    from scipy.spatial.distance import cdist
    from scipy.optimize import linear_sum_assignment
    
    # Gunakan per_year_coords yang sudah dihitung sebelumnya (Z @ Vc)
    # per_year_coords[sheet_names[0]] adalah koordinat tahun pertama (base)
    base_coords = per_year_coords[sheet_names[0]][:, :2]
    km_base = KMeans(n_clusters=K_CLUSTERS, random_state=42, n_init=10)
    km_base.fit(base_coords)
    base_centroids = km_base.cluster_centers_
    
    def get_ranked_labels(_coords_current, labels_awal, current_centroids, base_centroids_ref, compromise_scores):
        """
        Penyelarasan label menggunakan Hungarian Algorithm (Kuhn, 1955) 
        untuk konsistensi antar-tahun, diikuti perankingan otomatis berdasarkan mean PC1 Kompromi.
        """
        # 1. Hungarian Matching ke Base Year
        dist_matrix = cdist(base_centroids_ref, current_centroids, metric='euclidean')
        row_ind, col_ind = linear_sum_assignment(dist_matrix)
        mapping = {col_ind[i]: row_ind[i] for i in range(len(col_ind))}
        aligned_labels = np.array([mapping[l] for l in labels_awal])
        
        # 2. Re-ranking otomatis per tahun (berdasarkan rata-rata PC1 skor kompromi)
        # Ini memastikan Cluster 3 (Tinggi) selalu merujuk pada performa tinggi secara global
        cluster_means = []
        unique_lbls = sorted(list(set(aligned_labels)))
        for cl in unique_lbls:
            # Gunakan skor kompromi sebagai referensi ranking (Sesuai app.py Section 11)
            cluster_means.append(np.mean(compromise_scores[aligned_labels == cl, 0]))
        
        # Urutkan: mean terendah dapat indeks 0, tertinggi dapat indeks K-1
        sorted_indices = np.argsort(cluster_means)
        rank_map = {old_val: rank for rank, old_val in enumerate(sorted_indices)}
        
        final_labels = np.array([rank_map[l] for l in aligned_labels])
        return final_labels

    cluster_per_year = {}
    for yr in sheet_names:
        coords = per_year_coords[yr][:, :2]
        km = KMeans(n_clusters=K_CLUSTERS, random_state=42, n_init=10)
        labels_raw = km.fit_predict(coords)
        curr_centroids = km.cluster_centers_
        
        # Penyelarasan & Perankingan (Kuhn / Hungarian + PC1 Rank)
        labels = get_ranked_labels(coords, labels_raw, curr_centroids, base_centroids, scores_raw)
        cluster_per_year[yr] = labels
        
        # Scatter biplot Cluster per tahun
        ps_y, pl_y = apply_visual_adjustments(coords, loadings, norm=NORM_SCORE, scale=SCALE_LOAD)
        # Gunakan warna dari app.py: Merah (Rendah), Jingga (Sedang), Hijau (Tinggi)
        palette = ['#EF5350', '#FFB300', '#4CAF50', '#42A5F5', '#8E24AA']
        
        fig_sc = go.Figure()
        for cl in range(K_CLUSTERS):
            mask = labels == cl
            cluster_name = f"Cluster {cl+1}"
            if K_CLUSTERS == 3:
                cluster_name = ["Rendah", "Sedang", "Tinggi"][cl]
            elif K_CLUSTERS == 2:
                cluster_name = ["Rendah", "Tinggi"][cl]
            
            # Format text and sizes for this cluster using ps_y coordinates
            cl_texts = []
            cl_sizes = []
            idx_list = [i for i in range(len(obs_labels)) if mask[i]]
            for idx in idx_list:
                label = obs_labels[idx]
                if label in HIGHLIGHT_OBJECTS:
                    cl_texts.append(f"<b>{label} ({ps_y[idx, 0]:.2f}, {ps_y[idx, 1]:.2f})</b>")
                    cl_sizes.append(14)
                else:
                    cl_texts.append(label)
                    cl_sizes.append(9)
                
            fig_sc.add_trace(go.Scatter(
                x=ps_y[mask, 0], y=ps_y[mask, 1],
                mode='markers+text', text=cl_texts,
                textposition='top center', textfont=dict(size=9, color='black'),
                marker=dict(size=cl_sizes, color=palette[cl]),
                name=f'Cluster {cl+1} ({cluster_name})'
            ))
        fig_sc.add_hline(y=0, line_dash='dot', line_color='gray')
        fig_sc.add_vline(x=0, line_dash='dot', line_color='gray')
        # Tambahkan vektor loading dengan warna hitam beropasitas rendah
        for _li, _lvar in enumerate(selected_vars):
            fig_sc.add_trace(go.Scatter(
                x=[0, pl_y[_li, 0]], y=[0, pl_y[_li, 1]],
                mode='lines+text',
                text=['', _lvar],
                textposition='top center',
                textfont=dict(size=8, color='rgba(0,0,0,0.45)'),
                line=dict(color='rgba(0,0,0,0.2)', width=1.2),
                showlegend=False, hoverinfo='skip'
            ))
        fig_sc.update_layout(title=f"Biplot Cluster K-Means (Diberi Peringkat) — Tahun {yr}",
                             xaxis_title=ax_x, yaxis_title=ax_y, template='plotly_white',
                             xaxis=dict(scaleanchor='y', scaleratio=1))
        save_png(fig_sc, f"cluster_scatter_statis_{yr}.png", OUT_DIR, width=800, height=800)
    
        # Elbow (Gunakan Xc dari coords asli Z @ Vc)
        Xc = coords
        inertias = []
        max_k = min(11, len(Xc) + 1)
        k_range = range(1, max_k)
        for kk in k_range:
            km_e = KMeans(n_clusters=kk, random_state=42, n_init=10)
            km_e.fit(Xc)
            inertias.append(km_e.inertia_)
        fig_elbow = px.line(x=list(k_range), y=inertias, markers=True,
                            title=f"Kurva Elbow — Tahun {yr}",
                            labels={'x': 'Jumlah Cluster (k)', 'y': 'Inersia (SSE)'},
                            color_discrete_sequence=['#1976D2'])
        fig_elbow.update_traces(
            text=[f"{val:,.2f}" for val in inertias],
            textposition="top center",
            mode="lines+markers+text"
        )
        fig_elbow.update_layout(template='plotly_white')
        save_png(fig_elbow, f"elbow_plot_{yr}.png", OUT_DIR, width=700, height=450)
    
        # Dendrogram
        Z = linkage(Xc, 'ward')
        try:
            fig_dendro = ff.create_dendrogram(Xc, labels=obs_labels, orientation='left')
            fig_dendro.update_layout(title=f"Dendrogram — Tahun {yr}",
                                      template='plotly_white', margin=dict(l=150, r=20, t=40, b=20), height=550)
            save_png(fig_dendro, f"dendrogram_{yr}.png", OUT_DIR, width=800, height=550)
        except Exception as e:
            print(f"  [WARN] Dendrogram {yr} gagal: {e}")
            
        # Unweighted Elbow Plot and Dendrogram in Root (only when IS_FIRST)
        if IS_FIRST:
            Xc_bp = pca_pc_adj_dict[yr]
            inertias_bp = []
            for kk in k_range:
                km_e_bp = KMeans(n_clusters=kk, random_state=42, n_init=10)
                km_e_bp.fit(Xc_bp)
                inertias_bp.append(km_e_bp.inertia_)
            fig_elbow_bp = px.line(x=list(k_range), y=inertias_bp, markers=True,
                                   title=f"Kurva Elbow (Unweighted) — Tahun {yr}",
                                   labels={'x': 'Jumlah Cluster (k)', 'y': 'Inersia (SSE)'},
                                   color_discrete_sequence=['#1976D2'])
            fig_elbow_bp.update_traces(
                text=[f"{val:,.2f}" for val in inertias_bp],
                textposition="top center",
                mode="lines+markers+text"
            )
            fig_elbow_bp.update_layout(template='plotly_white')
            save_png(fig_elbow_bp, f"elbow_plot_{yr}.png", ROOT_OUT_DIR, width=700, height=450)
            
            try:
                fig_dendro_bp = ff.create_dendrogram(Xc_bp, labels=obs_labels, orientation='left')
                fig_dendro_bp.update_layout(title=f"Dendrogram (Unweighted) — Tahun {yr}",
                                            template='plotly_white', margin=dict(l=150, r=20, t=40, b=20), height=550)
                save_png(fig_dendro_bp, f"dendrogram_{yr}.png", ROOT_OUT_DIR, width=800, height=550)
            except Exception as e:
                print(f"  [WARN] Dendrogram unweighted {yr} gagal: {e}")

    # ============================================================
    # 8.A PERBANDINGAN CLUSTER BIPLOT VS CLUSTER STATIS
    # ============================================================
    print("\n=== 8.A Perbandingan Cluster Biplot vs Cluster Statis ===")
    for yr in sheet_names:
        lbl_statis_comp = cluster_traj # Compromise (STATIS)
        lbl_biplot_yr = cluster_per_year[yr] # Yearly Biplot
        
        cross_mat_bs = np.zeros((K_CLUSTERS, K_CLUSTERS), dtype=int)
        for s_l, b_l in zip(lbl_statis_comp, lbl_biplot_yr):
            cross_mat_bs[s_l, b_l] += 1
            
        df_cross_bs = pd.DataFrame(cross_mat_bs,
                                   index=[get_cluster_name(i, "Statis") for i in range(K_CLUSTERS)],
                                   columns=[get_cluster_name(j, "Biplot", f" ({yr})") for j in range(K_CLUSTERS)])
        df_cross_bs.index.name = "Statis (Compromise)"
        df_cross_bs = df_cross_bs.reset_index()
        save_tex_table(df_cross_bs, f"output_table_biplot_vs_statis_sum_{yr}.tex", OUT_DIR,
                       f"Matriks Perbandingan Cluster Biplot vs STATIS (vs Kompromi) ({yr})", f"biplot_statis_{yr}", float_fmt="{:.0f}", header_makecell=True, label_prefix=CUR_LABEL_PREFIX)
    
        rows_bs_nm = {}
        for s_l in range(K_CLUSTERS):
            for b_l in range(K_CLUSTERS):
                names = [obs_labels[i] for i in range(len(obs_labels))
                         if lbl_statis_comp[i] == s_l and lbl_biplot_yr[i] == b_l]
                rows_bs_nm[f"{get_cluster_name(s_l, 'Statis')} & {get_cluster_name(b_l, 'Biplot')}"] = ", ".join(names) if names else "-"
        save_tex_name_table(rows_bs_nm, f"output_table_biplot_vs_statis_name_{yr}.tex", OUT_DIR,
                            f"Nama Daerah Perbandingan Cluster Biplot vs STATIS (vs Kompromi) ({yr})", f"biplot_statis_name_{yr}", label_prefix=CUR_LABEL_PREFIX)
    
    # ============================================================
    # 8.B PERBANDINGAN CLUSTER STATIS TAHUNAN VS IPM TAHUNAN (per tahun) [Seksi 6]
    # ============================================================
    if ipm_col:
        print("\n=== 8.B Perbandingan Cluster STATIS Tahunan vs Kategori IPM (per tahun) ===")
        ipm_cats = ["Sangat Tinggi", "Tinggi", "Sedang", "Rendah"]
        for yr in sheet_names:
            lbl_statis_yr = cluster_per_year[yr]
            ipm_yr = [ipm_label(tables[yr].loc[o, ipm_col]) for o in obs_labels]
            
            cross_mat_si = np.zeros((K_CLUSTERS, 4), dtype=int)
            for km_l, ip_l in zip(lbl_statis_yr, ipm_yr):
                if ip_l in ipm_cats:
                    cross_mat_si[km_l, ipm_cats.index(ip_l)] += 1
            df_cross_si = pd.DataFrame(cross_mat_si,
                                       index=[get_cluster_name(i, "Cluster") for i in range(K_CLUSTERS)],
                                       columns=ipm_cats)
            df_cross_si.index.name = "Cluster STATIS"
            df_cross_si = df_cross_si.reset_index()
            save_tex_table(df_cross_si, f"output_table_statis_vs_ipm_sum_{yr}.tex", OUT_DIR,
                           f"Perbandingan Cluster STATIS Tahunan vs Kategori IPM (UNDP) ({yr})", f"statis_ipm_{yr}", float_fmt="{:.0f}", header_makecell=True, label_prefix=CUR_LABEL_PREFIX)
            
            rows_si_nm = {}
            for km_l in range(K_CLUSTERS):
                for ip_l in ipm_cats:
                    names = [obs_labels[i] for i in range(len(obs_labels))
                             if lbl_statis_yr[i] == km_l and ipm_yr[i] == ip_l]
                    rows_si_nm[f"{get_cluster_name(km_l, 'Cl.')} & {ip_l}"] = ", ".join(names) if names else "-"
            save_tex_name_table(rows_si_nm, f"output_table_statis_vs_ipm_name_{yr}.tex", OUT_DIR,
                                f"Nama Daerah Perbandingan Cluster STATIS Tahunan vs IPM (UNDP) ({yr})", f"statis_ipm_name_{yr}", label_prefix=CUR_LABEL_PREFIX)

    # ============================================================
    # 8.C PERBANDINGAN CLUSTER KOMPROMI STATIS VS CLUSTER STATIS TAHUNAN [Seksi 8]
    # ============================================================
    print("\n=== 8.C Perbandingan Cluster Kompromi STATIS vs Cluster STATIS Tahunan ===")
    for yr in sheet_names:
        lbl_comp = cluster_traj  # Compromise STATIS (overall trajectory)
        lbl_statis_yr = cluster_per_year[yr]   # Yearly STATIS
        
        cross_mat_cs = np.zeros((K_CLUSTERS, K_CLUSTERS), dtype=int)
        for c_l, s_l in zip(lbl_comp, lbl_statis_yr):
            cross_mat_cs[c_l, s_l] += 1
        
        df_cross_cs = pd.DataFrame(cross_mat_cs,
                                   index=[get_cluster_name(i, "Kompromi") for i in range(K_CLUSTERS)],
                                   columns=[get_cluster_name(j, "Statis", f" ({yr})") for j in range(K_CLUSTERS)])
        df_cross_cs.index.name = "Kompromi STATIS"
        df_cross_cs = df_cross_cs.reset_index()
        save_tex_table(df_cross_cs, f"output_table_compromise_vs_statis_sum_{yr}.tex", OUT_DIR,
                       f"Perbandingan Cluster Kompromi STATIS vs Cluster STATIS Tahunan ({yr})", f"comp_statis_{yr}", float_fmt="{:.0f}", header_makecell=True, label_prefix=CUR_LABEL_PREFIX)
        
        rows_cs_nm = {}
        for c_l in range(K_CLUSTERS):
            for s_l in range(K_CLUSTERS):
                names = [obs_labels[i] for i in range(len(obs_labels))
                         if lbl_comp[i] == c_l and lbl_statis_yr[i] == s_l]
                rows_cs_nm[f"{get_cluster_name(c_l, 'Kompromi')} & {get_cluster_name(s_l, 'Statis')}"] = ", ".join(names) if names else "-"
        save_tex_name_table(rows_cs_nm, f"output_table_compromise_vs_statis_name_{yr}.tex", OUT_DIR,
                            f"Nama Daerah Perbandingan Cluster Kompromi STATIS vs STATIS Tahunan ({yr})", f"comp_statis_name_{yr}", label_prefix=CUR_LABEL_PREFIX)

    # ============================================================
    # 8.D PERBANDINGAN CLUSTER KOMPROMI STATIS VS KATEGORI IPM (UNDP) (per tahun) [Seksi 9]
    # ============================================================
    if ipm_col:
        print("\n=== 8.D Perbandingan Cluster Kompromi STATIS vs Kategori IPM (UNDP) (per tahun) ===")
        ipm_cats = ["Sangat Tinggi", "Tinggi", "Sedang", "Rendah"]
        for yr in sheet_names:
            ipm_yr = [ipm_label(tables[yr].loc[o, ipm_col]) for o in obs_labels]
            
            cross_mat_ci = np.zeros((K_CLUSTERS, 4), dtype=int)
            for km_l, ip_l in zip(cluster_traj, ipm_yr):
                if ip_l in ipm_cats:
                    cross_mat_ci[km_l, ipm_cats.index(ip_l)] += 1
            df_cross_ci = pd.DataFrame(cross_mat_ci,
                                       index=[get_cluster_name(i, "Kompromi") for i in range(K_CLUSTERS)],
                                       columns=ipm_cats)
            df_cross_ci.index.name = "Kompromi STATIS"
            df_cross_ci = df_cross_ci.reset_index()
            save_tex_table(df_cross_ci, f"output_table_compromise_vs_ipm_sum_{yr}.tex", OUT_DIR,
                           f"Perbandingan Cluster Kompromi STATIS vs Kategori IPM (UNDP) ({yr})", f"comp_ipm_{yr}", float_fmt="{:.0f}", header_makecell=True, label_prefix=CUR_LABEL_PREFIX)
            
            rows_ci_nm = {}
            for km_l in range(K_CLUSTERS):
                for ip_l in ipm_cats:
                    names = [obs_labels[i] for i in range(len(obs_labels))
                             if cluster_traj[i] == km_l and ipm_yr[i] == ip_l]
                    rows_ci_nm[f"{get_cluster_name(km_l, 'Kompromi')} & {ip_l}"] = ", ".join(names) if names else "-"
            save_tex_name_table(rows_ci_nm, f"output_table_compromise_vs_ipm_name_{yr}.tex", OUT_DIR,
                                f"Nama Daerah Perbandingan Cluster Kompromi STATIS vs IPM (UNDP) ({yr})", f"comp_ipm_name_{yr}", label_prefix=CUR_LABEL_PREFIX)
    
    # ============================================================
    # 8.E MATRIKS TRANSISI CLUSTER BIPLOT TAHUNAN (Biplot k vs Biplot k+1) [Seksi 1]
    # ============================================================
    print("\n=== 8.E Matriks Transisi Cluster Biplot Tahunan (k vs k+1) ===")
    # Recompute biplot labels per year using unweighted PCA coords
    biplot_per_year = {}
    for yr in sheet_names:
        coords_bp = pca_scores_dict[yr][:, :2]
        km_bp = KMeans(n_clusters=K_CLUSTERS, random_state=42, n_init=10)
        lbls_bp_raw = km_bp.fit_predict(coords_bp)
        curr_c = km_bp.cluster_centers_
        dist_m = cdist(base_centroids, curr_c, metric='euclidean')
        _, col_i = linear_sum_assignment(dist_m)
        mp_bp = {col_i[i]: i for i in range(K_CLUSTERS)}
        aligned_bp = np.array([mp_bp[l] for l in lbls_bp_raw])
        if ipm_col:
            ipm_vals = tables[yr][ipm_col].values
            cl_means_bp = [np.mean(ipm_vals[aligned_bp == cl]) for cl in range(K_CLUSTERS)]
        else:
            cl_means_bp = [np.mean(coords_bp[aligned_bp == cl, 0]) for cl in range(K_CLUSTERS)]
        srt_bp = np.argsort(cl_means_bp)
        rk_bp = {old: new for new, old in enumerate(srt_bp)}
        biplot_per_year[yr] = np.array([rk_bp[l] for l in aligned_bp])

    year_pairs = [(sheet_names[i], sheet_names[i+1]) for i in range(len(sheet_names)-1)]
    for t1, t2 in year_pairs:
        lbl1_bp = biplot_per_year[t1]
        lbl2_bp = biplot_per_year[t2]
        pair = f"{t1}x{t2}"
        mat_count_bp = np.zeros((K_CLUSTERS, K_CLUSTERS), dtype=int)
        for a, b in zip(lbl1_bp, lbl2_bp):
            mat_count_bp[a, b] += 1
        df_trans_bp = pd.DataFrame(mat_count_bp,
                                   index=[get_cluster_name(i, "Cluster", f" ({t1})") for i in range(K_CLUSTERS)],
                                   columns=[get_cluster_name(j, "Cluster", f" ({t2})") for j in range(K_CLUSTERS)])
        df_trans_bp.index.name = f"{t1}/{t2}"
        df_trans_bp = df_trans_bp.reset_index()
        if IS_FIRST:
            save_tex_table(df_trans_bp, f"output_table_biplot_transition_sum_{pair}.tex", ROOT_OUT_DIR,
                           f"Matriks Transisi Cluster Biplot (Unweighted) {t1} \\(\\rightarrow\\) {t2}", f"biplot_trans_{pair}", float_fmt="{:.0f}", header_makecell=True, label_prefix=CUR_LABEL_PREFIX)
        
        rows_bp_nm = {}
        for a in range(K_CLUSTERS):
            for b in range(K_CLUSTERS):
                names = [obs_labels[i] for i in range(len(obs_labels)) if lbl1_bp[i]==a and lbl2_bp[i]==b]
                rows_bp_nm[f"{get_cluster_name(a, 'Cluster', f' ({t1})')} \\(\\rightarrow\\) {get_cluster_name(b, 'Cluster', f' ({t2})')}"] = ", ".join(names) if names else "-"
        if IS_FIRST:
            save_tex_name_table(rows_bp_nm, f"output_table_biplot_transition_name_{pair}.tex", ROOT_OUT_DIR,
                                f"Nama Daerah Transisi Cluster Biplot {t1} \\(\\rightarrow\\) {t2}", f"biplot_trans_name_{pair}", label_prefix=CUR_LABEL_PREFIX)
    
    # Matriks Transisi Cluster (jumlah & nama)
    year_pairs = [(sheet_names[i], sheet_names[i+1]) for i in range(len(sheet_names)-1)]
    for t1, t2 in year_pairs:
        lbl1 = cluster_per_year[t1]
        lbl2 = cluster_per_year[t2]
        pair = f"{t1}x{t2}"
        # Jumlah
        mat_count = np.zeros((K_CLUSTERS, K_CLUSTERS), dtype=int)
        for a, b in zip(lbl1, lbl2):
            mat_count[a, b] += 1
        df_trans = pd.DataFrame(mat_count, index=[get_cluster_name(i, "Cluster", f" ({t1})") for i in range(K_CLUSTERS)],
                                columns=[get_cluster_name(j, "Cluster", f" ({t2})") for j in range(K_CLUSTERS)])
        df_trans.index.name = f"{t1}/{t2}"
        df_trans = df_trans.reset_index()
        save_tex_table(df_trans, f"output_table_statis_transition_sum_{pair}.tex", OUT_DIR,
                       f"Matriks Transisi Cluster {t1} \\(\\rightarrow\\) {t2}", f"transsum{pair}", float_fmt="{:.0f}", header_makecell=True, label_prefix=CUR_LABEL_PREFIX)
    
        # Nama daerah
        rows_name = {}
        for a in range(K_CLUSTERS):
            for b in range(K_CLUSTERS):
                names = [obs_labels[i] for i in range(len(obs_labels)) if lbl1[i]==a and lbl2[i]==b]
                rows_name[f"{get_cluster_name(a, 'Cluster', f' ({t1})')} \\(\\rightarrow\\) {get_cluster_name(b, 'Cluster', f' ({t2})')}"] = ", ".join(names) if names else "-"
        save_tex_name_table(rows_name, f"output_table_statis_transition_name_{pair}.tex", OUT_DIR,
                            f"Nama Daerah Perpindahan Cluster {t1} \\(\\rightarrow\\) {t2}", f"transname{pair}", label_prefix=CUR_LABEL_PREFIX)
    
        # IPM transition (jika ada)
        if ipm_col:
            def ipm_labels_for_year(yr):
                return [ipm_label(tables[yr].loc[o, ipm_col]) for o in obs_labels]
    
            ipm1 = ipm_labels_for_year(t1)
            ipm2 = ipm_labels_for_year(t2)
            ipm_cats = ["Sangat Tinggi", "Tinggi", "Sedang", "Rendah"]
            ipm_mat = np.zeros((4, 4), dtype=int)
            for a, b in zip(ipm1, ipm2):
                if a in ipm_cats and b in ipm_cats:
                    ipm_mat[ipm_cats.index(a), ipm_cats.index(b)] += 1
            # Gunakan label kolom lebih pendek untuk IPM transition
            df_ipm = pd.DataFrame(ipm_mat, index=ipm_cats, columns=ipm_cats)
            df_ipm.index.name = f"{t1}/{t2}"
            df_ipm = df_ipm.reset_index()
            save_tex_table(df_ipm, f"output_table_ipm_sum_{pair}.tex", OUT_DIR,
                           f"Matriks Transisi Kategori IPM (UNDP) Tahun {t1} ke {t2}", f"ipm{pair}", float_fmt="{:.0f}", header_makecell=True, label_prefix=CUR_LABEL_PREFIX)
    
            # Nama daerah IPM
            rows_ipm_name = {}
            for a in ipm_cats:
                for b in ipm_cats:
                    names = [obs_labels[i] for i in range(len(obs_labels)) if ipm1[i]==a and ipm2[i]==b]
                    rows_ipm_name[f"{a} ({t1}) \\(\\rightarrow\\) {b} ({t2})"] = ", ".join(names) if names else "-"
            save_tex_name_table(rows_ipm_name, f"output_table_ipm_name_{pair}.tex", OUT_DIR,
                                f"Nama Daerah Matriks Transisi Kategori IPM (UNDP) {t1} \\(\\rightarrow\\) {t2}", f"ipmname{pair}", label_prefix=CUR_LABEL_PREFIX)
    
    # Cross-tab K-Means vs IPM per tahun akhir
    if ipm_col:
        print("\n=== 6b. Cross-tabulation K-Means vs IPM ===")
        for yr in sheet_names:
            lbl_km = cluster_per_year[yr]
            ipm_yr = [ipm_label(tables[yr].loc[o, ipm_col]) for o in obs_labels]
            ipm_cats = ["Sangat Tinggi", "Tinggi", "Sedang", "Rendah"]
            cross_mat = np.zeros((K_CLUSTERS, 4), dtype=int)
            for km_l, ip_l in zip(lbl_km, ipm_yr):
                if ip_l in ipm_cats:
                    cross_mat[km_l, ipm_cats.index(ip_l)] += 1
            df_cross = pd.DataFrame(cross_mat,
                                    index=[get_cluster_name(i, "Cluster") for i in range(K_CLUSTERS)],
                                    columns=ipm_cats)
            df_cross.index.name = "Cluster K-Means"
            df_cross = df_cross.reset_index()
            save_tex_table(df_cross, f"output_table_cross_matrix_sum_{yr}.tex", OUT_DIR,
                           f"Perbandingan Cluster Biplot vs Kategori IPM (UNDP) ({yr})", f"cross{yr}", float_fmt="{:.0f}", header_makecell=True, label_prefix=CUR_LABEL_PREFIX)
    
            # Nama daerah per sel
            rows_cross_nm = {}
            for km_l in range(K_CLUSTERS):
                for ip_l in ipm_cats:
                    names = [obs_labels[i] for i in range(len(obs_labels))
                             if lbl_km[i] == km_l and ipm_yr[i] == ip_l]
                    rows_cross_nm[f"{get_cluster_name(km_l, 'Cl.')} & {ip_l}"] = ", ".join(names) if names else "-"
            save_tex_name_table(rows_cross_nm, f"output_table_cross_matrix_name_{yr}.tex", OUT_DIR,
                                f"Nama Daerah Perbandingan Cluster Biplot vs Kategori IPM (UNDP) ({yr})", f"crossname{yr}", label_prefix=CUR_LABEL_PREFIX)
    
    
    # ============================================================
    # 7. CLUSTERING TRAJEKTORI KESELURUHAN + DENDROGRAM KOMPROMI
    # ============================================================
    # (cluster_traj sudah dihitung sebelumnya di Part 4)
    print(f"\n=== 7. Clustering Trajektori Keseluruhan ===")
    
    palette = ['#EF5350', '#FFB300', '#4CAF50', '#42A5F5', '#8E24AA']
    fig_traj_cl = go.Figure()
    for cl in range(K_CLUSTERS):
        mask = cluster_traj == cl
        cluster_name = f"Cluster {cl+1}"
        if K_CLUSTERS == 3: cluster_name = ["Rendah", "Sedang", "Tinggi"][cl]
        elif K_CLUSTERS == 2: cluster_name = ["Rendah", "Tinggi"][cl]
        
        fig_traj_cl.add_trace(go.Scatter(
            x=plot_scores[mask, 0], y=plot_scores[mask, 1],
            mode='markers+text',
            text=[obs_labels[i] for i in range(len(obs_labels)) if mask[i]],
            textposition='top center', textfont=dict(size=9, color='black'),
            marker=dict(size=9, color=palette[cl]),
            name=f'Cluster {cl+1} ({cluster_name})'
        ))
    fig_traj_cl.add_hline(y=0, line_dash='dot', line_color='gray')
    fig_traj_cl.add_vline(x=0, line_dash='dot', line_color='gray')
    # Tambahkan vektor loading dengan warna hitam beropasitas rendah
    for _li, _lvar in enumerate(selected_vars):
        fig_traj_cl.add_trace(go.Scatter(
            x=[0, plot_loadings[_li, 0]], y=[0, plot_loadings[_li, 1]],
            mode='lines+text',
            text=['', _lvar],
            textposition='top center',
            textfont=dict(size=8, color='rgba(0,0,0,0.45)'),
            line=dict(color='rgba(0,0,0,0.2)', width=1.2),
            showlegend=False, hoverinfo='skip'
        ))
    fig_traj_cl.update_layout(title="Scatter Plot Cluster Trajektori (Diberi Peringkat)",
                               xaxis_title=ax_x, yaxis_title=ax_y, template='plotly_white',
                               xaxis=dict(scaleanchor='y', scaleratio=1))
    save_png(fig_traj_cl, "compromise_scatter.png", OUT_DIR, width=800, height=800)
    
    # Tabel ringkasan anggota cluster trajektori (grouped: Kelompok | Jumlah | Daftar)
    from collections import defaultdict as _dd_cl
    _cl_groups: dict = _dd_cl(list)
    for _lbl, _ci in zip(obs_labels, cluster_traj):
        _cl_groups[_ci].append(_lbl)
    _cap_cl = f"Ringkasan Anggota Cluster Kompromi STATIS ({SCENARIO.replace('scenario', 'Skenario ')})"
    _lbl_cl = f"{CUR_LABEL_PREFIX}compromclust"
    _cl_path = os.path.join(OUT_DIR, "output_table_compromise_cluster_sum_name.tex")
    with open(_cl_path, "w", encoding="utf-8") as _cf:
        _cf.write("\\begin{table}[H]\n\\centering\n")
        _cf.write(f"\\caption{{{_cap_cl}}} \\label{{tab:{_lbl_cl}}}\n")
        _cf.write("\\begin{adjustbox}{max width=\\textwidth}\n")
        _cf.write("\\begin{tabular}{|p{3cm}|c|p{10cm}|}\n\\hline\n")
        _cf.write("\\textbf{Kelompok (Cluster)} & \\textbf{Jumlah Wilayah} & \\textbf{Daftar Kabupaten/Kota} \\\\\n\\hline\n")
        for _ci in sorted(_cl_groups.keys()):
            _cname = escape_tex(get_cluster_name(_ci))
            _members = ", ".join(_cl_groups[_ci])
            _cf.write(f"{_cname} & {len(_cl_groups[_ci])} & {escape_tex(_members)} \\\\\n\\hline\n")
        _cf.write("\\end{tabular}\n\\end{adjustbox}\n\\end{table}\n")
    print(f"  [TEX] output_table_compromise_cluster_sum_name.tex")
    
    
    # ============================================================
    # 8.5 PETA CHOROPLETH CLUSTER (geopandas + matplotlib)
    # ============================================================
    print("\n=== 8.5. Peta Choropleth Cluster ===")
    
    CLUSTER_COLORS = ['#EF5350', '#FFB300', '#4CAF50', '#42A5F5', '#8E24AA'] # Match app.py: Red, Orange, Green, Blue, Purple
    
    def draw_cluster_map(labels_arr, obs_labels_list, gdf_map, title, out_filename, out_dir=None):
        if out_dir is None:
            out_dir = OUT_DIR
        n_cl = K_CLUSTERS
        palette = CLUSTER_COLORS[:n_cl]
        df_cl = pd.DataFrame({'name_raw': obs_labels_list, 'Cluster': labels_arr})
        gdf_plot = gdf_map.copy()
        gdf_plot = gdf_plot.merge(df_cl, left_on='id_cocok', right_on='name_raw', how='left')
    
        fig, ax = plt.subplots(1, 1, figsize=(13, 9))
        # Wilayah di luar sampel → abu muda
        gdf_plot[gdf_plot['Cluster'].isna()].plot(
            ax=ax, color='#EFEFEF', edgecolor='#BBBBBB', linewidth=0.4)
        # Tiap cluster diberi warna berbeda sesuai ranking
        palette = ['#EF5350', '#FFB300', '#4CAF50', '#42A5F5', '#8E24AA']
        for cl_idx in range(n_cl):
            subset = gdf_plot[gdf_plot['Cluster'] == cl_idx]
            if not subset.empty:
                cluster_name = f"Cluster {cl_idx + 1}"
                if n_cl == 3: cluster_name = ["Rendah", "Sedang", "Tinggi"][cl_idx]
                elif n_cl == 2: cluster_name = ["Rendah", "Tinggi"][cl_idx]
                
                subset.plot(ax=ax, color=palette[cl_idx],
                            edgecolor='white', linewidth=0.6,
                            label=f'Cluster {cl_idx + 1} ({cluster_name})')
    
        # Nama daerah di tengah tiap poligon yang cocok
        for _, row in gdf_plot.dropna(subset=['Cluster']).iterrows():
            try:
                pt = row.geometry.centroid
                # Potong nama panjang: ambil kata terakhir agar lebih ringkas
                name = str(row['id_cocok'])
                # Singkat "Kota" / "Kabupaten" agar muat
                name_short = (name
                              .replace('Kabupaten ', 'Kab. ')
                              .replace('Kota ', 'Kota\n'))
                ax.annotate(
                    name_short,
                    xy=(pt.x, pt.y),
                    fontsize=4.8,
                    ha='center', va='center',
                    color='#1A1A1A',
                    fontweight='bold',
                    multialignment='center',
                    bbox=dict(boxstyle='round,pad=0.15',
                              facecolor='white', alpha=0.65,
                              edgecolor='none', linewidth=0)
                )
            except Exception:
                pass
    
        ax.set_title(title, fontsize=13, fontweight='bold', pad=10)
        ax.set_axis_off()
    
        # Paksa axes limit ke extent poligon yang cocok (berwarna) saja
        matched = gdf_plot.dropna(subset=['Cluster'])
        if not matched.empty:
            minx, miny, maxx, maxy = matched.total_bounds
            pad_x = (maxx - minx) * 0.05
            pad_y = (maxy - miny) * 0.05
            ax.set_xlim(min(minx - pad_x, 105.0), maxx + pad_x)
            ax.set_ylim(miny - pad_y, min(maxy + pad_y, -5.2))
    
        # Legend DI DALAM peta (bukan di samping kanan)
        patches = [mpatches.Patch(color=palette[i], label=get_cluster_name(i))
                   for i in range(n_cl)]
        legend = ax.legend(
            handles=patches,
            loc='lower left',
            fontsize=11,
            framealpha=0.88,
            edgecolor='#AAAAAA',
            title='Cluster',
            title_fontsize=11
        )
        legend.get_frame().set_linewidth(1.0)
    
        plt.tight_layout(pad=0.5)
        plt.savefig(os.path.join(out_dir, out_filename), dpi=200, bbox_inches='tight')
        plt.close(fig)
        print(f"  [PNG] {out_filename}")
    
    try:
        gdf_map = gpd.read_file(SHP_PATH)
        gdf_map['geometry'] = gdf_map['geometry'].simplify(tolerance=0.005, preserve_topology=True)
        gdf_map['id_cocok'] = gdf_map.apply(
            lambda row: row.get('NAME_2') or row.get('WADMKK') or row.get('NAMOBJ') or row.get('Name') or "", axis=1)
        # Bounding box dipersempit ke wilayah studi saja
        # Bounding box dipersempit ke wilayah studi (Banten, DKI, Jabar)
        # Longitude: 105.0 (Pandeglang) s.d 109.2 (Cirebon dll)
        # Latitude: -7.9 (Banten/Jabar Selatan) s.d -5.2 (Kep. Seribu)
        gdf_map = gdf_map.cx[105.0:109.2, -8.0:-5.2]
        print(f"  Shapefile OK. Wilayah dalam bbox: {len(gdf_map)}")
    
        # Peta per tahun
        for yr in sheet_names:
            labels_yr = cluster_per_year[yr]
            draw_cluster_map(labels_yr, obs_labels, gdf_map,
                             f"Peta Cluster STATIS Tahun {yr}", f"cluster_map_statis_{yr}.png")
    
        # Peta trajektori keseluruhan
        draw_cluster_map(cluster_traj, obs_labels, gdf_map,
                         "Peta Cluster STATIS 2020-2024", "compromise_map.png")
    
    except Exception as e:
        print(f"  [WARN] Peta choropleth gagal: {e}")
    
    
    # ============================================================
    # 8.9 SPATIAL AUTOCORRELATION (Moran's I)
    # ============================================================
    print("\n=== 8.9. Uji Moran's I (Spasial) ===")
    try:
        # Moran's I dihitung untuk PC1 (Kompromi) - Sumbu utama ekonomi
        res_moran = _calculate_moran_manual(gdf_map, scores_raw[:, 0], obs_labels)
        save_moran_tex(res_moran, "output_moran.tex", OUT_DIR, label_prefix=CUR_LABEL_PREFIX)
    except Exception as e:
        print(f"  [WARN] Uji Moran gagal: {e}")
    
    # ============================================================
    # 8.A-1 PERBANDINGAN CLUSTER BIPLOT (UNWEIGHTED) VS STATIS (WEIGHTED) TAHUNAN
    # ============================================================
    print("\n=== 8.A-1 Perbandingan Cluster Biplot (Unweighted) vs Statis (Weighted) Tahunan ===")
    for yr in sheet_names:
        coords_biplot = pca_scores_dict[yr][:, :2]
        coords_statis = per_year_coords[yr][:, :2]
        
        # 1. K-Means (Unweighted Biplot)
        km_biplot = KMeans(n_clusters=K_CLUSTERS, random_state=42, n_init=10)
        lbls_biplot_raw = km_biplot.fit_predict(coords_biplot)
        curr_centroids_bp = km_biplot.cluster_centers_
        
        # 1. K-Means (Weighted STATIS)
        km_statis = KMeans(n_clusters=K_CLUSTERS, random_state=42, n_init=10)
        lbls_statis_raw = km_statis.fit_predict(coords_statis)
        curr_centroids_st = km_statis.cluster_centers_
    
        # Align to base_centroids (from STATIS base year)
        dist_matrix_bp = cdist(base_centroids, curr_centroids_bp, metric='euclidean')
        _, col_ind_bp = linear_sum_assignment(dist_matrix_bp)
        mapping_bp = {col_ind_bp[i]: i for i in range(K_CLUSTERS)}
        aligned_lbls_bp = np.array([mapping_bp[l] for l in lbls_biplot_raw])
    
        dist_matrix_st = cdist(base_centroids, curr_centroids_st, metric='euclidean')
        _, col_ind_st = linear_sum_assignment(dist_matrix_st)
        mapping_st = {col_ind_st[i]: i for i in range(K_CLUSTERS)}
        aligned_lbls_st = np.array([mapping_st[l] for l in lbls_statis_raw])
        
        # 2. Ranking by PC1 (Unweighted Biplot)
        # Penyelarasan Orientasi: Pastikan searah dengan kompromi
        if 'scores_raw' in locals():
            corr_bp = np.corrcoef(coords_biplot[:, 0], scores_raw[:, 0])[0, 1]
            if corr_bp < 0: coords_biplot[:, 0] *= -1
            
            corr_st = np.corrcoef(coords_statis[:, 0], scores_raw[:, 0])[0, 1]
            if corr_st < 0: coords_statis[:, 0] *= -1
    
        if ipm_col:
            ipm_vals = tables[yr][ipm_col].values
            cluster_means_bp = [np.mean(ipm_vals[aligned_lbls_bp == cl]) for cl in range(K_CLUSTERS)]
            cluster_means_st = [np.mean(ipm_vals[aligned_lbls_st == cl]) for cl in range(K_CLUSTERS)]
        else:
            cluster_means_bp = [np.mean(coords_biplot[aligned_lbls_bp == cl, 0]) for cl in range(K_CLUSTERS)]
            cluster_means_st = [np.mean(coords_statis[aligned_lbls_st == cl, 0]) for cl in range(K_CLUSTERS)]
            
        sorted_indices_bp = np.argsort(cluster_means_bp)
        rank_map_bp = {old: new for new, old in enumerate(sorted_indices_bp)}
        lbl_biplot_yr = np.array([rank_map_bp[l] for l in aligned_lbls_bp])
        
        sorted_indices_st = np.argsort(cluster_means_st)
        rank_map_st = {old: new for new, old in enumerate(sorted_indices_st)}
        lbl_statis_yr = np.array([rank_map_st[l] for l in aligned_lbls_st])
        
        # Cross-tabulation (Row: Biplot, Col: STATIS)
        cross_mat_bs_yr = np.zeros((K_CLUSTERS, K_CLUSTERS), dtype=int)
        for b_l, s_l in zip(lbl_biplot_yr, lbl_statis_yr):
            cross_mat_bs_yr[b_l, s_l] += 1
            
        df_cross_bs_yr = pd.DataFrame(cross_mat_bs_yr,
                                      index=[get_cluster_name(i, "Biplot") for i in range(K_CLUSTERS)],
                                      columns=[get_cluster_name(j, "Statis") for j in range(K_CLUSTERS)])
        df_cross_bs_yr.index.name = "Biplot (Unweighted)"
        df_cross_bs_yr = df_cross_bs_yr.reset_index()
        save_tex_table(df_cross_bs_yr, f"output_table_biplot_vs_statis_compare_sum_{yr}.tex", OUT_DIR,
                       f"Matriks Perbandingan Cluster Biplot vs STATIS (Tahunan) ({yr})", f"biplot_statis_comp_{yr}", float_fmt="{:.0f}", header_makecell=True, label_prefix=CUR_LABEL_PREFIX)
    
        rows_bs_nm_yr = {}
        for b_l in range(K_CLUSTERS):
            for s_l in range(K_CLUSTERS):
                names = [obs_labels[i] for i in range(len(obs_labels))
                         if lbl_biplot_yr[i] == b_l and lbl_statis_yr[i] == s_l]
                rows_bs_nm_yr[f"{get_cluster_name(b_l, 'Biplot')} & {get_cluster_name(s_l, 'Statis')}"] = ", ".join(names) if names else "-"
        save_tex_name_table(rows_bs_nm_yr, f"output_table_biplot_vs_statis_compare_name_{yr}.tex", OUT_DIR,
                            f"Nama Daerah Perbandingan Cluster Biplot vs STATIS (Tahunan) ({yr})", f"biplot_statis_comp_name_{yr}", label_prefix=CUR_LABEL_PREFIX)
                            
        # --- Comparison 7: Kompromi STATIS vs Cluster Biplot Tahunan ---
        lbl_comp = cluster_traj
        cross_mat_bc = np.zeros((K_CLUSTERS, K_CLUSTERS), dtype=int)
        for b_l, c_l in zip(lbl_biplot_yr, lbl_comp):
            cross_mat_bc[b_l, c_l] += 1
            
        df_cross_bc = pd.DataFrame(
            cross_mat_bc,
            index=[get_cluster_name(i, "Biplot") for i in range(K_CLUSTERS)],
            columns=[get_cluster_name(j, "Kompromi") for j in range(K_CLUSTERS)]
        )
        df_cross_bc.index.name = "Biplot (Unweighted)"
        df_cross_bc = df_cross_bc.reset_index()
        save_tex_table(
            df_cross_bc, f"output_table_biplot_vs_compromise_sum_{yr}.tex", OUT_DIR,
            f"Matriks Perbandingan Cluster Biplot vs Kompromi STATIS ({yr})", 
            f"biplot_comp_{yr}", float_fmt="{:.0f}", header_makecell=True, label_prefix=CUR_LABEL_PREFIX
        )
        
        rows_bc_nm = {}
        for b_l in range(K_CLUSTERS):
            for c_l in range(K_CLUSTERS):
                names = [obs_labels[i] for i in range(len(obs_labels))
                         if lbl_biplot_yr[i] == b_l and lbl_comp[i] == c_l]
                rows_bc_nm[f"{get_cluster_name(b_l, 'Biplot')} & {get_cluster_name(c_l, 'Kompromi')}"] = ", ".join(names) if names else "-"
        save_tex_name_table(
            rows_bc_nm, f"output_table_biplot_vs_compromise_name_{yr}.tex", OUT_DIR,
            f"Nama Daerah Perbandingan Cluster Biplot vs Kompromi STATIS ({yr})", 
            f"biplot_comp_name_{yr}", label_prefix=CUR_LABEL_PREFIX
        )
                            
        # Draw Map for Biplot (Unweighted PCA Map - Root only)
        if 'gdf_map' in locals() and IS_FIRST:
            draw_cluster_map(lbl_biplot_yr, obs_labels, gdf_map,
                             f"Peta Cluster Biplot (Unweighted) Tahun {yr}", f"cluster_map_biplot_{yr}.png", out_dir=ROOT_OUT_DIR)
                             
        # Draw Scatter for Biplot
        palette = ['#EF5350', '#FFB300', '#4CAF50', '#42A5F5', '#8E24AA']
        fig_sc_bp = go.Figure()
        sp_adj = pca_pc_adj_dict[yr] # Rotated, mirrored, scaled unweighted coordinates
        for cl in range(K_CLUSTERS):
            mask = lbl_biplot_yr == cl
            cluster_name = f"Cluster {cl+1}"
            if K_CLUSTERS == 3: cluster_name = ["Rendah", "Sedang", "Tinggi"][cl]
            elif K_CLUSTERS == 2: cluster_name = ["Rendah", "Tinggi"][cl]
            
            # Format text and sizes for this cluster using sp_adj
            cl_texts_bp = []
            cl_sizes_bp = []
            idx_list = [idx for idx in range(len(obs_labels)) if mask[idx]]
            for idx in idx_list:
                label = obs_labels[idx]
                if label in HIGHLIGHT_OBJECTS:
                    cl_texts_bp.append(f"<b>{label} ({sp_adj[idx, 0]:.2f}, {sp_adj[idx, 1]:.2f})</b>")
                    cl_sizes_bp.append(14)
                else:
                    cl_texts_bp.append(label)
                    cl_sizes_bp.append(9)
            
            fig_sc_bp.add_trace(go.Scatter(
                x=sp_adj[mask, 0], y=sp_adj[mask, 1],
                mode='markers+text', text=cl_texts_bp,
                textposition='top center', textfont=dict(size=9, color='black'),
                marker=dict(size=cl_sizes_bp, color=palette[cl]),
                name=f'Cluster {cl+1} ({cluster_name})'
            ))
        fig_sc_bp.add_hline(y=0, line_dash='dot', line_color='gray')
        fig_sc_bp.add_vline(x=0, line_dash='dot', line_color='gray')
        # Tambahkan vektor loading dengan warna hitam beropasitas rendah
        _lp_bp = pca_load_adj_dict[yr]
        for _li, _lvar in enumerate(selected_vars):
            fig_sc_bp.add_trace(go.Scatter(
                x=[0, _lp_bp[_li, 0]], y=[0, _lp_bp[_li, 1]],
                mode='lines+text',
                text=['', _lvar],
                textposition='top center',
                textfont=dict(size=8, color='rgba(0,0,0,0.45)'),
                line=dict(color='rgba(0,0,0,0.2)', width=1.2),
                showlegend=False, hoverinfo='skip'
            ))
        fig_sc_bp.update_layout(title=f"Biplot Cluster K-Means (Unweighted) — Tahun {yr}",
                             xaxis_title=ax_x, yaxis_title=ax_y, template='plotly_white',
                             xaxis=dict(scaleanchor='y', scaleratio=1))
        if IS_FIRST:
            save_png(fig_sc_bp, f"cluster_scatter_biplot_{yr}.png", ROOT_OUT_DIR, width=800, height=800)

    # ============================================================
    # 8.F STATISTIKA DESKRIPTIF (DENGAN BOBOT)
    # ============================================================
    print("\n=== 8.C Statistika Deskriptif ===")
    for yr in sheet_names:
        df_y = tables[yr]
        rows_desc = []
        
        m_list = m_weights.copy()
        if m_list.sum() > 0:
            m_list = m_list / m_list.sum()
            
        for col in df_y.columns:
            if col not in selected_vars and col != ipm_col:
                continue
                
            vals = df_y[col].values
            n = len(vals)
            mu = np.sum(m_list * vals)
            diff = vals - mu
            variance = np.sum(m_list * (diff**2))
            sigma = np.sqrt(variance)
            
            m3 = np.sum(m_list * (diff**3))
            skew_v = m3 / (sigma**3) if sigma > 0 else 0
            
            m4 = np.sum(m_list * (diff**4))
            kurt_v = (m4 / (sigma**4)) - 3 if sigma > 0 else 0
            
            cv_v = (sigma / mu * 100) if mu != 0 else None
            
            rows_desc.append({
                'Indikator': col,
                'Mean ($\\mu$)': mu,
                'Std Dev ($\\sigma$)': sigma,
                'Min': np.min(vals),
                'Q1': np.percentile(vals, 25),
                'Median': np.median(vals),
                'Q3': np.percentile(vals, 75),
                'Max': np.max(vals),
                'Skewness ($\\gamma_1$)': skew_v,
                'Kurtosis ($\\gamma_2$)': kurt_v,
                'CV (%)': cv_v if cv_v is not None else 0
            })
            
        df_desc = pd.DataFrame(rows_desc)
        if IS_FIRST:
            n_samples = len(df_y)
            save_tex_table(df_desc, f"output_table_descriptive_{yr}.tex", ROOT_OUT_DIR,
                           f"Statistika Deskriptif (Dengan Bobot) Tahun {yr} (N = {n_samples})", f"desc_{yr}", float_fmt="{:.4f}", header_makecell=False, label_prefix=CUR_LABEL_PREFIX)
    

    # ============================================================
    # 10. MENGGABUNGKAN GAMBAR PERBANDINGAN BERSANDINGAN (SIDE-BY-SIDE) FOR 9 COMPARISONS
    # ============================================================
    print("\n=== 10. Menggabungkan Gambar Perbandingan (Side-by-Side) ===")
    try:
        from PIL import Image
    
        def combine_images_side_by_side(img_left_path, img_right_path, out_path):
            if not os.path.exists(img_left_path) or not os.path.exists(img_right_path):
                print(f"  [WARN] Missing input for combine: {os.path.basename(img_left_path)} or {os.path.basename(img_right_path)}")
                return
            try:
                img1 = Image.open(img_left_path)
                img2 = Image.open(img_right_path)
                
                # Resize right image to match left image's height if needed
                if img1.height != img2.height:
                    new_width = int(img2.width * (img1.height / img2.height))
                    img2 = img2.resize((new_width, img1.height), Image.Resampling.LANCZOS)
                    
                total_width = img1.width + img2.width
                max_height = img1.height
                
                new_im = Image.new('RGB', (total_width, max_height), (255, 255, 255))
                new_im.paste(img1, (0, 0))
                new_im.paste(img2, (img1.width, 0))
                new_im.save(out_path)
                print(f"  [PNG Combined] {os.path.basename(out_path)}")
            except Exception as e:
                print(f"  [WARN] Gagal menggabungkan gambar {os.path.basename(out_path)}: {e}")

        # Helper to draw pie charts for clusters
        def draw_pie_chart(labels_idx, title, out_filename, out_dir):
            try:
                level_names = ["Rendah", "Sedang", "Tinggi"] if K_CLUSTERS == 3 else ["Rendah", "Tinggi"]
                labels_str = [f"Cluster {l+1} ({level_names[l]})" for l in labels_idx]
                from collections import Counter
                counts = Counter(labels_str)
                keys = sorted(list(counts.keys()))
                sizes = [counts[k] for k in keys]
                
                # Map colors based on level
                # Cluster 1 = Red, Cluster 2 = Orange, Cluster 3 = Green
                color_map = {
                    f"Cluster 1 ({level_names[0]})": '#EF5350',
                    f"Cluster 2 ({level_names[1]})": '#FFB300',
                    f"Cluster 3 ({level_names[2]})": '#4CAF50'
                }
                if len(level_names) == 2:
                    color_map = {
                        f"Cluster 1 ({level_names[0]})": '#EF5350',
                        f"Cluster 2 ({level_names[1]})": '#4CAF50'
                    }
                colors = [color_map.get(k, '#8E24AA') for k in keys]
                
                fig, ax = plt.subplots(figsize=(6, 5))
                ax.pie(sizes, labels=keys, autopct='%1.1f%%', startangle=90, colors=colors,
                       wedgeprops=dict(edgecolor='white', linewidth=1))
                ax.axis('equal')
                plt.title(title, fontsize=12, fontweight='bold', pad=10)
                plt.tight_layout()
                plt.savefig(os.path.join(out_dir, out_filename), dpi=150, bbox_inches='tight')
                plt.close(fig)
                print(f"  [PNG Pie] {out_filename}")
            except Exception as e:
                print(f"  [WARN] Gagal menggambar pie chart {out_filename}: {e}")

        # Helper to draw pie charts for IPM
        def draw_ipm_pie_chart(labels, title, out_filename, out_dir):
            try:
                from collections import Counter
                counts = Counter(labels)
                ipm_cats = ["Sangat Tinggi", "Tinggi", "Sedang", "Rendah"]
                ipm_colors = ['#0D47A1', '#1976D2', '#90CAF9', '#FFCDD2']
                
                ordered_cats = [c for c in ipm_cats if c in counts]
                sizes = [counts[c] for c in ordered_cats]
                colors = [ipm_colors[ipm_cats.index(c)] for c in ordered_cats]
                
                fig, ax = plt.subplots(figsize=(6, 5))
                ax.pie(sizes, labels=ordered_cats, autopct='%1.1f%%', startangle=90, colors=colors,
                       wedgeprops=dict(edgecolor='white', linewidth=1))
                ax.axis('equal')
                plt.title(title, fontsize=12, fontweight='bold', pad=10)
                plt.tight_layout()
                plt.savefig(os.path.join(out_dir, out_filename), dpi=150, bbox_inches='tight')
                plt.close(fig)
                print(f"  [PNG IPM Pie] {out_filename}")
            except Exception as e:
                print(f"  [WARN] Gagal menggambar IPM pie chart {out_filename}: {e}")

        # Helper to draw IPM maps
        def draw_ipm_map(ipm_labels, obs_labels_list, gdf_map, title, out_filename, out_dir):
            try:
                ipm_cats = ["Sangat Tinggi", "Tinggi", "Sedang", "Rendah"]
                ipm_colors = ['#0D47A1', '#1976D2', '#90CAF9', '#FFCDD2']
                df_cl = pd.DataFrame({'name_raw': obs_labels_list, 'IPM_Cat': ipm_labels})
                gdf_plot = gdf_map.copy()
                gdf_plot = gdf_plot.merge(df_cl, left_on='id_cocok', right_on='name_raw', how='left')
                
                fig, ax = plt.subplots(1, 1, figsize=(13, 9))
                # Gray for non-sample regions
                gdf_plot[gdf_plot['IPM_Cat'].isna()].plot(
                    ax=ax, color='#EFEFEF', edgecolor='#BBBBBB', linewidth=0.4)
                    
                for cl_idx, cat in enumerate(ipm_cats):
                    subset = gdf_plot[gdf_plot['IPM_Cat'] == cat]
                    if not subset.empty:
                        subset.plot(ax=ax, color=ipm_colors[cl_idx],
                                    edgecolor='white', linewidth=0.6,
                                    label=cat)
                
                # Annotate names
                for _, row in gdf_plot.dropna(subset=['IPM_Cat']).iterrows():
                    try:
                        pt = row.geometry.centroid
                        name = str(row['id_cocok'])
                        name_short = name.replace('Kabupaten ', 'Kab. ').replace('Kota ', 'Kota\n')
                        ax.annotate(name_short, xy=(pt.x, pt.y), fontsize=4.8, ha='center', va='center',
                                    color='#1A1A1A', fontweight='bold', multialignment='center',
                                    bbox=dict(boxstyle='round,pad=0.15', facecolor='white', alpha=0.65, edgecolor='none'))
                    except Exception:
                        pass
                        
                ax.set_title(title, fontsize=13, fontweight='bold', pad=10)
                ax.set_axis_off()
                matched = gdf_plot.dropna(subset=['IPM_Cat'])
                if not matched.empty:
                    minx, miny, maxx, maxy = matched.total_bounds
                    pad_x = (maxx - minx) * 0.05
                    pad_y = (maxy - miny) * 0.05
                    ax.set_xlim(min(minx - pad_x, 105.0), maxx + pad_x)
                    ax.set_ylim(miny - pad_y, min(maxy + pad_y, -5.2))
                    
                patches = [mpatches.Patch(color=ipm_colors[i], label=ipm_cats[i]) for i in range(4) if not gdf_plot[gdf_plot['IPM_Cat'] == ipm_cats[i]].empty]
                ax.legend(handles=patches, loc='lower left', fontsize=11, framealpha=0.88, edgecolor='#AAAAAA', title='IPM')
                plt.tight_layout(pad=0.5)
                plt.savefig(os.path.join(out_dir, out_filename), dpi=200, bbox_inches='tight')
                plt.close(fig)
                print(f"  [PNG IPM Map] {out_filename}")
            except Exception as e:
                print(f"  [WARN] Gagal menggambar IPM map {out_filename}: {e}")

        # A. GENERATE INDIVIDUAL PIE CHARTS
        print("  Generating individual pie charts...")
        for yr in sheet_names:
            # 1. Unweighted Biplot Pies
            draw_pie_chart(biplot_per_year[yr], f"Proporsi Cluster Biplot Tahun {yr}", f"cluster_pie_biplot_{yr}.png", ROOT_OUT_DIR)
            # 2. Weighted STATIS Pies
            draw_pie_chart(cluster_per_year[yr], f"Proporsi Cluster STATIS Tahun {yr}", f"cluster_pie_statis_{yr}.png", OUT_DIR)
            # 3. IPM Pies
            if ipm_col:
                ipm_yr = [ipm_label(tables[yr].loc[o, ipm_col]) for o in obs_labels]
                draw_ipm_pie_chart(ipm_yr, f"Proporsi Kategori IPM Tahun {yr}", f"ipm_pie_{yr}.png", ROOT_OUT_DIR)
                
        # 4. Global Compromise STATIS Pie
        draw_pie_chart(cluster_traj, "Proporsi Cluster Kompromi STATIS (Keseluruhan)", "compromise_pie.png", OUT_DIR)

        # B. GENERATE INDIVIDUAL IPM MAPS
        if ipm_col and 'gdf_map' in locals():
            print("  Generating individual IPM maps...")
            for yr in sheet_names:
                ipm_yr = [ipm_label(tables[yr].loc[o, ipm_col]) for o in obs_labels]
                draw_ipm_map(ipm_yr, obs_labels, gdf_map, f"Peta Kategori IPM (UNDP) Tahun {yr}", f"ipm_map_{yr}.png", ROOT_OUT_DIR)

        # C. COMBINE IMAGES SIDE-BY-SIDE FOR ALL 9 COMPARISONS
        print("  Combining comparative images side-by-side...")
        year_pairs = [(sheet_names[i], sheet_names[i+1]) for i in range(len(sheet_names)-1)]
        
        # Comparison 1: Biplot k vs Biplot k+1
        for y1, y2 in year_pairs:
            pair = f"{y1}x{y2}"
            combine_images_side_by_side(
                os.path.join(ROOT_OUT_DIR, f"cluster_map_biplot_{y1}.png"),
                os.path.join(ROOT_OUT_DIR, f"cluster_map_biplot_{y2}.png"),
                os.path.join(OUT_DIR, f"compare_map_trans_biplot_{pair}.png")
            )
            combine_images_side_by_side(
                os.path.join(ROOT_OUT_DIR, f"cluster_scatter_biplot_{y1}.png"),
                os.path.join(ROOT_OUT_DIR, f"cluster_scatter_biplot_{y2}.png"),
                os.path.join(OUT_DIR, f"compare_scatter_trans_biplot_{pair}.png")
            )
            combine_images_side_by_side(
                os.path.join(ROOT_OUT_DIR, f"cluster_pie_biplot_{y1}.png"),
                os.path.join(ROOT_OUT_DIR, f"cluster_pie_biplot_{y2}.png"),
                os.path.join(OUT_DIR, f"compare_pie_trans_biplot_{pair}.png")
            )

        # Comparison 2: STATIS k vs STATIS k+1
        for y1, y2 in year_pairs:
            pair = f"{y1}x{y2}"
            combine_images_side_by_side(
                os.path.join(OUT_DIR, f"cluster_map_statis_{y1}.png"),
                os.path.join(OUT_DIR, f"cluster_map_statis_{y2}.png"),
                os.path.join(OUT_DIR, f"compare_map_trans_statis_{pair}.png")
            )
            combine_images_side_by_side(
                os.path.join(OUT_DIR, f"cluster_scatter_statis_{y1}.png"),
                os.path.join(OUT_DIR, f"cluster_scatter_statis_{y2}.png"),
                os.path.join(OUT_DIR, f"compare_scatter_trans_statis_{pair}.png")
            )
            combine_images_side_by_side(
                os.path.join(OUT_DIR, f"cluster_pie_statis_{y1}.png"),
                os.path.join(OUT_DIR, f"cluster_pie_statis_{y2}.png"),
                os.path.join(OUT_DIR, f"compare_pie_trans_statis_{pair}.png")
            )

        # Comparison 3: Biplot k vs STATIS k
        for yr in sheet_names:
            combine_images_side_by_side(
                os.path.join(ROOT_OUT_DIR, f"cluster_map_biplot_{yr}.png"),
                os.path.join(OUT_DIR, f"cluster_map_statis_{yr}.png"),
                os.path.join(OUT_DIR, f"compare_map_biplot_vs_statis_{yr}.png")
            )
            combine_images_side_by_side(
                os.path.join(ROOT_OUT_DIR, f"cluster_scatter_biplot_{yr}.png"),
                os.path.join(OUT_DIR, f"cluster_scatter_statis_{yr}.png"),
                os.path.join(OUT_DIR, f"compare_scatter_biplot_vs_statis_{yr}.png")
            )
            combine_images_side_by_side(
                os.path.join(ROOT_OUT_DIR, f"cluster_pie_biplot_{yr}.png"),
                os.path.join(OUT_DIR, f"cluster_pie_statis_{yr}.png"),
                os.path.join(OUT_DIR, f"compare_pie_biplot_vs_statis_{yr}.png")
            )

        # Comparisons involving IPM
        if ipm_col:
            # Comparison 4: IPM k vs IPM k+1
            for y1, y2 in year_pairs:
                pair = f"{y1}x{y2}"
                combine_images_side_by_side(
                    os.path.join(ROOT_OUT_DIR, f"ipm_map_{y1}.png"),
                    os.path.join(ROOT_OUT_DIR, f"ipm_map_{y2}.png"),
                    os.path.join(OUT_DIR, f"compare_map_ipm_{pair}.png")
                )
                combine_images_side_by_side(
                    os.path.join(ROOT_OUT_DIR, f"ipm_pie_{y1}.png"),
                    os.path.join(ROOT_OUT_DIR, f"ipm_pie_{y2}.png"),
                    os.path.join(OUT_DIR, f"compare_pie_ipm_{pair}.png")
                )

            # Comparison 5: Biplot k vs IPM k
            for yr in sheet_names:
                combine_images_side_by_side(
                    os.path.join(ROOT_OUT_DIR, f"cluster_map_biplot_{yr}.png"),
                    os.path.join(ROOT_OUT_DIR, f"ipm_map_{yr}.png"),
                    os.path.join(OUT_DIR, f"compare_map_biplot_vs_ipm_{yr}.png")
                )
                combine_images_side_by_side(
                    os.path.join(ROOT_OUT_DIR, f"cluster_pie_biplot_{yr}.png"),
                    os.path.join(ROOT_OUT_DIR, f"ipm_pie_{yr}.png"),
                    os.path.join(OUT_DIR, f"compare_pie_biplot_vs_ipm_{yr}.png")
                )

            # Comparison 6: STATIS k vs IPM k
            for yr in sheet_names:
                combine_images_side_by_side(
                    os.path.join(OUT_DIR, f"cluster_map_statis_{yr}.png"),
                    os.path.join(ROOT_OUT_DIR, f"ipm_map_{yr}.png"),
                    os.path.join(OUT_DIR, f"compare_map_statis_vs_ipm_{yr}.png")
                )
                combine_images_side_by_side(
                    os.path.join(OUT_DIR, f"cluster_pie_statis_{yr}.png"),
                    os.path.join(ROOT_OUT_DIR, f"ipm_pie_{yr}.png"),
                    os.path.join(OUT_DIR, f"compare_pie_statis_vs_ipm_{yr}.png")
                )

            # Comparison 9: Kompromi STATIS vs IPM k
            for yr in sheet_names:
                combine_images_side_by_side(
                    os.path.join(OUT_DIR, "compromise_map.png"),
                    os.path.join(ROOT_OUT_DIR, f"ipm_map_{yr}.png"),
                    os.path.join(OUT_DIR, f"compare_map_compromise_vs_ipm_{yr}.png")
                )
                combine_images_side_by_side(
                    os.path.join(OUT_DIR, "compromise_pie.png"),
                    os.path.join(ROOT_OUT_DIR, f"ipm_pie_{yr}.png"),
                    os.path.join(OUT_DIR, f"compare_pie_compromise_vs_ipm_{yr}.png")
                )

        # Comparison 7: Kompromi STATIS vs Biplot k
        for yr in sheet_names:
            combine_images_side_by_side(
                os.path.join(OUT_DIR, "compromise_map.png"),
                os.path.join(ROOT_OUT_DIR, f"cluster_map_biplot_{yr}.png"),
                os.path.join(OUT_DIR, f"compare_map_compromise_vs_biplot_{yr}.png")
            )
            combine_images_side_by_side(
                os.path.join(OUT_DIR, "compromise_scatter.png"),
                os.path.join(ROOT_OUT_DIR, f"cluster_scatter_biplot_{yr}.png"),
                os.path.join(OUT_DIR, f"compare_scatter_compromise_vs_biplot_{yr}.png")
            )
            combine_images_side_by_side(
                os.path.join(OUT_DIR, "compromise_pie.png"),
                os.path.join(ROOT_OUT_DIR, f"cluster_pie_biplot_{yr}.png"),
                os.path.join(OUT_DIR, f"compare_pie_compromise_vs_biplot_{yr}.png")
            )

        # Comparison 8: Kompromi STATIS vs STATIS k
        for yr in sheet_names:
            combine_images_side_by_side(
                os.path.join(OUT_DIR, "compromise_map.png"),
                os.path.join(OUT_DIR, f"cluster_map_statis_{yr}.png"),
                os.path.join(OUT_DIR, f"compare_map_compromise_vs_statis_{yr}.png")
            )
            combine_images_side_by_side(
                os.path.join(OUT_DIR, "compromise_scatter.png"),
                os.path.join(OUT_DIR, f"cluster_scatter_statis_{yr}.png"),
                os.path.join(OUT_DIR, f"compare_scatter_compromise_vs_statis_{yr}.png")
            )
            combine_images_side_by_side(
                os.path.join(OUT_DIR, "compromise_pie.png"),
                os.path.join(OUT_DIR, f"cluster_pie_statis_{yr}.png"),
                os.path.join(OUT_DIR, f"compare_pie_compromise_vs_statis_{yr}.png")
            )

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"  [WARN] Gagal melakukan proses Step 10: {e}")
    
# ============================================================
# FINAL CLEANUP
# ============================================================
deduplicate_and_clean(ROOT_OUT_DIR)

print("\n" + "="*60)
print("  PROSES EXPORT SELESAI!")
print(f"  Output Root: {ROOT_OUT_DIR}")
print("="*60 + "\n")
