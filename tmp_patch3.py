import sys
import re

formulas_code = r'''from dash import html, dcc

math_style = {
    'padding': '15px', 'backgroundColor': '#F8FAFC', 'borderLeft': '4px solid #1976D2', 
    'marginTop': '10px', 'borderRadius': '5px', 'overflowX': 'auto'
}
summary_style = {
    'fontWeight': 'bold', 'cursor': 'pointer', 'color': '#1565C0', 'fontSize': '16px',
    'padding': '10px', 'backgroundColor': '#E3F2FD', 'borderRadius': '5px'
}

def render_diagnostic_formulas(kmo_val=None, kmo_str="", bart_p=None, bart_str=""):
    k_tex = "KMO" if kmo_val is None else f"{kmo_val:.4f}"
    b_tex = "p" if bart_p is None else f"{bart_p}"

    return html.Div([
        html.Details([
            html.Summary("1. Uji Kaiser-Meyer-Olkin (KMO) Measure of Sampling Adequacy", style=summary_style),
            html.Div([dcc.Markdown(mathjax=True, children=f"""
**Tujuan:** Mengukur kelayakan data untuk analisis multivariat.
$$ KMO = \\frac{{\\sum_{{j \\neq k}} r_{{jk}}^2}}{{\\sum_{{j \\neq k}} r_{{jk}}^2 + \\sum_{{j \\neq k}} q_{{jk}}^2}} $$
*(Di mana $r$ adalah korelasi Pearson, dan $q$ adalah korelasi spasial parsial)*

**Hasil:**
$$ KMO = {k_tex} \\quad \\text{{({kmo_str})}} $$
            """)], style=math_style)
        ], style={'marginBottom': '10px'}),
        
        html.Details([
            html.Summary("2. Bartlett's Test of Sphericity", style=summary_style),
            html.Div([dcc.Markdown(mathjax=True, children=f"""
**Tujuan:** Menguji apakah matriks korelasi berbeda secara signifikan dari matriks identitas.
$$ \\chi^2 \\approx - \\left( n - 1 - \\frac{{2p + 5}}{{6}} \\right) \\ln |R| $$

**Hasil (P-value):**
$$ p = {b_tex} \\quad \\text{{({bart_str})}} $$
            """)], style=math_style)
        ], style={'marginBottom': '10px'})
    ])

def render_statis_formulas(alpha_vals=None, years=None, w_c_slice=None, k_val=1):
    alpha_str = "\\sum_{t=1}^{K} \\alpha_t W_t"
    if alpha_vals and years:
        alpha_str = " + ".join([f"({a:.4f})W_{{{years[i]}}}" for i, a in enumerate(alpha_vals)])
        
    wc_tex = ""
    if w_c_slice is not None:
        matrix_rows = []
        for r in w_c_slice:
            matrix_rows.append(" & ".join([f"{float(v):.2f}" for v in r]))
        wc_tex = f"\\approx \\begin{{bmatrix}} {' \\\\ '.join(matrix_rows)} \\end{{bmatrix}}"
    
    return html.Div([
        html.Details([
            html.Summary("1. Standardisasi Data (Z-Score)", style=summary_style),
            html.Div([dcc.Markdown(mathjax=True, children="""
**Tujuan:** Agar indikator dengan skala berbeda (misal: Rupiah vs Persen) tidak mendominasi perhitungan jarak.
$$ z_{ijt} = \\frac{x_{ijt} - \\bar{x}_{jt}}{s_{jt}} $$
- $x_{ijt}$: Nilai indikator ke-$j$ untuk wilayah ke-$i$ pada tahun ke-$t$
- $\\bar{x}_{jt}$: Rata-rata indikator ke-$j$ pada tahun ke-$t$
- $s_{jt}$: Standar deviasi indikator ke-$j$ pada tahun ke-$t$
            """)], style=math_style)
        ], style={'marginBottom': '10px'}),
        
        html.Details([
            html.Summary("2. Peta Kemiripan Tahunan (Intra-struktur $\\mathbf{W}_t$)", style=summary_style),
            html.Div([dcc.Markdown(mathjax=True, children="""
**Tujuan:** Mengubah data mentah menjadi konfigurasi jarak spasial antar wilayah.
$$ \\mathbf{W}_t = \\mathbf{Z}_t \\mathbf{Z}_t^T $$
- $\\mathbf{Z}_t$: Matriks data terstandardisasi pada tahun $t$
- $\\mathbf{W}_t$: Matriks kemiripan (produk skalar) antar Kabupaten/Kota. Nilai tinggi menunjukkan kemiripan kinerja wilayah pada tahun tersebut.
            """)], style=math_style)
        ], style={'marginBottom': '10px'}),
        
        html.Details([
            html.Summary("3. Hubungan Antar-Tahun (Koefisien RV & Bobot $\\alpha$)", style=summary_style),
            html.Div([dcc.Markdown(mathjax=True, children="""
**Tujuan:** Mengukur kemiripan struktur secara keseluruhan antara tahun yang berbeda.
$$ RV(\\mathbf{W}_A, \\mathbf{W}_B) = \\frac{tr(\\mathbf{W}_A \\mathbf{W}_B)}{\\sqrt{tr(\\mathbf{W}_A^2) tr(\\mathbf{W}_B^2)}} $$
Setelah menghitung matriks RV antar semua tahun, dihitung Bobot $\\alpha_t$ melalui eigenvektor utama dari matriks RV untuk menekan efek dari tahun yang sangat berbeda (anomali).
            """)], style=math_style)
        ], style={'marginBottom': '10px'}),

        html.Details([
            html.Summary("4. Matriks Kompromi ($W_c$)", style=summary_style),
            html.Div([dcc.Markdown(mathjax=True, children=f"""
**Tujuan:** Menggabungkan seluruh tahun menjadi satu "Peta Rata-rata" (Konsensus).
$$ W_c = {alpha_str} $$
$$ {wc_tex} $$
- $\\alpha_t$: Bobot signifikansi dari struktur tahun ke-$t$. 
*(Catatan: Matriks di atas adalah contoh slice 3x3 dari wilayah pertama untuk simplisitas).*
            """)], style=math_style)
        ], style={'marginBottom': '10px'}),
        
        html.Details([
            html.Summary("5. Dekomposisi Singular (SVD) & Koordinat Kompromi", style=summary_style),
            html.Div([dcc.Markdown(mathjax=True, children="""
**Tujuan:** Mendapatkan titik kordinat (X,Y) dari peta rata-rata kompromi untuk Plot Biplot.
$$ W_c = U S V^T $$
Koordinat Skor (Objek):
$$ \\mathbf{F}_c = U \\sqrt{S} $$
            """)], style=math_style)
        ], style={'marginBottom': '10px'})
    ])

def render_cluster_formulas(moran_i=None, moran_exp=None):
    m_tex = "I" if moran_i is None else f"{moran_i:.4f}"
    e_tex = "E[I]" if moran_exp is None else f"{moran_exp:.4f}"
    
    return html.Div([
        html.Details([
            html.Summary("1. Fungsi Objektif K-Means (Inersia)", style=summary_style),
            html.Div([dcc.Markdown(mathjax=True, children="""
$$ J = \\sum_{j=1}^{k} \\sum_{i \\in C_j} ||\\mathbf{x}_i^{(traj)} - \\boldsymbol{\\mu}_j||^2 $$
            """)], style=math_style)
        ], style={'marginBottom': '10px'}),
        html.Details([
            html.Summary("2. Hierarchical Clustering (Ward's Linkage)", style=summary_style),
            html.Div([dcc.Markdown(mathjax=True, children="""
$$ d(u,v) = \\sqrt{\\frac{|u| \\cdot |v|}{|u| + |v|}} ||\\boldsymbol{\\mu}_u - \\boldsymbol{\\mu}_v||^2 $$
            """)], style=math_style)
        ], style={'marginBottom': '10px'}),
        html.Details([
            html.Summary("3. Global Moran\'s I (Autokorelasi Spasial PC1)", style=summary_style),
            html.Div([dcc.Markdown(mathjax=True, children=f"""
$$ I = \\frac{{N}}{{\\sum_i \\sum_j w_{{ij}}}} \\frac{{\\sum_i \\sum_j w_{{ij}} (x_i - \\bar{{x}})(x_j - \\bar{{x}})}}{{\\sum_i (x_i - \\bar{{x}})^2}} $$
*(Di mana $w_{{ij}}$ adalah bobot ketetanggaan spatila antar wilayah)*

**Hasil Substitusi:**
$$ I_{{obs}} = {m_tex} \\quad \\text{{(Ekspektasi: }} {e_tex} \\text{{)}} $$
            """)], style=math_style)
        ], style={'marginBottom': '10px'})
    ])
'''

