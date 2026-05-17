# -*- coding: utf-8 -*-
import os
import re
import base64
import glob
from flask import send_from_directory
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, callback_context

# Initialize Dash application with premium theme and Google Fonts
EXTERNAL_STYLESHEETS = [
    'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap'
]

app = Dash(
    __name__,
    external_stylesheets=EXTERNAL_STYLESHEETS,
    suppress_callback_exceptions=True,
    title="STATIS Scenario Comparison Dashboard"
)
server = app.server

# Project absolute base path
BASE_DIR = os.path.abspath("d:/Skripsi/my")

# Custom Flask route to dynamically and securely serve local PNG images
@server.route('/serve_file/<path:filepath>')
def serve_file(filepath):
    # Normalize path separators
    filepath = filepath.replace('\\', '/')
    target_path = os.path.abspath(os.path.join(BASE_DIR, filepath))
    
    # Security check: Ensure requested file is within the project directory and is a file
    if not target_path.startswith(BASE_DIR):
        return "Unauthorized Access", 403
        
    if os.path.exists(target_path) and os.path.isfile(target_path):
        directory = os.path.dirname(target_path)
        filename = os.path.basename(target_path)
        return send_from_directory(directory, filename)
        
    return "File Not Found", 404


def clean_latex_text(text):
    r"""
    Cleans up LaTeX markup from captions and table cells, translating mathematical
    symbols (\mu, \sigma, \rightarrow, etc.) into beautiful, clear web-safe Unicode.
    """
    text = text.strip()
    if not text:
        return ""
        
    # 1. Clean up known LaTeX commands with balanced braces
    # E.g. \makecell{...}, \textbf{...}, \textit{...}, \bo{...}, \mathbf{...}, \makebox{...}, \text{...}
    commands = ['\\makecell', '\\textbf', '\\textit', '\\bo', '\\mathbf', '\\makebox', '\\text']
    for cmd in commands:
        while cmd + '{' in text:
            idx = text.find(cmd + '{')
            brace_start = idx + len(cmd + '{')
            
            # Balance braces
            brace_count = 1
            brace_end = -1
            for i in range(brace_start, len(text)):
                if text[i] == '{':
                    brace_count += 1
                elif text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        brace_end = i
                        break
            if brace_end != -1:
                inner = text[brace_start:brace_end]
                text = text[:idx] + inner + text[brace_end+1:]
            else:
                text = text.replace(cmd + '{', '').replace('}', '')
                
    # 2. Map LaTeX math symbols to beautiful Unicode characters
    latex_symbols = {
        '\\rightarrow': '→',
        '\\to': '→',
        '\\mu': 'μ',
        '\\sigma': 'σ',
        '\\alpha': 'α',
        '\\beta': 'β',
        '\\gamma': 'γ',
        '\\lambda': 'λ',
        '\\times': '×',
        '\\in': '∈',
        '\\approx': '≈',
        '\\neq': '≠',
    }
    for sym, uni in latex_symbols.items():
        text = text.replace(sym + ' ', uni).replace(sym, uni)
        
    # 3. Strip structural/positioning/styling LaTeX decorators
    text = re.sub(r'\\bfseries\s*', '', text)
    text = re.sub(r'\\itshape\s*', '', text)
    text = re.sub(r'\\small\s*', '', text)
    text = re.sub(r'\\large\s*', '', text)
    text = re.sub(r'\\centering\s*', '', text)
    text = re.sub(r'\\makebox\[[^\]]*\]', '', text)
    text = re.sub(r'\\makeatletter.*$', '', text)
    text = re.sub(r'\\label\{[^\}]+\}', '', text)
    
    # 4. Handle subscripts and superscripts inside math mode
    # E.g. _{2020} -> _2020, ^{2} -> ^2, ^{(2)} -> ^(2)
    text = re.sub(r'\_\{([^\}]+)\}', r'_\1', text)
    text = re.sub(r'\^\{([^\}]+)\}', r'^\1', text)
    
    # 5. Remove math mode delimiters and raw brackets
    text = text.replace('\\(', '').replace('\\)', '')
    text = text.replace('$', '')
    text = text.replace('\\\\', ' ')
    
    # 6. Clean standard escape characters
    text = text.replace('\\_', '_')
    text = text.replace('\\%', '%')
    text = text.replace('\\$', '$')
    text = text.replace('\\&', '&')
    text = text.replace('\\', '')  # Remove any remaining stray backslashes
    
    return text.strip()


