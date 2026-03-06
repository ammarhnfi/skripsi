# Import Library
import dash
import json
import geopandas as gpd
from dash import Dash, dcc, html, Input, Output, State, dash_table, exceptions, ctx
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from scipy.cluster.hierarchy import dendrogram, linkage
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import base64

# Inisialisasi library
pd.set_option('display.max_columns', None)
scaler = StandardScaler()
pca = PCA(n_components=2)

# --- KONFIGURASI LINK DATASET CONTOH ---
BASE_URL = "https://huggingface.co/spaces/ammarhnfi/skripsi/resolve/main" 
EXAMPLE_DATASETS = [
    {"name": "Data Gabungan (FINAL DATA.xlsx)", "url": f"{BASE_URL}/FINAL DATA.xlsx"},
]

# --- STYLING (Modern Blue Theme) ---
EXTERNAL_STYLESHEETS = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# Warna Tema
COLOR_BG_MAIN = "#F0F4F8"       # Abu kebiruan sangat muda (Background)
COLOR_CARD_BG = "#FFFFFF"       # Putih (Card)
COLOR_HEADER_TEXT = "#1565C0"   # Biru Tua (Judul)
COLOR_ACCENT = "#1976D2"        # Biru (Tombol/Highlight)
COLOR_BORDER = "#BBDEFB"        # Biru Muda (Border)

CARD_STYLE = {
    "boxShadow": "0 2px 5px 0 rgba(0,0,0,0.05)",
    "borderRadius": "8px",
    "backgroundColor": COLOR_CARD_BG,
    "padding": "25px",
    "marginBottom": "25px",
    "border": f"1px solid {COLOR_BORDER}"
}

HEADER_STYLE = {
    "textAlign": "center", 
    "color": COLOR_HEADER_TEXT, 
    "fontWeight": "700", 
    "marginBottom": "15px",
    "letterSpacing": "0.5px"
}

LABEL_STYLE = {
    "fontWeight": "600",
    "color": "#37474F",
    "fontSize": "1.4rem",
    "marginBottom": "8px"
}

# --- [GANTI BAGIAN LOAD DATA] ---
# Jika file .shp ada di folder laptop Anda (misal: 'peta_indo.shp')
try:
    print("Sedang membaca Shapefile...")
    # Baca Shapefile pakai Geopandas
    gdf = gpd.read_file("gadm41_IDN_2.shp") 
    print("Mengoptimalkan/Menyederhanakan geometri peta...")
    # 2. SIMPLIFIKASI GEOMETRI (PENTING!)
    # tolerance=0.005 derajat (sekitar 500m). Ini drastis mengurangi ukuran file 
    # tapi bentuk pulau/kota masih sangat dikenali untuk visualisasi web.
    gdf['geometry'] = gdf['geometry'].simplify(tolerance=0.005, preserve_topology=True)
    # KONVERSI KE GEOJSON (Wajib! Karena Plotly cuma ngerti GeoJSON)
    indonesia_geojson = json.loads(gdf.to_json())
    print("Peta berhasil dimuat, disederhanakan, dan dikonversi!")
except Exception as e:
    print(f"Gagal memuat Shapefile: {e}")
    indonesia_geojson = None

# -----------------------------
# Helper Functions
# -----------------------------
def get_rotation_angle(df_pc, df_load, baseline_type, baseline_name, year):
    try:
        vec = np.array([0.0, 0.0])
        if baseline_type == 'skor':
            sub = df_pc[(df_pc['Kabupaten/Kota'] == baseline_name) & (df_pc['Tahun'] == year)]
            if not sub.empty: vec = sub[['PC1', 'PC2']].iloc[0].values
        elif baseline_type == 'loading':
            sub = df_load[(df_load['features'] == baseline_name) & (df_load['Tahun'] == year)]
            if not sub.empty: vec = sub[['PC1', 'PC2']].iloc[0].values
        if np.allclose(vec, 0): return 0.0
        return -np.arctan2(vec[1], vec[0])
    except: return 0.0

def rotate_dataframe(df, angle, cols=['PC1', 'PC2']):
    df_rot = df.copy()
    if len(cols) < 2: return df_rot
    c, s = np.cos(angle), np.sin(angle)
    R = np.array([[c, -s], [s, c]])
    vals = df_rot[cols].values
    df_rot[cols] = vals.dot(R.T)
    return df_rot

def _calculate_R_matrix(Ws_list, k):
    R = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            num = np.trace(Ws_list[i].T @ Ws_list[j])
            den = np.sqrt(np.trace(Ws_list[i].T @ Ws_list[i]) * np.trace(Ws_list[j].T @ Ws_list[j]))
            R[i, j] = 0.0 if den == 0 else num / den
    return R

def _get_first_eigenvalue(R_matrix):
    vals = np.linalg.eigvals(R_matrix)
    return np.sort(np.real(vals))[-1]

# --- Helper untuk Dendrogram ke Plotly ---
def _calculate_moran_manual(gdf, value_analytics, obs_names_analytics):
    """
    Hitung Moran's I secara manual menggunakan Geopandas adjacency (Touches).
    Tanpa library pysal/esda agar ringan.
    """
    try:
        # 1. Match Data dengan GeoData
        # Kita butuh geometri yang sesuai urutan data analisis
        # Buat mapping nama -> geometri
        geom_map = {}
        for _, row in gdf.iterrows():
            # Coba berbagai kemungkinan nama properti
            name = row.get('NAME_2') or row.get('kab_kota') or row.get('NAMOBJ') or row.get('Name') or ""
            if name: geom_map[str(name)] = row['geometry']
            
        # 2. Re-construct Series data yang urut
        y = []
        geoms = []
        valid_indices = []
        
        for i, name in enumerate(obs_names_analytics):
            if name in geom_map:
                y.append(value_analytics[i])
                geoms.append(geom_map[name])
                valid_indices.append(i)
        
        if len(y) < 5: return None, None # Terlalu sedikit
        
        y = np.array(y)
        n = len(y)
        
        # 3. Buat Weight Matrix (W) berdasarkan sentuhan (Queen Contiguity)
        # Ini manual: cek satu-satu intersection/touches (O(n^2) tapi n=41 kecil jadi aman)
        W = np.zeros((n, n))
        temp_gdf = gpd.GeoDataFrame({'geometry': geoms})
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    if temp_gdf.iloc[i].geometry.touches(temp_gdf.iloc[j].geometry):
                        W[i, j] = 1.0
        
        # Row Standardization
        row_sums = W.sum(axis=1)
        # Hindari bagi nol
        with np.errstate(divide='ignore', invalid='ignore'):
            W_std = W / row_sums[:, None]
        W_std[np.isnan(W_std)] = 0.0
        
        # 4. Hitung Moran's I
        y_bar = np.mean(y)
        y_dev = y - y_bar
        sum_sq_dev = np.sum(y_dev**2)
        
        numerator = 0.0
        for i in range(n):
            for j in range(n):
                numerator += W_std[i, j] * y_dev[i] * y_dev[j]
        
        moran_i = (n / np.sum(W)) * (numerator / sum_sq_dev) if np.sum(W) > 0 else 0
        
        # Hitung Z-score (Approximation)
        # E[I] = -1 / (N-1)
        expected_i = -1.0 / (n - 1)
        # Var[I] simple approximation (Bootstrap atau analytical kompleks, kita pakai simple visual interpretation saja dulu atau 0)
        # Biar aman kita return I dan Expected saja
        return moran_i, expected_i
        
    except Exception as e:
        print(f"Moran Error: {e}")
        return None, None

def create_dendrogram_plot(X, labels):
    # Hitung Linkage Matrix
    Z = linkage(X, 'ward')
    # Create dendrogram figure factory is heavy, manual approach for speed:
    # Kita pakai Plotly Figure Factory (ff) kalau ada, tapi biar ringan kita pakai Scipy text logic atau simple plot.
    # Agar simple dan cantik, kita pakai library plotly.figure_factory jika diinstall. 
    # TAPI KARENA SAYA TIDAK TAHU APAKAH ANDA PUNYA, SAYA PAKAI LOGIKA MANUAL YANG AMAN:
    
    import plotly.figure_factory as ff
    try:
        fig = ff.create_dendrogram(X, labels=labels, orientation='left')
        fig.update_layout(template='plotly_white', margin=dict(l=150, r=20, t=20, b=20), height=450)
        return fig
    except:
        # Fallback jika library kurang lengkap (jarang terjadi di env standar)
        fig = go.Figure()
        fig.add_annotation(text="Mohon install 'scipy' agar dendrogram muncul.", showarrow=False)
        return fig

# -----------------------------
# LATEX EXPORT HELPERS
# -----------------------------
def export_core_latex(res):
    try:
        lines = []
        lines.append(r"% Generated by final.py")
        lines.append(r"\newcommand{\statisDatasetName}{Data Statistik}")
        
        # Alphas
        alphas = res.get('alphas', [])
        years = res.get('sheet_names', [])
        labels = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        for i, (yr, val) in enumerate(zip(years, alphas)):
            if i < len(labels):
                lines.append(fr"\newcommand{{\statisAlphaTahun{labels[i]}}}{{{val:.4f}}} % {yr}")
        
        # Inertia (Dim 1)
        eig_vals = np.array(res.get('eig_vals_c', [0]))
        if len(eig_vals) > 0:
            val = eig_vals[0]
            pct = 100 * val / np.sum(eig_vals)
            lines.append(fr"\newcommand{{\statisEigenA}}{{{val:.4f}}}")
            lines.append(fr"\newcommand{{\statisInertiaA}}{{{pct:.2f}}}")
            
        # Simpan di parent directory agar sejajar dengan file LaTeX utama
        with open("../output_core_statis.tex", "w") as f:
            f.write("\n".join(lines))
        print("LaTeX Core Exported to ../output_core_statis.tex!")
    except Exception as e:
        print(f"Failed to export LaTeX Core: {e}")

def export_tables_latex(res):
    """
    Exports STATIS tables to SEPARATE LaTeX files for contextual embedding.
    """
    try:
        # Helper to write individual table file
        def write_single_table(data_list, filename, caption, label, columns=None, float_fmt="{:.4f}", longtable=False):
            if not data_list: return
            
            # Sanitizer for LaTeX
            def escape_tex(val):
                if isinstance(val, (int, float)): return val
                s = str(val)
                chars = {'_': r'\_', '%': r'\%', '$': r'\$', '#': r'\#', '&': r'\&'}
                for c, r in chars.items():
                    s = s.replace(c, r)
                return s

            df = pd.DataFrame(data_list)
            if columns: df = df[columns]
            
            lines = []
            if longtable:
                # LONGTABLE logic
                lines.append(r"\begin{longtable}{|" + "c|"*len(df.columns) + "}")
                lines.append(r"\caption{" + caption + "} \label{tab:" + label + "} \\\\")
                lines.append(r"\hline")
                # Escape headers
                header = " & ".join([f"\\textbf{{{escape_tex(c)}}}" for c in df.columns]) + " \\\\"
                lines.append(header)
                lines.append(r"\hline")
                lines.append(r"\endfirsthead")
                lines.append(r"\hline")
                lines.append(header)
                lines.append(r"\hline")
                lines.append(r"\endhead")
                lines.append(r"\hline")
                lines.append(r"\endfoot")
                
                for _, row in df.iterrows():
                    # Escape row values
                    row_str = " & ".join([float_fmt.format(val) if isinstance(val, (int, float)) else escape_tex(val) for val in row])
                    lines.append(row_str + " \\\\")
                
                lines.append(r"\hline")
                lines.append(r"\end{longtable}")
            else:
                # STANDARD TABLE logic
                lines.append(r"\begin{table}[H]")
                lines.append(r"\centering")
                lines.append(r"\caption{" + caption + "} \label{tab:" + label + "}")
                lines.append(r"\begin{tabular}{|" + "c|"*len(df.columns) + "}")
                lines.append(r"\hline")
                # Escape headers
                header = " & ".join([f"\\textbf{{{escape_tex(c)}}}" for c in df.columns]) + " \\\\"
                lines.append(header)
                lines.append(r"\hline")
                
                for _, row in df.iterrows():
                    # Escape row values
                    row_str = " & ".join([float_fmt.format(val) if isinstance(val, (int, float)) else escape_tex(val) for val in row])
                    lines.append(row_str + " \\\\")
                
                lines.append(r"\hline")
                lines.append(r"\end{tabular}")
                lines.append(r"\end{table}")

            # Write to specific file
            with open(f"../output_table_{filename}.tex", "w") as f:
                f.write("\n".join(lines))
            print(f"Exported ../output_table_{filename}.tex")

        # 1. Bobot Alpha
        write_single_table(res.get('Bobot (Alpha)'), "alpha", "Nilai Bobot (Alpha)", "alpha")
        
        # 2. Nilai Eigen
        write_single_table(res.get('Nilai Eigen (Lambda)'), "eigen", "Dekomposisi Nilai Eigen", "eigen")
        
        # 3. Matriks R
        write_single_table(res.get('Matriks Inter-struktur (R)'), "rv", "Koefisien RV Antar-tahun", "rv")
        
        # 4. Loadings
        write_single_table(res.get('Loadings Kompromi (Gc)'), "loadings", "Loadings Kompromi", "loadings")
        
        # 5. Skor (Longtable)
        write_single_table(res.get('Skor Kompromi (Fc)'), "scores", "Koordinat Skor Kompromi", "scores", longtable=True)
        
    except Exception as e:
        print(f"Failed to export Split Tables: {e}")

