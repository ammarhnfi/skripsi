import os
import re

source_file = r"d:\Skripsi\my\web\skripsiv2\app.py"
with open(source_file, 'r', encoding='utf-8') as f:
    text = f.read()

# Headers to split by
headers = [
    "# Import Library",
    "# -----------------------------",
]

# We will just write a new set of python files to skripsiv2
# Let's extract the imports
import_block = text.split("# Inisialisasi library")[0]

init_block = text.split("# --- KONFIGURASI LINK DATASET CONTOH ---")[0].split("# Inisialisasi library")[1]

# We can just manually copy the code blocks since they are very distinct.
# Actually, the safest way is to read the file, and split it by our known sections.

section_helpers = text.split("# Helper Functions")[1].split("# LATEX EXPORT HELPERS")[0]
section_latex_helpers = text.split("# LATEX EXPORT HELPERS")[1].split("# STATIS Core Logic (Perhitungan Berat)")[0]
section_core = text.split("# STATIS Core Logic (Perhitungan Berat)")[1].split("# PLOT HELPERS")[0]
section_plot_helpers = text.split("# PLOT HELPERS (With Visual Scaling)")[1].split("# APP LAYOUT")[0]

section_layout = text.split("# APP LAYOUT")[1].split("# CALLBACKS")[0]
section_callbacks = text.split("# CALLBACKS")[1]

# Let's write utils.py (Helpers + Plot Helpers + Latex)
with open(r"d:\Skripsi\my\web\skripsiv2\utils.py", "w", encoding='utf-8') as f:
    f.write(import_block)
    f.write("\n# Helper Functions\n")
    f.write(section_helpers)
    f.write("\n# LATEX EXPORT HELPERS\n")
    f.write(section_latex_helpers)
    f.write("\n# PLOT HELPERS (With Visual Scaling)\n")
    f.write(section_plot_helpers)

# Let's write statis_analysis.py
with open(r"d:\Skripsi\my\web\skripsiv2\statis_analysis.py", "w", encoding='utf-8') as f:
    f.write(import_block)
    f.write("from utils import *\n")
    
    # We need to un-round the p-values in this block.
    # In run_permutation_test, find the rounding if there is any.
    core_text = section_core
    f.write("\n# STATIS Core Logic\n")
    # Also grab the diagnostics logic which we injected earlier
    # Wait, the diagnostics logic was injected at the end of the file in the last patch or before APP LAYOUT
    if "# DATA DIAGNOSTICS HELPERS" in text:
        diag_text = text.split("# DATA DIAGNOSTICS HELPERS")[1].split("# APP LAYOUT")[0]
        # In diag_text, find the p_val rounding and remove it. The previous script didn't round p_val in calculation,
        # but in the callback it formatted as {p_val:.4f}. We will fix that in callbacks.py.
        f.write("# DATA DIAGNOSTICS HELPERS\n")
        f.write(diag_text)
    
    f.write(core_text)