def parse_latex_table(filepath):
    r"""
    Parses standard LaTeX table (.tex) files and extracts captions,
    headers, and data rows using a robust brace-matching parser.
    """
    try:
        if not os.path.exists(filepath):
            return None
            
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract caption using brace-matching to perfectly resolve nested braces
        caption = os.path.basename(filepath)
        caption_idx = content.find('\\caption{')
        if caption_idx != -1:
            brace_start = caption_idx + len('\\caption{')
            brace_count = 1
            brace_end = -1
            for i in range(brace_start, len(content)):
                if content[i] == '{':
                    brace_count += 1
                elif content[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        brace_end = i
                        break
            if brace_end != -1:
                caption = content[brace_start:brace_end]
                
        # Clean caption text
        caption = clean_latex_text(caption)
        
        # Find where \begin{tabular} is
        start_idx = content.find('\\begin{tabular}')
        if start_idx == -1:
            return None
            
        # Find the column format braces after \begin{tabular}
        search_area = content[start_idx + len('\\begin{tabular}'):]
        
        # Skip optional positioning argument [pos] if present
        pos_match = re.match(r'^\s*\[.*?\]', search_area)
        if pos_match:
            search_area = search_area[pos_match.end():]
            
        brace_start = search_area.find('{')
        if brace_start == -1:
            return None
            
        # Track braces to find end of column specification (e.g. |p{4cm}|p{10cm}|)
        brace_count = 1
        brace_end = -1
        for idx in range(brace_start + 1, len(search_area)):
            char = search_area[idx]
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    brace_end = idx
                    break
                    
        if brace_end == -1:
            return None
            
        global_brace_end = start_idx + len('\\begin{tabular}') + (pos_match.end() if pos_match else 0) + brace_end
        
        # Find \end{tabular}
        end_idx = content.find('\\end{tabular}', start_idx)
        if end_idx == -1:
            return None
            
        table_body = content[global_brace_end + 1 : end_idx]
        
        # Parse rows
        rows = []
        for line in table_body.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('\\hline') or line.startswith('\\begin') or line.startswith('\\end'):
                continue
            if line.endswith('\\\\'):
                line = line[:-2].strip()
                
            # Temporarily replace LaTeX escaped ampersand \& to prevent incorrect column splitting
            temp_line = line.replace('\\&', '__AMP__')
            
            # Split columns by & (which are actual column separators now)
            cols = [c.strip() for c in temp_line.split('&')]
            
            # Clean up latex commands from each cell
            clean_cols = []
            for col in cols:
                col = col.replace('__AMP__', '\\&')
                clean_cols.append(clean_latex_text(col))
                
            rows.append(clean_cols)
            
        if not rows:
            return None
            
        headers = rows[0]
        data_rows = rows[1:]
        return {
            'caption': caption,
            'headers': headers,
            'data': data_rows
        }
    except Exception as e:
        print(f"Error parsing LaTeX table {filepath}: {e}")
        return None


# Global Premium CSS embedded directly
GLOBAL_CSS = """
body {
    background-color: #0F172A;
    color: #E2E8F0;
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    margin: 0;
    padding: 0;
}
.app-container {
    padding: 40px;
    max-width: 1600px;
    margin: 0 auto;
}
.header-glass {
    background: rgba(30, 41, 59, 0.45);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 24px;
    padding: 30px;
    margin-bottom: 40px;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.title-container h1 {
    margin: 0 0 6px 0;
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.5px;
    background: linear-gradient(135deg, #06B6D4, #3B82F6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.title-container p {
    margin: 0;
    font-size: 14px;
    color: #94A3B8;
}
.card {
    background: rgba(30, 41, 59, 0.3);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 20px;
    padding: 24px;
    margin-bottom: 30px;
    box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.15);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.card:hover {
    transform: translateY(-2px);
    border-color: rgba(6, 182, 212, 0.3);
    box-shadow: 0 12px 30px 0 rgba(6, 182, 212, 0.1);
}
.section-title {
    font-size: 18px;
    font-weight: 600;
    color: #F8FAFC;
    margin-top: 0;
    margin-bottom: 20px;
    border-left: 4px solid #06B6D4;
    padding-left: 12px;
}
.badge {
    background: rgba(6, 182, 212, 0.1);
    color: #06B6D4;
    border: 1px solid rgba(6, 182, 212, 0.2);
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 600;
    display: inline-block;
}
.premium-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
    font-size: 13.5px;
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.05);
}
.premium-table th {
    background-color: rgba(15, 23, 42, 0.6);
    color: #06B6D4;
    font-weight: 600;
    text-align: left;
    padding: 12px 16px;
    border-bottom: 2px solid rgba(255, 255, 255, 0.1);
}
.premium-table td {
    padding: 10px 16px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    color: #E2E8F0;
}
.premium-table tr:hover {
    background-color: rgba(255, 255, 255, 0.03);
}
.grid-container {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(450px, 1fr));
    gap: 24px;
}
.side-by-side-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 30px;
}
.comparison-card-title {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding-bottom: 12px;
    margin-bottom: 16px;
}
.comparison-card-title h3 {
    margin: 0;
    font-size: 15px;
    font-weight: 600;
    color: #E2E8F0;
}
.img-container {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.05);
    background: rgba(15, 23, 42, 0.4);
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 250px;
    transition: all 0.3s;
}
.img-container img {
    max-width: 100%;
    height: auto;
    object-fit: contain;
    transition: transform 0.3s ease;
}
.img-container img:hover {
    transform: scale(1.03);
}
.placeholder-box {
    color: #64748B;
    font-size: 14px;
    text-align: center;
    padding: 40px;
    border: 2px dashed rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    width: 100%;
    box-sizing: border-box;
}
.dropdown-custom .Select-control {
    background-color: rgba(30, 41, 59, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px !important;
    color: #F8FAFC !important;
    height: 42px !important;
}
.dropdown-custom .Select-menu-outer {
    background-color: #1E293B !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px !important;
}
.dropdown-custom .Select-value-label {
    color: #F8FAFC !important;
}
.dropdown-custom .VirtualizedSelectOption {
    color: #E2E8F0 !important;
    background-color: transparent !important;
}
.dropdown-custom .VirtualizedSelectFocusedOption {
    background-color: rgba(6, 182, 212, 0.2) !important;
    color: #F8FAFC !important;
}
.tabs-custom .tab {
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    color: #94A3B8 !important;
    font-weight: 500 !important;
    padding: 12px 20px !important;
    font-size: 14px !important;
    transition: all 0.2s;
}
.tabs-custom .tab--selected {
    color: #06B6D4 !important;
    border-bottom: 2px solid #06B6D4 !important;
    font-weight: 600 !important;
}
/* Premium Scrollbar */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}
::-webkit-scrollbar-track {
    background: #0F172A;
}
::-webkit-scrollbar-thumb {
    background: #1E293B;
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
    background: #334155;
}
"""

# Custom HTML index template to inject our premium global styles
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            __GLOBAL_CSS__
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''.replace('__GLOBAL_CSS__', GLOBAL_CSS)

# App Layout
app.layout = html.Div([
    html.Div([
        
        # --- HEADER GLASS PANEL ---
        html.Div([
            html.Div([
                html.H1("STATIS Scenario Comparison Dashboard"),
                html.P("Compare statistical models, biplots, clustering maps, and data matrices side-by-side.")
            ], className="title-container"),
            
            # Selector for output folders
            html.Div([
                html.Label("Pilih Folder Output:", style={"fontWeight": "600", "fontSize": "13px", "color": "#94A3B8", "marginBottom": "6px", "display": "block"}),
                dcc.Dropdown(
                    id='folder-selector',
                    options=[
                        {'label': '📂 output_real (Data Skripsi Real)', 'value': 'output_real'},
                        {'label': '📂 output_sample (Data Contoh)', 'value': 'output_sample'},
                        {'label': '📂 output_app (Ekspor Aplikasi)', 'value': 'output_app'}
                    ],
                    value='output_real',
                    clearable=False,
                    className="dropdown-custom",
                    style={"width": "320px"}
                )
            ])
        ], className="header-glass"),
        
        # Alert for missing folder
        html.Div(id='missing-folder-alert'),
        
        # Dashboard Content
        html.Div(id='dashboard-content')
        
    ], className="app-container")
])


def render_html_table(parsed):
    """Renders a parsed dictionary as a premium looking HTML table."""
    if not parsed:
        return html.Div("Gagal parsing tabel.", className="placeholder-box")
        
    return html.Div([
        html.H5(parsed['caption'], style={"color": "#06B6D4", "fontSize": "14px", "fontWeight": "600", "marginBottom": "10px", "textAlign": "center"}),
        html.Table([
            html.Thead([
                html.Tr([html.Th(h) for h in parsed['headers']])
            ]),
            html.Tbody([
                html.Tr([html.Td(cell) for cell in row]) for row in parsed['data']
            ])
        ], className="premium-table")
    ], style={"overflowX": "auto", "width": "100%"})


@app.callback(
    [Output('missing-folder-alert', 'children'),
     Output('dashboard-content', 'children')],
    [Input('folder-selector', 'value')]
)
def update_dashboard(selected_folder):
    target_dir = os.path.join(BASE_DIR, selected_folder)
    
    # Check if folder exists
    if not os.path.exists(target_dir):
        alert = html.Div([
            html.H4("⚠️ Folder Tidak Ditemukan", style={"margin": "0 0 6px 0", "color": "#F43F5E"}),
            html.P(f"Direktori '{selected_folder}' belum dibuat atau tidak ditemukan di {target_dir}. "
                   "Folder ini biasanya akan terbuat secara otomatis saat Anda menjalankan ekspor dari dashboard utama web/app.py.",
                   style={"margin": "0"})
        ], style={
            "background": "rgba(244, 63, 94, 0.15)",
            "border": "1px solid rgba(244, 63, 94, 0.3)",
            "borderRadius": "16px",
            "padding": "20px",
            "color": "#FDA4AF",
            "marginBottom": "30px"
        })
        return alert, None
        
    alert = None
    
    # -----------------------------
    # 1. SCAN ROOT DIRECTORY FILES
    # -----------------------------
    root_files = os.listdir(target_dir)
    root_pngs = sorted([f for f in root_files if f.endswith('.png') and f.startswith('boxplot')])
    root_texs = sorted([f for f in root_files if f.endswith('.tex') and f.startswith('output_table')])
    
    # Render Descriptive & KMO tables in root
    root_tables_rendered = []
    for tex in root_texs:
        parsed = parse_latex_table(os.path.join(target_dir, tex))
        if parsed:
            root_tables_rendered.append(
                html.Div([
                    render_html_table(parsed)
                ], className="card", style={"padding": "20px"})
            )
            
    # Render Boxplots in root
    root_boxplots_rendered = []
    for png in root_pngs:
        filepath = f"{selected_folder}/{png}"
        root_boxplots_rendered.append(
            html.Div([
                html.H5(png.replace('_', ' ').replace('.png', '').upper(), style={"fontSize": "13px", "color": "#94A3B8", "marginBottom": "12px", "textAlign": "center"}),
                html.Div([
                    html.Img(src=f"/serve_file/{filepath}")
                ], className="img-container", style={"minHeight": "180px"})
            ], className="card", style={"padding": "16px"})
        )
        
    root_section = html.Div([
        html.H2("📊 Root Output Files (Global & Descriptive)", className="section-title"),
        
        # Tabs for Root Files
        dcc.Tabs(className="tabs-custom", parent_className="card", style={"padding": "0", "marginBottom": "24px"}, children=[
            dcc.Tab(label="📈 Boxplots (Distribusi Data)", className="tab", selected_className="tab--selected", children=[
                html.Div([
                    html.Div(root_boxplots_rendered, className="grid-container", style={"padding": "20px"})
                    if root_boxplots_rendered else html.Div("Tidak ada boxplot di folder root.", className="placeholder-box")
                ])
            ]),
            dcc.Tab(label="📋 Global & Descriptive Tables", className="tab", selected_className="tab--selected", children=[
                html.Div([
                    html.Div(root_tables_rendered, className="grid-container", style={"padding": "20px"})
                    if root_tables_rendered else html.Div("Tidak ada tabel di folder root.", className="placeholder-box")
                ])
            ])
        ])
    ])
    
    # ---------------------------------------------
    # 2. SCAN & ALIGN SCENARIO 1 & SCENARIO 2 FILES
    # ---------------------------------------------
    sc1_dir = os.path.join(target_dir, 'scenario1')
    sc2_dir = os.path.join(target_dir, 'scenario2')
    
    sc1_files = os.listdir(sc1_dir) if os.path.exists(sc1_dir) else []
    sc2_files = os.listdir(sc2_dir) if os.path.exists(sc2_dir) else []
    
    # Get unique basenames
    all_filenames = sorted(list(set(sc1_files + sc2_files)))
    
    # Filter files (ignore raw/backups/auxiliary files)
    ignored_patterns = ['.aux', '.log', '.bak', 'output_macros.tex', 'output_core_statis.tex']
    display_files = []
    for f in all_filenames:
        if any(f.endswith(p) for p in ignored_patterns):
            continue
        if f.endswith('.png') or f.endswith('.tex'):
            display_files.append(f)
            
    # Group scenario files into logical categories
    categories = {
        'core': {
            'label': '💎 Kompromis & Trajektori (Core)',
            'files': ['scree_plot.png', 'loading_plot.png', 'rv_heatmap.png', 'statis_trajectories.png', 
                      'statis_trajectories_highlight.png', 'compromise_map.png', 'compromise_biplot_matplotlib.png',
                      'variable_contribution.png', 'variable_cos2.png', 'beta_trajectory.png'],
            'elements': []
        },
        'yearly': {
            'label': '📅 Biplot per Tahun',
            'files': [], # dynamic matching for biplot_tahun_*.png
            'elements': []
        },
        'cluster': {
            'label': '🧩 Klastering & Dendrogram',
            'files': [], # dynamic matching for cluster_* and dendrogram_* and elbow_*
            'elements': []
        },
        'compare': {
            'label': '🔄 Perbandingan & Transisi',
            'files': [], # dynamic matching for compare_*
            'elements': []
        },
        'tables': {
            'label': '📋 Tabel Output (.tex)',
            'files': [], # all .tex files
            'elements': []
        }
    }
    
    # Sort files into categories dynamically
    for f in display_files:
        if f.endswith('.tex'):
            categories['tables']['files'].append(f)
        elif f in categories['core']['files']:
            pass # already hardcoded in list
        elif 'biplot_tahun' in f:
            categories['yearly']['files'].append(f)
        elif 'cluster' in f or 'dendrogram' in f or 'elbow' in f:
            categories['cluster']['files'].append(f)
        elif 'compare' in f:
            categories['compare']['files'].append(f)
        else:
            # Fallback to core if unknown plot
            categories['core']['files'].append(f)
            
    # Remove duplicates and sort
    for cat_key in categories:
        categories[cat_key]['files'] = sorted(list(set(categories[cat_key]['files'])))
        
    # Build comparison rendering for each file in each category
    for cat_key, cat_info in categories.items():
        for filename in cat_info['files']:
            
            sc1_path = os.path.join(sc1_dir, filename)
            sc2_path = os.path.join(sc2_dir, filename)
            
            has_sc1 = os.path.exists(sc1_path)
            has_sc2 = os.path.exists(sc2_path)
            
            # Scenario 1 Panel (Left)
            if has_sc1:
                if filename.endswith('.png'):
                    sc1_el = html.Div([
                        html.Div([
                            html.Img(src=f"/serve_file/{selected_folder}/scenario1/{filename}")
                        ], className="img-container")
                    ])
                else: # .tex table
                    parsed = parse_latex_table(sc1_path)
                    if parsed:
                        sc1_el = render_html_table(parsed)
                    else:
                        # Raw text fallback
                        with open(sc1_path, 'r', encoding='utf-8') as tf:
                            raw_txt = tf.read()
                        sc1_el = html.Pre(raw_txt, style={"fontSize": "11px", "color": "#94A3B8", "maxHeight": "300px", "overflow": "auto", "background": "#0F172A", "padding": "12px", "borderRadius": "8px"})
            else:
                sc1_el = html.Div([
                    html.Div("File tidak tersedia di Skenario 1", className="placeholder-box")
                ])
                
            # Scenario 2 Panel (Right)
            if has_sc2:
                if filename.endswith('.png'):
                    sc2_el = html.Div([
                        html.Div([
                            html.Img(src=f"/serve_file/{selected_folder}/scenario2/{filename}")
                        ], className="img-container")
                    ])
                else: # .tex table
                    parsed = parse_latex_table(sc2_path)
                    if parsed:
                        sc2_el = render_html_table(parsed)
                    else:
                        # Raw text fallback
                        with open(sc2_path, 'r', encoding='utf-8') as tf:
                            raw_txt = tf.read()
                        sc2_el = html.Pre(raw_txt, style={"fontSize": "11px", "color": "#94A3B8", "maxHeight": "300px", "overflow": "auto", "background": "#0F172A", "padding": "12px", "borderRadius": "8px"})
            else:
                sc2_el = html.Div([
                    html.Div("File tidak tersedia di Skenario 2", className="placeholder-box")
                ])
                
            # Create Card comparing Scenario 1 (Left) vs Scenario 2 (Right)
            title_text = filename.replace('_', ' ').replace('.png', '').replace('.tex', '').upper()
            is_tex_badge = html.Span("DATA MATRIX/TABLE", className="badge") if filename.endswith('.tex') else html.Span("VISUALIZATION PLOT", className="badge", style={"background": "rgba(59, 130, 246, 0.1)", "color": "#3B82F6", "borderColor": "rgba(59, 130, 246, 0.2)"})
            
            comparison_element = html.Div([
                # Card Title and Type Badge
                html.Div([
                    html.H3(title_text),
                    html.Div([
                        is_tex_badge,
                        html.Span(f"Filename: {filename}", style={"marginLeft": "12px", "fontSize": "12px", "color": "#64748B"})
                    ])
                ], className="comparison-card-title"),
                
                # Side by Side Grid
                html.Div([
                    # Skenario 1
                    html.Div([
                        html.Div("SKENARIO 1 (ACT KLASIK - HOST WILAYAH / MATRIKS W)", style={"fontWeight": "600", "color": "#06B6D4", "fontSize": "12px", "marginBottom": "12px", "letterSpacing": "0.5px"}),
                        sc1_el
                    ]),
                    # Skenario 2
                    html.Div([
                        html.Div("SKENARIO 2 (DUAL STATIS - HOST INDIKATOR / MATRIKS S)", style={"fontWeight": "600", "color": "#3B82F6", "fontSize": "12px", "marginBottom": "12px", "letterSpacing": "0.5px"}),
                        sc2_el
                    ])
                ], className="side-by-side-grid")
            ], className="card")
            
            cat_info['elements'].append(comparison_element)

    # Compile Scenario Tabs
    tabs_children = []
    for cat_key, cat_info in categories.items():
        tab_content = html.Div([
            html.Div(cat_info['elements'], style={"padding": "20px"})
            if cat_info['elements'] else html.Div("Tidak ada file dalam kategori ini.", className="placeholder-box")
        ])
        tabs_children.append(
            dcc.Tab(label=cat_info['label'], className="tab", selected_className="tab--selected", children=[tab_content])
        )
        
    scenario_section = html.Div([
        html.Div([
            html.H2("⚔️ Side-by-Side Scenario Comparison", className="section-title", style={"margin": "0"}),
            html.Span("Skenario 1 (Kiri) vs Skenario 2 (Kanan)", style={"fontSize": "13px", "color": "#94A3B8", "marginLeft": "16px"})
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "20px"}),
        
        dcc.Tabs(className="tabs-custom", parent_className="card", style={"padding": "0"}, children=tabs_children)
    ])
    
    return alert, html.Div([
        root_section,
        html.Div(style={"height": "30px"}),
        scenario_section
    ])


if __name__ == '__main__':
    # Runs on port 8060 to avoid any conflict with standard Dash web/app.py on port 8050
    print("Memulai STATIS Scenario Comparison Dashboard...")
    print("Dashboard akan berjalan di URL: http://127.0.0.1:8060/")
    app.run(debug=True, port=8060)
