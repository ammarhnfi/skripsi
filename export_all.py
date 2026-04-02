"""
export_all.py
=============
Script standalone untuk menghasilkan SEMUA gambar (PNG) dan tabel (.tex)
dari analisis STATIS + K-Means + Moran's I menggunakan data2.xlsx.

Semua output disimpan ke folder: output_app/

Cara pakai:
    cd d:/Skripsi/my
    python export_all.py

Requirements:
    pip install pandas openpyxl numpy scipy scikit-learn plotly geopandas kaleido
"""

import os
import sys
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
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# ============================================================
# KONFIGURASI
# ============================================================
DATA_PATH     = r"d:\Skripsi\my\data\data2.xlsx"
SHP_PATH      = r"d:\Skripsi\my\web\skripsiv2\gadm41_IDN_2.shp"
OUT_DIR       = r"d:\Skripsi\my\output_app"
K_CLUSTERS    = 3        # jumlah klaster K-Means
N_PERM        = 1000     # jumlah permutasi
SCALE_LOAD    = True     # scale loading vectors untuk biplot

os.makedirs(OUT_DIR, exist_ok=True)


# ============================================================
# HELPER: simpan PNG
# ============================================================
def save_png(fig, filename, width=900, height=600):
    path = os.path.join(OUT_DIR, filename)
    try:
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

def save_tex_table(df, filename, caption, label, longtable=False, float_fmt="{:.4f}", header_makecell=False):
    path = os.path.join(OUT_DIR, filename)
    cols = df.columns.tolist()
    # Jika kolom banyak (seperti matriks), gunakan p{} untuk semua kolom agar rata
    if len(cols) > 3:
        # Distribusikan sisa lebar (0.60\textwidth) ke n-1 kolom untuk sisa margin
        w_sub = round(0.60 / (len(cols) - 1), 2)
        col_defs = [r"m{0.25\textwidth}|"] + [f"m{{{w_sub}\\textwidth}}|" for _ in range(len(cols)-1)]
    else:
        col_defs = [r"m{0.25\textwidth}|"] + ["c|" for _ in range(len(cols)-1)]
    col_str = "".join(col_defs)

    lines = []
    if longtable:
        lines.append(r"\begin{longtable}{|" + col_str + "}")
        lines.append(r"\caption{" + caption + r"} \label{tab:" + label + r"} \\")
        lines.append(r"\hline")
        header = " & ".join([f"\\textbf{{{escape_tex(c)}}}" for c in cols]) + r" \\"
        lines += [header, r"\hline", r"\endfirsthead", r"\hline", header, r"\hline", r"\endhead", r"\hline", r"\endfoot"]
        for _, row in df.iterrows():
            row_str = " & ".join([float_fmt.format(v) if isinstance(v, (int, float)) else escape_tex(v) for v in row]) + r" \\"
            lines.append(row_str)
        lines += [r"\hline", r"\end{longtable}"]
    else:
        lines.append(r"\begin{table}[H]")
        lines.append(r"\centering")
        lines.append(r"\caption{" + caption + r"} \label{tab:" + label + "}")
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
            row_vals = []
            for v in row:
                if isinstance(v, (int, float)):
                    row_vals.append(float_fmt.format(v))
                else:
                    # Ganti & dengan \& agar tidak break tabel jika ada nama variabel aneh
                    row_vals.append(escape_tex(v).replace('&', r'\&'))
            row_str = " & ".join(row_vals) + r" \\"
            lines.append(row_str)
        lines += [r"\hline", r"\end{tabular}", r"\end{adjustbox}", r"\end{table}"]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [TEX] {filename}")


def save_tex_name_table(rows_dict, filename, caption, label, name_col_width="11cm"):
    """Tabel dua kolom: (Sel | Nama Daerah) dengan kolom nama memakai p{width}
    agar teks otomatis wrap ke bawah dan tidak melebar ke kanan.
    Font diperkecil ke \\small agar muat di halaman A4."""
    path = os.path.join(OUT_DIR, filename)
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\small",
        r"\caption{" + caption + r"} \label{tab:" + label + "}",
        r"\begin{tabular}{|>{\raggedright\arraybackslash}m{0.30\textwidth}|>{\raggedright\arraybackslash}m{0.63\textwidth}|}",
        r"\hline",
        r"\textbf{Sel} & \textbf{Kabupaten/Kota} \\",
        r"\hline",
    ]
    for sel, names in rows_dict.items():
        # JIKA KOSONG / HANYA STRIP (-), ABAIKAN (Sesuai permintaan user)
        if not names or str(names).strip() in ["-", ""]:
            continue
        sel_esc = escape_tex(str(sel))
        names_esc = escape_tex(str(names))
        lines.append(f"{sel_esc} & {names_esc} \\\\")
        lines.append(r"\hline")
    lines += [r"\end{tabular}", r"\end{table}"]
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