def export_perm_latex(p_val, desc):
    try:
        lines = []
        lines.append(r"% Generated by final.py (Permutation)")
        lines.append(fr"\newcommand{{\statisPValue}}{{{p_val:.4f}}}")
        lines.append(fr"\newcommand{{\statisKet}}{{{desc}}}")
        
        with open("../output_perm_statis.tex", "w") as f:
            f.write("\n".join(lines))
        print("LaTeX Perm Exported to ../output_perm_statis.tex!")
    except Exception as e:
        print(f"Failed to export LaTeX Perm: {e}")

# -----------------------------
# STATIS Core Logic (Perhitungan Berat)

# -----------------------------
def run_statis_core(uploaded_content_string, selected_vars, sheet_names):
    """
    Menjalankan perhitungan STATIS Lengkap (Matriks, Skor, Loading).
    Mengembalikan data siap plot dan siap tabel.
    """
    if uploaded_content_string is None: raise Exception("File belum di-upload.")
    
    # 1. Load Data
    try:
        _, content_string = uploaded_content_string.split(',')
        decoded = base64.b64decode(content_string)
        excel_file_stream = io.BytesIO(decoded)
    except Exception as e: raise Exception(f"Error decoding file: {e}")
    
    tables = []
    for s in sheet_names: 
        excel_file_stream.seek(0) 
        df_s = pd.read_excel(excel_file_stream, sheet_name=s).set_index("Kabupaten/Kota")
        vars_in_sheet = [v for v in selected_vars if v in df_s.columns]
        if vars_in_sheet: tables.append(df_s[vars_in_sheet].copy())

    if not tables: raise Exception("Data tidak valid atau variabel tidak ditemukan.")
    
    # 2. Align Indices
    if not all(tables[0].index.equals(t.index) for t in tables):
        common = tables[0].index
        for t in tables: common = common.intersection(t.index)
        tables = [t.loc[common].copy() for t in tables]

    obs_labels = tables[0].index.tolist()
    selected_vars_final = tables[0].columns.tolist() 
    k = len(tables)

    # 3. Standardisasi & Intra-struktur (W)
    scaler_statis = StandardScaler()
    tables_std, X_matrices, Ws = [], [], []
    
    for t in tables:
        arr = t.values.astype(float)
        arr_scaled = scaler_statis.fit_transform(arr) # Z-score
        tables_std.append(pd.DataFrame(arr_scaled, index=t.index, columns=t.columns))
        X_matrices.append(arr_scaled)
        Ws.append(arr_scaled @ arr_scaled.T) # W = Z * Z'

    # 4. Inter-struktur (R)
    R = _calculate_R_matrix(Ws, k)
    vals_R, vecs_R = np.linalg.eig(R)
    vals_R, vecs_R = np.real(vals_R), np.real(vecs_R)
    
    # Sort Eigen
    idx = np.argsort(vals_R)[::-1]
    vals_R_sorted, vecs_R_sorted = vals_R[idx], vecs_R[:, idx]
    
    # Bobot (Alpha)
    p1 = vecs_R_sorted[:,0]
    if p1.sum() < 0: p1 = -p1
    alphas = p1 / p1.sum()

    # 5. Kompromi (Wc)
    Wc = np.zeros_like(Ws[0])
    for a, W in zip(alphas, Ws): Wc += a * W

    # 6. Dekomposisi Wc (Mendapatkan Skor Fc)
    eig_vals_c, eig_vecs_c = np.linalg.eig(Wc)
    eig_vals_c, eig_vecs_c = np.real(eig_vals_c), np.real(eig_vecs_c)
    idxc = np.argsort(eig_vals_c)[::-1]
    eig_vals_c, eig_vecs_c = eig_vals_c[idxc], eig_vecs_c[:, idxc]
    
    # Skor Kompromi (Fc) - Raw (Sesuai Teori)
    # Ambil 2 komponen pertama untuk plot
    sq_2 = np.sqrt(np.clip(eig_vals_c[:2], a_min=0, a_max=None))
    scores_raw = eig_vecs_c[:, :2] * sq_2
    
    # Ambil full components untuk tabel
    sq_full = np.sqrt(np.clip(eig_vals_c, a_min=0, a_max=None))

    # 7. Loadings (Gc) - Korelasi Var vs Skor
    loadings = []
    for i, var in enumerate(selected_vars_final):
        arrs = [t[var].values for t in tables_std]
        # Rata-rata variabel antar tahun (untuk korelasi dengan Kompromi)
        x = np.mean(np.stack(arrs, axis=1), axis=1)
        if np.allclose(x, 0): cx, cy = 0.0, 0.0
        else:
            cx = np.corrcoef(x, scores_raw[:,0])[0,1] if np.std(x)!=0 and np.std(scores_raw[:,0])!=0 else 0
            cy = np.corrcoef(x, scores_raw[:,1])[0,1] if np.std(x)!=0 and np.std(scores_raw[:,1])!=0 else 0
            cx = 0.0 if np.isnan(cx) else cx
            cy = 0.0 if np.isnan(cy) else cy
        loadings.append([cx, cy])
    loadings = np.array(loadings)

    # 8. Trajectories Coordinates (Projected)
    per_year_coords = {}
    for year, dfstd in zip(sheet_names, tables_std):
        # Proyeksi Data Tahun t ke Loadings Kompromi
        per_year_coords[year] = dfstd.values @ loadings

    # --- PERSIAPAN DATAFRAME UNTUK TABEL DETAIL ---
    
    # A. Bobot
    df_alphas = pd.DataFrame({'Tahun': sheet_names, 'Bobot (Alpha)': [round(a, 4) for a in alphas]})
    
    # B. Eigenvalues
    var_expl = eig_vals_c / eig_vals_c.sum() * 100
    df_eigen = pd.DataFrame({
        'Dim': [f'Dim {i+1}' for i in range(len(eig_vals_c))],
        'Eigen': [round(v, 4) for v in eig_vals_c],
        'Akar Ciri': [round(v, 4) for v in sq_full],
        'Var (%)': [round(v, 2) for v in var_expl],
        'Kum (%)': [round(v, 2) for v in np.cumsum(var_expl)]
    })
    
    # C. Vektor Eigen (Vc)
    df_Vc = pd.DataFrame(eig_vecs_c, index=obs_labels, columns=[f"Vec {i+1}" for i in range(len(obs_labels))])
    df_Vc.index.name = 'Kab/Kota'; df_Vc = df_Vc.reset_index()
    
    # D. Skor (Fc)
    df_Fc = pd.DataFrame(scores_raw, index=obs_labels, columns=['PC1', 'PC2'])
    df_Fc.index.name = 'Kab/Kota'; df_Fc = df_Fc.reset_index()
    
    # E. Loadings (Gc)
    df_Gc = pd.DataFrame(loadings, index=selected_vars_final, columns=['PC1', 'PC2'])
    df_Gc.index.name = 'Variabel'; df_Gc = df_Gc.reset_index()
    
    # F. Matriks R
    df_R = pd.DataFrame(R, index=sheet_names, columns=sheet_names)
    df_R.index.name = 'Tahun'; df_R = df_R.reset_index()
    
    # G. Matriks Wc
    df_Wc = pd.DataFrame(Wc, index=obs_labels, columns=obs_labels)
    df_Wc.index.name = 'Kab/Kota'; df_Wc = df_Wc.reset_index()
    
    # H. Dataset Gabungan
    df_dataset = pd.concat([t.add_suffix(f" ({n})") for t, n in zip(tables, sheet_names)], axis=1)
    df_dataset.index.name = 'Kab/Kota'; df_dataset = df_dataset.reset_index()
    
    # I. Intra-Matrices Dictionary
    intra_dicts = {}
    for i, yr in enumerate(sheet_names):
        df_wt = pd.DataFrame(Ws[i], index=obs_labels, columns=obs_labels)
        df_wt.index.name = 'Kab/Kota'; df_wt = df_wt.reset_index()
        intra_dicts[f"Matriks Intra ({yr})"] = df_wt.to_dict('records')

    # Return Result Dictionary
    res = {
        # Core Data
        'R': R, 'alphas': alphas, 'eig_vals_c': eig_vals_c, 'scores': scores_raw,
        'obs_labels': obs_labels, 'selected_vars': selected_vars_final, 'loadings': loadings,
        'per_year_coords': per_year_coords, 'sheet_names': sheet_names,
        'X_matrices': X_matrices, 'vals_R_sorted': vals_R_sorted, 'k': k, # For Permutation
        
        # Table Data Records
        'Dataset Asli (X)': df_dataset.to_dict('records'),
        'Bobot (Alpha)': df_alphas.to_dict('records'),
        'Nilai Eigen (Lambda)': df_eigen.to_dict('records'),
        'Vektor Eigen (Vc)': df_Vc.to_dict('records'),
        'Skor Kompromi (Fc)': df_Fc.to_dict('records'),
        'Loadings Kompromi (Gc)': df_Gc.to_dict('records'),
        'Matriks Inter-struktur (R)': df_R.to_dict('records'),
        'Matriks Kompromi (Wc)': df_Wc.to_dict('records')
    }
    res.update(intra_dicts)
    return res

def run_permutation_test(X_matrices, k, lambda_obs, n_permutations):
    dist_lambdas = []
    for _ in range(n_permutations):
        Ws_perm = []
        for X in X_matrices:
            X_perm = np.random.permutation(X) # Shuffle baris
            Ws_perm.append(X_perm @ X_perm.T)
        R_perm = _calculate_R_matrix(Ws_perm, k)
        dist_lambdas.append(_get_first_eigenvalue(R_perm))
    
    dist_lambdas = np.array(dist_lambdas)
    # P-value (with +1 correction)
    p_value = (np.sum(dist_lambdas >= lambda_obs) + 1) / (n_permutations + 1)
    return dist_lambdas, p_value

# -----------------------------
# PLOT HELPERS (With Visual Scaling)
# -----------------------------
def apply_visual_adjustments(scores, loadings, norm_scores, scale_loadings):
    """
    Melakukan scaling HANYA untuk plotting, tidak mengubah data tabel.
    """
    plot_scores = scores.copy()
    plot_loadings = loadings.copy()
    
    # 1. Normalize Scores (Optional)
    if norm_scores:
        max_val = np.max(np.abs(plot_scores))
        if max_val > 0: plot_scores = plot_scores / max_val
            
    # 2. Scale Loadings (Visual scaling to match score magnitude)
    if scale_loadings:
        max_score_mag = np.max(np.abs(plot_scores))
        max_load_mag = np.max(np.abs(plot_loadings))
        if max_load_mag > 0:
            scale_factor = (max_score_mag / max_load_mag) * 0.8 
            plot_loadings = plot_loadings * scale_factor
            
    return plot_scores, plot_loadings