with open(r"d:\Skripsi\my\web\skripsiv2\formulas.py", 'w', encoding='utf-8') as f:
    f.write(formulas_code)

# ----------------- MODIFY LAYOUT -----------------

with open(r"d:\Skripsi\my\web\skripsiv2\layout.py", 'r', encoding='utf-8') as f:
    layout_code = f.read()

# 1. Add RUN DIAGNOSTIK button to panel 2 Controls
btn_statis = r"""        html.Div(className='row', style={'marginTop': '15px'}, children=[
             html.Div(className='twelve columns', children=[
                html.Label('Filter Vektor Spesifik (Visualisasi):', style={'fontWeight':'bold'}),
                dcc.Dropdown(id='vector-selector-final', multi=True, placeholder="Pilih vektor spesifik untuk ditampilkan (Kosong = Semua)...")
            ])
        ])
    ]),"""
new_btn_statis = btn_statis.replace("]),", "]),\n        html.Button('RUN ANALISIS STATIS & BIPLOT', id='btn-run-statis', n_clicks=0, style={'width': '100%', 'marginTop': '20px', 'backgroundColor': COLOR_ACCENT, 'color': 'white', 'fontWeight': 'bold', 'borderRadius': '5px'})\n    ]),")
layout_code = layout_code.replace(btn_statis, new_btn_statis)