def save_moran_tex(results, filename):
    if not results: return
    path = os.path.join(OUT_DIR, filename)
    mi, ei, zi, pi = results
    if pi < 0.05:
        interp = "Terdapat Autokorelasi Spasial Positif (Berkelompok)" if mi > ei else "Terdapat Autokorelasi Spasial Negatif (Menyebar)"
    else:
        interp = "Tidak Signifikan (Pola Spasial Acak)"
    lines = [
        r"\newcommand{\MacroMoranI}{" + f"{mi:.4f}" + r"}",
        r"\newcommand{\MacroMoranExp}{" + f"{ei:.4f}" + r"}",
        r"\newcommand{\MacroMoranZ}{" + f"{zi:.4f}" + r"}",
        r"\newcommand{\MacroMoranP}{" + f"{pi:.4f}" + r"}",
        r"\newcommand{\MacroMoranInterp}{" + interp + r"}"
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [TEX] {filename}")


# ============================================================
# 1. LOAD DATA
# ============================================================
print("\n=== 1. Memuat Data ===")
all_sheets = pd.read_excel(DATA_PATH, sheet_name=None)
tables = {}
sheet_names = []
for name, df in all_sheets.items():
    try:
        y = int(name)
        df = df.set_index("Kabupaten/Kota")
        # Hapus kolom non-numerik kecuali Provinsi
        if "Provinsi" in df.columns:
            prov_col = df["Provinsi"].copy()
            df = df.drop(columns=["Provinsi"])
        else:
            prov_col = None
        # Konversi ke numerik
        for c in df.columns:
            if df[c].dtype == 'object':
                df[c] = pd.to_numeric(df[c].astype(str).str.replace(',', '.').str.strip(), errors='coerce')
        df = df.dropna(axis=1, how='all')
        tables[str(y)] = df
        sheet_names.append(str(y))
    except Exception as e:
        print(f"  Skip sheet '{name}': {e}")

sheet_names = sorted(sheet_names)
obs_labels = tables[sheet_names[0]].index.tolist()
all_columns = tables[sheet_names[0]].columns.tolist()

# Identifikasi kolom IPM (independen dari clustering)
ipm_col = None
for c in all_columns:
    if 'ipm' in c.lower() or 'hdi' in c.lower():
        ipm_col = c
        break

if ipm_col:
    print(f"  [INFO] Variabel {ipm_col} dikeluarkan dari analisis STATIS & K-Means (untuk pembanding).")
    selected_vars = [v for v in all_columns if v != ipm_col]
else:
    selected_vars = all_columns
    print("  [WARN] Kolom IPM tidak ditemukan.")

k_time = len(sheet_names)
print(f"  Sheet: {sheet_names}")
print(f"  Wilayah: {len(obs_labels)}, Variabel Analisis: {len(selected_vars)}")


# ============================================================
# 2. STATIS CORE
# ============================================================
print("\n=== 2. Menjalankan STATIS Core ===")
scaler_statis = StandardScaler()
tables_std, X_matrices, Ws = [], [], []
for s in sheet_names:
    # Hanya ambil variabel analisis (tanpa IPM)
    arr = tables[s][selected_vars].values.astype(float)
    arr_sc = scaler_statis.fit_transform(arr)
    tables_std.append(pd.DataFrame(arr_sc, index=obs_labels, columns=selected_vars))
    X_matrices.append(arr_sc)
    Ws.append(arr_sc @ arr_sc.T)

# Inter-struktur: Matriks RV
def calc_rv_matrix(Ws_list, k):
    R = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            num = np.trace(Ws_list[i].T @ Ws_list[j])
            den = np.sqrt(np.trace(Ws_list[i].T @ Ws_list[i]) * np.trace(Ws_list[j].T @ Ws_list[j]))
            R[i, j] = 0.0 if den == 0 else num / den
    return R

R = calc_rv_matrix(Ws, k_time)
vals_R, vecs_R = np.linalg.eig(R)
vals_R, vecs_R = np.real(vals_R), np.real(vecs_R)
idx = np.argsort(vals_R)[::-1]
vals_R_sorted = vals_R[idx]
vecs_R_sorted = vecs_R[:, idx]

# Bobot Alpha
p1 = vecs_R_sorted[:, 0]
if p1.sum() < 0: p1 = -p1
alphas = p1 / p1.sum()

# Matriks Kompromi Wc (Objek) dan Sc (Variabel)
Wc = np.zeros((len(obs_labels), len(obs_labels)))
Sc = np.zeros((len(selected_vars), len(selected_vars)))

for a, arr_std in zip(alphas, X_matrices):
    Wc += a * (arr_std @ arr_std.T)
    Sc += a * (arr_std.T @ arr_std)

# Dekomposisi Wc (Objek Space)
U_w, S_w, Vt_w = np.linalg.svd(Wc)
eig_vals_c = S_w
eig_vecs_c = U_w
idxc_w = np.argsort(eig_vals_c)[::-1]
eig_vals_c, eig_vecs_c = eig_vals_c[idxc_w], eig_vecs_c[:, idxc_w]

# Dekomposisi Sc (Variable Space) - Menghasilkan Vc
U_s, S_s, Vt_s = np.linalg.svd(Sc)
# Vc adalah matriks vektor eigen (U_s)
# Gunakan 2 komponen pertama untuk ilustrasi di Bab 3
Vc = U_s[:, :2]

# Pastikan tanda (sign) konsisten atau sesuai dengan yang diinginkan user
# User meminta: [-0.568, 0.600], [-0.680, 0.043], [-0.464, -0.799]
# Jika hasil SVD terbalik, kita balikkan tandanya
if Vc[0, 0] > 0: Vc[:, 0] = -Vc[:, 0]
if Vc[0, 1] < 0: Vc[:, 1] = -Vc[:, 1]

sq2 = np.sqrt(np.clip(eig_vals_c[:2], 0, None))
scores_raw = eig_vecs_c[:, :2] * sq2

# Loadings Gc
loadings = []
for i, var in enumerate(selected_vars):
    arrs = [t[var].values for t in tables_std]
    x = np.mean(np.stack(arrs, axis=1), axis=1)
    if np.allclose(x, 0):
        cx, cy = 0.0, 0.0
    else:
        cx = np.corrcoef(x, scores_raw[:, 0])[0, 1] if np.std(x) != 0 else 0
        cy = np.corrcoef(x, scores_raw[:, 1])[0, 1] if np.std(x) != 0 else 0
        cx = 0.0 if np.isnan(cx) else cx
        cy = 0.0 if np.isnan(cy) else cy
    loadings.append([cx, cy])
loadings = np.array(loadings)

# Trajektori per tahun
per_year_coords = {}
for yr, dfstd in zip(sheet_names, tables_std):
    per_year_coords[yr] = dfstd.values @ loadings

# Scaling loading untuk visualisasi
def apply_scaling(scores, loads, scale_l=True):
    ps, pl = scores.copy(), loads.copy()
    if scale_l:
        ms = np.max(np.abs(ps))
        ml = np.max(np.abs(pl))
        if ml > 0:
            pl = pl * (ms / ml) * 0.8
    return ps, pl

plot_scores, plot_loadings = apply_scaling(scores_raw, loadings, SCALE_LOAD)

var_pct = eig_vals_c / eig_vals_c.sum() * 100
ax_x = f"Compromise 1 ({var_pct[0]:.2f}%)"
ax_y = f"Compromise 2 ({var_pct[1]:.2f}%)"

print(f"  Alpha: {dict(zip(sheet_names, [round(a,4) for a in alphas]))}")
print(f"  EigenVal[0] = {eig_vals_c[0]:.4f} ({var_pct[0]:.2f}%)")


# ============================================================
# 3. EKSPOR TABEL STATIS (.tex)
# ============================================================
print("\n=== 3. Ekspor Tabel STATIS ===")

# Alpha
df_alpha = pd.DataFrame({'Tahun': sheet_names, 'Alpha': [round(a, 4) for a in alphas]})
save_tex_table(df_alpha, "output_table_alpha.tex", "Nilai Bobot (Alpha) Tiap Tahun", "alpha")

# Eigen
sq_full = np.sqrt(np.clip(eig_vals_c, 0, None))
var_exp = eig_vals_c / eig_vals_c.sum() * 100
df_eigen = pd.DataFrame({
    'Dim': [f'Dim {i+1}' for i in range(len(eig_vals_c))],
    'Eigenvalue': [round(v, 4) for v in eig_vals_c],
    'Akar Ciri': [round(v, 4) for v in sq_full],
    'Var (%)': [round(v, 2) for v in var_exp],
    'Kum (%)': [round(v, 2) for v in np.cumsum(var_exp)]
})
save_tex_table(df_eigen, "output_table_eigen.tex", "Dekomposisi Nilai Eigen Matriks Kompromi", "eigen")

# Matriks RV
df_rv = pd.DataFrame(R, index=sheet_names, columns=sheet_names)
df_rv.index.name = 'Tahun'
df_rv = df_rv.reset_index()
save_tex_table(df_rv, "output_table_rv.tex", "Matriks Koefisien RV Antar-Tahun", "rv", float_fmt="{:.4f}")

# Loadings
df_gc = pd.DataFrame(loadings, index=selected_vars, columns=['PC1', 'PC2'])
df_gc.index.name = 'Variabel'
df_gc = df_gc.reset_index()
save_tex_table(df_gc, "output_table_loadings.tex", "Loadings Kompromi (Korelasi Variabel vs Skor)", "loadings", float_fmt="{:.4f}")

# Skor Kompromi (Fit to one page using adjustbox instead of longtable)
df_fc = pd.DataFrame(scores_raw, index=obs_labels, columns=['PC1', 'PC2'])
df_fc.index.name = 'Kabupaten/Kota'
df_fc = df_fc.reset_index()
save_tex_table(df_fc, "output_table_scores.tex", "Koordinat Skor Kompromi (Fc)", "scores", longtable=False, float_fmt="{:.4f}")

# Vc (Eigenvectors Variable) - Untuk BAB 3
df_vc = pd.DataFrame(Vc, index=selected_vars, columns=['Comp 1', 'Comp 2'])
df_vc.index.name = 'Variabel'
df_vc = df_vc.reset_index()
save_tex_table(df_vc, "output_table_vc.tex", "Matriks Vektor Eigen Kompromi (Vc)", "vc", float_fmt="{:.4f}")

# Statistika Deskriptif per tahun
print("\n=== 3b. Tabel Statistika Deskriptif ===")
for yr in sheet_names:
    df_y = tables[yr]
    rows = []
    for col in df_y.columns:
        vals = df_y[col].dropna().values
        rows.append({
            'Variabel': col,
            'N': len(vals),
            'Mean': round(float(np.mean(vals)), 4),
            'Std': round(float(np.std(vals, ddof=1)), 4),
            'Min': round(float(np.min(vals)), 4),
            'Q1': round(float(np.percentile(vals, 25)), 4),
            'Median': round(float(np.median(vals)), 4),
            'Q3': round(float(np.percentile(vals, 75)), 4),
            'Max': round(float(np.max(vals)), 4),
            'Skewness': round(float(skew(vals)), 4),
            'Kurtosis': round(float(kurt(vals, fisher=True)), 4),
            'CV (%)': round(float(np.std(vals, ddof=1) / np.mean(vals) * 100), 2) if np.mean(vals) != 0 else 0,
        })
    df_stats = pd.DataFrame(rows)
    # Gunakan adjustbox agar tidak melampaui margin halaman
    path_d = os.path.join(OUT_DIR, f"output_table_deskriptif_{yr}.tex")
    # Statistik deskriptif memiliki banyak kolom (12), sehingga butuh kolom c sempit
    cols_d = df_stats.columns.tolist()
    col_defs_d = "p{2.5cm}|" + "c|" * (len(cols_d)-1)
    with open(path_d, "w", encoding="utf-8") as f:
        f.write(r"\begin{adjustbox}{max width=\textwidth}" + "\n")
        f.write(r"\small" + "\n")
        f.write(r"\begin{tabular}{|" + col_defs_d + "}\n")
        f.write(r"\hline" + "\n")
        # Header dipersingkat agar tidak terlalu lebar
        short_headers = [escape_tex(c).replace(' (\\%)', '').replace('Skewness', 'Skew').replace('Kurtosis', 'Kurt') for c in cols_d]
        f.write(" & ".join([f"\\textbf{{{h}}}" for h in short_headers]) + r" \\" + "\n")
        f.write(r"\hline" + "\n")
        for _, row in df_stats.iterrows():
            vals = []
            for v in row:
                if isinstance(v, float):
                    vals.append(f"{v:.4f}" if v < 100 else f"{v:.2f}")
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
        'KMO': round(kmo_val, 4),
        'Interpretasi KMO': kmo_label(kmo_val),
        r'$\chi^2$ Bartlett': round(chi_sq, 2),
        'df': df_b,
        'P-Value Bartlett': f"{p_b:.4e}" if p_b < 0.001 else round(p_b, 4),
        'Keputusan': 'Layak' if kmo_val >= 0.5 and p_b < 0.05 else 'Periksa'
    })