def create_biplot(scores, loadings, labels, vars, title, color=COLOR_ACCENT, show_loadings=True):
    fig = go.Figure()
    
    # Points
    fig.add_trace(go.Scatter(x=scores[:,0], y=scores[:,1], mode='markers+text',
                             text=labels, textposition='top center',
                             marker=dict(size=8, color=color, opacity=0.8), name='Objek'))
    
    # Vectors
    if show_loadings and len(vars) > 0:
        for i, var in enumerate(vars):
            fig.add_trace(go.Scatter(x=[0, loadings[i,0]], y=[0, loadings[i,1]], 
                                     mode='lines+markers+text', marker=dict(size=6, symbol='arrow-bar-up'),
                                     line=dict(color='#D81B60', width=2), text=[None, var],
                                     textposition='top center', name=f'{var}', 
                                     hoverinfo='text', hovertext=f"<b>{var}</b><br>Loading: ({loadings[i, 0]:.4f}, {loadings[i, 1]:.4f})"))

    fig.update_layout(title=title, xaxis=dict(constrain='domain'), yaxis=dict(scaleanchor='x', scaleratio=1),
                      width=600, height=600, autosize=False, margin=dict(l=40, r=40, t=60, b=40), showlegend=False,
                      template="plotly_white")
    return fig

# -----------------------------
# APP LAYOUT
# -----------------------------
app = Dash(__name__, external_stylesheets=EXTERNAL_STYLESHEETS)
server = app.server