# 2. Add Run Diagnostics Button and replace the hardcoded formulas container with render_diagnostic_formulas container
diag_section = r"""    # --- [NEW] DATA DIAGNOSTICS & MATH FORMULAS ---
    html.Div(style=CARD_STYLE, children=[
        html.H5("Diagnostic Tests & Mathematical Insights", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
        
        # Diagnostics
        html.Div(className='row', children=[
            html.Div(className='six columns', children=[
                html.H6("Kaiser-Meyer-Olkin (KMO) Test", style={'fontWeight': 'bold'}),
                html.Div(id='kmo-result', style={'fontSize': '16px', 'padding': '10px', 'backgroundColor': '#E8F5E9', 'borderRadius': '5px'})
            ]),
            html.Div(className='six columns', children=[
                html.H6("Bartlett's Test of Sphericity", style={'fontWeight': 'bold'}),
                html.Div(id='bartlett-result', style={'fontSize': '16px', 'padding': '10px', 'backgroundColor': '#E8F5E9', 'borderRadius': '5px'})
            ])
        ]),
        
        html.Hr(),
        
        # Latex Toggle (Collapsible Google Colab Style)
        html.H6("Buka Bagian Bawah Untuk Melihat Detail Rumus Matematis DataFrame:", style={'fontWeight': 'bold', 'marginTop': '20px'}),
        collapsible_formulas
    ]),"""

new_diag_section = r"""    # --- [NEW] DATA DIAGNOSTICS ---
    html.Div(style=CARD_STYLE, children=[
        html.H5("1. Diagnostic Tests", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
        html.Div(style={'textAlign': 'center', 'marginBottom': '20px'}, children=[
            html.Button('RUN DIAGNOSTIK', id='btn-run-diag', n_clicks=0, style={'backgroundColor': '#FFB300', 'color': 'white', 'fontWeight': 'bold', 'borderRadius': '5px', 'width': '200px'})
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
    ]),"""