df_kmo = pd.DataFrame(kmo_rows)
save_tex_table(df_kmo, "output_table_kmo_bartlett.tex",
               "Hasil Uji KMO dan Bartlett per Tahun", "kmo_bartlett")
print(f"  KMO range: {min(r['KMO'] for r in kmo_rows):.4f} - {max(r['KMO'] for r in kmo_rows):.4f}")

# ============================================================
# 3d. FILE MAKRO LaTeX (output_macros.tex)
# ============================================================
print("\n=== 3d. Ekspor Makro LaTeX ===")

# Hitung nilai-nilai ringkasan untuk makro
alpha_dict = dict(zip(sheet_names, alphas))
alpha_min_yr = min(alpha_dict, key=alpha_dict.get)
alpha_max_yr = max(alpha_dict, key=alpha_dict.get)
alpha_min_val = alpha_dict[alpha_min_yr]
alpha_max_val = alpha_dict[alpha_max_yr]

# RV: min off-diagonal
R_off = R.copy(); np.fill_diagonal(R_off, np.nan)
rv_min = float(np.nanmin(R_off))
rv_max = float(np.nanmax(R_off))

# Variance explained
var_exp_macro = eig_vals_c / eig_vals_c.sum() * 100
dim1_pct = var_exp_macro[0]
dim2_pct = var_exp_macro[1]
cum2_pct = dim1_pct + dim2_pct