app.layout = html.Div(style={'backgroundColor': COLOR_BG_MAIN, 'padding': '30px', 'fontFamily': 'Segoe UI, Roboto, Helvetica, Arial, sans-serif'}, children=[
    dcc.Store(id='global-data-store'), 
    dcc.Store(id='pca-results-store'),
    dcc.Store(id='statis-core-store'), # Menyimpan hasil STATIS lengkap
    
    # --- HEADER ---
    html.Div(style=CARD_STYLE, children=[
        html.H1('Dashboard Analisis Spasio-Temporal Sosio-Ekonomi', style=HEADER_STYLE),
        html.H2('(Metode STATIS & Dynamic Biplot)', style={'textAlign': 'center', 'color': '#546E7A', 'marginTop': '-10px'}),
        html.H3("Studi Kasus: Provinsi Banten, DKI Jakarta, dan Jawa Barat (2020-2024)", style={'textAlign': 'center', 'color': '#78909C', 'fontStyle': 'italic'})
    ]),
    
    # --- 1. DATA INPUT ---
    html.Div(style=CARD_STYLE, children=[
        html.H5("1. Input Data", style=LABEL_STYLE),
        
        # --- [TAMBAHAN] INFO FORMAT EXCEL ---
        html.Div(style={'backgroundColor': '#E3F2FD', 'borderLeft': '5px solid #2196F3', 'padding': '15px', 'marginBottom': '20px', 'borderRadius': '4px'}, children=[
            html.H6("📝 Ketentuan Format File Excel:", style={'fontWeight': 'bold', 'marginTop': '0', 'color': '#0D47A1'}),
            html.Ul(style={'marginBottom': '0', 'fontSize': '14px', 'color': '#1565C0'}, children=[
                html.Li("File harus memiliki kolom wajib: 'Kabupaten/Kota' dan 'Provinsi'."),
                html.Li("Setiap Sheet merepresentasikan Satu Tahun dan harus dinamai dengan angka tahun (contoh: 2020, 2021)."),
                html.Li("Pastikan tidak ada sel yang di-merge pada header.")
            ])
        ]),
        # ------------------------------------

        html.Div([
            html.Span("Download Contoh Dataset: ", style={'marginRight':'10px', 'color': '#455A64'}),
            *[html.A(d['name'], href=d['url'], target="_blank", download=d['name'], style={'marginRight':'15px', 'fontWeight':'bold', 'textDecoration':'none', 'color': COLOR_ACCENT}) for d in EXAMPLE_DATASETS]
        ], style={'marginBottom':'15px', 'textAlign':'center', 'fontSize':'14px'}),
        
        dcc.Upload(
            id='upload-data',
            children=html.Div(['📂 Drag & Drop atau ', html.A('Pilih File Excel', style={'fontWeight':'bold', 'color': COLOR_ACCENT, 'textDecoration': 'underline'})]),
            style={'width': '100%', 'height': '80px', 'lineHeight': '80px', 'borderWidth': '2px', 'borderStyle': 'dashed', 'borderRadius': '12px', 'textAlign': 'center', 'borderColor': COLOR_ACCENT, 'backgroundColor': '#FAFAFA', 'cursor': 'pointer', 'transition': '0.3s'},
            multiple=False
        ),
        
        # Tempat Alert Muncul
        html.Div(id='output-data-upload', style={'marginTop': '20px'})
    ]),

    # --- 2. CONTROLS ---
    html.Div(style=CARD_STYLE, children=[
        html.H4("Panel Kontrol Analisis", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
        html.Div(className='row', children=[
            html.Div(className='three columns', children=[
                html.Label('Pilih Variabel Analisis:', style={'fontWeight':'bold'}),
                dcc.Dropdown(id='variable-dropdown-final', multi=True, placeholder="Pilih variabel...", style={'fontSize': '14px'})
            ]),
            html.Div(className='three columns', children=[
                html.Label('Rotasi Baseline (Semua Plot):', style={'fontWeight':'bold'}),
                dcc.RadioItems(id='baseline-type-final', options=[{'label':'Variabel','value':'loading'},{'label':'Kab/Kota','value':'skor'}], value='loading', labelStyle={'display':'inline-block','marginRight':'10px'}),
                dcc.Dropdown(id='baseline-name-final', placeholder="Pilih referensi...", style={'fontSize': '14px'})
            ]),
            html.Div(className='three columns', children=[
                html.Label('Filter Tahun:', style={'fontWeight':'bold'}),
                dcc.Checklist(id='year-checklist-final', inline=True, style={'marginBottom':'5px'}),
                html.Label('Mirroring (Flip PC2):', style={'fontSize':'12px', 'color':'#666'}),
                dcc.Checklist(id='mirror-year-checklist-final', inline=True)
            ]),
            html.Div(className='three columns', children=[
                html.Label('Highlight Trajektori:', style={'fontWeight':'bold'}),
                dcc.Dropdown(id='trajectory-dropdown-final', multi=True, placeholder="Pilih objek...", style={'fontSize': '14px'})
            ])
        ]),
        html.Hr(style={'borderColor': '#ECEFF1'}),
        
        # Fitur Tambahan (7 & 8)
        html.Div(className='row', children=[
            html.Div(className='six columns', children=[
                html.Label('Opsi Tampilan Vektor:', style={'fontWeight':'bold'}),
                dcc.RadioItems(
                    id='loading-vector-scope-final',
                    options=[{'label':'Hidden','value':'none'}, {'label':'2D Only','value':'2d'}, {'label':'3D Only','value':'3d'}, {'label':'All Plots','value':'both'}],
                    value='both',
                    labelStyle={'display':'inline-block', 'marginRight':'15px'}
                ),
            ]),
            html.Div(className='six columns', children=[
                html.Label('Pengaturan Skala Visual:', style={'fontWeight':'bold'}),
                dcc.Checklist(
                    id='visual-scaling-opts',
                    options=[
                        {'label': 'Normalisasi Skor (-1 s.d 1)', 'value': 'norm_score'},
                        {'label': 'Skala Visual Loadings (Agar sebanding)', 'value': 'scale_load'}
                    ],
                    value=['scale_load'], # Default scale loadings ON
                    inline=True,
                    inputStyle={"marginRight": "5px"}
                )
            ])
        ]),
        html.Div(className='row', style={'marginTop': '15px'}, children=[
             html.Div(className='twelve columns', children=[
                html.Label('Filter Vektor Spesifik (Visualisasi):', style={'fontWeight':'bold'}),
                dcc.Dropdown(id='vector-selector-final', multi=True, placeholder="Pilih vektor spesifik untuk ditampilkan (Kosong = Semua)...")
            ])
        ])
    ]),

    # --- 3. DYNAMIC BIPLOT ---
    html.Div(style=CARD_STYLE, children=[
        html.H5("Visualisasi Dynamic Biplot (Spasio-Temporal)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
        dcc.Loading(type='cube', color=COLOR_ACCENT, children=[
            dcc.Graph(id='graph-3d-main', style={'height': '700px'})
        ]),
        html.Hr(),
        html.Div(className='row', children=[
            html.Div(className='six columns', children=[
                html.H5("Snapshot 2D per Tahun", style={'textAlign': 'center', 'color': '#455A64'}),
                dcc.Dropdown(id='year-dropdown-2d-single', style={'width':'60%', 'margin':'0 auto', 'marginBottom':'10px'}),
                dcc.Loading(children=[dcc.Graph(id='graph-2d-year', style={'height': '600px'})])
            ]),
            html.Div(className='six columns', children=[
                html.H5("Proyeksi Trajektori 2D", style={'textAlign': 'center', 'color': '#455A64'}),
                html.P("Lintasan pergerakan objek dari tahun ke tahun", style={'textAlign':'center', 'color':'#90A4AE', 'fontSize':'12px'}),
                dcc.Loading(children=[dcc.Graph(id='graph-2d-traj', style={'height': '600px'})])
            ])
        ]),
        html.Hr(),
        html.H6("Data Trajektori Terpilih (Tabel)", style={'textAlign':'center', 'fontWeight':'bold', 'color': COLOR_ACCENT}),
        dcc.Loading(children=[
            dash_table.DataTable(
                id='trajectory-table',
                export_format='xlsx',
                style_table={'overflowX': 'auto'},
                style_header={'backgroundColor': '#37474F', 'color': 'white', 'fontWeight': 'bold'},
                style_cell={'textAlign': 'center', 'padding': '8px', 'fontFamily': 'sans-serif'},
                page_size=10
            )
        ])
    ]),

    # --- 4. STATIS ANALYSIS ---
    html.Div(style=CARD_STYLE, children=[
        html.H5("Analisis STATIS (Struktur Kompromi)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
        
        # 4 Plot Grid
        html.Div(className='row', style={'marginBottom':'120px'}, children=[
            html.Div(className='six columns', children=[
                dcc.Loading(children=[dcc.Graph(id='statis-compromise', style={'height': '500px'})])
            ]),
            html.Div(className='six columns', children=[
                dcc.Loading(children=[dcc.Graph(id='statis-biplot', style={'height': '500px'})])
            ])
        ]),
        html.Div(className='row', style={'marginTop':'30px'}, children=[
            html.Div(className='six columns', children=[
                dcc.Loading(children=[dcc.Graph(id='statis-interstructure', style={'height': '500px'})])
            ]),
            html.Div(className='six columns', children=[
                dcc.Loading(children=[dcc.Graph(id='statis-trajectory', style={'height': '500px'})])
            ])
        ]),
        
        html.Hr(style={'borderColor': '#B0BEC5', 'marginTop': '30px'}),
        
        # Permutation Test
        html.Div(style={'padding': '20px', 'borderRadius': '10px', 'border': '0px solid #FFF59D'}, children=[
            html.H5("Uji Signifikansi Stabilitas (Permutasi)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
            html.Div(className='row', style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'marginBottom': '10px'}, children=[
                html.Label("Jumlah Permutasi (N): ", style={'marginRight': '10px', 'fontWeight': 'bold'}),
                dcc.Input(id='perm-n-input', type='number', value=1000, min=100, step=100, style={'width': '100px', 'marginRight': '20px'}),
                html.Button("RUN PERMUTATION TEST", id='btn-run-perm', n_clicks=0, style={'backgroundColor': COLOR_ACCENT, 'color': 'white', 'fontWeight': 'bold', 'borderRadius': '5px'})
            ]),
            dcc.Loading(children=[
                dcc.Graph(id='perm-graph', style={'height': '350px'}),
                html.Div(id='perm-result-text', style={'textAlign': 'center', 'fontSize': '16px', 'marginTop': '10px', 'fontWeight': 'bold', 'color': '#333'})
            ])
        ]),

        html.Hr(style={'borderColor': '#B0BEC5', 'marginTop': '40px'}),
        
        # Detail Tables
        html.H5("Detail Hasil Analisis (Tabel & Matriks)", style={'textAlign': 'center', 'fontWeight':'bold', 'color': COLOR_ACCENT}),
        html.Div(className='row', style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'marginBottom': '20px'}, children=[
            html.Label("Pilih Tabel:", style={'marginRight': '10px', 'fontWeight': 'bold'}),
            dcc.Dropdown(id='statis-table-selector', placeholder="Pilih Tabel...", clearable=False, style={'width': '300px', 'marginRight': '20px'}),
            html.Label("Baris per Halaman:", style={'marginRight': '10px', 'fontWeight': 'bold'}),
            dcc.Input(id='table-page-size', type='number', value=10, min=5, max=100, step=5, style={'width': '80px'})
        ]),
        
        html.Div(id='table-info-display', style={'textAlign': 'center', 'marginBottom': '10px', 'fontStyle': 'italic', 'color': '#607D8B'}),
        
        dcc.Loading(children=[
            dash_table.DataTable(
                id='statis-detail-table',
                export_format='xlsx',
                style_table={'overflowX': 'auto'},
                style_header={'backgroundColor': '#455A64', 'color': 'white', 'fontWeight': 'bold'},
                style_cell={'textAlign': 'center', 'padding': '8px', 'minWidth': '100px'},
                style_data_conditional=[
                    {'if': {'row_index': 'odd'}, 'backgroundColor': '#F5F5F5'}
                ],
                page_action='native', # Enable pagination
                page_current=0,
                page_size=10
            )
        ]),
        html.Hr(style={'borderColor': '#B0BEC5', 'marginTop': '40px'}),
        # --- [TAMBAHAN BARU] SECTION 5: EVALUASI JUMLAH CLUSTER (ELBOW & DENDROGRAM) ---
        html.Div(style=CARD_STYLE, children=[
            html.H5("Tahap Pembantu: Evaluasi Jumlah Cluster (Visual Aids)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
            html.P("Gunakan kurva Elbow dan Dendrogram di bawah ini untuk menentukan jumlah cluster (k) yang optimal pada suatu tahun.", style={'textAlign': 'center', 'color': '#546E7A'}),
            html.Div(className='row', style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'marginBottom': '20px'}, children=[
                html.Label("Evaluasi Tahun:", style={'marginRight': '10px', 'fontWeight': 'bold'}),
                dcc.Dropdown(id='eval-year-dropdown', clearable=False, style={'width': '150px'})
            ]),
            html.Div(className='row', children=[
                html.Div(className='six columns', children=[
                    html.H6("Metode Elbow (Inersia K-Means)", style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='elbow-graph', style={'height': '400px'})])
                ]),
                html.Div(className='six columns', children=[
                    html.H6("Dendrogram (Agglomerative Hierarchical)", style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='dendrogram-graph', style={'height': '400px'})])
                ])
            ])
        ]),

        # --- [TAMBAHAN BARU] SECTION 6: CLUSTERING TAHUNAN & MATRIKS TRANSISI ---
        html.Div(style=CARD_STYLE, children=[
            html.H5("Analisis Klaster Spasio-Temporal (Tahunan & Migrasi)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
            html.Div(className='row', style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'marginBottom': '20px'}, children=[
                html.Label("Pasangan Tahun Transisi:", style={'marginRight': '10px', 'fontWeight': 'bold'}),
                dcc.Dropdown(id='trans-year-dropdown', clearable=False, style={'width': '200px', 'marginRight': '20px'}),
                html.Label("Jumlah Cluster (k):", style={'marginRight': '10px', 'fontWeight': 'bold'}),
                dcc.Input(id='trans-k-input', type='number', value=3, min=2, max=10, step=1, style={'width': '60px', 'marginRight': '20px'}),
                html.Button("RUN CLUSTERING TAHUNAN", id='btn-run-trans', n_clicks=0, 
                            style={'backgroundColor': COLOR_ACCENT, 'color': 'white', 'fontWeight': 'bold', 'border': 'none', 'borderRadius': '5px'})
            ]),
            html.Div(className='row', children=[
                html.Div(className='six columns', children=[
                    html.H6(id='title-trans-map-t1', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='trans-map-t1', style={'height': '500px'})])
                ]),
                html.Div(className='six columns', children=[
                    html.H6(id='title-trans-map-t2', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='trans-map-t2', style={'height': '500px'})])
                ])
            ]),
            html.Div(className='row', children=[
                html.Div(className='six columns', children=[
                    html.H6(id='title-trans-scatter-t1', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='trans-scatter-t1', style={'height': '500px'})])
                ]),
                html.Div(className='six columns', children=[
                    html.H6(id='title-trans-scatter-t2', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='trans-scatter-t2', style={'height': '500px'})])
                ])
            ]),
            html.Hr(),
            html.H6("Matriks Transisi (Perpindahan Kabupaten/Kota)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
            html.Div(style={'display': 'flex', 'justifyContent': 'center', 'marginBottom': '10px'}, children=[
                dcc.RadioItems(id='trans-view-mode', options=[{'label': ' Tampilkan Jumlah', 'value': 'count'}, {'label': ' Tampilkan Nama Daerah', 'value': 'names'}], value='count', inline=True, inputStyle={"marginRight": "5px", "marginLeft": "15px"})
            ]),
            dcc.Loading(children=[
                dash_table.DataTable(id='trans-matrix-table', style_table={'overflowX': 'auto'}, style_header={'backgroundColor': '#37474F', 'color': 'white', 'fontWeight': 'bold'}, style_cell={'textAlign': 'center', 'padding': '8px', 'fontFamily': 'sans-serif'})
            ])
        ]),

        # --- SECTION 7: CLUSTERING TRAJEKTORI KESELURUHAN ---
        html.Div(style=CARD_STYLE, children=[
            html.H5("Analisis Lanjutan: Clustering Trajektori Keseluruhan (STATIS)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
            html.P("Mengelompokkan Kabupaten/Kota berdasarkan kemiripan pola pergerakan (nasib) selama periode penuh.", 
                   style={'textAlign': 'center', 'color': '#546E7A', 'marginBottom': '20px'}),
            
            html.Div(className='row', style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'marginBottom': '20px'}, children=[
                html.Label("Jumlah Cluster (k):", style={'marginRight': '10px', 'fontWeight': 'bold'}),
                dcc.Input(id='cluster-k-input', type='number', value=3, min=2, max=10, step=1, style={'width': '60px', 'marginRight': '20px'}),
                html.Button("RUN CLUSTERING TRAJEKTORI", id='btn-run-cluster', n_clicks=0, 
                            style={'backgroundColor': COLOR_ACCENT, 'color': 'white', 'fontWeight': 'bold', 'border': 'none', 'borderRadius': '5px'})
            ]),

            html.Div(className='row', children=[
                # Kiri: Scatter Plot
                html.Div(className='six columns', children=[
                    html.H5("Peta Sebaran (Scatter Plot)", style={'textAlign': 'center', 'fontSize': '14px', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='cluster-scatter', style={'height': '800px'})])
                ]),
                # Kanan: Dendrogram
                html.Div(className='six columns', children=[
                    html.H5("Dendrogram Kemiripan", style={'textAlign': 'center', 'fontSize': '14px', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='cluster-dendrogram', style={'height': '800px'})])
                ])
            ]),

            # --- [TAMBAHAN BARU: PETA SPASIAL] ---
            html.Hr(style={'borderColor': '#E0E0E0', 'marginTop': '20px', 'marginBottom': '20px'}),
            html.H5("Distribusi Geografis Cluster (Peta Wilayah)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
            dcc.Loading(type='cube', color=COLOR_ACCENT, children=[
                dcc.Graph(id='cluster-map', style={'height': '500px'})
            ]),
            # -------------------------------------

            html.Div(id='cluster-interpretation', style={'marginTop': '15px', 'padding': '15px', 'backgroundColor': '#E3F2FD', 'borderRadius': '5px', 'borderLeft': '5px solid #1565C0', 'fontStyle': 'italic', 'color': '#0D47A1'})
        ]),

        # --- [TAMBAHAN BARU] SECTION 8: BASELINE MATRIKS TRANSISI (IPM/UNDP) ---
        html.Div(style=CARD_STYLE, children=[
            html.H5("Disclaimer & Baseline: Matriks Transisi Berdasarkan Kategori IPM (UNDP)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': '#E64A19'}),
            html.P("Sebelum menentukan jumlah klaster k-means, Anda dapat melihat kondisi riil perpindahan wilayah berdasarkan 4 kategori Indeks Pembangunan Manusia (UNDP): Sangat Tinggi (≥80), Tinggi (70-79.99), Sedang (55-69.99), dan Rendah (<55).", 
                   style={'textAlign': 'center', 'color': '#546E7A', 'marginBottom': '20px'}),
            
            html.Div(className='row', style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'marginBottom': '20px'}, children=[
                html.Label("Pasangan Tahun Transisi IPM:", style={'marginRight': '10px', 'fontWeight': 'bold'}),
                dcc.Dropdown(id='ipm-trans-year-dropdown', clearable=False, style={'width': '200px', 'marginRight': '20px'}),
                html.Button("TAMPILKAN BASELINE IPM", id='btn-run-ipm-trans', n_clicks=0, 
                            style={'backgroundColor': '#E64A19', 'color': 'white', 'fontWeight': 'bold', 'border': 'none', 'borderRadius': '5px'})
            ]),
            
            html.Div(id='ipm-disclaimer-text', style={'textAlign': 'center', 'marginBottom': '20px', 'fontStyle': 'italic', 'fontWeight': 'bold'}),
            
            html.Div(style={'display': 'flex', 'justifyContent': 'center', 'marginBottom': '10px'}, children=[
                dcc.RadioItems(id='ipm-trans-view-mode', options=[
                    {'label': ' Tampilkan Jumlah', 'value': 'count'}, 
                    {'label': ' Tampilkan Nama Daerah', 'value': 'names'}
                ], value='count', inline=True, inputStyle={"marginRight": "5px", "marginLeft": "15px"})
            ]),
            
            dcc.Loading(children=[
                dash_table.DataTable(id='ipm-trans-matrix-table', style_table={'overflowX': 'auto'}, 
                                     style_header={'backgroundColor': '#37474F', 'color': 'white', 'fontWeight': 'bold'}, 
                                     style_cell={'textAlign': 'center', 'padding': '8px', 'fontFamily': 'sans-serif'})
            ])
        ]),

        # --- [TAMBAHAN BARU] SECTION 9: PERBANDINGAN CLUSTER VS IPM (CROSS-TABULATION) ---
        html.Div(style=CARD_STYLE, children=[
            html.H5("Perbandingan Anggota Cluster K-Means vs Kategori IPM (UNDP)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': '#00695C'}),
            html.P("Bagian ini menampilkan tabel tabulasi silang (cross-tabulation) antara cluster yang dibentuk oleh algoritma K-Means dengan pengelompokan baku dari UNDP berdasarkan skor IPM. Ini berguna untuk mengevaluasi apakah cluster data-driven sejalan dengan standar institusi global.", 
                   style={'textAlign': 'center', 'color': '#546E7A', 'marginBottom': '20px'}),
            
            html.Div(className='row', style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'marginBottom': '20px'}, children=[
                html.Label("Tahun:", style={'marginRight': '10px', 'fontWeight': 'bold'}),
                dcc.Dropdown(id='cross-year-dropdown', clearable=False, style={'width': '120px', 'marginRight': '20px'}),
                html.Label("Jumlah Cluster K-Means (k):", style={'marginRight': '10px', 'fontWeight': 'bold'}),
                dcc.Input(id='cross-k-input', type='number', value=3, min=2, max=10, step=1, style={'width': '60px', 'marginRight': '20px'}),
                html.Button("TAMPILKAN PERBANDINGAN", id='btn-run-cross', n_clicks=0, 
                            style={'backgroundColor': '#00897B', 'color': 'white', 'fontWeight': 'bold', 'border': 'none', 'borderRadius': '5px'})
            ]),
            
            html.Div(style={'display': 'flex', 'justifyContent': 'center', 'marginBottom': '10px'}, children=[
                dcc.RadioItems(id='cross-view-mode', options=[
                    {'label': ' Tampilkan Jumlah', 'value': 'count'}, 
                    {'label': ' Tampilkan Nama Daerah', 'value': 'names'}
                ], value='count', inline=True, inputStyle={"marginRight": "5px", "marginLeft": "15px"})
            ]),
            
            dcc.Loading(children=[
                dash_table.DataTable(id='cross-table', style_table={'overflowX': 'auto'}, 
                                     style_header={'backgroundColor': '#37474F', 'color': 'white', 'fontWeight': 'bold'}, 
                                     style_cell={'textAlign': 'center', 'padding': '8px', 'fontFamily': 'sans-serif'})
            ])
        ])
    ])
])