layout_code = layout_code.replace(diag_section, new_diag_section)

# 3. Add Formula Container inside STATIS section
statis_section = r"""        html.H5("Analisis STATIS (Struktur Kompromi)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
        
        # 4 Plot Grid"""
new_statis_section = r"""        html.H5("Analisis STATIS (Struktur Kompromi)", style={'textAlign': 'center', 'fontWeight': 'bold', 'color': COLOR_ACCENT}),
        dcc.Loading(children=[html.Div(id='formula-statis-output', style={'marginBottom': '20px'})]),
        # 4 Plot Grid"""
layout_code = layout_code.replace(statis_section, new_statis_section)

# 4. Add Formula Container inside Cluster Trajectory Section
cluster_section = r"""            html.Div(id='cluster-interpretation', style={'marginTop': '15px', 'padding': '15px', 'backgroundColor': '#E3F2FD', 'borderRadius': '5px', 'borderLeft': '5px solid #1565C0', 'fontStyle': 'italic', 'color': '#0D47A1'})
        ]),"""
new_cluster_section = r"""            html.Div(id='cluster-interpretation', style={'marginTop': '15px', 'padding': '15px', 'backgroundColor': '#E3F2FD', 'borderRadius': '5px', 'borderLeft': '5px solid #1565C0', 'fontStyle': 'italic', 'color': '#0D47A1'}),
            dcc.Loading(children=[html.Div(id='formula-cluster-output', style={'marginTop': '20px'})])
        ]),"""
layout_code = layout_code.replace(cluster_section, new_cluster_section)

# 5. Remove collapsible_formulas import from layout.py
layout_code = layout_code.replace("from formulas import collapsible_formulas\n", "")

with open(r"d:\Skripsi\my\web\skripsiv2\layout.py", 'w', encoding='utf-8') as f:
    f.write(layout_code)


# ----------------- MODIFY CALLBACKS -----------------
with open(r"d:\Skripsi\my\web\skripsiv2\callbacks.py", 'r', encoding='utf-8') as f:
    cb_code = f.read()

cb_code = cb_code.replace("from utils import *", "from utils import *\nfrom formulas import render_diagnostic_formulas, render_statis_formulas, render_cluster_formulas")

# 1. Update cb_diag_math to use explicit RUN BUTTON and Output formula
old_diag_cb = r"""# 4b. DIAGNOSTICS & MATH FORMULAS CALLBACK
@app.callback(
    Output('kmo-result', 'children'),
    Output('kmo-result', 'style'),
    Output('bartlett-result', 'children'),
    Output('bartlett-result', 'style'),
    
    Input('statis-core-store', 'data'),
    Input('global-data-store', 'data'),
    
)
def cb_diag_math(res, data_store):
    if not res or not data_store: return "Wait...", {}, "Wait...", {}
    
    # 1. Diagnostics
    df = pd.read_json(io.StringIO(data_store['df_json']), orient='split')
    df_dict = {y: df[df['Tahun'] == y] for y in data_store['years']}
    kmo_val, p_val, kmo_int, bart_int = calc_kmo_bartlett(df_dict, res['selected_vars'])
    
    kmo_txt = f"KMO = {kmo_val:.3f} ({kmo_int})"
    bart_txt = f"P-value = {p_val} ({bart_int})" # No Rounding!
    
    kmo_style = {'fontSize': '16px', 'padding': '10px', 'borderRadius': '5px', 'backgroundColor': '#E8F5E9' if kmo_val >= 0.5 else '#FFEBEE'}
    bart_style = {'fontSize': '16px', 'padding': '10px', 'borderRadius': '5px', 'backgroundColor': '#E8F5E9' if p_val < 0.05 else '#FFEBEE'}

    return kmo_txt, kmo_style, bart_txt, bart_style"""

