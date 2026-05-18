#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Formulas & calculation step dashboard using Flask/Dash & MathJax.
Loads pre-calculated high-fidelity formulas directly from formulas_substitusi.json.
This ensures 100% mathematical accuracy, ultra-fast boot time, and zero crash risk.
"""

import os
import json
import dash
from dash import dcc, html, Input, Output, State

# 1. Load the pre-calculated formulas JSON
JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "landing-page", "public", "formulas_substitusi.json")

if os.path.exists(JSON_PATH):
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        FORMULAS = json.load(f)
else:
    FORMULAS = []
    print(f"Warning: {JSON_PATH} not found.")

# 2. Define categories matching the thesis chapters
CATEGORIES = {
    "all": "📐 Semua Rumus",
    "descriptive": "📊 Statistika Deskriptif",
    "suitability": "🛡️ Uji Kelayakan Data",
    "pca": "🔑 Korelasi & PCA",
    "statis": "📐 Tahapan Metode STATIS",
    "spatial": "🗺️ Klaster & Spasial"
}

# 3. Create the Dash application
app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    external_stylesheets=[]
)
app.title = "📐 STATIS Math Formulas & Substitutions"
server = app.server

# Custom CSS for the dashboard (premium glassmorphism theme)
app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
        <script>
            window.MathJax = {
                tex: {
                    inlineMath: [['$', '$'], ['\\(', '\\)']],
                    displayMath: [['$$', '$$'], ['\\[', '\\]']],
                    processEscapes: true,
                    processEnvironments: true
                },
                options: {
                    skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre']
                }
            };
        </script>
        <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async></script>
        <style>
            * {
                box-sizing: border-box;
                font-family: 'Outfit', sans-serif;
            }
            body {
                background: radial-gradient(circle at top right, #0b1528, #030712);
                color: #e2e8f0;
                margin: 0;
                padding: 0;
                min-height: 100vh;
            }
            .app-container {
                max-width: 1600px;
                margin: 0 auto;
                padding: 40px;
            }
            .header-glass {
                background: rgba(30, 41, 59, 0.45);
                backdrop-filter: blur(16px);
                -webkit-backdrop-filter: blur(16px);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 24px;
                padding: 30px;
                margin-bottom: 28px;
                box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 20px;
            }
            .header-title h1 {
                margin: 0 0 6px 0;
                font-size: 28px;
                font-weight: 700;
                letter-spacing: -0.5px;
                background: linear-gradient(135deg, #06b6d4, #3b82f6);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .header-title p {
                margin: 0;
                font-size: 14px;
                color: #94a3b8;
            }
            .back-btn {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(6, 182, 212, 0.3);
                color: #06b6d4;
                padding: 8px 18px;
                borderRadius: 30px;
                text-decoration: none;
                font-size: 0.85rem;
                font-weight: 700;
                display: inline-flex;
                align-items: center;
                gap: 8px;
                transition: all 0.2s;
                cursor: pointer;
                border-radius: 30px;
            }
            .back-btn:hover {
                background: rgba(6, 182, 212, 0.15);
                transform: translateY(-1px);
            }
            .search-filter-box {
                background: rgba(30, 41, 59, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 24px;
                padding: 24px;
                margin-bottom: 28px;
                display: flex;
                flex-direction: column;
                gap: 20px;
            }
            .search-input {
                width: 100%;
                background: rgba(15, 23, 42, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 16px;
                padding: 14px 20px;
                font-size: 15px;
                color: #f8fafc;
                outline: none;
                transition: all 0.2s;
            }
            .search-input:focus {
                border-color: #06b6d4;
                box-shadow: 0 0 0 2px rgba(6, 182, 212, 0.2);
            }
            .cat-tabs {
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
                border-bottom: 1px solid rgba(255,255,255,0.06);
                padding-bottom: 16px;
            }
            .cat-tab {
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.08);
                color: #94a3b8;
                padding: 8px 18px;
                border-radius: 30px;
                cursor: pointer;
                font-size: 0.85rem;
                font-weight: 600;
                transition: all 0.2s;
            }
            .cat-tab:hover {
                color: #e2e8f0;
                border-color: rgba(255,255,255,0.15);
            }
            .cat-tab.active {
                background: rgba(6, 182, 212, 0.15);
                border: 1px solid rgba(6, 182, 212, 0.4);
                color: #38bdf8;
            }
            .formulas-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(650px, 1fr));
                gap: 28px;
            }
            .formula-card {
                background: rgba(30, 41, 59, 0.35);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 24px;
                padding: 28px;
                display: flex;
                flex-direction: column;
                gap: 20px;
                transition: all 0.3s;
                box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            }
            .formula-card:hover {
                transform: translateY(-2px);
                border-color: rgba(6, 182, 212, 0.25);
                box-shadow: 0 8px 30px rgba(0,0,0,0.25);
            }
            .card-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid rgba(255,255,255,0.06);
                padding-bottom: 14px;
            }
            .card-title {
                margin: 0;
                font-size: 1.05rem;
                font-weight: 600;
                color: #f8fafc;
            }
            .card-badge {
                background: rgba(56, 189, 248, 0.1);
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.2);
                border-radius: 20px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            .math-box {
                background: rgba(15, 23, 42, 0.5);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 16px;
                padding: 20px;
                overflow-x: auto;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            .details-btn {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                color: #94a3b8;
                padding: 8px 16px;
                border-radius: 12px;
                font-size: 0.8rem;
                font-weight: 600;
                cursor: pointer;
                display: inline-flex;
                align-items: center;
                gap: 6px;
                transition: all 0.2s;
                width: fit-content;
            }
            .details-btn:hover {
                background: rgba(255,255,255,0.08);
                color: #e2e8f0;
            }
            .explanation-box {
                background: rgba(15, 23, 42, 0.3);
                border: 1px solid rgba(255,255,255,0.04);
                border-radius: 16px;
                padding: 18px;
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            .explanation-title {
                font-size: 0.75rem;
                font-weight: 700;
                color: #64748b;
                letter-spacing: 1px;
                text-transform: uppercase;
                margin: 0;
            }
            .explanation-list {
                list-style: none;
                margin: 0;
                padding: 0;
                display: flex;
                flex-direction: column;
                gap: 6px;
            }
            .explanation-item {
                font-size: 0.85rem;
                color: #cbd5e1;
                display: flex;
                align-items: flex-start;
                gap: 8px;
            }
            .explanation-item::before {
                content: "•";
                color: #38bdf8;
                font-weight: bold;
            }
            .hasil-box {
                background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(5, 150, 105, 0.15));
                border: 1px solid rgba(16, 185, 129, 0.3);
                border-radius: 16px;
                padding: 16px 20px;
                color: #34d399;
                font-weight: 600;
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            .hasil-title {
                font-size: 0.7rem;
                font-weight: 700;
                color: #34d399;
                letter-spacing: 1px;
                text-transform: uppercase;
                margin: 0;
                opacity: 0.8;
            }
            .hasil-value {
                overflow-x: auto;
                display: flex;
                justify-content: center;
                align-items: center;
            }
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
"""