# -----------------------------
# CALLBACKS
# -----------------------------

# 1. Upload & Validasi
@app.callback(
    Output('global-data-store', 'data'), 
    Output('output-data-upload', 'children'),
    Input('upload-data', 'contents'), 
    State('upload-data', 'filename')
)
def cb_upload(contents, filename):
    if not contents: 
        raise exceptions.PreventUpdate
        
    try:
        _, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        # Baca semua sheet
        all_sheets = pd.read_excel(io.BytesIO(decoded), sheet_name=None)
        
        all_data, sheet_names = [], []
        for name, df in all_sheets.items():
            # Validasi Nama Sheet (Harus Integer Tahun)
            try: 
                y = int(name)
                df['Tahun'] = y
                all_data.append(df)
                sheet_names.append(name)
            except: 
                pass # Skip sheet yang bukan tahun
        
        if not all_data: 
            return None, html.Div([
                html.Strong("Gagal!"), " Tidak ditemukan sheet dengan nama Tahun (angka) yang valid."
            ], style={'backgroundColor': '#FFEBEE', 'color': '#C62828', 'padding': '15px', 'borderRadius': '5px', 'border': '1px solid #EF9A9A', 'textAlign': 'center'})
        
        df_concat = pd.concat(all_data, ignore_index=True)
        
        # Validasi Kolom Wajib
        required_cols = ['Kabupaten/Kota', 'Provinsi']
        missing = [c for c in required_cols if c not in df_concat.columns]
        
        if missing:
            return None, html.Div([
                html.Strong("Format Salah!"), f" Kolom berikut tidak ditemukan: {', '.join(missing)}"
            ], style={'backgroundColor': '#FFEBEE', 'color': '#C62828', 'padding': '15px', 'borderRadius': '5px', 'border': '1px solid #EF9A9A', 'textAlign': 'center'})

        # Cleaning
        cols = df_concat.columns.drop(['Provinsi', 'Kabupaten/Kota', 'Tahun'])
        for c in cols:
            if df_concat[c].dtype == 'object': 
                df_concat[c] = pd.to_numeric(df_concat[c].astype(str).str.replace(',', '.').str.replace(' ', ''), errors='coerce')
        df_concat.dropna(inplace=True)
        
        # Store
        base_features = sorted(list(set(cols)))
        years = sorted(list(df_concat['Tahun'].unique()))
        kab_kota = df_concat['Kabupaten/Kota'].unique().tolist()
        
        store = {
            'df_json': df_concat.to_json(orient='split'), 
            'base_features': base_features, 
            'kab_kota': kab_kota, 
            'years': years, 
            'sheet_names': sheet_names
        }
        
        # Alert SUKSES (Hijau)
        success_msg = html.Div([
            html.Strong("Berhasil!"), f" File '{filename}' dimuat dengan {len(years)} tahun data."
        ], style={'backgroundColor': '#E8F5E9', 'color': '#2E7D32', 'padding': '15px', 'borderRadius': '5px', 'border': '1px solid #A5D6A7', 'textAlign': 'center'})
        
        return store, success_msg

    except Exception as e:
        # Alert ERROR (Merah)
        error_msg = html.Div([
            html.Strong("Error!"), f" Terjadi kesalahan saat memproses file: {str(e)}"
        ], style={'backgroundColor': '#FFEBEE', 'color': '#C62828', 'padding': '15px', 'borderRadius': '5px', 'border': '1px solid #EF9A9A', 'textAlign': 'center'})
        return None, error_msg
    
# 2. Controls & Dropdowns Sync
@app.callback(
    Output('variable-dropdown-final', 'options'), Output('variable-dropdown-final', 'value'),
    Output('trajectory-dropdown-final', 'options'), Output('year-checklist-final', 'options'), Output('year-checklist-final', 'value'),
    Output('mirror-year-checklist-final', 'options'), Output('year-dropdown-2d-single', 'options'), Output('year-dropdown-2d-single', 'value'),
    Output('baseline-name-final', 'options'), 
    Output('eval-year-dropdown', 'options'), Output('eval-year-dropdown', 'value'),
    Output('trans-year-dropdown', 'options'), Output('trans-year-dropdown', 'value'),
    Output('ipm-trans-year-dropdown', 'options'), Output('ipm-trans-year-dropdown', 'value'),
    Output('cross-year-dropdown', 'options'), Output('cross-year-dropdown', 'value'),
    Input('global-data-store', 'data'), Input('baseline-type-final', 'value')
)
def cb_controls(data, base_type):
    if not data: raise exceptions.PreventUpdate
    feats, kabs, years = data['base_features'], data['kab_kota'], data['years']
    traj_opts = ([{'label': f'{k} (Kab/Kota)', 'value': f'skor_{k}'} for k in kabs] + 
                 [{'label': f'{f} (Variabel)', 'value': f'loading_{f}'} for f in feats])
    y_opts = [{'label': str(y), 'value': y} for y in years]
    base_opts = [{'label': f, 'value': f} for f in (feats if base_type == 'loading' else kabs)]
    
    trans_y_opts = []
    for i in range(1, len(years)):
        trans_y_opts.append({'label': f"{years[i-1]} / {years[i]}", 'value': years[i]})
    
    return [{'label': f, 'value': f} for f in feats], feats, traj_opts, y_opts, years, y_opts, y_opts, years[0], base_opts, y_opts, years[-1], trans_y_opts, (trans_y_opts[-1]['value'] if trans_y_opts else None), trans_y_opts, (trans_y_opts[-1]['value'] if trans_y_opts else None), y_opts, years[-1]

# 2b. Sync Vector Selector with Selected Vars
@app.callback(
    Output('vector-selector-final', 'options'),
    Input('variable-dropdown-final', 'value')
)
def cb_sync_vector_selector(selected_vars):
    if not selected_vars: return []
    return [{'label': v, 'value': v} for v in selected_vars]

# 3. Dynamic PCA Calculation
@app.callback(
    Output('pca-results-store', 'data'), Input('variable-dropdown-final', 'value'), State('global-data-store', 'data')
)
def cb_pca_calc(vars, data):
    if not vars or not data: raise exceptions.PreventUpdate
    df = pd.read_json(io.StringIO(data['df_json']), orient='split')
    pc_list, load_list = [], []
    for y in data['years']:
        df_y = df[df['Tahun'] == y]
        if df_y.empty: continue
        X = df_y[vars]
        coords = pca.fit_transform(scaler.fit_transform(X))
        d_sc = df_y[['Kabupaten/Kota', 'Provinsi', 'Tahun']].copy()
        d_sc['PC1'], d_sc['PC2'] = coords[:,0], coords[:,1]
        pc_list.append(d_sc)
        d_load = pd.DataFrame(pca.components_.T, columns=['PC1', 'PC2'])
        d_load['features'], d_load['Tahun'] = vars, y
        load_list.append(d_load)
    return {'pc_scores': pd.concat(pc_list).to_json(orient='split'), 'loadings': pd.concat(load_list).to_json(orient='split')}

# 4. STATIS Core Calculation
@app.callback(
    Output('statis-core-store', 'data'), Input('variable-dropdown-final', 'value'),
    State('upload-data', 'contents'), State('global-data-store', 'data')
)
def cb_statis_calc(vars, contents, global_data):
    if not vars or not contents: raise exceptions.PreventUpdate
    try: return run_statis_core(contents, vars, global_data['sheet_names'])
    except: return None

# 5. DYNAMIC BIPLOT PLOTS
@app.callback(
    Output('graph-3d-main', 'figure'), Output('graph-2d-year', 'figure'), Output('graph-2d-traj', 'figure'),
    Output('trajectory-table', 'data'), Output('trajectory-table', 'columns'),
    Input('pca-results-store', 'data'), Input('year-checklist-final', 'value'), Input('mirror-year-checklist-final', 'value'),
    Input('baseline-type-final', 'value'), Input('baseline-name-final', 'value'), Input('trajectory-dropdown-final', 'value'),
    Input('year-dropdown-2d-single', 'value'), Input('loading-vector-scope-final', 'value'),
    Input('visual-scaling-opts', 'value'), Input('vector-selector-final', 'value')
)
def cb_update_plots(pca_data, years_filter, mirror_years, base_type, base_name, traj_sel, year_2d, load_scope, vis_opts, selected_vectors_to_show):
    if not pca_data or not years_filter: return {}, {}, {}, [], []
    
    norm_score = 'norm_score' in vis_opts if vis_opts else False
    scale_load = 'scale_load' in vis_opts if vis_opts else False
    
    df_pc = pd.read_json(io.StringIO(pca_data['pc_scores']), orient='split')
    df_load = pd.read_json(io.StringIO(pca_data['loadings']), orient='split')
    df_pc = df_pc[df_pc['Tahun'].isin(years_filter)]
    df_load = df_load[df_load['Tahun'].isin(years_filter)]
    
    if selected_vectors_to_show and len(selected_vectors_to_show) > 0:
         df_load = df_load[df_load['features'].isin(selected_vectors_to_show)]

    df_pc_fin, df_load_fin = df_pc.copy(), df_load.copy()
    for y in sorted(df_pc['Tahun'].unique()):
        angle = get_rotation_angle(df_pc, df_load, base_type, base_name, y) if base_name else 0
        mask_p, mask_l = df_pc_fin['Tahun'] == y, df_load_fin['Tahun'] == y
        if angle != 0:
            df_pc_fin.loc[mask_p, ['PC1', 'PC2']] = rotate_dataframe(df_pc.loc[mask_p], angle)
            df_load_fin.loc[mask_l, ['PC1', 'PC2']] = rotate_dataframe(df_load.loc[mask_l], angle)
        if mirror_years and y in mirror_years:
            df_pc_fin.loc[mask_p, 'PC2'] *= -1
            df_load_fin.loc[mask_l, 'PC2'] *= -1

    # Visual Scaling
    pc_plot, load_plot = apply_visual_adjustments(df_pc_fin[['PC1','PC2']].values, df_load_fin[['PC1','PC2']].values, norm_score, scale_load)
    df_pc_plt = df_pc_fin.copy(); df_pc_plt[['PC1','PC2']] = pc_plot
    df_load_plt = df_load_fin.copy(); df_load_plt[['PC1','PC2']] = load_plot

    # 3D
    fig_3d = px.scatter_3d(df_pc_plt, x='Tahun', y='PC1', z='PC2', color='Provinsi', hover_name='Kabupaten/Kota')
    fig_3d.update_traces(marker=dict(size=4))
    if load_scope in ['3d', 'both']:
        for y in sorted(df_pc['Tahun'].unique()):
            d_l = df_load_plt[df_load_plt['Tahun'] == y]
            d_l_raw = df_load_fin[df_load_fin['Tahun'] == y]
            for idx, row in d_l.iterrows():
                raw = d_l_raw.loc[idx]
                fig_3d.add_trace(go.Scatter3d(
                    x=[y, y], y=[0, row['PC1']], z=[0, row['PC2']],
                    mode='lines+text', line=dict(color='red', width=1), opacity=0.5,
                    text=[None, str(row['features'])], textposition='top center', showlegend=False,
                    hoverinfo='text', hovertext=f"Loading: {row['features']}<br>Raw: ({raw['PC1']:.2f}, {raw['PC2']:.2f})"
                ))
    if traj_sel:
        for sel in traj_sel:
            t_type, t_name = sel.split('_', 1)
            if t_type == 'skor':
                d_t = df_pc_plt[df_pc_plt['Kabupaten/Kota'] == t_name].sort_values('Tahun')
                fig_3d.add_trace(go.Scatter3d(x=d_t['Tahun'], y=d_t['PC1'], z=d_t['PC2'], mode='lines+markers', name=t_name))
            elif t_type == 'loading':
                d_t = df_load_plt[df_load_plt['features'] == t_name].sort_values('Tahun')
                if not d_t.empty: fig_3d.add_trace(go.Scatter3d(x=d_t['Tahun'], y=d_t['PC1'], z=d_t['PC2'], mode='lines+markers', name=t_name))
    fig_3d.update_layout(title='Visualisasi 3D (Rotated)', margin=dict(l=0, r=0, b=0, t=30), scene=dict(aspectmode='manual', aspectratio=dict(x=2, y=1, z=1)))

    # 2D
    fig_2d_y = go.Figure()
    if year_2d:
        d_p, d_l = df_pc_plt[df_pc_plt['Tahun']==year_2d], df_load_plt[df_load_plt['Tahun']==year_2d]
        d_l_raw = df_load_fin[df_load_fin['Tahun']==year_2d]
        fig_2d_y.add_trace(go.Scatter(x=d_p['PC1'], y=d_p['PC2'], mode='markers+text', text=d_p['Kabupaten/Kota'], textposition='top center', name='Skor'))
        if load_scope in ['2d', 'both']:
            for idx, r in d_l.iterrows():
                raw = d_l_raw.loc[idx]
                fig_2d_y.add_trace(go.Scatter(x=[0, r['PC1']], y=[0, r['PC2']], mode='lines+text', text=[None, r['features']], textposition='top center', line=dict(color='red'), showlegend=False, hoverinfo='text', hovertext=f"Var: {r['features']}<br>Raw: ({r['PC1']:.2f}, {r['PC2']:.2f})"))
    fig_2d_y.update_layout(title=f"Snapshot {year_2d}", xaxis=dict(scaleanchor='y', scaleratio=1), template='plotly_white')

    # Traj 2D
    fig_2d_t = go.Figure()
    table_rows = []
    if traj_sel:
        for sel in traj_sel:
            t_type, t_name = sel.split('_', 1)
            if t_type == 'skor':
                d_t = df_pc_plt[df_pc_plt['Kabupaten/Kota'] == t_name].sort_values('Tahun')
                d_t_raw = df_pc_fin[df_pc_fin['Kabupaten/Kota'] == t_name].sort_values('Tahun')
                fig_2d_t.add_trace(go.Scatter(x=d_t['PC1'], y=d_t['PC2'], mode='lines+markers+text', text=d_t['Tahun'], name=t_name))
                for _, r in d_t.iterrows(): table_rows.append({'Nama':t_name, 'Tahun':r['Tahun'], 'PC1':round(r['PC1'],4), 'PC2':round(r['PC2'],4)})
            elif t_type == 'loading':
                d_t = df_load_plt[df_load_plt['features'] == t_name].sort_values('Tahun')
                d_t_raw = df_load_fin[df_load_fin['features'] == t_name].sort_values('Tahun')
                fig_2d_t.add_trace(go.Scatter(x=d_t['PC1'], y=d_t['PC2'], mode='lines+markers+text', text=d_t['Tahun'], name=t_name))
                for _, r in d_t.iterrows(): table_rows.append({'Nama':t_name, 'Tahun':r['Tahun'], 'PC1':round(r['PC1'],4), 'PC2':round(r['PC2'],4)})
    fig_2d_t.update_layout(title="Trajektori 2D", xaxis=dict(scaleanchor='y', scaleratio=1), template='plotly_white')
    
    return fig_3d, fig_2d_y, fig_2d_t, table_rows, [{"name": i, "id": i} for i in pd.DataFrame(table_rows).columns] if table_rows else []