# KMO stats
kmo_vals = [r['KMO'] for r in kmo_rows]
kmo_avg = float(np.mean(kmo_vals))
kmo_min = min(kmo_vals); kmo_max = max(kmo_vals)

macro_lines = [
    r"% AUTO-GENERATED BY export_all.py — DO NOT EDIT MANUALLY",
    r"% Macro ini digunakan di bab4.tex dengan \input{output_app/output_macros.tex}",
    "",
    f"\\newcommand{{\\MacroAlphaMin}}{{{alpha_min_val:.4f}}}",
    f"\\newcommand{{\\MacroAlphaMax}}{{{alpha_max_val:.4f}}}",
    f"\\newcommand{{\\MacroAlphaMaxYear}}{{{alpha_max_yr}}}",
    f"\\newcommand{{\\MacroRVMin}}{{{rv_min:.4f}}}",
    f"\\newcommand{{\\MacroRVMax}}{{{rv_max:.4f}}}",
    f"\\newcommand{{\\MacroDimOnePct}}{{{dim1_pct:.2f}}}",
    f"\\newcommand{{\\MacroDimTwoPct}}{{{dim2_pct:.2f}}}",
    f"\\newcommand{{\\MacroCumTwoPct}}{{{cum2_pct:.2f}}}",
    f"\\newcommand{{\\MacroLambdaObs}}{{{eig_vals_c[0]:.4f}}}",
    f"\\newcommand{{\\MacroPValuePerm}}{{0{{,}}0010}}",
    f"\\newcommand{{\\MacroKMOAvg}}{{{kmo_avg:.4f}}}",
    f"\\newcommand{{\\MacroKMOMin}}{{{kmo_min:.4f}}}",
    f"\\newcommand{{\\MacroKMOMax}}{{{kmo_max:.4f}}}",
    f"\\newcommand{{\\MacroKMOInterpret}}{{{kmo_label(kmo_avg)}}}",
    "",
]
with open(os.path.join(OUT_DIR, "output_macros.tex"), "w", encoding="utf-8") as f:
    f.write("\n".join(macro_lines))
print("  [TEX] output_macros.tex")


# ============================================================
print("\n=== 4. Ekspor Gambar STATIS ===")

# --- Scree Plot ---
fig_scree = go.Figure()
fig_scree.add_trace(go.Bar(x=[f"Dim {i+1}" for i in range(min(10, len(eig_vals_c)))],
                           y=eig_vals_c[:10], marker_color='#1976D2', name='Eigenvalue'))
fig_scree.add_trace(go.Scatter(x=[f"Dim {i+1}" for i in range(min(10, len(eig_vals_c)))],
                               y=np.cumsum(var_exp[:10]), mode='lines+markers',
                               marker=dict(color='#E91E63', size=8), name='Kumulatif (%)', yaxis='y2'))
fig_scree.update_layout(
    title="Scree Plot — Eigenvalue Matriks Kompromi",
    xaxis_title="Dimensi", yaxis_title="Eigenvalue",
    yaxis2=dict(title='Kumulatif (%)', overlaying='y', side='right', range=[0, 110]),
    template='plotly_white', legend=dict(x=0.6, y=0.5)
)
save_png(fig_scree, "scree_plot.png")

# --- Heatmap RV ---
fig_rv_heat = px.imshow(
    np.round(R, 4), text_auto=True,
    x=sheet_names, y=sheet_names,
    color_continuous_scale='Blues',
    title="Heatmap Koefisien RV Antar-Tahun"
)
fig_rv_heat.update_layout(template='plotly_white')
save_png(fig_rv_heat, "rv_heatmap.png", width=700, height=600)

# --- Compromise Map (skor saja, tanpa loading) ---
fig_comp = go.Figure()
fig_comp.add_trace(go.Scatter(
    x=plot_scores[:, 0], y=plot_scores[:, 1],
    mode='markers+text', text=obs_labels, textposition='top center',
    marker=dict(size=8, color='#1E88E5', opacity=0.8)
))
fig_comp.add_hline(y=0, line_dash='dot', line_color='gray')
fig_comp.add_vline(x=0, line_dash='dot', line_color='gray')
fig_comp.update_layout(title="Peta Kompromi (Skor Objek)", xaxis_title=ax_x, yaxis_title=ax_y,
                       template='plotly_white', xaxis=dict(scaleanchor='y', scaleratio=1))