# Let's write formulas.py containing the strings for Markdown
formulas = '''from dash import html, dcc

math_style = {
    'padding': '15px', 'backgroundColor': '#F8FAFC', 'borderLeft': '4px solid #1976D2', 
    'marginTop': '10px', 'borderRadius': '5px', 'overflowX': 'auto'
}
summary_style = {
    'fontWeight': 'bold', 'cursor': 'pointer', 'color': '#1565C0', 'fontSize': '16px',
    'padding': '10px', 'backgroundColor': '#E3F2FD', 'borderRadius': '5px'
}

collapsible_formulas = html.Div([
    html.Details([
        html.Summary("1. Standardisasi Data (Z-Score)", style=summary_style),
        html.Div([dcc.Markdown(mathjax=True, children=r"""
**Tujuan:** Agar indikator dengan skala berbeda (misal: Rupiah vs Persen) tidak mendominasi perhitungan jarak.

$$ z_{ijt} = \\frac{x_{ijt} - \\bar{x}_{jt}}{s_{jt}} $$

- $x_{ijt}$: Nilai indikator ke-$j$ untuk wilayah ke-$i$ pada tahun ke-$t$
- $\\bar{x}_{jt}$: Rata-rata indikator ke-$j$ pada tahun ke-$t$
- $s_{jt}$: Standar deviasi indikator ke-$j$ pada tahun ke-$t$
        """)], style=math_style)
    ], style={'marginBottom': '10px'}),
    
    html.Details([
        html.Summary("2. Peta Kemiripan Tahunan (Intra-struktur $\\mathbf{W}_t$)", style=summary_style),
        html.Div([dcc.Markdown(mathjax=True, children=r"""
**Tujuan:** Mengubah data mentah menjadi konfigurasi jarak spasial antar wilayah.

$$ \mathbf{W}_t = \mathbf{Z}_t \mathbf{Z}_t^T $$

- $\mathbf{Z}_t$: Matriks data terstandardisasi pada tahun $t$
- $\mathbf{W}_t$: Matriks kemiripan (produk skalar) antar Kabupaten/Kota. Nilai tinggi menunjukkan kemiripan kinerja wilayah pada tahun tersebut.
        """)], style=math_style)
    ], style={'marginBottom': '10px'}),
    
    html.Details([
        html.Summary("3. Hubungan Antar-Tahun (Koefisien RV & Bobot $\\alpha$)", style=summary_style),
        html.Div([dcc.Markdown(mathjax=True, children=r"""
**Tujuan:** Mengukur kemiripan struktur secara keseluruhan antara tahun yang berbeda.

$$ RV(\mathbf{W}_A, \mathbf{W}_B) = \\frac{tr(\mathbf{W}_A \mathbf{W}_B)}{\\sqrt{tr(\mathbf{W}_A^2) tr(\mathbf{W}_B^2)}} $$

Setelah menghitung matriks RV antar semua tahun, dihitung Bobot $\\alpha_t$ melalui eigenvektor utama dari matriks RV untuk menekan efek dari tahun yang sangat berbeda (anomali).
        """)], style=math_style)
    ], style={'marginBottom': '10px'}),

    html.Details([
        html.Summary("4. Matriks Kompromi ($W_c$)", style=summary_style),
        html.Div([dcc.Markdown(mathjax=True, children=r"""
**Tujuan:** Menggabungkan seluruh tahun menjadi satu "Peta Rata-rata" (Konsensus).

$$ W_c = \\sum_{t=1}^{K} \\alpha_t W_t $$

- $\\alpha_t$: Bobot signifikansi dari struktur tahun ke-$t$. 
        """)], style=math_style)
    ], style={'marginBottom': '10px'}),
    
    html.Details([
        html.Summary("5. Dekomposisi Singular (SVD) & Koordinat Kompromi", style=summary_style),
        html.Div([dcc.Markdown(mathjax=True, children=r"""
**Tujuan:** Mendapatkan titik kordinat (X,Y) dari peta rata-rata kompromi untuk Plot Biplot.

$$ W_c = U S V^T $$

Koordinat Skor (Objek):
$$ \mathbf{F}_c = U \sqrt{S} $$
        """)], style=math_style)
    ], style={'marginBottom': '10px'}),

    html.Details([
        html.Summary("6. Uji Signifikansi (KMO, Bartlett, & Moran's I)", style=summary_style),
        html.Div([dcc.Markdown(mathjax=True, children=r"""
**A. Kaiser-Meyer-Olkin (KMO) Measure of Sampling Adequacy**
$$ KMO = \\frac{\\sum_{j \\neq k} r_{jk}^2}{\\sum_{j \\neq k} r_{jk}^2 + \\sum_{j \\neq k} q_{jk}^2} $$
*(Di mana $r$ adalah korelasi Pearson, dan $q$ adalah korelasi spasial parsial)*

**B. Bartlett's Test of Sphericity**
$$ \\chi^2 \approx - \\left( n - 1 - \\frac{2p + 5}{6} \\right) \\ln |R| $$

**C. Global Moran's I (Autokorelasi Spasial)**
$$ I = \\frac{N}{\\sum_i \\sum_j w_{ij}} \\frac{\\sum_i \\sum_j w_{ij} (x_i - \\bar{x})(x_j - \\bar{x})}{\\sum_i (x_i - \\bar{x})^2} $$
*(Di mana $w_{ij}$ adalah bobot ketetanggaan/sentuhan antara wilayah $i$ dan $j$)*
        """)], style=math_style)
    ], style={'marginBottom': '10px'}),
])
'''
with open(r"d:\Skripsi\my\web\skripsiv2\formulas.py", "w", encoding='utf-8') as f:
    f.write(formulas)