# 6. STATIS PLOTS & TABLES
@app.callback(
    Output('statis-compromise', 'figure'), Output('statis-biplot', 'figure'),
    Output('statis-interstructure', 'figure'), Output('statis-trajectory', 'figure'),
    Output('statis-table-selector', 'options'), Output('statis-detail-table', 'data'), Output('statis-detail-table', 'columns'),
    Output('table-info-display', 'children'),
    Input('statis-core-store', 'data'), Input('statis-table-selector', 'value'), Input('visual-scaling-opts', 'value'),
    Input('table-page-size', 'value')
)
def cb_statis_viz(res, table_key, vis_opts, page_size):
    if not res: return {}, {}, {}, {}, [], [], [], ""
    
    # Cek Opsi Visualisasi
    norm_score = 'norm_score' in vis_opts if vis_opts else False
    scale_load = 'scale_load' in vis_opts if vis_opts else False
    
    # Ambil Data Dasar
    scores = np.array(res['scores'])
    loadings = np.array(res['loadings'])
    
    # --- 1. Scaling untuk Compromise & Biplot ---
    plot_scores, plot_loadings = apply_visual_adjustments(scores, loadings, norm_score, scale_load)
    
    # Label Sumbu (Persentase Variansi)
    eig_vals = np.array(res['eig_vals_c'])
    var_pct = eig_vals / eig_vals.sum() * 100
    ax_x = f"Compromise 1 ({var_pct[0]:.2f}%)"
    ax_y = f"Compromise 2 ({var_pct[1]:.2f}%)"
    
    # Hitung Faktor Normalisasi Global (Penting untuk Trajektori)
    # Agar Trajektori punya skala yang sama dengan Peta Kompromi
    global_max_val = 1.0
    if norm_score:
        global_max_val = np.max(np.abs(scores))
        if global_max_val == 0: global_max_val = 1.0

    # PLOT 1: Interstructure
    fig_inter = px.imshow(res['R'], text_auto=True, x=res['sheet_names'], y=res['sheet_names'], 
                          color_continuous_scale='Viridis', title="Interstructure (RV Matrix)")
    
    # PLOT 2: Compromise Map
    fig_comp = create_biplot(plot_scores, np.zeros_like(loadings), res['obs_labels'], [], 
                             "Compromise Map", color='#1E88E5')
    fig_comp.update_layout(xaxis_title=ax_x, yaxis_title=ax_y)

    # PLOT 3: Biplot
    fig_bi = create_biplot(plot_scores, plot_loadings, res['obs_labels'], res['selected_vars'], 
                           "Compromise Biplot", show_loadings=True)
    fig_bi.update_layout(xaxis_title=ax_x, yaxis_title=ax_y)
    
    # PLOT 4: Trajectory (Perbaikan Logika)
    coords_dict = res['per_year_coords']
    df_traj_list = []
    
    for yr, coords in coords_dict.items():
        c = np.array(coords)
        
        # Terapkan Normalisasi jika User Meminta
        # Kita bagi dengan Max Value dari GLOBAL SCORES agar proporsional
        if norm_score:
            c = c / global_max_val
        
        # Build DF untuk Plotly Express
        df_t = pd.DataFrame(c[:, :2], columns=['PC1', 'PC2'])
        df_t['Kab/Kota'] = res['obs_labels']
        df_t['Tahun'] = yr
        df_traj_list.append(df_t)
        
    df_traj = pd.concat(df_traj_list)
    
    # Gunakan Line Plot (Garis terhubung per Kota)
    fig_traj = px.line(df_traj, x='PC1', y='PC2', color='Kab/Kota', markers=True, 
                       title='STATIS Trajectories (Projected)')
    
    # Pastikan layout konsisten
    fig_traj.update_layout(template='plotly_white', xaxis=dict(scaleanchor='y', scaleratio=1), 
                           xaxis_title=ax_x, yaxis_title=ax_y)
    
    # 5. Tables Logic
    # Filter key internal agar tidak muncul di dropdown
    exclude_keys = ['R', 'alphas', 'eig_vals_c', 'scores', 'loadings', 'per_year_coords', 
                    'sheet_names', 'X_matrices', 'vals_R_sorted', 'k', 'obs_labels', 
                    'selected_vars', 'perm_lambda_obs', 'perm_distribution', 'perm_p_value']
    
    table_opts = [{'label': k.replace('table_', '').replace('_', ' ').title(), 'value': k} 
                  for k in res.keys() if k not in exclude_keys]
    
    tbl_data, tbl_cols, info_text = [], [], ""
    if table_key:
        tbl_data = res.get(table_key, [])
        if tbl_data: 
            tbl_cols = [{"name": i, "id": i} for i in tbl_data[0].keys()]
            info_text = f"Menampilkan Tabel: {table_key}"

    # --- AUTO EXPORT LATEX ---
    export_core_latex(res)
    export_tables_latex(res)

    return fig_comp, fig_bi, fig_inter, fig_traj, table_opts, tbl_data, tbl_cols, info_text


# 7. Permutation Test
@app.callback(
    Output('perm-graph', 'figure'), Output('perm-result-text', 'children'),
    Input('btn-run-perm', 'n_clicks'), State('perm-n-input', 'value'), State('statis-core-store', 'data')
)
def cb_run_perm(n_clicks, n_perm, res):
    if not n_clicks or not res: return {}, ""
    X_matrices = [np.array(m) for m in res['X_matrices']]
    lambda_obs = res['vals_R_sorted'][0]
    dist, p_val = run_permutation_test(X_matrices, res['k'], lambda_obs, n_perm)
    
    fig = px.histogram(x=dist, title=f"Distribusi Null (N={n_perm})", color_discrete_sequence=['#90A4AE'])
    fig.add_vline(x=lambda_obs, line_color="#D32F2F", line_dash="dash", annotation_text=f"Observed: {lambda_obs:.3f}")
    fig.update_layout(template='plotly_white')
    
    interp = "Signifikan (Struktur Stabil)" if p_val < 0.05 else "Tidak Signifikan (Acak)"
    
    # --- AUTO EXPORT LATEX ---
    export_perm_latex(p_val, interp)
    
    return fig, f"P-value = {p_val:.4f}. Interpretasi: {interp}"


# 8. Update Table Page Size
@app.callback(
    Output('statis-detail-table', 'page_size'),
    Input('table-page-size', 'value')
)
def update_page_size(size):
    return size if size else 10

# 9. EVALUASI CLUSTER (ELBOW & DENDROGRAM)
@app.callback(
    Output('elbow-graph', 'figure'),
    Output('dendrogram-graph', 'figure'),
    Input('eval-year-dropdown', 'value'),
    State('statis-core-store', 'data')
)
def cb_eval_cluster(eval_year, res):
    if not eval_year or not res: return {}, {}
    coords = np.array(res['per_year_coords'][str(eval_year)])
    obs_labels = res['obs_labels']
    
    # 1. ELBOW
    sse = []
    k_range = range(1, min(11, len(coords)))
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(coords)
        sse.append(km.inertia_)
    
    fig_elbow = go.Figure()
    fig_elbow.add_trace(go.Scatter(x=list(k_range), y=sse, mode='lines+markers', line=dict(color=COLOR_ACCENT, width=3), marker=dict(size=8)))
    fig_elbow.update_layout(title=f"Metode Elbow (Tahun {eval_year})", xaxis_title="Jumlah Cluster (k)", yaxis_title="Sum of Squared Errors (SSE)", template='plotly_white')
    import os
    os.makedirs("../huggingface", exist_ok=True)
    try: fig_elbow.write_image(f"../huggingface/elbow_plot_{eval_year}.png")
    except: pass

    # 2. DENDROGRAM
    try:
        import plotly.figure_factory as ff
        from scipy.cluster.hierarchy import linkage
        Z = linkage(coords, method='ward')
        fig_dendro = ff.create_dendrogram(coords, labels=obs_labels, orientation='left', linkagefun=lambda x: Z, colorscale=px.colors.qualitative.Bold)
        fig_dendro.update_layout(title=f"Dendrogram Hierarchical (Tahun {eval_year})", template='plotly_white', margin=dict(l=150))
        try: fig_dendro.write_image(f"../huggingface/dendrogram_{eval_year}.png")
        except: pass
    except Exception as e:
        fig_dendro = go.Figure().add_annotation(text=f"Error Dendrogram: {e}", showarrow=False)

    return fig_elbow, fig_dendro