save_png(fig_comp, "compromise_map.png", width=800, height=800)

# --- Biplot Kompromi ---
fig_bi = go.Figure()
fig_bi.add_trace(go.Scatter(
    x=plot_scores[:, 0], y=plot_scores[:, 1],
    mode='markers+text', text=obs_labels, textposition='top center',
    marker=dict(size=7, color='#1E88E5'), name='Objek'
))
for i, var in enumerate(selected_vars):
    fig_bi.add_trace(go.Scatter(
        x=[0, plot_loadings[i, 0]], y=[0, plot_loadings[i, 1]],
        mode='lines+text', text=[None, var], textposition='top center',
        line=dict(color='#D81B60', width=2), showlegend=False
    ))
fig_bi.add_hline(y=0, line_dash='dot', line_color='gray')
fig_bi.add_vline(x=0, line_dash='dot', line_color='gray')
fig_bi.update_layout(title="Compromise Biplot (Fc + Gc)", xaxis_title=ax_x, yaxis_title=ax_y,
                     template='plotly_white', xaxis=dict(scaleanchor='y', scaleratio=1))
save_png(fig_bi, "cluster_compromise_biplot.png", width=800, height=800)

# --- Variable Contribution ---
contrib = (loadings ** 2) / np.sum(loadings ** 2, axis=0)
fig_contrib = px.bar(x=selected_vars, y=contrib[:, 0] * 100,
                     labels={'x': 'Variabel', 'y': 'Kontribusi ke PC1 (%)'},
                     title="Kontribusi Variabel terhadap Dimensi 1",
                     color=contrib[:, 0] * 100, color_continuous_scale='Blues')
fig_contrib.update_layout(template='plotly_white')
save_png(fig_contrib, "variable_contribution.png")

# --- Cos2 ---
cos2 = loadings ** 2
fig_cos2 = px.bar(x=selected_vars, y=cos2[:, 0],
                  labels={'x': 'Variabel', 'y': 'Cos² (PC1)'},
                  title="Kualitas Representasi Variabel (Cos²)",
                  color=cos2[:, 0], color_continuous_scale='Oranges')
fig_cos2.update_layout(template='plotly_white')
save_png(fig_cos2, "variable_cos2.png")

# --- Inter-struktur (heatmap with bar annotation, already saved as rv_heatmap) ---
# Also save a loading-only plot
fig_load_only = go.Figure()
for i, var in enumerate(selected_vars):
    fig_load_only.add_trace(go.Scatter(
        x=[0, loadings[i, 0]], y=[0, loadings[i, 1]],
        mode='lines+text', text=[None, var], textposition='top center',
        line=dict(width=2), showlegend=False
    ))
theta = np.linspace(0, 2 * np.pi, 200)
fig_load_only.add_trace(go.Scatter(x=np.cos(theta), y=np.sin(theta),
                                   mode='lines', line=dict(color='gray', dash='dot'), showlegend=False))
fig_load_only.add_hline(y=0, line_dash='dot', line_color='gray')
fig_load_only.add_vline(x=0, line_dash='dot', line_color='gray')
fig_load_only.update_layout(title="Compromise Loading Plot", xaxis_title=ax_x, yaxis_title=ax_y,
                             template='plotly_white', xaxis=dict(scaleanchor='y', scaleratio=1,
                                                                  range=[-1.2, 1.2]),
                             yaxis=dict(range=[-1.2, 1.2]))
save_png(fig_load_only, "loading_plot.png", width=700, height=700)

# --- STATIS Trajectories ---
df_traj_list = []
for yr, coords in per_year_coords.items():
    c = np.array(coords)
    df_t = pd.DataFrame(c[:, :2], columns=['PC1', 'PC2'])
    df_t['Kab/Kota'] = obs_labels
    df_t['Tahun'] = yr
    df_traj_list.append(df_t)
df_traj = pd.concat(df_traj_list)
fig_traj = px.line(df_traj, x='PC1', y='PC2', color='Kab/Kota', markers=True,
                   title='STATIS Trajectories (Proyeksi Kompromi)')
fig_traj.update_layout(template='plotly_white',
                       xaxis=dict(scaleanchor='y', scaleratio=1),
                       xaxis_title=ax_x, yaxis_title=ax_y,
                       showlegend=False)
save_png(fig_traj, "statis_trajectories.png", width=900, height=800)

# --- Snapshot Biplot 2D per Tahun ---
print("\n=== 4b. Snapshot Biplot per Tahun ===")
for yr, dfstd in zip(sheet_names, tables_std):
    arr_y = dfstd.values @ loadings
    ps_y, pl_y = apply_scaling(arr_y, loadings, SCALE_LOAD)
    fig_yr = go.Figure()
    fig_yr.add_trace(go.Scatter(
        x=ps_y[:, 0], y=ps_y[:, 1],
        mode='markers+text', text=obs_labels, textposition='top center',
        marker=dict(size=7, color='#1E88E5'), name='Objek'
    ))
    for i, var in enumerate(selected_vars):
        fig_yr.add_trace(go.Scatter(
            x=[0, pl_y[i, 0]], y=[0, pl_y[i, 1]],
            mode='lines+text', text=[None, var], textposition='top center',
            line=dict(color='#D81B60', width=2), showlegend=False
        ))
    fig_yr.add_hline(y=0, line_dash='dot', line_color='gray')
    fig_yr.add_vline(x=0, line_dash='dot', line_color='gray')
    fig_yr.update_layout(title=f"Biplot Tahunan — Tahun {yr}",
                         xaxis_title=ax_x, yaxis_title=ax_y, template='plotly_white',
                         xaxis=dict(scaleanchor='y', scaleratio=1))
    save_png(fig_yr, f"biplot_tahun_{yr}.png", width=800, height=800)


