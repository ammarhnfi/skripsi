import sys
import os

target = r"d:\Skripsi\my\web\skripsiv2\app.py"

with open(target, 'r', encoding='utf-8') as f:
    code = f.read()

# --- 1. INJECT MATH/LATEX HELPER ---
# We inject a small CSS style and the MathJax component into the Layout.
import_mathjax = """import base64
"""
import_mathjax_new = """import base64
import dash_mathjax
"""
code = code.replace(import_mathjax, import_mathjax_new)

# Add MathJax script to requirements if it's there, but Dash sometimes needs external scripts
# So we just use dcc.Markdown with math=True (available in dash>=2.8.0)
external_style = """EXTERNAL_STYLESHEETS = ['https://codepen.io/chriddyp/pen/bWLwgP.css']"""
external_style_new = """EXTERNAL_STYLESHEETS = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
MATHJAX_SCRIPT = 'https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/MathJax.js?config=TeX-MML-AM_CHTML'
"""
code = code.replace(external_style, external_style_new)
code = code.replace("app = Dash(__name__, external_stylesheets=EXTERNAL_STYLESHEETS)", 
                    "app = Dash(__name__, external_stylesheets=EXTERNAL_STYLESHEETS, external_scripts=[MATHJAX_SCRIPT])")


# --- 2. INJECT DIAGNOSTICS LOGIC ---
diag_logic = """# -----------------------------
# APP LAYOUT
# -----------------------------"""
diag_logic_new = """# -----------------------------
# DATA DIAGNOSTICS HELPERS
# -----------------------------
import scipy.stats as stats

def calc_kmo_bartlett(df_dict, variables):
    try:
        kmos = []
        p_vals = []
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
        kmo_interp = "Excellent" if mean_kmo >= 0.9 else "Great" if mean_kmo >= 0.8 else "Good" if mean_kmo >= 0.7 else "Acceptable" if mean_kmo >= 0.5 else "Poor"
        bart_interp = "Significant (Suitable)" if mean_p < 0.05 else "Not Significant (Orthogonal)"
        return mean_kmo, mean_p, kmo_interp, bart_interp
    except: return 0.0, 1.0, "Error", "Error"

# -----------------------------
# APP LAYOUT
# -----------------------------"""
code = code.replace(diag_logic, diag_logic_new)

# --- 3. INJECT DATA DIAGNOSTICS & LATEX TOGGLE INTO UI ---
ui_controls_end = """        html.Div(className='row', style={'marginTop': '15px'}, children=[
             html.Div(className='twelve columns', children=[
                html.Label('Filter Vektor Spesifik (Visualisasi):', style={'fontWeight':'bold'}),
                dcc.Dropdown(id='vector-selector-final', multi=True, placeholder="Pilih vektor spesifik untuk ditampilkan (Kosong = Semua)...")
            ])
        ])
    ]),"""

ui_new = """        html.Div(className='row', style={'marginTop': '15px'}, children=[
             html.Div(className='twelve columns', children=[
                html.Label('Filter Vektor Spesifik (Visualisasi):', style={'fontWeight':'bold'}),
                dcc.Dropdown(id='vector-selector-final', multi=True, placeholder="Pilih vektor spesifik untuk ditampilkan (Kosong = Semua)...")
            ])
        ])
    ]),

    # --- [NEW] DATA DIAGNOSTICS & MATH FORMULAS ---
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
        
        # Latex Toggle
        html.H6("Show Mathematical Processing Steps (LaTeX Form):", style={'fontWeight': 'bold'}),
        dcc.Checklist(id='show-math-toggle', options=[{'label': ' Tampilkan Perhitungan Matematis', 'value': 'show'}], value=[], inline=True),
        html.Div(id='math-formulas-container', style={'display': 'none', 'marginTop': '20px', 'padding': '20px', 'backgroundColor': '#F5F5F5', 'borderLeft': f'4px solid {COLOR_ACCENT}'})
    ]),
"""
code = code.replace(ui_controls_end, ui_new)

