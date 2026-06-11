"""
export_elbow.py
===============
Script khusus untuk menghasilkan ulang Elbow Plot per tahun dengan
label nilai SSE (bawah titik) dan Silhouette (atas titik) untuk
kedua skenario STATIS.

Cara pakai:
    python export_elbow.py --real
    python export_elbow.py --sampel
"""

import sys
import os
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

sys.stdout.reconfigure(encoding='utf-8')

from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

# ── Config ──────────────────────────────────────────────────────────────────
is_real   = '--real'   in sys.argv
is_sampel = '--sampel' in sys.argv

if not is_real and not is_sampel:
    print("Gunakan flag --real atau --sampel")
    sys.exit(1)

config_path = (r'd:\Skripsi\my\debug\export_real.json'   if is_real
               else r'd:\Skripsi\my\debug\export_sample.json')

with open(config_path, 'r', encoding='utf-8') as f:
    cfg = json.load(f)

DATA_PATH     = cfg['excel_path']
SELECTED_VARS = cfg['variables']
SHEET_NAMES   = cfg['sheets']
ROOT_OUT_DIR  = cfg['output_dir']
_JP_NAMES     = ['JP', 'Jumlah Penduduk', 'jumlah_penduduk', 'jumlah penduduk']

# ── Load data ────────────────────────────────────────────────────────────────
tables_raw, jp_raw = {}, {}
for yr in SHEET_NAMES:
    df = pd.read_excel(DATA_PATH, sheet_name=yr, index_col=1)
    df.index.name = 'Kab/Kota'
    df = df.select_dtypes(include=[np.number])
    tables_raw[yr] = df
    for jpc in _JP_NAMES:
        if jpc in df.columns:
            jp_raw[yr] = df[jpc].to_dict(); break

obs_labels = tables_raw[SHEET_NAMES[0]].index.tolist()
n = len(obs_labels)

# ── Demographic weights ──────────────────────────────────────────────────────
_jp_arrays = []
for yr in SHEET_NAMES:
    if yr in jp_raw:
        jp_y = np.array([jp_raw[yr].get(idx, np.nan) for idx in obs_labels], dtype=float)
        if not np.any(np.isnan(jp_y)) and np.all(jp_y > 0):
            _jp_arrays.append(jp_y)
JP_mean   = np.array(_jp_arrays).mean(axis=0) if _jp_arrays else np.ones(n)
m_weights = JP_mean / JP_mean.sum()
D_sqrt    = np.diag(np.sqrt(m_weights))
D_inv_sqrt = np.diag(1.0 / np.sqrt(m_weights))
D_diag    = np.diag(m_weights)

# ── STATIS weighted Z-score matrices ─────────────────────────────────────────
X_matrices, Ws, Ss = [], [], []
for s in SHEET_NAMES:
    arr     = tables_raw[s][SELECTED_VARS].values.astype(float)
    mu      = m_weights @ arr
    centered = arr - mu
    sigma   = np.sqrt(np.clip(m_weights @ (centered ** 2), 1e-12, None))
    Z_k     = centered / sigma
    X_matrices.append(Z_k)
    Ws.append(Z_k @ Z_k.T)            # scenario1: n×n outer product
    Ss.append(Z_k.T @ D_diag @ Z_k)   # scenario2: p×p covariance

# ── Alpha helper ─────────────────────────────────────────────────────────────
def calc_H(mats, k, D=None):
    H = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            H[i, j] = (np.trace(mats[i] @ D @ mats[j] @ D)
                       if D is not None else np.trace(mats[i] @ mats[j]))
    return H

def get_alpha(H):
    vals, vecs = np.linalg.eig(H)
    idx = np.argsort(np.real(vals))[::-1][0]
    vec = np.real(vecs[:, idx])
    if vec.sum() < 0: vec = -vec
    return vec / vec.sum()

k_time = len(SHEET_NAMES)
alphas_W = get_alpha(calc_H(Ws, k_time, D=D_diag))
alphas_S = get_alpha(calc_H(Ss, k_time))