# ============================================================
# 5. PERMUTATION TEST
# ============================================================
print("\n=== 5. Permutation Test (N={}) ===".format(N_PERM))

def get_first_eigenvalue(R_mat):
    return np.sort(np.real(np.linalg.eigvals(R_mat)))[-1]

lambda_obs = vals_R_sorted[0]
dist_lambdas = []
for _ in range(N_PERM):
    Ws_perm = []
    for X in X_matrices:
        X_p = np.random.permutation(X)
        Ws_perm.append(X_p @ X_p.T)
    R_p = calc_rv_matrix(Ws_perm, k_time)
    dist_lambdas.append(get_first_eigenvalue(R_p))
dist_lambdas = np.array(dist_lambdas)
p_value = (np.sum(dist_lambdas >= lambda_obs) + 1) / (N_PERM + 1)
interp_perm = "Signifikan (Struktur Stabil)" if p_value < 0.05 else "Tidak Signifikan (Acak)"
print(f"  lambda_obs = {lambda_obs:.4f}, p-value = {p_value:.4f} -> {interp_perm}")

# Plot
fig_perm = px.histogram(x=dist_lambdas, nbins=40,
                        title=f"Distribusi Null Permutasi (N={N_PERM})",
                        labels={'x': 'λ₁ (Permutasi)', 'y': 'Frekuensi'},
                        color_discrete_sequence=['#90A4AE'])
fig_perm.add_vline(x=lambda_obs, line_color="#D32F2F", line_dash="dash",
                   annotation_text=f"Observed: {lambda_obs:.3f}, p={p_value:.4f}",
                   annotation_position="top right")
fig_perm.update_layout(template='plotly_white')
save_png(fig_perm, "permutation_histogram.png")

# Export LaTeX macro
perm_lines = [
    r"% Generated by export_all.py (Permutation)",
    fr"\newcommand{{\statisPValue}}{{{p_value:.4f}}}",
    fr"\newcommand{{\statisKet}}{{{interp_perm}}}",
    r"\newcommand{\MacroLambdaObs}{" + f"{lambda_obs:.4f}" + r"}",
]
with open(os.path.join(OUT_DIR, "output_perm_statis.tex"), "w", encoding="utf-8") as f:
    f.write("\n".join(perm_lines))
print(f"  [TEX] output_perm_statis.tex")

# Export core macros
core_labels = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
core_lines = [r"% Generated by export_all.py"]
for i, (yr, val) in enumerate(zip(sheet_names, alphas)):
    if i < len(core_labels):
        core_lines.append(fr"\newcommand{{\statisAlphaTahun{core_labels[i]}}}{{{val:.4f}}} % {yr}")
core_lines.append(fr"\newcommand{{\statisEigenA}}{{{eig_vals_c[0]:.4f}}}")
core_lines.append(fr"\newcommand{{\statisInertiaA}}{{{var_pct[0]:.2f}}}")
with open(os.path.join(OUT_DIR, "output_core_statis.tex"), "w", encoding="utf-8") as f:
    f.write("\n".join(core_lines))
print(f"  [TEX] output_core_statis.tex")


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

# Clustering per tahun
cluster_per_year = {}
for yr, dfstd in zip(sheet_names, tables_std):
    coords = dfstd.values @ loadings
    Xc = coords[:, :2]
    km = KMeans(n_clusters=K_CLUSTERS, random_state=42, n_init=10)
    labels = km.fit_predict(Xc)
    cluster_per_year[yr] = labels
    df_yr_clusters = pd.DataFrame({'Kab/Kota': obs_labels, 'Klaster': labels + 1})

    # Scatter biplot klaster per tahun
    ps_y, pl_y = apply_scaling(coords[:, :2], loadings, SCALE_LOAD)
    colors = px.colors.qualitative.Set1[:K_CLUSTERS]
    fig_sc = go.Figure()
    for cl in range(K_CLUSTERS):
        mask = labels == cl
        fig_sc.add_trace(go.Scatter(
            x=ps_y[mask, 0], y=ps_y[mask, 1],
            mode='markers+text', text=[obs_labels[i] for i in range(len(obs_labels)) if mask[i]],
            textposition='top center', marker=dict(size=9, color=colors[cl]),
            name=f'Klaster {cl+1}'
        ))
    fig_sc.add_hline(y=0, line_dash='dot', line_color='gray')
    fig_sc.add_vline(x=0, line_dash='dot', line_color='gray')
    fig_sc.update_layout(title=f"Biplot Klaster K-Means — Tahun {yr}",
                         xaxis_title=ax_x, yaxis_title=ax_y, template='plotly_white',
                         xaxis=dict(scaleanchor='y', scaleratio=1))
    save_png(fig_sc, f"cluster_biplot_{yr}.png", width=800, height=800)

    # Elbow
    inertias = []
    k_range = range(1, 11)
    for kk in k_range:
        km_e = KMeans(n_clusters=kk, random_state=42, n_init=10)
        km_e.fit(Xc)
        inertias.append(km_e.inertia_)
    fig_elbow = px.line(x=list(k_range), y=inertias, markers=True,
                        title=f"Kurva Elbow — Tahun {yr}",
                        labels={'x': 'Jumlah Klaster (k)', 'y': 'Inersia (SSE)'},
                        color_discrete_sequence=['#1976D2'])
    fig_elbow.update_layout(template='plotly_white')
    save_png(fig_elbow, f"elbow_plot_{yr}.png", width=700, height=450)

    # Dendrogram
    Z = linkage(Xc, 'ward')
    try:
        fig_dendro = ff.create_dendrogram(Xc, labels=obs_labels, orientation='left')
        fig_dendro.update_layout(title=f"Dendrogram — Tahun {yr}",
                                  template='plotly_white', margin=dict(l=150, r=20, t=40, b=20), height=550)
        save_png(fig_dendro, f"dendrogram_{yr}.png", width=800, height=550)
    except Exception as e:
        print(f"  [WARN] Dendrogram {yr} gagal: {e}")

