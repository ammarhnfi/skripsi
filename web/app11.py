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


# --- GLOBAL MAP INITIALIZATION ---
try:
    print("Sedang membaca Shapefile...")
    # Dynamic shapefile paths to ensure perfect resolution across all local & server environments
    shp_paths = [
        "gadm41_IDN_2.shp",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "gadm41_IDN_2.shp"),
        "D:\\Skripsi\\my\\web\\gadm41_IDN_2.shp",
        "/home/user/app/gadm41_IDN_2.shp"
    ]
    
    gdf = None
    last_error = ""
    for p in shp_paths:
        try:
            # 1. Try loading with pyogrio (preferred engine for speed)
            gdf = gpd.read_file(p, engine="pyogrio")
            print(f"Berhasil memuat Shapefile dengan pyogrio dari: {p}")
            break
        except Exception as e:
            last_error = str(e)
            try:
                # 2. Try loading with fiona (as default fallback)
                gdf = gpd.read_file(p)
                print(f"Berhasil memuat Shapefile dengan fiona dari: {p}")
                break
            except Exception as e2:
                last_error = f"{last_error} | {str(e2)}"
                
    if gdf is None:
        print("Mencoba mengunduh Shapefile dari Hugging Face...")
        import urllib.request
        base_url = "https://huggingface.co/spaces/ammarhnfi/skripsi/resolve/main"
        exts = [".shp", ".shx", ".dbf", ".prj", ".cpg"]
        download_dir = os.path.dirname(os.path.abspath(__file__))
        if not os.access(download_dir, os.W_OK):
            download_dir = "/tmp"
            
        for ext in exts:
            file_url = f"{base_url}/gadm41_IDN_2{ext}"
            local_file = os.path.join(download_dir, f"gadm41_IDN_2{ext}")
            try:
                print(f"Mengunduh {file_url} ke {local_file}")
                urllib.request.urlretrieve(file_url, local_file)
            except Exception as dl_err:
                print(f"Gagal mengunduh {ext}: {dl_err}")
                
        try:
            shp_p = os.path.join(download_dir, "gadm41_IDN_2.shp")
            gdf = gpd.read_file(shp_p, engine="pyogrio")
            print(f"Berhasil memuat Shapefile yang diunduh dengan pyogrio dari: {shp_p}")
        except Exception as e3:
            try:
                shp_p = os.path.join(download_dir, "gadm41_IDN_2.shp")
                gdf = gpd.read_file(shp_p)
                print(f"Berhasil memuat Shapefile yang diunduh dengan fiona dari: {shp_p}")
            except Exception as e4:
                raise Exception(f"Semua jalur, engine, dan download fallback gagal. Error terakhir: {e4}")
    
    print("Mengoptimalkan/Menyederhanakan geometri peta...")
    gdf['geometry'] = gdf['geometry'].simplify(tolerance=0.005, preserve_topology=True)
    
    # Create matching keys (Eksak sesuai GADM)
    def get_raw_name(row):
        return row.get('NAME_2') or row.get('WADMKK') or row.get('NAMOBJ') or row.get('Name') or ""
    
    gdf['id_cocok'] = gdf.apply(get_raw_name, axis=1)
    
    indonesia_geojson = json.loads(gdf.to_json())
    print(f"Peta berhasil dimuat! Total Wilayah: {len(gdf)}")
except Exception as e:
    print(f"Gagal memuat Shapefile: {e}")
    gdf = None
    indonesia_geojson = None

# --- AESTHETIC STYLES ---
math_style = {
    "padding": "24px", 
    "backgroundColor": "#F1F5F9", 
    "borderLeft": "6px solid #2563EB",
    "marginTop": "15px", 
    "borderRadius": "12px", 
    "overflowX": "auto", 
    "fontSize": "19px",
    "boxShadow": "0 4px 6px -1px rgb(0 0 0 / 0.1)"
}
summary_style = {
    "fontWeight": "bold", 
    "cursor": "pointer", 
    "color": "#1E40AF", 
    "fontSize": "18px",
    "padding": "12px 18px", 
    "backgroundColor": "#DBEAFE", 
    "borderRadius": "8px",
    "transition": "all 0.2s ease"
}

def render_step(title, content):
    return html.Div([
        html.H6(title, style={"fontWeight": "bold", "marginTop": "10px", "color": "#1E293B"}),
        dcc.Markdown(children=content, mathjax=True, id=f'math-{hash(content)}')
    ])


def render_diagnostic_formulas(n=None, df_k=None, r_sq=None, q_sq=None, kmo_val=None, kmo_str="", bart_chi=None, bart_p=None, bart_str=""):
    if kmo_val is None:
        return html.Div()

    # --- KMO ---
    kmo_f1 = r"""
$$
KMO = \frac{\sum_{j \neq k} r_{jk}^2}{\sum_{j \neq k} r_{jk}^2 + \sum_{j \neq k} q_{jk}^2} 
$$
"""
    kmo_f2 = fr"""
$$
KMO = \frac{{{r_sq:.4f}}}{{{r_sq:.4f} + {q_sq:.4f}}} 
$$
""" if r_sq is not None else r"""
$$
KMO = \cdots
$$
"""
    kmo_f3 = fr"""
$$
KMO = {kmo_val:.4f} \quad \text{{({kmo_str})}} 
$$
""" if kmo_val is not None else r"""
$$
KMO = \cdots
$$
"""
    
    # --- Bartlett ---
    bart_f1 = r"""
$$
\chi^2 \approx - \left( n - 1 - \frac{2p + 5}{6} \right) \ln |R| 
$$
"""
    if n is not None and df_k is not None:
        bart_f2 = fr"""
$$
\chi^2 \approx - \left( {n} - 1 - \frac{{2({int(df_k)}) + 5}}{{6}} \right) \ln |R| = {bart_chi:.4f} 
$$
""" if bart_chi is not None else r"""
$$
\cdots
$$
"""
    else: 
        bart_f2 = r"""
$$
\chi^2 \approx \cdots
$$
"""

    bart_f3 = fr"""
$$
p = {bart_p} \quad \text{{({bart_str})}} 
$$
""" if bart_p is not None else r"""
$$
p = \cdots
$$
"""

    return html.Div([
        html.Details([
            html.Summary(dcc.Markdown("1. Uji Kaiser-Meyer-Olkin (KMO) Measure of Sampling Adequacy", mathjax=True, style={'display':'inline-block', 'verticalAlign':'middle'}), style=summary_style),
            html.Div([
                html.P("Tujuan: Mengukur kelayakan data untuk analisis multivariat.", style={'fontStyle': 'italic'}),
                render_step("1. General Formula", kmo_f1),
                render_step("2. Substitution", kmo_f2),
                render_step("3. Final Result", kmo_f3),
            ], style=math_style)
        ], style={'marginBottom': '10px', 'marginTop': '10px'}),
        
        html.Details([
            html.Summary(dcc.Markdown("2. Bartlett's Test of Sphericity", mathjax=True, style={'display':'inline-block', 'verticalAlign':'middle'}), style=summary_style),
            html.Div([
                html.P("Tujuan: Menguji apakah matriks korelasi berbeda secara signifikan dari matriks identitas.", style={'fontStyle': 'italic'}),
                render_step("1. General Formula", bart_f1),
                render_step("2. Substitution", bart_f2),
                render_step("3. Final Result", bart_f3),
            ], style=math_style)
        ], style={'marginBottom': '10px'})
    ])

def render_statis_formulas(alpha_vals=None, years=None, w_c_slice=None, inter_rv=None, t1=None, t2=None):
    if alpha_vals is None:
        return html.Div()

    # -- RV --
    rv_f1 = r"""
$$
RV(\mathbf{W}_A, \mathbf{W}_B) = \frac{tr(\mathbf{W}_A \mathbf{W}_B)}{\sqrt{tr(\mathbf{W}_A^2) tr(\mathbf{W}_B^2)}} 
$$
"""
    t_a, t_b = (years[0], years[1]) if years and len(years) > 1 else ("A", "B")
    rv_val = inter_rv[0,1] if (inter_rv is not None and inter_rv.shape[0]>1) else 0.0
    
    rv_f2 = fr"""
$$
RV(\mathbf{{W}}_{{{t_a}}}, \mathbf{{W}}_{{{t_b}}}) = \cdots 
$$
"""
    rv_f3 = fr"""
$$
RV = {rv_val:.4f} 
$$
""" if (inter_rv is not None) else r"""
$$
RV = \cdots 
$$
"""
    
    # -- Wc --
    wc_f1 = r"""
$$
\mathbf{W}_c = \sum_{t=1}^{K} \alpha_t \mathbf{W}_t 
$$
"""
    if alpha_vals is not None and years is not None:
        sub_parts = [fr"({a:.3f}) \mathbf{{W}}_{{{years[i]}}}" for i, a in enumerate(alpha_vals)]
        wc_f2 = fr"""
$$
\mathbf{{W}}_c = {' + '.join(sub_parts)} 
$$
"""
    else: 
        wc_f2 = r"""
$$
\mathbf{W}_c = \alpha_1 \mathbf{W}_1 + \alpha_2 \mathbf{W}_2 \cdots 
$$
"""

    # -- Aproksimasi Wc --
    wc_f3 = r"$$ \mathbf{W}_c \approx \text{N/A} $$"
    if w_c_slice is not None:
        matrix_rows = [" & ".join([f"{float(v):.2f}" for v in r]) for r in w_c_slice]
        # Gunakan EMPAT backslash agar di Markdown tersisa DUA untuk MathJax
        matrix_str = " \\\\\\\\ ".join(matrix_rows)
        # Gunakan block math murni tanpa spasi tambahan
        wc_f3 = r"$$\mathbf{W}_c \approx \begin{bmatrix} " + matrix_str + r" \end{bmatrix}$$"
    else: 
        wc_f3 = r"""
$$
\mathbf{W}_c = \cdots 
$$
"""
    
    return html.Div([
        html.Details([
            html.Summary(dcc.Markdown(r"1. Peta Kemiripan Tahunan (Intra-struktur $\mathbf{W}_t$)", mathjax=True, style={'display':'inline-block', 'verticalAlign':'middle'}), style=summary_style),
            html.Div([
                html.P("Mengubah data z-score mentah menjadi konfigurasi jarak spasial antar wilayah.", style={'fontStyle': 'italic'}),
                render_step("1. General Formula", r"""
$$
\mathbf{W}_t = \mathbf{Z}_t \mathbf{Z}_t^T 
$$
""")
            ], style=math_style)
        ], style={'marginBottom': '10px', 'marginTop': '10px'}),
        
        html.Details([
            html.Summary(dcc.Markdown("2. Hubungan Antar-Tahun ($\\mathbf{H}$, RV, dan Bobot $\\alpha$)", mathjax=True, style={'display':'inline-block', 'verticalAlign':'middle'}), style=summary_style),
            html.Div([
                html.P("Matriks interstruktur $\\mathbf{H}$ memakai produk Hilbert–Schmidt $\\mathrm{tr}(\\mathbf{W}_i \\mathbf{D} \\mathbf{W}_j \\mathbf{D})$; koefisien RV menormalisasi elemen tersebut; bobot $\\alpha$ diambil dari vektor eigen pertama $\\mathbf{H}$ (Lavit 1994).", style={'fontStyle': 'italic'}),
                render_step("1. Koefisien RV (tampilan)", rv_f1),
                render_step("2. Matriks interstruktur", r"""
$$
H_{ij} = \mathrm{tr}(\mathbf{W}_i \mathbf{D} \mathbf{W}_j \mathbf{D}), \qquad \mathbf{H}\mathbf{u} = \theta \mathbf{u}, \quad \alpha_k = \frac{u_{1k}}{\sum_{k'} u_{1k'}}
$$
"""),
                render_step("3. Nilai RV", rv_f3),
            ], style=math_style)
        ], style={'marginBottom': '10px'}),

        html.Details([
            html.Summary(dcc.Markdown(r"3. Matriks Kompromi ($\mathbf{W}_c$)", mathjax=True, style={'display':'inline-block', 'verticalAlign':'middle'}), style=summary_style),
            html.Div([
                html.P("Dihitung sebagai kombinasi linear dari semua matriks W tahunan dikali bobot utamanya.", style={'fontStyle': 'italic'}),
                render_step("1. General Formula", wc_f1),
                render_step("2. Substitution", wc_f2),
                render_step("3. Final Result (Slice 3x3)", wc_f3),
            ], style=math_style)
        ], style={'marginBottom': '10px'}),
        
        html.Details([
            html.Summary(dcc.Markdown("4. Dekomposisi Spektral Kompromi", mathjax=True, style={'display':'inline-block', 'verticalAlign':'middle'}), style=summary_style),
            html.Div([
                html.P("Mendapatkan titik kordinat akhir untuk memetakan objek di grafik Biplot.", style={'fontStyle': 'italic'}),
                render_step("1. General Formula", r"""
$$
\mathbf{W}_c = \mathbf{P} \mathbf{\Lambda}_c \mathbf{P}^T 
$$
"""),
                render_step("2. Final Coordinates", r"""
$$
\mathbf{F}_c = \mathbf{P} \sqrt{\mathbf{\Lambda}_c} 
$$
""")
            ], style=math_style)
        ], style={'marginBottom': '10px'})
    ])

def render_cluster_formulas(moran_i=None, moran_exp=None, n=None, sum_w=None, sum_w_dev=None, sum_dev_sq=None):
    if moran_i is None:
        return html.Div()

    m_f1 = r"""
$$
I = \frac{N}{\sum_i \sum_j w_{ij}} \frac{\sum_i \sum_j w_{ij} (x_i - \bar{x})(x_j - \bar{x})}{\sum_i (x_i - \bar{x})^2} 
$$
"""
    
    if all(v is not None for v in [n, sum_w, sum_w_dev, sum_dev_sq]):
        m_f2 = fr"""
$$
I = \left( \frac{{{n}}}{{{sum_w:.2f}}} \right) \frac{{{sum_w_dev:.2f}}}{{{sum_dev_sq:.2f}}} 
$$
"""
    else: 
        m_f2 = r"""
$$
I = \cdots 
$$
"""
    
    if moran_i is not None and moran_exp is not None:
        m_f3 = fr"""
$$
I_{{obs}} = {moran_i:.4f} \quad \text{{(Ekspektasi: }} {moran_exp:.4f} \text{{)}} 
$$
"""
    else: 
        m_f3 = r"""
$$
I_{{obs}} = \cdots 
$$
"""
    
    return html.Div([
        html.Details([
            html.Summary(dcc.Markdown("1. Global Moran\'s I (Autokorelasi Spasial PC1)", mathjax=True, style={'display':'inline-block', 'verticalAlign':'middle'}), style=summary_style),
            html.Div([
                render_step("1. General Formula", m_f1),
                render_step("2. Substitution", m_f2),
                render_step("3. Final Result", m_f3),
            ], style=math_style)
        ], style={'marginBottom': '10px', 'marginTop': '10px'}),
        
        html.Details([
            html.Summary(dcc.Markdown("2. Fungsi Objektif K-Means", mathjax=True, style={'display':'inline-block', 'verticalAlign':'middle'}), style=summary_style),
            html.Div([
                render_step("1. General Formula", r"""
$$
J = \sum_{j=1}^{k} \sum_{i \in C_j} ||\mathbf{x}_i^{(traj)} - \mathbf{\mu}_j||^2 
$$
""")
            ], style=math_style)
        ], style={'marginBottom': '10px'}),
        
        html.Details([
            html.Summary(dcc.Markdown("3. Jarak Trajektori Spasio-Temporal", mathjax=True, style={'display':'inline-block', 'verticalAlign':'middle'}), style=summary_style),
            html.Div([
                html.P("Mengukur seberapa jauh perbedaan lintas objek sepanjang tahun", style={'fontStyle': 'italic'}),
                render_step("1. General Formula", r"""
$$
d(i,j) = \sqrt{\sum_t (x_{it}-x_{jt})^2} 
$$
""")
            ], style=math_style)
        ], style={'marginBottom': '10px'})
    ])

def render_permutation_formulas(p_val=None, lambda_obs=None, n_perm=None, interpretation=""):
    
    f1 = r"""
$$
P(\lambda \geq \lambda_{obs}) = \frac{\#\{\lambda^* \geq \lambda_{obs}\} + 1}{N_{perm} + 1} 
$$
"""
    
    if p_val is not None and lambda_obs is not None and n_perm is not None:
        count_val = int(round(p_val * (n_perm + 1))) - 1
        f2 = fr"""
$$
P(\lambda \geq {lambda_obs:.4f}) = \frac{{{count_val} + 1}}{{{n_perm} + 1}} = {p_val:.4f} 
$$
"""
    else:
        f2 = r"""
$$
P(\lambda \geq \lambda_{obs}) = \cdots 
$$
"""

    f3 = fr"""
$$
\text{{P-value}} = {p_val:.4f} 
$$
""" if p_val is not None else r"""
$$
\text{P-value} = \cdots 
$$
"""

    decision = ""
    if p_val is not None:
        if p_val < 0.05:
            decision = fr"""
$$
\text{{Keputusan: Tolak }} H_0 \text{{ (Signifikan/Stabil)}} 
$$
"""
        else:
            decision = fr"""
$$
\text{{Keputusan: Gagal Tolak }} H_0 \text{{ (Tidak Signifikan/Acak)}} 
$$
"""

    return html.Div([
        html.Details([
            html.Summary(dcc.Markdown("1. Formula Uji Permutasi", mathjax=True, style={'display':'inline-block', 'verticalAlign':'middle'}), style=summary_style),
            html.Div([
                render_step("1. Probabilitas Empiris", f1)
            ], style=math_style)
        ], style={'marginBottom': '10px', 'marginTop': '10px'}),

        html.Details([
            html.Summary(dcc.Markdown("2. Substitusi & Perhitungan", mathjax=True, style={'display':'inline-block', 'verticalAlign':'middle'}), style=summary_style),
            html.Div([
                render_step("1. Nilai Observasi & Jumlah Sampel", f2)
            ], style=math_style)
        ], style={'marginBottom': '10px'}),

        html.Details([
            html.Summary(dcc.Markdown("3. Hasil Akhir & Keputusan Hipotesis", mathjax=True, style={'display':'inline-block', 'verticalAlign':'middle'}), style=summary_style),
            html.Div([
                render_step("1. Final P-value", f3),
                render_step("2. Kesimpulan Statistik", decision)
            ], style=math_style)
        ], style={'marginBottom': '10px'})
    ])


def render_descriptive_formulas():
    """Returns a collapsible section showing formulas for all descriptive statistics."""
    formulas = {
        "Rata-rata (Mean)": (
            r"""
$$
\bar{x} = \frac{1}{n} \sum_{i=1}^{n} x_i
$$
""",
            "Nilai rata-rata dari seluruh observasi pada setiap variabel."
        ),
        "Simpangan Baku (Std. Dev)": (
            r"""
$$
s = \sqrt{\frac{1}{n-1} \sum_{i=1}^{n} (x_i - \bar{x})^2}
$$
""",
            "Ukuran penyebaran data terhadap rata-ratanya."
        ),
        "Nilai Minimum & Maksimum": (
            r"""
$$
\text{Min} = \min(x_1, \ldots, x_n), \quad \text{Max} = \max(x_1, \ldots, x_n)
$$
""",
            "Nilai terkecil dan terbesar dalam data."
        ),
        "Median (Q2)": (
            r"""
$$
Q_2 = \begin{cases} x_{\left(\frac{n+1}{2}\right)} & n \text{ ganjil} \\ \frac{x_{\left(\frac{n}{2}\right)} + x_{\left(\frac{n}{2}+1\right)}}{2} & n \text{ genap} \end{cases}
$$
""",
            "Nilai tengah data setelah diurutkan."
        ),
        "Kuartil & IQR": (
            r"""
$$
IQR = Q_3 - Q_1
$$
""",
            "Jarak antar-kuartil — ukuran penyebaran yang robust terhadap pencilan."
        ),
        "Skewness (Kemiringan)": (
            r"""
$$
g_1 = \frac{\frac{1}{n}\sum_{i=1}^n (x_i - \bar{x})^3}{s^3}
$$
""",
            "$g_1 > 0$: condong kanan (right-skewed); $g_1 < 0$: condong kiri."
        ),
        "Kurtosis (Keruncingan)": (
            r"""
$$
g_2 = \frac{\frac{1}{n}\sum_{i=1}^n (x_i - \bar{x})^4}{s^4} - 3
$$
""",
            "$g_2 > 0$: lebih runcing dari normal (leptokurtik); $g_2 < 0$: lebih datar (platikurtik)."
        ),
        "Koefisien Variasi (CV)": (
            r"""
$$
CV = \frac{s \text{ atau } \sigma}{\bar{x} \text{ atau } \mu} \times 100\%
$$
""",
            "Ukuran variasi relatif — berguna untuk membandingkan variabelitas antar-variabel bersatuan berbeda."
        ),
        "Bobot Populasi (Weighted Mode)": (
            r"""
$$
m_i = \frac{\overline{V}_i}{\sum_{i=1}^n \overline{V}_i} \quad \text{dimana} \quad \overline{V}_i = \frac{1}{K}\sum_{k=1}^K V_{ik}
$$
""",
            "Bobot demografis wilayah ke-i berdasarkan rata-rata variabel bobot (V) selama K tahun."
        ),
    }

    items = []
    for i, (name, (formula, desc)) in enumerate(formulas.items(), 1):
        items.append(
            html.Details([
                html.Summary(
                    dcc.Markdown(f"{i}. {name}", mathjax=True,
                                 style={'display': 'inline-block', 'verticalAlign': 'middle'}),
                    style=summary_style
                ),
                html.Div([
                    dcc.Markdown(desc, mathjax=True,
                                 style={'fontStyle': 'italic', 'color': '#455A64', 'marginBottom': '5px'}),
                    render_step("Formula", formula)
                ], style=math_style)
            ], style={'marginBottom': '8px'})
        )

    return html.Div(items, style={'marginTop': '20px'})


# ==========================================

# Import Library

COLOR_ACCENT = '#1976D2'




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

# --- Helper untuk Dendrogram ke Plotly ---
# --- Redundant function removed ---

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
        os.makedirs("../output_app", exist_ok=True)
        with open("../output_app/output_core_statis.tex", "w") as f:
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
            


            df = pd.DataFrame(data_list)
            if columns: df = df[columns]
            
            lines = []
            if longtable:
                # LONGTABLE logic
                lines.append(r"\begin{longtable}{|" + "c|"*len(df.columns) + "}")
                lines.append(r"\caption{" + escape_tex(caption) + r"} \label{tab:" + label + r"} \\\\")
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
                    row_str = " & ".join([float_fmt.format(val).replace('.', ',') if isinstance(val, (int, float, np.number)) else escape_tex(val) for val in row])
                    lines.append(row_str + " \\\\")
                
                lines.append(r"\hline")
                lines.append(r"\end{longtable}")
            else:
                # STANDARD TABLE logic
                lines.append(r"\begin{table}[H]")
                lines.append(r"\centering")
                lines.append(r"\caption{" + escape_tex(caption) + r"} \label{tab:" + label + r"}")
                lines.append(r"\begin{tabular}{|" + "c|"*len(df.columns) + "}")
                lines.append(r"\hline")
                # Escape headers
                header = " & ".join([f"\\textbf{{{escape_tex(c)}}}" for c in df.columns]) + " \\\\"
                lines.append(header)
                lines.append(r"\hline")
                
                for _, row in df.iterrows():
                    # Escape row values
                    row_str = " & ".join([float_fmt.format(val).replace('.', ',') if isinstance(val, (int, float, np.number)) else escape_tex(val) for val in row])
                    lines.append(row_str + " \\\\")
                
                lines.append(r"\hline")
                lines.append(r"\end{tabular}")
                lines.append(r"\end{table}")

            # Write to specific file
            os.makedirs("../output_app", exist_ok=True)
            with open(f"../output_app/output_table_{filename}.tex", "w") as f:
                f.write("\n".join(lines))
            print(f"Exported ../output_table_{filename}.tex")

        # 1. Alphas
        write_single_table(res.get(r'Bobot (\alpha)'), "alpha", "Nilai Bobot (Alpha)", "alpha")
        
        # 2. Nilai Eigen
        write_single_table(res.get(r'Nilai Eigen (\Lambda_c)'), "eigen", "Dekomposisi Nilai Eigen", "eigen")
        
        # 3. Matriks H (interstruktur) dan RV
        write_single_table(res.get(r'Matriks Interstruktur Hilbert-Schmidt (\mathbf{H})'), "H_inter", r"Matriks interstruktur $\mathbf{H}$ (tr$(\mathbf{W}_i\mathbf{W}_j)$)", "H_inter")
        write_single_table(res.get(r'Matriks Koefisien RV (\mathbf{R}_{\mathrm{RV}})'), "rv", r"Koefisien RV antar-tahun ($\mathbf{R}_{\mathrm{RV}}$)", "rv")
        
        # 4. Loadings
        write_single_table(res.get(r'Loadings Kompromi (G_c)'), "loadings", "Loadings Kompromi", "loadings")
        
        # 5. Skor (Longtable)
        write_single_table(res.get(r'Skor Kompromi (F_c)'), "scores", "Koordinat Skor Kompromi", "scores", longtable=True)
        
    except Exception as e:
        print(f"Failed to export Split Tables: {e}")

def export_perm_latex(p_val, desc):
    try:
        lines = []
        lines.append(r"% Generated by final.py (Permutation)")
        lines.append(fr"\newcommand{{\statisPValue}}{{{p_val:.4f}}}")
        lines.append(fr"\newcommand{{\statisKet}}{{{desc}}}")
        
        os.makedirs("../output_app", exist_ok=True)
        with open("../output_app/output_perm_statis.tex", "w") as f:
            f.write("\n".join(lines))
        print("LaTeX Perm Exported to ../output_perm_statis.tex!")
    except Exception as e:
        print(f"Failed to export LaTeX Perm: {e}")

# -----------------------------

# PLOT HELPERS (With Visual Scaling)

# -----------------------------
def apply_visual_adjustments(scores, loadings, norm_scores, scale_loadings, singular_values=None):
    """
    Melakukan scaling HANYA untuk plotting, tidak mengubah data tabel.

    Jika `singular_values` diberikan, ikuti saran Abdi et al. (2012):
    - Jika `singular_values` adalah array/iterable dengan 2 elemen, perlakukan
      sebagai [SV_PC1, SV_PC2] global dan kalikan tiap kolom loading dengan
      nilai tersebut.
    - Jika `singular_values` adalah array berukuran (n_loadings, 2), lakukan
      pengalian per-baris (berguna ketika loadings berisi data dari beberapa
      tahun dan tiap baris punya pasangan singular values masing-masing).
    Jika `singular_values` tidak diberikan, jatuhkan ke skema penskalaan
    sebelumnya (rasio magnitudo maksimum) sebagai fallback.
    """
    plot_scores = scores.copy()
    plot_loadings = loadings.copy()

    # 1. Normalize Scores (Optional)
    max_val = None
    if norm_scores:
        max_val = np.max(np.abs(plot_scores))
        if max_val > 0:
            plot_scores = plot_scores / max_val

    # 2. Scale Loadings following Abdi et al. (2012) when possible
    if scale_loadings:
        try:
            if singular_values is not None:
                sv = np.array(singular_values)
                # Case: global singular values for two components
                if sv.ndim == 1 and sv.size >= 2:
                    plot_loadings = plot_loadings.copy()
                    plot_loadings[:, 0] = loadings[:, 0] * sv[0]
                    plot_loadings[:, 1] = loadings[:, 1] * sv[1]
                # Case: per-row singular values (n_rows x 2)
                elif sv.ndim == 2 and sv.shape[1] >= 2 and sv.shape[0] == plot_loadings.shape[0]:
                    plot_loadings = plot_loadings.copy()
                    plot_loadings[:, 0] = loadings[:, 0] * sv[:, 0]
                    plot_loadings[:, 1] = loadings[:, 1] * sv[:, 1]
                else:
                    # Fallback to old heuristic if shape mismatch
                    raise ValueError("singular_values shape not recognized")

                # If scores were normalized, scale loadings to same viewport
                if norm_scores and max_val and max_val > 0:
                    plot_loadings = plot_loadings / max_val
            else:
                # Original heuristic fallback: scale by ratio of maxima
                max_score_mag = np.max(np.abs(plot_scores))
                max_load_mag = np.max(np.abs(plot_loadings))
                if max_load_mag > 0:
                    scale_factor = (max_score_mag / max_load_mag) * 0.8
                    plot_loadings = plot_loadings * scale_factor
        except Exception:
            # On any problem, fallback gracefully to leaving loadings unchanged
            plot_loadings = plot_loadings

    return plot_scores, plot_loadings

def create_biplot(scores, loadings, labels, vars, title, color=COLOR_ACCENT, show_loadings=True, show_points=True, show_arrows=True):
    fig = go.Figure()
    
    # Points
    if show_points:
        fig.add_trace(go.Scatter(x=scores[:,0], y=scores[:,1], mode='markers+text',
                                 text=labels, textposition='top center',
                                 marker=dict(size=8, color=color, opacity=0.8), name='Objek'))
    
    # Vectors
    if show_loadings and len(vars) > 0:
        for i, var in enumerate(vars):
            marker_opts = dict(size=6, symbol='arrow-bar-up') if show_arrows else dict(size=0)
            fig.add_trace(go.Scatter(x=[0, loadings[i,0]], y=[0, loadings[i,1]], 
                                     mode='lines+markers+text', marker=marker_opts,
                                     line=dict(color='#D81B60', width=2), text=[None, var],
                                     textposition='top center', name=f'{var}', 
                                     hoverinfo='text', hovertext=f"<b>{var}</b><br>Loading: ({loadings[i, 0]:.4f}, {loadings[i, 1]:.4f})"))

    fig.update_layout(title=title, xaxis=dict(constrain='domain'), yaxis=dict(scaleanchor='x', scaleratio=1),
                      width=600, height=600, autosize=False, margin=dict(l=40, r=40, t=60, b=40), showlegend=False,
                      template="plotly_white")
    return fig

# -----------------------------
# DATA DIAGNOSTICS HELPERS
# -----------------------------

def calc_kmo_bartlett(df_dict, variables):
    try:
        kmos, p_vals = [], []
        n, p, r_sq, q_sq, chi2_stat = 0, 0, 0, 0, 0
        for sheet, df in df_dict.items():
            if len(variables) < 2: return 0, 1.0, "Need >1 var", "Need >1 var"
            data = df[variables].values
            R = np.corrcoef(data.T)
            
            # KMO
            try:
                inv_R = np.linalg.inv(R)
                D = np.diag(1.0 / np.sqrt(np.diag(inv_R)))
                Q = D @ inv_R @ D
                r_sq = np.sum(R**2) - np.sum(np.diag(R**2))
                q_sq = np.sum(Q**2) - np.sum(np.diag(Q**2))
                kmos.append(r_sq / (r_sq + q_sq) if (r_sq + q_sq) > 0 else 0)
            except: kmos.append(0)
            
            # Bartlett
            n, p = data.shape
            det_R = np.linalg.det(R)
            if det_R > 0:
                chi2_stat = - (n - 1 - (2*p + 5)/6) * np.log(det_R)
                df_chi = p * (p - 1) / 2
                p_val = stats.chi2.sf(chi2_stat, df_chi)
                p_vals.append(p_val)
            else: p_vals.append(1.0)
            
        mean_kmo = np.mean(kmos)
        mean_p = np.mean(p_vals)
        kmo_interp = ("Marvelous (Luar Biasa)" if mean_kmo >= 0.9 else
                      "Meritorious (Sangat Baik)" if mean_kmo >= 0.8 else
                      "Middling (Cukup Baik)" if mean_kmo >= 0.7 else
                      "Mediocre (Biasa)" if mean_kmo >= 0.6 else
                      "Miserable (Buruk, namun dapat diterima)" if mean_kmo >= 0.5 else
                      "Unacceptable (Tidak diterima)")
        bart_interp = "Significant (Suitable)" if mean_p < 0.05 else "Not Significant (Orthogonal)"
        return mean_kmo, mean_p, kmo_interp, bart_interp, n, p, r_sq, q_sq, chi2_stat
    except: return 0.0, 1.0, "Error", "Error", 0, 0, 0, 0, 0

# -----------------------------
# STATIS Core Logic
# -----------------------------
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

def run_permutation_test(X_matrices, k, lambda_obs, n_permutations, m_weights=None):
    # Set seed untuk konsistensi hasil (penting untuk Skripsi)
    np.random.seed(42) 
    dist_lambdas = []
    
    D = None
    if m_weights is not None:
        D = np.diag(m_weights)
    
    for _ in range(n_permutations):
        Ws_perm = []
        for X in X_matrices:
            # Permutasi PER KOLOM secara independen sesuai literatur Abdi et al. 2012
            X_p = np.zeros_like(X)
            for j in range(X.shape[1]):
                X_p[:, j] = np.random.permutation(X[:, j])
            Ws_perm.append(X_p @ X_p.T)
                
        H_perm = _calculate_H_matrix(Ws_perm, k, D=D)
        dist_lambdas.append(_get_first_eigenvalue(H_perm))
    
    dist_lambdas = np.array(dist_lambdas)
    # P-value (dengan koreksi +1 untuk menghindari p=0)
    p_value = (np.sum(dist_lambdas >= lambda_obs) + 1) / (n_permutations + 1)
    return dist_lambdas, p_value


def compute_structure_vector(H, alphas, sheet_names, X_matrices, m_weights, obs_labels,
                              province_map=None, scenario='scenario1'):
    """
    Mengimplementasikan model vektor struktur Areia, Oliveira & Mexia (2008),
    sebagaimana dirangkum dalam Oliveira et al. (2024).

    Model: H = lambda * alpha * alpha^T + E_bar
    Estimator vektor struktur: beta_tilde = lambda_1 * u_1  (vektor eigen pertama H, sebelum normalisasi)

    Parameter
    ----------
    H            : np.ndarray (K x K) — matriks interstruktur Hilbert-Schmidt
    alphas       : np.ndarray (K,)   — bobot kompromi (u_1 ternormalisasi)
    sheet_names  : list[str]         — nama situasi (tahun)
    X_matrices   : list[np.ndarray]  — daftar matriks Z_k terstandarisasi (n x p)
    m_weights    : np.ndarray (n,)   — bobot demografis m_i
    obs_labels   : list[str]         — nama objek (kabupaten/kota)
    province_map : dict[str, list[str]] — {"Banten": [...], "DKI Jakarta": [...], "Jawa Barat": [...]}
                   Jika None, analisis transversal tidak dilakukan.

    Returns
    -------
    dict berisi semua kuantitas inferensial
    """
    K = len(sheet_names)
    H = np.array(H)

    # ----------------------------------------------------------------
    # 1. Eigendekomposisi H (sudah tersedia di run_statis_core, namun
    #    dihitung ulang di sini agar fungsi ini berdiri sendiri)
    # ----------------------------------------------------------------
    vals_H, vecs_H = np.linalg.eig(H)
    vals_H = np.real(vals_H)
    vecs_H = np.real(vecs_H)
    idx_sort = np.argsort(vals_H)[::-1]
    vals_H = vals_H[idx_sort]
    vecs_H = vecs_H[:, idx_sort]

    lambda1 = vals_H[0]               # nilai eigen pertama (skalar kegentingan)
    u1      = vecs_H[:, 0]            # vektor eigen pertama (sebelum normalisasi)

    # Pastikan tanda u1 positif (konvensi: elemen terbesar positif)
    if u1.sum() < 0:
        u1 = -u1

    # 2. Vektor struktur: beta_k = lambda1 * u1_k  (Persamaan eq:beta_vec)
    beta_tilde = lambda1 * u1         # shape (K,)

    # 3. Norm Frobenius H: ||H||_F^2 = tr(H^T H) = tr(H^2) (H simetris)
    H_frobenius_sq = np.trace(H @ H)

    # 4. SS Residual: V = ||H||_F^2 - lambda1^2  (Persamaan eq:ss_residual)
    V = H_frobenius_sq - lambda1**2

    # 5. Inertia dimensi pertama: Inertia_1 = lambda1 / sum(lambda_j)
    #    Gunakan hanya eigenvalue positif untuk keabsahan numerik
    sum_eigenvalues = np.sum(np.clip(vals_H, a_min=0, a_max=None))
    inertia1 = lambda1 / sum_eigenvalues if sum_eigenvalues > 0 else np.nan

    # 6. Rasio dominansi: lambda_1 / lambda_2 (indikator kegentingan)
    dominance_ratio = lambda1 / vals_H[1] if (K > 1 and vals_H[1] > 1e-12) else np.inf

    # ----------------------------------------------------------------
    # 7. Analisis Transversal: Vektor struktur per provinsi
    # ----------------------------------------------------------------
    beta_provinsi = {}
    u1_provinsi = {}
    lambda1_provinsi = {}
    skipped_provinces = []

    if province_map is not None:
        for prov_name, prov_wilayah in province_map.items():
            # Indeks wilayah pada provinsi ini
            # Robust matching
            obs_labels_clean = [str(lab).strip().upper() for lab in obs_labels]
            prov_wilayah_clean = [str(w).strip().upper() for w in prov_wilayah]
            prov_idx = [i for i, lab in enumerate(obs_labels_clean) if lab in prov_wilayah_clean]
            
            if len(prov_idx) < 2:
                skipped_provinces.append(prov_name)
                continue  # Lewati jika terlalu sedikit wilayah

            # Hitung bobot untuk sub-populasi ini (ternormalisasi ulang)
            m_sub = m_weights[prov_idx]
            m_sub_norm = m_sub / m_sub.sum()
            D_sqrt_sub = np.diag(np.sqrt(m_sub_norm))

            # Hitung W_k dan H untuk sub-seri
            if scenario == 'scenario1':
                Ws_sub = []
                for X_k in X_matrices:
                    X_sub = X_k[prov_idx, :]
                    DsqZ = D_sqrt_sub @ X_sub
                    Ws_sub.append(DsqZ @ DsqZ.T)
                H_sub = _calculate_H_matrix(Ws_sub, K)
            else:
                Ss_sub = []
                for X_k in X_matrices:
                    X_sub = X_k[prov_idx, :]
                    S_sub = X_sub.T @ np.diag(m_sub_norm) @ X_sub
                    Ss_sub.append(S_sub)
                H_sub = _calculate_H_matrix(Ss_sub, K)
            vals_sub, vecs_sub = np.linalg.eig(H_sub)
            vals_sub = np.real(vals_sub)
            vecs_sub = np.real(vecs_sub)
            idx_sub = np.argsort(vals_sub)[::-1]
            lambda1_sub = vals_sub[idx_sub[0]]
            u1_sub = vecs_sub[:, idx_sub[0]]
            if u1_sub.sum() < 0:
                u1_sub = -u1_sub
            beta_provinsi[prov_name] = (lambda1_sub * u1_sub).tolist() # Convert to list for JSON
            u1_provinsi[prov_name] = u1_sub.tolist()
            lambda1_provinsi[prov_name] = float(lambda1_sub)

    return {
        'lambda1':         float(lambda1),
        'u1':              u1.tolist(),
        'beta_tilde':      beta_tilde.tolist(),
        'H_frobenius_sq':  float(H_frobenius_sq),
        'V':               float(V),
        'inertia1':        float(inertia1),
        'dominance_ratio': float(dominance_ratio),
        'vals_H':          vals_H.tolist(),
        'sheet_names':     sheet_names,
        'beta_provinsi':   beta_provinsi,   # dict {prov_name: list(K,)}
        'u1_provinsi':     u1_provinsi,     # dict {prov_name: list(K,)}
        'lambda1_provinsi': lambda1_provinsi, # dict {prov_name: float}
        'skipped_provinces': skipped_provinces
    }


def export_structure_vector_latex(sv_res, output_dir="../output_app", label_prefix=""):
    """
    Mengekspor hasil compute_structure_vector ke tabel LaTeX dan grafik PNG.
    Menghasilkan:
      - output_table_beta_vec.tex        : Tabel komponen beta_tilde per tahun
      - output_table_struktur_diagnostik.tex : Tabel diagnostik dominansi
      - output_table_beta_provinsi.tex   : Tabel beta_tilde per provinsi
      - beta_trajectory.png              : Plot lintasan temporal beta_tilde_k
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import re as _re

    os.makedirs(output_dir, exist_ok=True)
    sheet_names  = sv_res['sheet_names']
    beta_tilde   = sv_res['beta_tilde']
    beta_provinsi = sv_res.get('beta_provinsi', {})
    K = len(sheet_names)

    def _tex_table(rows, col_headers, caption, label, filename):
        """Helper: tulis tabel tabular standar ke file .tex."""
        n_cols = len(col_headers)
        lines = []
        lines.append(r"\begin{table}[H]")
        lines.append(r"\centering")
        lines.append(r"\small")
        lines.append(fr"\caption{{{escape_tex(caption)}}} \label{{tab:{label_prefix}{label}}}")
        lines.append(r"\begin{tabular}{|" + "c|" * n_cols + "}")
        lines.append(r"\hline")
        lines.append(" & ".join([fr"\textbf{{{h}}}" for h in col_headers]) + r" \\")
        lines.append(r"\hline")
        for row in rows:
            lines.append(" & ".join([_re.sub(r'(\d)\.(\d)', r'\1,\2', str(v)) for v in row]) + r" \\")
        lines.append(r"\hline")
        lines.append(r"\end{tabular}")
        lines.append(r"\end{table}")
        path = os.path.join(output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"[StrukturVektor] Exported: {path}")

    # --- (A) Tabel komponen beta_tilde ---
    rows_beta = [
        [yr, f"{bt:.4f}"]
        for yr, bt in zip(sheet_names, beta_tilde)
    ]
    _tex_table(
        rows=rows_beta,
        col_headers=["Tahun ($k$)", r"$\tilde{\beta}_k = \lambda_1 u_{1k}$"],
        caption=r"Komponen Vektor Struktur $\tilde{\boldsymbol{\beta}}$ per Situasi Waktu",
        label="beta_vec",
        filename="output_table_beta_vec.tex"
    )

    # --- (B) Tabel diagnostik dominansi ---
    lambda1        = sv_res['lambda1']
    H_frob_sq      = sv_res['H_frobenius_sq']
    V              = sv_res['V']
    inertia1       = sv_res['inertia1']
    dom_ratio      = sv_res['dominance_ratio']
    V_ratio        = V / H_frob_sq if H_frob_sq > 0 else np.nan

    rows_diag = [
        [r"$\lambda_1$ (Nilai Eigen Dominan)",     f"{lambda1:.4f}"],
        [r"$\|\mathbf{H}\|_F^2$ (Frobenius$^2$)",  f"{H_frob_sq:.4f}"],
        [r"$V$ (SS Residual)",                      f"{V:.4f}"],
        [r"$V / \|\mathbf{H}\|_F^2$ (Rasio Sisa)", f"{V_ratio:.4f}"],
        [r"Inertia$_1$ (Dominansi \%)",             f"{inertia1*100:.2f}\\%"],
        [r"$\lambda_1 / \lambda_2$ (Rasio Kegentingan)", f"{dom_ratio:.4f}" if np.isfinite(dom_ratio) else r"$\infty$"],
    ]
    _tex_table(
        rows=rows_diag,
        col_headers=["Kuantitas", "Nilai"],
        caption=r"Diagnostik Dominansi Model Rank-1 (Areia \textit{et al.}, 2008)",
        label="struktur_diagnostik",
        filename="output_table_struktur_diagnostik.tex"
    )

    # --- (C) Tabel beta per provinsi ---
    if beta_provinsi:
        prov_names = list(beta_provinsi.keys())
        col_headers_prov = ["Tahun ($k$)"] + prov_names
        rows_prov = []
        for ki, yr in enumerate(sheet_names):
            row = [yr] + [f"{beta_provinsi[p][ki]:.4f}" if ki < len(beta_provinsi[p]) else "-"
                          for p in prov_names]
            rows_prov.append(row)
        _tex_table(
            rows=rows_prov,
            col_headers=col_headers_prov,
            caption=r"Komponen Vektor Struktur $\tilde{\beta}_{gk}$ per Provinsi (Analisis Transversal)",
            label="beta_provinsi",
            filename="output_table_beta_provinsi.tex"
        )

    # --- (D) Plot lintasan temporal beta_tilde_k ---
    fig, ax = plt.subplots(figsize=(7, 4))
    x_vals = list(range(K))

    ax.plot(x_vals, beta_tilde, marker='o', linewidth=2.0, color='#1976D2',
            markersize=8, label=r'$\tilde{\beta}_k$ (Gabungan)')

    if beta_provinsi:
        colors_prov = ['#D81B60', '#43A047', '#FB8C00']
        for (prov, betas), color in zip(beta_provinsi.items(), colors_prov):
            if len(betas) == K:
                ax.plot(x_vals, betas, marker='s', linewidth=1.5,
                        linestyle='--', color=color, markersize=6,
                        label=fr'$\tilde{{\beta}}_{{gk}}$ {prov}', alpha=0.85)

    ax.set_xticks(x_vals)
    ax.set_xticklabels(sheet_names, fontsize=10)
    ax.set_xlabel("Tahun ($k$)", fontsize=11)
    ax.set_ylabel(r"$\tilde{\beta}_k = \lambda_1 u_{1k}$", fontsize=11)
    ax.set_title(r"Lintasan Temporal Komponen Vektor Struktur $\tilde{\boldsymbol{\beta}}$",
                 fontsize=12, fontweight='bold')
    ax.legend(fontsize=9, loc='best')
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    plot_path = os.path.join(output_dir, "beta_trajectory.png")
    fig.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"[StrukturVektor] Plot saved: {plot_path}")



# -----------------------------
pd.set_option('display.max_columns', None)
scaler = StandardScaler()
pca = PCA(n_components=2)


COLOR_BG_MAIN = '#F0F4F8'
COLOR_CARD_BG = '#FFFFFF'
COLOR_HEADER_TEXT = '#1565C0'
COLOR_ACCENT = '#1976D2'
COLOR_BORDER = '#BBDEFB'
CARD_STYLE = {'boxShadow': '0 2px 5px 0 rgba(0,0,0,0.05)', 'borderRadius': '8px', 'backgroundColor': COLOR_CARD_BG, 'padding': '25px', 'marginBottom': '25px', 'border': f'1px solid {COLOR_BORDER}'}
HEADER_STYLE = {'textAlign': 'center', 'color': COLOR_HEADER_TEXT, 'fontWeight': '700', 'marginBottom': '15px', 'letterSpacing': '0.5px'}
LABEL_STYLE = {'fontWeight': '600', 'color': '#37474F', 'fontSize': '1.4rem', 'marginBottom': '8px'}
BASE_URL = "https://huggingface.co/spaces/ammarhnfi/skripsi/resolve/main"
EXAMPLE_DATASETS = [{"name": "Data Gabungan (Data Final.xlsx)", "url": f"{BASE_URL}/Data Final.xlsx"}]
layout = html.Div(style={'backgroundColor': COLOR_BG_MAIN, 'padding': '30px', 'fontFamily': 'Segoe UI, Roboto, Helvetica, Arial, sans-serif'}, children=[
    dcc.Store(id='global-data-store'), 
    dcc.Store(id='pca-results-store'),
    dcc.Store(id='statis-core-store'), # Menyimpan hasil STATIS lengkap
    dcc.Store(id='descriptive-store'), # Menyimpan hasil statistika deskriptif
    dcc.Store(id='statis-trans-store'), # [NEW] Menyimpan hasil clustering transisi (k-means)
    dcc.Store(id='weighted-trans-store'), # [NEW] Menyimpan hasil clustering transisi terbobot STATIS
    dcc.Store(id='biplot-statis-compare-store'), # [NEW] Menyimpan hasil perbandingan biplot vs statis
    
    # --- HEADER ---
    html.Div(style=CARD_STYLE, children=[
        html.H1('Dashboard Analisis Spasio-Temporal Sosio-Ekonomi', style=HEADER_STYLE),
        html.H2('(Metode STATIS & Dynamic Biplot)', style={'textAlign': 'center', 'color': '#546E7A', 'marginTop': '-10px'}),
        html.H3("Analisis Struktur Ekonomi dan Kesejahteraan Wilayah (STATIS)", style={'textAlign': 'center', 'color': '#78909C', 'fontStyle': 'italic'}),
        html.Div(style={'textAlign': 'center', 'marginTop': '16px'}, children=[
            html.A(
                '🌐 Kunjungi Landing Page Skripsi',
                href='https://skripsi-ammarhnfi.vercel.app/',
                target='_blank',
                style={
                    'display': 'inline-block',
                    'padding': '10px 24px',
                    'backgroundColor': '#1565C0',
                    'color': '#ffffff',
                    'borderRadius': '8px',
                    'textDecoration': 'none',
                    'fontWeight': '700',
                    'fontSize': '14px',
                    'letterSpacing': '0.3px',
                    'boxShadow': '0 2px 8px rgba(21,101,192,0.3)',
                    'transition': 'background 0.2s',
                }
            )
        ])
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

    # --- 2. STATISTIKA DESKRIPTIF ---
    html.Div(style=CARD_STYLE, children=[
        html.H5("Statistika Deskriptif", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
        html.P("Eksplor distribusi dan karakteristik tiap variabel sebelum analisis STATIS.",
               style={'textAlign': 'center', 'color': '#546E7A', 'marginBottom': '15px'}),
        html.Div(style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center',
                         'width': '100%', 'gap': '15px', 'marginBottom': '10px', 'flexWrap': 'wrap'}, children=[
            html.Div([
                html.Label('Pilih Tahun:', style={'fontWeight': 'bold', 'marginRight': '8px'}),
                dcc.Dropdown(
                    id='desc-year-dropdown',
                    placeholder='Pilih tahun ...',
                    style={'width': '150px'}
                ),
            ], style={'display': 'flex', 'alignItems': 'center'}),
            
            html.Div([
                html.Label('Mode Bobot:', style={'fontWeight': 'bold', 'marginRight': '8px'}),
                dcc.RadioItems(
                    id='desc-weight-mode',
                    options=[
                        {'label': ' Tanpa Bobot', 'value': 'unweighted'},
                        {'label': ' Dengan Bobot', 'value': 'weighted'}
                    ],
                    value='unweighted',
                    inline=True,
                    inputStyle={"marginRight": "5px", "marginLeft": "10px"}
                ),
            ], style={'display': 'flex', 'alignItems': 'center'}),

            html.Div(id='desc-weight-var-container', style={'display': 'none', 'alignItems': 'center'}, children=[
                html.Label('Variabel Bobot:', style={'fontWeight': 'bold', 'marginRight': '8px'}),
                dcc.Dropdown(
                    id='desc-weight-var-dropdown',
                    placeholder='Pilih variabel bobot...',
                    style={'width': '180px'}
                ),
            ]),
        ]),

        html.Div(style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center',
                         'width': '100%', 'gap': '10px', 'marginBottom': '10px', 'flexWrap': 'wrap'}, children=[
            html.Label('Exclude Variabel:', style={'fontWeight': 'bold', 'marginRight': '4px', 'whiteSpace': 'nowrap'}),
            dcc.Dropdown(
                id='desc-exclude-vars',
                multi=True,
                placeholder='Pilih variabel yang ingin dikecualikan...',
                style={'minWidth': '280px', 'maxWidth': '600px', 'flex': '1'}
            ),

            html.Button('RUN DESKRIPTIF', id='btn-run-desc', n_clicks=0,
                        style={'backgroundColor': '#00897B', 'color': 'white', 'fontWeight': 'bold',
                               'borderRadius': '5px', 'padding': '0 20px', 'border': 'none', 'height': '38px',
                               'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center',
                               'cursor': 'pointer', 'whiteSpace': 'nowrap'}),
            dcc.Loading(type='circle', color='#00897B', children=html.Div(id='spinner-run-desc'), style={'display': 'inline-block', 'marginLeft': '10px', 'verticalAlign': 'middle', 'width': '30px'})
        ]),
        dcc.Loading(children=[
            html.Div(id='desc-table-output', style={'marginTop': '15px'}),
            html.Div(id='desc-boxplot-output', style={'marginTop': '10px'}),
            html.Div(id='desc-formula-output', style={'marginTop': '20px'}),
            html.Div(id='desc-corr-output', style={'marginTop': '20px'})
        ]),
        # --- Multi-Year View ---
        html.Hr(style={'borderColor': '#BBDEFB', 'marginTop': '25px'}),
        html.Div(style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center',
                         'width': '100%', 'gap': '12px', 'marginBottom': '6px'}, children=[
            html.Span("Perbandingan Antar Tahun", style={'fontWeight': 'bold', 'color': '#37474F', 'fontSize': '15px'}),
            dcc.Dropdown(
                id='desc-multi-stat',
                options=[
                    {'label': 'Mean (Rata-rata)', 'value': 'mean'},
                    {'label': 'Std Dev', 'value': 'std'},
                    {'label': 'Median', 'value': 'median'},
                    {'label': 'Q1 (Kuartil 1)', 'value': 'q1'},
                    {'label': 'Q3 (Kuartil 3)', 'value': 'q3'},
                    {'label': 'Min', 'value': 'min'},
                    {'label': 'Max', 'value': 'max'},
                    {'label': 'Skewness', 'value': 'skewness'},
                    {'label': 'Kurtosis', 'value': 'kurtosis'},
                    {'label': 'CV (%)', 'value': 'cv'},
                ],
                value='mean',
                clearable=False,
                style={'width': '200px', 'minWidth': '200px'}
            ),
            html.Button('TAMPILKAN SEMUA TAHUN', id='btn-run-desc-multi', n_clicks=0,
                        style={'backgroundColor': '#5C6BC0', 'color': 'white', 'fontWeight': 'bold',
                               'borderRadius': '5px', 'padding': '0 15px', 'border': 'none', 'height': '38px',
                               'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center',
                               'cursor': 'pointer', 'whiteSpace': 'nowrap'}),
            dcc.Loading(type='circle', color='#5C6BC0', children=html.Div(id='spinner-run-desc-multi'), style={'display': 'inline-block', 'marginLeft': '10px', 'verticalAlign': 'middle', 'width': '30px'})
        ]),
        html.Div(style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center',
                         'gap': '8px', 'marginBottom': '10px'}, children=[
            html.Span("Skala Y:", style={'fontSize': '13px', 'color': '#546E7A', 'fontWeight': 'bold'}),
            dcc.RadioItems(
                id='desc-multi-scale',
                options=[
                    {'label': 'Auto (sesuai data)', 'value': 'auto'},
                    {'label': 'Mulai dari 0', 'value': 'zero'},
                ],
                value='auto',
                inline=True,
                labelStyle={'marginRight': '15px', 'fontSize': '13px'},
                inputStyle={'marginRight': '4px'}
            )
        ]),
        dcc.Loading(children=[
            html.Div(id='desc-multi-table-output', style={'marginTop': '10px'}),
            html.Div(id='desc-multi-trend-output', style={'marginTop': '10px'})
        ])
    ]),

    # --- 3. DATA DIAGNOSTICS ---
    html.Div(style=CARD_STYLE, children=[
        html.H5("Diagnostic Tests (KMO & Bartlett)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
        html.Div(style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'marginBottom': '20px'}, children=[
            html.Button('RUN DIAGNOSTIK', id='btn-run-diag', n_clicks=0, style={'backgroundColor': '#FFB300', 'color': 'white', 'fontWeight': 'bold', 'borderRadius': '5px', 'width': '200px'}),
            dcc.Loading(type='circle', color='#FFB300', children=html.Div(id='spinner-run-diag'), style={'display': 'inline-block', 'marginLeft': '10px', 'verticalAlign': 'middle', 'width': '30px'})
        ]),
        dcc.Loading(children=[
            html.Div(className='row', id='diag-results-container', style={'display': 'none'}, children=[
                html.Div(className='six columns', children=[
                    html.H6("Kaiser-Meyer-Olkin (KMO) Test", style={'fontWeight': 'bold'}),
                    html.Div(id='kmo-result', style={'fontSize': '16px', 'padding': '10px', 'backgroundColor': '#E8F5E9', 'borderRadius': '5px'})
                ]),
                html.Div(className='six columns', children=[
                    html.H6("Bartlett's Test of Sphericity", style={'fontWeight': 'bold'}),
                    html.Div(id='bartlett-result', style={'fontSize': '16px', 'padding': '10px', 'backgroundColor': '#E8F5E9', 'borderRadius': '5px'})
                ])
            ])
        ]),
        html.Div(id='formula-diag-output', style={'marginTop': '20px'})
    ]),

    # --- 4. CONTROLS (STATIS Panel) ---
    html.Div(style=CARD_STYLE, children=[
        html.H4("Panel Kontrol Analisis Dynamic Biplot dan STATIS", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
        html.Div(className='row', children=[
            html.Div(className='three columns', children=[
                html.Label('Pilih Variabel Analisis:', style={'fontWeight':'bold'}),
                dcc.Dropdown(id='variable-dropdown-final', multi=True, placeholder="Pilih variabel...", style={'fontSize': '14px'}),
                html.Div(id='weight-var-statis-exclude-note', style={'fontSize': '11px', 'color': '#78909C', 'marginTop': '4px'})
            ]),
            html.Div(className='three columns', children=[
                html.Label('Variabel Bobot (mᵢ):', style={'fontWeight':'bold'}),
                dcc.Dropdown(id='weight-var-statis-dropdown', multi=False, placeholder="Pilih variabel bobot...", style={'fontSize': '14px'}),
                html.Div("Variabel ini dihitung sebagai mᵢ = ̅Vᵢ/Σ̅V dan dikecualikan dari analisis.", style={'fontSize': '11px', 'color': '#78909C', 'marginTop': '4px'})
            ]),
            html.Div(className='three columns', children=[
                html.Label('Rotasi Baseline (Semua Plot):', style={'fontWeight':'bold'}),
                dcc.RadioItems(id='baseline-type-final', options=[{'label':'Variabel','value':'loading'},{'label':'Kab/Kota','value':'skor'}], value='loading', labelStyle={'display':'inline-block','marginRight':'10px'}),
                dcc.Dropdown(id='baseline-name-final', placeholder="Pilih referensi...", style={'fontSize': '14px'})
            ]),
            html.Div(className='three columns', children=[
                html.Label('Filter Tahun:', style={'fontWeight':'bold'}),
                dcc.Checklist(id='year-checklist-final', inline=True, style={'marginBottom':'5px'}),
                html.Label('Mirroring Biplot PCA (Flip PC2):', style={'fontSize':'12px', 'color':'#263238'}),
                dcc.Checklist(id='mirror-year-checklist-final', inline=True, style={'marginBottom':'5px'}),
                html.Label('Mirroring Biplot STATIS (Flip PC2):', style={'fontSize':'12px', 'color':'#2E7D32'}),
                dcc.Checklist(id='mirror-year-checklist-statis', inline=True)
            ]),
            html.Div(className='three columns', children=[
                html.Label('Highlight Trajektori:', style={'fontWeight':'bold'}),
                dcc.Dropdown(id='trajectory-dropdown-final', multi=True, placeholder="Pilih objek...", style={'fontSize': '14px'})
            ])
        ]),
        html.Hr(style={'borderColor': '#ECEFF1'}),
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
                dcc.RadioItems(
                    id='visual-scaling-opts',
                    options=[
                        {'label': 'Tanpa Skala', 'value': 'none'},
                        {'label': 'Normalisasi Skor (-1 s.d 1)', 'value': 'norm_score'},
                        {'label': 'Skala Visual Loadings (Agar sebanding)', 'value': 'scale_load'}
                    ],
                    value='scale_load',
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
        ]),
        html.P("Pilih Skenario Analisis (Lavit, 1994):", style={'marginTop': '15px', 'fontWeight': 'bold'}),
        dcc.RadioItems(
            id='statis-scenario',
            options=[
                {'label': ' Skenario 1: ACT Klasik (Host = Wilayah)', 'value': 'scenario1'},
                {'label': ' Skenario 2: Dual STATIS (Host = Indikator)', 'value': 'scenario2'}
            ],
            value='scenario2',
            labelStyle={'display': 'block', 'marginBottom': '5px'}
        ),
        html.P("Orientasi Sumbu Kompromi:", style={'marginTop': '12px', 'marginBottom': '4px', 'fontWeight': 'bold', 'color': '#546E7A', 'fontSize': '0.9rem'}),
        dcc.Checklist(
            id='statis-mirror-opts',
            options=[
                {'label': ' Balik arah PC1 (Mirror Sumbu Kompromi 1)', 'value': 'mirror_pc1'},
                {'label': ' Balik arah PC2 (Mirror Sumbu Kompromi 2)', 'value': 'mirror_pc2'}
            ],
            value=[],
            labelStyle={'display': 'block', 'marginBottom': '3px', 'fontSize': '0.85rem', 'color': '#37474F'}
        ),
        html.Div(style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'marginTop': '20px'}, children=[
            html.Button('RUN ANALISIS STATIS & BIPLOT', id='btn-run-statis', n_clicks=0, style={'flex': '1', 'backgroundColor': COLOR_ACCENT, 'color': 'white', 'fontWeight': 'bold', 'borderRadius': '5px'}),
            dcc.Loading(type='circle', color=COLOR_ACCENT, children=html.Div(id='spinner-run-statis'), style={'display': 'inline-block', 'marginLeft': '10px', 'verticalAlign': 'middle', 'width': '30px', 'flexShrink': '0'})
        ]),
        html.Div(id='statis-error-msg', style={'color': 'red', 'marginTop': '10px'})
    ]),


    # --- 3. DYNAMIC BIPLOT ---
    html.Div(id='biplot-section-container', style={'visibility': 'hidden', 'height': '0', 'overflow': 'hidden', 'margin': '0', 'padding': '0'}, children=[
        html.H5("Visualisasi Dynamic Biplot (Spasio-Temporal)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
        dcc.Loading(type='cube', color=COLOR_ACCENT, children=[
            dcc.Graph(id='graph-3d-main', style={'height': '700px'}, responsive=True, config={'responsive': True})
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
        ]),
        html.Hr(),
        html.H6("Pergeseran Centroid Tahunan — PCA Biplot", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
        html.P("Jarak Euclidean D(c₁, c₂) antar-centroid skor biplot tahun berturutan (Persamaan ​D(c₁ᵢ, c₂ⱼ) = √Σ(c₁ᵢₕ − c₂ⱼₕ)²).", style={'textAlign': 'center', 'color': '#546E7A', 'fontSize': '12px', 'marginBottom': '10px'}),
        dcc.Loading(children=[
            dash_table.DataTable(
                id='biplot-centroid-dist-table',
                export_format='xlsx',
                style_table={'overflowX': 'auto'},
                style_header={'backgroundColor': '#37474F', 'color': 'white', 'fontWeight': 'bold'},
                style_cell={'textAlign': 'center', 'padding': '8px', 'fontFamily': 'sans-serif'},
                page_size=20
            )
        ]),
        html.Hr(),
        html.H6("Jarak Pergeseran Per-Entitas Antar-Tahun — PCA Biplot", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
        html.P("Jarak Euclidean D(c₁ᵢ, c₂ⱼ) posisi entitas terpilih antar-tahun berturutan.", style={'textAlign': 'center', 'color': '#546E7A', 'fontSize': '12px', 'marginBottom': '10px'}),
        html.Div(className='row', style={'marginBottom': '10px'}, children=[
            html.Div(className='three columns', children=[
                html.Label('Jenis Entitas:', style={'fontWeight': 'bold'}),
                dcc.RadioItems(
                    id='biplot-entity-type',
                    options=[{'label': 'Kab/Kota', 'value': 'skor'}, {'label': 'Variabel', 'value': 'loading'}],
                    value='skor',
                    labelStyle={'display': 'inline-block', 'marginRight': '10px'}
                )
            ]),
            html.Div(className='nine columns', children=[
                dcc.Dropdown(id='biplot-entity-name', placeholder="Pilih entitas...", style={'fontSize': '14px'})
            ])
        ]),
        dcc.Loading(children=[
            dash_table.DataTable(
                id='biplot-entity-dist-table',
                export_format='xlsx',
                style_table={'overflowX': 'auto'},
                style_header={'backgroundColor': '#37474F', 'color': 'white', 'fontWeight': 'bold'},
                style_cell={'textAlign': 'center', 'padding': '8px', 'fontFamily': 'sans-serif'},
                page_size=20
            )
        ])
    ]),

    # --- 3B. DYNAMIC BIPLOT STATIS (SKOR INTRA F) ---
    html.Div(id='statis-biplot-3d-section-container', style={'visibility': 'hidden', 'height': '0', 'overflow': 'hidden', 'margin': '0', 'padding': '0'}, children=[
        html.H5("Visualisasi Dynamic Biplot (Skor Intra F dari STATIS)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': '#2E7D32'}),
        dcc.Loading(type='cube', color='#2E7D32', children=[
            dcc.Graph(id='statis-graph-3d-main', style={'height': '700px'}, responsive=True, config={'responsive': True})
        ]),
        html.Hr(),
        html.Div(className='row', children=[
            html.Div(className='six columns', children=[
                html.H5("Snapshot 2D per Tahun (Skor Intra STATIS)", style={'textAlign': 'center', 'color': '#2E7D32'}),
                dcc.Dropdown(id='statis-year-dropdown-2d-single', style={'width':'60%', 'margin':'0 auto', 'marginBottom':'10px'}),
                dcc.Loading(children=[dcc.Graph(id='statis-graph-2d-year', style={'height': '600px'})])
            ]),
            html.Div(className='six columns', children=[
                html.H5("Proyeksi Trajektori 2D (Trajectory Scores)", style={'textAlign': 'center', 'color': '#2E7D32'}),
                html.P("Lintasan pergerakan objek dari tahun ke tahun", style={'textAlign':'center', 'color':'#90A4AE', 'fontSize':'12px'}),
                dcc.Loading(children=[dcc.Graph(id='statis-graph-2d-traj', style={'height': '600px'})])
            ])
        ]),
        html.Hr(),
        html.H6("Data Trajektori STATIS Terpilih (Tabel)", style={'textAlign':'center', 'fontWeight':'bold', 'color': '#2E7D32'}),
        dcc.Loading(children=[
            dash_table.DataTable(
                id='statis-trajectory-table',
                export_format='xlsx',
                style_table={'overflowX': 'auto'},
                style_header={'backgroundColor': '#2E7D32', 'color': 'white', 'fontWeight': 'bold'},
                style_cell={'textAlign': 'center', 'padding': '8px', 'fontFamily': 'sans-serif'},
                page_size=10
            )
        ]),
        html.Hr(),
        html.H6("Pergeseran Centroid Tahunan — STATIS (Skor Intra Fₖ)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': '#2E7D32'}),
        html.P("Jarak Euclidean D(c₁, c₂) antar-centroid skor intra Fₖ tahun berturutan (Persamaan ​D(c₁ᵢ, c₂ⱼ) = √Σ(c₁ᵢₕ − c₂ⱼₕ)²).", style={'textAlign': 'center', 'color': '#546E7A', 'fontSize': '12px', 'marginBottom': '10px'}),
        dcc.Loading(children=[
            dash_table.DataTable(
                id='statis-centroid-dist-table',
                export_format='xlsx',
                style_table={'overflowX': 'auto'},
                style_header={'backgroundColor': '#2E7D32', 'color': 'white', 'fontWeight': 'bold'},
                style_cell={'textAlign': 'center', 'padding': '8px', 'fontFamily': 'sans-serif'},
                page_size=20
            )
        ]),
        html.Hr(),
        html.H6("Jarak Pergeseran Per-Entitas Antar-Tahun — STATIS (Skor Intra Fₖ)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': '#2E7D32'}),
        html.P("Jarak Euclidean D(c₁ᵢ, c₂ⱼ) posisi entitas terpilih antar-tahun berturutan.", style={'textAlign': 'center', 'color': '#546E7A', 'fontSize': '12px', 'marginBottom': '10px'}),
        html.Div(className='row', style={'marginBottom': '10px'}, children=[
            html.Div(className='three columns', children=[
                html.Label('Jenis Entitas:', style={'fontWeight': 'bold'}),
                dcc.RadioItems(
                    id='statis-entity-type',
                    options=[{'label': 'Kab/Kota', 'value': 'skor'}, {'label': 'Variabel', 'value': 'loading'}],
                    value='skor',
                    labelStyle={'display': 'inline-block', 'marginRight': '10px'}
                )
            ]),
            html.Div(className='nine columns', children=[
                dcc.Dropdown(id='statis-entity-name', placeholder="Pilih entitas...", style={'fontSize': '14px'})
            ])
        ]),
        dcc.Loading(children=[
            dash_table.DataTable(
                id='statis-entity-dist-table',
                export_format='xlsx',
                style_table={'overflowX': 'auto'},
                style_header={'backgroundColor': '#2E7D32', 'color': 'white', 'fontWeight': 'bold'},
                style_cell={'textAlign': 'center', 'padding': '8px', 'fontFamily': 'sans-serif'},
                page_size=20
            )
        ])
    ]),

    # --- 3C. MATRIKS JARAK & PERBANDINGAN PCA VS STATIS ---
    html.Div(id='distance-comparison-section-container', style={'display': 'none'}, children=[
        html.H5("Analisis Dampak Pembobotan STATIS terhadap Skor Objek", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': '#0288D1'}),
        html.P("Perbandingan posisi objek atau variabel antara ruang PCA (Unweighted) dan Skor Intra STATIS (Weighted). Selisih posisi mencerminkan dampak pembobotan STATIS, bukan jarak geometri dalam ruang bersama.", style={'textAlign': 'center', 'color': '#546E7A', 'marginBottom': '20px'}),
        html.Div(className='row', style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'marginBottom': '20px'}, children=[
            html.Label("Pilih Tahun:", style={'marginRight': '10px', 'fontWeight': 'bold'}),
            dcc.Dropdown(id='compare-year-dropdown', clearable=False, style={'width': '150px', 'marginRight': '20px'}),
            html.Label("Pilih Jenis Data:", style={'marginRight': '10px', 'fontWeight': 'bold'}),
            dcc.Dropdown(id='compare-data-type', options=[{'label': 'Skor (Objek)', 'value': 'scores'}, {'label': 'Loadings (Variabel)', 'value': 'loadings'}], value='scores', clearable=False, style={'width': '200px', 'marginRight': '20px'})
        ]),
        dcc.Loading(children=[
            dash_table.DataTable(
                id='compare-distance-table',
                export_format='xlsx',
                style_table={'overflowX': 'auto'},
                style_header={'backgroundColor': '#0288D1', 'color': 'white', 'fontWeight': 'bold'},
                style_cell={'textAlign': 'center', 'padding': '8px', 'fontFamily': 'sans-serif'},
                page_size=10
            )
        ])
    ]),

    # --- 4. STATIS ANALYSIS ---
    html.Div(id='statis-section-container', style={'display': 'none'}, children=[
        html.H5("Analisis STATIS (Struktur Kompromi)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
        dcc.Loading(children=[html.Div(id='formula-statis-output', style={'marginBottom': '20px'})]),
        # 4 Plot Grid -> Expanded to 7 Plot Grid
        html.Div(className='row', style={'marginBottom':'30px'}, children=[
            html.Div(className='six columns', children=[
                dcc.Loading(children=[dcc.Graph(id='statis-scree', style={'height': '400px'})])
            ]),
            html.Div(className='six columns', children=[
                dcc.Loading(children=[dcc.Graph(id='statis-interstructure', style={'height': '400px'})])
            ])
        ]),
        html.Div(className='row', style={'marginBottom':'30px'}, children=[
            html.Div(className='six columns', children=[
                dcc.Loading(children=[dcc.Graph(id='statis-biplot', style={'height': '600px'})])
            ]),
            html.Div(className='six columns', children=[
                dcc.Loading(children=[dcc.Graph(id='statis-structure-vector', style={'height': '600px'})])
            ])
        ]),
        html.Div(className='row', style={'marginBottom':'30px'}, children=[
            html.Div(className='six columns', children=[
                dcc.Loading(children=[dcc.Graph(id='statis-contribution', style={'height': '400px'})])
            ]),
            html.Div(className='six columns', children=[
                dcc.Loading(children=[dcc.Graph(id='statis-cos2', style={'height': '400px'})])
            ])
        ]),
        html.Div(className='row', style={'marginTop':'30px'}, children=[
            html.Div(className='six columns', children=[
                dcc.Loading(children=[dcc.Graph(id='statis-trajectory', style={'height': '500px'})])
            ]),
            html.Div(className='six columns', children=[
                dcc.Loading(children=[dcc.Graph(id='statis-trajectory-loading', style={'height': '500px'})])
            ])
        ]),
        
        html.Hr(style={'borderColor': '#B0BEC5', 'marginTop': '30px'}),
        
        # Permutation Test
        html.Div(style={'padding': '20px', 'borderRadius': '10px', 'border': '0px solid #FFF59D'}, children=[
            html.H5("Uji Signifikansi Stabilitas (Permutasi)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
            html.Div(className='row', style={'display': 'flex', 'justifyContent': 'center', 'alignItems': 'center', 'marginBottom': '10px'}, children=[
                html.Label("Jumlah Permutasi (N): ", style={'marginRight': '10px', 'fontWeight': 'bold'}),
                dcc.Input(id='perm-n-input', type='number', value=1000, min=100, step=100, style={'width': '100px', 'marginRight': '20px'}),
                html.Button("RUN PERMUTATION TEST", id='btn-run-perm', n_clicks=0, style={'backgroundColor': COLOR_ACCENT, 'color': 'white', 'fontWeight': 'bold', 'borderRadius': '5px'}),
                dcc.Loading(type='circle', color=COLOR_ACCENT, children=html.Div(id='spinner-run-perm'), style={'display': 'inline-block', 'marginLeft': '10px', 'verticalAlign': 'middle', 'width': '30px'})
            ]),
            dcc.Loading(children=[
                dcc.Graph(id='perm-graph', style={'height': '350px'}),
                html.Div(id='perm-result-text', style={'textAlign': 'center', 'fontSize': '16px', 'marginTop': '10px', 'fontWeight': 'bold', 'color': '#333'}),
                dcc.Loading(children=[html.Div(id='formula-perm-output', style={'marginTop': '20px'})])
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
        html.Div(style={'textAlign': 'center', 'marginTop': '10px'}, children=[
            html.Button("Unduh Tabel sebagai .TEX", id="btn-dl-detail-tex", style={'backgroundColor': '#607D8B', 'color': 'white', 'border': 'none', 'padding': '5px 15px', 'borderRadius': '3px', 'cursor': 'pointer'}),
            dcc.Download(id="download-detail-tex")
        ]),
        html.Hr(style={'borderColor': '#B0BEC5', 'marginTop': '40px'}),
        # --- [TAMBAHAN BARU] SECTION 5: EVALUASI JUMLAH CLUSTER (ELBOW & DENDROGRAM) ---
        html.Div(style=CARD_STYLE, children=[
            html.H5("Tahap Pembantu: Evaluasi Jumlah Klaster (Visual Aids)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
            html.P("Gunakan kurva Elbow dan Dendrogram di bawah ini untuk menentukan jumlah klaster (k) yang optimal pada suatu tahun.", style={'textAlign': 'center', 'color': '#546E7A'}),
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
            html.H5("Analisis Klaster Spasio-Temporal Tahunan (Berdasarkan PCA 3D Tanpa Bobot)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
            html.Div(className='row', style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'marginBottom': '20px'}, children=[
                html.Label("Pasangan Tahun Transisi:", style={'marginRight': '10px', 'fontWeight': 'bold'}),
                dcc.Dropdown(id='trans-year-dropdown', clearable=False, style={'width': '200px', 'marginRight': '20px'}),
                html.Label("Jumlah Klaster (k):", style={'marginRight': '10px', 'fontWeight': 'bold'}),
                dcc.Input(id='trans-k-input', type='number', value=3, min=2, max=10, step=1, style={'width': '60px', 'marginRight': '20px'}),
                html.Button("RUN CLUSTERING TAHUNAN", id='btn-run-trans', n_clicks=0,
                            style={'backgroundColor': COLOR_ACCENT, 'color': 'white', 'fontWeight': 'bold', 'border': 'none', 'borderRadius': '5px', 'height': '38px', 'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center', 'padding': '0 20px', 'cursor': 'pointer'}),
                dcc.Loading(type='circle', color=COLOR_ACCENT, children=html.Div(id='spinner-run-trans'), style={'display': 'inline-block', 'marginLeft': '10px', 'verticalAlign': 'middle', 'width': '30px'})
            ]),
            html.Div(id='trans-results-container', style={'display': 'none'}, children=[
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
                html.Div(className='row', style={'marginTop': '15px'}, children=[
                    html.Div(className='six columns', children=[
                        html.H6(id='title-trans-pie-t1', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                        dcc.Loading(children=[dcc.Graph(id='trans-pie-t1', style={'height': '400px'})])
                    ]),
                    html.Div(className='six columns', children=[
                        html.H6(id='title-trans-pie-t2', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                        dcc.Loading(children=[dcc.Graph(id='trans-pie-t2', style={'height': '400px'})])
                    ])
                ]),
                html.Hr(),
                html.H6("Matriks Transisi (Perpindahan Kabupaten/Kota)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
                html.Div(style={'display': 'flex', 'justifyContent': 'center', 'marginBottom': '10px'}, children=[
                    dcc.RadioItems(id='trans-view-mode', options=[{'label': ' Tampilkan Jumlah', 'value': 'count'}, {'label': ' Tampilkan Nama Daerah', 'value': 'names'}], value='count', inline=True, inputStyle={"marginRight": "5px", "marginLeft": "15px"})
                ]),
                dcc.Loading(children=[
                    dash_table.DataTable(id='trans-matrix-table', export_format='xlsx', style_table={'overflowX': 'auto'}, style_header={'backgroundColor': '#37474F', 'color': 'white', 'fontWeight': 'bold'}, style_cell={'textAlign': 'center', 'padding': '8px', 'fontFamily': 'sans-serif'})
                ]),
                html.Div(style={'textAlign': 'center', 'marginTop': '10px'}, children=[
                    html.Button("Unduh Tabel sebagai .TEX", id="btn-dl-trans-tex", style={'backgroundColor': '#607D8B', 'color': 'white', 'border': 'none', 'borderRadius': '3px', 'cursor': 'pointer', 'height': '32px', 'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center', 'padding': '0 15px', 'fontSize': '12px'}),
                    dcc.Download(id="download-trans-tex")
                ])
            ])
        ]),

        # --- [TAMBAHAN BARU] SECTION 6B: CLUSTERING TAHUNAN & MATRIKS TRANSISI TERBOBOT (STATIS) ---
        html.Div(style=CARD_STYLE, children=[
            html.H5("Analisis Klaster Spasio-Temporal Tahunan (Berdasarkan Trajektori STATIS Terbobot)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': '#2E7D32'}),
            html.Div(className='row', style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'marginBottom': '20px'}, children=[
                html.Label("Pasangan Tahun Transisi:", style={'marginRight': '10px', 'fontWeight': 'bold'}),
                dcc.Dropdown(id='weighted-trans-year-dropdown', clearable=False, style={'width': '200px', 'marginRight': '20px'}),
                html.Label("Jumlah Klaster (k):", style={'marginRight': '10px', 'fontWeight': 'bold'}),
                dcc.Input(id='weighted-trans-k-input', type='number', value=3, min=2, max=10, step=1, style={'width': '60px', 'marginRight': '20px'}),
                html.Button("RUN CLUSTERING TERBOBOT", id='btn-run-weighted-trans', n_clicks=0,
                            style={'backgroundColor': '#2E7D32', 'color': 'white', 'fontWeight': 'bold', 'border': 'none', 'borderRadius': '5px', 'height': '38px', 'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center', 'padding': '0 20px', 'cursor': 'pointer'}),
                dcc.Loading(type='circle', color='#2E7D32', children=html.Div(id='spinner-run-weighted-trans'), style={'display': 'inline-block', 'marginLeft': '10px', 'verticalAlign': 'middle', 'width': '30px'})
            ]),
            html.Div(id='weighted-trans-results-container', style={'display': 'none'}, children=[
                html.Div(className='row', children=[
                    html.Div(className='six columns', children=[
                        html.H6(id='title-weighted-trans-map-t1', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                        dcc.Loading(children=[dcc.Graph(id='weighted-trans-map-t1', style={'height': '500px'})])
                    ]),
                    html.Div(className='six columns', children=[
                        html.H6(id='title-weighted-trans-map-t2', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                        dcc.Loading(children=[dcc.Graph(id='weighted-trans-map-t2', style={'height': '500px'})])
                    ])
                ]),
                html.Div(className='row', children=[
                    html.Div(className='six columns', children=[
                        html.H6(id='title-weighted-trans-scatter-t1', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                        dcc.Loading(children=[dcc.Graph(id='weighted-trans-scatter-t1', style={'height': '500px'})])
                    ]),
                    html.Div(className='six columns', children=[
                        html.H6(id='title-weighted-trans-scatter-t2', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                        dcc.Loading(children=[dcc.Graph(id='weighted-trans-scatter-t2', style={'height': '500px'})])
                    ])
                ]),
                html.Div(className='row', style={'marginTop': '15px'}, children=[
                    html.Div(className='six columns', children=[
                        html.H6(id='title-weighted-trans-pie-t1', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                        dcc.Loading(children=[dcc.Graph(id='weighted-trans-pie-t1', style={'height': '400px'})])
                    ]),
                    html.Div(className='six columns', children=[
                        html.H6(id='title-weighted-trans-pie-t2', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                        dcc.Loading(children=[dcc.Graph(id='weighted-trans-pie-t2', style={'height': '400px'})])
                    ])
                ]),
                html.Hr(),
                html.H6("Matriks Transisi Terbobot (Perpindahan Kabupaten/Kota)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': '#2E7D32'}),
                html.Div(style={'display': 'flex', 'justifyContent': 'center', 'marginBottom': '10px'}, children=[
                    dcc.RadioItems(id='weighted-trans-view-mode', options=[{'label': ' Tampilkan Jumlah', 'value': 'count'}, {'label': ' Tampilkan Nama Daerah', 'value': 'names'}], value='count', inline=True, inputStyle={"marginRight": "5px", "marginLeft": "15px"})
                ]),
                dcc.Loading(children=[
                    dash_table.DataTable(id='weighted-trans-matrix-table', export_format='xlsx', style_table={'overflowX': 'auto'}, style_header={'backgroundColor': '#37474F', 'color': 'white', 'fontWeight': 'bold'}, style_cell={'textAlign': 'center', 'padding': '8px', 'fontFamily': 'sans-serif'})
                ]),
                html.Div(style={'textAlign': 'center', 'marginTop': '10px'}, children=[
                    html.Button("Unduh Tabel sebagai .TEX", id="btn-dl-weighted-trans-tex", style={'backgroundColor': '#607D8B', 'color': 'white', 'border': 'none', 'borderRadius': '3px', 'cursor': 'pointer', 'height': '32px', 'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center', 'padding': '0 15px', 'fontSize': '12px'}),
                    dcc.Download(id="download-weighted-trans-tex")
                ])
            ])
        ]),

        # --- [TAMBAHAN BARU] SECTION 6C: PERBANDINGAN METODE CLUSTER (BIPLOT VS STATIS) PADA TAHUN TERTENTU ---
        html.Div(style=CARD_STYLE, children=[
            html.H5("Perbandingan Cluster: Biplot PCA (Unweighted) vs Trajektori STATIS (Weighted)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': '#D84315'}),
            html.P("Membandingkan hasil pengelompokan wilayah antara metode Biplot PCA biasa dan trajektori STATIS untuk satu tahun tertentu.", style={'textAlign': 'center', 'color': '#546E7A', 'marginBottom': '20px'}),
            
            html.Div(className='row', style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'marginBottom': '20px'}, children=[
                html.Label("Pilih Tahun:", style={'marginRight': '10px', 'fontWeight': 'bold'}),
                dcc.Dropdown(id='biplot-statis-compare-year', clearable=False, style={'width': '200px', 'marginRight': '20px'}),
                html.Label("Jumlah Klaster (k):", style={'marginRight': '10px', 'fontWeight': 'bold'}),
                dcc.Input(id='biplot-statis-compare-k', type='number', value=3, min=2, max=10, step=1, style={'width': '60px', 'marginRight': '20px'}),
                html.Button("RUN PERBANDINGAN", id='btn-run-biplot-statis-compare', n_clicks=0,
                            style={'backgroundColor': '#D84315', 'color': 'white', 'fontWeight': 'bold', 'border': 'none', 'borderRadius': '5px', 'height': '38px', 'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center', 'padding': '0 20px', 'cursor': 'pointer'}),
                dcc.Loading(type='circle', color='#D84315', children=html.Div(id='spinner-run-biplot-statis-compare'), style={'display': 'inline-block', 'marginLeft': '10px', 'verticalAlign': 'middle', 'width': '30px'})
            ]),
            html.Div(id='biplot-statis-compare-results-container', style={'display': 'none'}, children=[
                html.Div(className='row', children=[
                    html.Div(className='six columns', children=[
                        html.H6(id='title-biplot-statis-compare-map-biplot', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                        dcc.Loading(children=[dcc.Graph(id='biplot-statis-compare-map-biplot', style={'height': '500px'})])
                    ]),
                    html.Div(className='six columns', children=[
                        html.H6(id='title-biplot-statis-compare-map-statis', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                        dcc.Loading(children=[dcc.Graph(id='biplot-statis-compare-map-statis', style={'height': '500px'})])
                    ])
                ]),
                html.Div(className='row', children=[
                    html.Div(className='six columns', children=[
                        html.H6(id='title-biplot-statis-compare-scatter-biplot', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                        dcc.Loading(children=[dcc.Graph(id='biplot-statis-compare-scatter-biplot', style={'height': '500px'})])
                    ]),
                    html.Div(className='six columns', children=[
                        html.H6(id='title-biplot-statis-compare-scatter-statis', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                        dcc.Loading(children=[dcc.Graph(id='biplot-statis-compare-scatter-statis', style={'height': '500px'})])
                    ])
                ]),
                html.Div(className='row', style={'marginTop': '15px'}, children=[
                    html.Div(className='six columns', children=[
                        html.H6(id='title-biplot-statis-compare-pie-biplot', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                        dcc.Loading(children=[dcc.Graph(id='biplot-statis-compare-pie-biplot', style={'height': '400px'})])
                    ]),
                    html.Div(className='six columns', children=[
                        html.H6(id='title-biplot-statis-compare-pie-statis', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                        dcc.Loading(children=[dcc.Graph(id='biplot-statis-compare-pie-statis', style={'height': '400px'})])
                    ])
                ]),
                html.Hr(),
                html.H6("Matriks Tabulasi Silang (Biplot vs STATIS)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': '#D84315'}),
                html.Div(style={'display': 'flex', 'justifyContent': 'center', 'marginBottom': '10px'}, children=[
                    dcc.RadioItems(id='biplot-statis-compare-view-mode', options=[{'label': ' Tampilkan Jumlah', 'value': 'count'}, {'label': ' Tampilkan Nama Daerah', 'value': 'names'}], value='count', inline=True, inputStyle={"marginRight": "5px", "marginLeft": "15px"})
                ]),
                dcc.Loading(children=[
                    dash_table.DataTable(id='biplot-statis-compare-matrix-table', export_format='xlsx', style_table={'overflowX': 'auto'}, style_header={'backgroundColor': '#37474F', 'color': 'white', 'fontWeight': 'bold'}, style_cell={'textAlign': 'center', 'padding': '8px', 'fontFamily': 'sans-serif'})
                ]),
                html.Div(style={'textAlign': 'center', 'marginTop': '10px'}, children=[
                    html.Button("Unduh Tabel sebagai .TEX", id="btn-dl-biplot-statis-compare-tex", style={'backgroundColor': '#607D8B', 'color': 'white', 'border': 'none', 'borderRadius': '3px', 'cursor': 'pointer', 'height': '32px', 'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center', 'padding': '0 15px', 'fontSize': '12px'}),
                    dcc.Download(id="download-biplot-statis-compare-tex")
                ])
            ])
        ]),

        # --- SECTION 7: CLUSTERING TRAJEKTORI KESELURUHAN ---
        html.Div(style=CARD_STYLE, children=[
            html.H5("Analisis Lanjutan: Clustering Trajektori Keseluruhan (STATIS)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
            html.P("Mengelompokkan Kabupaten/Kota berdasarkan kemiripan pola pergerakan (nasib) selama periode penuh.", 
                   style={'textAlign': 'center', 'color': '#546E7A', 'marginBottom': '20px'}),
            
            html.Div(className='row', style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'marginBottom': '20px'}, children=[
                html.Label("Jumlah Klaster (k):", style={'marginRight': '10px', 'fontWeight': 'bold'}),
                dcc.Input(id='cluster-k-input', type='number', value=3, min=2, max=10, step=1, style={'width': '60px', 'marginRight': '20px'}),
                html.Button("RUN CLUSTERING TRAJEKTORI", id='btn-run-cluster', n_clicks=0,
                            style={'backgroundColor': COLOR_ACCENT, 'color': 'white', 'fontWeight': 'bold', 'border': 'none', 'borderRadius': '5px', 'height': '38px', 'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center', 'padding': '0 25px', 'cursor': 'pointer'}),
                dcc.Loading(type='circle', color=COLOR_ACCENT, children=html.Div(id='spinner-run-cluster'), style={'display': 'inline-block', 'marginLeft': '10px', 'verticalAlign': 'middle', 'width': '30px'})
            ]),

            html.Div(id='cluster-results-container', style={'display': 'none'}, children=[
                html.Div(className='row', children=[
                    # Kiri: Scatter Plot
                    html.Div(className='six columns', children=[
                        html.H5("Peta Sebaran (Scatter Plot)", style={'textAlign': 'center', 'fontSize': '14px', 'fontWeight': 'bold'}),
                        dcc.Loading(children=[dcc.Graph(id='cluster-scatter', style={'height': '800px'})])
                    ]),
                    # Kanan: Pie Chart
                    html.Div(className='six columns', children=[
                        html.H5("Proporsi Klaster (Pie Chart)", style={'textAlign': 'center', 'fontSize': '14px', 'fontWeight': 'bold'}),
                        dcc.Loading(children=[dcc.Graph(id='cluster-pie', style={'height': '450px'})])
                    ])
                ]),

                # --- [TAMBAHAN BARU: PETA SPASIAL] ---
                html.Hr(style={'borderColor': '#E0E0E0', 'marginTop': '20px', 'marginBottom': '20px'}),
                html.H5("Distribusi Geografis Klaster (Peta Wilayah)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
                dcc.Loading(type='cube', color=COLOR_ACCENT, children=[
                    dcc.Graph(id='cluster-map', style={'height': '500px'})
                ]),
                # -------------------------------------

                html.Div(id='cluster-interpretation', style={'marginTop': '15px', 'padding': '15px', 'backgroundColor': '#E3F2FD', 'borderRadius': '5px', 'borderLeft': '5px solid #1565C0', 'fontStyle': 'italic', 'color': '#0D47A1'}),

                # --- [NEW] Tabel Anggota Klaster ---
                html.H6("Daftar Anggota per Kelompok (Cluster)", style={'textAlign': 'center', 'fontWeight': 'bold', 'marginTop': '30px', 'color': COLOR_ACCENT}),
                dcc.Loading(children=[
                    dash_table.DataTable(
                        id='cluster-member-table',
                        export_format='xlsx',
                        style_table={'overflowX': 'auto', 'marginTop': '10px'},
                        style_header={'backgroundColor': '#37474F', 'color': 'white', 'fontWeight': 'bold'},
                        style_cell={'textAlign': 'left', 'padding': '10px', 'fontFamily': 'sans-serif', 'whiteSpace': 'normal', 'height': 'auto'},
                        style_data_conditional=[
                            {'if': {'row_index': 'odd'}, 'backgroundColor': '#F5F5F5'}
                        ]
                    )
                ]),

                dcc.Loading(children=[html.Div(id='formula-cluster-output', style={'marginTop': '20px'})])
            ])
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
                            style={'backgroundColor': '#E64A19', 'color': 'white', 'fontWeight': 'bold', 'border': 'none', 'borderRadius': '5px', 'height': '38px', 'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center', 'padding': '0 20px', 'cursor': 'pointer'}),
                dcc.Loading(type='circle', color='#E64A19', children=html.Div(id='spinner-run-ipm-trans'), style={'display': 'inline-block', 'marginLeft': '10px', 'verticalAlign': 'middle', 'width': '30px'})
            ]),
            
            html.Div(id='ipm-trans-results-container', style={'display': 'none'}, children=[
                html.Div(id='ipm-disclaimer-text', style={'textAlign': 'center', 'marginBottom': '20px', 'fontStyle': 'italic', 'fontWeight': 'bold'}),

                html.Div(className='row', children=[
                    html.Div(className='six columns', children=[
                        html.H6(id='title-ipm-trans-map-t1', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                        dcc.Loading(children=[dcc.Graph(id='ipm-trans-map-t1', style={'height': '500px'})])
                    ]),
                    html.Div(className='six columns', children=[
                        html.H6(id='title-ipm-trans-map-t2', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                        dcc.Loading(children=[dcc.Graph(id='ipm-trans-map-t2', style={'height': '500px'})])
                    ])
                ]),
                html.Div(className='row', style={'marginTop': '15px'}, children=[
                    html.Div(className='six columns', children=[
                        html.H6(id='title-ipm-trans-pie-t1', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                        dcc.Loading(children=[dcc.Graph(id='ipm-trans-pie-t1', style={'height': '400px'})])
                    ]),
                    html.Div(className='six columns', children=[
                        html.H6(id='title-ipm-trans-pie-t2', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                        dcc.Loading(children=[dcc.Graph(id='ipm-trans-pie-t2', style={'height': '400px'})])
                    ])
                ]),
                html.Hr(),

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
                ]),
                html.Div(style={'textAlign': 'center', 'marginTop': '10px'}, children=[
                    html.Button("Unduh Tabel sebagai .TEX", id="btn-dl-ipm-trans-tex", style={'backgroundColor': '#607D8B', 'color': 'white', 'border': 'none', 'borderRadius': '3px', 'cursor': 'pointer', 'height': '32px', 'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center', 'padding': '0 15px', 'fontSize': '12px'}),
                    dcc.Download(id="download-ipm-trans-tex")
                ])
            ])
        ]),

        # --- [TAMBAHAN BARU] SECTION 9: PERBANDINGAN CLUSTER VS IPM (CROSS-TABULATION) ---
        html.Div(style=CARD_STYLE, children=[
            html.H5("Perbandingan Klaster Biplot vs Kategori IPM (UNDP)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': '#00695C'}),
            html.P("Bagian ini menampilkan tabel tabulasi silang (cross-tabulation) antara klaster yang dibentuk oleh algoritma K-Means dengan pengelompokan baku dari UNDP berdasarkan skor IPM. Ini berguna untuk mengevaluasi apakah klaster data-driven sejalan dengan standar institusi global.", 
                   style={'textAlign': 'center', 'color': '#546E7A', 'marginBottom': '20px'}),
            
            html.Div(className='row', style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'marginBottom': '20px'}, children=[
                html.Label("Tahun:", style={'marginRight': '10px', 'fontWeight': 'bold'}),
                dcc.Dropdown(id='cross-year-dropdown', clearable=False, style={'width': '120px', 'marginRight': '20px'}),
                html.Label("Jumlah Klaster K-Means (k):", style={'marginRight': '10px', 'fontWeight': 'bold'}),
                dcc.Input(id='cross-k-input', type='number', value=3, min=2, max=10, step=1, style={'width': '60px', 'marginRight': '20px'}),
                html.Button("TAMPILKAN PERBANDINGAN", id='btn-run-cross', n_clicks=0,
                            style={'backgroundColor': '#00897B', 'color': 'white', 'fontWeight': 'bold', 'border': 'none', 'borderRadius': '5px', 'height': '38px', 'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center', 'padding': '0 20px', 'cursor': 'pointer'}),
                dcc.Loading(type='circle', color='#00897B', children=html.Div(id='spinner-run-cross'), style={'display': 'inline-block', 'marginLeft': '10px', 'verticalAlign': 'middle', 'width': '30px'})
            ]),
            
            html.Div(id='cross-results-container', style={'display': 'none'}, children=[
            # Maps Row
            html.Div(className='row', children=[
                html.Div(className='six columns', children=[
                    html.H6(id='title-cross-map-biplot', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='cross-map-biplot', style={'height': '500px'})])
                ]),
                html.Div(className='six columns', children=[
                    html.H6(id='title-cross-map-ipm', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='cross-map-ipm', style={'height': '500px'})])
                ])
            ]),
            
            # Pie Row
            html.Div(className='row', style={'marginTop': '15px'}, children=[
                html.Div(className='six columns', children=[
                    html.H6(id='title-cross-pie-biplot', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='cross-pie-biplot', style={'height': '400px'})])
                ]),
                html.Div(className='six columns', children=[
                    html.H6(id='title-cross-pie-ipm', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='cross-pie-ipm', style={'height': '400px'})])
                ])
            ]),
            html.Hr(),
            
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
            ]),
            html.Div(style={'textAlign': 'center', 'marginTop': '10px'}, children=[
                html.Button("Unduh Tabel sebagai .TEX", id="btn-dl-cross-tex", style={'backgroundColor': '#607D8B', 'color': 'white', 'border': 'none', 'borderRadius': '3px', 'cursor': 'pointer', 'height': '32px', 'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center', 'padding': '0 15px', 'fontSize': '12px'}),
                dcc.Download(id="download-cross-tex")
            ])
            ])  # end cross-results-container
        ]),

        # --- SECTION: PERBANDINGAN CLUSTER STATIS VS KATEGORI IPM (UNDP) ---
        html.Div(style=CARD_STYLE, children=[
            html.H5("Perbandingan Klaster STATIS vs Kategori IPM (UNDP)", 
                    style={'textAlign': 'center', 'fontWeight': 'bold', 'color': '#004D40'}),
            html.P("Membandingkan hasil pengelompokan wilayah berdasarkan Trajektori STATIS (Weighted) per tahun dengan Kategori IPM (UNDP).", 
                   style={'textAlign': 'center', 'color': '#546E7A', 'marginBottom': '20px'}),
            
            html.Div(className='row', style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'marginBottom': '20px'}, children=[
                html.Div([
                    html.Label("Tahun:", style={'fontWeight': 'bold', 'marginRight': '8px'}),
                    dcc.Dropdown(id='statis-vs-ipm-year', clearable=False, style={'width': '120px'})
                ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px'}),
                
                html.Div([
                    html.Label("Jumlah Klaster (k):", style={'fontWeight': 'bold', 'marginRight': '8px'}),
                    dcc.Input(id='statis-vs-ipm-k', type='number', value=3, min=2, max=10, style={'width': '60px'})
                ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px'}),
                
                html.Button("BANDINGKAN CLUSTER", id='btn-run-statis-vs-ipm', n_clicks=0,
                            style={'backgroundColor': '#004D40', 'color': 'white', 'fontWeight': 'bold', 'border': 'none', 'borderRadius': '5px', 'height': '38px', 'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center', 'padding': '0 20px', 'cursor': 'pointer'}),
                dcc.Loading(type='circle', color='#004D40', children=html.Div(id='spinner-run-statis-vs-ipm'), style={'display': 'inline-block', 'marginLeft': '10px', 'verticalAlign': 'middle', 'width': '30px'})
            ]),

            html.Div(id='statis-vs-ipm-results-container', style={'display': 'none'}, children=[
            # Maps Row
            html.Div(className='row', children=[
                html.Div(className='six columns', children=[
                    html.H6(id='title-statis-vs-ipm-map-statis', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='statis-vs-ipm-map-statis', style={'height': '500px'})])
                ]),
                html.Div(className='six columns', children=[
                    html.H6(id='title-statis-vs-ipm-map-ipm', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='statis-vs-ipm-map-ipm', style={'height': '500px'})])
                ])
            ]),
            
            # Pie Row
            html.Div(className='row', style={'marginTop': '15px'}, children=[
                html.Div(className='six columns', children=[
                    html.H6(id='title-statis-vs-ipm-pie-statis', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='statis-vs-ipm-pie-statis', style={'height': '400px'})])
                ]),
                html.Div(className='six columns', children=[
                    html.H6(id='title-statis-vs-ipm-pie-ipm', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='statis-vs-ipm-pie-ipm', style={'height': '400px'})])
                ])
            ]),
            html.Hr(),
            
            html.Div(style={'display': 'flex', 'justifyContent': 'center', 'marginBottom': '10px'}, children=[
                dcc.RadioItems(id='statis-vs-ipm-view-mode', options=[
                    {'label': ' Tampilkan Jumlah', 'value': 'count'}, 
                    {'label': ' Tampilkan Nama Daerah', 'value': 'names'}
                ], value='count', inline=True, inputStyle={"marginRight": "5px", "marginLeft": "15px"})
            ]),
            
            dcc.Loading(children=[
                dash_table.DataTable(id='statis-vs-ipm-table', style_table={'overflowX': 'auto'}, 
                                     style_header={'backgroundColor': '#37474F', 'color': 'white', 'fontWeight': 'bold'}, 
                                     style_cell={'textAlign': 'center', 'padding': '8px', 'fontFamily': 'sans-serif'})
            ]),
            html.Div(style={'textAlign': 'center', 'marginTop': '10px'}, children=[
                html.Button("Unduh Tabel sebagai .TEX", id="btn-dl-statis-vs-ipm-tex", style={'backgroundColor': '#607D8B', 'color': 'white', 'border': 'none', 'borderRadius': '3px', 'cursor': 'pointer', 'height': '32px', 'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center', 'padding': '0 15px', 'fontSize': '12px'}),
                dcc.Download(id="download-statis-vs-ipm-tex")
            ])
            ])  # end statis-vs-ipm-results-container
        ]),

        # --- SECTION 10: PERBANDINGAN HASIL CLUSTER KOMPROMI STATIS VS IPM RATA-RATA ---
        html.Div(style=CARD_STYLE, children=[
            html.H5("Perbandingan Klaster Kompromi STATIS vs Kategori IPM (UNDP)", 
                    style={'textAlign': 'center', 'fontWeight': 'bold', 'color': '#01579B'}),
            html.P("Membandingkan keanggotaan klaster hasil kompromi STATIS dengan Kategori IPM (UNDP) per tahun.", 
                   style={'textAlign': 'center', 'color': '#546E7A', 'marginBottom': '20px'}),
            
            html.Div(className='row', style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'marginBottom': '20px'}, children=[
                html.Div([
                    html.Label("Tahun:", style={'fontWeight': 'bold', 'marginRight': '8px'}),
                    dcc.Dropdown(id='statis-vs-ipm-avg-year', clearable=False, style={'width': '120px'})
                ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px'}),
                
                html.Div([
                    html.Label("Jumlah Klaster (k):", style={'fontWeight': 'bold', 'marginRight': '8px'}),
                    dcc.Input(id='statis-vs-ipm-avg-k', type='number', value=3, min=2, max=10, style={'width': '60px'})
                ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px'}),
                
                html.Button("BANDINGKAN CLUSTER", id='btn-run-statis-ipm-avg', n_clicks=0,
                            style={'backgroundColor': '#01579B', 'color': 'white', 'fontWeight': 'bold', 'border': 'none', 'borderRadius': '5px', 'height': '38px', 'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center', 'padding': '0 20px', 'cursor': 'pointer'}),
                dcc.Loading(type='circle', color='#01579B', children=html.Div(id='spinner-run-statis-ipm-avg'), style={'display': 'inline-block', 'marginLeft': '10px', 'verticalAlign': 'middle', 'width': '30px'})
            ]),

            html.Div(id='statis-ipm-avg-results-container', style={'display': 'none'}, children=[
            # Maps Row
            html.Div(className='row', children=[
                html.Div(className='six columns', children=[
                    html.H6(id='title-statis-ipm-avg-map-statis', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='statis-ipm-avg-map-statis', style={'height': '500px'})])
                ]),
                html.Div(className='six columns', children=[
                    html.H6(id='title-statis-ipm-avg-map-ipm', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='statis-ipm-avg-map-ipm', style={'height': '500px'})])
                ])
            ]),
            
            # Pie Row
            html.Div(className='row', style={'marginTop': '15px'}, children=[
                html.Div(className='six columns', children=[
                    html.H6(id='title-statis-ipm-avg-pie-statis', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='statis-ipm-avg-pie-statis', style={'height': '400px'})])
                ]),
                html.Div(className='six columns', children=[
                    html.H6(id='title-statis-ipm-avg-pie-ipm', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='statis-ipm-avg-pie-ipm', style={'height': '400px'})])
                ])
            ]),
            html.Hr(),
            
            html.Div(style={'display': 'flex', 'justifyContent': 'center', 'marginBottom': '10px'}, children=[
                dcc.RadioItems(id='statis-vs-ipm-avg-view-mode', options=[
                    {'label': ' Tampilkan Jumlah', 'value': 'count'}, 
                    {'label': ' Tampilkan Nama Daerah', 'value': 'names'}
                ], value='count', inline=True, inputStyle={"marginRight": "5px", "marginLeft": "15px"})
            ]),
            
            dcc.Loading(children=[
                dash_table.DataTable(id='statis-vs-ipm-avg-table', style_table={'overflowX': 'auto'}, 
                                     style_header={'backgroundColor': '#37474F', 'color': 'white', 'fontWeight': 'bold'}, 
                                     style_cell={'textAlign': 'center', 'padding': '8px', 'fontFamily': 'sans-serif'})
            ]),
            html.Div(style={'textAlign': 'center', 'marginTop': '10px'}, children=[
                html.Button("Unduh Tabel sebagai .TEX", id="btn-dl-statis-ipm-avg-tex", style={'backgroundColor': '#607D8B', 'color': 'white', 'border': 'none', 'borderRadius': '3px', 'cursor': 'pointer', 'height': '32px', 'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center', 'padding': '0 15px', 'fontSize': '12px'}),
                dcc.Download(id="download-statis-ipm-avg-tex")
            ])
            ])  # end statis-ipm-avg-results-container
        ]),

        # --- SECTION 11: PERBANDINGAN CLUSTER BIPLOT VS CLUSTER KOMPROMI STATIS ---
        html.Div(style=CARD_STYLE, children=[
            html.H5("Perbandingan Klaster Kompromi STATIS vs Klaster Biplot", 
                    style={'textAlign': 'center', 'fontWeight': 'bold', 'color': '#5D4037'}),
            html.P("Membandingkan stabilitas anggota klaster antara hasil 'Kompromi' (STATIS) dengan hasil 'Tahunan' (Statis per Tahun).", 
                   style={'textAlign': 'center', 'color': '#546E7A', 'marginBottom': '20px'}),
            
            html.Div(className='row', style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'marginBottom': '20px'}, children=[
                html.Div([
                    html.Label("Tahun:", style={'fontWeight': 'bold', 'marginRight': '8px'}),
                    dcc.Dropdown(id='biplot-vs-statis-year', clearable=False, style={'width': '120px'})
                ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px'}),
                
                html.Div([
                    html.Label("Jumlah Klaster (k):", style={'fontWeight': 'bold', 'marginRight': '8px'}),
                    dcc.Input(id='biplot-vs-statis-k', type='number', value=3, min=2, max=10, style={'width': '60px'})
                ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px'}),
                
                html.Button("BANDINGKAN CLUSTER", id='btn-run-biplot-statis', n_clicks=0,
                            style={'backgroundColor': '#5D4037', 'color': 'white', 'fontWeight': 'bold', 'border': 'none', 'borderRadius': '5px', 'height': '38px', 'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center', 'padding': '0 20px', 'cursor': 'pointer'}),
                dcc.Loading(type='circle', color='#5D4037', children=html.Div(id='spinner-run-biplot-statis'), style={'display': 'inline-block', 'marginLeft': '10px', 'verticalAlign': 'middle', 'width': '30px'})
            ]),

            html.Div(id='biplot-vs-statis-results-container', style={'display': 'none'}, children=[
            # Maps Row
            html.Div(className='row', children=[
                html.Div(className='six columns', children=[
                    html.H6(id='title-biplot-vs-statis-map-biplot', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='biplot-vs-statis-map-biplot', style={'height': '500px'})])
                ]),
                html.Div(className='six columns', children=[
                    html.H6(id='title-biplot-vs-statis-map-statis', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='biplot-vs-statis-map-statis', style={'height': '500px'})])
                ])
            ]),
            
            # Scatter Row
            html.Div(className='row', style={'marginTop': '15px'}, children=[
                html.Div(className='six columns', children=[
                    html.H6(id='title-biplot-vs-statis-scatter-biplot', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='biplot-vs-statis-scatter-biplot', style={'height': '500px'})])
                ]),
                html.Div(className='six columns', children=[
                    html.H6(id='title-biplot-vs-statis-scatter-statis', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='biplot-vs-statis-scatter-statis', style={'height': '500px'})])
                ])
            ]),
            
            # Pie Row
            html.Div(className='row', style={'marginTop': '15px'}, children=[
                html.Div(className='six columns', children=[
                    html.H6(id='title-biplot-vs-statis-pie-biplot', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='biplot-vs-statis-pie-biplot', style={'height': '400px'})])
                ]),
                html.Div(className='six columns', children=[
                    html.H6(id='title-biplot-vs-statis-pie-statis', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='biplot-vs-statis-pie-statis', style={'height': '400px'})])
                ])
            ]),
            html.Hr(),
            
            html.Div(style={'display': 'flex', 'justifyContent': 'center', 'marginBottom': '10px'}, children=[
                dcc.RadioItems(id='biplot-vs-statis-view-mode', options=[
                    {'label': ' Tampilkan Jumlah', 'value': 'count'}, 
                    {'label': ' Tampilkan Nama Daerah', 'value': 'names'}
                ], value='count', inline=True, inputStyle={"marginRight": "5px", "marginLeft": "15px"})
            ]),
            
            dcc.Loading(children=[
                dash_table.DataTable(id='biplot-vs-statis-table', style_table={'overflowX': 'auto'}, 
                                     style_header={'backgroundColor': '#37474F', 'color': 'white', 'fontWeight': 'bold'}, 
                                     style_cell={'textAlign': 'center', 'padding': '8px', 'fontFamily': 'sans-serif'})
            ]),
            html.Div(style={'textAlign': 'center', 'marginTop': '10px'}, children=[
                html.Button("Unduh Tabel sebagai .TEX", id="btn-dl-biplot-statis-tex", style={'backgroundColor': '#607D8B', 'color': 'white', 'border': 'none', 'borderRadius': '3px', 'cursor': 'pointer', 'height': '32px', 'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center', 'padding': '0 15px', 'fontSize': '12px'}),
                dcc.Download(id="download-biplot-statis-tex")
            ])
            ])  # end biplot-vs-statis-results-container
        ]),

        # --- SECTION: PERBANDINGAN CLUSTER KOMPROMI STATIS VS CLUSTER STATIS TAHUNAN ---
        html.Div(style=CARD_STYLE, children=[
            html.H5("Perbandingan Klaster Kompromi STATIS vs Klaster STATIS Tahunan", 
                    style={'textAlign': 'center', 'fontWeight': 'bold', 'color': '#33691E'}),
            html.P("Membandingkan stabilitas anggota klaster antara hasil 'Kompromi' (STATIS Trajektori Keseluruhan) dengan hasil STATIS per Tahun.", 
                   style={'textAlign': 'center', 'color': '#546E7A', 'marginBottom': '20px'}),
            
            html.Div(className='row', style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'marginBottom': '20px'}, children=[
                html.Div([
                    html.Label("Tahun:", style={'fontWeight': 'bold', 'marginRight': '8px'}),
                    dcc.Dropdown(id='compromise-statis-vs-statis-year', clearable=False, style={'width': '120px'})
                ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px'}),
                
                html.Div([
                    html.Label("Jumlah Klaster (k):", style={'fontWeight': 'bold', 'marginRight': '8px'}),
                    dcc.Input(id='compromise-statis-vs-statis-k', type='number', value=3, min=2, max=10, style={'width': '60px'})
                ], style={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px'}),
                
                html.Button("BANDINGKAN CLUSTER", id='btn-run-compromise-statis-vs-statis', n_clicks=0,
                            style={'backgroundColor': '#33691E', 'color': 'white', 'fontWeight': 'bold', 'border': 'none', 'borderRadius': '5px', 'height': '38px', 'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center', 'padding': '0 20px', 'cursor': 'pointer'}),
                dcc.Loading(type='circle', color='#33691E', children=html.Div(id='spinner-run-compromise-statis-vs-statis'), style={'display': 'inline-block', 'marginLeft': '10px', 'verticalAlign': 'middle', 'width': '30px'})
            ]),

            html.Div(id='compromise-statis-vs-statis-results-container', style={'display': 'none'}, children=[
            # Maps Row
            html.Div(className='row', children=[
                html.Div(className='six columns', children=[
                    html.H6(id='title-compromise-statis-vs-statis-map-comp', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='compromise-statis-vs-statis-map-comp', style={'height': '500px'})])
                ]),
                html.Div(className='six columns', children=[
                    html.H6(id='title-compromise-statis-vs-statis-map-statis', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='compromise-statis-vs-statis-map-statis', style={'height': '500px'})])
                ])
            ]),
            
            # Scatter Row
            html.Div(className='row', style={'marginTop': '15px'}, children=[
                html.Div(className='six columns', children=[
                    html.H6(id='title-compromise-statis-vs-statis-scatter-comp', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='compromise-statis-vs-statis-scatter-comp', style={'height': '500px'})])
                ]),
                html.Div(className='six columns', children=[
                    html.H6(id='title-compromise-statis-vs-statis-scatter-statis', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='compromise-statis-vs-statis-scatter-statis', style={'height': '500px'})])
                ])
            ]),
            
            # Pie Row
            html.Div(className='row', style={'marginTop': '15px'}, children=[
                html.Div(className='six columns', children=[
                    html.H6(id='title-compromise-statis-vs-statis-pie-comp', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='compromise-statis-vs-statis-pie-comp', style={'height': '400px'})])
                ]),
                html.Div(className='six columns', children=[
                    html.H6(id='title-compromise-statis-vs-statis-pie-statis', style={'textAlign': 'center', 'fontWeight': 'bold'}),
                    dcc.Loading(children=[dcc.Graph(id='compromise-statis-vs-statis-pie-statis', style={'height': '400px'})])
                ])
            ]),
            html.Hr(),
            
            html.Div(style={'display': 'flex', 'justifyContent': 'center', 'marginBottom': '10px'}, children=[
                dcc.RadioItems(id='compromise-statis-vs-statis-view-mode', options=[
                    {'label': ' Tampilkan Jumlah', 'value': 'count'}, 
                    {'label': ' Tampilkan Nama Daerah', 'value': 'names'}
                ], value='count', inline=True, inputStyle={"marginRight": "5px", "marginLeft": "15px"})
            ]),
            
            dcc.Loading(children=[
                dash_table.DataTable(id='compromise-statis-vs-statis-table', style_table={'overflowX': 'auto'}, 
                                     style_header={'backgroundColor': '#37474F', 'color': 'white', 'fontWeight': 'bold'}, 
                                     style_cell={'textAlign': 'center', 'padding': '8px', 'fontFamily': 'sans-serif'})
            ]),
            html.Div(style={'textAlign': 'center', 'marginTop': '10px'}, children=[
                html.Button("Unduh Tabel sebagai .TEX", id="btn-dl-compromise-statis-vs-statis-tex", style={'backgroundColor': '#607D8B', 'color': 'white', 'border': 'none', 'borderRadius': '3px', 'cursor': 'pointer', 'height': '32px', 'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center', 'padding': '0 15px', 'fontSize': '12px'}),
                dcc.Download(id="download-compromise-statis-vs-statis-tex")
            ])
            ])  # end compromise-statis-vs-statis-results-container
        ]),

        # --- SECTION BARU: PROFIL RATA-RATA VARIABEL PER KLASTER ---
        html.Div(style=CARD_STYLE, children=[
            html.H5("Profil Karakteristik Klaster: Rata-rata ± Simpangan Baku per Variabel",
                    style={'textAlign': 'center', 'fontWeight': 'bold', 'color': '#1A237E'}),
            html.P("Visualisasi rata-rata nilai variabel analisis beserta interval kepercayaan (± 1 SD) "
                   "untuk setiap klaster. Pilih metode klasterisasi dan tahun yang ingin dievaluasi.",
                   style={'textAlign': 'center', 'color': '#546E7A', 'marginBottom': '20px'}),

            html.Div(style={'display': 'flex', 'alignItems': 'flex-end', 'justifyContent': 'center',
                            'marginBottom': '20px', 'flexWrap': 'wrap', 'gap': '20px'}, children=[
                html.Div([
                    html.Label("Metode Klasterisasi:", style={'fontWeight': 'bold', 'marginBottom': '5px', 'display': 'block'}),
                    dcc.Dropdown(
                        id='barplot-method-dropdown',
                        options=[
                            {'label': 'Biplot PCA Tahunan', 'value': 'biplot'},
                            {'label': 'STATIS Terbobot Tahunan', 'value': 'statis_yr'},
                            {'label': 'Kompromi STATIS (Trajektori)', 'value': 'kompromi'},
                            {'label': 'Kategori IPM UNDP', 'value': 'ipm_cat'},
                        ],
                        value='kompromi',
                        clearable=False,
                        style={'width': '280px'}
                    )
                ]),

                html.Div(id='barplot-year-container', children=[
                    html.Label("Tahun Data:", style={'fontWeight': 'bold', 'marginBottom': '5px', 'display': 'block'}),
                    dcc.Dropdown(id='barplot-year-dropdown', clearable=False, style={'width': '120px'})
                ]),

                html.Div(id='barplot-k-container', children=[
                    html.Label("Jumlah Klaster (k):", style={'fontWeight': 'bold', 'marginBottom': '5px', 'display': 'block'}),
                    dcc.Input(id='barplot-k-input', type='number', value=3, min=2, max=10,
                              style={'width': '70px', 'height': '36px', 'padding': '4px 8px',
                                     'borderRadius': '4px', 'border': '1px solid #ccc'})
                ]),

                html.Div([
                    html.Button("TAMPILKAN PROFIL KLASTER", id='btn-run-barplot', n_clicks=0,
                                style={'backgroundColor': '#1A237E', 'color': 'white', 'fontWeight': 'bold',
                                       'border': 'none', 'borderRadius': '5px', 'height': '38px',
                                       'display': 'inline-flex', 'alignItems': 'center',
                                       'justifyContent': 'center', 'padding': '0 20px', 'cursor': 'pointer'}),
                    dcc.Loading(type='circle', color='#1A237E',
                                children=html.Div(id='spinner-run-barplot'),
                                style={'display': 'inline-block', 'marginLeft': '10px',
                                       'width': '30px', 'verticalAlign': 'middle'})
                ], style={'display': 'flex', 'alignItems': 'center'})
            ]),

            html.Div(id='barplot-results-container', style={'display': 'none'}, children=[
                html.Div(id='barplot-charts-output')
            ])
        ])
    ])
])

# -----------------------------


# ==========================================

# Import Library



# --- COLOR SYSTEM ---
COLOR_PRIMARY = "#1E3A8A" # Royal Blue
COLOR_ACCENT = "#2563EB"
COLOR_BG = "#F8FAFC"
COLOR_CARD_BG = "#FFFFFF"
COLOR_BORDER = "#E2E8F0"

# --- CLUSTER LABELING ---
CLUSTER_COLOR_MAP = {
    "Klaster 1 (Rendah)": "#EF5350",           # Merah (Rendah)
    "Klaster 2 (Sedang)": "#FFB300",           # Kuning/Oranye (Sedang)
    "Klaster 3 (Tinggi)": "#4CAF50",           # Hijau (Tinggi)
    "Klaster 4 (Sangat Tinggi)": "#42A5F5"     # Biru
}
LEVEL_ORDER = ["Klaster 4 (Sangat Tinggi)", "Klaster 3 (Tinggi)", "Klaster 2 (Sedang)", "Klaster 1 (Rendah)"]
IPM_COLOR_MAP = {
    "Sangat Tinggi": "#1565C0",      # Biru Tua
    "Tinggi": "#4CAF50",             # Hijau
    "Sedang": "#FFB300",             # Kuning/Oranye
    "Rendah": "#EF5350"              # Merah
}

# Order legend agar selalu sama
LEVEL_ORDER = ["Level 1 (Rendah)", "Level 2 (Sedang)", "Level 3 (Tinggi)", "Level 4", "Level 5"]
IPM_ORDER = ["Sangat Tinggi", "Tinggi", "Sedang", "Rendah"]


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
        
        # --- [NEW] AUTOMATIC NAME NORMALIZATION WITH SHAPEFILE ---
        valid_peta = gdf['id_cocok'].unique().tolist() if gdf is not None else []
        norm_to_valid = {str(v).strip().lower(): v for v in valid_peta}
        
        name_map = {}
        for k in kab_kota:
            k_clean = str(k).strip()
            if k in valid_peta:
                name_map[k] = k
            elif k_clean.lower() in norm_to_valid:
                name_map[k] = norm_to_valid[k_clean.lower()]
            else:
                import difflib
                suggestions = difflib.get_close_matches(k_clean, valid_peta, n=1, cutoff=0.6)
                if suggestions:
                    name_map[k] = suggestions[0]
                else:
                    clean_valid = [v for v in valid_peta if k_clean.lower() in str(v).lower() or any(sub in str(v).lower() for sub in k_clean.lower().split())]
                    if clean_valid:
                        name_map[k] = clean_valid[0]
                    else:
                        name_map[k] = k
        
        df_concat['Kabupaten/Kota'] = df_concat['Kabupaten/Kota'].map(name_map)
        kab_kota = df_concat['Kabupaten/Kota'].unique().tolist()
        
        # --- [NEW] VALIDASI NAMA EKSAK DENGAN SHAPEFILE ---
        import difflib
        valid_peta = gdf['id_cocok'].unique().tolist() if gdf is not None else []
        norm_to_valid = {str(v).strip().lower(): v for v in valid_peta}
        
        matches = []
        mismatches = []
        for k in kab_kota:
            k_clean = str(k).strip()
            if k in valid_peta:
                matches.append(k)
            elif k_clean.lower() in norm_to_valid:
                matches.append(k)
            else:
                mismatches.append(k)
        
        report_items = []
        
        # Bagian 1: Ringkasan & Sukses
        report_items.append(html.Div([
            html.Strong(f"✅ Berhasil Memuat: {filename}"),
            html.P(f"Total: {len(kab_kota)} Wilayah di Excel | {len(matches)} Cocok Eksak dengan Peta."),
        ], style={'marginBottom': '15px'}))

        if matches:
            report_items.append(html.Div([
                html.Span("Daftar Wilayah Sesuai (Eksak): ", style={'fontWeight': 'bold', 'color': '#2E7D32'}),
                html.Span(", ".join(matches), style={'fontSize': '13px'})
            ], style={'backgroundColor': '#E8F5E9', 'padding': '10px', 'borderRadius': '5px', 'marginBottom': '10px'}))

        # Bagian 2: Mismatch & Saran
        if mismatches:
            mismatch_ui = []
            for m in mismatches:
                m_clean = str(m).strip()
                suggestions = difflib.get_close_matches(m_clean, valid_peta, n=1, cutoff=0.5)
                if not suggestions:
                    clean_valid = [v for v in valid_peta if m_clean.lower() in str(v).lower() or any(sub in str(v).lower() for sub in m_clean.lower().split())]
                    if clean_valid:
                        suggestions = [clean_valid[0]]
                saran_txt = f" (Saran: '{suggestions[0]}')" if suggestions else " (Tidak ditemukan saran)"
                mismatch_ui.append(html.Li([
                    html.Span(f"'{m}'", style={'fontWeight': 'bold', 'color': '#C62828'}),
                    html.Span(saran_txt, style={'fontStyle': 'italic', 'color': '#546E7A'})
                ]))
            
            report_items.append(html.Div([
                html.Strong("⚠️ Wilayah Belum Sesuai (Penting untuk Moran & Map):", style={'color': '#D84315'}),
                html.P("Pastikan nama di Excel persis seperti saran di bawah agar dapat dipetakan:", style={'fontSize': '13px', 'marginTop': '5px'}),
                html.Ul(mismatch_ui, style={'fontSize': '13px', 'columnCount': '2' if len(mismatches) > 10 else '1'})
            ], style={'backgroundColor': '#FFF3E0', 'padding': '15px', 'borderRadius': '5px', 'border': '1px solid #FFE0B2', 'marginTop': '10px'}))

        store = {
            'df_json': df_concat.to_json(orient='split'), 
            'base_features': base_features, 
            'kab_kota': kab_kota, 
            'years': years, 
            'sheet_names': sheet_names
        }
        
        return store, html.Div(report_items, style={'padding': '15px', 'borderRadius': '8px', 'border': '1px solid #CFD8DC', 'backgroundColor': 'white'})

    except Exception as e:
        error_msg = html.Div([
            html.Strong("Error!"), f" Terjadi kesalahan saat memproses file: {str(e)}"
        ], style={'backgroundColor': '#FFEBEE', 'color': '#C62828', 'padding': '15px', 'borderRadius': '5px', 'border': '1px solid #EF9A9A', 'textAlign': 'center'})
        return None, error_msg
    
# 2. Controls & Dropdowns Sync
@app.callback(
    Output('variable-dropdown-final', 'options'), Output('variable-dropdown-final', 'value'),
    Output('trajectory-dropdown-final', 'options'), Output('year-checklist-final', 'options'), Output('year-checklist-final', 'value'),
    Output('mirror-year-checklist-final', 'options'), 
    Output('mirror-year-checklist-statis', 'options'),
    Output('year-dropdown-2d-single', 'options'), Output('year-dropdown-2d-single', 'value'),
    Output('baseline-name-final', 'options'), 
    Output('eval-year-dropdown', 'options'), Output('eval-year-dropdown', 'value'),
    Output('trans-year-dropdown', 'options'), Output('trans-year-dropdown', 'value'),
    Output('weighted-trans-year-dropdown', 'options'), Output('weighted-trans-year-dropdown', 'value'),
    Output('ipm-trans-year-dropdown', 'options'), Output('ipm-trans-year-dropdown', 'value'),
    Output('cross-year-dropdown', 'options'), Output('cross-year-dropdown', 'value'),
    Output('desc-year-dropdown', 'options'), Output('desc-year-dropdown', 'value'),
    Output('desc-weight-var-dropdown', 'options'), Output('desc-weight-var-dropdown', 'value'),
    Output('biplot-vs-statis-year', 'options'), Output('biplot-vs-statis-year', 'value'),
    Output('statis-year-dropdown-2d-single', 'options'), Output('statis-year-dropdown-2d-single', 'value'),
    Output('compare-year-dropdown', 'options'), Output('compare-year-dropdown', 'value'),
    Output('biplot-statis-compare-year', 'options'), Output('biplot-statis-compare-year', 'value'),
    Output('desc-exclude-vars', 'options'),
    Output('weight-var-statis-dropdown', 'options'), Output('weight-var-statis-dropdown', 'value'),
    Input('global-data-store', 'data'), Input('baseline-type-final', 'value')
)
def cb_controls(data, base_type):
    if not data: raise exceptions.PreventUpdate
    feats, kabs, years = data['base_features'], data['kab_kota'], data['years']
    traj_opts = ([{'label': f'{k} (Kab/Kota)', 'value': f'skor_{k}'} for k in kabs] + 
                 [{'label': f'{f} (Variabel)', 'value': f'loading_{f}'} for f in feats])
    y_opts = [{'label': str(y), 'value': y} for y in years]
    f_opts = [{'label': f, 'value': f} for f in feats]
    base_opts = [{'label': f, 'value': f} for f in (feats if base_type == 'loading' else kabs)]
    
    trans_y_opts = []
    for i in range(1, len(years)):
        trans_y_opts.append({'label': f"{years[i-1]} / {years[i]}", 'value': years[i]})

    default_weight = None
    for f in feats:
        if f.lower() in ['jp', 'jumlah penduduk', 'jumlah_penduduk', 'penduduk']:
            default_weight = f
            break
    
    return (
        f_opts, feats, traj_opts, y_opts, years, y_opts, y_opts, y_opts, years[0], base_opts,
        y_opts, years[-1], trans_y_opts, (trans_y_opts[-1]['value'] if trans_y_opts else None),
        trans_y_opts, (trans_y_opts[-1]['value'] if trans_y_opts else None),
        trans_y_opts, (trans_y_opts[-1]['value'] if trans_y_opts else None),
        y_opts, years[-1], y_opts, years[-1], f_opts, default_weight, y_opts, years[-1],
        y_opts, years[0], y_opts, years[-1], y_opts, years[-1],
        f_opts, f_opts, default_weight
    )

# 2b. Sync Vector Selector with Selected Vars
@app.callback(
    Output('vector-selector-final', 'options'),
    Input('variable-dropdown-final', 'value')
)
def cb_sync_vector_selector(selected_vars):
    if not selected_vars: return []
    return [{'label': v, 'value': v} for v in selected_vars]


# 2c. Sync Year options for the new comparison cards
@app.callback(
    Output('statis-vs-ipm-year', 'options'), Output('statis-vs-ipm-year', 'value'),
    Output('compromise-statis-vs-statis-year', 'options'), Output('compromise-statis-vs-statis-year', 'value'),
    Output('statis-vs-ipm-avg-year', 'options'), Output('statis-vs-ipm-avg-year', 'value'),
    Input('global-data-store', 'data')
)
def cb_sync_new_dropdowns(data):
    if not data: raise exceptions.PreventUpdate
    years = data['years']
    y_opts = [{'label': str(y), 'value': y} for y in years]
    return y_opts, years[-1], y_opts, years[-1], y_opts, years[-1]

# 3. Dynamic PCA Calculation
@app.callback(
    Output('pca-results-store', 'data'),
    Input('btn-run-statis', 'n_clicks'),
    State('variable-dropdown-final', 'value'),
    State('global-data-store', 'data'),
    State('weight-var-statis-dropdown', 'value')
)
def cb_pca_calc(n_clicks, vars, data, weight_var):
    if not n_clicks or not vars or not data: raise exceptions.PreventUpdate
    analysis_vars = [v for v in vars if v != weight_var] if weight_var else vars
    if not analysis_vars: raise exceptions.PreventUpdate
    df = pd.read_json(io.StringIO(data['df_json']), orient='split')
    pc_list, load_list = [], []
    for y in data['years']:
        df_y = df[df['Tahun'] == y]
        if df_y.empty: continue
        X = df_y[analysis_vars]
        pca = PCA(n_components=2)
        scaler = StandardScaler()
        coords = pca.fit_transform(scaler.fit_transform(X))
        loadings = pca.components_.T.copy()  # shape (n_features, 2)
        # Deterministic sign convention: largest-abs loading per PC must be positive.
        # Fixes SVD sign indeterminacy across LAPACK/numpy versions (e.g. local vs HuggingFace).
        for i in range(2):
            max_idx = np.argmax(np.abs(loadings[:, i]))
            if loadings[max_idx, i] < 0:
                loadings[:, i] *= -1
                coords[:, i] *= -1
        d_sc = df_y[['Kabupaten/Kota', 'Provinsi', 'Tahun']].copy()
        d_sc['PC1'], d_sc['PC2'] = coords[:,0], coords[:,1]
        pc_list.append(d_sc)
        d_load = pd.DataFrame(loadings, columns=['PC1', 'PC2'])
        try:
            sv = np.array(pca.singular_values_)[:2]
        except Exception:
            sv = np.array([1.0, 1.0])
        d_load['SV1'], d_load['SV2'] = sv[0], sv[1]
        d_load['features'], d_load['Tahun'] = analysis_vars, y
        load_list.append(d_load)
    return {'pc_scores': pd.concat(pc_list).to_json(orient='split'), 'loadings': pd.concat(load_list).to_json(orient='split')}

# 4a. Update note variabel analisis ketika variabel bobot berubah
@app.callback(
    Output('weight-var-statis-exclude-note', 'children'),
    Input('weight-var-statis-dropdown', 'value'),
    prevent_initial_call=False
)
def cb_weight_var_note(weight_var):
    if weight_var:
        return f'⚠ "{weight_var}" dikecualikan dari variabel analisis.'
    return ''

# 4. STATIS Core Calculation
@app.callback(
    Output('statis-core-store', 'data'),
    Output('statis-error-msg', 'children'),
    Output('spinner-run-statis', 'children'),
    Input('btn-run-statis', 'n_clicks'),
    State('variable-dropdown-final', 'value'),
    State('upload-data', 'contents'),
    State('global-data-store', 'data'),
    State('statis-scenario', 'value'),
    State('weight-var-statis-dropdown', 'value'),
    State('statis-mirror-opts', 'value'),
    prevent_initial_call=True
)
def cb_statis_calc(n_clicks, vars, contents, global_data, scenario, weight_var, mirror_opts):
    if not n_clicks or not vars or not contents or not global_data:
        raise exceptions.PreventUpdate
    # Keluarkan variabel bobot dari variabel analisis
    analysis_vars = [v for v in vars if v != weight_var] if weight_var else vars
    if not analysis_vars:
        return None, "❌ Tidak ada variabel analisis tersisa setelah variabel bobot dikecualikan.", ""
    try:
        print("--- [STATIS_CORE] MEMULAI PENGHITUNGAN ---")
        res = run_statis_core(contents, analysis_vars, global_data['sheet_names'], scenario=scenario, weight_var=weight_var)

        # --- Terapkan Mirror PC1/PC2 jika diminta ---
        mirror_opts = mirror_opts or []
        flip1 = -1.0 if 'mirror_pc1' in mirror_opts else 1.0
        flip2 = -1.0 if 'mirror_pc2' in mirror_opts else 1.0
        if flip1 != 1.0 or flip2 != 1.0:
            def _flip(arr2d):
                a = np.array(arr2d, dtype=float)
                a[:, 0] *= flip1; a[:, 1] *= flip2
                return a.tolist()
            res['scores'] = _flip(res['scores'])
            res['loadings'] = _flip(res['loadings'])
            if 'scores_svd' in res: res['scores_svd'] = _flip(res['scores_svd'])
            if 'loadings_svd' in res: res['loadings_svd'] = _flip(res['loadings_svd'])
            for yr in res.get('per_year_coords', {}):
                res['per_year_coords'][yr] = _flip(res['per_year_coords'][yr])
            for yr in res.get('sheet_names', []):
                gk = fr"Loading Intra \mathbf{{G}}_{{{yr}}}"
                if gk in res:
                    for rec in res[gk]:
                        if 'PC1' in rec: rec['PC1'] = float(rec['PC1']) * flip1
                        if 'PC2' in rec: rec['PC2'] = float(rec['PC2']) * flip2
        res['mirror_opts'] = mirror_opts

        # --- [TAMBAHAN] Injeksi Metadata Provinsi & Index untuk Visualisasi ---
        try:
            df_full = pd.read_json(io.StringIO(global_data['df_json']), orient='split')
            # NORMALIZE METADATA
            df_full['Kabupaten/Kota'] = df_full['Kabupaten/Kota'].astype(str).str.strip().str.upper()
            df_full['Provinsi'] = df_full['Provinsi'].astype(str).str.strip().str.upper()
            
            # Ambil mapping Kab/Kota -> Provinsi (unik per nama)
            prov_map = df_full.drop_duplicates('Kabupaten/Kota').set_index('Kabupaten/Kota')['Provinsi'].to_dict()
            res['prov_map'] = prov_map
            # Index wilayah (1-indexed) berdasarkan urutan obs_labels
            res['kab_index_map'] = {name: i+1 for i, name in enumerate(res['obs_labels'])}
            
            # --- [NEW] Hitung Vektor Struktur beta_tilde ---
            province_map_inv = {}
            for kab, prov in prov_map.items():
                if prov not in province_map_inv:
                    province_map_inv[prov] = []
                province_map_inv[prov].append(kab)
            
            # Filter province_map_inv agar hanya berisi wilayah yang ada di obs_labels
            obs_labels_set = set([str(x).strip().upper() for x in res['obs_labels']])
            province_map_inv_filtered = {}
            for p, kabs in province_map_inv.items():
                filtered_kabs = [k for k in kabs if k in obs_labels_set]
                if len(filtered_kabs) >= 2:
                    province_map_inv_filtered[p] = filtered_kabs
            
            sv_res = compute_structure_vector(
                H=res['H'], 
                alphas=np.array(res['alphas']), 
                sheet_names=res['sheet_names'], 
                X_matrices=[np.array(x) for x in res['X_matrices']], 
                m_weights=np.array(res['m_weights']), 
                obs_labels=res['obs_labels'],
                province_map=province_map_inv_filtered,
                scenario=scenario
            )
            res['structure_vector_res'] = sv_res
            
            # Format beta ke Tabel (USER REQUEST: Tables for Beta, Eigenvector, Eigenvalue)
            # 1. Tabel komponen beta_tilde per tahun (Global)
            beta_vec_table = []
            for i, yr in enumerate(res['sheet_names']):
                beta_vec_table.append({
                    'Tahun (k)': yr,
                    'β̃_k = λ₁ u₁ₖ': round(sv_res['beta_tilde'][i], 4)
                })
            res[r'Vektor Struktur (β) - Gabungan'] = beta_vec_table

            # 2. Tabel Vektor Eigen Struktur (u1) - Gabungan & Provinsi
            u1_table = []
            prov_names_sorted = sorted(list(sv_res['u1_provinsi'].keys()))
            for i, yr in enumerate(res['sheet_names']):
                row = {'Tahun (k)': yr, 'Global (u₁)': round(sv_res['u1'][i], 4)}
                for p in prov_names_sorted:
                    row[f'{p} (u₁)'] = round(sv_res['u1_provinsi'][p][i], 4)
                u1_table.append(row)
            res[r'Vektor Eigen Struktur (u₁)'] = u1_table

            # 3. Tabel Nilai Eigen Struktur (λ₁) - Gabungan & Provinsi
            lambda_table = [{'Wilayah': 'Global', 'Nilai Eigen (λ₁)': round(sv_res['lambda1'], 4)}]
            for p in prov_names_sorted:
                lambda_table.append({'Wilayah': p, 'Nilai Eigen (λ₁)': round(sv_res['lambda1_provinsi'][p], 4)})
            res[r'Nilai Eigen Struktur (λ₁)'] = lambda_table

            # 4. Tabel diagnostik dominansi
            diag_table = [
                {'Kuantitas': 'λ₁ (Nilai Eigen Dominan)', 'Nilai': round(sv_res['lambda1'], 4)},
                {'Kuantitas': '‖H‖_F² (Frobenius²)', 'Nilai': round(sv_res['H_frobenius_sq'], 4)},
                {'Kuantitas': 'V (SS Residual)', 'Nilai': round(sv_res['V'], 4)},
                {'Kuantitas': 'V / ‖H‖_F² (Rasio Sisa)', 'Nilai': round(sv_res['V'] / sv_res['H_frobenius_sq'], 4) if sv_res['H_frobenius_sq'] > 0 else 0},
                {'Kuantitas': 'Inertia₁ (Dominansi %)', 'Nilai': f"{sv_res['inertia1']*100:.2f}%"},
                {'Kuantitas': 'λ₁ / λ₂ (Rasio Kegentingan)', 'Nilai': round(sv_res['dominance_ratio'], 4) if np.isfinite(sv_res['dominance_ratio']) else "∞"}
            ]
            res[r'Diagnostik Vektor Struktur'] = diag_table

            # 5. Tabel beta_tilde per provinsi
            beta_prov_table = []
            for i, yr in enumerate(res['sheet_names']):
                row = {'Tahun (k)': yr}
                for p in prov_names_sorted:
                    row[p] = round(sv_res['beta_provinsi'][p][i], 4) if i < len(sv_res['beta_provinsi'][p]) else "-"
                beta_prov_table.append(row)
            res[r'Vektor Struktur (β) - Per Provinsi'] = beta_prov_table

            # --- [AUTO EXPORT] Generate .tex files immediately ---
            export_structure_vector_latex(sv_res, output_dir="../output_app", label_prefix="")

        except Exception as e_meta:
            print(f"Gagal injeksi metadata atau Vektor Struktur: {e_meta}")
            import traceback
            traceback.print_exc()
            
        print("--- [STATIS_CORE] BERHASIL ---")
        return res, "", ""
    except Exception as e:
        import traceback
        err_msg = f"ERROR DI PENGHITUNGAN CORE: {str(e)}"
        print(err_msg)
        traceback.print_exc()
        return None, f"Terjadi kesalahan: {str(e)}", ""

# 4c. SHOW/HIDE SECTIONS CALLBACK
@app.callback(
    Output('biplot-section-container', 'style'),
    Output('statis-biplot-3d-section-container', 'style'),
    Output('distance-comparison-section-container', 'style'),
    Output('statis-section-container', 'style'),
    Input('btn-run-statis', 'n_clicks'),
    prevent_initial_call=True
)
def cb_show_sections(n_clicks):
    if n_clicks and n_clicks > 0:
        style = CARD_STYLE.copy()
        style['display'] = 'block'
        style['marginTop'] = '30px'
        return style, style, style, style
    return {'visibility': 'hidden', 'height': '0', 'overflow': 'hidden', 'margin': '0', 'padding': '0'}, {'visibility': 'hidden', 'height': '0', 'overflow': 'hidden', 'margin': '0', 'padding': '0'}, {'display': 'none'}, {'display': 'none'}

# 4b. DIAGNOSTICS & MATH FORMULAS CALLBACK
@app.callback(
    Output('kmo-result', 'children'),
    Output('kmo-result', 'style'),
    Output('bartlett-result', 'children'),
    Output('bartlett-result', 'style'),
    Output('diag-results-container', 'style'),
    Output('formula-diag-output', 'children'),
    Output('spinner-run-diag', 'children'),
    Input('btn-run-diag', 'n_clicks'),
    State('global-data-store', 'data'),
    State('variable-dropdown-final', 'value'),
    State('weight-var-statis-dropdown', 'value')
)
def cb_diag_math(n_clicks, data_store, vars, weight_var):
    if not n_clicks or not data_store or not vars:
        return "Wait...", {}, "Wait...", {}, {'display': 'none'}, render_diagnostic_formulas(), ""

    # Keluarkan variabel bobot dari variabel analisis KMO
    analysis_vars = [v for v in vars if v != weight_var] if weight_var else vars
    if not analysis_vars:
        return "❌ Tidak ada variabel analisis.", {}, "❌ Tidak ada variabel analisis.", {}, {'display': 'none'}, render_diagnostic_formulas(), ""

    # 1. Diagnostics
    df = pd.read_json(io.StringIO(data_store['df_json']), orient='split')
    df_dict = {y: df[df['Tahun'] == y] for y in data_store['years']}
    kmo_val, p_val, kmo_int, bart_int, n, df_k, r_sq, q_sq, chi2_stat = calc_kmo_bartlett(df_dict, analysis_vars)

    kmo_txt = f"KMO = {kmo_val:.3f} ({kmo_int})"
    bart_txt = f"P-value = {p_val} ({bart_int})" # No Rounding!

    kmo_style = {'fontSize': '16px', 'padding': '10px', 'borderRadius': '5px', 'backgroundColor': '#E8F5E9' if kmo_val >= 0.5 else '#FFEBEE'}
    bart_style = {'fontSize': '16px', 'padding': '10px', 'borderRadius': '5px', 'backgroundColor': '#E8F5E9' if p_val < 0.05 else '#FFEBEE'}

    formula_ui = render_diagnostic_formulas(n, df_k, r_sq, q_sq, kmo_val, kmo_int, chi2_stat, p_val, bart_int)

    return kmo_txt, kmo_style, bart_txt, bart_style, {'display': 'flex'}, formula_ui, ""

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
    if not pca_data or not years_filter: return EMPTY_FIG, EMPTY_FIG, EMPTY_FIG, [], []
    
    norm_score = vis_opts == 'norm_score'
    scale_load = vis_opts == 'scale_load'

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
    # Use per-row singular values stored in PCA results (SV1, SV2)
    sv_rows = df_load_fin[['SV1','SV2']].values if 'SV1' in df_load_fin.columns and 'SV2' in df_load_fin.columns else None
    pc_plot, load_plot = apply_visual_adjustments(
        df_pc_fin[['PC1','PC2']].values,
        df_load_fin[['PC1','PC2']].values,
        norm_score,
        scale_load,
        singular_values=sv_rows
    )
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
                    hoverinfo='text', hovertext=f"Loading: {row['features']}<br>PC (Asli): ({raw['PC1']:.4f}, {raw['PC2']:.4f})<br>PC (Visual): ({row['PC1']:.4f}, {row['PC2']:.4f})"
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
    fig_3d.update_layout(title='Visualisasi 3D (Rotated)', margin=dict(l=0, r=0, b=0, t=30), autosize=True, scene=dict(aspectmode='manual', aspectratio=dict(x=2, y=1, z=1)))

    # 2D
    fig_2d_y = go.Figure()
    if year_2d:
        d_p, d_l = df_pc_plt[df_pc_plt['Tahun']==year_2d], df_load_plt[df_load_plt['Tahun']==year_2d]
        d_l_raw = df_load_fin[df_load_fin['Tahun']==year_2d]
        fig_2d_y.add_trace(go.Scatter(x=d_p['PC1'], y=d_p['PC2'], mode='markers+text', text=d_p['Kabupaten/Kota'], textposition='top center', name='Skor'))
        if load_scope in ['2d', 'both']:
            for idx, r in d_l.iterrows():
                raw = d_l_raw.loc[idx]
                fig_2d_y.add_trace(go.Scatter(x=[0, r['PC1']], y=[0, r['PC2']], mode='lines+text', text=[None, r['features']], textposition='top center', line=dict(color='red'), showlegend=False, hoverinfo='text', hovertext=f"Var: {r['features']}<br>PC (Asli): ({raw['PC1']:.4f}, {raw['PC2']:.4f})<br>PC (Visual): ({r['PC1']:.4f}, {r['PC2']:.4f})"))
    fig_2d_y.update_layout(title=f"Snapshot {year_2d}", xaxis=dict(scaleanchor='y', scaleratio=1), template='plotly_white')

    # Traj 2D
    fig_2d_t = go.Figure()
    table_rows = []
    if traj_sel:
        for sel in traj_sel:
            t_type, t_name = sel.split('_', 1)
            if t_type == 'skor':
                d_t = df_pc_plt[df_pc_plt['Kabupaten/Kota'] == t_name].sort_values('Tahun')
                # Titik akhir sebagai kotak
                symbols = ['circle'] * (len(d_t)-1) + ['square']
                fig_2d_t.add_trace(go.Scatter(
                    x=d_t['PC1'], y=d_t['PC2'], 
                    mode='lines+markers+text', 
                    marker=dict(symbol=symbols, size=8),
                    text=d_t['Tahun'], name=t_name
                ))
                for _, r in d_t.iterrows(): table_rows.append({'Nama':t_name, 'Tahun':r['Tahun'], 'PC1':round(r['PC1'],4), 'PC2':round(r['PC2'],4)})
            elif t_type == 'loading':
                d_t = df_load_plt[df_load_plt['features'] == t_name].sort_values('Tahun')
                symbols = ['circle'] * (len(d_t)-1) + ['square']
                fig_2d_t.add_trace(go.Scatter(
                    x=d_t['PC1'], y=d_t['PC2'], 
                    mode='lines+markers+text', 
                    marker=dict(symbol=symbols, size=8),
                    text=d_t['Tahun'], name=t_name
                ))
                for _, r in d_t.iterrows(): table_rows.append({'Nama':t_name, 'Tahun':r['Tahun'], 'PC1':round(r['PC1'],4), 'PC2':round(r['PC2'],4)})
    fig_2d_t.update_layout(title="Trajektori 2D", xaxis=dict(scaleanchor='y', scaleratio=1), template='plotly_white')
    
    return fig_3d, fig_2d_y, fig_2d_t, table_rows, [{"name": i, "id": i} for i in pd.DataFrame(table_rows).columns] if table_rows else []


@app.callback(
    Output('statis-graph-3d-main', 'figure'), Output('statis-graph-2d-year', 'figure'), Output('statis-graph-2d-traj', 'figure'),
    Output('statis-trajectory-table', 'data'), Output('statis-trajectory-table', 'columns'),
    Input('statis-core-store', 'data'), Input('year-checklist-final', 'value'), Input('mirror-year-checklist-statis', 'value'),
    Input('baseline-type-final', 'value'), Input('baseline-name-final', 'value'), Input('trajectory-dropdown-final', 'value'),
    Input('statis-year-dropdown-2d-single', 'value'), Input('loading-vector-scope-final', 'value'),
    Input('visual-scaling-opts', 'value'), Input('vector-selector-final', 'value'),
    State('global-data-store', 'data')
)
def cb_update_statis_plots(statis_data, years_filter, mirror_years, base_type, base_name, traj_sel, year_2d, load_scope, vis_opts, selected_vectors_to_show, global_data):
    if not statis_data or not years_filter or not global_data: return EMPTY_FIG, EMPTY_FIG, EMPTY_FIG, [], []
    
    norm_score = vis_opts == 'norm_score'
    scale_load = vis_opts == 'scale_load'

    import pandas as pd
    df_global = pd.read_json(io.StringIO(global_data['df_json']), orient='split')
    prov_map = df_global[['Kabupaten/Kota', 'Provinsi']].drop_duplicates().set_index('Kabupaten/Kota')['Provinsi'].to_dict()
    
    pc_list, load_list = [], []
    obs_labels = statis_data['obs_labels']
    for yr in statis_data['sheet_names']:
        if str(yr) not in [str(y) for y in years_filter]: continue
        # Skor Intra F_k
        coords_yr = np.array(statis_data['per_year_coords'][str(yr)])
        d_p = pd.DataFrame({'Kabupaten/Kota': obs_labels, 'Tahun': int(yr)})
        d_p['Provinsi'] = d_p['Kabupaten/Kota'].map(prov_map).fillna('Unknown')
        d_p['PC1'] = coords_yr[:,0]
        d_p['PC2'] = coords_yr[:,1]
        pc_list.append(d_p)
        
        # Loading Intra G_k
        G_key = fr"Loading Intra \mathbf{{G}}_{{{yr}}}"
        if G_key in statis_data:
            df_gk = pd.DataFrame(statis_data[G_key])
            df_gk['Tahun'] = int(yr)
            df_gk = df_gk.rename(columns={'Variabel': 'features'})
            load_list.append(df_gk)
            
    if not pc_list or not load_list: return EMPTY_FIG, EMPTY_FIG, EMPTY_FIG, [], []
    
    df_pc = pd.concat(pc_list, ignore_index=True)
    df_load = pd.concat(load_list, ignore_index=True)
    
    if selected_vectors_to_show and len(selected_vectors_to_show) > 0:
         df_load = df_load[df_load['features'].isin(selected_vectors_to_show)]

    df_pc_fin, df_load_fin = df_pc.copy(), df_load.copy()
    for y in sorted(df_pc['Tahun'].unique()):
        angle = get_rotation_angle(df_pc, df_load, base_type, base_name, y) if base_name else 0
        mask_p, mask_l = df_pc_fin['Tahun'] == y, df_load_fin['Tahun'] == y
        if angle != 0:
            df_pc_fin.loc[mask_p, ['PC1', 'PC2']] = rotate_dataframe(df_pc.loc[mask_p], angle)
            df_load_fin.loc[mask_l, ['PC1', 'PC2']] = rotate_dataframe(df_load.loc[mask_l], angle)
        if mirror_years and str(y) in [str(my) for my in mirror_years]:
            df_pc_fin.loc[mask_p, 'PC2'] *= -1
            df_load_fin.loc[mask_l, 'PC2'] *= -1

    # Visual Scaling (use compromise singular values if available)
    try:
        sv_comp = np.sqrt(np.array(statis_data.get('eig_vals_c', [1, 0]))[:2])
    except Exception:
        sv_comp = None
    pc_plot, load_plot = apply_visual_adjustments(
        df_pc_fin[['PC1','PC2']].values,
        df_load_fin[['PC1','PC2']].values,
        norm_score,
        scale_load,
        singular_values=sv_comp
    )
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
                if idx not in d_l_raw.index: continue
                raw = d_l_raw.loc[idx]
                fig_3d.add_trace(go.Scatter3d(
                    x=[y, y], y=[0, row['PC1']], z=[0, row['PC2']],
                    mode='lines+text', line=dict(color='red', width=1), opacity=0.5,
                    text=[None, str(row['features'])], textposition='top center', showlegend=False,
                    hoverinfo='text', hovertext=f"Loading: {row['features']}<br>PC (Asli): ({raw['PC1']:.4f}, {raw['PC2']:.4f})<br>PC (Visual): ({row['PC1']:.4f}, {row['PC2']:.4f})"
                ))
    if traj_sel:
        for sel in traj_sel:
            if '_' not in sel: continue
            t_type, t_name = sel.split('_', 1)
            if t_type == 'skor':
                d_t = df_pc_plt[df_pc_plt['Kabupaten/Kota'] == t_name].sort_values('Tahun')
                fig_3d.add_trace(go.Scatter3d(x=d_t['Tahun'], y=d_t['PC1'], z=d_t['PC2'], mode='lines+markers', name=t_name))
            elif t_type == 'loading':
                d_t = df_load_plt[df_load_plt['features'] == t_name].sort_values('Tahun')
                if not d_t.empty: fig_3d.add_trace(go.Scatter3d(x=d_t['Tahun'], y=d_t['PC1'], z=d_t['PC2'], mode='lines+markers', name=t_name))
    fig_3d.update_layout(title='Visualisasi 3D STATIS (Rotated)', margin=dict(l=0, r=0, b=0, t=30), autosize=True, scene=dict(aspectmode='manual', aspectratio=dict(x=2, y=1, z=1)))

    # 2D
    fig_2d_y = go.Figure()
    if year_2d:
        d_p, d_l = df_pc_plt[df_pc_plt['Tahun']==int(year_2d)], df_load_plt[df_load_plt['Tahun']==int(year_2d)]
        d_l_raw = df_load_fin[df_load_fin['Tahun']==int(year_2d)]
        fig_2d_y.add_trace(go.Scatter(x=d_p['PC1'], y=d_p['PC2'], mode='markers+text', text=d_p['Kabupaten/Kota'], textposition='top center', name='Skor'))
        if load_scope in ['2d', 'both']:
            for idx, r in d_l.iterrows():
                if idx not in d_l_raw.index: continue
                raw = d_l_raw.loc[idx]
                fig_2d_y.add_trace(go.Scatter(x=[0, r['PC1']], y=[0, r['PC2']], mode='lines+text', text=[None, r['features']], textposition='top center', line=dict(color='red'), showlegend=False, hoverinfo='text', hovertext=f"Var: {r['features']}<br>PC (Asli): ({raw['PC1']:.4f}, {raw['PC2']:.4f})<br>PC (Visual): ({r['PC1']:.4f}, {r['PC2']:.4f})"))
    fig_2d_y.update_layout(title=f"Snapshot 2D STATIS {year_2d}", xaxis=dict(scaleanchor='y', scaleratio=1), template='plotly_white')

    # Traj 2D
    fig_2d_t = go.Figure()
    table_rows = []
    if traj_sel:
        for sel in traj_sel:
            if '_' not in sel: continue
            t_type, t_name = sel.split('_', 1)
            if t_type == 'skor':
                d_t = df_pc_plt[df_pc_plt['Kabupaten/Kota'] == t_name].sort_values('Tahun')
                symbols = ['circle'] * (len(d_t)-1) + ['square']
                fig_2d_t.add_trace(go.Scatter(
                    x=d_t['PC1'], y=d_t['PC2'], 
                    mode='lines+markers+text', 
                    marker=dict(symbol=symbols, size=8),
                    text=d_t['Tahun'], name=t_name
                ))
                for _, r in d_t.iterrows(): table_rows.append({'Nama':t_name, 'Tahun':r['Tahun'], 'PC1':round(r['PC1'],4), 'PC2':round(r['PC2'],4)})
            elif t_type == 'loading':
                d_t = df_load_plt[df_load_plt['features'] == t_name].sort_values('Tahun')
                symbols = ['circle'] * (len(d_t)-1) + ['square']
                fig_2d_t.add_trace(go.Scatter(
                    x=d_t['PC1'], y=d_t['PC2'], 
                    mode='lines+markers+text', 
                    marker=dict(symbol=symbols, size=8),
                    text=d_t['Tahun'], name=t_name
                ))
                for _, r in d_t.iterrows(): table_rows.append({'Nama':t_name, 'Tahun':r['Tahun'], 'PC1':round(r['PC1'],4), 'PC2':round(r['PC2'],4)})
    fig_2d_t.update_layout(title="Trajektori 2D STATIS", xaxis=dict(scaleanchor='y', scaleratio=1), template='plotly_white')
    
    return fig_3d, fig_2d_y, fig_2d_t, table_rows, [{"name": i, "id": i} for i in pd.DataFrame(table_rows).columns] if table_rows else []


@app.callback(
    Output('compare-distance-table', 'data'), Output('compare-distance-table', 'columns'),
    Input('compare-year-dropdown', 'value'), Input('compare-data-type', 'value'),
    Input('pca-results-store', 'data'), Input('statis-core-store', 'data'),
    State('year-checklist-final', 'value'), State('mirror-year-checklist-final', 'value'),
    State('baseline-type-final', 'value'), State('baseline-name-final', 'value'),
    State('visual-scaling-opts', 'value'), State('vector-selector-final', 'value')
)
def cb_compare_distance(compare_year, data_type, pca_res, statis_res, years_filter, mirror_years, base_type, base_name, vis_opts, selected_vectors):
    if not compare_year or not data_type or not pca_res or not statis_res: return [], []
    
    norm_score = vis_opts == 'norm_score'
    scale_load = vis_opts == 'scale_load'

    import pandas as pd
    import numpy as np

    # 1. Compute PCA unweighted
    df_pc_u = pd.read_json(io.StringIO(pca_res['pc_scores']), orient='split')
    df_load_u = pd.read_json(io.StringIO(pca_res['loadings']), orient='split')
    
    if selected_vectors and len(selected_vectors) > 0:
         df_load_u = df_load_u[df_load_u['features'].isin(selected_vectors)]
         
    df_pc_plt, df_load_plt = df_pc_u.copy(), df_load_u.copy()
    for y in sorted(df_pc_u['Tahun'].unique()):
        angle = get_rotation_angle(df_pc_u, df_load_u, base_type, base_name, y) if base_name else 0
        mask_p, mask_l = df_pc_plt['Tahun'] == y, df_load_plt['Tahun'] == y
        if angle != 0:
            df_pc_plt.loc[mask_p, ['PC1', 'PC2']] = rotate_dataframe(df_pc_u.loc[mask_p], angle)
            df_load_plt.loc[mask_l, ['PC1', 'PC2']] = rotate_dataframe(df_load_u.loc[mask_l], angle)
        if mirror_years and str(y) in [str(my) for my in mirror_years]:
            df_pc_plt.loc[mask_p, 'PC2'] *= -1
            df_load_plt.loc[mask_l, 'PC2'] *= -1
            
    sv_u = df_load_u[['SV1','SV2']].values if 'SV1' in df_load_u.columns and 'SV2' in df_load_u.columns else None
    pc_p, load_p = apply_visual_adjustments(
        df_pc_plt[['PC1','PC2']].values,
        df_load_plt[['PC1','PC2']].values,
        norm_score,
        scale_load,
        singular_values=sv_u
    )
    df_pc_u_final = df_pc_plt.copy(); df_pc_u_final[['PC1','PC2']] = pc_p
    df_load_u_final = df_load_plt.copy(); df_load_u_final[['PC1','PC2']] = load_p
    
    # 2. Compute STATIS weighted
    pc_list, load_list = [], []
    obs_labels = statis_res['obs_labels']
    for yr in statis_res['sheet_names']:
        coords_yr = np.array(statis_res['per_year_coords'][str(yr)])
        d_p = pd.DataFrame({'Kabupaten/Kota': obs_labels, 'Tahun': int(yr)})
        d_p['PC1'] = coords_yr[:,0]
        d_p['PC2'] = coords_yr[:,1]
        pc_list.append(d_p)
        
        G_key = fr"Loading Intra \mathbf{{G}}_{{{yr}}}"
        if G_key in statis_res:
            df_gk = pd.DataFrame(statis_res[G_key])
            df_gk['Tahun'] = int(yr)
            df_gk = df_gk.rename(columns={'Variabel': 'features'})
            load_list.append(df_gk)
            
    df_pc_w = pd.concat(pc_list, ignore_index=True)
    df_load_w = pd.concat(load_list, ignore_index=True)
    
    if selected_vectors and len(selected_vectors) > 0:
         df_load_w = df_load_w[df_load_w['features'].isin(selected_vectors)]
         
    df_pc_w_plt, df_load_w_plt = df_pc_w.copy(), df_load_w.copy()
    for y in sorted(df_pc_w['Tahun'].unique()):
        angle = get_rotation_angle(df_pc_w, df_load_w, base_type, base_name, y) if base_name else 0
        mask_p, mask_l = df_pc_w_plt['Tahun'] == y, df_load_w_plt['Tahun'] == y
        if angle != 0:
            df_pc_w_plt.loc[mask_p, ['PC1', 'PC2']] = rotate_dataframe(df_pc_w.loc[mask_p], angle)
            df_load_w_plt.loc[mask_l, ['PC1', 'PC2']] = rotate_dataframe(df_load_w.loc[mask_l], angle)
        if mirror_years and str(y) in [str(my) for my in mirror_years]:
            df_pc_w_plt.loc[mask_p, 'PC2'] *= -1
            df_load_w_plt.loc[mask_l, 'PC2'] *= -1
            
    sv_w = None
    try:
        sv_w = np.sqrt(np.array(statis_res.get('eig_vals_c', [1, 0]))[:2])
    except Exception:
        sv_w = None
    pc_p_w, load_p_w = apply_visual_adjustments(
        df_pc_w_plt[['PC1','PC2']].values,
        df_load_w_plt[['PC1','PC2']].values,
        norm_score,
        scale_load,
        singular_values=sv_w
    )
    df_pc_w_final = df_pc_w_plt.copy(); df_pc_w_final[['PC1','PC2']] = pc_p_w
    df_load_w_final = df_load_w_plt.copy(); df_load_w_final[['PC1','PC2']] = load_p_w
    
    # 3. Filter for comparison
    table_data = []
    if data_type == 'scores':
        df_u_sub = df_pc_u_final[df_pc_u_final['Tahun'] == int(compare_year)]
        df_w_sub = df_pc_w_final[df_pc_w_final['Tahun'] == int(compare_year)]
        
        for _, r_u in df_u_sub.iterrows():
            name = r_u['Kabupaten/Kota']
            r_w = df_w_sub[df_w_sub['Kabupaten/Kota'] == name]
            if not r_w.empty:
                r_w = r_w.iloc[0]
                dist = np.sqrt((r_u['PC1'] - r_w['PC1'])**2 + (r_u['PC2'] - r_w['PC2'])**2)
                table_data.append({
                    "Nama": name, "Tahun": compare_year,
                    "PC1 (PCA)": round(r_u['PC1'], 4), "PC2 (PCA)": round(r_u['PC2'], 4),
                    "PC1 (STATIS)": round(r_w['PC1'], 4), "PC2 (STATIS)": round(r_w['PC2'], 4),
                    "Dampak Pembobotan": round(dist, 4)
                })
    else:
        df_u_sub = df_load_u_final[df_load_u_final['Tahun'] == int(compare_year)]
        df_w_sub = df_load_w_final[df_load_w_final['Tahun'] == int(compare_year)]

        for _, r_u in df_u_sub.iterrows():
            name = r_u['features']
            r_w = df_w_sub[df_w_sub['features'] == name]
            if not r_w.empty:
                r_w = r_w.iloc[0]
                dist = np.sqrt((r_u['PC1'] - r_w['PC1'])**2 + (r_u['PC2'] - r_w['PC2'])**2)
                table_data.append({
                    "Nama": name, "Tahun": compare_year,
                    "PC1 (PCA)": round(r_u['PC1'], 4), "PC2 (PCA)": round(r_u['PC2'], 4),
                    "PC1 (STATIS)": round(r_w['PC1'], 4), "PC2 (STATIS)": round(r_w['PC2'], 4),
                    "Dampak Pembobotan": round(dist, 4)
                })
                
    cols = [{"name": i, "id": i} for i in pd.DataFrame(table_data).columns] if table_data else []
    return table_data, cols


@app.callback(
    Output('biplot-centroid-dist-table', 'data'), Output('biplot-centroid-dist-table', 'columns'),
    Input('pca-results-store', 'data'), Input('year-checklist-final', 'value')
)
def cb_biplot_centroid_dist(pca_data, years_filter):
    if not pca_data or not years_filter: return [], []
    df_pc = pd.read_json(io.StringIO(pca_data['pc_scores']), orient='split')
    df_pc = df_pc[df_pc['Tahun'].isin(years_filter)]
    years_sorted = sorted(df_pc['Tahun'].unique())
    centroids = {y: (df_pc[df_pc['Tahun'] == y]['PC1'].mean(), df_pc[df_pc['Tahun'] == y]['PC2'].mean()) for y in years_sorted}
    rows = []
    for i, y in enumerate(years_sorted):
        c1, c2 = centroids[y]
        if i < len(years_sorted) - 1:
            ny = years_sorted[i + 1]
            nc1, nc2 = centroids[ny]
            dist = round(np.sqrt((c1 - nc1)**2 + (c2 - nc2)**2), 4)
        else:
            dist = '-'
        rows.append({'Tahun': y, 'Centroid PC1': round(c1, 4), 'Centroid PC2': round(c2, 4), 'D(cₜ, cₜ₊₁)': dist})
    cols = [{"name": k, "id": k} for k in rows[0].keys()] if rows else []
    return rows, cols


@app.callback(
    Output('statis-centroid-dist-table', 'data'), Output('statis-centroid-dist-table', 'columns'),
    Input('statis-core-store', 'data'), Input('year-checklist-final', 'value')
)
def cb_statis_centroid_dist(statis_data, years_filter):
    if not statis_data or not years_filter: return [], []
    obs_labels = statis_data['obs_labels']
    years_sorted = sorted([int(y) for y in statis_data['sheet_names'] if int(y) in [int(yf) for yf in years_filter]])
    centroids = {}
    for y in years_sorted:
        coords = np.array(statis_data['per_year_coords'][str(y)])
        centroids[y] = (coords[:, 0].mean(), coords[:, 1].mean())
    rows = []
    for i, y in enumerate(years_sorted):
        c1, c2 = centroids[y]
        if i < len(years_sorted) - 1:
            ny = years_sorted[i + 1]
            nc1, nc2 = centroids[ny]
            dist = round(np.sqrt((c1 - nc1)**2 + (c2 - nc2)**2), 4)
        else:
            dist = '-'
        rows.append({'Tahun': y, 'Centroid PC1': round(c1, 4), 'Centroid PC2': round(c2, 4), 'D(cₜ, cₜ₊₁)': dist})
    cols = [{"name": k, "id": k} for k in rows[0].keys()] if rows else []
    return rows, cols


@app.callback(
    Output('biplot-entity-name', 'options'), Output('biplot-entity-name', 'value'),
    Input('biplot-entity-type', 'value'), Input('pca-results-store', 'data')
)
def cb_biplot_entity_opts(entity_type, pca_data):
    if not pca_data: return [], None
    if entity_type == 'skor':
        df = pd.read_json(io.StringIO(pca_data['pc_scores']), orient='split')
        names = sorted(df['Kabupaten/Kota'].unique())
    else:
        df = pd.read_json(io.StringIO(pca_data['loadings']), orient='split')
        names = sorted(df['features'].unique())
    return [{'label': n, 'value': n} for n in names], None


@app.callback(
    Output('biplot-entity-dist-table', 'data'), Output('biplot-entity-dist-table', 'columns'),
    Input('biplot-entity-name', 'value'), Input('biplot-entity-type', 'value'),
    Input('pca-results-store', 'data'), Input('year-checklist-final', 'value')
)
def cb_biplot_entity_dist(name, entity_type, pca_data, years_filter):
    if not name or not pca_data or not years_filter: return [], []
    if entity_type == 'skor':
        df = pd.read_json(io.StringIO(pca_data['pc_scores']), orient='split')
        df = df[df['Tahun'].isin(years_filter) & (df['Kabupaten/Kota'] == name)].sort_values('Tahun')
    else:
        df = pd.read_json(io.StringIO(pca_data['loadings']), orient='split')
        df = df[df['Tahun'].isin(years_filter) & (df['features'] == name)].sort_values('Tahun')
    years = df['Tahun'].tolist()
    pc1s = df['PC1'].tolist(); pc2s = df['PC2'].tolist()
    rows = []
    for i, y in enumerate(years):
        if i < len(years) - 1:
            dist = round(np.sqrt((pc1s[i] - pc1s[i+1])**2 + (pc2s[i] - pc2s[i+1])**2), 4)
        else:
            dist = '-'
        rows.append({'Tahun': y, 'PC1': round(pc1s[i], 4), 'PC2': round(pc2s[i], 4), 'D(posₜ, posₜ₊₁)': dist})
    cols = [{"name": k, "id": k} for k in rows[0].keys()] if rows else []
    return rows, cols


@app.callback(
    Output('statis-entity-name', 'options'), Output('statis-entity-name', 'value'),
    Input('statis-entity-type', 'value'), Input('statis-core-store', 'data')
)
def cb_statis_entity_opts(entity_type, statis_data):
    if not statis_data: return [], None
    if entity_type == 'skor':
        names = sorted(statis_data['obs_labels'])
    else:
        yr0 = str(statis_data['sheet_names'][0])
        G_key = fr"Loading Intra \mathbf{{G}}_{{{yr0}}}"
        if G_key in statis_data:
            df = pd.DataFrame(statis_data[G_key])
            names = sorted(df['Variabel'].unique())
        else:
            names = []
    return [{'label': n, 'value': n} for n in names], None


@app.callback(
    Output('statis-entity-dist-table', 'data'), Output('statis-entity-dist-table', 'columns'),
    Input('statis-entity-name', 'value'), Input('statis-entity-type', 'value'),
    Input('statis-core-store', 'data'), Input('year-checklist-final', 'value')
)
def cb_statis_entity_dist(name, entity_type, statis_data, years_filter):
    if not name or not statis_data or not years_filter: return [], []
    years_sorted = sorted([int(y) for y in statis_data['sheet_names'] if int(y) in [int(yf) for yf in years_filter]])
    rows = []
    positions = []
    if entity_type == 'skor':
        obs_labels = statis_data['obs_labels']
        if name not in obs_labels: return [], []
        idx = obs_labels.index(name)
        for y in years_sorted:
            coords = np.array(statis_data['per_year_coords'][str(y)])
            positions.append((y, coords[idx, 0], coords[idx, 1]))
    else:
        for y in years_sorted:
            G_key = fr"Loading Intra \mathbf{{G}}_{{{y}}}"
            if G_key not in statis_data: continue
            df = pd.DataFrame(statis_data[G_key])
            row = df[df['Variabel'] == name]
            if row.empty: continue
            positions.append((y, row.iloc[0]['PC1'], row.iloc[0]['PC2']))
    for i, (y, p1, p2) in enumerate(positions):
        if i < len(positions) - 1:
            np1, np2 = positions[i+1][1], positions[i+1][2]
            dist = round(np.sqrt((p1 - np1)**2 + (p2 - np2)**2), 4)
        else:
            dist = '-'
        rows.append({'Tahun': y, 'PC1': round(p1, 4), 'PC2': round(p2, 4), 'D(posₜ, posₜ₊₁)': dist})
    cols = [{"name": k, "id": k} for k in rows[0].keys()] if rows else []
    return rows, cols


# 6. STATIS PLOTS & TABLES
@app.callback(
    Output('statis-scree', 'figure'), Output('statis-interstructure', 'figure'),
    Output('statis-biplot', 'figure'), Output('statis-structure-vector', 'figure'),
    Output('statis-contribution', 'figure'), Output('statis-cos2', 'figure'),
    Output('statis-trajectory', 'figure'), Output('statis-trajectory-loading', 'figure'),
    Output('statis-table-selector', 'options'), Output('statis-detail-table', 'data'),
    Output('statis-detail-table', 'columns'), Output('table-info-display', 'children'),
    Output('formula-statis-output', 'children'),
    Input('statis-core-store', 'data'), Input('statis-table-selector', 'value'),
    Input('visual-scaling-opts', 'value'), Input('table-page-size', 'value'),
    State('mirror-year-checklist-final', 'value'),
    State('baseline-type-final', 'value'),
    State('baseline-name-final', 'value')
)
def cb_statis_viz(res, table_key, vis_opts, page_size, mirror_years, base_type, base_name):
    # --- 1. SAFE EXIT: Jika data utama (res) belum ada ---
    if not res or not isinstance(res, dict):
        return EMPTY_FIG, EMPTY_FIG, EMPTY_FIG, EMPTY_FIG, EMPTY_FIG, EMPTY_FIG, EMPTY_FIG, EMPTY_FIG, [], [], [], "Silakan RUN ANALISIS dahulu.", html.Div()
    
    # --- 2. SAFE PREPARATION: Pastikan opsi dan data dasar tersedia ---
    norm_score = vis_opts == 'norm_score'
    scale_load = vis_opts == 'scale_load'
    
    # Ambil data esensial dengan try-except agar tidak crash
    try:
        scores = np.array(res.get('scores', []))
        loadings = np.array(res.get('loadings', []))
        eig_vals = np.array(res.get('eig_vals_c', [1, 0])) # Default agar tidak div by zero
        selected_vars = res.get('selected_vars', [])
        obs_labels = res.get('obs_labels', [])
        sheet_names = res.get('sheet_names', [])
        
        if scores.size == 0 or loadings.size == 0:
            raise ValueError("Data skor atau loading kosong.")
    except Exception as e:
        import traceback
        err_msg = f"Gagal memproses visualisasi: {str(e)} \n {traceback.format_exc()}"
        print(err_msg)
        return EMPTY_FIG, EMPTY_FIG, EMPTY_FIG, EMPTY_FIG, EMPTY_FIG, EMPTY_FIG, EMPTY_FIG, EMPTY_FIG, [], [], [], f"❌ Error Visualisasi: {str(e)}", html.Div()
    
    # Use compromise singular values (sqrt of eigenvalues) per Abdi et al. (2012)
    try:
        sv_comp = np.sqrt(np.array(eig_vals)[:2])
    except Exception:
        sv_comp = None
    plot_scores, plot_loadings = apply_visual_adjustments(scores, loadings, norm_score, scale_load, singular_values=sv_comp)
    
    # Label Sumbu (Persentase Variansi)
    eig_vals = np.array(res.get('eig_vals_c', [1, 0]))
    var_pct = (eig_vals / eig_vals.sum() * 100) if eig_vals.sum() > 0 else [0, 0]
    ax_x = f"Compromise 1 ({var_pct[0]:.2f}%)"
    ax_y = f"Compromise 2 ({var_pct[1]:.2f}%)"
    
    # Hitung Faktor Normalisasi Global (Penting untuk Trajektori)
    # Agar Trajektori punya skala yang sama dengan Peta Kompromi
    global_max_val = 1.0
    if norm_score:
        global_max_val = np.max(np.abs(scores))
        if global_max_val == 0: global_max_val = 1.0

    # PLOT 1: Interstructure Heatmap
    fig_inter = px.imshow(res['R'], text_auto=True, x=res['sheet_names'], y=res['sheet_names'], 
                       color_continuous_scale='Blues', title="RV Coefficient Matrix (Heatmap)")
    
    # PLOT 2: Scree Plot — cap at 10 meaningful dims, dual-axis bar+cumulative
    _n_scree = min(10, len(eig_vals))
    _ev = eig_vals[:_n_scree]
    _ev_pos = np.clip(_ev, 0, None)
    _cum_pct = np.cumsum(_ev_pos) / _ev_pos.sum() * 100 if _ev_pos.sum() > 0 else np.zeros(_n_scree)
    _dims = [f"Dim {i+1}" for i in range(_n_scree)]

    fig_scree = go.Figure()
    fig_scree.add_trace(go.Bar(
        x=_dims, y=_ev_pos,
        name="Eigenvalue",
        marker_color='#1565C0',
        text=[f"{v:.4f}".replace('.', ',') for v in _ev_pos],
        textposition="outside",
        yaxis='y1'
    ))
    fig_scree.add_trace(go.Scatter(
        x=_dims, y=_cum_pct,
        name="Kumulatif (%)",
        mode="lines+markers+text",
        marker=dict(color='#E91E63', size=8),
        line=dict(color='#E91E63', width=2),
        text=[f"{v:.2f}%".replace('.', ',') for v in _cum_pct],
        textposition="top center",
        yaxis='y2'
    ))
    fig_scree.update_layout(
        title="Scree Plot — Eigenvalue Matriks Kompromi",
        xaxis_title="Dimensi",
        yaxis=dict(title="Eigenvalue", side='left'),
        yaxis2=dict(title="Kumulatif (%)", overlaying='y', side='right', range=[0, 110], showgrid=False),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        template="plotly_white",
        bargap=0.3
    )
    
    # PLOT 3: Contribution
    contrib = (loadings**2) / np.sum(loadings**2, axis=0) # Normalization
    fig_contrib = px.bar(x=res['selected_vars'], y=contrib[:, 0], labels={'x': 'Variable', 'y': 'Contribution to PC1'}, title="Variable Contribution (PC1)")
    fig_contrib.update_layout(template="plotly_white")

    # PLOT 4: Cos2
    cos2 = loadings**2
    fig_cos2 = px.bar(x=res['selected_vars'], y=cos2[:, 0], labels={'x': 'Variable', 'y': 'Cos² (PC1)'}, title="Cos² Variable Representation (PC1)")
    fig_cos2.update_layout(template="plotly_white")

    # PLOT 5: Biplot (Compromise Biplot)
    fig_bi = create_biplot(plot_scores, plot_loadings, res['obs_labels'], res['selected_vars'], 
                           "Compromise Biplot", show_loadings=True, show_arrows=False)
    fig_bi.update_layout(xaxis_title=ax_x, yaxis_title=ax_y)
    
    # NEW: PLOT 5B: Structure Vector Calculation for Plot
    try:
        sv_res = res.get('structure_vector_res')
        if sv_res:
            beta_tilde = sv_res['beta_tilde']
            beta_provinsi = sv_res.get('beta_provinsi', {})
            x_vals_sv = res['sheet_names']
            
            fig_sv = go.Figure()
            fig_sv.add_trace(go.Scatter(
                x=x_vals_sv, y=beta_tilde, mode='lines+markers',
                name='β̃ₖ (Gabungan)', line=dict(color='#1976D2', width=3),
                marker=dict(size=10, symbol='circle')
            ))
            
            colors_prov_list = ['#D81B60', '#43A047', '#FB8C00', '#7B1FA2', '#0097A7', '#F44336', '#9C27B0', '#3F51B5']
            for i, (prov, betas) in enumerate(beta_provinsi.items()):
                color = colors_prov_list[i % len(colors_prov_list)]
                fig_sv.add_trace(go.Scatter(
                    x=x_vals_sv, y=betas, mode='lines+markers',
                    name=f'β̃_gk {prov}', line=dict(dash='dash', color=color),
                    marker=dict(size=8, symbol='square'),
                    opacity=0.8
                ))
                
            fig_sv.update_layout(
                title="Temporal Trajectory of Structure Vector (β̃)",
                xaxis_title="Year (k)",
                yaxis_title="β̃ₖ = λ₁ u₁ₖ",
                template="plotly_white",
                legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5)
            )
        else:
            fig_sv = go.Figure().add_annotation(text="Data Vektor Struktur tidak ditemukan.", showarrow=False)
    except Exception as e_sv:
        print(f"Error rendering structure vector plot: {e_sv}")
        fig_sv = go.Figure().add_annotation(text=f"Error Structure Vector: {e_sv}", showarrow=False)
    
    # PLOT 6: Object Trajectory
    # Build per-year DataFrames (raw) for scores and loadings, then compute visual versions
    coords_dict = res.get('per_year_coords', {})
    df_pc_list_all = []
    df_load_list_all = []
    for yr in res.get('sheet_names', []):
        coords = np.array(coords_dict.get(str(yr), []))
        if coords.size == 0:
            continue
        df_t = pd.DataFrame(coords[:, :2], columns=['PC1', 'PC2'])
        df_t['Kabupaten/Kota'] = res['obs_labels']
        df_t['Tahun'] = int(yr)
        df_pc_list_all.append(df_t)

        # loadings per-year (if present)
        G_key = fr"Loading Intra \mathbf{{G}}_{{{yr}}}"
        g_recs = res.get(G_key, [])
        if g_recs:
            df_g = pd.DataFrame(g_recs)
            df_g = df_g.rename(columns={'Variabel': 'features'}) if 'Variabel' in df_g.columns else df_g
            df_g['Tahun'] = int(yr)
            df_load_list_all.append(df_g)

    if df_pc_list_all:
        df_pc_all = pd.concat(df_pc_list_all, ignore_index=True)
    else:
        df_pc_all = pd.DataFrame(columns=['PC1','PC2','Kabupaten/Kota','Tahun'])

    if df_load_list_all:
        df_load_all = pd.concat(df_load_list_all, ignore_index=True)
    else:
        df_load_all = pd.DataFrame(columns=['Variabel','PC1','PC2','Tahun'])

    # Compute visual-adjusted coordinates for all per-year entries using compromise singular values
    try:
        sv_comp = np.sqrt(np.array(res.get('eig_vals_c', [1,0]))[:2])
    except Exception:
        sv_comp = None

    # --- B: Apply same rotation + mirror as Dynamic Biplot page (cb_update_statis_plots) ---
    try:
        df_pc_fin = df_pc_all.copy()
        df_load_fin = df_load_all.copy()
        if not df_pc_fin.empty:
            for _yr in sorted(df_pc_fin['Tahun'].unique()):
                _mask_p = df_pc_fin['Tahun'] == _yr
                _mask_l = df_load_fin['Tahun'] == _yr if not df_load_fin.empty else pd.Series(dtype=bool)
                # Rotation (needs 'features' col in df_load; rename from 'Variabel' if needed)
                _df_load_for_rot = df_load_fin.copy()
                if 'Variabel' in _df_load_for_rot.columns and 'features' not in _df_load_for_rot.columns:
                    _df_load_for_rot = _df_load_for_rot.rename(columns={'Variabel': 'features'})
                _angle = get_rotation_angle(df_pc_fin, _df_load_for_rot, base_type, base_name, _yr) if base_name else 0.0
                if _angle != 0:
                    df_pc_fin.loc[_mask_p, ['PC1','PC2']] = rotate_dataframe(df_pc_fin.loc[_mask_p], _angle)[['PC1','PC2']].values
                    if not df_load_fin.empty and _mask_l.any():
                        df_load_fin.loc[_mask_l, ['PC1','PC2']] = rotate_dataframe(df_load_fin.loc[_mask_l], _angle)[['PC1','PC2']].values
                # Mirror PC2
                _mirror_list = [str(m) for m in mirror_years] if mirror_years else []
                if str(_yr) in _mirror_list:
                    df_pc_fin.loc[_mask_p, 'PC2'] *= -1
                    if not df_load_fin.empty and _mask_l.any():
                        df_load_fin.loc[_mask_l, 'PC2'] *= -1
    except Exception as _e_rot:
        print(f"[WARN cb_statis_viz] rotation/mirror failed: {_e_rot}")
        df_pc_fin = df_pc_all.copy()
        df_load_fin = df_load_all.copy()

    try:
        if not df_pc_fin.empty:
            pc_vals = df_pc_fin[['PC1','PC2']].values
            load_vals = df_load_fin[['PC1','PC2']].values if not df_load_fin.empty else np.zeros((pc_vals.shape[0],2))
            pc_plot_all, load_plot_all = apply_visual_adjustments(pc_vals, load_vals, norm_score, scale_load, singular_values=sv_comp)
            df_pc_all_vis = df_pc_fin.copy()
            df_pc_all_vis[['PC1','PC2']] = pc_plot_all
        else:
            df_pc_all_vis = df_pc_fin.copy()

        if not df_load_fin.empty:
            df_load_all_vis = df_load_fin.copy()
            df_load_all_vis[['PC1','PC2']] = load_plot_all[:len(df_load_fin)]
        else:
            df_load_all_vis = df_load_fin.copy()
    except Exception:
        df_pc_all_vis = df_pc_fin.copy()
        df_load_all_vis = df_load_fin.copy()

    # Plot Trajectory Scores (per-year visual coordinates)
    fig_traj = go.Figure()
    prov_map = res.get('prov_map', {})
    kab_idx_map = res.get('kab_index_map', {})
    PROV_COLORS = {'DKI JAKARTA': '#1E88E5', 'JAWA BARAT': '#43A047', 'BANTEN': '#FB8C00'}

    for kab in res['obs_labels']:
        d_kab = df_pc_all_vis[df_pc_all_vis['Kabupaten/Kota'] == kab].sort_values('Tahun')
        if d_kab.empty: continue
        prov = prov_map.get(kab, 'N/A').upper()
        color = PROV_COLORS.get(prov, None)
        num = kab_idx_map.get(kab, '?')
        display_label = f"{num} : {kab}"
        symbols = ['circle'] * (len(d_kab) - 1) + ['square']
        fig_traj.add_trace(go.Scatter(
            x=d_kab['PC1'], y=d_kab['PC2'],
            mode='lines+markers',
            name=display_label,
            legendgroup=prov,
            legendgrouptitle_text=prov,
            line=dict(width=1.5, color=color),
            marker=dict(symbol=symbols, size=7, color=color),
            hoverinfo='text',
            text=[f"{kab} ({y})<br>PC1: {pc1:.3f}<br>PC2: {pc2:.3f}" for y, pc1, pc2 in zip(d_kab['Tahun'], d_kab['PC1'], d_kab['PC2'])]
        ))

    fig_traj.update_layout(
        title='Trajectory Scores (Warna per Provinsi, Akhir=Kotak)',
        template='plotly_white', 
        xaxis=dict(scaleanchor='y', scaleratio=1), 
        xaxis_title=ax_x, yaxis_title=ax_y,
        legend=dict(groupclick="toggleitem")
    )

    # PLOT 7: Trajectory Loading (Variable Trajectories over years)
    fig_traj_load = go.Figure()
    import plotly.colors as pcolors
    var_colors = pcolors.qualitative.Alphabet[:len(res['selected_vars'])]
    
    for vi, var in enumerate(res['selected_vars']):
        x_pts, y_pts, text_pts = [], [], []
        for yr in res['sheet_names']:
            # Prefer visual-adjusted loadings if available
            if not df_load_all_vis.empty:
                feat_col = 'features' if 'features' in df_load_all_vis.columns else ('Variabel' if 'Variabel' in df_load_all_vis.columns else None)
                if feat_col is not None:
                    mask = (df_load_all_vis[feat_col] == var) & (df_load_all_vis['Tahun'] == int(yr))
                    if mask.any():
                        rvis = df_load_all_vis[mask].iloc[0]
                        px_v, py_v = rvis['PC1'], rvis['PC2']
                        x_pts.append(px_v); y_pts.append(py_v); text_pts.append(yr)
                        continue
            # Fallback to raw records in res
            gk_recs = res.get(fr"Loading Intra \mathbf{{G}}_{{{yr}}}", [])
            for rec in gk_recs:
                if rec.get('Variabel') == var or rec.get('features') == var:
                    px_v = rec.get('PC1', 0)
                    py_v = rec.get('PC2', 0)
                    x_pts.append(px_v)
                    y_pts.append(py_v)
                    text_pts.append(yr)
                    break
        
        if x_pts:
            symbols = ['circle'] * (len(x_pts) - 1) + ['square']
            fig_traj_load.add_trace(go.Scatter(
                x=x_pts, y=y_pts,
                mode='lines+markers',
                name=f"{var}",
                line=dict(width=2, color=var_colors[vi % len(var_colors)]),
                marker=dict(symbol=symbols, size=8, color=var_colors[vi % len(var_colors)]),
                hoverinfo='text',
                text=[f"Var: {var} ({y})<br>PC1: {px_v:.3f}<br>PC2: {py_v:.3f}" for y, px_v, py_v in zip(text_pts, x_pts, y_pts)]
            ))
            
    fig_traj_load.update_layout(
        title='Trajectory Loadings (Warna per Variabel, Akhir=Kotak)',
        template='plotly_white',
        xaxis=dict(scaleanchor='y', scaleratio=1),
        xaxis_title=ax_x, yaxis_title=ax_y
    )
    
    # 5. Tables Logic
    exclude_keys = ['R', 'H', 'R_S', 'alphas', 'eig_vals_c', 'scores', 'loadings', 'per_year_coords', 
                    'sheet_names', 'X_matrices', 'vals_R_sorted', 'vals_H_sorted', 'k', 'obs_labels', 
                    'selected_vars', 'perm_lambda_obs', 'perm_distribution', 'perm_p_value',
                    'scenario', 'prov_map', 'kab_index_map', 'm_weights', r'Bobot (\alpha)',
                    'scores_svd', 'loadings_svd', 'intra_score_svd', 'intra_load_svd', 'structure_vector_res']
    
    def polish_statis_label(text):
        LABEL_MAP = {
            'R': "𝐌𝐚𝐭𝐫𝐢𝐤𝐬 𝐊𝐨𝐞𝐟𝐢𝐬𝐢𝐞𝐧 𝐑𝐕 (𝐑)",
            'H': "𝐌𝐚𝐭𝐫𝐢𝐤𝐬 𝐈𝐧𝐭𝐞𝐫𝐬𝐭𝐫𝐮𝐤𝐭𝐮𝐫 (𝐇)",
            'alphas': "𝐁𝐨𝐛𝐨𝐭 𝐓𝐚𝐡𝐮𝐧 (𝛂ₖ)",
            'eig_vals_c': "𝐍𝐢𝐥𝐚𝐢 𝐄𝐢𝐠𝐞𝐧 𝐊𝐨𝐦𝐩𝐫𝐨𝐦𝐢 (𝚲꜀)",
            'lambdac': "𝐍𝐢𝐥𝐚𝐢 𝐄𝐢𝐠𝐞𝐧 𝐊𝐨𝐦𝐩𝐫𝐨𝐦𝐢 (𝚲꜀)",
            'm_weights': "𝐁𝐨𝐛𝐨𝐭 𝐖𝐢𝐥𝐚𝐲𝐚𝐡 (𝐦ᵢ)",
            'mweight': "𝐁𝐨𝐛𝐨𝐭 𝐖𝐢𝐥𝐚𝐲𝐚𝐡 (𝐦ᵢ)",
            'prov_map': "𝐏𝐞𝐦𝐞𝐭𝐚𝐚𝐧 𝐏𝐫𝐨𝐯𝐢𝐧𝐬𝐢",
            'kab_index_map': "𝐈𝐧𝐝𝐞𝐤𝐬 𝐖𝐢𝐥𝐚𝐲𝐚𝐡",
            r'Dataset Asli (\mathbf{X})': "𝐃𝐚𝐭𝐚𝐬𝐞𝐭 𝐀𝐬𝐥𝐢 (𝐗)",
            r'Bobot (\alpha)': "𝐁𝐨𝐛𝐨𝐭 𝐓𝐚𝐡𝐮𝐧 (𝛂)",
            r'Nilai Eigen (\Lambda_c)': "𝐍𝐢𝐥𝐚𝐢 𝐄𝐢𝐠𝐞𝐧 𝐊𝐨𝐦𝐩𝐫𝐨𝐦𝐢 (𝚲꜀)",
            r'Skor Kompromi (F_c)': "𝐒𝐤𝐨𝐫 𝐊𝐨𝐦𝐩𝐫𝐨𝐦𝐢 (𝐅꜀)",
            r'Loadings Kompromi (G_c)': "𝐋𝐨𝐚𝐝𝐢𝐧𝐠𝐬 𝐊𝐨𝐦𝐩𝐫𝐨𝐦𝐢 (𝐆꜀)",
            r'Matriks Koefisien RV (Wilayah) (\mathbf{R}_W)': "𝐌𝐚𝐭𝐫𝐢𝐤𝐬 𝐊𝐨𝐞𝐟𝐢𝐬𝐢𝐞𝐧 𝐑𝐕 (𝐖𝐢𝐥𝐚𝐲𝐚𝐡 - 𝐖)",
            r'Matriks Koefisien RV (Indikator) (\mathbf{R}_S)': "𝐌𝐚𝐭𝐫𝐢𝐤𝐬 𝐊𝐨𝐞𝐟𝐢𝐬𝐢𝐞𝐧 𝐑𝐕 (𝐈𝐧𝐝𝐢𝐤𝐚𝐭𝐨𝐫 - 𝐒)",
            r'Matriks Interstruktur (Wilayah) (\mathbf{H}_W)': "𝐌𝐚𝐭𝐫𝐢𝐤𝐬 𝐈𝐧𝐭𝐞𝐫𝐬𝐭𝐫𝐮𝐤𝐭𝐮𝐫 (𝐖𝐢𝐥𝐚𝐲𝐚𝐡 - 𝐇)",
            r'Matriks Interstruktur (Indikator) (\mathbf{H}_S)': "𝐌𝐚𝐭𝐫𝐢𝐤𝐬 𝐈𝐧𝐭𝐞𝐫𝐬𝐭𝐫𝐮𝐤𝐭𝐮𝐫 (𝐈𝐧𝐝𝐢𝐤𝐚𝐭𝐨𝐫 - 𝐇)",
            r'Vektor Eigen (Kompas Wilayah) (\mathbf{P}_W)': "𝐕𝐞𝐤𝐭𝐨𝐫 𝐄𝐢𝐠𝐞𝐧 / 𝐊𝐨𝐦𝐩𝐚𝐬 (𝐖𝐢𝐥𝐚𝐲𝐚𝐡)",
            r'Vektor Eigen (Kompas Indikator) (\mathbf{P}_S)': "𝐕𝐞𝐤𝐭𝐨𝐫 𝐄𝐢𝐠𝐞𝐧 / 𝐊𝐨𝐦𝐩𝐚𝐬 (𝐈𝐧𝐝𝐢𝐤𝐚𝐭𝐨𝐫)",
            r'Bobot Alpha (Wilayah) (\alpha_W)': "𝐁𝐨𝐛𝐨𝐭 𝐓𝐚𝐡𝐮𝐧 (𝛂 - 𝐖𝐢𝐥𝐚𝐲𝐚𝐡)",
            r'Bobot Alpha (Indikator) (\alpha_S)': "𝐁𝐨𝐛𝐨𝐭 𝐓𝐚𝐡𝐮𝐧 (𝛂 - 𝐈𝐧𝐝𝐢𝐤𝐚𝐭𝐨𝐫)",
            r'Matriks Kompromi (\mathbf{W}_c)': "𝐌𝐚𝐭𝐫𝐢𝐤𝐬 𝐊𝐨𝐦𝐩𝐫𝐨𝐦𝐢 (𝐖꜀)",
            r'Matriks Kompromi Variabel (\mathbf{S}_c)': "𝐌𝐚𝐭𝐫𝐢𝐤𝐬 𝐊𝐨𝐦𝐩𝐫𝐨𝐦𝐢 𝐕𝐚𝐫𝐢𝐚𝐛𝐞𝐥 (𝐒꜀)",
            r'Vektor Struktur (β) - Gabungan': "𝐕𝐞𝐤𝐭𝐨𝐫 𝐒𝐭𝐫𝐮𝐤𝐭𝐮𝐫 (β) - 𝐆𝐚𝐛𝐮𝐧𝐠𝐚𝐧",
            r'Vektor Eigen Struktur (u₁)': "𝐕𝐞𝐤𝐭𝐨𝐫 𝐄𝐢𝐠𝐞𝐧 𝐒𝐭𝐫𝐮𝐤𝐭𝐮𝐫 (𝐮₁)",
            r'Nilai Eigen Struktur (λ₁)': "𝐍𝐢𝐥𝐚𝐢 𝐄𝐢𝐠𝐞𝐧 𝐒𝐭𝐫𝐮𝐤𝐭𝐮𝐫 (λ₁)",
            r'Diagnostik Vektor Struktur': "𝐃𝐢𝐚𝐠𝐧𝐨𝐬𝐭𝐢𝐤 𝐕𝐞𝐤𝐭𝐨𝐫 𝐒𝐭𝐫𝐮𝐤𝐭𝐮𝐫",
            r'Vektor Struktur (β) - Per Provinsi': "𝐕𝐞𝐤𝐭𝐨𝐫 𝐒𝐭𝐫𝐮𝐤𝐭𝐮𝐫 (β) - 𝐏𝐞𝐫 𝐏𝐫𝐨𝐯𝐢𝐧𝐬𝐢"
        }
        
        if text in LABEL_MAP:
            return LABEL_MAP[text]
            
        import re
        sub = {'0':'₀','1':'₁','2':'₂','3':'₃','4':'₄','5':'₅','6':'₆','7':'₇','8':'₈','9':'₉','c':'꜀'}
        t = text.replace(r'\mathbf', '').replace('\\', '').replace('{', '').replace('}', '').replace('_', '')
        
        m = re.search(r'(\d{4})', t)
        if m:
            yr_sub = "".join([sub.get(c, c) for c in m.group(1)])
            if "Matriks" in t and "W" in t: return f"𝐌𝐚𝐭𝐫𝐢𝐤𝐬 𝐈𝐧𝐭𝐫𝐚-𝐒𝐤𝐨𝐫 (𝐖{yr_sub})"
            if "Matriks" in t and "S" in t: return f"𝐌𝐚𝐭𝐫𝐢𝐤𝐬 𝐈𝐧𝐭𝐫𝐚-𝐋𝐨𝐚𝐝𝐢𝐧𝐠 (𝐒{yr_sub})"
            if "Skor" in t and "Intra" in t: return f"𝐒𝐤𝐨𝐫 𝐈𝐧𝐭𝐫𝐚 (𝐅{yr_sub})"
            if "Loading" in t and "Matriks" not in t: return f"𝐋𝐨𝐚𝐝𝐢𝐧𝐠 𝐈𝐧𝐭𝐫𝐚 (𝐆{yr_sub})"
        
        t = t.replace('(', '').replace(')', '')
        return t

    # Bobot wilayah m_i selalu di posisi paling atas
    table_opts = []
    if 'm_weights' in res:
        table_opts.append({'label': polish_statis_label('m_weights'), 'value': 'm_weights'})
    for k in res.keys():
        if k not in exclude_keys:
            table_opts.append({'label': polish_statis_label(k), 'value': k})
            
    def sort_table_opts(item):
        import re
        val = item['value']
        m = re.search(r'(\d{4})', val)
        if m:
            yr = int(m.group(1))
            if 'W_' in val or '\\mathbf{W}' in val:
                rank = 1
            elif 'F_' in val or '\\mathbf{F}' in val:
                rank = 2
            elif 'S_' in val or '\\mathbf{S}' in val:
                rank = 3
            elif 'G_' in val or '\\mathbf{G}' in val:
                rank = 4
            else:
                rank = 5
            return (1, yr, rank, val)
        else:
            return (0, 0, 0, val)

    table_opts.sort(key=sort_table_opts)
    
    tbl_data, tbl_cols, info_text = [], [], "Silakan pilih tabel hasil di atas."
    
    if table_key and table_key in res:
        tbl_data = res.get(table_key, [])
        
        if table_key == 'prov_map' and isinstance(tbl_data, dict):
            tbl_data = [{"Kabupaten/Kota": k, "Provinsi": v} for k, v in tbl_data.items()]
        elif table_key == 'kab_index_map' and isinstance(tbl_data, dict):
            tbl_data = [{"Kabupaten/Kota": k, "Indeks": v} for k, v in tbl_data.items()]
        elif table_key in ['m_weights', 'mweight'] and isinstance(tbl_data, list):
            labels = res.get('obs_labels', [f"Wilayah {i+1}" for i in range(len(tbl_data))])
            tbl_data = [{"Kabupaten/Kota": kab, "Bobot (m_i)": v} for kab, v in zip(labels, tbl_data)]
        elif isinstance(tbl_data, list) and len(tbl_data) > 0 and not isinstance(tbl_data[0], dict):
            tbl_data = [{"Index": i+1, "Value": v} for i, v in enumerate(tbl_data)]

        # --- LOGIKA PERBANDINGAN KOORDINAT (ASLI VS VISUAL) ---
        if table_key and any(x in table_key for x in ["Skor", "Loading"]):
            new_tbl_data = []
            
            # Cari data ASLI (SVD Murni) dari res
            raw_data_svd = None
            if "Kompromi" in table_key:
                if "Skor" in table_key: raw_data_svd = np.array(res.get('scores_svd', []))
                else: raw_data_svd = np.array(res.get('loadings_svd', []))
            else:
                # Cari tahun dari table_key (misal: F_{2020})
                import re
                m = re.search(r'(\d{4})', table_key)
                if m:
                    yr = m.group(1)
                    if "Skor" in table_key: raw_data_svd = np.array(res.get('intra_score_svd', {}).get(yr, []))
                    else: raw_data_svd = np.array(res.get('intra_load_svd', {}).get(yr, []))

            for idx, row in enumerate(tbl_data):
                new_row = row.copy()
                if 'PC1' in row and 'PC2' in row:
                    # 1. Nilai ASLI (SVD Murni sebelum flip)
                    if raw_data_svd is not None and idx < len(raw_data_svd):
                        pc1_asli, pc2_asli = raw_data_svd[idx, 0], raw_data_svd[idx, 1]
                    else:
                        pc1_asli, pc2_asli = row['PC1'], row['PC2'] # Fallback
                    
                    # 2. Nilai VISUAL (Hasil Akhir di Dash)
                    # Determine visual values using apply_visual_adjustments outputs
                    pc1_vis, pc2_vis = row['PC1'], row['PC2']
                    try:
                        if "Kompromi" in table_key:
                            # Use compromise visual arrays computed earlier (plot_scores / plot_loadings)
                            if "Skor" in table_key and plot_scores is not None and idx < len(plot_scores):
                                pc1_vis, pc2_vis = plot_scores[idx, 0], plot_scores[idx, 1]
                            elif "Loading" in table_key and plot_loadings is not None and idx < len(plot_loadings):
                                pc1_vis, pc2_vis = plot_loadings[idx, 0], plot_loadings[idx, 1]
                        else:
                            # Per-year table: find matching row in df_pc_all_vis / df_load_all_vis
                            import re as _re
                            m2 = _re.search(r'(\d{4})', table_key)
                            yr2 = int(m2.group(1)) if m2 else None
                            # label key (name column)
                            label_key = list(row.keys())[0]
                            if "Skor" in table_key and not df_pc_all_vis.empty and yr2 is not None:
                                mask = (df_pc_all_vis['Kabupaten/Kota'] == row[label_key]) & (df_pc_all_vis['Tahun'] == yr2)
                                if mask.any():
                                    rvis = df_pc_all_vis[mask].iloc[0]
                                    pc1_vis, pc2_vis = rvis['PC1'], rvis['PC2']
                            if "Loading" in table_key and not df_load_all_vis.empty and yr2 is not None:
                                # loadings may use 'features' or 'Variabel' as label
                                feat_col = 'features' if 'features' in df_load_all_vis.columns else ('Variabel' if 'Variabel' in df_load_all_vis.columns else None)
                                if feat_col is not None:
                                    mask = (df_load_all_vis[feat_col] == row[label_key]) & (df_load_all_vis['Tahun'] == yr2)
                                    if mask.any():
                                        rvis = df_load_all_vis[mask].iloc[0]
                                        pc1_vis, pc2_vis = rvis['PC1'], rvis['PC2']
                    except Exception:
                        pass
                    
                    label_key = list(row.keys())[0]
                    new_row = {
                        label_key: row[label_key],
                        "PC1 (Asli/SVD)": round(pc1_asli, 4),
                        "PC2 (Asli/SVD)": round(pc2_asli, 4),
                        "PC1 (Visual/Dash)": round(pc1_vis, 4),
                        "PC2 (Visual/Dash)": round(pc2_vis, 4)
                    }
                new_tbl_data.append(new_row)
            tbl_data = new_tbl_data

        if tbl_data and len(tbl_data) > 0: 
            try:
                tbl_cols = [{"name": i, "id": i} for i in tbl_data[0].keys()]
                info_text = f"✅ Menampilkan Tabel: {polish_statis_label(table_key)}"
            except Exception as e_tbl:
                tbl_cols = []
                info_text = f"❌ Error saat memproses kolom: {str(e_tbl)}"
        else:
            info_text = f"⚠️ Tabel '{polish_statis_label(table_key)}' tersedia tapi tidak berisi data."
    elif table_key:
        info_text = f"❌ Error: Tabel '{table_key}' tidak ditemukan dalam hasil analisis terbaru."

    # --- AUTO EXPORT LATEX ---
    export_core_latex(res)
    export_tables_latex(res)

    # Render Statis Formulas
    wc_data = res.get(r'Matriks Kompromi (\mathbf{W}_c)', [])
    w_slice = None
    if wc_data:
        w_slice = [[float(v) for v in list(r.values())[1:4]] for r in wc_data[:3]]
        
    r_matrix = np.array(res['R'])
    form_statis_ui = render_statis_formulas(res['alphas'], res['sheet_names'], w_slice, r_matrix)

    return fig_scree, fig_inter, fig_bi, fig_sv, fig_contrib, fig_cos2, fig_traj, fig_traj_load, table_opts, tbl_data, tbl_cols, info_text, form_statis_ui


# 7. Permutation Test
@app.callback(
    Output('perm-graph', 'figure'), Output('perm-result-text', 'children'),
    Output('formula-perm-output', 'children'),
    Output('spinner-run-perm', 'children'),
    Input('btn-run-perm', 'n_clicks'), State('perm-n-input', 'value'), State('statis-core-store', 'data')
)
def cb_run_perm(n_clicks, n_perm, res):
    if not n_clicks or not res or not isinstance(res, dict): return EMPTY_FIG, "Tunggu data STATIS...", "", ""
    if res.get("ERROR_STATUS"): return EMPTY_FIG, f"Gagal: {res.get('MESSAGE')}", "", ""

    try:
        X_matrices = [np.array(m) for m in res['X_matrices']]
        m_weights = np.array(res['m_weights']) if 'm_weights' in res else None
        lambda_obs = res['vals_H_sorted'][0]
        dist, p_val = run_permutation_test(X_matrices, res['k'], lambda_obs, n_perm, m_weights=m_weights)

        fig = px.histogram(x=dist, title=f"Distribusi Null (N={n_perm})", color_discrete_sequence=['#90A4AE'])
        fig.add_vline(x=lambda_obs, line_color="#D32F2F", line_dash="dash", annotation_text=f"Observed: {lambda_obs:.3f}")
        fig.update_layout(template='plotly_white')

        interp = "Signifikan (Struktur Stabil)" if p_val < 0.05 else "Tidak Signifikan (Acak)"

        # --- AUTO EXPORT LATEX ---
        export_perm_latex(p_val, interp)

        # Render Result Formulas
        form_ui = render_permutation_formulas(p_val, lambda_obs, n_perm, interp)

        return fig, f"P-value = {p_val}. Interpretasi: {interp}", form_ui, ""
    except Exception as e:
        return EMPTY_FIG, f"Error Permutasi: {str(e)}", "", ""

# --- FALLBACK RETURN UNTUK ERROR DI PERMUTASI ---
@app.callback(
    Output('perm-graph', 'figure', allow_duplicate=True), 
    Output('perm-result-text', 'children', allow_duplicate=True),
    Output('formula-perm-output', 'children', allow_duplicate=True),
    Input('statis-core-store', 'data'),
    prevent_initial_call=True
)
def cb_handle_perm_error(res):
    if res and isinstance(res, dict) and res.get("ERROR_STATUS"):
        return EMPTY_FIG, f"Gagal simulasi: {res.get('MESSAGE')}", ""
    raise exceptions.PreventUpdate


# 7b_2. Toggle Weight Var Selection
@app.callback(
    Output('desc-weight-var-container', 'style'),
    Input('desc-weight-mode', 'value')
)
def cb_toggle_weight_vars(mode):
    if mode == 'weighted':
        return {'display': 'flex', 'alignItems': 'center', 'marginLeft': '20px'}
    return {'display': 'none'}

# 10. Callback Section 10: Biplot vs Statis Yearly
@app.callback(
    Output('biplot-vs-statis-table', 'data'),
    Output('biplot-vs-statis-table', 'columns'),
    Output('title-biplot-vs-statis-map-biplot', 'children'),
    Output('biplot-vs-statis-map-biplot', 'figure'),
    Output('title-biplot-vs-statis-map-statis', 'children'),
    Output('biplot-vs-statis-map-statis', 'figure'),
    Output('title-biplot-vs-statis-scatter-biplot', 'children'),
    Output('biplot-vs-statis-scatter-biplot', 'figure'),
    Output('title-biplot-vs-statis-scatter-statis', 'children'),
    Output('biplot-vs-statis-scatter-statis', 'figure'),
    Output('title-biplot-vs-statis-pie-biplot', 'children'),
    Output('biplot-vs-statis-pie-biplot', 'figure'),
    Output('title-biplot-vs-statis-pie-statis', 'children'),
    Output('biplot-vs-statis-pie-statis', 'figure'),
    Output('biplot-vs-statis-results-container', 'style'),
    Output('spinner-run-biplot-statis', 'children'),
    Input('btn-run-biplot-statis', 'n_clicks'),
    State('biplot-vs-statis-year', 'value'),
    State('biplot-vs-statis-k', 'value'),
    State('biplot-vs-statis-view-mode', 'value'),
    State('statis-core-store', 'data'),
    State('global-data-store', 'data')
)
def cb_run_biplot_vs_statis(n, year, k, mode, statis_data, global_data):
    if not n or not statis_data or not global_data or not year:
        return [], [], "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, {'display': 'none'}, ""
    
    try:
        from sklearn.cluster import KMeans
        from sklearn.decomposition import PCA
        from sklearn.preprocessing import StandardScaler
        
        # A. Get STATIS Trajectory Klaster (Aligned with Section 7)
        obs_labels = statis_data['obs_labels']
        coords_dict = statis_data['per_year_coords']
        sheet_names = statis_data.get('sheet_names', sorted(list(coords_dict.keys())))
        alphas = statis_data.get('alphas', [1.0] * len(sheet_names))
        
        # Build weighted trajectory features (Lavit 1994 logic)
        features = []
        for i in range(len(obs_labels)):
            city_feats = []
            for j, yr in enumerate(sheet_names):
                w = np.sqrt(alphas[j])
                coords_yr = np.array(coords_dict[str(yr)])
                city_feats.extend(coords_yr[i, :] * w)
            features.append(city_feats)
        X_traj = np.array(features)
        
        km_biplot = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X_traj)
        
        # --- ALIGNED LABELING (Ref Section 7 ranking by Compromise PC1) ---
        scores_comp = np.array(statis_data['scores'])
        cl_means_b = [np.mean(scores_comp[km_biplot.labels_ == cl, 0]) for cl in range(k)]
        rnk_b = np.argsort(cl_means_b)
        mp_b = {old: new for new, old in enumerate(rnk_b)}
        name_map = {0: "Rendah", 1: "Sedang", 2: "Tinggi"}
        labels_biplot = [f"Klaster {mp_b[l]+1} ({name_map.get(mp_b[l], 'Level ' + str(mp_b[l]+1))})" for l in km_biplot.labels_]
        
        # B. Get Static Klaster (K-means on raw data of the selected year)
        df_all = pd.read_json(io.StringIO(global_data['df_json']), orient='split')
        mask = df_all['Tahun'].astype(str) == str(year)
        df_year = df_all[mask].copy()
        
        # Sesuai urutan obs_labels agar alignment benar
        df_year = df_year.set_index('Kabupaten/Kota').reindex(obs_labels).reset_index()
        numeric_cols = df_year.select_dtypes(include='number').drop(columns=['Tahun'], errors='ignore').columns
        X_year = df_year[numeric_cols].fillna(0).values
        
        # Standardize before K-means
        X_std = StandardScaler().fit_transform(X_year)
        km_static = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X_std)
        
        # --- ALIGNED LABELING (Using IPM of current year for ranking to ensure stable colors) ---
        ipm_col = None
        for c in df_all.columns:
            if 'ipm' in c.lower():
                ipm_col = c
                break
        if ipm_col:
            df_year_ipm = df_all[df_all['Tahun'].astype(str) == str(year)].set_index('Kabupaten/Kota').reindex(obs_labels)
            ipm_vals = df_year_ipm[ipm_col].fillna(df_year_ipm[ipm_col].mean()).values
            cl_means_s = [np.mean(ipm_vals[km_static.labels_ == cl]) for cl in range(k)]
        else:
            pc1_yearly = PCA(n_components=1).fit_transform(X_std).flatten()
            cl_means_s = [np.mean(pc1_yearly[km_static.labels_ == cl]) for cl in range(k)]
            
        rnk_s = np.argsort(cl_means_s)
        mp_s = {old: new for new, old in enumerate(rnk_s)}
        labels_static = [f"Statis {mp_s[l]+1} ({name_map.get(mp_s[l], 'Lvl ' + str(mp_s[l]+1))})" for l in km_static.labels_]
        
        # C. Cross-tab
        df_comp = pd.DataFrame({
            'Kabupaten/Kota': obs_labels,
            'Biplot (Kompromi)': labels_biplot,
            'Statis (Tahunan)': labels_static
        })
        
        ct = pd.crosstab(df_comp['Biplot (Kompromi)'], df_comp['Statis (Tahunan)'])

        # Sort CT to be consistent (Lvl 1 to Lvl K)
        ct = ct.sort_index(ascending=True).sort_index(axis=1, ascending=True)

        if mode == 'names':
            res_df = ct.copy().astype(object)
            for r in ct.index:
                for c in ct.columns:
                    names = df_comp[(df_comp['Biplot (Kompromi)'] == r) & (df_comp['Statis (Tahunan)'] == c)]['Kabupaten/Kota'].tolist()
                    res_df.loc[r, c] = ", ".join(names) if names else "-"
            res_df = res_df.reset_index()
        else:
            res_df = ct.reset_index()
            
        cols = [{"name": str(i), "id": str(i)} for i in res_df.columns]
        
        # D. BUILD MAPS, SCATTERS, PIE
        # Define exact color map matching between Klaster & Statis prefixes
        BIPLOT_COLOR_MAP = {}
        for key, color in CLUSTER_COLOR_MAP.items():
            BIPLOT_COLOR_MAP[key] = color
            BIPLOT_COLOR_MAP[key.replace("Cluster", "Statis")] = color
            
        BIPLOT_ORDER = [o.replace("Cluster", "Statis") for o in LEVEL_ORDER]

        fig_map_biplot, fig_map_statis = go.Figure(), go.Figure()
        if indonesia_geojson:
            mapbox_center, mapbox_zoom = {"lat": -6.9, "lon": 107}, 6.5
            df_map_b = pd.DataFrame({'Kab/Kota': obs_labels, 'Cluster': labels_static, 'match_key': obs_labels})
            df_map_s = pd.DataFrame({'Kab/Kota': obs_labels, 'Cluster': labels_biplot, 'match_key': obs_labels})
            
            fig_map_biplot = px.choropleth_mapbox(df_map_b, geojson=indonesia_geojson, locations='match_key', featureidkey='properties.id_cocok', color='Cluster', color_discrete_map=BIPLOT_COLOR_MAP, category_orders={"Cluster": BIPLOT_ORDER}, hover_name='Kab/Kota', mapbox_style="carto-positron", center=mapbox_center, zoom=mapbox_zoom, opacity=0.7)
            fig_map_biplot.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            
            fig_map_statis = px.choropleth_mapbox(df_map_s, geojson=indonesia_geojson, locations='match_key', featureidkey='properties.id_cocok', color='Cluster', color_discrete_map=CLUSTER_COLOR_MAP, category_orders={"Cluster": LEVEL_ORDER}, hover_name='Kab/Kota', mapbox_style="carto-positron", center=mapbox_center, zoom=mapbox_zoom, opacity=0.7)
            fig_map_statis.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            
            for f, df_m in [(fig_map_biplot, df_map_b), (fig_map_statis, df_map_s)]:
                lon_list, lat_list, text_list = [], [], []
                for _, row in df_m.iterrows():
                    area = row['Kab/Kota']
                    geom = gdf[gdf['id_cocok'] == area]
                    if not geom.empty:
                        lon_list.append(geom.geometry.centroid.x.values[0])
                        lat_list.append(geom.geometry.centroid.y.values[0])
                        text_list.append(area)
                if text_list:
                    f.add_trace(go.Scattermapbox(lon=lon_list, lat=lat_list, mode='text', text=text_list, textfont=dict(size=9, color='black'), showlegend=False))
                    
        # PCA 2D for selected year biplot scatter
        pca_2d = PCA(n_components=2).fit_transform(X_std)
        fig_scatter_biplot = px.scatter(x=pca_2d[:,0], y=pca_2d[:,1], color=labels_static, text=obs_labels, color_discrete_map=BIPLOT_COLOR_MAP, category_orders={"color": BIPLOT_ORDER})
        fig_scatter_biplot.update_traces(marker=dict(size=9), textposition='top center')
        fig_scatter_biplot.update_layout(template='plotly_white', xaxis_title="PC1", yaxis_title="PC2")
        
        # STATIS Trajectory compromise scatter
        fig_scatter_statis = px.scatter(x=scores_comp[:,0], y=scores_comp[:,1], color=labels_biplot, text=obs_labels, color_discrete_map=CLUSTER_COLOR_MAP, category_orders={"color": LEVEL_ORDER})
        fig_scatter_statis.update_traces(marker=dict(size=9), textposition='top center')
        fig_scatter_statis.update_layout(template='plotly_white', xaxis_title="PC1 Kompromi", yaxis_title="PC2 Kompromi")
        
        from collections import Counter
        counts_b = Counter(labels_static)
        fig_pie_biplot = px.pie(
            names=list(counts_b.keys()),
            values=list(counts_b.values()),
            color=list(counts_b.keys()),
            color_discrete_map=BIPLOT_COLOR_MAP,
            category_orders={"names": BIPLOT_ORDER}
        )
        fig_pie_biplot.update_layout(template='plotly_white')
        
        counts_s = Counter(labels_biplot)
        fig_pie_statis = px.pie(
            names=list(counts_s.keys()),
            values=list(counts_s.values()),
            color=list(counts_s.keys()),
            color_discrete_map=CLUSTER_COLOR_MAP,
            category_orders={"names": LEVEL_ORDER}
        )
        fig_pie_statis.update_layout(template='plotly_white')
        
        return (
            res_df.to_dict('records'), cols,
            f"Peta Klaster Biplot ({year})", fig_map_biplot,
            "Peta Klaster Kompromi STATIS", fig_map_statis,
            f"Scatter Plot Klaster Biplot ({year})", fig_scatter_biplot,
            "Scatter Plot Klaster Kompromi STATIS", fig_scatter_statis,
            f"Proporsi Klaster Biplot ({year})", fig_pie_biplot,
            "Proporsi Klaster Kompromi STATIS", fig_pie_statis,
            {'display': 'block'}, ""
        )
    except Exception as e:
        print(f"Error Section 10: {e}")
        return [], [], "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, {'display': 'none'}, ""

# 11. Callback Section 11: Statis vs IPM Rata-rata
@app.callback(
    Output('statis-vs-ipm-avg-table', 'data'),
    Output('statis-vs-ipm-avg-table', 'columns'),
    Output('title-statis-ipm-avg-map-statis', 'children'),
    Output('statis-ipm-avg-map-statis', 'figure'),
    Output('title-statis-ipm-avg-map-ipm', 'children'),
    Output('statis-ipm-avg-map-ipm', 'figure'),
    Output('title-statis-ipm-avg-pie-statis', 'children'),
    Output('statis-ipm-avg-pie-statis', 'figure'),
    Output('title-statis-ipm-avg-pie-ipm', 'children'),
    Output('statis-ipm-avg-pie-ipm', 'figure'),
    Output('statis-ipm-avg-results-container', 'style'),
    Output('spinner-run-statis-ipm-avg', 'children'),
    Input('btn-run-statis-ipm-avg', 'n_clicks'),
    State('statis-vs-ipm-avg-k', 'value'),
    State('statis-vs-ipm-avg-view-mode', 'value'),
    State('statis-vs-ipm-avg-year', 'value'),
    State('statis-core-store', 'data'),
    State('global-data-store', 'data')
)
def cb_run_statis_vs_ipm_avg(n, k, mode, year, statis_data, global_data):
    if not n or not statis_data or not global_data:
        return [], [], "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, {'display': 'none'}, ""
        
    try:
        from sklearn.cluster import KMeans
        # A. STATIS Trajectory Klaster (Aligned with Section 7)
        obs_labels = statis_data['obs_labels']
        coords_dict = statis_data['per_year_coords']
        sheet_names = statis_data.get('sheet_names', sorted(list(coords_dict.keys())))
        alphas = statis_data.get('alphas', [1.0] * len(sheet_names))
        
        features = []
        for i in range(len(obs_labels)):
            city_feats = []
            for j, yr in enumerate(sheet_names):
                w = np.sqrt(alphas[j])
                coords_yr = np.array(coords_dict[str(yr)])
                city_feats.extend(coords_yr[i, :] * w)
            features.append(city_feats)
        X_traj = np.array(features)
        
        km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X_traj)
        
        # --- ALIGNED LABELING (Ref Section 7 ranking by Compromise PC1) ---
        scores_comp = np.array(statis_data['scores'])
        cl_means = [np.mean(scores_comp[km.labels_ == cl, 0]) for cl in range(k)]
        rnk = np.argsort(cl_means)
        mp = {old: new for new, old in enumerate(rnk)}
        name_map = {0: "Rendah", 1: "Sedang", 2: "Tinggi"}
        labels_statis = [f"Klaster {mp[l]+1} ({name_map.get(mp[l], 'Level ' + str(mp[l]+1))})" for l in km.labels_]
        
        # B. IPM for Selected Year
        df_all = pd.read_json(io.StringIO(global_data['df_json']), orient='split')
        ipm_col = None
        for c in df_all.columns:
            if 'ipm' in c.lower():
                ipm_col = c
                break
        
        if not ipm_col:
            return [{'Error': 'Kolom IPM tidak ditemukan'}], [{'name': 'Error', 'id': 'Error'}], "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, {'display': 'none'}, ""

        df_year_ipm = df_all[df_all['Tahun'].astype(str) == str(year)].set_index('Kabupaten/Kota').reindex(obs_labels)
        ipm_vals = df_year_ipm[ipm_col].fillna(df_year_ipm[ipm_col].mean()).values
        
        def ipm_cat(val):
            if val >= 80: return "Sangat Tinggi"
            if val >= 70: return "Tinggi"
            if val >= 55: return "Sedang" # Align with UNDP Standard in Section 8
            return "Rendah"
            
        cats_ipm = [ipm_cat(v) for v in ipm_vals]
        
        df_comp = pd.DataFrame({
            'Kabupaten/Kota': obs_labels,
            'STATIS_Compromise': labels_statis,
            'IPM_Average': cats_ipm
        })
        
        # Reorder IPM cat
        order = ["Sangat Tinggi", "Tinggi", "Sedang", "Rendah"]
        df_comp['IPM_Average'] = pd.Categorical(df_comp['IPM_Average'], categories=[o for o in order if o in df_comp['IPM_Average'].unique()], ordered=True)
        
        ct = pd.crosstab(df_comp['STATIS_Compromise'], df_comp['IPM_Average'])

        # Sort CT by Klaster Level (rows = STATIS Compromise, cols = IPM)
        ct = ct.sort_index(axis=0, ascending=True)

        if mode == 'names':
            res_df = ct.copy().astype(object)
            for r in ct.index:
                for c in ct.columns:
                    names = df_comp[(df_comp['STATIS_Compromise'] == r) & (df_comp['IPM_Average'] == c)]['Kabupaten/Kota'].tolist()
                    res_df.loc[r, c] = ", ".join(names) if names else "-"
            res_df = res_df.reset_index()
        else:
            res_df = ct.reset_index()
            
        cols = [{"name": str(i), "id": str(i)} for i in res_df.columns]
        
        # C. BUILD MAPS, PIE
        fig_map_statis, fig_map_ipm = go.Figure(), go.Figure()
        if indonesia_geojson:
            mapbox_center, mapbox_zoom = {"lat": -6.9, "lon": 107}, 6.5
            df_map_s = pd.DataFrame({'Kab/Kota': obs_labels, 'Cluster': labels_statis, 'match_key': obs_labels})
            df_map_i = pd.DataFrame({'Kab/Kota': obs_labels, 'Cluster': cats_ipm, 'match_key': obs_labels})
            
            fig_map_statis = px.choropleth_mapbox(df_map_s, geojson=indonesia_geojson, locations='match_key', featureidkey='properties.id_cocok', color='Cluster', color_discrete_map=CLUSTER_COLOR_MAP, category_orders={"Cluster": LEVEL_ORDER}, hover_name='Kab/Kota', mapbox_style="carto-positron", center=mapbox_center, zoom=mapbox_zoom, opacity=0.7)
            fig_map_statis.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            
            fig_map_ipm = px.choropleth_mapbox(df_map_i, geojson=indonesia_geojson, locations='match_key', featureidkey='properties.id_cocok', color='Cluster', color_discrete_map=IPM_COLOR_MAP, category_orders={"Cluster": IPM_ORDER}, hover_name='Kab/Kota', mapbox_style="carto-positron", center=mapbox_center, zoom=mapbox_zoom, opacity=0.7)
            fig_map_ipm.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            
            for f, df_m in [(fig_map_statis, df_map_s), (fig_map_ipm, df_map_i)]:
                lon_list, lat_list, text_list = [], [], []
                for _, row in df_m.iterrows():
                    area = row['Kab/Kota']
                    geom = gdf[gdf['id_cocok'] == area]
                    if not geom.empty:
                        lon_list.append(geom.geometry.centroid.x.values[0])
                        lat_list.append(geom.geometry.centroid.y.values[0])
                        text_list.append(area)
                if text_list:
                    f.add_trace(go.Scattermapbox(lon=lon_list, lat=lat_list, mode='text', text=text_list, textfont=dict(size=9, color='black'), showlegend=False))
                    
        from collections import Counter
        counts_s = Counter(labels_statis)
        fig_pie_statis = px.pie(
            names=list(counts_s.keys()),
            values=list(counts_s.values()),
            color=list(counts_s.keys()),
            color_discrete_map=CLUSTER_COLOR_MAP,
            category_orders={"names": LEVEL_ORDER}
        )
        fig_pie_statis.update_layout(template='plotly_white')
        
        counts_i = Counter(cats_ipm)
        fig_pie_ipm = px.pie(
            names=list(counts_i.keys()),
            values=list(counts_i.values()),
            color=list(counts_i.keys()),
            color_discrete_map=IPM_COLOR_MAP,
            category_orders={"names": IPM_ORDER}
        )
        fig_pie_ipm.update_layout(template='plotly_white')
        
        return (
            res_df.to_dict('records'), cols,
            "Peta Klaster Kompromi STATIS", fig_map_statis,
            "Peta Kategori IPM (UNDP)", fig_map_ipm,
            "Proporsi Klaster Kompromi STATIS", fig_pie_statis,
            "Proporsi Kategori IPM (UNDP)", fig_pie_ipm,
            {'display': 'block'}, ""
        )
    except Exception as e:
        print(f"Error Section 11: {e}")
        return [], [], "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, {'display': 'none'}, ""


# --- CALLBACK: PERBANDINGAN CLUSTER STATIS VS KATEGORI IPM (UNDP) ---
@app.callback(
    Output('statis-vs-ipm-table', 'data'),
    Output('statis-vs-ipm-table', 'columns'),
    Output('title-statis-vs-ipm-map-statis', 'children'),
    Output('statis-vs-ipm-map-statis', 'figure'),
    Output('title-statis-vs-ipm-map-ipm', 'children'),
    Output('statis-vs-ipm-map-ipm', 'figure'),
    Output('title-statis-vs-ipm-pie-statis', 'children'),
    Output('statis-vs-ipm-pie-statis', 'figure'),
    Output('title-statis-vs-ipm-pie-ipm', 'children'),
    Output('statis-vs-ipm-pie-ipm', 'figure'),
    Output('statis-vs-ipm-results-container', 'style'),
    Output('spinner-run-statis-vs-ipm', 'children'),
    Input('btn-run-statis-vs-ipm', 'n_clicks'),
    Input('statis-vs-ipm-view-mode', 'value'),
    State('statis-vs-ipm-year', 'value'),
    State('statis-vs-ipm-k', 'value'),
    State('global-data-store', 'data'),
    State('statis-core-store', 'data')
)
def cb_run_statis_vs_ipm(n_clicks, view_mode, sel_year, k, data_store, statis_store):
    if not n_clicks or not sel_year or not data_store or not statis_store:
        return [], [], "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, {'display': 'none'}, ""

    try:
        from sklearn.cluster import KMeans
        # 1. Ambil IPM kategories dari data asli
        df = pd.read_json(io.StringIO(data_store['df_json']), orient='split')
        df_yr = df[df['Tahun'] == sel_year].set_index('Kabupaten/Kota')
        
        def categorize_ipm(val):
            if val >= 80: return "Sangat Tinggi"
            elif val >= 70: return "Tinggi"
            elif val >= 55: return "Sedang"
            else: return "Rendah"
        df_yr['IPM_Cat'] = df_yr['IPM'].apply(categorize_ipm)
        
        # 2. Ambil label K-Means STATIS Tahunan dari statis store
        obs_labels = statis_store['obs_labels']
        str_year = str(sel_year)
        if str_year not in statis_store['per_year_coords']:
            return [], [], "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, {'display': 'none'}, ""

        coords = np.array(statis_store['per_year_coords'][str_year])
        km_curr = KMeans(n_clusters=k, random_state=42, n_init=10)
        lbls = km_curr.fit_predict(coords)
        
        # Rank by PC1
        cl_means = [np.mean(coords[lbls == cl, 0]) for cl in range(k)]
        sorted_indices = np.argsort(cl_means)
        rank_map = {old: new for new, old in enumerate(sorted_indices)}
        name_map = {0: "Rendah", 1: "Sedang", 2: "Tinggi", 3: "Sangat Tinggi"}
        str_labels = [f"Klaster {rank_map[l]+1} ({name_map.get(rank_map[l], 'Level ' + str(rank_map[l]+1))})" for l in lbls]
        
        # Gabung
        df_clusters = pd.DataFrame({'Cluster_Statis': str_labels}, index=obs_labels)
        df_merged = df_yr.join(df_clusters).dropna(subset=['Cluster_Statis', 'IPM_Cat'])
        
        # Tabulasi Silang
        categories = ["Sangat Tinggi", "Tinggi", "Sedang", "Rendah"]
        target_clusters = [f"Klaster {i+1} ({name_map.get(i, 'Level ' + str(i+1))})" for i in range(k)]
        
        df_merged['IPM_Cat'] = pd.Categorical(df_merged['IPM_Cat'], categories=categories, ordered=True)
        df_merged['Cluster_Statis'] = pd.Categorical(df_merged['Cluster_Statis'], categories=target_clusters, ordered=True)
        
        ct = pd.crosstab(df_merged['IPM_Cat'], df_merged['Cluster_Statis'])
        ct = ct.reindex(index=categories, fill_value=0).reindex(columns=target_clusters, fill_value=0)
        
        if view_mode == 'names':
            res_df = ct.copy().astype(object)
            for r in ct.index:
                for c in ct.columns:
                    names = df_merged[(df_merged['IPM_Cat'] == r) & (df_merged['Cluster_Statis'] == c)].index.tolist()
                    res_df.loc[r, c] = ", ".join(names) if names else "-"
            res_df = res_df.reset_index()
        else:
            res_df = ct.reset_index()
            
        cols = [{"name": str(c), "id": str(c)} for c in res_df.columns]
        
        # C. BUILD MAPS AND PIES
        fig_map_statis, fig_map_ipm = go.Figure(), go.Figure()
        if indonesia_geojson:
            mapbox_center, mapbox_zoom = {"lat": -6.9, "lon": 107}, 6.5
            df_map_s = pd.DataFrame({'Kab/Kota': obs_labels, 'Cluster': str_labels, 'match_key': obs_labels})
            cats_ipm_list = df_yr['IPM_Cat'].reindex(obs_labels).fillna('Sedang').tolist()
            df_map_i = pd.DataFrame({'Kab/Kota': obs_labels, 'Cluster': cats_ipm_list, 'match_key': obs_labels})
            
            fig_map_statis = px.choropleth_mapbox(df_map_s, geojson=indonesia_geojson, locations='match_key', featureidkey='properties.id_cocok', color='Cluster', color_discrete_map=CLUSTER_COLOR_MAP, category_orders={"Cluster": LEVEL_ORDER}, hover_name='Kab/Kota', mapbox_style="carto-positron", center=mapbox_center, zoom=mapbox_zoom, opacity=0.7)
            fig_map_statis.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            
            fig_map_ipm = px.choropleth_mapbox(df_map_i, geojson=indonesia_geojson, locations='match_key', featureidkey='properties.id_cocok', color='Cluster', color_discrete_map=IPM_COLOR_MAP, category_orders={"Cluster": IPM_ORDER}, hover_name='Kab/Kota', mapbox_style="carto-positron", center=mapbox_center, zoom=mapbox_zoom, opacity=0.7)
            fig_map_ipm.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            
            for f, df_m in [(fig_map_statis, df_map_s), (fig_map_ipm, df_map_i)]:
                lon_list, lat_list, text_list = [], [], []
                for _, row in df_m.iterrows():
                    area = row['Kab/Kota']
                    geom = gdf[gdf['id_cocok'] == area]
                    if not geom.empty:
                        lon_list.append(geom.geometry.centroid.x.values[0])
                        lat_list.append(geom.geometry.centroid.y.values[0])
                        text_list.append(area)
                if text_list:
                    f.add_trace(go.Scattermapbox(lon=lon_list, lat=lat_list, mode='text', text=text_list, textfont=dict(size=9, color='black'), showlegend=False))
                    
        from collections import Counter
        counts_s = Counter(str_labels)
        fig_pie_statis = px.pie(
            names=list(counts_s.keys()),
            values=list(counts_s.values()),
            color=list(counts_s.keys()),
            color_discrete_map=CLUSTER_COLOR_MAP,
            category_orders={"names": LEVEL_ORDER}
        )
        fig_pie_statis.update_layout(template='plotly_white')
        
        counts_i = Counter(df_yr['IPM_Cat'].reindex(obs_labels).fillna('Sedang').tolist())
        fig_pie_ipm = px.pie(
            names=list(counts_i.keys()),
            values=list(counts_i.values()),
            color=list(counts_i.keys()),
            color_discrete_map=IPM_COLOR_MAP,
            category_orders={"names": IPM_ORDER}
        )
        fig_pie_ipm.update_layout(template='plotly_white')
        
        return (
            res_df.to_dict('records'), cols,
            f"Peta Klaster STATIS ({sel_year})", fig_map_statis,
            f"Peta Kategori IPM ({sel_year})", fig_map_ipm,
            f"Proporsi Klaster STATIS ({sel_year})", fig_pie_statis,
            f"Proporsi Kategori IPM ({sel_year})", fig_pie_ipm,
            {'display': 'block'}, ""
        )
    except Exception as e:
        print(f"Error cb_run_statis_vs_ipm: {e}")
        return [], [], "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, {'display': 'none'}, ""


@app.callback(
    Output("download-statis-vs-ipm-tex", "data"),
    Input("btn-dl-statis-vs-ipm-tex", "n_clicks"),
    State("statis-vs-ipm-table", "data"),
    State("statis-vs-ipm-table", "columns"),
    State("statis-vs-ipm-year", "value"),
    State("statis-vs-ipm-view-mode", "value"),
    prevent_initial_call=True
)
def dl_statis_vs_ipm_tex(n_clicks, data, columns, year, mode):
    if not n_clicks or not data or not columns: return None
    sfx = "name" if mode == "names" else "sum"
    filename = f"output_table_statis_vs_ipm_{sfx}_{year}.tex"
    if mode == "names":
        caption = f"Nama Daerah Perbandingan Klaster STATIS Tahunan vs IPM (UNDP) ({year})"
        label = f"statis_ipm_name_{year}"
    else:
        caption = f"Perbandingan Klaster STATIS Tahunan vs Kategori IPM (UNDP) ({year})"
        label = f"statis_ipm_{year}"
    content = ui_table_to_latex(data, columns, caption, f"tab:{label}")
    return dict(content=content, filename=filename)


# --- CALLBACK: PERBANDINGAN CLUSTER KOMPROMI STATIS VS CLUSTER STATIS TAHUNAN ---
@app.callback(
    Output('compromise-statis-vs-statis-table', 'data'),
    Output('compromise-statis-vs-statis-table', 'columns'),
    Output('title-compromise-statis-vs-statis-map-comp', 'children'),
    Output('compromise-statis-vs-statis-map-comp', 'figure'),
    Output('title-compromise-statis-vs-statis-map-statis', 'children'),
    Output('compromise-statis-vs-statis-map-statis', 'figure'),
    Output('title-compromise-statis-vs-statis-scatter-comp', 'children'),
    Output('compromise-statis-vs-statis-scatter-comp', 'figure'),
    Output('title-compromise-statis-vs-statis-scatter-statis', 'children'),
    Output('compromise-statis-vs-statis-scatter-statis', 'figure'),
    Output('title-compromise-statis-vs-statis-pie-comp', 'children'),
    Output('compromise-statis-vs-statis-pie-comp', 'figure'),
    Output('title-compromise-statis-vs-statis-pie-statis', 'children'),
    Output('compromise-statis-vs-statis-pie-statis', 'figure'),
    Output('compromise-statis-vs-statis-results-container', 'style'),
    Output('spinner-run-compromise-statis-vs-statis', 'children'),
    Input('btn-run-compromise-statis-vs-statis', 'n_clicks'),
    Input('compromise-statis-vs-statis-view-mode', 'value'),
    State('compromise-statis-vs-statis-year', 'value'),
    State('compromise-statis-vs-statis-k', 'value'),
    State('statis-core-store', 'data')
)
def cb_run_compromise_statis_vs_statis(n_clicks, view_mode, year, k, statis_data):
    if not n_clicks or not statis_data or not year:
        return [], [], "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, {'display': 'none'}, ""
    
    try:
        from sklearn.cluster import KMeans
        # A. Get STATIS Trajectory Klaster (Compromise)
        obs_labels = statis_data['obs_labels']
        coords_dict = statis_data['per_year_coords']
        sheet_names = statis_data.get('sheet_names', sorted(list(coords_dict.keys())))
        alphas = statis_data.get('alphas', [1.0] * len(sheet_names))
        
        # Build weighted trajectory features (Lavit 1994 logic)
        features = []
        for i in range(len(obs_labels)):
            city_feats = []
            for j, yr in enumerate(sheet_names):
                w = np.sqrt(alphas[j])
                coords_yr = np.array(coords_dict[str(yr)])
                city_feats.extend(coords_yr[i, :] * w)
            features.append(city_feats)
        X_traj = np.array(features)
        
        km_comp = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X_traj)
        
        # Rank by Compromise PC1
        scores_comp = np.array(statis_data['scores'])
        cl_means_c = [np.mean(scores_comp[km_comp.labels_ == cl, 0]) for cl in range(k)]
        rnk_c = np.argsort(cl_means_c)
        mp_c = {old: new for new, old in enumerate(rnk_c)}
        name_map = {0: "Rendah", 1: "Sedang", 2: "Tinggi", 3: "Sangat Tinggi"}
        labels_comp = [f"Klaster {mp_c[l]+1} ({name_map.get(mp_c[l], 'Level ' + str(mp_c[l]+1))})" for l in km_comp.labels_]
        
        # B. Get STATIS Tahunan Klaster (for selected year)
        str_year = str(year)
        if str_year not in coords_dict:
            return [], [], "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, {'display': 'none'}, ""

        X_year = np.array(coords_dict[str_year])
        km_yr = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X_year)
        
        # Rank by current year STATIS PC1
        cl_means_y = [np.mean(X_year[km_yr.labels_ == cl, 0]) for cl in range(k)]
        rnk_y = np.argsort(cl_means_y)
        mp_y = {old: new for new, old in enumerate(rnk_y)}
        labels_yr = [f"Klaster {mp_y[l]+1} ({name_map.get(mp_y[l], 'Level ' + str(mp_y[l]+1))})" for l in km_yr.labels_]
        
        # C. Cross-tab
        df_comp = pd.DataFrame({
            'Kabupaten/Kota': obs_labels,
            'Kompromi': labels_comp,
            'Tahunan': labels_yr
        })
        
        target_clusters = [f"Klaster {i+1} ({name_map.get(i, 'Level ' + str(i+1))})" for i in range(k)]
        df_comp['Kompromi'] = pd.Categorical(df_comp['Kompromi'], categories=target_clusters, ordered=True)
        df_comp['Tahunan'] = pd.Categorical(df_comp['Tahunan'], categories=target_clusters, ordered=True)
        
        ct = pd.crosstab(df_comp['Kompromi'], df_comp['Tahunan'])
        ct = ct.reindex(index=target_clusters, fill_value=0).reindex(columns=target_clusters, fill_value=0)

        if view_mode == 'names':
            res_df = ct.copy().astype(object)
            for r in ct.index:
                for c in ct.columns:
                    names = df_comp[(df_comp['Kompromi'] == r) & (df_comp['Tahunan'] == c)]['Kabupaten/Kota'].tolist()
                    res_df.loc[r, c] = ", ".join(names) if names else "-"
            res_df = res_df.reset_index()
        else:
            res_df = ct.reset_index()
            
        cols = [{"name": str(i), "id": str(i)} for i in res_df.columns]
        
        # D. BUILD MAPS, SCATTERS, PIE
        fig_map_comp, fig_map_statis = go.Figure(), go.Figure()
        if indonesia_geojson:
            mapbox_center, mapbox_zoom = {"lat": -6.9, "lon": 107}, 6.5
            df_map_c = pd.DataFrame({'Kab/Kota': obs_labels, 'Cluster': labels_comp, 'match_key': obs_labels})
            df_map_s = pd.DataFrame({'Kab/Kota': obs_labels, 'Cluster': labels_yr, 'match_key': obs_labels})
            
            fig_map_comp = px.choropleth_mapbox(df_map_c, geojson=indonesia_geojson, locations='match_key', featureidkey='properties.id_cocok', color='Cluster', color_discrete_map=CLUSTER_COLOR_MAP, category_orders={"Cluster": LEVEL_ORDER}, hover_name='Kab/Kota', mapbox_style="carto-positron", center=mapbox_center, zoom=mapbox_zoom, opacity=0.7)
            fig_map_comp.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            
            fig_map_statis = px.choropleth_mapbox(df_map_s, geojson=indonesia_geojson, locations='match_key', featureidkey='properties.id_cocok', color='Cluster', color_discrete_map=CLUSTER_COLOR_MAP, category_orders={"Cluster": LEVEL_ORDER}, hover_name='Kab/Kota', mapbox_style="carto-positron", center=mapbox_center, zoom=mapbox_zoom, opacity=0.7)
            fig_map_statis.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            
            for f, df_m in [(fig_map_comp, df_map_c), (fig_map_statis, df_map_s)]:
                lon_list, lat_list, text_list = [], [], []
                for _, row in df_m.iterrows():
                    area = row['Kab/Kota']
                    geom = gdf[gdf['id_cocok'] == area]
                    if not geom.empty:
                        lon_list.append(geom.geometry.centroid.x.values[0])
                        lat_list.append(geom.geometry.centroid.y.values[0])
                        text_list.append(area)
                if text_list:
                    f.add_trace(go.Scattermapbox(lon=lon_list, lat=lat_list, mode='text', text=text_list, textfont=dict(size=9, color='black'), showlegend=False))
                    
        # Scatters
        fig_scatter_comp = px.scatter(x=scores_comp[:,0], y=scores_comp[:,1], color=labels_comp, text=obs_labels, color_discrete_map=CLUSTER_COLOR_MAP, category_orders={"color": LEVEL_ORDER})
        fig_scatter_comp.update_traces(marker=dict(size=9), textposition='top center')
        fig_scatter_comp.update_layout(template='plotly_white', xaxis_title="PC1 Kompromi", yaxis_title="PC2 Kompromi")
        
        fig_scatter_statis = px.scatter(x=X_year[:,0], y=X_year[:,1], color=labels_yr, text=obs_labels, color_discrete_map=CLUSTER_COLOR_MAP, category_orders={"color": LEVEL_ORDER})
        fig_scatter_statis.update_traces(marker=dict(size=9), textposition='top center')
        fig_scatter_statis.update_layout(template='plotly_white', xaxis_title="PC1 Tahunan", yaxis_title="PC2 Tahunan")
        
        from collections import Counter
        counts_c = Counter(labels_comp)
        fig_pie_comp = px.pie(
            names=list(counts_c.keys()),
            values=list(counts_c.values()),
            color=list(counts_c.keys()),
            color_discrete_map=CLUSTER_COLOR_MAP,
            category_orders={"names": LEVEL_ORDER}
        )
        fig_pie_comp.update_layout(template='plotly_white')
        
        counts_s = Counter(labels_yr)
        fig_pie_statis = px.pie(
            names=list(counts_s.keys()),
            values=list(counts_s.values()),
            color=list(counts_s.keys()),
            color_discrete_map=CLUSTER_COLOR_MAP,
            category_orders={"names": LEVEL_ORDER}
        )
        fig_pie_statis.update_layout(template='plotly_white')
        
        return (
            res_df.to_dict('records'), cols,
            "Peta Klaster Kompromi STATIS", fig_map_comp,
            f"Peta Klaster STATIS Tahunan ({year})", fig_map_statis,
            "Scatter Plot Klaster Kompromi STATIS", fig_scatter_comp,
            f"Scatter Plot Klaster STATIS Tahunan ({year})", fig_scatter_statis,
            "Proporsi Klaster Kompromi STATIS", fig_pie_comp,
            f"Proporsi Klaster STATIS Tahunan ({year})", fig_pie_statis,
            {'display': 'block'}, ""
        )
    except Exception as e:
        print(f"Error cb_run_compromise_statis_vs_statis: {e}")
        return [], [], "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, {'display': 'none'}, ""


@app.callback(
    Output("download-compromise-statis-vs-statis-tex", "data"),
    Input("btn-dl-compromise-statis-vs-statis-tex", "n_clicks"),
    State("compromise-statis-vs-statis-table", "data"),
    State("compromise-statis-vs-statis-table", "columns"),
    State("compromise-statis-vs-statis-year", "value"),
    State("compromise-statis-vs-statis-view-mode", "value"),
    prevent_initial_call=True
)
def dl_compromise_statis_vs_statis_tex(n_clicks, data, columns, year, mode):
    if not n_clicks or not data or not columns: return None
    sfx = "name" if mode == "names" else "sum"
    filename = f"output_table_compromise_vs_statis_{sfx}_{year}.tex"
    if mode == "names":
        caption = f"Nama Daerah Perbandingan Klaster Kompromi STATIS vs Klaster STATIS Tahunan ({year})"
        label = f"compromise_statis_name_{year}"
    else:
        caption = f"Perbandingan Klaster Kompromi STATIS vs Klaster STATIS Tahunan ({year})"
        label = f"compromise_statis_{year}"
    content = ui_table_to_latex(data, columns, caption, f"tab:{label}")
    return dict(content=content, filename=filename)


# 7c. Run Descriptive Statistics
@app.callback(
    Output('desc-table-output', 'children'),
    Output('desc-boxplot-output', 'children'),
    Output('desc-formula-output', 'children'),
    Output('desc-corr-output', 'children'),
    Output('spinner-run-desc', 'children'),
    Input('btn-run-desc', 'n_clicks'),
    State('desc-year-dropdown', 'value'),
    State('desc-weight-mode', 'value'),
    State('desc-weight-var-dropdown', 'value'),
    State('desc-exclude-vars', 'value'),
    State('global-data-store', 'data')
)
def cb_run_desc(n_clicks, selected_year, weight_mode, weight_var, exclude_vars, data):
    if not n_clicks or not data or not selected_year:
        return "", "", "", "", ""

    try:
        df_all = pd.read_json(io.StringIO(data['df_json']), orient='split')
        
        # 1. Hitung Bobot m_i (jika mode weighted)
        m_weights = None
        if weight_mode == 'weighted' and weight_var and weight_var in df_all.columns:
            # Rata-rata variabel bobot per wilayah lintas tahun
            # m_i = \bar{V}_i / \sum \bar{V}_i
            df_weight = df_all.groupby('Kabupaten/Kota')[weight_var].mean()
            m_sum = df_weight.sum()
            if m_sum > 0:
                m_weights = (df_weight / m_sum).to_dict()
        
        # 2. Filter Data Tahun Terpilih
        tahun_col = df_all['Tahun']
        try:
            mask = tahun_col == int(selected_year)
        except (ValueError, TypeError):
            mask = tahun_col.astype(str) == str(selected_year)
        df_year = df_all[mask].copy()

        # Drop metadata columns
        drop_cols = ['Kabupaten/Kota', 'Provinsi', 'Tahun']
        df_clean = df_year.drop(columns=[c for c in drop_cols if c in df_year.columns], errors='ignore')

        # Detect numeric
        df = df_clean.select_dtypes(include='number').dropna(axis=1, how='all')
        non_numeric = df_clean.select_dtypes(exclude='number').columns.tolist()
        # Apply exclude-vars filter
        if exclude_vars:
            df = df.drop(columns=[v for v in exclude_vars if v in df.columns])
    except Exception as e:
        return html.P(f"Error membaca data: {e}", style={'color': 'red'}), "", "", "", ""

    # --- Diagnostic info bar ---
    if df_year.empty:
        diag = html.Div(
            f"⚠️ Tidak ada data untuk tahun {selected_year}. Pastikan kolom 'Tahun' di data cocok dengan pilihan.",
            style={'backgroundColor': '#FFF3CD', 'color': '#856404', 'padding': '10px',
                   'borderRadius': '6px', 'marginBottom': '10px', 'fontWeight': 'bold'}
        )
        return diag, "", "", "", ""

    mode_text = "Dengan Bobot" if m_weights else "Tanpa Bobot (Konvensional)"
    info_parts = [f"✅ {len(df.columns)} kolom numerik | Mode: {mode_text}"]
    if m_weights:
        info_parts.append(f"Bobot: {weight_var}")
    
    diag_bar = html.Div(info_parts[0] + (" | " + info_parts[1] if len(info_parts) > 1 else ""),
        style={'backgroundColor': '#E8F5E9' if m_weights else '#E3F2FD', 'padding': '8px 14px', 'borderRadius': '6px',
               'marginBottom': '12px', 'fontSize': '13px', 'color': '#333', 'fontWeight': 'bold'})

    if df.empty:
        return html.Div([
            diag_bar,
            html.P("Tidak ada kolom numerik yang dapat dianalisis.", style={'color': 'red'})
        ]), "", "", "", ""

    from scipy.stats import skew, kurtosis as kurt
    # Build summary stats
    rows = []
    # Jika weighted, kita butuh list m_i yang sejajar dengan df
    m_list = None
    if m_weights:
        m_list = np.array([m_weights.get(kab, 0) for kab in df_year['Kabupaten/Kota']])
        # Re-normalize if any missing to ensure sum = 1 for the year's specific rows
        if m_list.sum() > 0:
            m_list = m_list / m_list.sum()

    for col in df.columns:
        vals = df[col].values
        n = len(vals)
        
        if m_weights and m_list is not None:
            # --- WEIGHTED CALCULATIONS ---
            mu = np.sum(m_list * vals)
            diff = vals - mu
            variance = np.sum(m_list * (diff**2))
            sigma = np.sqrt(variance)
            
            # Skewness: m3 / sigma^3
            m3 = np.sum(m_list * (diff**3))
            skew_v = m3 / (sigma**3) if sigma > 0 else 0
            
            # Kurtosis: (m4 / sigma^4) - 3
            m4 = np.sum(m_list * (diff**4))
            kurt_v = (m4 / (sigma**4)) - 3 if sigma > 0 else 0
            
            cv_v = (sigma / mu * 100) if mu != 0 else None
            
            rows.append({
                'Variabel': col,
                'N': n,
                'Mean (μ)': round(mu, 4),
                'Std Dev (σ)': round(sigma, 4),
                'Min': round(np.min(vals), 4),
                'Q1': round(np.percentile(vals, 25), 4),
                'Median': round(np.median(vals), 4),
                'Q3': round(np.percentile(vals, 75), 4),
                'Max': round(np.max(vals), 4),
                'Skewness (γ1)': round(skew_v, 4),
                'Kurtosis (γ2)': round(kurt_v, 4),
                'CV (%)': round(cv_v, 2) if cv_v is not None else None
            })
        else:
            # --- UNWEIGHTED (POPULATION PARAMETERS) ---
            from scipy.stats import skew, kurtosis as kurt
            mean_v = np.mean(vals)
            std_v = np.std(vals, ddof=0) # Sesuai Lampiran_Rumus.tex (Populasi Utuh)
            rows.append({
                'Variabel': col,
                'N': n,
                'Mean': round(mean_v, 4),
                'Std Dev': round(std_v, 4),
                'Min': round(np.min(vals), 4),
                'Q1': round(np.percentile(vals, 25), 4),
                'Median': round(np.median(vals), 4),
                'Q3': round(np.percentile(vals, 75), 4),
                'Max': round(np.max(vals), 4),
                'Skewness': round(skew(vals), 4),
                'Kurtosis': round(kurt(vals, fisher=True), 4),
                'CV (%)': round(std_v / mean_v * 100, 2) if mean_v != 0 else None
            })

    df_stats = pd.DataFrame(rows)

    # --- TABLE ---
    tbl = dash_table.DataTable(
        columns=[{"name": c, "id": c} for c in df_stats.columns],
        data=df_stats.to_dict('records'),
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'center', 'fontSize': '13px', 'padding': '6px'},
        style_header={'backgroundColor': '#DBEAFE', 'fontWeight': 'bold', 'color': '#1E3A5F', 'textAlign': 'center'},
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F8FAFC'}],
        page_size=20
    )

    tbl_section = html.Div([
        diag_bar,
        html.H6(f"Tabel Statistika Deskriptif – Tahun {selected_year}",
                style={'textAlign': 'center', 'fontWeight': 'bold', 'color': '#1565C0', 'marginBottom': '10px'}),
        tbl
    ])

    # --- BOXPLOTS (one per column) ---
    figs = []
    for col in df.columns:
        fig = px.box(df, y=col, points='outliers', title=col,
                     color_discrete_sequence=[COLOR_ACCENT])
        fig.update_layout(
            template='plotly_white', height=300,
            title_x=0.5, margin=dict(l=20, r=20, t=40, b=20),
            showlegend=False
        )
        figs.append(html.Div(dcc.Graph(figure=fig), className='three columns'))

    boxplot_section = html.Div([
        html.H6("Distribusi Variabel (Boxplot)", style={'textAlign': 'center', 'fontWeight': 'bold',
                                                         'color': '#1565C0', 'marginBottom': '10px'}),
        html.Div(className='row', style={'display': 'flex', 'flexWrap': 'wrap'}, children=figs)
    ])

    # --- FORMULAS ---
    formula_section = html.Div([
        html.Hr(style={'borderColor': '#BBDEFB'}),
        html.H6("Rumus Statistika Deskriptif", style={'textAlign': 'center', 'fontWeight': 'bold',
                                                       'color': '#1565C0', 'marginBottom': '5px'}),
        render_descriptive_formulas()
    ])

    # --- CORRELATION MATRIX (mirip chart.Correlation() dari R) ---
    from scipy.stats import pearsonr

    def sig_stars(p):
        if p < 0.001: return '***'
        if p < 0.01:  return '**'
        if p < 0.05:  return '*'
        return 'ns'

    corr_cols = df.columns.tolist()
    n_vars = len(corr_cols)

    # 1. Heatmap korelasi bertanda signifikansi
    corr_vals  = np.zeros((n_vars, n_vars))
    pval_mat   = np.ones((n_vars, n_vars))
    annot_text = [[""] * n_vars for _ in range(n_vars)]

    for i, ci in enumerate(corr_cols):
        for j, cj in enumerate(corr_cols):
            xi = df[ci].dropna().values
            xj = df[cj].dropna().values
            common = np.isfinite(xi) & np.isfinite(xj)
            if i == j:
                corr_vals[i, j] = 1.0
                pval_mat[i, j]  = 0.0
                annot_text[i][j] = f"<b>{ci}</b>"
            elif np.sum(common) > 2:
                # Check variance to avoid division by zero in pearsonr
                if np.std(xi[common]) > 1e-9 and np.std(xj[common]) > 1e-9:
                    r, p = pearsonr(xi[common], xj[common])
                    corr_vals[i, j] = r
                    pval_mat[i, j]  = p
                    stars = sig_stars(p)
                    annot_text[i][j] = f"<b>{r:.3f}</b><br>{stars}"
                else:
                    annot_text[i][j] = "0.000<br>ns"
            else:
                annot_text[i][j] = "N/A"

    # Warna: merah = negatif, biru = positif
    corr_heatmap = go.Figure(go.Heatmap(
        z=corr_vals,
        x=corr_cols, y=corr_cols,
        colorscale='RdBu',
        zmid=0, zmin=-1, zmax=1,
        text=[[annot_text[i][j] for j in range(n_vars)] for i in range(n_vars)],
        texttemplate="%{text}",
        showscale=True,
        colorbar=dict(title='r', thickness=14)
    ))
    corr_heatmap.update_layout(
        title=f"Matriks Korelasi Pearson (Tahun {selected_year})",
        title_x=0.5,
        template='plotly_white',
        height=max(400, 60 * n_vars),
        margin=dict(l=20, r=20, t=60, b=20),
        xaxis=dict(side='bottom'),
        yaxis=dict(autorange='reversed')
    )

    # 2. Scatter Plot Matrix (SPLOM) — batas cukup 8 variabel agar tidak terlalu penuh
    splom_cols = corr_cols[:8] if n_vars > 8 else corr_cols
    splom_note = f" (hanya 8 pertama dari {n_vars})" if n_vars > 8 else ""

    # Bangun custom color per pair: bintang signifikansi di diagonal label
    splom_fig = go.Figure(go.Splom(
        dimensions=[dict(label=c, values=df[c]) for c in splom_cols],
        showupperhalf=True,
        diagonal_visible=True,
        marker=dict(
            size=4,
            color='#2563EB',
            opacity=0.55,
            line=dict(width=0)
        ),
        text=[f"<b>{ki}</b>" for ki in (df_year['Kabupaten/Kota'].values if 'Kabupaten/Kota' in df_year.columns else df.index)],
        hovertemplate="<b>%{text}</b><br>x=%{x:.3f}<br>y=%{y:.3f}<extra></extra>"
    ))
    splom_fig.update_traces(diagonal_visible=True)
    splom_fig.update_layout(
        title=f"Scatter Plot Matrix Variabel Deskriptif{splom_note} (Tahun {selected_year})",
        title_x=0.5,
        template='plotly_white',
        height=max(500, 120 * len(splom_cols)),
        margin=dict(l=20, r=20, t=60, b=20)
    )

    corr_section = html.Div([
        html.Hr(style={'borderColor': '#BBDEFB'}),
        html.H6("Matriks Korelasi & Scatter Plot Matrix",
                style={'textAlign': 'center', 'fontWeight': 'bold', 'color': '#1565C0', 'marginBottom': '10px'}),
        html.P(
            [
                "Heatmap menampilkan nilai korelasi Pearson (",
                html.I("r"), ") antar variabel beserta tanda signifikansi: ",
                html.B("*** p<0.001"), ", ",
                html.B("** p<0.01"), ", ",
                html.B("* p<0.05"), ", ",
                html.Span("ns = tidak signifikan", style={'color': '#888'}), "."
            ],
            style={'fontSize': '13px', 'color': '#555', 'textAlign': 'center', 'marginBottom': '10px'}
        ),
        dcc.Graph(figure=corr_heatmap, style={'marginBottom': '20px'}),
        dcc.Graph(figure=splom_fig)
    ])

    return tbl_section, boxplot_section, formula_section, corr_section, ""


# 8. Update Table Page Size
@app.callback(
    Output('statis-detail-table', 'page_size'),
    Input('table-page-size', 'value')
)
def update_page_size(size):
    return size if size else 10


# 7d. Multi-Year Descriptive Statistics
@app.callback(
    Output('desc-multi-table-output', 'children'),
    Output('desc-multi-trend-output', 'children'),
    Output('spinner-run-desc-multi', 'children'),
    Input('btn-run-desc-multi', 'n_clicks'),
    State('desc-multi-stat', 'value'),
    State('desc-multi-scale', 'value'),
    State('desc-weight-mode', 'value'),
    State('desc-weight-var-dropdown', 'value'),
    State('global-data-store', 'data')
)
def cb_run_desc_multi(n_clicks, stat_key, scale_mode, weight_mode, weight_var, data):
    if not n_clicks or not data:
        return "", "", ""

    from scipy.stats import skew, kurtosis as kurt

    try:
        df_all = pd.read_json(io.StringIO(data['df_json']), orient='split')
        drop_cols = ['Kabupaten/Kota', 'Provinsi']
        years = sorted(df_all['Tahun'].unique())

        # 1. Hitung Bobot m_i (jika mode weighted) Lintas Tahun
        m_weights = None
        if weight_mode == 'weighted' and weight_var and weight_var in df_all.columns:
            # m_i = \bar{V}_i / \sum \bar{V}_i
            df_weight = df_all.groupby('Kabupaten/Kota')[weight_var].mean()
            m_sum = df_weight.sum()
            if m_sum > 0:
                m_weights = (df_weight / m_sum).to_dict()

    except Exception as e:
        return html.P(f"Error: {e}", style={'color': 'red'}), "", ""

    STAT_LABELS = {
        'mean': 'Mean (Rata-rata)', 'std': 'Std Dev', 'median': 'Median',
        'q1': 'Q1 (Kuartil 1)', 'q3': 'Q3 (Kuartil 3)',
        'min': 'Min', 'max': 'Max',
        'skewness': 'Skewness', 'kurtosis': 'Kurtosis', 'cv': 'CV (%)'
    }

    # Build per-year stats
    year_dfs = {}
    for yr in years:
        try:
            mask = df_all['Tahun'] == int(yr)
        except Exception:
            mask = df_all['Tahun'].astype(str) == str(yr)
        
        df_yr_full = df_all[mask].copy()
        df_yr = df_yr_full.drop(columns=[c for c in drop_cols + ['Tahun'] if c in df_yr_full.columns], errors='ignore')
        df_yr = df_yr.select_dtypes(include='number')
        
        if df_yr.empty:
            continue

        if m_weights:
            # --- WEIGHTED MODE ---
            # Cari m_i yang sejajar dengan df_yr_full
            m_list = np.array([m_weights.get(kab, 0) for kab in df_yr_full['Kabupaten/Kota']])
            if m_list.sum() > 0:
                m_list = m_list / m_list.sum() # Normalisasi lokal thn t
            
            s_year = {}
            for col in df_yr.columns:
                vals = df_yr[col].values
                mu = np.sum(m_list * vals)
                diff = vals - mu
                
                if stat_key == 'mean':
                    val = mu
                elif stat_key == 'std':
                    val = np.sqrt(np.sum(m_list * (diff**2)))
                elif stat_key == 'skewness':
                    sigma = np.sqrt(np.sum(m_list * (diff**2)))
                    m3 = np.sum(m_list * (diff**3))
                    val = m3 / (sigma**3) if sigma > 0 else 0
                elif stat_key == 'kurtosis':
                    sigma = np.sqrt(np.sum(m_list * (diff**2)))
                    m4 = np.sum(m_list * (diff**4))
                    val = (m4 / (sigma**4)) - 3 if sigma > 0 else 0
                elif stat_key == 'cv':
                    sigma = np.sqrt(np.sum(m_list * (diff**2)))
                    val = (sigma / mu * 100) if mu != 0 else 0
                elif stat_key == 'median':
                    val = np.median(vals) # Median weighted is complex, we use raw median for simplicity or a weighted one? 
                    # Usually descriptive comparison for median stays unweighted unless specified
                elif stat_key == 'q1': val = np.percentile(vals, 25)
                elif stat_key == 'q3': val = np.percentile(vals, 75)
                elif stat_key == 'min': val = np.min(vals)
                elif stat_key == 'max': val = np.max(vals)
                else: val = 0
                
                s_year[col] = val
            year_dfs[yr] = pd.Series(s_year)
        else:
            # --- UNWEIGHTED MODE ---
            if stat_key == 'mean':
                year_dfs[yr] = df_yr.mean()
            elif stat_key == 'std':
                year_dfs[yr] = df_yr.std(ddof=0) # Sesuai populasi
            elif stat_key == 'median':
                year_dfs[yr] = df_yr.median()
            elif stat_key == 'q1':
                year_dfs[yr] = df_yr.quantile(0.25)
            elif stat_key == 'q3':
                year_dfs[yr] = df_yr.quantile(0.75)
            elif stat_key == 'min':
                year_dfs[yr] = df_yr.min()
            elif stat_key == 'max':
                year_dfs[yr] = df_yr.max()
            elif stat_key == 'skewness':
                year_dfs[yr] = df_yr.apply(lambda col: skew(col.dropna()))
            elif stat_key == 'kurtosis':
                year_dfs[yr] = df_yr.apply(lambda col: kurt(col.dropna(), fisher=True))
            elif stat_key == 'cv':
                m = df_yr.mean()
                s = df_yr.std(ddof=0)
                year_dfs[yr] = (s / m * 100).where(m != 0)

    if not year_dfs:
        return html.P("Tidak ada data yang dapat ditampilkan.", style={'color': 'red'}), "", ""

    df_pivot = pd.DataFrame(year_dfs).T
    df_pivot.index.name = 'Tahun'
    df_pivot = df_pivot.reset_index().round(4)

    # --- Pivot TABLE ---
    tbl = dash_table.DataTable(
        columns=[{"name": str(c), "id": str(c)} for c in df_pivot.columns],
        data=df_pivot.to_dict('records'),
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'center', 'fontSize': '12px', 'padding': '5px'},
        style_header={'backgroundColor': '#EDE7F6', 'fontWeight': 'bold', 'color': '#311B92', 'textAlign': 'center'},
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F3E5F5'}],
        export_format='xlsx'
    )

    tbl_section = html.Div([
        html.H6(f"{STAT_LABELS.get(stat_key, stat_key)} per Variabel — Semua Tahun",
                style={'textAlign': 'center', 'fontWeight': 'bold', 'color': '#4527A0', 'marginBottom': '8px'}),
        tbl
    ])

    # --- TREND LINE CHARTS ---
    vars_to_plot = [c for c in df_pivot.columns if c != 'Tahun']
    trend_figs = []
    for var in vars_to_plot:
        fig = px.line(df_pivot, x='Tahun', y=var, markers=True, title=var,
                      color_discrete_sequence=['#5C6BC0'])
        fig.update_traces(line=dict(width=2.5), marker=dict(size=8))
        yaxis_opts = dict(tickmode='auto')
        if scale_mode == 'zero':
            yaxis_opts['rangemode'] = 'tozero'
        fig.update_layout(
            template='plotly_white', height=260, title_x=0.5,
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis=dict(tickmode='array', tickvals=list(df_pivot['Tahun'])),
            yaxis=yaxis_opts,
            showlegend=False
        )
        trend_figs.append(
            html.Div(dcc.Graph(figure=fig, config={'displayModeBar': False}),
                     style={'width': '25%', 'display': 'inline-block', 'padding': '4px'})
        )

    trend_section = html.Div([
        html.H6(f"Tren {STAT_LABELS.get(stat_key, stat_key)} per Variabel",
                style={'textAlign': 'center', 'fontWeight': 'bold', 'color': '#4527A0',
                       'marginTop': '20px', 'marginBottom': '8px'}),
        html.Div(trend_figs, style={'display': 'flex', 'flexWrap': 'wrap'})
    ])

    return tbl_section, trend_section, ""


# 8. Update Table Page Size
@app.callback(
    Output('elbow-graph', 'figure'),
    Output('dendrogram-graph', 'figure'),
    Input('eval-year-dropdown', 'value'),
    State('statis-core-store', 'data')
)
def cb_eval_cluster(eval_year, res):
    if not eval_year or not res: return EMPTY_FIG, EMPTY_FIG
    if str(eval_year) not in res.get('per_year_coords', {}):
        return EMPTY_FIG, EMPTY_FIG
    coords = np.array(res['per_year_coords'][str(eval_year)])
    obs_labels = res['obs_labels']
    
    # 1. ELBOW + SILHOUETTE
    sse = []
    sil = []
    k_range = range(1, min(11, len(coords)))
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels_k = km.fit_predict(coords)
        sse.append(km.inertia_)
        if k >= 2:
            sil.append(round(float(silhouette_score(coords, labels_k)), 4))

    fig_elbow = go.Figure()
    fig_elbow.add_trace(go.Scatter(
        x=list(k_range), y=sse, mode='lines+markers', name='SSE',
        line=dict(color=COLOR_ACCENT, width=3), marker=dict(size=8)
    ))
    fig_elbow.add_trace(go.Scatter(
        x=list(range(2, min(11, len(coords)))), y=sil, mode='lines+markers', name='Siluet',
        line=dict(color='#E53935', width=2, dash='dot'), marker=dict(size=7),
        yaxis='y2'
    ))
    fig_elbow.update_layout(
        title=f"Metode Elbow & Siluet (Tahun {eval_year})",
        xaxis_title="Jumlah Klaster (k)",
        yaxis_title="Sum of Squared Errors (SSE)",
        yaxis2=dict(title='Koefisien Siluet', overlaying='y', side='right', range=[0, 1]),
        template='plotly_white',
        legend=dict(x=0.75, y=0.95)
    )
    import os
    os.makedirs("../output_app", exist_ok=True)
    try: fig_elbow.write_image(f"../output_app/elbow_plot_{eval_year}.png")
    except: pass

    # 2. DENDROGRAM
    try:
        import plotly.figure_factory as ff
        from scipy.cluster.hierarchy import linkage
        Z = linkage(coords, method='ward')
        fig_dendro = ff.create_dendrogram(coords, labels=obs_labels, orientation='left', linkagefun=lambda x: Z, colorscale=px.colors.qualitative.Bold)
        fig_dendro.update_layout(title=f"Dendrogram Hierarchical (Tahun {eval_year})", template='plotly_white', margin=dict(l=150))
        try: fig_dendro.write_image(f"../output_app/dendrogram_{eval_year}.png")
        except: pass
    except Exception as e:
        fig_dendro = go.Figure().add_annotation(text=f"Error Dendrogram: {e}", showarrow=False)

    return fig_elbow, fig_dendro


# 10A. CALCULATION: CLUSTERING TAHUNAN & MATRIKS TRANSISI
@app.callback(
    Output('statis-trans-store', 'data'),
    Output('spinner-run-trans', 'children'),
    Input('btn-run-trans', 'n_clicks'),
    State('trans-year-dropdown', 'value'),
    State('trans-k-input', 'value'),
    State('pca-results-store', 'data'),
    State('global-data-store', 'data')
)
def cb_calc_trans(n_clicks, t2_year, k, pca_res, global_data):
    if not n_clicks or not t2_year or not pca_res or not global_data: raise exceptions.PreventUpdate

    years = sorted(list(global_data['years']))
    try:
        t2_idx = years.index(int(t2_year))
        if t2_idx == 0: raise exceptions.PreventUpdate
        t1_year = years[t2_idx - 1]
    except (ValueError, IndexError):
        raise exceptions.PreventUpdate
        
    import pandas as pd
    df_scores = pd.read_json(io.StringIO(pca_res['pc_scores']), orient='split')
    df_t1 = df_scores[df_scores['Tahun'] == int(t1_year)]
    df_t2 = df_scores[df_scores['Tahun'] == int(t2_year)]
    
    if df_t1.empty or df_t2.empty: raise exceptions.PreventUpdate

    coords_t1 = df_t1[['PC1', 'PC2']].to_numpy()
    coords_t2 = df_t2[['PC1', 'PC2']].to_numpy()
    obs_labels = df_t1['Kabupaten/Kota'].tolist()
    
    from scipy.optimize import linear_sum_assignment
    from scipy.spatial.distance import cdist
    
    # Base centroids for alignment
    km_base = KMeans(n_clusters=k, random_state=42, n_init=10)
    km_base.fit(coords_t1)
    base_centroids = km_base.cluster_centers_
    
    def get_aligned_labels(coords):
        km_curr = KMeans(n_clusters=k, random_state=42, n_init=10)
        lbls = km_curr.fit_predict(coords)
        curr_centroids = km_curr.cluster_centers_
        dist_matrix = cdist(base_centroids, curr_centroids, metric='euclidean')
        row_ind, col_ind = linear_sum_assignment(dist_matrix)
        mapping = {col_ind[i]: row_ind[i] for i in range(len(col_ind))}
        new_labels = [mapping[l] for l in lbls]
        
        cluster_means = []
        unique_lbls = sorted(list(set(new_labels)))
        for cl in unique_lbls:
            cluster_means.append(np.mean(coords[[i for i, l in enumerate(new_labels) if l == cl], 0]))
        
        sorted_indices = np.argsort(cluster_means)
        rank_map = {old: new for new, old in enumerate(sorted_indices)}
        name_map = {0: "Klaster 1 (Rendah)", 1: "Klaster 2 (Sedang)", 2: "Klaster 3 (Tinggi)"}
        return [name_map.get(rank_map[l], f"Level {rank_map[l]+1}") for l in new_labels]
        
    str_labels_t1 = get_aligned_labels(coords_t1)
    str_labels_t2 = get_aligned_labels(coords_t2)
    
    return {
        't1_year': str(t1_year),
        't2_year': str(t2_year),
        'str_labels_t1': str_labels_t1,
        'str_labels_t2': str_labels_t2,
        'obs_labels': obs_labels,
        'coords_t1': coords_t1.tolist(),
        'coords_t2': coords_t2.tolist(),
        'k': k
    }, ""


# 10A-2. CALCULATION: CLUSTERING TAHUNAN TERBOBOT & MATRIKS TRANSISI
@app.callback(
    Output('weighted-trans-store', 'data'),
    Output('spinner-run-weighted-trans', 'children'),
    Input('btn-run-weighted-trans', 'n_clicks'),
    State('weighted-trans-year-dropdown', 'value'),
    State('weighted-trans-k-input', 'value'),
    State('statis-core-store', 'data')
)
def cb_calc_weighted_trans(n_clicks, t2_year, k, res):
    if not n_clicks or not t2_year or not res: raise exceptions.PreventUpdate

    years = sorted(list(res['per_year_coords'].keys()))
    try:
        t2_idx = years.index(str(t2_year))
        if t2_idx == 0: raise exceptions.PreventUpdate
        t1_year = years[t2_idx - 1]
    except (ValueError, IndexError):
        raise exceptions.PreventUpdate
    
    coords_t1 = np.array(res['per_year_coords'][t1_year])
    coords_t2 = np.array(res['per_year_coords'][str(t2_year)])
    obs_labels = res['obs_labels']
    
    from scipy.optimize import linear_sum_assignment
    from scipy.spatial.distance import cdist
    
    # Base centroids for alignment
    km_base = KMeans(n_clusters=k, random_state=42, n_init=10)
    km_base.fit(coords_t1)
    base_centroids = km_base.cluster_centers_
    
    def get_aligned_labels(coords):
        km_curr = KMeans(n_clusters=k, random_state=42, n_init=10)
        lbls = km_curr.fit_predict(coords)
        curr_centroids = km_curr.cluster_centers_
        dist_matrix = cdist(base_centroids, curr_centroids, metric='euclidean')
        row_ind, col_ind = linear_sum_assignment(dist_matrix)
        mapping = {col_ind[i]: row_ind[i] for i in range(len(col_ind))}
        new_labels = [mapping[l] for l in lbls]
        
        cluster_means = []
        unique_lbls = sorted(list(set(new_labels)))
        for cl in unique_lbls:
            cluster_means.append(np.mean(coords[[i for i, l in enumerate(new_labels) if l == cl], 0]))
        
        sorted_indices = np.argsort(cluster_means)
        rank_map = {old: new for new, old in enumerate(sorted_indices)}
        name_map = {0: "Klaster 1 (Rendah)", 1: "Klaster 2 (Sedang)", 2: "Klaster 3 (Tinggi)"}
        return [name_map.get(rank_map[l], f"Level {rank_map[l]+1}") for l in new_labels]
        
    str_labels_t1 = get_aligned_labels(coords_t1)
    str_labels_t2 = get_aligned_labels(coords_t2)
    
    return {
        't1_year': str(t1_year),
        't2_year': str(t2_year),
        'str_labels_t1': str_labels_t1,
        'str_labels_t2': str_labels_t2,
        'obs_labels': obs_labels,
        'coords_t1': coords_t1.tolist(),
        'coords_t2': coords_t2.tolist(),
        'k': k
    }, ""

# 10A-3. CALCULATION: PERBANDINGAN BIPLOT VS STATIS TAHUN TERTENTU
@app.callback(
    Output('biplot-statis-compare-store', 'data'),
    Output('spinner-run-biplot-statis-compare', 'children'),
    Input('btn-run-biplot-statis-compare', 'n_clicks'),
    State('biplot-statis-compare-year', 'value'),
    State('biplot-statis-compare-k', 'value'),
    State('pca-results-store', 'data'),
    State('statis-core-store', 'data')
)
def cb_calc_biplot_statis_compare(n_clicks, year, k, pca_res, statis_res):
    if not n_clicks or not year or not pca_res or not statis_res: raise exceptions.PreventUpdate

    import pandas as pd

    # Biplot Coordinates
    df_scores = pd.read_json(io.StringIO(pca_res['pc_scores']), orient='split')
    df_year = df_scores[df_scores['Tahun'] == int(year)]
    if df_year.empty: raise exceptions.PreventUpdate
    coords_biplot = df_year[['PC1', 'PC2']].to_numpy()

    # STATIS Coordinates
    try:
        coords_statis = np.array(statis_res['per_year_coords'][str(year)])
    except KeyError:
        raise exceptions.PreventUpdate
        
    obs_labels = df_year['Kabupaten/Kota'].tolist()
    
    from scipy.optimize import linear_sum_assignment
    from scipy.spatial.distance import cdist
    
    # Base centroids for alignment (use biplot as base)
    km_base = KMeans(n_clusters=k, random_state=42, n_init=10)
    km_base.fit(coords_biplot)
    base_centroids = km_base.cluster_centers_
    
    def get_aligned_labels(coords):
        km_curr = KMeans(n_clusters=k, random_state=42, n_init=10)
        lbls = km_curr.fit_predict(coords)
        curr_centroids = km_curr.cluster_centers_
        dist_matrix = cdist(base_centroids, curr_centroids, metric='euclidean')
        row_ind, col_ind = linear_sum_assignment(dist_matrix)
        mapping = {col_ind[i]: row_ind[i] for i in range(len(col_ind))}
        new_labels = [mapping[l] for l in lbls]
        
        cluster_means = []
        unique_lbls = sorted(list(set(new_labels)))
        for cl in unique_lbls:
            cluster_means.append(np.mean(coords[[i for i, l in enumerate(new_labels) if l == cl], 0]))
        
        sorted_indices = np.argsort(cluster_means)
        rank_map = {old: new for new, old in enumerate(sorted_indices)}
        name_map = {0: "Klaster 1 (Rendah)", 1: "Klaster 2 (Sedang)", 2: "Klaster 3 (Tinggi)"}
        return [name_map.get(rank_map[l], f"Level {rank_map[l]+1}") for l in new_labels]
        
    str_labels_biplot = get_aligned_labels(coords_biplot)
    str_labels_statis = get_aligned_labels(coords_statis)
    
    return {
        't1_year': "Biplot",
        't2_year': "STATIS",
        'actual_year': str(year),
        'str_labels_t1': str_labels_biplot,
        'str_labels_t2': str_labels_statis,
        'obs_labels': obs_labels,
        'coords_t1': coords_biplot.tolist(),
        'coords_t2': coords_statis.tolist(),
        'k': k
    }, ""

# 10B. RENDERING: PLOTS (FIGS)
@app.callback(
    Output('title-trans-map-t1', 'children'),
    Output('trans-map-t1', 'figure'),
    Output('title-trans-map-t2', 'children'),
    Output('trans-map-t2', 'figure'),
    Output('title-trans-scatter-t1', 'children'),
    Output('trans-scatter-t1', 'figure'),
    Output('title-trans-scatter-t2', 'children'),
    Output('trans-scatter-t2', 'figure'),
    Output('title-trans-pie-t1', 'children'),
    Output('trans-pie-t1', 'figure'),
    Output('title-trans-pie-t2', 'children'),
    Output('trans-pie-t2', 'figure'),
    Output('trans-results-container', 'style'),
    Input('statis-trans-store', 'data')
)
def cb_render_trans_plots(data):
    if not data: return "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, {'display': 'none'}
    
    t1_year, t2_year = data['t1_year'], data['t2_year']
    str_labels_t1, str_labels_t2 = data['str_labels_t1'], data['str_labels_t2']
    obs_labels = data['obs_labels']
    coords_t1, coords_t2 = np.array(data['coords_t1']), np.array(data['coords_t2'])

    # Figures logic (Scatter & Map)
    fig_scatter_t1 = px.scatter(x=coords_t1[:,0], y=coords_t1[:,1], color=str_labels_t1, text=obs_labels, color_discrete_map=CLUSTER_COLOR_MAP, category_orders={"color": LEVEL_ORDER})
    fig_scatter_t1.update_traces(marker=dict(size=9), textposition='top center')
    fig_scatter_t1.update_layout(template='plotly_white', xaxis_title="PC1", yaxis_title="PC2")
    
    fig_scatter_t2 = px.scatter(x=coords_t2[:,0], y=coords_t2[:,1], color=str_labels_t2, text=obs_labels, color_discrete_map=CLUSTER_COLOR_MAP, category_orders={"color": LEVEL_ORDER})
    fig_scatter_t2.update_traces(marker=dict(size=9), textposition='top center')
    fig_scatter_t2.update_layout(template='plotly_white', xaxis_title="PC1", yaxis_title="PC2")
    
    fig_map_t1, fig_map_t2 = go.Figure(), go.Figure()
    if indonesia_geojson:
        mapbox_center, mapbox_zoom = {"lat": -6.9, "lon": 107}, 6.5
        df_map_t1 = pd.DataFrame({'Kab/Kota': obs_labels, 'Cluster': str_labels_t1, 'match_key': obs_labels})
        df_map_t2 = pd.DataFrame({'Kab/Kota': obs_labels, 'Cluster': str_labels_t2, 'match_key': obs_labels})
        
        fig_map_t1 = px.choropleth_mapbox(df_map_t1, geojson=indonesia_geojson, locations='match_key', featureidkey='properties.id_cocok', color='Cluster', color_discrete_map=CLUSTER_COLOR_MAP, category_orders={"Cluster": LEVEL_ORDER}, hover_name='Kab/Kota', mapbox_style="carto-positron", center=mapbox_center, zoom=mapbox_zoom, opacity=0.7)
        fig_map_t1.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        
        fig_map_t2 = px.choropleth_mapbox(df_map_t2, geojson=indonesia_geojson, locations='match_key', featureidkey='properties.id_cocok', color='Cluster', color_discrete_map=CLUSTER_COLOR_MAP, category_orders={"Cluster": LEVEL_ORDER}, hover_name='Kab/Kota', mapbox_style="carto-positron", center=mapbox_center, zoom=mapbox_zoom, opacity=0.7)
        fig_map_t2.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        
        for f, df in [(fig_map_t1, df_map_t1), (fig_map_t2, df_map_t2)]:
            lon_list, lat_list, text_list = [], [], []
            for _, row in df.iterrows():
                area = row['Kab/Kota']
                geom = gdf[gdf['id_cocok'] == area]
                if not geom.empty:
                    lon_list.append(geom.geometry.centroid.x.values[0])
                    lat_list.append(geom.geometry.centroid.y.values[0])
                    text_list.append(area)
            if text_list:
                f.add_trace(go.Scattermapbox(lon=lon_list, lat=lat_list, mode='text', text=text_list, textfont=dict(size=9, color='black'), showlegend=False))

    from collections import Counter
    counts_t1 = Counter(str_labels_t1)
    fig_pie_t1 = px.pie(
        names=list(counts_t1.keys()),
        values=list(counts_t1.values()),
        color=list(counts_t1.keys()),
        color_discrete_map=CLUSTER_COLOR_MAP,
        category_orders={"names": LEVEL_ORDER}
    )
    fig_pie_t1.update_layout(template='plotly_white')
    
    counts_t2 = Counter(str_labels_t2)
    fig_pie_t2 = px.pie(
        names=list(counts_t2.keys()),
        values=list(counts_t2.values()),
        color=list(counts_t2.keys()),
        color_discrete_map=CLUSTER_COLOR_MAP,
        category_orders={"names": LEVEL_ORDER}
    )
    fig_pie_t2.update_layout(template='plotly_white')

    return (
        f"Peta Sebaran Klaster ({t1_year})", fig_map_t1,
        f"Peta Sebaran Klaster ({t2_year})", fig_map_t2,
        f"Biplot Klaster ({t1_year})", fig_scatter_t1,
        f"Biplot Klaster ({t2_year})", fig_scatter_t2,
        f"Proporsi Klaster ({t1_year})", fig_pie_t1,
        f"Proporsi Klaster ({t2_year})", fig_pie_t2,
        {'display': 'block'}
    )

# 10C. RENDERING: TABLE (INSTANT)
@app.callback(
    Output('trans-matrix-table', 'data'),
    Output('trans-matrix-table', 'columns'),
    Input('statis-trans-store', 'data'),
    Input('trans-view-mode', 'value')
)
def cb_render_trans_table(data, view_mode):
    if not data: return [], []
    t1_year, t2_year, str_labels_t1, str_labels_t2, obs_labels, k = data['t1_year'], data['t2_year'], data['str_labels_t1'], data['str_labels_t2'], data['obs_labels'], data['k']
    unique_l1, unique_l2 = sorted(list(set(str_labels_t1))), sorted(list(set(str_labels_t2)))
    matrix_data = []
    for c1 in unique_l1:
        row_dict = {f"Tahun {t1_year} \\ {t2_year}": c1} # Gunakan \\ untuk escape backslash di f-string
        for c2 in unique_l2:
            intersect_indices = [idx for idx, (l1, l2) in enumerate(zip(str_labels_t1, str_labels_t2)) if l1 == c1 and l2 == c2]
            row_dict[c2] = str(len(intersect_indices)) if view_mode == 'count' else (", ".join([obs_labels[idx] for idx in intersect_indices]) if intersect_indices else "-")
        matrix_data.append(row_dict)
    cols = [{"name": str(c), "id": str(c)} for c in matrix_data[0].keys()] if matrix_data else []
    return matrix_data, cols


# 10B-2. RENDERING TERBOBOT: PLOTS (FIGS)
@app.callback(
    Output('title-weighted-trans-map-t1', 'children'),
    Output('weighted-trans-map-t1', 'figure'),
    Output('title-weighted-trans-map-t2', 'children'),
    Output('weighted-trans-map-t2', 'figure'),
    Output('title-weighted-trans-scatter-t1', 'children'),
    Output('weighted-trans-scatter-t1', 'figure'),
    Output('title-weighted-trans-scatter-t2', 'children'),
    Output('weighted-trans-scatter-t2', 'figure'),
    Output('title-weighted-trans-pie-t1', 'children'),
    Output('weighted-trans-pie-t1', 'figure'),
    Output('title-weighted-trans-pie-t2', 'children'),
    Output('weighted-trans-pie-t2', 'figure'),
    Output('weighted-trans-results-container', 'style'),
    Input('weighted-trans-store', 'data')
)
def cb_render_weighted_trans_plots(data):
    if not data: return "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, {'display': 'none'}
    
    t1_year, t2_year = data['t1_year'], data['t2_year']
    str_labels_t1, str_labels_t2 = data['str_labels_t1'], data['str_labels_t2']
    obs_labels = data['obs_labels']
    coords_t1, coords_t2 = np.array(data['coords_t1']), np.array(data['coords_t2'])

    # Figures logic (Scatter & Map)
    fig_scatter_t1 = px.scatter(x=coords_t1[:,0], y=coords_t1[:,1], color=str_labels_t1, text=obs_labels, color_discrete_map=CLUSTER_COLOR_MAP, category_orders={"color": LEVEL_ORDER})
    fig_scatter_t1.update_traces(marker=dict(size=9), textposition='top center')
    fig_scatter_t1.update_layout(template='plotly_white', xaxis_title="PC1", yaxis_title="PC2")
    
    fig_scatter_t2 = px.scatter(x=coords_t2[:,0], y=coords_t2[:,1], color=str_labels_t2, text=obs_labels, color_discrete_map=CLUSTER_COLOR_MAP, category_orders={"color": LEVEL_ORDER})
    fig_scatter_t2.update_traces(marker=dict(size=9), textposition='top center')
    fig_scatter_t2.update_layout(template='plotly_white', xaxis_title="PC1", yaxis_title="PC2")
    
    fig_map_t1, fig_map_t2 = go.Figure(), go.Figure()
    if indonesia_geojson:
        mapbox_center, mapbox_zoom = {"lat": -6.9, "lon": 107}, 6.5
        df_map_t1 = pd.DataFrame({'Kab/Kota': obs_labels, 'Cluster': str_labels_t1, 'match_key': obs_labels})
        df_map_t2 = pd.DataFrame({'Kab/Kota': obs_labels, 'Cluster': str_labels_t2, 'match_key': obs_labels})
        
        fig_map_t1 = px.choropleth_mapbox(df_map_t1, geojson=indonesia_geojson, locations='match_key', featureidkey='properties.id_cocok', color='Cluster', color_discrete_map=CLUSTER_COLOR_MAP, category_orders={"Cluster": LEVEL_ORDER}, hover_name='Kab/Kota', mapbox_style="carto-positron", center=mapbox_center, zoom=mapbox_zoom, opacity=0.7)
        fig_map_t1.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        
        fig_map_t2 = px.choropleth_mapbox(df_map_t2, geojson=indonesia_geojson, locations='match_key', featureidkey='properties.id_cocok', color='Cluster', color_discrete_map=CLUSTER_COLOR_MAP, category_orders={"Cluster": LEVEL_ORDER}, hover_name='Kab/Kota', mapbox_style="carto-positron", center=mapbox_center, zoom=mapbox_zoom, opacity=0.7)
        fig_map_t2.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        
        for f, df in [(fig_map_t1, df_map_t1), (fig_map_t2, df_map_t2)]:
            lon_list, lat_list, text_list = [], [], []
            for _, row in df.iterrows():
                area = row['Kab/Kota']
                geom = gdf[gdf['id_cocok'] == area]
                if not geom.empty:
                    lon_list.append(geom.geometry.centroid.x.values[0])
                    lat_list.append(geom.geometry.centroid.y.values[0])
                    text_list.append(area)
            if text_list:
                f.add_trace(go.Scattermapbox(lon=lon_list, lat=lat_list, mode='text', text=text_list, textfont=dict(size=9, color='black'), showlegend=False))

    from collections import Counter
    counts_t1 = Counter(str_labels_t1)
    fig_pie_t1 = px.pie(
        names=list(counts_t1.keys()),
        values=list(counts_t1.values()),
        color=list(counts_t1.keys()),
        color_discrete_map=CLUSTER_COLOR_MAP,
        category_orders={"names": LEVEL_ORDER}
    )
    fig_pie_t1.update_layout(template='plotly_white')
    
    counts_t2 = Counter(str_labels_t2)
    fig_pie_t2 = px.pie(
        names=list(counts_t2.keys()),
        values=list(counts_t2.values()),
        color=list(counts_t2.keys()),
        color_discrete_map=CLUSTER_COLOR_MAP,
        category_orders={"names": LEVEL_ORDER}
    )
    fig_pie_t2.update_layout(template='plotly_white')

    return (
        f"Peta Sebaran Klaster Terbobot ({t1_year})", fig_map_t1,
        f"Peta Sebaran Klaster Terbobot ({t2_year})", fig_map_t2,
        f"Biplot Klaster Terbobot ({t1_year})", fig_scatter_t1,
        f"Biplot Klaster Terbobot ({t2_year})", fig_scatter_t2,
        f"Proporsi Klaster Terbobot ({t1_year})", fig_pie_t1,
        f"Proporsi Klaster Terbobot ({t2_year})", fig_pie_t2,
        {'display': 'block'}
    )


# 10C-2. RENDERING TERBOBOT: TABLE (INSTANT)
@app.callback(
    Output('weighted-trans-matrix-table', 'data'),
    Output('weighted-trans-matrix-table', 'columns'),
    Input('weighted-trans-store', 'data'),
    Input('weighted-trans-view-mode', 'value')
)
def cb_render_weighted_trans_table(data, view_mode):
    if not data: return [], []
    t1_year, t2_year, str_labels_t1, str_labels_t2, obs_labels, k = data['t1_year'], data['t2_year'], data['str_labels_t1'], data['str_labels_t2'], data['obs_labels'], data['k']
    unique_l1, unique_l2 = sorted(list(set(str_labels_t1))), sorted(list(set(str_labels_t2)))
    matrix_data = []
    for c1 in unique_l1:
        row_dict = {f"Tahun {t1_year} \\ {t2_year}": c1} # Gunakan \\ untuk escape backslash di f-string
        for c2 in unique_l2:
            intersect_indices = [idx for idx, (l1, l2) in enumerate(zip(str_labels_t1, str_labels_t2)) if l1 == c1 and l2 == c2]
            row_dict[c2] = str(len(intersect_indices)) if view_mode == 'count' else (", ".join([obs_labels[idx] for idx in intersect_indices]) if intersect_indices else "-")
        matrix_data.append(row_dict)
    cols = [{"name": str(c), "id": str(c)} for c in matrix_data[0].keys()] if matrix_data else []
    return matrix_data, cols

# 10C-3. RENDERING PERBANDINGAN: PLOTS (FIGS)
@app.callback(
    Output('title-biplot-statis-compare-map-biplot', 'children'),
    Output('biplot-statis-compare-map-biplot', 'figure'),
    Output('title-biplot-statis-compare-map-statis', 'children'),
    Output('biplot-statis-compare-map-statis', 'figure'),
    Output('title-biplot-statis-compare-scatter-biplot', 'children'),
    Output('biplot-statis-compare-scatter-biplot', 'figure'),
    Output('title-biplot-statis-compare-scatter-statis', 'children'),
    Output('biplot-statis-compare-scatter-statis', 'figure'),
    Output('title-biplot-statis-compare-pie-biplot', 'children'),
    Output('biplot-statis-compare-pie-biplot', 'figure'),
    Output('title-biplot-statis-compare-pie-statis', 'children'),
    Output('biplot-statis-compare-pie-statis', 'figure'),
    Output('biplot-statis-compare-results-container', 'style'),
    Input('biplot-statis-compare-store', 'data')
)
def cb_render_biplot_statis_compare_plots(data):
    if not data: return "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, {'display': 'none'}
    
    t1_year, t2_year = data['t1_year'], data['t2_year']
    actual_year = data['actual_year']
    str_labels_t1, str_labels_t2 = data['str_labels_t1'], data['str_labels_t2']
    obs_labels = data['obs_labels']
    coords_t1, coords_t2 = np.array(data['coords_t1']), np.array(data['coords_t2'])

    # Figures logic (Scatter & Map)
    fig_scatter_t1 = px.scatter(x=coords_t1[:,0], y=coords_t1[:,1], color=str_labels_t1, text=obs_labels, color_discrete_map=CLUSTER_COLOR_MAP, category_orders={"color": LEVEL_ORDER})
    fig_scatter_t1.update_traces(marker=dict(size=9), textposition='top center')
    fig_scatter_t1.update_layout(template='plotly_white', xaxis_title="PC1", yaxis_title="PC2")
    
    fig_scatter_t2 = px.scatter(x=coords_t2[:,0], y=coords_t2[:,1], color=str_labels_t2, text=obs_labels, color_discrete_map=CLUSTER_COLOR_MAP, category_orders={"color": LEVEL_ORDER})
    fig_scatter_t2.update_traces(marker=dict(size=9), textposition='top center')
    fig_scatter_t2.update_layout(template='plotly_white', xaxis_title="PC1", yaxis_title="PC2")
    
    fig_map_t1, fig_map_t2 = go.Figure(), go.Figure()
    if indonesia_geojson:
        mapbox_center, mapbox_zoom = {"lat": -6.9, "lon": 107}, 6.5
        df_map_t1 = pd.DataFrame({'Kab/Kota': obs_labels, 'Cluster': str_labels_t1, 'match_key': obs_labels})
        df_map_t2 = pd.DataFrame({'Kab/Kota': obs_labels, 'Cluster': str_labels_t2, 'match_key': obs_labels})
        
        fig_map_t1 = px.choropleth_mapbox(df_map_t1, geojson=indonesia_geojson, locations='match_key', featureidkey='properties.id_cocok', color='Cluster', color_discrete_map=CLUSTER_COLOR_MAP, category_orders={"Cluster": LEVEL_ORDER}, hover_name='Kab/Kota', mapbox_style="carto-positron", center=mapbox_center, zoom=mapbox_zoom, opacity=0.7)
        fig_map_t1.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        
        fig_map_t2 = px.choropleth_mapbox(df_map_t2, geojson=indonesia_geojson, locations='match_key', featureidkey='properties.id_cocok', color='Cluster', color_discrete_map=CLUSTER_COLOR_MAP, category_orders={"Cluster": LEVEL_ORDER}, hover_name='Kab/Kota', mapbox_style="carto-positron", center=mapbox_center, zoom=mapbox_zoom, opacity=0.7)
        fig_map_t2.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        
        for f, df in [(fig_map_t1, df_map_t1), (fig_map_t2, df_map_t2)]:
            lon_list, lat_list, text_list = [], [], []
            for _, row in df.iterrows():
                area = row['Kab/Kota']
                geom = gdf[gdf['id_cocok'] == area]
                if not geom.empty:
                    lon_list.append(geom.geometry.centroid.x.values[0])
                    lat_list.append(geom.geometry.centroid.y.values[0])
                    text_list.append(area)
            if text_list:
                f.add_trace(go.Scattermapbox(lon=lon_list, lat=lat_list, mode='text', text=text_list, textfont=dict(size=9, color='black'), showlegend=False))

    from collections import Counter
    counts_t1 = Counter(str_labels_t1)
    fig_pie_t1 = px.pie(
        names=list(counts_t1.keys()),
        values=list(counts_t1.values()),
        color=list(counts_t1.keys()),
        color_discrete_map=CLUSTER_COLOR_MAP,
        category_orders={"names": LEVEL_ORDER}
    )
    fig_pie_t1.update_layout(template='plotly_white')
    
    counts_t2 = Counter(str_labels_t2)
    fig_pie_t2 = px.pie(
        names=list(counts_t2.keys()),
        values=list(counts_t2.values()),
        color=list(counts_t2.keys()),
        color_discrete_map=CLUSTER_COLOR_MAP,
        category_orders={"names": LEVEL_ORDER}
    )
    fig_pie_t2.update_layout(template='plotly_white')

    return (
        f"Peta Sebaran Klaster {t1_year} ({actual_year})", fig_map_t1,
        f"Peta Sebaran Klaster {t2_year} ({actual_year})", fig_map_t2,
        f"Klaster {t1_year} ({actual_year})", fig_scatter_t1,
        f"Klaster {t2_year} ({actual_year})", fig_scatter_t2,
        f"Proporsi Klaster {t1_year} ({actual_year})", fig_pie_t1,
        f"Proporsi Klaster {t2_year} ({actual_year})", fig_pie_t2,
        {'display': 'block'}
    )

# 10C-4. RENDERING PERBANDINGAN: TABLE (INSTANT)
@app.callback(
    Output('biplot-statis-compare-matrix-table', 'data'),
    Output('biplot-statis-compare-matrix-table', 'columns'),
    Input('biplot-statis-compare-store', 'data'),
    Input('biplot-statis-compare-view-mode', 'value')
)
def cb_render_biplot_statis_compare_table(data, view_mode):
    if not data: return [], []
    t1_year, t2_year = data['t1_year'], data['t2_year']
    actual_year = data['actual_year']
    str_labels_t1, str_labels_t2 = data['str_labels_t1'], data['str_labels_t2']
    obs_labels, k = data['obs_labels'], data['k']
    unique_l1, unique_l2 = sorted(list(set(str_labels_t1))), sorted(list(set(str_labels_t2)))
    matrix_data = []
    for c1 in unique_l1:
        row_dict = {f"Tahun {actual_year} ({t1_year} \\ {t2_year})": c1}
        for c2 in unique_l2:
            intersect_indices = [idx for idx, (l1, l2) in enumerate(zip(str_labels_t1, str_labels_t2)) if l1 == c1 and l2 == c2]
            row_dict[c2] = str(len(intersect_indices)) if view_mode == 'count' else (", ".join([obs_labels[idx] for idx in intersect_indices]) if intersect_indices else "-")
        matrix_data.append(row_dict)
    cols = [{"name": str(c), "id": str(c)} for c in matrix_data[0].keys()] if matrix_data else []
    return matrix_data, cols


# 11. CLUSTERING TRAJEKTORI CALLBACK (STATIS FULL)
@app.callback(
    Output('cluster-scatter', 'figure'),
    Output('cluster-pie', 'figure'),
    Output('cluster-map', 'figure'),
    Output('cluster-interpretation', 'children'),
    Output('formula-cluster-output', 'children'),
    Output('cluster-member-table', 'data'),
    Output('cluster-member-table', 'columns'),
    Output('cluster-results-container', 'style'),
    Output('spinner-run-cluster', 'children'),
    Input('btn-run-cluster', 'n_clicks'),
    State('cluster-k-input', 'value'),
    State('statis-core-store', 'data')
)
def cb_run_clustering_trajectory(n_clicks, k_clusters, res):
    if not n_clicks or not res:
        return EMPTY_FIG, EMPTY_FIG, EMPTY_FIG, "", html.Div(), [], [], {'display': 'none'}, ""
    
    obs_labels = res['obs_labels']
    coords_dict = res['per_year_coords']
    sheet_names = res.get('sheet_names', sorted(list(coords_dict.keys())))
    alphas = res.get('alphas', [1.0] * len(sheet_names))
    
    # --- 1. Clustering Logic (Weighted Trajectory per Lavit 1994) ---
    features = []
    for i in range(len(obs_labels)):
        city_feats = []
        for j, yr in enumerate(sheet_names):
            # Apply interstructure weights: dist^2 = sum( alpha_k * ||x_ik - x_jk||^2 )
            # To handle this with standard KMeans, we multiply coordinates by sqrt(alpha)
            w = np.sqrt(alphas[j])
            coords = np.array(coords_dict[str(yr)])
            city_feats.extend(coords[i, :] * w) 
        features.append(city_feats)
    
    X_traj = np.array(features)
    kmeans = KMeans(n_clusters=k_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_traj)
    
    # --- [KEBARUAN] RANKING CLUSTER TRAJEKTORI BERDASARKAN PC1 KOMPROMI ---
    # Mirror sudah diterapkan di statis-core-store oleh cb_statis_calc, jadi ranking langsung.
    scores_comp = np.array(res['scores'])
    unique_lbls = sorted(list(set(labels)))

    cluster_pc1_means = [
        np.mean(scores_comp[[i for i, l in enumerate(labels) if l == cl], 0])
        for cl in unique_lbls
    ]
    sorted_indices = np.argsort(cluster_pc1_means)
    rank_map = {old: new for new, old in enumerate(sorted_indices)}
    name_map = {0: "Klaster 1 (Rendah)", 1: "Klaster 2 (Sedang)", 2: "Klaster 3 (Tinggi)"}
    str_labels = [name_map.get(rank_map[l], f"Level {rank_map[l]+1}") for l in labels]

    # --- 2. Scatter Plot ---
    fig_scatter = px.scatter(
        x=scores_comp[:, 0], y=scores_comp[:, 1], color=str_labels,
        text=obs_labels, title="Klaster pada Ruang Kompromi",
        color_discrete_map=CLUSTER_COLOR_MAP,
        category_orders={"color": LEVEL_ORDER}
    )
    fig_scatter.update_traces(marker=dict(size=8), textfont=dict(size=8), textposition='top center')
    fig_scatter.update_layout(template='plotly_white')

    # --- 3. Pie Chart ---
    try:
        df_pie = pd.DataFrame({'Cluster': str_labels})
        fig_pie = px.pie(
            df_pie,
            names='Cluster',
            title="Proporsi Klaster Trajektori",
            color='Cluster',
            color_discrete_map=CLUSTER_COLOR_MAP,
            category_orders={"Cluster": LEVEL_ORDER}
        )
        fig_pie.update_traces(marker=dict(line=dict(width=0)))
        fig_pie.update_layout(
            template='plotly_white', margin=dict(t=40, b=10, l=10, r=10),
            xaxis=dict(visible=False, showgrid=False, zeroline=False, showline=False),
            yaxis=dict(visible=False, showgrid=False, zeroline=False, showline=False),
        )
    except Exception as e:
        fig_pie = go.Figure().add_annotation(text=f"Error Pie Chart: {e}", showarrow=False)

    # --- 3B. Hitung Moran's I untuk PC1 Kompromi (Sumbu Ekonomi Utama) ---
    moran_text = ""
    formulas_m_i = None
    formulas_m_exp = None
    if res and indonesia_geojson and gdf is not None:
        try:
            # Ambil skor PC1
            scores = np.array(res['scores'])
            pc1_scores = scores[:, 0]
            obs_labels_mc = res['obs_labels']
            
            # Hitung
            m_i, m_exp, n, sum_w, sum_w_dev, sum_dev_sq = _calculate_moran_manual(gdf, pc1_scores, obs_labels_mc)
            
            if m_i is not None:
                status = "Berkelompok (Clustered)" if m_i > m_exp else "Menyebar (Dispersed/Random)"
                moran_text = f" | Global Moran's I (PC1): {m_i:.4f} (Exp: {m_exp:.4f}) -> Pola: {status}"
                formulas_m_i, formulas_m_exp, formulas_n, formulas_sum_w, formulas_sum_w_dev, formulas_sum_dev_sq = m_i, m_exp, n, sum_w, sum_w_dev, sum_dev_sq
        except Exception as e:
            print(f"Gagal hitung Moran di callback: {e}")

    # --- 4. PETA CHOROPLETH (UPDATED MATCHING LOGIC) ---
    fig_map = go.Figure()
    
    if indonesia_geojson:
        # A. Siapkan DataFrame
        df_map = pd.DataFrame({'Kab/Kota': obs_labels, 'Cluster': str_labels})
        df_map['match_key'] = df_map['Kab/Kota']
        
        # B. Inject Key ke GeoJSON (In-Memory)
        found_matches = 0
        
        for feature in indonesia_geojson['features']:
            props = feature['properties']
            
            # Cari nama di GeoJSON (Eksak)
            clean_geo_name = props.get('id_cocok') or ""
            
            # Cek apakah cocok dengan data Excel
            if clean_geo_name in df_map['match_key'].values:
                found_matches += 1

        # C. Plotting
        title_text = f"Peta Sebaran Klaster (Cocok: {found_matches} Wilayah)"
        if found_matches == 0:
            title_text += " - PERINGATAN: Nama wilayah tidak ada yang cocok!"

        fig_map = px.choropleth_mapbox(
            df_map,
            geojson=indonesia_geojson,
            locations='match_key',           # Eksak
            featureidkey='properties.id_cocok', 
            color='Cluster',
            color_discrete_map=CLUSTER_COLOR_MAP,
            category_orders={"Cluster": LEVEL_ORDER},
            hover_name='Kab/Kota',
            mapbox_style="carto-positron",
            center={"lat": -6.9, "lon": 107}, # Geser ke kiri (zoom out 2x)
            zoom=6.5, opacity=0.7
        )
        fig_map.update_layout(title=title_text, margin={"r":0,"t":40,"l":0,"b":0})
        # Add Text Labels — use pre-built centroid dict for speed
        centroid_dict = {row['id_cocok']: (row.geometry.centroid.x, row.geometry.centroid.y)
                         for _, row in gdf.iterrows() if row['id_cocok'] in obs_labels}
        lon_list_c = [centroid_dict[a][0] for a in obs_labels if a in centroid_dict]
        lat_list_c = [centroid_dict[a][1] for a in obs_labels if a in centroid_dict]
        text_list_c = [a for a in obs_labels if a in centroid_dict]
        if text_list_c:
            fig_map.add_trace(go.Scattermapbox(lon=lon_list_c, lat=lat_list_c, mode='text', text=text_list_c, textfont=dict(size=9, color='black'), showlegend=False))
    else:
        fig_map.add_annotation(text="Gagal memuat data GeoJSON.", showarrow=False)

    # 5. Interpretasi
    counts = np.bincount(labels)
    interp_text = [html.Strong("Interpretasi Klaster (Trajectory): "), html.Br()]
    if moran_text: 
        interp_text.append(html.Span(moran_text, style={'color': '#D81B60', 'fontWeight': 'bold'}))
        interp_text.append(html.Br())
        
    for i in range(len(counts)):
        cluster_name = name_map.get(rank_map[i], f"Klaster {rank_map[i]+1}")
        interp_text.append(f"{cluster_name}: {counts[i]} Wilayah.")
        if i < len(counts)-1: interp_text.append(" | ")
    
    # --- 6. Tabel Anggota (NEW) ---
    member_data = []
    for r in range(k_clusters):
        # Cari label original mana yang sesuai dengan rank r
        target_labels = [old for old, new in rank_map.items() if new == r]
        if not target_labels: continue
        old_l = target_labels[0]
        c_name = name_map.get(r, f"Level {r+1}")
        m_list = [obs_labels[idx] for idx, l in enumerate(labels) if l == old_l]
        member_data.append({
            'cluster_name': c_name,
            'count': len(m_list),
            'member_list': ", ".join(m_list)
        })
    
    member_cols = [
        {"name": "Kelompok (Cluster)", "id": "cluster_name"},
        {"name": "Jumlah Wilayah", "id": "count"},
        {"name": "Daftar Kabupaten/Kota", "id": "member_list"}
    ]

    # --- 7. Formulasi ---
    if formulas_m_i is not None:
        math_ui = render_cluster_formulas(formulas_m_i, formulas_m_exp, formulas_n, formulas_sum_w, formulas_sum_w_dev, formulas_sum_dev_sq)
    else:
        math_ui = render_cluster_formulas()

    return fig_scatter, fig_pie, fig_map, interp_text, math_ui, member_data, member_cols, {'display': 'block'}, ""

# 12. IPM MATRIX CALLBACK (UNDP CATEGORIES)
@app.callback(
    Output('ipm-disclaimer-text', 'children'),
    Output('ipm-trans-matrix-table', 'data'),
    Output('ipm-trans-matrix-table', 'columns'),
    Output('title-ipm-trans-map-t1', 'children'),
    Output('ipm-trans-map-t1', 'figure'),
    Output('title-ipm-trans-map-t2', 'children'),
    Output('ipm-trans-map-t2', 'figure'),
    Output('title-ipm-trans-pie-t1', 'children'),
    Output('ipm-trans-pie-t1', 'figure'),
    Output('title-ipm-trans-pie-t2', 'children'),
    Output('ipm-trans-pie-t2', 'figure'),
    Output('ipm-trans-results-container', 'style'),
    Output('spinner-run-ipm-trans', 'children'),
    Input('btn-run-ipm-trans', 'n_clicks'),
    Input('ipm-trans-view-mode', 'value'),
    State('ipm-trans-year-dropdown', 'value'),
    State('global-data-store', 'data')
)
def cb_run_ipm_trans(n_clicks, view_mode, t2_year, data):
    if not n_clicks or not t2_year or not data: return "", [], [], "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, {'display': 'none'}, ""

    df = pd.read_json(io.StringIO(data['df_json']), orient='split')
    years = data['years']

    if 'IPM' not in df.columns:
        return "Kolom IPM tidak ditemukan pada data yang diunggah.", [], [], "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, {'display': 'none'}, ""

    t2_idx = years.index(t2_year)
    if t2_idx == 0: return "Pilih tahun selain tahun pertama.", [], [], "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, {'display': 'none'}, ""
    t1_year = years[t2_idx - 1]

    # Filter Data untuk T1 dan T2
    df_t1 = df[df['Tahun'] == t1_year].set_index('Kabupaten/Kota')
    df_t2 = df[df['Tahun'] == t2_year].set_index('Kabupaten/Kota')

    common_kabs = df_t1.index.intersection(df_t2.index)
    if len(common_kabs) == 0: return "Tidak ada data Kabupaten/Kota yang cocok antara dua tahun.", [], [], "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, {'display': 'none'}, ""
    
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
        matrix_tex.append(r"% !TeX root = ../induk.tex")
        matrix_tex.append(r"\begin{table}[H]")
        matrix_tex.append(r"\centering")
        matrix_tex.append(r"\caption{Matriks Transisi IPM Tahun " + str(t1_year) + r" ke " + str(t2_year) + r"} \label{tab:ipm_transisi_" + str(t1_year) + r"_" + str(t2_year) + r"}")
        matrix_tex.append(r"\begin{tabular}{|c|" + "p{2cm}|"*len(categories) + "}")
        matrix_tex.append(r"\hline")
        
        header_row = [f"\\makecell{{\\textbf{{Tahun {t1_year}}} \\\\ \\textbf{{{t2_year}}}}}"] + [f"\\textbf{{{cat} ({t2_year})}}" for cat in categories]
        matrix_tex.append(" & ".join(header_row) + r" \\ \hline")
        
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
    os.makedirs("../output_app", exist_ok=True)
    try:
        with open(f"../output_app/output_table_ipm_sum_{t1_year}x{t2_year}.tex", "w") as f: f.write("\n".join(tex_count))
        with open(f"../output_app/output_table_ipm_name_{t1_year}x{t2_year}.tex", "w") as f: f.write("\n".join(tex_names))
    except: pass
        
    req_data = data_count if view_mode == 'count' else data_names
    cols = [{"name": c, "id": c} for c in req_data[0].keys()] if req_data else []
    
    # --- BUILD MAP & PIE CHARTS ---
    obs_labels = list(common_kabs)
    str_labels_t1 = df_t1.loc[common_kabs, 'IPM_Cat'].tolist()
    str_labels_t2 = df_t2.loc[common_kabs, 'IPM_Cat'].tolist()
    
    fig_map_t1, fig_map_t2 = go.Figure(), go.Figure()
    if indonesia_geojson:
        mapbox_center, mapbox_zoom = {"lat": -6.9, "lon": 107}, 6.5
        df_map_t1 = pd.DataFrame({'Kab/Kota': obs_labels, 'Cluster': str_labels_t1, 'match_key': obs_labels})
        df_map_t2 = pd.DataFrame({'Kab/Kota': obs_labels, 'Cluster': str_labels_t2, 'match_key': obs_labels})
        
        fig_map_t1 = px.choropleth_mapbox(df_map_t1, geojson=indonesia_geojson, locations='match_key', featureidkey='properties.id_cocok', color='Cluster', color_discrete_map=IPM_COLOR_MAP, category_orders={"Cluster": IPM_ORDER}, hover_name='Kab/Kota', mapbox_style="carto-positron", center=mapbox_center, zoom=mapbox_zoom, opacity=0.7)
        fig_map_t1.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        
        fig_map_t2 = px.choropleth_mapbox(df_map_t2, geojson=indonesia_geojson, locations='match_key', featureidkey='properties.id_cocok', color='Cluster', color_discrete_map=IPM_COLOR_MAP, category_orders={"Cluster": IPM_ORDER}, hover_name='Kab/Kota', mapbox_style="carto-positron", center=mapbox_center, zoom=mapbox_zoom, opacity=0.7)
        fig_map_t2.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        
        for f, df_m in [(fig_map_t1, df_map_t1), (fig_map_t2, df_map_t2)]:
            lon_list, lat_list, text_list = [], [], []
            for _, row in df_m.iterrows():
                area = row['Kab/Kota']
                geom = gdf[gdf['id_cocok'] == area]
                if not geom.empty:
                    lon_list.append(geom.geometry.centroid.x.values[0])
                    lat_list.append(geom.geometry.centroid.y.values[0])
                    text_list.append(area)
            if text_list:
                f.add_trace(go.Scattermapbox(lon=lon_list, lat=lat_list, mode='text', text=text_list, textfont=dict(size=9, color='black'), showlegend=False))

    from collections import Counter
    counts_p1 = Counter(str_labels_t1)
    fig_pie_t1 = px.pie(
        names=list(counts_p1.keys()),
        values=list(counts_p1.values()),
        color=list(counts_p1.keys()),
        color_discrete_map=IPM_COLOR_MAP,
        category_orders={"names": IPM_ORDER}
    )
    fig_pie_t1.update_layout(template='plotly_white')
    
    counts_p2 = Counter(str_labels_t2)
    fig_pie_t2 = px.pie(
        names=list(counts_p2.keys()),
        values=list(counts_p2.values()),
        color=list(counts_p2.keys()),
        color_discrete_map=IPM_COLOR_MAP,
        category_orders={"names": IPM_ORDER}
    )
    fig_pie_t2.update_layout(template='plotly_white')

    return (
        disclaimer_parts, req_data, cols,
        f"Peta Sebaran IPM ({t1_year})", fig_map_t1,
        f"Peta Sebaran IPM ({t2_year})", fig_map_t2,
        f"Proporsi Kategori IPM ({t1_year})", fig_pie_t1,
        f"Proporsi Kategori IPM ({t2_year})", fig_pie_t2,
        {'display': 'block'}, ""
    )


# 13. CROSS TABULATION CALLBACK (K-MEANS VS IPM)
@app.callback(
    Output('cross-table', 'data'),
    Output('cross-table', 'columns'),
    Output('title-cross-map-biplot', 'children'),
    Output('cross-map-biplot', 'figure'),
    Output('title-cross-map-ipm', 'children'),
    Output('cross-map-ipm', 'figure'),
    Output('title-cross-pie-biplot', 'children'),
    Output('cross-pie-biplot', 'figure'),
    Output('title-cross-pie-ipm', 'children'),
    Output('cross-pie-ipm', 'figure'),
    Output('cross-results-container', 'style'),
    Output('spinner-run-cross', 'children'),
    Input('btn-run-cross', 'n_clicks'),
    Input('cross-view-mode', 'value'),
    State('cross-year-dropdown', 'value'),
    State('cross-k-input', 'value'),
    State('global-data-store', 'data'),
    State('statis-core-store', 'data')
)
def cb_run_cross_tab(n_clicks, view_mode, sel_year, k, data_store, statis_store):
    if not n_clicks or not sel_year or not data_store or not statis_store:
        return [], [], "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, {'display': 'none'}, ""

    try:
        # 1. Ambil IPM kategories dari data asli
        df = pd.read_json(io.StringIO(data_store['df_json']), orient='split')
        if 'IPM' not in df.columns:
            return [], [], "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, {'display': 'none'}, ""

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
        if str_year not in statis_store['per_year_coords']:
            return [], [], "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, {'display': 'none'}, ""
        
        coords = np.array(statis_store['per_year_coords'][str_year])
        km_curr = KMeans(n_clusters=k, random_state=42, n_init=10)
        lbls = km_curr.fit_predict(coords)
        curr_centroids = km_curr.cluster_centers_
        
        # --- AUTOMATED ALIGNED LABELING (Same as Spatial-Temporal section) ---
        cluster_means = []
        unique_lbls = sorted(list(set(lbls)))
        for cl in unique_lbls:
            cluster_means.append(np.mean(coords[[i for i, l in enumerate(lbls) if l == cl], 0]))
            
        sorted_indices = np.argsort(cluster_means)
        rank_map = {old: new for new, old in enumerate(sorted_indices)}
        name_map = {0: "Klaster 1 (Rendah)", 1: "Klaster 2 (Sedang)", 2: "Klaster 3 (Tinggi)"}
        str_labels = [name_map.get(rank_map[l], f"Klaster {rank_map[l]+1}") for l in lbls]
        
        # Gabung
        df_clusters = pd.DataFrame({'Cluster_KMeans': str_labels}, index=obs_labels)
        df_merged = df_yr.join(df_clusters).dropna(subset=['Cluster_KMeans', 'IPM_Cat'])
        
        # Tabulasi Silang
        categories = ["Sangat Tinggi", "Tinggi", "Sedang", "Rendah"]
        target_clusters = [name_map.get(i, f"Klaster {i+1}") for i in range(k)]
        
        def build_cross_matrix(mode):
            matrix_data, matrix_tex = [], []
            matrix_tex.append(r"% !TeX root = ../induk.tex")
            matrix_tex.append(r"\begin{table}[H]")
            matrix_tex.append(r"\centering")
            matrix_tex.append(r"\caption{Perbandingan Klaster dengan Kategori IPM (" + str(sel_year) + r")} \label{tab:ipm_cross_" + str(sel_year) + r"}")
            matrix_tex.append(r"\begin{tabular}{|c|" + "p{2cm}|"*len(categories) + "}")
            matrix_tex.append(r"\hline")
            
            header_row = ["Klaster K-Means"] + categories
            matrix_tex.append(" & ".join([f"\\textbf{{{x}}}" for x in header_row]) + r" \\ \hline")
            
            for c_name in target_clusters:
                row_dict = {"Klaster K-Means": c_name}
                tex_row = [f"\\textbf{{{c_name}}}"]
                for cat in categories:
                    kabs = df_merged[(df_merged['Cluster_KMeans'] == c_name) & (df_merged['IPM_Cat'] == cat)].index.tolist()
                    if mode == 'count': val = str(len(kabs))
                    else: val = ", ".join(kabs) if kabs else "-"
                    row_dict[cat] = val
                    tex_row.append(val.replace('&', r'\&').replace('%', r'\%'))
                matrix_data.append(row_dict)
                matrix_tex.append(" & ".join(tex_row) + r" \\ \hline")
                
            matrix_tex.append(r"\end{tabular}")
            matrix_tex.append(r"\end{table}")
            return matrix_data, matrix_tex
            
        data_count, tex_count = build_cross_matrix('count')
        data_names, tex_names = build_cross_matrix('names')
        
        import os
        os.makedirs("../output_app", exist_ok=True)
        try:
            with open(f"../output_app/output_table_cross_matrix_sum_{sel_year}.tex", "w") as f: f.write("\n".join(tex_count))
            with open(f"../output_app/output_table_cross_matrix_name_{sel_year}.tex", "w") as f: f.write("\n".join(tex_names))
        except: 
            pass
        
        req_data = data_count if view_mode == 'count' else data_names
        cols = [{"name": c, "id": c} for c in req_data[0].keys()] if req_data else []
        
        # C. BUILD MAPS AND PIES
        fig_map_biplot, fig_map_ipm = go.Figure(), go.Figure()
        if indonesia_geojson:
            mapbox_center, mapbox_zoom = {"lat": -6.9, "lon": 107}, 6.5
            df_map_b = pd.DataFrame({'Kab/Kota': obs_labels, 'Cluster': str_labels, 'match_key': obs_labels})
            cats_ipm_list = df_yr['IPM_Cat'].reindex(obs_labels).fillna('Sedang').tolist()
            df_map_i = pd.DataFrame({'Kab/Kota': obs_labels, 'Cluster': cats_ipm_list, 'match_key': obs_labels})
            
            fig_map_biplot = px.choropleth_mapbox(df_map_b, geojson=indonesia_geojson, locations='match_key', featureidkey='properties.id_cocok', color='Cluster', color_discrete_map=CLUSTER_COLOR_MAP, category_orders={"Cluster": LEVEL_ORDER}, hover_name='Kab/Kota', mapbox_style="carto-positron", center=mapbox_center, zoom=mapbox_zoom, opacity=0.7)
            fig_map_biplot.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            
            fig_map_ipm = px.choropleth_mapbox(df_map_i, geojson=indonesia_geojson, locations='match_key', featureidkey='properties.id_cocok', color='Cluster', color_discrete_map=IPM_COLOR_MAP, category_orders={"Cluster": IPM_ORDER}, hover_name='Kab/Kota', mapbox_style="carto-positron", center=mapbox_center, zoom=mapbox_zoom, opacity=0.7)
            fig_map_ipm.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            
            for f, df_m in [(fig_map_biplot, df_map_b), (fig_map_ipm, df_map_i)]:
                lon_list, lat_list, text_list = [], [], []
                for _, row in df_m.iterrows():
                    area = row['Kab/Kota']
                    geom = gdf[gdf['id_cocok'] == area]
                    if not geom.empty:
                        lon_list.append(geom.geometry.centroid.x.values[0])
                        lat_list.append(geom.geometry.centroid.y.values[0])
                        text_list.append(area)
                if text_list:
                    f.add_trace(go.Scattermapbox(lon=lon_list, lat=lat_list, mode='text', text=text_list, textfont=dict(size=9, color='black'), showlegend=False))
                    
        from collections import Counter
        counts_b = Counter(str_labels)
        fig_pie_biplot = px.pie(
            names=list(counts_b.keys()),
            values=list(counts_b.values()),
            color=list(counts_b.keys()),
            color_discrete_map=CLUSTER_COLOR_MAP,
            category_orders={"names": LEVEL_ORDER}
        )
        fig_pie_biplot.update_layout(template='plotly_white')
        
        counts_i = Counter(df_yr['IPM_Cat'].reindex(obs_labels).fillna('Sedang').tolist())
        fig_pie_ipm = px.pie(
            names=list(counts_i.keys()),
            values=list(counts_i.values()),
            color=list(counts_i.keys()),
            color_discrete_map=IPM_COLOR_MAP,
            category_orders={"names": IPM_ORDER}
        )
        fig_pie_ipm.update_layout(template='plotly_white')
        
        return (
            req_data, cols,
            f"Peta Klaster Biplot ({sel_year})", fig_map_biplot,
            f"Peta Kategori IPM ({sel_year})", fig_map_ipm,
            f"Proporsi Klaster Biplot ({sel_year})", fig_pie_biplot,
            f"Proporsi Kategori IPM ({sel_year})", fig_pie_ipm,
            {'display': 'block'}, ""
        )
    except Exception as e:
        print(f"Error cb_run_cross_tab: {e}")
        return [], [], "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, "", EMPTY_FIG, {'display': 'none'}, ""

# =========================================================
# UTIL: EKSPOR TABEL UI COMPONENT KE .TEX
# =========================================================
def ui_table_to_latex(data, columns, caption, label):
    if not data or not columns: return "% Data kosong"
    
    col_ids = [c['id'] for c in columns if 'id' in c]
    col_names = [c['name'] for c in columns if 'name' in c]
    if not col_ids: return "% Setup kolom gagal"
    
    tex = [r"% !TeX root = ../induk.tex", r"\begin{table}[H]", r"\centering"]
    tex.append(rf"\caption{{{escape_tex(caption)}}} \label{{{label}}}")
    
    # Lebar kolom pertama otomatis, sisa p{2.3cm} agar muat
    aligns = "|c|" + "p{2.3cm}|" * (len(col_ids)-1)
    tex.append(rf"\begin{{tabular}}{{{aligns}}}")
    tex.append(r"\hline")
    
    # Header
    header = " & ".join([f"\\textbf{{{n}}}" for n in col_names])
    tex.append(header + r" \\ \hline")
    
    # Baris
    for row in data:
        row_vals = []
        for i, cid in enumerate(col_ids):
            val = str(row.get(cid, "-")).replace("&", r"\&").replace("%", r"\%")
            if i == 0: row_vals.append(f"\\textbf{{{val}}}")
            else: row_vals.append(val)
        tex.append(" & ".join(row_vals) + r" \\ \hline")
        
    tex.append(r"\end{tabular}")
    tex.append(r"\end{table}")
    return "\n".join(tex)

@app.callback(
    Output("download-trans-tex", "data"),
    Input("btn-dl-trans-tex", "n_clicks"),
    State("trans-matrix-table", "data"), State("trans-matrix-table", "columns"),
    State("trans-year-dropdown", "value"), State("trans-view-mode", "value"),
    prevent_initial_call=True
)
def dl_trans_tex(n_clicks, data, columns, year, mode):
    if not data or not year: return dash.no_update
    y2 = int(year)
    y1 = y2 - 1
    sfx = "name" if mode == "names" else "sum"
    filename = f"output_table_biplot_transition_{sfx}_{y1}x{y2}.tex"
    if mode == "names":
        caption = f"Nama Daerah Transisi Klaster Biplot Tahunan ({y1} vs {y2})"
        label = f"biplot_transition_name_{y1}x{y2}"
    else:
        caption = f"Matriks Transisi Klaster Biplot Tahunan ({y1} vs {y2})"
        label = f"biplot_transition_{y1}x{y2}"
    tex_str = ui_table_to_latex(data, columns, caption, f"tab:{label}")
    return dcc.send_string(tex_str, filename)

@app.callback(
    Output("download-weighted-trans-tex", "data"),
    Input("btn-dl-weighted-trans-tex", "n_clicks"),
    State("weighted-trans-matrix-table", "data"), State("weighted-trans-matrix-table", "columns"),
    State("weighted-trans-year-dropdown", "value"), State("weighted-trans-view-mode", "value"),
    prevent_initial_call=True
)
def dl_weighted_trans_tex(n_clicks, data, columns, year, mode):
    if not data or not year: return dash.no_update
    y2 = int(year)
    y1 = y2 - 1
    sfx = "name" if mode == "names" else "sum"
    filename = f"output_table_statis_transition_{sfx}_{y1}x{y2}.tex"
    if mode == "names":
        caption = f"Nama Daerah Transisi Klaster STATIS Tahunan ({y1} vs {y2})"
        label = f"statis_transition_name_{y1}x{y2}"
    else:
        caption = f"Matriks Transisi Klaster STATIS Tahunan ({y1} vs {y2})"
        label = f"statis_transition_{y1}x{y2}"
    tex_str = ui_table_to_latex(data, columns, caption, f"tab:{label}")
    return dcc.send_string(tex_str, filename)

@app.callback(
    Output("download-biplot-statis-compare-tex", "data"),
    Input("btn-dl-biplot-statis-compare-tex", "n_clicks"),
    State("biplot-statis-compare-matrix-table", "data"), State("biplot-statis-compare-matrix-table", "columns"),
    State("biplot-statis-compare-year", "value"), State("biplot-statis-compare-view-mode", "value"),
    prevent_initial_call=True
)
def dl_biplot_statis_compare_tex(n_clicks, data, columns, year, mode):
    if not data or not year: return dash.no_update
    sfx = "name" if mode == "names" else "sum"
    filename = f"output_table_biplot_vs_statis_compare_{sfx}_{year}.tex"
    if mode == "names":
        caption = f"Nama Daerah Perbandingan Klaster Biplot vs STATIS Tahunan ({year})"
        label = f"biplot_statis_comp_name_{year}"
    else:
        caption = f"Matriks Perbandingan Klaster Biplot vs STATIS (Tahunan) ({year})"
        label = f"biplot_statis_comp_{year}"
    tex_str = ui_table_to_latex(data, columns, caption, f"tab:{label}")
    return dcc.send_string(tex_str, filename)

@app.callback(
    Output("download-ipm-trans-tex", "data"),
    Input("btn-dl-ipm-trans-tex", "n_clicks"),
    State("ipm-trans-matrix-table", "data"), State("ipm-trans-matrix-table", "columns"),
    State("ipm-trans-year-dropdown", "value"), State("ipm-trans-view-mode", "value"),
    prevent_initial_call=True
)
def dl_ipm_tex(n_clicks, data, columns, year, mode):
    if not data or not year: return dash.no_update
    y2 = int(year)
    y1 = y2 - 1
    sfx = "name" if mode == "names" else "sum"
    filename = f"output_table_ipm_{sfx}_{y1}x{y2}.tex"
    if mode == "names":
        caption = f"Nama Daerah Transisi Kategori IPM (UNDP) ({y1} vs {y2})"
        label = f"ipm_transition_name_{y1}x{y2}"
    else:
        caption = f"Matriks Transisi Kategori IPM (UNDP) ({y1} vs {y2})"
        label = f"ipm_transition_{y1}x{y2}"
    tex_str = ui_table_to_latex(data, columns, caption, f"tab:{label}")
    return dcc.send_string(tex_str, filename)

@app.callback(
    Output("download-cross-tex", "data"),
    Input("btn-dl-cross-tex", "n_clicks"),
    State("cross-table", "data"), State("cross-table", "columns"),
    State("cross-year-dropdown", "value"), State("cross-view-mode", "value"),
    prevent_initial_call=True
)
def dl_cross_tex(n_clicks, data, columns, year, mode):
    if not data or not year: return dash.no_update
    sfx = "name" if mode == "names" else "sum"
    filename = f"output_table_cross_matrix_{sfx}_{year}.tex"
    if mode == "names":
        caption = f"Nama Daerah Perbandingan Klaster Biplot vs IPM (UNDP) ({year})"
        label = f"biplot_ipm_name_{year}"
    else:
        caption = f"Matriks Perbandingan Klaster Biplot vs Kategori IPM (UNDP) ({year})"
        label = f"biplot_ipm_{year}"
    tex_str = ui_table_to_latex(data, columns, caption, f"tab:{label}")
    return dcc.send_string(tex_str, filename)

@app.callback(
    Output("download-biplot-statis-tex", "data"),
    Input("btn-dl-biplot-statis-tex", "n_clicks"),
    State("biplot-vs-statis-table", "data"), State("biplot-vs-statis-table", "columns"),
    State("biplot-vs-statis-year", "value"), State("biplot-vs-statis-view-mode", "value"),
    prevent_initial_call=True
)
def dl_biplot_statis_tex(n_clicks, data, columns, year, mode):
    if not data or not year: return dash.no_update
    sfx = "name" if mode == "names" else "sum"
    filename = f"output_table_biplot_vs_statis_{sfx}_{year}.tex"
    if mode == "names":
        caption = f"Nama Daerah Perbandingan Klaster Biplot vs STATIS (vs Kompromi) ({year})"
        label = f"biplot_statis_name_{year}"
    else:
        caption = f"Matriks Perbandingan Klaster Biplot vs STATIS (vs Kompromi) ({year})"
        label = f"biplot_statis_{year}"
    tex_str = ui_table_to_latex(data, columns, caption, f"tab:{label}")
    return dcc.send_string(tex_str, filename)

@app.callback(
    Output("download-statis-ipm-avg-tex", "data"),
    Input("btn-dl-statis-ipm-avg-tex", "n_clicks"),
    State("statis-vs-ipm-avg-table", "data"), State("statis-vs-ipm-avg-table", "columns"),
    State("statis-vs-ipm-avg-year", "value"), State("statis-vs-ipm-avg-view-mode", "value"),
    prevent_initial_call=True
)
def dl_statis_ipm_avg_tex(n_clicks, data, columns, year, mode):
    if not data or not year: return dash.no_update
    sfx = "name" if mode == "names" else "sum"
    filename = f"output_table_compromise_vs_ipm_{sfx}_{year}.tex"
    if mode == "names":
        caption = f"Nama Daerah Perbandingan Klaster Kompromi STATIS vs IPM (UNDP) ({year})"
        label = f"compromise_ipm_name_{year}"
    else:
        caption = f"Perbandingan Klaster Kompromi STATIS vs Kategori IPM (UNDP) ({year})"
        label = f"compromise_ipm_{year}"
    tex_str = ui_table_to_latex(data, columns, caption, f"tab:{label}")
    return dcc.send_string(tex_str, filename)

@app.callback(
    Output("download-detail-tex", "data"),
    Input("btn-dl-detail-tex", "n_clicks"),
    State("statis-detail-table", "data"), State("statis-detail-table", "columns"), State("statis-table-selector", "value"),
    prevent_initial_call=True
)
def dl_detail_tex(n_clicks, data, columns, table_name):
    if not data: return dash.no_update
    caption = f"Tabel Hasil Analisis: {table_name}" if table_name else "Tabel Hasil Analisis"
    tex_str = ui_table_to_latex(data, columns, caption, "tab:statis_detail")
    return dcc.send_string(tex_str, f"output_tabel_{table_name}.tex" if table_name else "output_tabel.tex")


# ==========================================
# SECTION BARU: PROFIL RATA-RATA VARIABEL PER KLASTER
# ==========================================

@app.callback(
    Output('barplot-year-dropdown', 'options'),
    Output('barplot-year-dropdown', 'value'),
    Input('global-data-store', 'data'),
)
def sync_barplot_year_opts(global_data):
    if not global_data or 'years' not in global_data:
        return [], None
    years = sorted(global_data['years'])
    opts = [{'label': str(y), 'value': y} for y in years]
    return opts, years[-1] if years else None


@app.callback(
    Output('barplot-k-container', 'style'),
    Input('barplot-method-dropdown', 'value'),
)
def toggle_barplot_k(method):
    if method == 'ipm_cat':
        return {'display': 'none'}
    return {}


@app.callback(
    Output('barplot-charts-output', 'children'),
    Output('barplot-results-container', 'style'),
    Output('spinner-run-barplot', 'children'),
    Input('btn-run-barplot', 'n_clicks'),
    State('barplot-method-dropdown', 'value'),
    State('barplot-year-dropdown', 'value'),
    State('barplot-k-input', 'value'),
    State('global-data-store', 'data'),
    State('statis-core-store', 'data'),
    State('pca-results-store', 'data'),
    prevent_initial_call=True
)
def cb_run_barplot(n_clicks, method, sel_year, k, global_data, statis_res, pca_res):
    if not n_clicks or not global_data or not statis_res:
        return [], {'display': 'none'}, ""

    try:
        selected_vars = statis_res.get('selected_vars', [])
        obs_labels = statis_res.get('obs_labels', [])

        if not selected_vars or not obs_labels:
            return [html.P("Data belum tersedia. Jalankan analisis STATIS terlebih dahulu.",
                           style={'color': '#D84315', 'textAlign': 'center', 'padding': '20px'})], {'display': 'block'}, ""

        str_labels = []

        if method == 'biplot':
            if not pca_res or not sel_year:
                return [html.P("Pilih tahun. Pastikan analisis PCA sudah dijalankan.",
                               style={'color': '#D84315', 'textAlign': 'center', 'padding': '20px'})], {'display': 'block'}, ""
            df_scores = pd.read_json(io.StringIO(pca_res['pc_scores']), orient='split')
            df_yr = df_scores[df_scores['Tahun'] == int(sel_year)]
            if df_yr.empty:
                return [html.P(f"Data Biplot untuk tahun {sel_year} tidak tersedia.",
                               style={'color': '#D84315', 'textAlign': 'center', 'padding': '20px'})], {'display': 'block'}, ""
            coords = df_yr[['PC1', 'PC2']].to_numpy()
            obs_labels = df_yr['Kabupaten/Kota'].tolist()
            km = KMeans(n_clusters=k, random_state=42, n_init=10)
            lbls = km.fit_predict(coords)
            cl_means = [np.mean(coords[lbls == cl, 0]) for cl in range(k)]
            sorted_idx = np.argsort(cl_means)
            rank_map = {old: new for new, old in enumerate(sorted_idx)}
            name_map = {0: "Klaster 1 (Rendah)", 1: "Klaster 2 (Sedang)", 2: "Klaster 3 (Tinggi)", 3: "Klaster 4 (Sangat Tinggi)"}
            str_labels = [name_map.get(rank_map[l], f"Klaster {rank_map[l]+1}") for l in lbls]

        elif method == 'statis_yr':
            if not sel_year:
                return [html.P("Pilih tahun.", style={'color': '#D84315', 'textAlign': 'center', 'padding': '20px'})], {'display': 'block'}, ""
            str_yr = str(sel_year)
            if str_yr not in statis_res.get('per_year_coords', {}):
                return [html.P(f"Data STATIS untuk tahun {sel_year} tidak tersedia.",
                               style={'color': '#D84315', 'textAlign': 'center', 'padding': '20px'})], {'display': 'block'}, ""
            coords = np.array(statis_res['per_year_coords'][str_yr])
            km = KMeans(n_clusters=k, random_state=42, n_init=10)
            lbls = km.fit_predict(coords)
            cl_means = [np.mean(coords[lbls == cl, 0]) for cl in range(k)]
            sorted_idx = np.argsort(cl_means)
            rank_map = {old: new for new, old in enumerate(sorted_idx)}
            name_map = {0: "Klaster 1 (Rendah)", 1: "Klaster 2 (Sedang)", 2: "Klaster 3 (Tinggi)", 3: "Klaster 4 (Sangat Tinggi)"}
            str_labels = [name_map.get(rank_map[l], f"Klaster {rank_map[l]+1}") for l in lbls]

        elif method == 'kompromi':
            coords_dict = statis_res.get('per_year_coords', {})
            sheet_names_k = statis_res.get('sheet_names', sorted(list(coords_dict.keys())))
            alphas_k = statis_res.get('alphas', [1.0] * len(sheet_names_k))
            features = []
            for i in range(len(obs_labels)):
                city_feats = []
                for j, yr in enumerate(sheet_names_k):
                    w = np.sqrt(alphas_k[j])
                    c = np.array(coords_dict[str(yr)])
                    city_feats.extend(c[i, :] * w)
                features.append(city_feats)
            X_traj = np.array(features)
            km = KMeans(n_clusters=k, random_state=42, n_init=10)
            lbls = km.fit_predict(X_traj)
            scores_comp = np.array(statis_res['scores'])
            unique_lbls = sorted(list(set(lbls)))
            cl_pc1 = [np.mean(scores_comp[[i for i, l in enumerate(lbls) if l == cl], 0]) for cl in unique_lbls]
            sorted_idx = np.argsort(cl_pc1)
            rank_map = {old: new for new, old in enumerate(sorted_idx)}
            name_map = {0: "Klaster 1 (Rendah)", 1: "Klaster 2 (Sedang)", 2: "Klaster 3 (Tinggi)", 3: "Klaster 4 (Sangat Tinggi)"}
            str_labels = [name_map.get(rank_map[l], f"Klaster {rank_map[l]+1}") for l in lbls]

        elif method == 'ipm_cat':
            if not sel_year:
                return [html.P("Pilih tahun.", style={'color': '#D84315', 'textAlign': 'center', 'padding': '20px'})], {'display': 'block'}, ""
            df_all_ipm = pd.read_json(io.StringIO(global_data['df_json']), orient='split')
            df_yr_ipm = df_all_ipm[df_all_ipm['Tahun'] == int(sel_year)].set_index('Kabupaten/Kota')
            def _cat_ipm(v):
                if pd.isna(v): return "Sedang"
                return "Sangat Tinggi" if v >= 80 else "Tinggi" if v >= 70 else "Sedang" if v >= 55 else "Rendah"
            str_labels = [_cat_ipm(df_yr_ipm.loc[o, 'IPM']) if o in df_yr_ipm.index else "Sedang" for o in obs_labels]
        else:
            str_labels = ['Klaster 1 (Rendah)'] * len(obs_labels)

        label_map = {obs: lbl for obs, lbl in zip(obs_labels, str_labels)}

        # Get raw variable data
        df_raw = pd.read_json(io.StringIO(global_data['df_json']), orient='split')
        if sel_year:
            df_yr_raw = df_raw[df_raw['Tahun'] == int(sel_year)].set_index('Kabupaten/Kota')
        else:
            df_yr_raw = df_raw.groupby('Kabupaten/Kota')[selected_vars].mean()

        # Cluster ordering and colors
        if method == 'ipm_cat':
            ordered_clusters = [c for c in ["Rendah", "Sedang", "Tinggi", "Sangat Tinggi"] if c in set(str_labels)]
            color_map_use = IPM_COLOR_MAP
        else:
            ordered_clusters = sorted(
                set(str_labels),
                key=lambda x: int(x.split(' ')[1]) if len(x.split(' ')) > 1 and x.split(' ')[1].isdigit() else 0
            )
            color_map_use = CLUSTER_COLOR_MAP

        year_label = f" (Tahun {sel_year})" if sel_year else " (Semua Tahun)"
        method_label = {
            'biplot': 'Biplot PCA', 'statis_yr': 'STATIS Terbobot',
            'kompromi': 'Kompromi STATIS', 'ipm_cat': 'Kategori IPM UNDP'
        }.get(method, method)

        graphs = []
        row_items = []
        n_vars = len(selected_vars)

        for vi, var in enumerate(selected_vars):
            means, stds, colors = [], [], []
            for cl in ordered_clusters:
                vals = [
                    float(df_yr_raw.loc[o, var])
                    for o in obs_labels
                    if label_map.get(o) == cl
                    and o in df_yr_raw.index
                    and var in df_yr_raw.columns
                    and pd.notna(df_yr_raw.loc[o, var])
                ]
                means.append(np.mean(vals) if vals else 0.0)
                stds.append(np.std(vals) if vals else 0.0)
                colors.append(color_map_use.get(cl, '#90CAF9'))

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=ordered_clusters,
                y=means,
                error_y=dict(type='data', array=stds, visible=True, color='#37474F', thickness=1.5, width=8),
                marker_color=colors,
                customdata=stds,
                hovertemplate='<b>%{x}</b><br>Rata-rata: %{y:.4f}<br>Std Dev: %{customdata:.4f}<extra></extra>',
            ))
            fig.update_layout(
                title=dict(
                    text=f"<b>{var}</b>{year_label}<br><sup>{method_label}</sup>",
                    font=dict(size=13), x=0.5
                ),
                xaxis_title="Klaster",
                yaxis_title=f"Rata-rata {var}",
                template='plotly_white',
                margin=dict(l=60, r=20, t=70, b=60),
                height=380,
                showlegend=False,
                bargap=0.4,
            )
            row_items.append(html.Div(className='six columns', children=[
                dcc.Graph(figure=fig, style={'height': '380px'})
            ]))
            if len(row_items) == 2 or vi == n_vars - 1:
                graphs.append(html.Div(className='row', style={'marginBottom': '15px'}, children=row_items))
                row_items = []

        k_info = f" | k = {k}" if method != 'ipm_cat' else ""
        info_div = html.Div(
            style={'backgroundColor': '#E8EAF6', 'borderRadius': '6px', 'padding': '12px',
                   'marginBottom': '15px', 'textAlign': 'center'},
            children=[
                html.Strong(f"Metode: {method_label} | Tahun: {sel_year if sel_year else 'Semua'}{k_info}"),
                html.Br(),
                html.Span(f"n = {len(obs_labels)} wilayah | {n_vars} variabel analisis",
                          style={'fontSize': '13px', 'color': '#546E7A'})
            ]
        )

        return [info_div] + graphs, {'display': 'block'}, ""

    except Exception as e:
        return [html.P(f"Error: {str(e)}",
                       style={'color': '#D84315', 'textAlign': 'center', 'padding': '20px'})], {'display': 'block'}, ""


app.layout = layout

if __name__ == '__main__':
    # Run on port 7860 for Hugging Face Spaces compatibility
    app.run(host='0.0.0.0', port=7860, debug=True)