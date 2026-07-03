from dash import Dash, dcc, html, Input, Output, State, dash_table, exceptions, ctx
import base64
import dash
import geopandas as gpd
import io
import json
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import scipy.stats as stats
import os
from scipy.cluster.hierarchy import dendrogram, linkage
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from scipy.optimize import linear_sum_assignment
EXTERNAL_STYLESHEETS = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
external_scripts = [
    "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"
]
EMPTY_FIG = go.Figure(layout=go.Layout(
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    xaxis={'visible': False, 'showgrid': False, 'zeroline': False},
    yaxis={'visible': False, 'showgrid': False, 'zeroline': False},
    margin={'l': 0, 'r': 0, 't': 0, 'b': 0},
    height=10
))

app = Dash(
    __name__,
    external_stylesheets=EXTERNAL_STYLESHEETS,
    external_scripts=external_scripts,
    suppress_callback_exceptions=True
)
server = app.server

def _calculate_R_matrix(Ws_list, k, D=None):
    """Matriks koefisien RV (normalisasi); untuk heatmap dan interpretasi."""
    R = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            if D is not None:
                num = np.trace(Ws_list[i] @ D @ Ws_list[j] @ D)
                den = np.sqrt(np.trace(Ws_list[i] @ D @ Ws_list[i] @ D) * np.trace(Ws_list[j] @ D @ Ws_list[j] @ D))
            else:
                num = np.trace(Ws_list[i] @ Ws_list[j])
                den = np.sqrt(np.trace(Ws_list[i] @ Ws_list[i]) * np.trace(Ws_list[j] @ Ws_list[j]))
            R[i, j] = 0.0 if den == 0 else num / den
    return R


def _calculate_H_matrix(Ws_list, k, D=None):
    """Matriks interstruktur: elemen (i,j) = tr(W_i W_j) (Lavit 1994; Oliveira et al. 2024)."""
    H = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            if D is not None:
                if isinstance(D, list):
                    H[i, j] = np.trace(Ws_list[i] @ D[i] @ Ws_list[j] @ D[j])
                else:
                    H[i, j] = np.trace(Ws_list[i] @ D @ Ws_list[j] @ D)
            else:
                H[i, j] = np.trace(Ws_list[i] @ Ws_list[j])
    return H


def _calculate_moran_manual(gdf, value_analytics, obs_names_analytics):
    """
    Hitung Moran's I secara manual menggunakan Geopandas adjacency (Touches).
    Tanpa library pysal/esda agar ringan.
    """
    try:
        if gdf is None: return None, None, None, None, None, None
        
        # 1. Match Data dengan GeoData (Eksak)
        geom_map = {}
        for _, row in gdf.iterrows():
            name = str(row['id_cocok'])
            if name: geom_map[name] = row['geometry']
            
        # 2. Re-construct Series data yang urut
        y, geoms = [], []
        for i, name in enumerate(obs_names_analytics):
            if name in geom_map:
                y.append(value_analytics[i])
                geoms.append(geom_map[name])
        
        if len(y) < 5: 
            return None, None, None, None, None, None
        
        y = np.array(y)
        n = len(y)
        
        # 3. Buat Weight Matrix (W) berdasarkan sentuhan (Queen Contiguity)
        W = np.zeros((n, n))
        temp_gdf = gpd.GeoDataFrame({'geometry': geoms})
        for i in range(n):
            for j in range(n):
                if i != j:
                    if temp_gdf.iloc[i].geometry.touches(temp_gdf.iloc[j].geometry):
                        W[i, j] = 1.0
        
        # Row Standardization
        row_sums = W.sum(axis=1)
        with np.errstate(divide='ignore', invalid='ignore'):
            W_std = W / row_sums[:, None]
        W_std[np.isnan(W_std)] = 0.0
        
        # 4. Hitung Moran's I
        y_bar = np.mean(y)
        y_dev = y - y_bar
        sum_sq_dev = np.sum(y_dev**2)
        
        sum_w_std = float(n) if n > 0 else 0.0
        if sum_sq_dev == 0: return 0.0, -1.0/(n-1) if n > 1 else 0.0, n, 0.0, 0.0, 0.0
        
        numerator = 0.0
        for i in range(n):
            for j in range(n):
                numerator += W_std[i, j] * y_dev[i] * y_dev[j]
        
        # Sesuai formula Moran's I untuk baris-terstandarisasi (S0 = n)
        moran_i = numerator / sum_sq_dev
        expected_i = -1.0 / (n - 1) if n > 1 else 0.0
        
        return moran_i, expected_i, n, sum_w_std, numerator, sum_sq_dev
        
    except Exception as e:
        print(f"Moran Error: {e}")
        return None, None, None, None, None, None

def _get_first_eigenvalue(square_matrix):
    vals = np.linalg.eigvals(square_matrix)
    return np.sort(np.real(vals))[-1]