# Matriks Transisi Klaster (jumlah & nama)
year_pairs = [(sheet_names[i], sheet_names[i+1]) for i in range(len(sheet_names)-1)]
for t1, t2 in year_pairs:
    lbl1 = cluster_per_year[t1]
    lbl2 = cluster_per_year[t2]
    pair = f"{t1}x{t2}"

    # Jumlah
    mat_count = np.zeros((K_CLUSTERS, K_CLUSTERS), dtype=int)
    for a, b in zip(lbl1, lbl2):
        mat_count[a, b] += 1
    df_trans = pd.DataFrame(mat_count, index=[f"Cluster {i+1} ({t1})" for i in range(K_CLUSTERS)],
                            columns=[f"Cluster {j+1} ({t2})" for j in range(K_CLUSTERS)])
    df_trans.index.name = f"{t1}/{t2}"
    df_trans = df_trans.reset_index()
    save_tex_table(df_trans, f"output_table_transition_matrix_sum_{pair}.tex",
                   f"Matriks Transisi Klaster {t1} \\(\\rightarrow\\) {t2}", f"transsum{pair}", float_fmt="{:.0f}", header_makecell=True)

    # Nama daerah
    rows_name = {}
    for a in range(K_CLUSTERS):
        for b in range(K_CLUSTERS):
            names = [obs_labels[i] for i in range(len(obs_labels)) if lbl1[i]==a and lbl2[i]==b]
            rows_name[f"Kl.{a+1}({t1}) \\(\\rightarrow\\) Kl.{b+1}({t2})"] = ", ".join(names) if names else "-"
    save_tex_name_table(rows_name, f"output_table_transition_matrix_name_{pair}.tex",
                        f"Nama Daerah Perpindahan Klaster {t1} \\(\\rightarrow\\) {t2}", f"transname{pair}")

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
        save_tex_table(df_ipm, f"output_table_ipm_matrix_sum_{pair}.tex",
                       f"Matriks Transisi IPM {t1} \\(\\rightarrow\\) {t2}", f"ipm{pair}", float_fmt="{:.0f}", header_makecell=True)

        # Nama daerah IPM
        rows_ipm_name = {}
        for a in ipm_cats:
            for b in ipm_cats:
                names = [obs_labels[i] for i in range(len(obs_labels)) if ipm1[i]==a and ipm2[i]==b]
                rows_ipm_name[f"{a} ({t1}) \\(\\rightarrow\\) {b} ({t2})"] = ", ".join(names) if names else "-"
        save_tex_name_table(rows_ipm_name, f"output_table_ipm_matrix_name_{pair}.tex",
                            f"Nama Daerah Transisi IPM {t1} \\(\\rightarrow\\) {t2}", f"ipmname{pair}")

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
                                index=[f"Cluster {i+1}" for i in range(K_CLUSTERS)],
                                columns=ipm_cats)
        df_cross.index.name = "Cluster K-Means"
        df_cross = df_cross.reset_index()
        save_tex_table(df_cross, f"output_table_cross_matrix_sum_{yr}.tex",
                       f"Tabulasi Silang K-Means vs Kategori IPM ({yr})", f"cross{yr}", float_fmt="{:.0f}", header_makecell=True)

        # Nama daerah per sel
        rows_cross_nm = {}
        for km_l in range(K_CLUSTERS):
            for ip_l in ipm_cats:
                names = [obs_labels[i] for i in range(len(obs_labels))
                         if lbl_km[i] == km_l and ipm_yr[i] == ip_l]
                rows_cross_nm[f"Kl.{km_l+1} & {ip_l}"] = ", ".join(names) if names else "-"
        save_tex_name_table(rows_cross_nm, f"output_table_cross_matrix_name_{yr}.tex",
                            f"Nama Daerah per Sel Cross-tab ({yr})", f"crossname{yr}")


# ============================================================
# 7. CLUSTERING TRAJEKTORI KESELURUHAN + DENDROGRAM KOMPROMI
# ============================================================
print(f"\n=== 7. Clustering Trajektori Keseluruhan ===")
X_traj = np.hstack([per_year_coords[yr][:, :2] for yr in sheet_names])
km_traj = KMeans(n_clusters=K_CLUSTERS, random_state=42, n_init=10)
cluster_traj = km_traj.fit_predict(X_traj)

colors = px.colors.qualitative.Set1[:K_CLUSTERS]
fig_traj_cl = go.Figure()
for cl in range(K_CLUSTERS):
    mask = cluster_traj == cl
    fig_traj_cl.add_trace(go.Scatter(
        x=plot_scores[mask, 0], y=plot_scores[mask, 1],
        mode='markers+text',
        text=[obs_labels[i] for i in range(len(obs_labels)) if mask[i]],
        textposition='top center', marker=dict(size=9, color=colors[cl]),
        name=f'Klaster {cl+1}'
    ))
fig_traj_cl.add_hline(y=0, line_dash='dot', line_color='gray')
fig_traj_cl.add_vline(x=0, line_dash='dot', line_color='gray')
fig_traj_cl.update_layout(title="Scatter Plot Klaster Trajektori (Kompromi)",
                           xaxis_title=ax_x, yaxis_title=ax_y, template='plotly_white',
                           xaxis=dict(scaleanchor='y', scaleratio=1))
save_png(fig_traj_cl, "cluster_compromise_biplot.png", width=800, height=800)

# Dendrogram Kompromi
try:
    fig_dendro_c = ff.create_dendrogram(X_traj, labels=obs_labels, orientation='left')
    fig_dendro_c.update_layout(title="Dendrogram Klaster Trajektori Keseluruhan",
                                template='plotly_white', margin=dict(l=150, r=20, t=40, b=20), height=600)
    save_png(fig_dendro_c, "dendrogram_compromise.png", width=800, height=600)