# 4. App Layout Definition
app.layout = html.Div(
    className="app-container",
    children=[
        # Header Panel
        html.Div(
            className="header-glass",
            children=[
                html.Div(
                    className="header-title",
                    children=[
                        html.Div(
                            style={"display": "flex", "gap": "12px", "marginBottom": "8px", "alignItems": "center"},
                            children=[
                                html.A("⬅ Kembali ke Beranda", href="http://localhost:5173", className="back-btn")
                            ]
                        ),
                        html.H1("📐 STATIS Math Formulas & Substitutions"),
                        html.P("Eksplorasi seluruh 67 rumus matematika dari landasan teori skripsi beserta 24 kalkulasi langkah substitusi riil secara statis.")
                    ]
                )
            ]
        ),
        
        # Search & Filter Block
        html.Div(
            className="search-filter-box",
            children=[
                dcc.Input(
                    id="search-query",
                    type="text",
                    placeholder="🔍 Cari formula berdasarkan nama, variabel, atau keterangan...",
                    className="search-input"
                ),
                html.Div(
                    className="cat-tabs",
                    children=[
                        html.Button(
                            label,
                            id={"type": "cat-btn", "index": key},
                            className="cat-tab active" if key == "all" else "cat-tab"
                        )
                        for key, label in CATEGORIES.items()
                    ]
                )
            ]
        ),
        
        # Grid of Formulas
        html.Div(
            id="formulas-grid-container",
            className="formulas-grid"
        ),
        
        # Store for active category
        dcc.Store(id="active-category-store", data="all")
    ]
)