# 10. CLUSTERING TAHUNAN & MATRIKS TRANSISI
@app.callback(
    Output('title-trans-map-t1', 'children'),
    Output('trans-map-t1', 'figure'),
    Output('title-trans-map-t2', 'children'),
    Output('trans-map-t2', 'figure'),
    Output('title-trans-scatter-t1', 'children'),
    Output('trans-scatter-t1', 'figure'),
    Output('title-trans-scatter-t2', 'children'),
    Output('trans-scatter-t2', 'figure'),
    Output('trans-matrix-table', 'data'),
    Output('trans-matrix-table', 'columns'),
    Input('btn-run-trans', 'n_clicks'),
    Input('trans-view-mode', 'value'),
    State('trans-year-dropdown', 'value'),
    State('trans-k-input', 'value'),
    State('statis-core-store', 'data')
)
def cb_run_trans(n_clicks, view_mode, t2_year, k, res):
    if not n_clicks or not t2_year or not res: return "", {}, "", {}, "", {}, "", {}, [], []
    
    years = sorted(list(res['per_year_coords'].keys()))
    t2_idx = years.index(str(t2_year))
    if t2_idx == 0: return "Pilih tahun selain tahun pertama.", {}, "", {}, "", {}, "", {}, [], []
    t1_year = years[t2_idx - 1]
    
    coords_t1 = np.array(res['per_year_coords'][t1_year])
    coords_t2 = np.array(res['per_year_coords'][str(t2_year)])
    obs_labels = res['obs_labels']
    
    km_t1 = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels_t1 = km_t1.fit_predict(coords_t1)
    km_t2 = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels_t2 = km_t2.fit_predict(coords_t2)
    str_labels_t1 = [f"Cluster {l+1}" for l in labels_t1]
    str_labels_t2 = [f"Cluster {l+1}" for l in labels_t2]
    
    # SCATTER T1
    fig_scatter_t1 = px.scatter(x=coords_t1[:,0], y=coords_t1[:,1], color=str_labels_t1, text=obs_labels, title="", color_discrete_sequence=px.colors.qualitative.Bold)
    fig_scatter_t1.update_traces(marker=dict(size=9), textposition='top center')
    fig_scatter_t1.update_layout(template='plotly_white', xaxis_title="PC1", yaxis_title="PC2")
    
    # SCATTER T2
    fig_scatter_t2 = px.scatter(x=coords_t2[:,0], y=coords_t2[:,1], color=str_labels_t2, text=obs_labels, title="", color_discrete_sequence=px.colors.qualitative.Bold)
    fig_scatter_t2.update_traces(marker=dict(size=9), textposition='top center')
    fig_scatter_t2.update_layout(template='plotly_white', xaxis_title="PC1", yaxis_title="PC2")
    
    import os
    os.makedirs("../huggingface", exist_ok=True)
    try: fig_scatter_t1.write_image(f"../huggingface/cluster_biplot_{t1_year}.png")
    except: pass
    try: fig_scatter_t2.write_image(f"../huggingface/cluster_biplot_{t2_year}.png")
    except: pass

    # MAP T1 & T2
    fig_map_t1 = go.Figure()
    fig_map_t2 = go.Figure()
    if indonesia_geojson:
        # Menyesuaikan Center & Zoom sesuai request user
        # mapbox_center = {"lat": -6.9, "lon": 108.5} # Geser ke kiri (bujur lebih tinggi maka map ketarik ke kiri relatif terhadap frame)
        # zoom sekitar 6.2 dari asalnya 7
        mapbox_center = {"lat": -6.9, "lon": 107}
        mapbox_zoom = 6.5
        
        df_map_t1 = pd.DataFrame({'Kab/Kota': obs_labels, 'Cluster': str_labels_t1, 'match_key': obs_labels})
        df_map_t2 = pd.DataFrame({'Kab/Kota': obs_labels, 'Cluster': str_labels_t2, 'match_key': obs_labels})
        
        for feature in indonesia_geojson['features']:
            props = feature['properties']
            raw_name = props.get('NAME_2') or props.get('kab_kota') or props.get('NAMOBJ') or props.get('Name') or ""
            feature['properties']['id_cocok'] = str(raw_name)

        fig_map_t1 = px.choropleth_mapbox(df_map_t1, geojson=indonesia_geojson, locations='match_key', featureidkey='properties.id_cocok', color='Cluster', color_discrete_sequence=px.colors.qualitative.Bold, hover_name='Kab/Kota', mapbox_style="carto-positron", center=mapbox_center, zoom=mapbox_zoom, opacity=0.7)
        fig_map_t1.update_layout(title="", margin={"r":0,"t":0,"l":0,"b":0})
        
        fig_map_t2 = px.choropleth_mapbox(df_map_t2, geojson=indonesia_geojson, locations='match_key', featureidkey='properties.id_cocok', color='Cluster', color_discrete_sequence=px.colors.qualitative.Bold, hover_name='Kab/Kota', mapbox_style="carto-positron", center=mapbox_center, zoom=mapbox_zoom, opacity=0.7)
        fig_map_t2.update_layout(title="", margin={"r":0,"t":0,"l":0,"b":0})
        
        try: fig_map_t1.write_image(f"../huggingface/cluster_map_{t1_year}.png")
        except: pass
        try: fig_map_t2.write_image(f"../huggingface/cluster_map_{t2_year}.png")
        except: pass

    # MATRIKS TRANSISI
    def build_matrix(mode):
        matrix_data, matrix_tex = [], []
        matrix_tex.append(r"\begin{table}[H]")
        matrix_tex.append(r"\centering")
        matrix_tex.append(r"\caption{Matriks Transisi Klaster Tahun " + str(t1_year) + r" ke " + str(t2_year) + r"} \label{tab:transisi_" + str(t1_year) + r"_" + str(t2_year) + r"}")
        matrix_tex.append(r"\begin{tabular}{|c|" + "p{2cm}|"*k + "}")
        matrix_tex.append(r"\hline")
        
        header_row = [f"Tahun {t1_year} \\\\ {t2_year}"] + [f"Cluster {j+1} ({t2_year})" for j in range(k)]
        matrix_tex.append(" & ".join([f"\\textbf{{{x}}}" for x in header_row]) + r" \\ \hline")
        
        for i in range(k):
            row_dict = {f"Tahun {t1_year} \\ {t2_year}": f"Cluster {i+1} ({t1_year})"}
            tex_row = [f"\\textbf{{Cluster {i+1} ({t1_year})}}"]
            for j in range(k):
                intersect_indices = [idx for idx, (l1, l2) in enumerate(zip(labels_t1, labels_t2)) if l1 == i and l2 == j]
                if mode == 'count': val = str(len(intersect_indices))
                else: val = ", ".join([obs_labels[idx] for idx in intersect_indices]) if intersect_indices else "-"
                row_dict[f"Cluster {j+1} ({t2_year})"] = val
                tex_row.append(val.replace('&', r'\\&').replace('%', r'\\%'))
            matrix_data.append(row_dict)
            matrix_tex.append(" & ".join(tex_row) + r" \\ \hline")
            
        matrix_tex.append(r"\end{tabular}")
        matrix_tex.append(r"\end{table}")
        return matrix_data, matrix_tex

    data_count, tex_count = build_matrix('count')
    data_names, tex_names = build_matrix('names')
    
    try:
        with open(f"../huggingface/output_table_transition_matrix_sum_{t1_year}x{t2_year}.tex", "w") as f: f.write("\n".join(tex_count))
        with open(f"../huggingface/output_table_transition_matrix_name_{t1_year}x{t2_year}.tex", "w") as f: f.write("\n".join(tex_names))
    except: pass
    
    req_data = data_count if view_mode == 'count' else data_names
    cols = [{"name": c, "id": c} for c in req_data[0].keys()] if req_data else []
    
    return (
        f"Peta Sebaran Cluster (Tahun {t1_year})", fig_map_t1,
        f"Peta Sebaran Cluster (Tahun {t2_year})", fig_map_t2,
        f"Biplot Cluster (Tahun {t1_year})", fig_scatter_t1,
        f"Biplot Cluster (Tahun {t2_year})", fig_scatter_t2,
        req_data, cols
    )


# 11. CLUSTERING TRAJEKTORI CALLBACK (STATIS FULL)
@app.callback(
    Output('cluster-scatter', 'figure'),
    Output('cluster-dendrogram', 'figure'),
    Output('cluster-map', 'figure'),
    Output('cluster-interpretation', 'children'),
    Input('btn-run-cluster', 'n_clicks'),
    State('cluster-k-input', 'value'),
    State('statis-core-store', 'data')
)
def cb_run_clustering_trajectory(n_clicks, k_clusters, res):
    if not n_clicks or not res: 
        return {}, {}, {}, "Silakan klik tombol 'RUN CLUSTERING'."
    
    obs_labels = res['obs_labels']
    coords_dict = res['per_year_coords']
    years = sorted(list(coords_dict.keys()))
    
    # --- 1. Clustering Logic ---
    features = []
    for i in range(len(obs_labels)):
        city_feats = []
        for yr in years:
            coords = np.array(coords_dict[str(yr)])
            city_feats.extend(coords[i, :]) 
        features.append(city_feats)
    
    X_traj = np.array(features)
    kmeans = KMeans(n_clusters=k_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_traj)
    str_labels = [f"Cluster {l+1}" for l in labels]

    # --- 2. Scatter Plot ---
    scores_comp = np.array(res['scores'])
    fig_scatter = px.scatter(
        x=scores_comp[:, 0], y=scores_comp[:, 1], color=str_labels,
        text=obs_labels, title="Cluster pada Ruang Kompromi",
        color_discrete_sequence=px.colors.qualitative.Bold
    )
    fig_scatter.update_traces(marker=dict(size=8), textposition='top center')
    fig_scatter.update_layout(template='plotly_white', width=800, height=800)
    import os
    os.makedirs("../huggingface", exist_ok=True)
    try: fig_scatter.write_image("../huggingface/cluster_compromise_biplot.png")
    except: pass

    # --- 3. Dendrogram (Dengan Pewarnaan Sesuai K) ---
    try:
        import plotly.figure_factory as ff
        from scipy.cluster.hierarchy import linkage
        
        # 1. Hitung Linkage Matrix manual untuk mencari threshold
        Z = linkage(X_traj, method='ward')
        
        # 2. Hitung Threshold Jarak agar terbentuk persis K cluster
        # Logika: Kita cari jarak merge pada langkah ke-(k-1) dari atas.
        # Kita set threshold sedikit di bawah jarak tersebut.
        if k_clusters > 1 and k_clusters < len(X_traj):
            # Ambil rata-rata jarak antara merge k dan k-1 agar aman
            dist_k = Z[-k_clusters, 2]      # Jarak saat masih k+1 cluster
            dist_k_minus_1 = Z[-(k_clusters-1), 2] # Jarak saat jadi k cluster
            color_thresh = 0.5 * (dist_k + dist_k_minus_1)
        else:
            color_thresh = 0 # Default jika k=1 atau error
            
        # 3. Buat Dendrogram dengan threshold tersebut
        fig_dendro = ff.create_dendrogram(
            X_traj, 
            labels=obs_labels, 
            orientation='left', 
            linkagefun=lambda x: Z, # Gunakan Z yang sama agar konsisten
            color_threshold=color_thresh, # <--- INI KUNCINYA
            colorscale=px.colors.qualitative.Bold
        )
        
        fig_dendro.update_layout(title="Dendrogram Kemiripan Trajektori", template='plotly_white', margin=dict(l=150))
        import os
        os.makedirs("../huggingface", exist_ok=True)
        try: fig_dendro.write_image("../huggingface/dendrogram_compromise.png")
        except: pass
    except Exception as e:
        fig_dendro = go.Figure().add_annotation(text=f"Error Dendrogram: {e}", showarrow=False)

    # --- 3B. Hitung Moran's I untuk PC1 Kompromi (Sumbu Ekonomi Utama) ---
    moran_text = ""
    if res and indonesia_geojson and gdf is not None:
        try:
            # Ambil skor PC1
            scores = np.array(res['scores'])
            pc1_scores = scores[:, 0]
            obs_labels_mc = res['obs_labels']
            
            # Hitung
            m_i, m_exp = _calculate_moran_manual(gdf, pc1_scores, obs_labels_mc)
            
            if m_i is not None:
                status = "Berkelompok (Clustered)" if m_i > m_exp else "Menyebar (Dispersed/Random)"
                moran_text = f" | Global Moran's I (PC1): {m_i:.4f} (Exp: {m_exp:.4f}) -> Pola: {status}"
        except Exception as e:
            print(f"Gagal hitung Moran di callback: {e}")

    # --- 4. PETA CHOROPLETH (UPDATED MATCHING LOGIC) ---
    fig_map = go.Figure()
    
    if indonesia_geojson:
        # A. Siapkan DataFrame
        df_map = pd.DataFrame({'Kab/Kota': obs_labels, 'Cluster': str_labels})
        df_map['match_key'] = df_map['Kab/Kota']
        
        # B. Inject Key ke GeoJSON (In-Memory)
        # Kita cari properti nama kabupaten di GeoJSON Anda
        found_matches = 0
        
        for feature in indonesia_geojson['features']:
            props = feature['properties']
            
            # Coba berbagai kemungkinan nama properti di GeoJSON Anda
            # Prioritas: 'WADMKK' (dari diskusi kita), lalu 'kab_kota', 'NAMOBJ', 'Name'
            raw_name = props.get('NAME_2') or props.get('kab_kota') or props.get('NAMOBJ') or props.get('Name') or ""
            
            # Bersihkan nama di GeoJSON
            clean_geo_name = str(raw_name)
            
            # Simpan nama bersih ini ke properti baru 'id_cocok'
            feature['properties']['id_cocok'] = clean_geo_name
            
            # Cek apakah cocok dengan data Excel
            if clean_geo_name in df_map['match_key'].values:
                found_matches += 1

        # C. Plotting
        title_text = f"Peta Sebaran Cluster (Cocok: {found_matches} Wilayah)"
        if found_matches == 0:
            title_text += " - PERINGATAN: Nama wilayah tidak ada yang cocok!"

        fig_map = px.choropleth_mapbox(
            df_map,
            geojson=indonesia_geojson,
            locations='match_key',           # Kolom di DataFrame
            featureidkey='properties.id_cocok', # Properti buatan di GeoJSON
            color='Cluster',
            color_discrete_sequence=px.colors.qualitative.Bold,
            hover_name='Kab/Kota',
            mapbox_style="carto-positron",
            center={"lat": -6.9, "lon": 107}, # Geser ke kiri (zoom out 2x)
            zoom=6.5, opacity=0.7
        )
        fig_map.update_layout(title=title_text, margin={"r":0,"t":40,"l":0,"b":0})
        import os
        os.makedirs("../huggingface", exist_ok=True)
        try: fig_map.write_image("../huggingface/cluster_compromise_map.png")
        except: pass
    else:
        fig_map.add_annotation(text="Gagal memuat data GeoJSON.", showarrow=False)

    # 5. Interpretasi
    counts = np.bincount(labels)
    interp_text = [html.Strong("Interpretasi Cluster: "), html.Br()]
    if moran_text: 
        interp_text.append(html.Span(moran_text, style={'color': '#D81B60', 'fontWeight': 'bold'}))
        interp_text.append(html.Br())
        
    for i, count in enumerate(counts):
        interp_text.append(f"Cluster {i+1}: {count} Wilayah.")
        if i < len(counts)-1: interp_text.append(" | ")
    
    return fig_scatter, fig_dendro, fig_map, interp_text