# Let's write layout.py
layout_text = section_layout.replace(
    "# --- [NEW] DATA DIAGNOSTICS & MATH FORMULAS ---", 
    "from formulas import collapsible_formulas\n    # --- [NEW] DATA DIAGNOSTICS & MATH FORMULAS ---"
)

# We need to inject the collapsible_formulas right over the old math_formulas_container.
# Actually, we can just replace the whole Latex Toggle section.
old_latex_toggle = """        # Latex Toggle
        html.H6("Show Mathematical Processing Steps (LaTeX Form):", style={'fontWeight': 'bold'}),
        dcc.Checklist(id='show-math-toggle', options=[{'label': ' Tampilkan Perhitungan Matematis', 'value': 'show'}], value=[], inline=True),
        html.Div(id='math-formulas-container', style={'display': 'none', 'marginTop': '20px', 'padding': '20px', 'backgroundColor': '#F5F5F5', 'borderLeft': f'4px solid {COLOR_ACCENT}'})
    ]),"""

new_latex_toggle = """        # Latex Toggle (Collapsible Google Colab Style)
        html.H6("Buka Bagian Bawah Untuk Melihat Detail Rumus Matematis DataFrame:", style={'fontWeight': 'bold', 'marginTop': '20px'}),
        collapsible_formulas
    ]),"""

if old_latex_toggle in layout_text:
    layout_text = layout_text.replace(old_latex_toggle, new_latex_toggle)
else:
    # manual replacement if spacing differs
    import re
    layout_text = re.sub(r"# Latex Toggle.*?\]\),", new_latex_toggle, layout_text, flags=re.DOTALL)


with open(r"d:\Skripsi\my\web\skripsiv2\layout.py", "w", encoding='utf-8') as f:
    f.write(import_block)
    f.write(init_block)
    # The layout in app.py starts at "app = Dash(..." which we will put in app.py.
    # The layout itself is assigned to app.layout.
    # So we'll find "app.layout = html.Div(..."
    if "app.layout = " in layout_text:
        layout_components = "layout = " + layout_text.split("app.layout = ")[1]
        # remove the app.runServer line if it exists
        layout_components = layout_components.split("if __name__ == '__main__':")[0]
        f.write("from formulas import collapsible_formulas\n")
        f.write("from dash import Dash, dcc, html, dash_table\n")
        f.write("\nCOLOR_BG_MAIN = '#F0F4F8'\nCOLOR_CARD_BG = '#FFFFFF'\nCOLOR_HEADER_TEXT = '#1565C0'\nCOLOR_ACCENT = '#1976D2'\nCOLOR_BORDER = '#BBDEFB'\nCARD_STYLE = {'boxShadow': '0 2px 5px 0 rgba(0,0,0,0.05)', 'borderRadius': '8px', 'backgroundColor': COLOR_CARD_BG, 'padding': '25px', 'marginBottom': '25px', 'border': f'1px solid {COLOR_BORDER}'}\nHEADER_STYLE = {'textAlign': 'center', 'color': COLOR_HEADER_TEXT, 'fontWeight': '700', 'marginBottom': '15px', 'letterSpacing': '0.5px'}\nLABEL_STYLE = {'fontWeight': '600', 'color': '#37474F', 'fontSize': '1.4rem', 'marginBottom': '8px'}\n")
        
        # also we need EXAMPLE_DATASETS if it's there
        f.write('BASE_URL = "https://huggingface.co/spaces/ammarhnfi/skripsi/resolve/main"\n')
        f.write('EXAMPLE_DATASETS = [{"name": "Data Gabungan (FINAL DATA.xlsx)", "url": f"{BASE_URL}/FINAL DATA.xlsx"}]\n')
        
        # Remove the app instancing code if it accidentally got here
        f.write(layout_components)


# Let's write callbacks.py
# Un-round p-value inside callbacks.py
cb_text = section_callbacks
# KMO/Bartlett callback modification
old_bart_txt = '''bart_txt = f"P-value = {p_val:.4f} ({bart_int})"'''
new_bart_txt = '''bart_txt = f"P-value = {p_val} ({bart_int})" # No Rounding!'''
cb_text = cb_text.replace(old_bart_txt, new_bart_txt)