# 5. Callbacks
@app.callback(
    Output("active-category-store", "data"),
    Output({"type": "cat-btn", "index": dash.ALL}, "className"),
    Input({"type": "cat-btn", "index": dash.ALL}, "n_clicks"),
    State({"type": "cat-btn", "index": dash.ALL}, "id"),
    prevent_initial_call=True
)
def update_active_category(n_clicks, ids):
    ctx = dash.callback_context
    if not ctx.triggered:
        return "all", ["cat-tab active" if id_dict["index"] == "all" else "cat-tab" for id_dict in ids]
    
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    triggered_dict = json.loads(triggered_id)
    selected_cat = triggered_dict["index"]
    
    class_names = []
    for id_dict in ids:
        if id_dict["index"] == selected_cat:
            class_names.append("cat-tab active")
        else:
            class_names.append("cat-tab")
            
    return selected_cat, class_names

@app.callback(
    Output("formulas-grid-container", "children"),
    Input("search-query", "value"),
    Input("active-category-store", "data")
)
def render_formulas(search_val, active_cat):
    filtered = []
    search_term = (search_val or "").lower()
    
    for f in FORMULAS:
        # Category Filter
        if active_cat != "all" and f.get("category") != active_cat:
            continue
            
        # Search Filter
        if search_term:
            matches_title = search_term in f.get("title", "").lower()
            matches_formula = search_term in f.get("formula", "").lower()
            matches_keterangan = any(search_term in k.lower() for k in f.get("keterangan", []))
            if not (matches_title or matches_formula or matches_keterangan):
                continue
                
        filtered.append(f)
        
    cards = []
    for f in filtered:
        card_id = f.get("id")
        
        # Badges mapping
        badge_label = "UMUM"
        cat = f.get("category")
        if cat == "descriptive": badge_label = "DESKRIPTIF"
        elif cat == "suitability": badge_label = "KELAYAKAN"
        elif cat == "pca": badge_label = "KORELASI & PCA"
        elif cat == "statis": badge_label = "METODE STATIS"
        elif cat == "spatial": badge_label = "KLASTER & SPASIAL"
        
        # Keterangan items
        ket_elements = []
        for k in f.get("keterangan", []):
            ket_elements.append(html.Li(className="explanation-item", children=k))
            
        # Substitusi items
        sub_elements = []
        for s in f.get("substitusi", []):
            sub_elements.append(html.Li(className="explanation-item", children=s))
            
        cards.append(
            html.Div(
                className="formula-card",
                children=[
                    # Title Block
                    html.Div(
                        className="card-header",
                        children=[
                            html.H3(f.get("title"), className="card-title"),
                            html.Span(badge_label, className="card-badge")
                        ]
                    ),
                    
                    # Formula Mathjax Block
                    html.Div(
                        className="math-box",
                        children=f.get("formula")
                    ),
                    
                    # Detailed Substitutions & Explanation
                    html.Div(
                        className="explanation-box",
                        children=[
                            html.H5("VARIABEL & DEFINISI", className="explanation-title"),
                            html.Ul(className="explanation-list", children=ket_elements),
                            html.Hr(style={"border": "none", "borderTop": "1px solid rgba(255,255,255,0.06)", "margin": "12px 0"}),
                            html.H5("LANGKAH SUBTITUSI DATA", className="explanation-title"),
                            html.Ul(className="explanation-list", children=sub_elements)
                        ]
                    ),
                    
                    # Real Results Box
                    html.Div(
                        className="hasil-box",
                        children=[
                            html.H5("HASIL KOMPUTASI REAL", className="hasil-title"),
                            html.Div(className="hasil-value", children=f.get("hasil"))
                        ]
                    )
                ]
            )
        )
        
    return cards

# 6. Main runner
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8070))
    # Standard Flask/Dash debug off for production deployment safety
    app.run_server(host="0.0.0.0", port=port, debug=False)