new_diag_cb = r"""# 4b. DIAGNOSTICS & MATH FORMULAS CALLBACK
@app.callback(
    Output('kmo-result', 'children'),
    Output('kmo-result', 'style'),
    Output('bartlett-result', 'children'),
    Output('bartlett-result', 'style'),
    Output('diag-results-container', 'style'),
    Output('formula-diag-output', 'children'),
    Input('btn-run-diag', 'n_clicks'),
    State('global-data-store', 'data'),
    State('variable-dropdown-final', 'value')
)
def cb_diag_math(n_clicks, data_store, vars):
    if not n_clicks or not data_store or not vars: 
        return "Wait...", {}, "Wait...", {}, {'display': 'none'}, render_diagnostic_formulas()
    
    # 1. Diagnostics
    df = pd.read_json(io.StringIO(data_store['df_json']), orient='split')
    df_dict = {y: df[df['Tahun'] == y] for y in data_store['years']}
    kmo_val, p_val, kmo_int, bart_int = calc_kmo_bartlett(df_dict, vars)
    
    kmo_txt = f"KMO = {kmo_val:.3f} ({kmo_int})"
    bart_txt = f"P-value = {p_val} ({bart_int})" # No Rounding!
    
    kmo_style = {'fontSize': '16px', 'padding': '10px', 'borderRadius': '5px', 'backgroundColor': '#E8F5E9' if kmo_val >= 0.5 else '#FFEBEE'}
    bart_style = {'fontSize': '16px', 'padding': '10px', 'borderRadius': '5px', 'backgroundColor': '#E8F5E9' if p_val < 0.05 else '#FFEBEE'}

    formula_ui = render_diagnostic_formulas(kmo_val, kmo_int, p_val, bart_int)

    return kmo_txt, kmo_style, bart_txt, bart_style, {'display': 'flex'}, formula_ui"""

cb_code = cb_code.replace(old_diag_cb, new_diag_cb)

# 2. Update cb_statis_calc to trigger off `btn-run-statis`
old_statis_calc = r"""# 4. STATIS Core Calculation
@app.callback(
    Output('statis-core-store', 'data'), Input('variable-dropdown-final', 'value'),
    State('upload-data', 'contents'), State('global-data-store', 'data')
)
def cb_statis_calc(vars, contents, global_data):
    if not vars or not contents: raise exceptions.PreventUpdate
    try: return run_statis_core(contents, vars, global_data['sheet_names'])
    except: return None"""

new_statis_calc = r"""# 4. STATIS Core Calculation
@app.callback(
    Output('statis-core-store', 'data'), 
    Input('btn-run-statis', 'n_clicks'),
    State('variable-dropdown-final', 'value'),
    State('upload-data', 'contents'), State('global-data-store', 'data')
)
def cb_statis_calc(n_clicks, vars, contents, global_data):
    if not n_clicks or not vars or not contents: raise exceptions.PreventUpdate
    try: return run_statis_core(contents, vars, global_data['sheet_names'])
    except: return None"""

cb_code = cb_code.replace(old_statis_calc, new_statis_calc)

# 3. Update Statis VIZ to generate forms
old_statis_viz_def = r"""@app.callback(
    Output('statis-compromise', 'figure'), Output('statis-biplot', 'figure'),
    Output('statis-interstructure', 'figure'), Output('statis-trajectory', 'figure'),
    Output('statis-table-selector', 'options'), Output('statis-detail-table', 'data'), Output('statis-detail-table', 'columns'),
    Output('table-info-display', 'children'),
    Input('statis-core-store', 'data'), Input('statis-table-selector', 'value'), Input('visual-scaling-opts', 'value'),
    Input('table-page-size', 'value')
)
def cb_statis_viz(res, table_key, vis_opts, page_size):
    if not res: return {}, {}, {}, {}, [], [], [], \"\""""

new_statis_viz_def = r"""@app.callback(
    Output('statis-compromise', 'figure'), Output('statis-biplot', 'figure'),
    Output('statis-interstructure', 'figure'), Output('statis-trajectory', 'figure'),
    Output('statis-table-selector', 'options'), Output('statis-detail-table', 'data'), Output('statis-detail-table', 'columns'),
    Output('table-info-display', 'children'), Output('formula-statis-output', 'children'),
    Input('statis-core-store', 'data'), Input('statis-table-selector', 'value'), Input('visual-scaling-opts', 'value'),
    Input('table-page-size', 'value')
)
def cb_statis_viz(res, table_key, vis_opts, page_size):
    if not res: return {}, {}, {}, {}, [], [], [], "", render_statis_formulas()"""