# Find perm p-value and unround
old_perm_txt = '''f"P-value = {p_val:.4f}. Interpretasi: {interp}"'''
new_perm_txt = '''f"P-value = {p_val}. Interpretasi: {interp}" # No Rounding!'''
cb_text = cb_text.replace(old_perm_txt, new_perm_txt)

# Remove the Math Formals Toggle logic since we made it a static Details menu
old_math_vars = """Output('math-formulas-container', 'children'),
    Output('math-formulas-container', 'style'),"""
cb_text = cb_text.replace(old_math_vars, "")

old_math_inputs = """Input('show-math-toggle', 'value')"""
cb_text = cb_text.replace(old_math_inputs, "")

cb_text_lines = cb_text.split('\n')
clean_cb_text = []
skip = False
for line in cb_text_lines:
    if "def cb_diag_math" in line:
        line = "def cb_diag_math(res, data_store):"
    if "2. Math Formulas (LaTeX)" in line:
         skip = True
    if skip and "return" in line and "kmo_txt" in line:
         skip = False
         line = "    return kmo_txt, kmo_style, bart_txt, bart_style"

    if not skip:
         clean_cb_text.append(line)

cb_text = "\n".join(clean_cb_text)


with open(r"d:\Skripsi\my\web\skripsiv2\callbacks.py", "w", encoding='utf-8') as f:
    f.write(import_block)
    f.write("from dash import dash_table\n")
    f.write("from utils import *\n")
    f.write("from statis_analysis import *\n")
    # Need layout config colors
    f.write("\nCOLOR_ACCENT = '#1976D2'\n\n")
    f.write(cb_text)

# Let's write the main app.py file which glues it all together
with open(r"d:\Skripsi\my\web\skripsiv2\app.py", "w", encoding='utf-8') as f:
    f.write(import_block)
    f.write("""
from layout import layout
import callbacks

EXTERNAL_STYLESHEETS = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
MATHJAX_SCRIPT = 'https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/MathJax.js?config=TeX-MML-AM_CHTML'

app = Dash(__name__, external_stylesheets=EXTERNAL_STYLESHEETS, external_scripts=[MATHJAX_SCRIPT], suppress_callback_exceptions=True)
server = app.server

app.layout = layout

# Inject the app instance into callbacks module
callbacks.app = app

# If we have callback decorators in callbacks.py, they need 'app'. 
# This requires a bit of magic or we can just import app in callbacks.py.
# Safer way in Dash: callbacks wrapper function or importing app.
""")

# Wait, `callbacks.py` uses `@app.callback`.
# If it's a separate file, it needs `from app import app`.
# But `app.py` needs `callbacks`. This is a circular dependency.
# The standard Dash way is to define `app` in `app.py`, then in `callbacks.py` do `from app import app`.
# Then in `app.py` we can `import callbacks` AFTER defining `app`.

with open(r"d:\Skripsi\my\web\skripsiv2\app.py", "w", encoding='utf-8') as f:
    f.write(import_block)
    f.write("""
from dash import Dash
EXTERNAL_STYLESHEETS = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
MATHJAX_SCRIPT = 'https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.5/MathJax.js?config=TeX-MML-AM_CHTML'

app = Dash(__name__, external_stylesheets=EXTERNAL_STYLESHEETS, external_scripts=[MATHJAX_SCRIPT], suppress_callback_exceptions=True)
server = app.server

from layout import layout
app.layout = layout

import callbacks

if __name__ == '__main__':
    app.run_server(host='0.0.0.0', port=7860)
""")

# Prepend `from app import app` to callbacks.py
with open(r"d:\Skripsi\my\web\skripsiv2\callbacks.py", "r", encoding='utf-8') as f:
    cb_data = f.read()

# Make sure we don't have circular imports messing up due to double Dash initialization.
with open(r"d:\Skripsi\my\web\skripsiv2\callbacks.py", "w", encoding='utf-8') as f:
    f.write("from app import app\n")
    f.write(cb_data)

print("Modularization script written. Check files.")