# 12. IPM MATRIX CALLBACK (UNDP CATEGORIES)
@app.callback(
    Output('ipm-disclaimer-text', 'children'),
    Output('ipm-trans-matrix-table', 'data'),
    Output('ipm-trans-matrix-table', 'columns'),
    Input('btn-run-ipm-trans', 'n_clicks'),
    Input('ipm-trans-view-mode', 'value'),
    State('ipm-trans-year-dropdown', 'value'),
    State('global-data-store', 'data')
)
def cb_run_ipm_trans(n_clicks, view_mode, t2_year, data):
    if not n_clicks or not t2_year or not data: return "", [], []
    
    df = pd.read_json(io.StringIO(data['df_json']), orient='split')
    years = data['years']
    
    if 'IPM' not in df.columns:
        return "Kolom IPM tidak ditemukan pada data yang diunggah.", [], []
        
    t2_idx = years.index(t2_year)
    if t2_idx == 0: return "Pilih tahun selain tahun pertama.", [], []
    t1_year = years[t2_idx - 1]
    
    # Filter Data untuk T1 dan T2
    df_t1 = df[df['Tahun'] == t1_year].set_index('Kabupaten/Kota')
    df_t2 = df[df['Tahun'] == t2_year].set_index('Kabupaten/Kota')
    
    common_kabs = df_t1.index.intersection(df_t2.index)
    if len(common_kabs) == 0: return "Tidak ada data Kabupaten/Kota yang cocok antara dua tahun.", [], []
    
    df_t1 = df_t1.loc[common_kabs]
    df_t2 = df_t2.loc[common_kabs]
    
    # Kategori UNDP
    def categorize_ipm(val):
        if val >= 80: return "Sangat Tinggi"
        elif val >= 70: return "Tinggi"
        elif val >= 55: return "Sedang"
        else: return "Rendah"
        
    df_t1['IPM_Cat'] = df_t1['IPM'].apply(categorize_ipm)
    df_t2['IPM_Cat'] = df_t2['IPM'].apply(categorize_ipm)
    
    categories = ["Sangat Tinggi", "Tinggi", "Sedang", "Rendah"]
    
    # Hitung Disclaimer / Summary
    counts_t1 = df_t1['IPM_Cat'].value_counts()
    counts_t2 = df_t2['IPM_Cat'].value_counts()
    
    disclaimer_parts = []
    disclaimer_parts.append(html.Span(f"Tahun {t1_year}: ", style={'color': '#1565C0'}))
    for cat in categories:
        if cat in counts_t1: disclaimer_parts.append(f"{cat} ({counts_t1[cat]}), ")
    disclaimer_parts.append(html.Br())
    disclaimer_parts.append(html.Span(f"Tahun {t2_year}: ", style={'color': '#D81B60'}))
    for cat in categories:
        if cat in counts_t2: disclaimer_parts.append(f"{cat} ({counts_t2[cat]}), ")
        
    # Bangun Matriks
    def build_ipm_matrix(mode):
        matrix_data, matrix_tex = [], []
        matrix_tex.append(r"\begin{table}[H]")
        matrix_tex.append(r"\centering")
        matrix_tex.append(r"\caption{Matriks Transisi IPM Tahun " + str(t1_year) + r" ke " + str(t2_year) + r"} \label{tab:ipm_transisi_" + str(t1_year) + r"_" + str(t2_year) + r"}")
        matrix_tex.append(r"\begin{tabular}{|c|" + "p{2cm}|"*len(categories) + "}")
        matrix_tex.append(r"\hline")
        
        header_row = [f"Tahun {t1_year} \\\\ {t2_year}"] + [f"{cat} ({t2_year})" for cat in categories]
        matrix_tex.append(" & ".join([f"\\textbf{{{x}}}" for x in header_row]) + r" \\ \hline")
        
        for cat_t1 in categories:
            row_dict = {f"Tahun {t1_year} \\ {t2_year}": f"{cat_t1} ({t1_year})"}
            tex_row = [f"\\textbf{{{cat_t1} ({t1_year})}}"]
            for cat_t2 in categories:
                # Ambil daerah yang pindah dari cat_t1 ke cat_t2
                mask = (df_t1['IPM_Cat'] == cat_t1) & (df_t2['IPM_Cat'] == cat_t2)
                kabs = df_t1[mask].index.tolist()
                
                if mode == 'count': val = str(len(kabs))
                else: val = ", ".join(kabs) if kabs else "-"
                row_dict[f"{cat_t2} ({t2_year})"] = val
                tex_row.append(val.replace('&', r'\\&').replace('%', r'\\%'))
                
            matrix_data.append(row_dict)
            matrix_tex.append(" & ".join(tex_row) + r" \\ \hline")
            
        matrix_tex.append(r"\end{tabular}")
        matrix_tex.append(r"\end{table}")
        return matrix_data, matrix_tex

    data_count, tex_count = build_ipm_matrix('count')
    data_names, tex_names = build_ipm_matrix('names')
    
    import os
    os.makedirs("../huggingface", exist_ok=True)
    try:
        with open(f"../huggingface/output_table_ipm_matrix_sum_{t1_year}x{t2_year}.tex", "w") as f: f.write("\n".join(tex_count))
        with open(f"../huggingface/output_table_ipm_matrix_name_{t1_year}x{t2_year}.tex", "w") as f: f.write("\n".join(tex_names))
    except: pass
        
    req_data = data_count if view_mode == 'count' else data_names
    cols = [{"name": c, "id": c} for c in req_data[0].keys()] if req_data else []
    
    return disclaimer_parts, req_data, cols


# 13. CROSS TABULATION CALLBACK (K-MEANS VS IPM)
@app.callback(
    Output('cross-table', 'data'),
    Output('cross-table', 'columns'),
    Input('btn-run-cross', 'n_clicks'),
    Input('cross-view-mode', 'value'),
    State('cross-year-dropdown', 'value'),
    State('cross-k-input', 'value'),
    State('global-data-store', 'data'),
    State('statis-core-store', 'data')
)
def cb_run_cross_tab(n_clicks, view_mode, sel_year, k, data_store, statis_store):
    if not n_clicks or not sel_year or not data_store or not statis_store: return [], []
    
    # 1. Ambil IPM kategories dari data asli
    df = pd.read_json(io.StringIO(data_store['df_json']), orient='split')
    if 'IPM' not in df.columns: return [], []
    
    df_yr = df[df['Tahun'] == sel_year].set_index('Kabupaten/Kota')
    def categorize_ipm(val):
        if val >= 80: return "Sangat Tinggi"
        elif val >= 70: return "Tinggi"
        elif val >= 55: return "Sedang"
        else: return "Rendah"
    df_yr['IPM_Cat'] = df_yr['IPM'].apply(categorize_ipm)
    
    # 2. Ambil label K-Means dari statis store
    obs_labels = statis_store['obs_labels']
    str_year = str(sel_year)
    if str_year not in statis_store['per_year_coords']: return [], []
    
    coords = np.array(statis_store['per_year_coords'][str_year])
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(coords)
    
    # Gabung
    df_clusters = pd.DataFrame({'Cluster_KMeans': [f"Cluster {l+1}" for l in labels]}, index=obs_labels)
    df_merged = df_yr.join(df_clusters).dropna(subset=['Cluster_KMeans', 'IPM_Cat'])
    
    # Tabulasi Silang
    categories = ["Sangat Tinggi", "Tinggi", "Sedang", "Rendah"]
    
    def build_cross_matrix(mode):
        matrix_data, matrix_tex = [], []
        matrix_tex.append(r"\begin{table}[H]")
        matrix_tex.append(r"\centering")
        matrix_tex.append(r"\caption{Perbandingan Anggota Cluster dengan Kategori IPM (" + str(sel_year) + r")} \label{tab:ipm_cross_" + str(sel_year) + r"}")
        matrix_tex.append(r"\begin{tabular}{|c|" + "p{2cm}|"*len(categories) + "}")
        matrix_tex.append(r"\hline")
        
        header_row = ["Cluster K-Means"] + categories
        matrix_tex.append(" & ".join([f"\\textbf{{{x}}}" for x in header_row]) + r" \\ \hline")
        
        for c_idx in range(k):
            c_name = f"Cluster {c_idx+1}"
            row_dict = {"Cluster K-Means": c_name}
            tex_row = [f"\\textbf{{{c_name}}}"]
            for cat in categories:
                kabs = df_merged[(df_merged['Cluster_KMeans'] == c_name) & (df_merged['IPM_Cat'] == cat)].index.tolist()
                if mode == 'count': val = str(len(kabs))
                else: val = ", ".join(kabs) if kabs else "-"
                row_dict[cat] = val
                tex_row.append(val.replace('&', r'\\&').replace('%', r'\\%'))
            matrix_data.append(row_dict)
            matrix_tex.append(" & ".join(tex_row) + r" \\ \hline")
            
        matrix_tex.append(r"\end{tabular}")
        matrix_tex.append(r"\end{table}")
        return matrix_data, matrix_tex
        
    data_count, tex_count = build_cross_matrix('count')
    data_names, tex_names = build_cross_matrix('names')
    
    import os
    os.makedirs("../huggingface", exist_ok=True)
    try:
        with open(f"../huggingface/output_table_cross_matrix_sum_{sel_year}.tex", "w") as f: f.write("\n".join(tex_count))
        with open(f"../huggingface/output_table_cross_matrix_name_{sel_year}.tex", "w") as f: f.write("\n".join(tex_names))
    except: pass
    
    req_data = data_count if view_mode == 'count' else data_names
    cols = [{"name": c, "id": c} for c in req_data[0].keys()] if req_data else []
    return req_data, cols


if __name__ == '__main__':
    # Disable reloader to prevent restart loop when writing LaTeX files
    app.run(debug=True, use_reloader=False, port=3333)