def run_statis_core(uploaded_content_string, selected_vars, sheet_names, scenario='scenario2', weight_var=None):
    """
    Menjalankan penghitungan STATIS Lengkap (Matriks, Skor, Loading).
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
    jp_columns = {}  # {sheet_name: {wilayah: weight_var_value}} untuk bobot demografis
    _JP_NAMES = ['JP', 'Jumlah Penduduk', 'jumlah_penduduk', 'Penduduk', 'Total Penduduk']

    for s in sheet_names:
        # PENTING: Selalu seek(0) sebelum read_excel baru jika menggunakan stream yang sama
        excel_file_stream.seek(0)
        try:
            df_s = pd.read_excel(excel_file_stream, sheet_name=s)
            # Pastikan kolom Kabupaten/Kota ada dan bersih
            if 'Kabupaten/Kota' in df_s.columns:
                df_s = df_s.set_index("Kabupaten/Kota")
            elif df_s.index.name != "Kabupaten/Kota":
                # Jika tidak ada, coba ambil kolom pertama sebagai index
                df_s = df_s.set_index(df_s.columns[0])

            # Ekstrak kolom bobot: gunakan weight_var jika dipilih, fallback ke JP names
            bobot_col = None
            if weight_var and weight_var in df_s.columns:
                bobot_col = weight_var
            else:
                for jp_name in _JP_NAMES:
                    if jp_name in df_s.columns:
                        bobot_col = jp_name
                        break
            if bobot_col:
                jp_columns[s] = df_s[bobot_col].to_dict()

            vars_in_sheet = [v for v in selected_vars if v in df_s.columns]
            if vars_in_sheet:
                tables.append(df_s[vars_in_sheet].copy())
        except Exception as e_sheet:
            print(f"Error reading sheet {s}: {e_sheet}")
            continue

    if not tables: raise Exception("Data tidak valid atau variabel tidak ditemukan di sheet mana pun.")
    
    # 2. Align Indices (SANGAT PENTING: Hanya Wilayah yang ada di SEMUA tahun yang dianalisis)
    common_idx = tables[0].index
    for t in tables[1:]:
        common_idx = common_idx.intersection(t.index)
    
    if len(common_idx) == 0:
        raise Exception("Gagal: Tidak ada Nama Wilayah (Kabupaten/Kota) yang sama di seluruh tahun.")
        
    tables = [t.loc[common_idx].copy() for t in tables]
    
    # [ROBUSTNESS] Drop baris yang memiliki NaN pada variabel terpilih
    for i in range(len(tables)):
        tables[i] = tables[i].dropna(subset=selected_vars)
    
    # Re-align setelah dropna jika ada yang hilang tidak konsisten
    common_idx = tables[0].index
    for t in tables[1:]:
        common_idx = common_idx.intersection(t.index)
    tables = [t.loc[common_idx].copy() for t in tables]

    obs_labels = tables[0].index.tolist()
    selected_vars_final = tables[0].columns.tolist() 
    k = len(tables)
    n_obs = len(obs_labels)

    # 3a. Hitung Bobot Demografis m_i dari Jumlah Penduduk (JP)
    #     Sesuai Lavit et al. (1994): rata-rata JP lintas tahun agar ruang metrik D
    #     bersifat konstan di semua situasi (syarat validitas koefisien RV).
    jp_arrays = []
    for s in sheet_names:
        if s in jp_columns:
            jp_y = np.array([jp_columns[s].get(idx, np.nan) for idx in obs_labels], dtype=float)
            if not np.any(np.isnan(jp_y)) and np.all(jp_y > 0):
                jp_arrays.append(jp_y)

    if len(jp_arrays) > 0:
        JP_mean = np.array(jp_arrays).mean(axis=0)    # rata-rata JP lintas K tahun  -> shape (n,)
        m_weights = JP_mean / JP_mean.sum()            # m_i = JP_bar_i / sum(JP_bar)
        print(f"[STATIS] Bobot demografis m_i dari {len(jp_arrays)} tahun. sum(m)={m_weights.sum():.6f}")
    else:
        m_weights = np.ones(n_obs) / n_obs             # fallback: bobot seragam 1/n
        print("[STATIS] PERINGATAN: Kolom JP tidak ditemukan. Menggunakan bobot seragam 1/n.")

    # Matriks metrik D dan turunannya (Persamaan eq:matriks_D)
    D_sqrt     = np.diag(np.sqrt(m_weights))           # D^{1/2}  — diagonal sqrt(m_i)
    D_inv_sqrt = np.diag(1.0 / np.sqrt(m_weights))     # D^{-1/2} — diagonal 1/sqrt(m_i)
    m = m_weights                                       # alias ringkas untuk komputasi

    # 3b. Weighted Z-Score & Intra-struktur W_k = (D^{1/2} Z_k)(D^{1/2} Z_k)^T
    tables_std, X_matrices, Ws = [], [], []

    for t in tables:
        arr = t.values.astype(float)                   # shape (n, p)
        # Rata-rata populasi terbobot: mu_jk = sum_i m_i * x_ijk
        mu = m @ arr                                   # shape (p,)
        # Sentralisasi
        centered = arr - mu                            # shape (n, p)
        # Simpangan baku populasi terbobot: sigma_jk = sqrt(sum_i m_i*(x_ijk-mu_jk)^2)
        var_w = m @ (centered ** 2)                    # shape (p,)
        sigma = np.sqrt(np.clip(var_w, 1e-12, None))   # shape (p,) — clipping untuk stabilitas
        # Weighted Z-score: z_ijk = (x_ijk - mu_jk) / sigma_jk
        Z_k = centered / sigma                         # shape (n, p)

        tables_std.append(pd.DataFrame(Z_k, index=t.index, columns=t.columns))
        X_matrices.append(Z_k)
        # W_k = Z_k Z_k^T  -- pure unweighted intra-structure matrix (Lavit 1994)
        Ws.append(Z_k @ Z_k.T)                  # shape (n, n)
        
    # 4. Inter-struktur: H (produk Hilbert–Schmidt) dan matriks RV untuk tampilan
    D_diag_mat = np.diag(m_weights)
    H_W = _calculate_H_matrix(Ws, k, D=D_diag_mat)
    
    Ss_list = []
    for X_std in X_matrices:
        Sk = X_std.T @ D_diag_mat @ X_std   # S_k = Z_k^T D Z_k
        Ss_list.append(Sk)
        
    H_S = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            H_S[i, j] = np.trace(Ss_list[i] @ Ss_list[j])

    # PILIH SKENARIO (Lavit 1994)
    # Hitung p1 untuk kedua matriks agar bisa ditampilkan di tabel mana pun skenarionya
    # Menggunakan eigh karena H_W dan H_S simetris
    vals_HW, vecs_HW = np.linalg.eigh(H_W)
    idx_HW = np.argsort(np.real(vals_HW))[::-1]
    p1_W = np.real(vecs_HW[:, idx_HW[0]])
    if p1_W.sum() < 0: p1_W = -p1_W

    vals_HS, vecs_HS = np.linalg.eigh(H_S)
    idx_HS = np.argsort(np.real(vals_HS))[::-1]
    p1_S = np.real(vecs_HS[:, idx_HS[0]])
    if p1_S.sum() < 0: p1_S = -p1_S

    if scenario == 'scenario1':
        H = H_W
        p1 = p1_W
        print("  [STATIS] Menggunakan Skenario 1: ACT Klasik (Host = Wilayah)")
    else:
        H = H_S
        p1 = p1_S
        print("  [STATIS] Menggunakan Skenario 2: Dual STATIS (Host = Indikator)")

    # Bobot (Alpha): vektor eigen pertama dari H, dinormalisasi (Lavit 1994)
    alphas = p1 / p1.sum()

    # 5. Kompromi (Wc dan Sc)
    Wc = np.zeros_like(Ws[0])
    Sc = np.zeros_like(Ss_list[0])
    for a, W, S in zip(alphas, Ws, Ss_list):
        Wc += a * W
        Sc += a * S

    # 6. Dekomposisi dan Proyeksi
    if scenario == 'scenario1':
        # --- SKENARIO 1: HOST = WILAYAH (ACT Klasik) ---
        Wc_weighted = D_sqrt @ Wc @ D_sqrt
        P, Lambda_c, _ = np.linalg.svd(Wc_weighted)
        eig_vals_c = Lambda_c
        eig_vecs_c = P
        idxc = np.argsort(eig_vals_c)[::-1]
        eig_vals_c, eig_vecs_c = eig_vals_c[idxc], eig_vecs_c[:, idxc]
        
        # Skor: Fc = D^{-1/2} P Lambda^{1/2}
        sq2 = np.sqrt(np.clip(eig_vals_c[:2], 0, None))
        scores_raw = D_inv_sqrt @ eig_vecs_c[:, :2] * sq2
        sq_full = np.sqrt(np.clip(eig_vals_c, 0, None))
        
        # Loadings: Proyeksi Variabel dari TIAP TAHUN ke ruang Skor (Abdi et al. 2012, Eq. 39)
        loadings_intra_list = []
        for Zk in X_matrices:
            # Gk = Zk^T D Fc Lambda^{-1/2}
            Gk = Zk.T @ D_diag_mat @ scores_raw / np.clip(sq2, 1e-12, None)
            loadings_intra_list.append(Gk)
            
        # Compromise Loadings: Rata-rata dari koordinat loadings intra (Lavit Mazhab)
        Gc = np.zeros_like(loadings_intra_list[0])
        for a, Gk in zip(alphas, loadings_intra_list):
            Gc += a * Gk
            
        loadings = Gc
        Vc_vars = Gc / np.clip(sq2, 1e-12, None) # Normalisasi sebagai penunjuk arah
        
    else:
        # --- SKENARIO 2: HOST = INDIKATOR (Dual STATIS) ---
        U_s, S_s, _ = np.linalg.svd(Sc)
        eig_vals_c = S_s # Nilai eigen dari Sc
        idxc = np.argsort(eig_vals_c)[::-1]
        eig_vals_c = eig_vals_c[idxc]
        # Ambil 2 vektor eigen teratas (P) setelah diurutkan
        Vc_vars = U_s[:, idxc[:2]]
        
        # Loadings: Gc = P Lambda^{1/2}
        sq_s = np.sqrt(np.clip(eig_vals_c[:2], 0, None))
        
        # Loading Intra: Proyeksi struktur kovariansi parsial (Sk) ke ruang Kompromi (Lavit 1994)
        loadings_intra_list = []
        for Zk in X_matrices:
            # Gk = Sk @ Vc @ Lambda^{-1/2}
            Sk_i = Zk.T @ D_diag_mat @ Zk
            Gk = Sk_i @ Vc_vars[:, :2] / np.clip(sq_s, 1e-12, None)
            loadings_intra_list.append(Gk)
            
        # Compromise Loadings: Gc (Harus sama dengan Vc * sq_s jika menggunakan alfa)
        Gc = np.zeros_like(loadings_intra_list[0])
        for a, Gk in zip(alphas, loadings_intra_list):
            Gc += a * Gk
            
        loadings = Gc
        sq_full = np.sqrt(np.clip(eig_vals_c, 0, None))
        
        # Skor: Proyeksi Wilayah dari TIAP TAHUN ke ruang Loadings (Abdi et al. 2012, Eq. 25)
        scores_intra_list = []
        for Zk in X_matrices:
            # Fk = Zk @ (Gc * Lambda^{-1/2})
            # Kita gunakan Gc / sq_s karena Gc = Vc * sq_s
            Fk = Zk @ (Gc / np.clip(sq_s, 1e-12, None))
            scores_intra_list.append(Fk)
            
        # Skor Kompromi: Rata-rata dari koordinat skor intra
        scores_kompromi = np.zeros_like(scores_intra_list[0])
        for a, Fk in zip(alphas, scores_intra_list):
            scores_kompromi += a * Fk
            
        scores_raw = scores_kompromi
        
        # [PENTING] Vektor eigen objek secara dualitas: U = D_sqrt @ Zc @ V @ Lambda^-1/2
        # Untuk keperluan dualitas, kita tetap butuh representasi Zc sesaat di sini
        Zc_temp = np.zeros_like(X_matrices[0])
        for a, Zk in zip(alphas, X_matrices): Zc_temp += a * Zk
        eig_vecs_c = D_sqrt @ Zc_temp @ Vc_vars[:, :2] / np.clip(sq_s, 1e-12, None)

    # Simpan Koordinat Murni (Sebelum Flip) untuk Tabel Perbandingan
    intra_score_svd_dict = {}
    intra_load_svd_dict = {}
    for i, yr in enumerate(sheet_names):
        X_std = X_matrices[i]
        if scenario == 'scenario1':
            # Skenario 1: Host = Wilayah
            # Fk = Wk @ D^{1/2} @ P @ Lambda^{-1/2}
            fk_svd = Ws[i] @ D_sqrt @ eig_vecs_c[:, :2] / np.clip(sq2, 1e-12, None)
            # Gk = Zk^T @ D @ Fc @ Lambda^{-1/2}
            gk_svd = X_std.T @ D_diag_mat @ scores_raw / np.clip(sq2, 1e-12, None)
        else:
            # Skenario 2: Host = Indikator
            # Gk = Sk @ Vc @ Lambda^{-1/2}
            Sk_i = X_std.T @ D_diag_mat @ X_std
            gk_svd = Sk_i @ Vc_vars[:, :2] / np.clip(sq_s, 1e-12, None)
            # Fk = Zk @ (Gc @ Lambda^{-1/2})
            fk_svd = X_std @ (Gc / np.clip(sq_s, 1e-12, None))
        
        intra_score_svd_dict[str(yr)] = fk_svd.tolist()
        intra_load_svd_dict[str(yr)] = gk_svd.tolist()

    scores_svd = scores_raw.copy()
    loadings_svd = loadings.copy()

    # 8. Trajectories per year (Intra-Scores F_k)
    per_year_coords = {}
    if scenario == 'scenario1':
        for i, (year, Wk) in enumerate(zip(sheet_names, Ws)):
            per_year_coords[year] = Wk @ D_sqrt @ eig_vecs_c[:, :2] / np.clip(sq2, 1e-12, None)
    else:
        for year, dfstd in zip(sheet_names, tables_std):
            per_year_coords[year] = dfstd.values @ Vc_vars

    # Matriks & Tabel
    df_alphas = pd.DataFrame({'Tahun': sheet_names, 'Bobot (Alpha)': [round(a, 4) for a in alphas]})
    var_expl = eig_vals_c / eig_vals_c.sum() * 100
    df_eigen = pd.DataFrame({
        'Dim': [f'Dim {i+1}' for i in range(len(eig_vals_c))],
        'Eigen': [round(v, 4) for v in eig_vals_c],
        'Akar Ciri': [round(v, 4) for v in sq_full],
        'Var (%)': [round(v, 2) for v in var_expl],
        'Kum (%)': [round(v, 2) for v in np.cumsum(var_expl)]
    })
    df_Fc = pd.DataFrame(scores_raw, index=obs_labels, columns=['PC1', 'PC2'])
    df_Fc.index.name = 'Kab/Kota'; df_Fc = df_Fc.reset_index()
    df_Gc = pd.DataFrame(np.round(Gc, 6), index=selected_vars_final, columns=['PC1', 'PC2'])
    df_Gc.index.name = 'Variabel'; df_Gc = df_Gc.reset_index()
    R_W = _calculate_R_matrix(Ws, k, D=D_diag_mat)
    R_S = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            num = np.trace(Ss_list[i] @ Ss_list[j])
            den = np.sqrt(np.trace(Ss_list[i] @ Ss_list[i]) * np.trace(Ss_list[j] @ Ss_list[j]))
            R_S[i, j] = num / den if den > 0 else 0

    # Untuk Scree Plot Interstruktur (Penyelarasan dengan dashboard)
    R_used = R_W if scenario == 'scenario1' else R_S
    vals_R_sorted = np.sort(np.real(np.linalg.eigvals(R_used)))[::-1]
    H_used = H_W if scenario == 'scenario1' else H_S
    vals_H_sorted = np.sort(np.real(np.linalg.eigvals(H_used)))[::-1]

    df_R = pd.DataFrame(R_W, index=sheet_names, columns=sheet_names)
    df_R.index.name = 'Tahun'; df_R = df_R.reset_index()
    df_RS = pd.DataFrame(R_S, index=sheet_names, columns=sheet_names)
    df_RS.index.name = 'Tahun'; df_RS = df_RS.reset_index()
    
    # Simpan H_W dan H_S secara terpisah untuk tabel
    df_H_W = pd.DataFrame(H_W, index=sheet_names, columns=sheet_names)
    df_H_W.index.name = 'Tahun'; df_H_W = df_H_W.reset_index()
    df_H_S = pd.DataFrame(H_S, index=sheet_names, columns=sheet_names)
    df_H_S.index.name = 'Tahun'; df_H_S = df_H_S.reset_index()
    
    # Tabel Vektor Eigen (Kompas / Vektor Eigen Tergeneralisasi)
    # Menampilkan P_teori = D^{-1/2} @ P_svd agar memenuhi P^T D P = I
    P_theory = D_inv_sqrt @ eig_vecs_c[:, :2]
    df_V_W = pd.DataFrame(P_theory, index=obs_labels, columns=['P1', 'P2']).reset_index()
    df_V_S = pd.DataFrame(Vc_vars, index=selected_vars_final, columns=['P1', 'P2']).reset_index()
    df_Wc = pd.DataFrame(Wc, index=obs_labels, columns=obs_labels)
    df_Wc.index.name = 'Kab/Kota'; df_Wc = df_Wc.reset_index()
    df_Sc = pd.DataFrame(np.round(Sc, 6), index=selected_vars_final, columns=selected_vars_final)
    df_Sc.index.name = 'Variabel'; df_Sc = df_Sc.reset_index()
    df_dataset = pd.concat([t.add_suffix(f" ({n})") for t, n in zip(tables, sheet_names)], axis=1)
    df_dataset.index.name = 'Kab/Kota'; df_dataset = df_dataset.reset_index()

    intra_score_dicts = {}
    for i, yr in enumerate(sheet_names):
        # 1. Matriks Produk Skalar (W_k atau S_k)
        df_wk = pd.DataFrame(np.round(Ws[i], 6), index=obs_labels, columns=obs_labels)
        df_wk.index.name = 'Kab/Kota'; df_wk = df_wk.reset_index()
        intra_score_dicts[fr"Matriks Intra-Skor \mathbf{{W}}_{{{yr}}}"] = df_wk.to_dict('records')

        # 2. Skor Intra F_k (Trajectory Objek)
        # Skenario 1: Fk = Wk * D^{1/2} * P * Lambda^{-1/2}
        # Skenario 2: Fk = Zk * Vc
        if scenario == 'scenario1':
            Fk_val = Ws[i] @ D_sqrt @ eig_vecs_c[:, :2] / np.clip(sq2, 1e-12, None)
        else:
            Fk_val = per_year_coords[yr][:, :2]
            
        df_fk = pd.DataFrame(np.round(Fk_val, 6), index=obs_labels, columns=['PC1', 'PC2'])
        df_fk.index.name = 'Kab/Kota'; df_fk = df_fk.reset_index()
        intra_score_dicts[fr"Skor Intra \mathbf{{F}}_{{{yr}}}"] = df_fk.to_dict('records')
        
        # 3. Loading Intra G_k (Trajectory Variabel)
        # Skenario 1: Gk = Zk^T * D * Fc * Lambda^{-1/2} (Cross-Projection)
        # Skenario 2: Gk = Sk * Vc * Lambda^{-1/2} (Direct Projection - Dual STATIS)
        if scenario == 'scenario1':
            Gk_val = X_matrices[i].T @ D_diag_mat @ scores_raw / np.clip(sq2, 1e-12, None)
        else:
            # Hitung Sk untuk tahun i
            Sk_i = X_matrices[i].T @ D_diag_mat @ X_matrices[i]
            Gk_val = Sk_i @ Vc_vars[:, :2] / np.clip(sq_s, 1e-12, None)
            
        df_gk = pd.DataFrame(np.round(Gk_val, 6), index=selected_vars_final, columns=['PC1', 'PC2'])
        df_gk.index.name = 'Variabel'; df_gk = df_gk.reset_index()
        intra_score_dicts[fr"Loading Intra \mathbf{{G}}_{{{yr}}}"] = df_gk.to_dict('records')

        # 4. Matriks Intra-Loading S_k
        Sk_full = X_matrices[i].T @ D_diag_mat @ X_matrices[i]
        df_sk_intra = pd.DataFrame(np.round(Sk_full, 6), index=selected_vars_final, columns=selected_vars_final)
        df_sk_intra.index.name = 'Variabel'; df_sk_intra = df_sk_intra.reset_index()
        intra_score_dicts[fr"Matriks Intra-Loading \mathbf{{S}}_{{{yr}}}"] = df_sk_intra.to_dict('records')

    res = {
        'scenario': scenario,
        'R': R_W.tolist(), 'H': H_W.tolist(), 'alphas': alphas.tolist(), 'eig_vals_c': eig_vals_c.tolist(), 'scores': scores_raw.tolist(),
        'obs_labels': obs_labels, 'selected_vars': selected_vars_final, 'loadings': loadings.tolist(),
        'scores_svd': scores_svd.tolist(),
        'loadings_svd': loadings_svd.tolist(),
        'intra_score_svd': intra_score_svd_dict,
        'intra_load_svd': intra_load_svd_dict,
        'per_year_coords': {y: v.tolist() for y, v in per_year_coords.items()}, 'sheet_names': sheet_names,
        'X_matrices': [x.tolist() for x in X_matrices], 'vals_R_sorted': vals_R_sorted.tolist(),
        'vals_H_sorted': vals_H_sorted.tolist(), 'k': k,
        'm_weights': m_weights.tolist(),   # Bobot demografis m_i (konstan lintas tahun)
        r'Dataset Asli (\mathbf{X})': df_dataset.to_dict('records'),
        r'Bobot (\alpha)': df_alphas.to_dict('records'),
        r'Bobot Alpha (Wilayah) (\alpha_W)': df_alphas.to_dict('records') if scenario == 'scenario1' else pd.DataFrame({'Tahun': sheet_names, 'Bobot (Alpha)': [round(a, 4) for a in p1_W / p1_W.sum()]}).to_dict('records'),
        r'Bobot Alpha (Indikator) (\alpha_S)': df_alphas.to_dict('records') if scenario == 'scenario2' else pd.DataFrame({'Tahun': sheet_names, 'Bobot (Alpha)': [round(a, 4) for a in p1_S / p1_S.sum()]}).to_dict('records'),
        r'Nilai Eigen (\Lambda_c)': df_eigen.to_dict('records'),
        r'Skor Kompromi (F_c)': df_Fc.to_dict('records'),
        r'Loadings Kompromi (G_c)': df_Gc.to_dict('records'),
        r'Vektor Eigen (Kompas Wilayah) (\mathbf{P}_W)': df_V_W.to_dict('records'),
        r'Vektor Eigen (Kompas Indikator) (\mathbf{P}_S)': df_V_S.to_dict('records'),
        r'Matriks Interstruktur (Wilayah) (\mathbf{H}_W)': df_H_W.to_dict('records'),
        r'Matriks Interstruktur (Indikator) (\mathbf{H}_S)': df_H_S.to_dict('records'),
        r'Matriks Koefisien RV (Wilayah) (\mathbf{R}_W)': df_R.to_dict('records'),
        r'Matriks Koefisien RV (Indikator) (\mathbf{R}_S)': df_RS.to_dict('records'),
        r'Matriks Kompromi (\mathbf{W}_c)': df_Wc.to_dict('records'),
        r'Matriks Kompromi Variabel (\mathbf{S}_c)': df_Sc.to_dict('records')
    }
    res.update(intra_score_dicts)
    
    # [FINAL ROBUSTNESS] Pastikan tidak ada NaN/Inf yang merusak JSON dcc.Store
    def _clean_dict(d):
        for k, v in d.items():
            if isinstance(v, list):
                d[k] = np.nan_to_num(v).tolist()
            elif isinstance(v, dict):
                _clean_dict(v)
        return d
    
    return _clean_dict(res)


# ================================================================
# SIMULASI: Perbandingan Inisialisasi K-Means
# ================================================================

_DEFAULT_VARS = [
    'IPM','AHH_L','AHH_P','RLS','PDRB_ADHK',
    'TPAK','TPT','PPM','GK','GR','IPG','PKKP'
]
_PALETTE = ['#e74c3c','#f39c12','#27ae60','#2980b9','#8e44ad','#16a085']
_CARD = {
    'backgroundColor': 'white', 'borderRadius': '8px',
    'padding': '20px', 'marginBottom': '16px',
    'boxShadow': '0 2px 6px rgba(0,0,0,0.15)'
}


def _stat_box(title, value, color):
    return html.Div([
        html.Div(value, style={'fontSize': '28px', 'fontWeight': 'bold', 'color': color}),
        html.Div(title, style={'fontSize': '12px', 'color': '#666', 'marginTop': '2px'}),
    ], style={
        'backgroundColor': '#f8f9fa', 'border': f'2px solid {color}',
        'borderRadius': '8px', 'padding': '12px 18px',
        'minWidth': '130px', 'textAlign': 'center'
    })


def _yr_scatter(years, yr_labels, yr_centers, per_year_coords, obs_labels, n_clusters):
    """Per-year F_k scatter plots showing seeded centroids (Method B)."""
    figs = []
    for yr in years:
        Fk  = per_year_coords[yr]
        lbl = yr_labels[yr]
        fig = go.Figure()
        for c in range(n_clusters):
            mask = lbl == c
            fig.add_trace(go.Scatter(
                x=Fk[mask, 0], y=Fk[mask, 1], mode='markers',
                text=[obs_labels[i] for i in range(len(obs_labels)) if mask[i]],
                hovertemplate='%{text}<extra></extra>',
                marker=dict(color=_PALETTE[c], size=8, line=dict(width=1, color='white')),
                name=f'Klaster {c+1}'
            ))
        ctrs = yr_centers[yr]
        for c in range(n_clusters):
            fig.add_trace(go.Scatter(
                x=[ctrs[c, 0]], y=[ctrs[c, 1]], mode='markers',
                marker=dict(symbol='x', size=14, color=_PALETTE[c],
                            line=dict(width=3, color='black')),
                showlegend=False,
                hovertemplate=f'Centroid Klaster {c+1}<extra></extra>'
            ))
        fig.update_layout(
            title=f'Tahun {yr}',
            xaxis_title='PC1', yaxis_title='PC2',
            height=300, showlegend=(yr == years[0]),
            margin=dict(t=40, b=30, l=30, r=10), legend_title='Klaster'
        )
        col_w = f'{100 // min(len(years), 3)}%'
        figs.append(html.Div(
            dcc.Graph(figure=fig, config={'displayModeBar': False}),
            style={'width': col_w, 'display': 'inline-block', 'verticalAlign': 'top'}
        ))
    return html.Div([
        html.H4('Klaster Tahunan F_k — Seed untuk Metode B',
                style={'marginTop': 0, 'marginBottom': '6px'}),
        html.P(
            'Tanda ✕ hitam = centroid klaster yang digunakan sebagai inisialisasi trajektori.',
            style={'color': '#666', 'fontSize': '13px', 'marginTop': 0}
        ),
        html.Div(figs),
    ], style=_CARD)


def _diff_table(df_cmp, n_diff, n_clusters):
    from dash import dash_table as _dt
    tbl = df_cmp[['Wilayah', 'Metode A', 'Metode B', 'Status']].copy()
    tbl = tbl.sort_values('Status', ascending=False)
    cond = [
        {'if': {'filter_query': '{Status} = "⚡ Berbeda"'},
         'backgroundColor': '#fff3cd', 'fontWeight': 'bold'},
    ] + [
        {'if': {'filter_query': f'{{Metode A}} = "Klaster {c+1}"', 'column_id': 'Metode A'},
         'color': _PALETTE[c], 'fontWeight': 'bold'}
        for c in range(n_clusters)
    ] + [
        {'if': {'filter_query': f'{{Metode B}} = "Klaster {c+1}"', 'column_id': 'Metode B'},
         'color': _PALETTE[c], 'fontWeight': 'bold'}
        for c in range(n_clusters)
    ]
    return html.Div([
        html.H4(
            f'Tabel Perbandingan Klaster ({n_diff} dari {len(df_cmp)} wilayah berbeda)',
            style={'marginTop': 0}
        ),
        html.P(
            'Latar kuning = wilayah dengan klaster berbeda antara Metode A dan Metode B.',
            style={'color': '#666', 'fontSize': '13px', 'marginTop': 0}
        ),
        _dt.DataTable(
            data=tbl.to_dict('records'),
            columns=[{'name': c, 'id': c} for c in tbl.columns],
            style_table={'overflowX': 'auto'},
            style_header={
                'backgroundColor': '#1a1a2e', 'color': 'white',
                'fontWeight': 'bold', 'textAlign': 'center'
            },
            style_cell={'textAlign': 'left', 'padding': '8px 12px', 'fontSize': '13px'},
            style_data_conditional=cond,
            page_size=35, sort_action='native', filter_action='native',
        ),
    ], style=_CARD)


# ----------------------------------------------------------------
# Layout
# ----------------------------------------------------------------
app.layout = html.Div([
    html.Div([
        html.H2(
            'Simulasi: Inisialisasi K-Means Berbasis Centroid STATIS',
            style={'color': 'white', 'marginBottom': '6px', 'marginTop': 0}
        ),
        html.P(
            'Perbandingan K-Means standar (acak, n_init=10) vs. '
            'K-Means tersemai (centroid klaster tahunan STATIS terbobot).',
            style={'color': '#ccc', 'marginTop': 0, 'fontSize': '14px'}
        ),
    ], style={
        **_CARD,
        'background': 'linear-gradient(135deg,#1a1a2e 0%,#16213e 100%)',
        'color': 'white'
    }),

    html.Div([
        html.H4('Konfigurasi', style={'marginTop': 0, 'marginBottom': '14px'}),

        dcc.Upload(
            id='up-sim',
            children=html.Div(['📂 Klik atau seret file Excel di sini']),
            style={
                'lineHeight': '54px', 'borderWidth': '2px', 'borderStyle': 'dashed',
                'borderRadius': '8px', 'textAlign': 'center', 'borderColor': '#4a90d9',
                'color': '#4a90d9', 'cursor': 'pointer', 'marginBottom': '10px',
                'fontWeight': '500'
            },
            multiple=False
        ),
        html.Div(id='up-status',
                 style={'fontSize': '12px', 'color': '#888', 'marginBottom': '14px'}),

        html.Div([
            html.Div([
                html.Label('Tahun / Sheet (pisah koma):',
                           style={'fontWeight': '500', 'display': 'block', 'marginBottom': '4px'}),
                dcc.Input(
                    id='inp-sheets', value='2020,2021,2022,2023,2024', type='text',
                    style={'width': '100%', 'padding': '6px',
                           'borderRadius': '4px', 'border': '1px solid #ccc'}
                ),
            ], style={'width': '32%', 'display': 'inline-block',
                      'paddingRight': '12px', 'verticalAlign': 'top'}),

            html.Div([
                html.Label('Skenario STATIS:',
                           style={'fontWeight': '500', 'display': 'block', 'marginBottom': '4px'}),
                dcc.RadioItems(
                    id='dd-scenario',
                    options=[
                        {'label': ' Skenario 1 — ACT Klasik (Host = Wilayah)',
                         'value': 'scenario1'},
                        {'label': ' Skenario 2 — Dual STATIS (Host = Indikator)',
                         'value': 'scenario2'},
                    ],
                    value='scenario1', inline=False,
                    style={'fontSize': '13px', 'lineHeight': '1.8'}
                ),
            ], style={'width': '40%', 'display': 'inline-block',
                      'paddingRight': '12px', 'verticalAlign': 'top'}),

            html.Div([
                html.Label('Jumlah Klaster (K):',
                           style={'fontWeight': '500', 'display': 'block', 'marginBottom': '4px'}),
                dcc.Input(
                    id='inp-k', value='3', type='number', min=2, max=6,
                    style={'width': '60px', 'padding': '6px',
                           'borderRadius': '4px', 'border': '1px solid #ccc'}
                ),
            ], style={'width': '20%', 'display': 'inline-block', 'verticalAlign': 'top'}),
        ], style={'marginBottom': '14px'}),

        html.Div([
            html.Label('Variabel Analisis:',
                       style={'fontWeight': '500', 'display': 'block', 'marginBottom': '6px'}),
            dcc.Checklist(
                id='chk-vars',
                options=[{'label': f' {v}', 'value': v} for v in _DEFAULT_VARS],
                value=_DEFAULT_VARS, inline=True,
                style={'fontSize': '13px', 'lineHeight': '2.2'}
            ),
        ], style={'marginBottom': '14px'}),

        html.Button('▶  JALANKAN SIMULASI', id='btn-run', n_clicks=0, style={
            'backgroundColor': '#4a90d9', 'color': 'white', 'border': 'none',
            'padding': '10px 30px', 'borderRadius': '6px', 'fontSize': '14px',
            'fontWeight': '600', 'cursor': 'pointer'
        }),
    ], style=_CARD),

    dcc.Loading(
        id='loading-sim', type='circle',
        children=html.Div(id='sim-out', style={'minHeight': '100px'})
    ),
], style={
    'maxWidth': '1300px', 'margin': '0 auto', 'padding': '28px 20px',
    'fontFamily': '"Segoe UI", Roboto, sans-serif', 'backgroundColor': '#f0f2f5'
})


# ----------------------------------------------------------------
# Callbacks
# ----------------------------------------------------------------
@app.callback(Output('up-status', 'children'), Input('up-sim', 'filename'))
def _show_fname(fname):
    return f'✓ File dimuat: {fname}' if fname else 'Belum ada file dipilih.'


@app.callback(
    Output('sim-out', 'children'),
    Input('btn-run', 'n_clicks'),
    State('up-sim', 'contents'),
    State('up-sim', 'filename'),
    State('inp-sheets', 'value'),
    State('chk-vars', 'value'),
    State('dd-scenario', 'value'),
    State('inp-k', 'value'),
    prevent_initial_call=True,
)
def run_simulation(n_clicks, contents, filename, sheets_str, sel_vars, scenario, k_str):
    if not contents:
        return html.Div('⚠ Upload file Excel terlebih dahulu.',
                        style={'color': '#d9534f', 'padding': '20px'})
    if not sel_vars or len(sel_vars) < 2:
        return html.Div('⚠ Pilih minimal 2 variabel.',
                        style={'color': '#d9534f', 'padding': '20px'})

    n_clusters  = max(2, int(k_str or 3))
    sheet_names = [s.strip() for s in sheets_str.split(',') if s.strip()]

    try:
        res = run_statis_core(contents, sel_vars, sheet_names, scenario=scenario)
    except Exception as e:
        return html.Div(f'Error STATIS: {e}', style={'color': '#d9534f', 'padding': '20px'})

    alphas   = np.array(res['alphas'])
    years    = res['sheet_names']
    obs_labels = res['obs_labels']
    scores_c = np.array(res['scores'])   # (n_obs, 2) compromise space

    per_year_coords = {yr: np.array(v) for yr, v in res['per_year_coords'].items()}

    n_obs   = len(obs_labels)
    n_years = len(years)

    # Build weighted trajectory matrix X_traj  (n_obs x n_years*2)
    X_traj = np.zeros((n_obs, n_years * 2))
    for i, yr in enumerate(years):
        Fk = per_year_coords[yr]
        X_traj[:, i*2:(i+1)*2] = np.sqrt(alphas[i]) * Fk

    # ============================================================
    # METODE A: K-Means acak standar (n_init=10, random_state=42)
    # ============================================================
    km_A     = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    labels_A = km_A.fit_predict(X_traj)

    # ============================================================
    # METODE B: Centroid-seeded dari klaster tahunan STATIS
    # Langkah 1 — K-Means per tahun pada F_k, align label lintas tahun
    # ============================================================
    yr_labels  = {}
    yr_centers = {}

    for i, yr in enumerate(years):
        Fk = per_year_coords[yr]
        km_yr = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
        km_yr.fit(Fk)
        lbl = km_yr.labels_
        ctr = km_yr.cluster_centers_

        if i == 0:
            yr_labels[yr]  = lbl.copy()
            yr_centers[yr] = ctr.copy()
        else:
            prev_ctr = yr_centers[years[i - 1]]
            cost = np.linalg.norm(
                prev_ctr[:, None, :] - ctr[None, :, :], axis=2
            )
            row_ind, col_ind = linear_sum_assignment(cost)
            mapping = {col_ind[r]: r for r in range(n_clusters)}
            yr_labels[yr]  = np.array([mapping[l] for l in lbl])
            yr_centers[yr] = ctr[col_ind]

    # Langkah 2 — Matriks inisialisasi (n_clusters x n_years*2)
    init_matrix = np.zeros((n_clusters, n_years * 2))
    for c in range(n_clusters):
        for i, yr in enumerate(years):
            mu_ck = yr_centers[yr][c]
            init_matrix[c, i*2:(i+1)*2] = np.sqrt(alphas[i]) * mu_ck

    # Langkah 3 — K-Means seeded, n_init=1
    km_B       = KMeans(n_clusters=n_clusters, init=init_matrix, n_init=1, random_state=42)
    labels_B_r = km_B.fit_predict(X_traj)

    # Align label B ke label A (maximize overlap)
    cost_AB = np.zeros((n_clusters, n_clusters))
    for a in range(n_clusters):
        for b in range(n_clusters):
            cost_AB[a, b] = -np.sum((labels_A == a) & (labels_B_r == b))
    _, col_AB = linear_sum_assignment(cost_AB)
    map_AB   = {col_AB[r]: r for r in range(n_clusters)}
    labels_B = np.array([map_AB[l] for l in labels_B_r])

    # ============================================================
    # DataFrame perbandingan
    # ============================================================
    diff_mask = labels_A != labels_B
    n_diff    = int(diff_mask.sum())

    df_cmp = pd.DataFrame({
        'Wilayah' : obs_labels,
        'PC1'     : scores_c[:, 0],
        'PC2'     : scores_c[:, 1],
        'Metode A': [f'Klaster {l+1}' for l in labels_A],
        'Metode B': [f'Klaster {l+1}' for l in labels_B],
        'Status'  : ['⚡ Berbeda' if d else '—' for d in diff_mask],
    })

    # Scatter plot helper
    def _scatter(title, labels, highlight_diff=False):
        fig = go.Figure()
        for c in range(n_clusters):
            mask = labels == c
            fig.add_trace(go.Scatter(
                x=df_cmp.loc[mask, 'PC1'], y=df_cmp.loc[mask, 'PC2'],
                mode='markers+text', name=f'Klaster {c+1}',
                text=df_cmp.loc[mask, 'Wilayah'],
                textposition='top center', textfont=dict(size=7),
                marker=dict(color=_PALETTE[c], size=9, line=dict(width=1, color='white')),
            ))
        if highlight_diff and n_diff > 0:
            dr = df_cmp[diff_mask]
            fig.add_trace(go.Scatter(
                x=dr['PC1'], y=dr['PC2'], mode='markers',
                name='⚡ Berbeda dari A',
                marker=dict(symbol='star', size=16, color='rgba(0,0,0,0)',
                            line=dict(width=2, color='black')),
            ))
        fig.update_layout(
            title=title, xaxis_title='PC1 Kompromi', yaxis_title='PC2 Kompromi',
            height=500, legend_title='Klaster', margin=dict(t=50, b=40, l=50, r=20),
        )
        return fig

    fig_A = _scatter('Metode A — Inisialisasi Acak (n_init=10)', labels_A)
    fig_B = _scatter(
        'Metode B — Seeded dari Centroid Tahunan STATIS', labels_B,
        highlight_diff=True
    )

    inertia_delta = km_B.inertia_ - km_A.inertia_
    pct_diff_obs  = 100 * n_diff / n_obs if n_obs > 0 else 0

    def _hex_rgba(hex_c, alpha=0.5):
        h = hex_c.lstrip('#')
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f'rgba({r},{g},{b},{alpha})'

    # Sankey: aliran klaster A -> B
    source, target, value_s, link_color = [], [], [], []
    for a in range(n_clusters):
        for b in range(n_clusters):
            cnt = int(np.sum((labels_A == a) & (labels_B == b)))
            if cnt > 0:
                source.append(a)
                target.append(n_clusters + b)
                value_s.append(cnt)
                link_color.append(_hex_rgba(_PALETTE[a]))
    node_labels = (
        [f'A: Klaster {c+1}' for c in range(n_clusters)] +
        [f'B: Klaster {c+1}' for c in range(n_clusters)]
    )
    fig_sankey = go.Figure(go.Sankey(
        node=dict(
            label=node_labels,
            color=[_PALETTE[c] for c in range(n_clusters)] * 2,
            pad=18, thickness=22
        ),
        link=dict(source=source, target=target, value=value_s, color=link_color),
    ))
    fig_sankey.update_layout(
        title='Aliran Klaster: Metode A → Metode B',
        height=300, margin=dict(t=40, b=20, l=20, r=20)
    )

    interp_text = (
        'Metode B menghasilkan inertia lebih rendah → solusi lebih kompak.'
        if inertia_delta < 0 else
        'Metode A menghasilkan inertia lebih rendah pada ruang trajektori.'
    )

    return html.Div([
        # Summary cards
        html.Div([
            html.H4('Ringkasan Simulasi', style={'marginTop': 0}),
            html.Div([
                _stat_box('Wilayah', str(n_obs), '#4a90d9'),
                _stat_box('Berbeda', str(n_diff),
                          '#d9534f' if n_diff else '#5cb85c'),
                _stat_box('% Berbeda', f'{pct_diff_obs:.1f}%',
                          '#f0ad4e' if n_diff else '#5cb85c'),
                _stat_box('Inertia A', f'{km_A.inertia_:.2f}', '#888'),
                _stat_box('Inertia B', f'{km_B.inertia_:.2f}', '#888'),
                _stat_box('ΔInertia', f'{inertia_delta:+.2f}',
                          '#27ae60' if inertia_delta < 0 else '#e74c3c'),
            ], style={'display': 'flex', 'gap': '12px', 'flexWrap': 'wrap'}),
            html.P(
                interp_text + f' Terdapat {n_diff} wilayah ({pct_diff_obs:.1f}%)'
                              f' dengan klaster berbeda.',
                style={'marginTop': '12px', 'marginBottom': 0,
                       'color': '#444', 'fontSize': '13px'}
            ),
        ], style=_CARD),

        # Scatter side-by-side
        html.Div([
            html.H4('Ruang Kompromi STATIS', style={'marginTop': 0, 'marginBottom': '10px'}),
            html.Div([
                html.Div(dcc.Graph(figure=fig_A),
                         style={'width': '50%', 'display': 'inline-block'}),
                html.Div(dcc.Graph(figure=fig_B),
                         style={'width': '50%', 'display': 'inline-block'}),
            ]),
        ], style=_CARD),

        # Sankey
        html.Div([
            html.H4('Aliran Klaster (Sankey)', style={'marginTop': 0}),
            dcc.Graph(figure=fig_sankey, config={'displayModeBar': False}),
        ], style=_CARD),

        # Per-year scatter
        _yr_scatter(years, yr_labels, yr_centers, per_year_coords, obs_labels, n_clusters),

        # Difference table
        _diff_table(df_cmp, n_diff, n_clusters),
    ])


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7861, debug=True)