# ── Scenario 1: per-year coords (n × 2) ─────────────────────────────────────
Wc = sum(a * W for a, W in zip(alphas_W, Ws))
Wc_weighted = D_sqrt @ Wc @ D_sqrt
P1, Lam1, _ = np.linalg.svd(Wc_weighted)
idxc1 = np.argsort(Lam1)[::-1]
eig_vals1, eig_vecs1 = Lam1[idxc1], P1[:, idxc1]
sq2_1 = np.sqrt(np.clip(eig_vals1[:2], 1e-12, None))

def coords_s1(i):
    return Ws[i] @ D_sqrt @ eig_vecs1[:, :2] / sq2_1

# ── Scenario 2: per-year coords (n × 2) ─────────────────────────────────────
Sc = sum(a * S for a, S in zip(alphas_S, Ss))
U2, S2, _ = np.linalg.svd(Sc)
idxc2 = np.argsort(S2)[::-1]
eig_vecs2 = U2[:, idxc2]          # p × p (variable eigenvectors)
Vc_vars    = eig_vecs2[:, :2]     # p × 2

def coords_s2(i):
    return X_matrices[i] @ Vc_vars  # n × 2

# ── Save helper ───────────────────────────────────────────────────────────────
def save_png(fig, filename, out_dir, width=800, height=500):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, filename)
    try:
        fig.update_layout(title_x=0.5)
        fig.write_image(path, width=width, height=height, scale=2)
        print(f'  [PNG] {path}')
    except Exception as e:
        print(f'  [WARN] Gagal simpan {filename}: {e}')

# ── Elbow + Silhouette plot builder ──────────────────────────────────────────
def build_elbow_fig(coords, yr, label):
    max_k   = min(11, len(coords) + 1)
    k_range = range(1, max_k)

    inertias = []
    for kk in k_range:
        km = KMeans(n_clusters=kk, random_state=42, n_init=10)
        km.fit(coords)
        inertias.append(km.inertia_)

    sil_ks, sil_vals = [], []
    for kk in range(2, min(max_k, len(coords))):
        km_s  = KMeans(n_clusters=kk, random_state=42, n_init=10)
        lbl_s = km_s.fit_predict(coords)
        sil_ks.append(kk)
        sil_vals.append(round(float(silhouette_score(coords, lbl_s)), 4))

    fig = px.line(
        x=list(k_range), y=inertias, markers=True,
        title=f'Kurva Elbow & Siluet — {label} — Tahun {yr}',
        labels={'x': 'Jumlah Klaster (k)', 'y': 'Inersia (SSE)'},
        color_discrete_sequence=['#1976D2'],
    )
    fig.update_traces(
        text=[f'{v:,.2f}' for v in inertias],
        textposition='bottom center',
        mode='lines+markers+text',
        name='SSE',
        textfont=dict(size=11, color='#1976D2'),
    )
    fig.add_trace(go.Scatter(
        x=sil_ks, y=sil_vals,
        mode='lines+markers+text', name='Siluet',
        line=dict(color='#E53935', width=2, dash='dot'),
        marker=dict(size=8, color='#E53935'),
        text=[f'{v:.3f}' for v in sil_vals],
        textposition='top center',
        textfont=dict(size=11, color='#E53935'),
        yaxis='y2',
    ))
    fig.update_layout(
        template='plotly_white',
        yaxis2=dict(
            title='Koefisien Siluet',
            overlaying='y', side='right',
            range=[0, 1],
        ),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    return fig

# ── Run both scenarios ────────────────────────────────────────────────────────
SCENARIOS = {
    'scenario1': {'label': 'Skenario 1 (Wilayah)', 'coord_fn': coords_s1},
    'scenario2': {'label': 'Skenario 2 (Indikator)', 'coord_fn': coords_s2},
}

for scen, scfg in SCENARIOS.items():
    out_dir = os.path.join(ROOT_OUT_DIR, scen)
    print(f'\n[{scen.upper()}] Memproses elbow plots...')
    for i, yr in enumerate(SHEET_NAMES):
        coords = scfg['coord_fn'](i)
        fig = build_elbow_fig(coords, yr, scfg['label'])
        save_png(fig, f'elbow_plot_{yr}.png', out_dir, width=800, height=500)

print('\n[DONE] Elbow plots diperbarui untuk kedua skenario.')