cb_code = cb_code.replace(old_statis_viz_def, new_statis_viz_def)

# Add formula injection logic at the end of cb_statis_viz
old_statis_end = r"""    return fig_comp, fig_bi, fig_inter, fig_traj, table_opts, tbl_data, tbl_cols, info_text"""
new_statis_end = r"""    
    # Render Statis Formulas
    wc = np.array(res['Matriks Kompromi (Wc)'])
    w_slice = None
    if wc.shape[0] > 0:
        # ambil top 3x3 numeric part of it
        w_slice = [[float(v) for v in list(r.values())[1:4]] for r in wc[:3]]
    form_statis_ui = render_statis_formulas(res['alphas'], res['labels_R'], w_slice, res['k'])

    return fig_comp, fig_bi, fig_inter, fig_traj, table_opts, tbl_data, tbl_cols, info_text, form_statis_ui"""
if old_statis_end in cb_code:
    cb_code = cb_code.replace(old_statis_end, new_statis_end)


# 4. CLUSTERING TRAJEKTORY Callback
old_traj_output = r"""@app.callback(
    Output('cluster-scatter', 'figure'),
    Output('cluster-dendrogram', 'figure'),
    Output('cluster-map', 'figure'),
    Output('cluster-interpretation', 'children'),
    Input('btn-run-cluster', 'n_clicks'),"""
new_traj_output = r"""@app.callback(
    Output('cluster-scatter', 'figure'),
    Output('cluster-dendrogram', 'figure'),
    Output('cluster-map', 'figure'),
    Output('cluster-interpretation', 'children'),
    Output('formula-cluster-output', 'children'),
    Input('btn-run-cluster', 'n_clicks'),"""
cb_code = cb_code.replace(old_traj_output, new_traj_output)


old_traj_ret_none = r"""def cb_run_clustering_trajectory(n_clicks, k_clusters, res):
    if not n_clicks or not res: 
        return {}, {}, {}, "Silakan klik tombol 'RUN CLUSTERING'."""
new_traj_ret_none = r"""def cb_run_clustering_trajectory(n_clicks, k_clusters, res):
    if not n_clicks or not res: 
        return {}, {}, {}, "Silakan klik tombol 'RUN CLUSTERING'.", render_cluster_formulas()"""
cb_code = cb_code.replace(old_traj_ret_none, new_traj_ret_none)

old_traj_moran = r"""    moran_text = ""
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
            print(f"Gagal hitung Moran di callback: {e}")"""
            
new_traj_moran = r"""    moran_text = ""
    formulas_m_i = None
    formulas_m_exp = None
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
                formulas_m_i = m_i
                formulas_m_exp = m_exp
        except Exception as e:
            print(f"Gagal hitung Moran di callback: {e}")"""
cb_code = cb_code.replace(old_traj_moran, new_traj_moran)

old_traj_end = r"""    for i, count in enumerate(counts):
        interp_text.append(f"Cluster {i+1}: {count} Wilayah.")
        if i < len(counts)-1: interp_text.append(" | ")
        
    return fig_scatter, fig_dendro, fig_map, interp_text"""
new_traj_end = r"""    for i, count in enumerate(counts):
        interp_text.append(f"Cluster {i+1}: {count} Wilayah.")
        if i < len(counts)-1: interp_text.append(" | ")
    
    formula_cluster_ui = render_cluster_formulas(formulas_m_i, formulas_m_exp)
        
    return fig_scatter, fig_dendro, fig_map, interp_text, formula_cluster_ui"""

cb_code = cb_code.replace(old_traj_end, new_traj_end)


with open(r"d:\Skripsi\my\web\skripsiv2\callbacks.py", 'w', encoding='utf-8') as f:
    f.write(cb_code)

print("Patch applied successfully.")