# --- 4. CALLBACK FOR DIAGNOSTICS AND MATH ---
callback_inject_point = """# 5. DYNAMIC BIPLOT PLOTS"""

callback_diag_math = """# 4b. DIAGNOSTICS & MATH FORMULAS CALLBACK
@app.callback(
    Output('kmo-result', 'children'),
    Output('kmo-result', 'style'),
    Output('bartlett-result', 'children'),
    Output('bartlett-result', 'style'),
    Output('math-formulas-container', 'children'),
    Output('math-formulas-container', 'style'),
    Input('statis-core-store', 'data'),
    Input('global-data-store', 'data'),
    Input('show-math-toggle', 'value')
)
def cb_diag_math(res, data_store, show_math):
    if not res or not data_store: return "Wait...", {}, "Wait...", {}, "", {'display': 'none'}
    
    # 1. Diagnostics
    df = pd.read_json(io.StringIO(data_store['df_json']), orient='split')
    df_dict = {y: df[df['Tahun'] == y] for y in data_store['years']}
    kmo_val, p_val, kmo_int, bart_int = calc_kmo_bartlett(df_dict, res['selected_vars'])
    
    kmo_txt = f"KMO = {kmo_val:.3f} ({kmo_int})"
    bart_txt = f"P-value = {p_val:.4f} ({bart_int})"
    
    kmo_style = {'fontSize': '16px', 'padding': '10px', 'borderRadius': '5px', 'backgroundColor': '#E8F5E9' if kmo_val >= 0.5 else '#FFEBEE'}
    bart_style = {'fontSize': '16px', 'padding': '10px', 'borderRadius': '5px', 'backgroundColor': '#E8F5E9' if p_val < 0.05 else '#FFEBEE'}

    # 2. Math Formulas (LaTeX)
    math_style = {'display': 'block', 'marginTop': '20px', 'padding': '20px', 'backgroundColor': '#F5F5F5', 'borderLeft': f'4px solid {COLOR_ACCENT}'} if show_math else {'display': 'none'}
    
    # Render Matrix Wc dynamically as an example of math steps
    # We take the top-left 3x3 of Wc just to avoid huge math blocks
    Wc = np.array(res['Matriks Kompromi (Wc)'])
    if Wc.shape[0] > 0:
        k = res['k']
        alpha_str = " + ".join([f"{a:.3f} W_{i+1}" for i, a in enumerate(res['alphas'])])
        
        top3_wc = Wc[:3] # ambil 3 element pertama
        matrix_rows = []
        for r in top3_wc:
            vals = [str(x) for x in list(r.values())[1:4]] # ambil values numerik, skip label kota
            matrix_rows.append(" & ".join([f"{float(v):.2f}" for v in vals]))
            
        wc_tex = r"\\begin{aligned} W_c &= \sum_{k=1}^{" + str(k) + r"} \\alpha_k W_k \\\\" + r" &= " + alpha_str + r" \\\\" + r" &\\approx \\begin{bmatrix} " + r" \\\\ ".join(matrix_rows) + r" \\end{bmatrix} \\end{aligned}"
        
        math_content = dcc.Markdown(f"**Proses Pembentukan Matriks Kompromi ($W_c$):** \n\n $$ {wc_tex} $$ \n\n*(Catatan: Matriks dipotong 3x3 untuk simplisitas tampilan)*", mathjax=True)
    else:
        math_content = html.Span("Data tidak cukup untuk render matematis.")

    return kmo_txt, kmo_style, bart_txt, bart_style, math_content, math_style

# 5. DYNAMIC BIPLOT PLOTS"""

code = code.replace(callback_inject_point, callback_diag_math)

with open(target, 'w', encoding='utf-8') as f:
    f.write(code)

print("Diagnostics and LaTeX Patch scripts applied successfully.")