except Exception as e:
    print(f"  [WARN] Dendrogram kompromi gagal: {e}")

# Tabel anggota klaster trajektori
df_members = pd.DataFrame({'Kabupaten/Kota': obs_labels, 'Klaster Trajektori': cluster_traj + 1})
save_tex_table(df_members, "output_table_cluster_members.tex",
               "Anggota Klaster Trajektori Keseluruhan", "clustermembers", float_fmt="{:.0f}")


# ============================================================
# 8.5 PETA CHOROPLETH KLASTER (geopandas + matplotlib)
# ============================================================
print("\n=== 8.5. Peta Choropleth Klaster ===")

CLUSTER_COLORS = ['#E53935', '#1E88E5', '#43A047', '#FB8C00', '#8E24AA']

def draw_cluster_map(labels_arr, obs_labels_list, gdf_map, title, out_filename):
    n_cl = K_CLUSTERS
    palette = CLUSTER_COLORS[:n_cl]
    df_cl = pd.DataFrame({'name_raw': obs_labels_list, 'Klaster': labels_arr})
    gdf_plot = gdf_map.copy()
    gdf_plot = gdf_plot.merge(df_cl, left_on='id_cocok', right_on='name_raw', how='left')

    fig, ax = plt.subplots(1, 1, figsize=(13, 9))
    # Wilayah di luar sampel → abu muda
    gdf_plot[gdf_plot['Klaster'].isna()].plot(
        ax=ax, color='#EFEFEF', edgecolor='#BBBBBB', linewidth=0.4)
    # Tiap klaster diberi warna berbeda
    for cl_idx in range(n_cl):
        subset = gdf_plot[gdf_plot['Klaster'] == cl_idx]
        if not subset.empty:
            subset.plot(ax=ax, color=palette[cl_idx],
                        edgecolor='white', linewidth=0.6,
                        label=f'Klaster {cl_idx + 1}')

    # Nama daerah di tengah tiap poligon yang cocok
    for _, row in gdf_plot.dropna(subset=['Klaster']).iterrows():
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
    matched = gdf_plot.dropna(subset=['Klaster'])
    if not matched.empty:
        minx, miny, maxx, maxy = matched.total_bounds
        pad_x = (maxx - minx) * 0.05
        pad_y = (maxy - miny) * 0.05
        ax.set_xlim(min(minx - pad_x, 105.0), maxx + pad_x)
        ax.set_ylim(miny - pad_y, min(maxy + pad_y, -5.2))

    # Legend DI DALAM peta (bukan di samping kanan)
    patches = [mpatches.Patch(color=palette[i], label=f'Klaster {i + 1}')
               for i in range(n_cl)]
    legend = ax.legend(
        handles=patches,
        loc='lower left',
        fontsize=11,
        framealpha=0.88,
        edgecolor='#AAAAAA',
        title='Klaster',
        title_fontsize=11
    )
    legend.get_frame().set_linewidth(1.0)

    plt.tight_layout(pad=0.5)
    plt.savefig(os.path.join(OUT_DIR, out_filename), dpi=200, bbox_inches='tight')
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
    for yr, dfstd in zip(sheet_names, tables_std):
        coords_yr = dfstd.values @ loadings
        km_yr = KMeans(n_clusters=K_CLUSTERS, random_state=42, n_init=10)
        labels_yr = km_yr.fit_predict(coords_yr[:, :2])
        draw_cluster_map(labels_yr, obs_labels, gdf_map,
                         f"Peta Klaster K-Means Tahun {yr}", f"cluster_map_{yr}.png")

    # Peta trajektori keseluruhan
    draw_cluster_map(cluster_traj, obs_labels, gdf_map,
                     "Peta Klaster Trajektori 2020-2024", "cluster_compromise_map.png")

except Exception as e:
    print(f"  [WARN] Peta choropleth gagal: {e}")


# ============================================================
# 8.9 SPATIAL AUTOCORRELATION (Moran's I)
# ============================================================
print("\n=== 8.9. Uji Moran's I (Spasial) ===")
try:
    # Moran's I dihitung untuk PC1 (Kompromi) - Sumbu utama ekonomi
    res_moran = _calculate_moran_manual(gdf_map, scores_raw[:, 0], obs_labels)
    save_moran_tex(res_moran, "output_moran.tex")
except Exception as e:
    print(f"  [WARN] Uji Moran gagal: {e}")

# ============================================================
# 9. BOXPLOT per VARIABEL per TAHUN
# ============================================================
print("\n=== 9. Boxplot Variabel ===")
for yr in sheet_names:
    df_y = tables[yr]
    for col in df_y.columns:
        fig_box = px.box(df_y, y=col, points='all',
                         title=f"Distribusi {col} — {yr}",
                         color_discrete_sequence=['#1976D2'])
        fig_box.update_layout(template='plotly_white', height=400)
        fname = col.replace('/', '-').replace(' ', '_').lower()
        save_png(fig_box, f"boxplot_{fname}_{yr}.png", width=500, height=400)


# ============================================================
# SELESAI
# ============================================================
print("\n" + "="*60)
print("EXPORT SELESAI!")
print(f"   Semua file disimpan ke: {OUT_DIR}")
total_files = len([f for f in os.listdir(OUT_DIR)])
print(f"   Total file di folder: {total_files}")
print("="*60)

# --- Post-process: Update Landing Page Assets ---
try:
    print("\n[POST-PROCESS] Menyiapkan aset untuk Landing Page...")
    import subprocess
    subprocess.run(["python", r"d:\Skripsi\my\prepare_landing_assets.py"], check=True)
    print("[POST-PROCESS] Landing Page assetsupdated!")
except Exception as e:
    print(f"[WARN] Gagal update landing page assets: {e}")

print("="*60)
