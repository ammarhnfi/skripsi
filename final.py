# Import Library
import dash
from dash import Dash, dcc, html, Input, Output, State, dash, exceptions
# Hapus matplotlib.animation, karena tidak dipakai di app Dash
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
# import matplotlib.pyplot as plt # Tidak dipakai di app
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import base64

# Inisialisasi library (skaler dan pca akan di-fit di dalam callback)
pd.set_option('display.max_columns', None)
scaler = StandardScaler()
pca = PCA(n_components=2)

# -----------------------------
# Helper Functions (PCA Utils)
# -----------------------------
def get_rotation_angle_for_2d(pc_scores, loadings, baseline_type, baseline_name, kab_kota_list, loading_list):
    try:
        if baseline_type == 'loading':
            if 'features' in loadings.columns:
                sub = loadings[loadings['features'] == baseline_name]
                if not sub.empty:
                    vec = sub[['PC1', 'PC2']].iloc[0].values
                else:
                    return 0.0
            else:
                 return 0.0
        elif baseline_type == 'skor':
            if baseline_name in kab_kota_list:
                idx = kab_kota_list.index(baseline_name)
                if idx < len(pc_scores):
                    vec = pc_scores.iloc[idx].values[:2]
                else:
                    if 'Kabupaten/Kota' in pc_scores.columns:
                        sub = pc_scores[pc_scores['Kabupaten/Kota'] == baseline_name]
                        if not sub.empty:
                            vec = sub[['PC1','PC2']].iloc[0].values
                        else:
                            return 0.0
                    else:
                        return 0.0
            else:
                if 'Kabupaten/Kota' in pc_scores.columns:
                    sub = pc_scores[pc_scores['Kabupaten/Kota'] == baseline_name]
                    if not sub.empty:
                        vec = sub[['PC1','PC2']].iloc[0].values
                    else:
                        return 0.0
                else:
                    return 0.0
        else:
            return 0.0
    except Exception:
        return 0.0
    if np.allclose(vec[:2], 0):
        return 0.0
    return -np.arctan2(vec[1], vec[0])

def get_rotation_angle_for_3d(df_pc_scores_all_years, df_loadings_all_years, baseline_type, baseline_name, years_selected):
    try:
        angles = []
        for y in years_selected:
            if baseline_type == 'skor':
                sub = df_pc_scores_all_years[(df_pc_scores_all_years['Kabupaten/Kota'] == baseline_name) &
                                             (df_pc_scores_all_years['Tahun'] == y)]
                if sub.empty:
                    angles.append(0.0)
                else:
                    vec = sub[['PC1','PC2']].iloc[0].values
                    if np.allclose(vec[:2], 0):
                        angles.append(0.0)
                    else:
                        angles.append(-np.arctan2(vec[1], vec[0]))
            elif baseline_type == 'loading':
                sub = df_loadings_all_years[
                    (df_loadings_all_years['Tahun'] == y) &
                    (df_loadings_all_years['features'] == baseline_name)
                ]
                if sub.empty:
                    angles.append(0.0)
                else:
                    vec = sub[['PC1', 'PC2']].iloc[0].values
                    if np.allclose(vec[:2], 0):
                        angles.append(0.0)
                    else:
                        angles.append(-np.arctan2(vec[1], vec[0]))
            else:
                angles.append(0.0)
        return angles
    except Exception as e:
        print("Error in get_rotation_angle_for_3d:", e)
        return [0.0] * len(years_selected)

def rotate_df(df, angle, cols_to_rotate=['PC1','PC2']):
    df_rot = df.copy()
    if isinstance(angle, (list, tuple, np.ndarray)):
        if len(angle) == 1:
            angle = float(angle[0])
        else:
            raise ValueError("rotate_df expects scalar angle for full-DataFrame rotation")

    cols_exist = [c for c in cols_to_rotate if c in df_rot.columns]
    if len(cols_exist) < 2:
        return df_rot

    a = float(angle)
    R = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    
    vals = df_rot.loc[:, cols_exist].values
    rotated = vals.dot(R.T)
    df_rot.loc[:, cols_exist] = rotated
    return df_rot

# -----------------------------
# Helper: run_statis function
# -----------------------------
STATS_SECTION_TITLE = html.H3(id='statis-section-title', style={'marginTop':'40px'})

def run_statis(uploaded_content_string, selected_vars, sheet_names):
    if uploaded_content_string is None:
        raise Exception("File STATIS belum di-upload.")
        
    try:
        content_type, content_string = uploaded_content_string.split(',')
        decoded = base64.b64decode(content_string)
        excel_file_stream = io.BytesIO(decoded)
    except Exception as e:
         raise Exception(f"Error decoding file: {e}")
         
    tables = []
    try:
        for s in sheet_names: 
            excel_file_stream.seek(0) 
            df_s = pd.read_excel(excel_file_stream, sheet_name=s).set_index("Kabupaten/Kota")
            vars_in_sheet = [v for v in selected_vars if v in df_s.columns]
            if not vars_in_sheet:
                continue
            tables.append(df_s[vars_in_sheet].copy())
    except Exception as e:
         raise Exception(f"Error saat membaca file Excel: {e}. Pastikan sheet {sheet_names} ada.")

    if not tables:
        raise Exception("Tidak ada data STATIS yang bisa diproses (cek nama variabel/sheets).")

    if not all(tables[0].index.equals(t.index) for t in tables):
        common = tables[0].index
        for t in tables:
            common = common.intersection(t.index)
        tables = [t.loc[common].copy() for t in tables]

    obs_labels = tables[0].index.tolist()
    selected_vars_final = tables[0].columns.tolist() 
    n = len(obs_labels)
    k = len(tables)

    scaler_statis = StandardScaler()
    tables_std = []
    for t in tables:
        arr = t.values.astype(float)
        arr_scaled = scaler_statis.fit_transform(arr)
        tables_std.append(pd.DataFrame(arr_scaled, index=t.index, columns=t.columns))

    Ws = []
    for df in tables_std:
        Xc = df - df.mean()
        W = Xc.values @ Xc.values.T
        Ws.append(W)

    R = np.zeros((k,k))
    for i in range(k):
        for j in range(k):
            num = np.trace(Ws[i].T @ Ws[j])
            den = np.sqrt(np.trace(Ws[i].T @ Ws[i]) * np.trace(Ws[j].T @ Ws[j]))
            R[i,j] = 0.0 if den == 0 else num/den

    vals_R, vecs_R = np.linalg.eig(R)
    vals_R = np.real(vals_R)
    vecs_R = np.real(vecs_R)
    idx = np.argsort(vals_R)[::-1]
    vecs_R = vecs_R[:, idx]
    p1 = vecs_R[:,0]
    if p1.sum() < 0:
        p1 = -p1
    alphas = p1 / p1.sum()

    Wc = np.zeros_like(Ws[0])
    for a, W in zip(alphas, Ws):
        Wc += a * W

    eig_vals_c, eig_vecs_c = np.linalg.eig(Wc)
    eig_vals_c = np.real(eig_vals_c)
    eig_vecs_c = np.real(eig_vecs_c)
    idxc = np.argsort(eig_vals_c)[::-1]
    eig_vals_c = eig_vals_c[idxc]
    eig_vecs_c = eig_vecs_c[:, idxc]
    
    sq = np.sqrt(np.clip(eig_vals_c[:2], a_min=0, a_max=None))
    scores = eig_vecs_c[:, :2] * sq

    var_means = pd.DataFrame(index=obs_labels, columns=selected_vars_final, dtype=float)
    for i, var in enumerate(selected_vars_final):
        arrs = [t[var].values for t in tables_std]
        var_means[var] = np.mean(np.stack(arrs, axis=1), axis=1)

    loadings = []
    for var in selected_vars_final:
        x = var_means[var].values
        if np.allclose(x, 0):
            cx, cy = 0.0, 0.0
        else:
            cx = np.corrcoef(x, scores[:,0])[0,1] if np.std(x) != 0 and np.std(scores[:,0]) != 0 else 0.0
            cy = np.corrcoef(x, scores[:,1])[0,1] if np.std(x) != 0 and np.std(scores[:,1]) != 0 else 0.0
            cx = 0.0 if np.isnan(cx) else cx
            cy = 0.0 if np.isnan(cy) else cy
        loadings.append([cx, cy])
    loadings = np.array(loadings)

    per_year_coords = {}
    for year, dfstd in zip(sheet_names, tables_std):
        coords = dfstd.values @ loadings
        per_year_coords[year] = coords 

    return {
        'R': R,
        'alphas': alphas,
        'eig_vals_c': eig_vals_c,
        'scores': scores,
        'obs_labels': obs_labels,
        'selected_vars': selected_vars_final,
        'loadings': loadings,
        'per_year_coords': per_year_coords
    }

# -----------------------------
# Plot helpers (plotly)
# -----------------------------
def fig_interstructure(R, years):
    fig = px.imshow(R, text_auto=True, x=years, y=years, color_continuous_scale='Viridis',
                    title="Interstructure matrix (RV-like) — similarity between years")
    fig.update_layout(margin=dict(t=40,l=40,r=40,b=40))
    return fig

def fig_compromise(scores, obs_labels, eig_vals_c):
    df = pd.DataFrame(scores, columns=['Comp1','Comp2'])
    df['label'] = obs_labels
    inertia1 = eig_vals_c[0]/eig_vals_c.sum()*100 if eig_vals_c.sum()!=0 else 0
    inertia2 = eig_vals_c[1]/eig_vals_c.sum()*100 if eig_vals_c.sum()!=0 else 0
    fig = px.scatter(df, x='Comp1', y='Comp2', text='label',
                     title=f'Compromise Map — PC1 ({inertia1:.1f}%) vs PC2 ({inertia2:.1f}%)',
                     width=900, height=700)
    fig.update_traces(textposition='top center')
    fig.update_layout(xaxis=dict(zeroline=True), yaxis=dict(zeroline=True), margin=dict(t=60))
    return fig

def fig_biplot(scores, obs_labels, loadings, selected_vars, eig_vals_c):
    df_obs = pd.DataFrame(scores, columns=['Comp1','Comp2'])
    df_obs['label'] = obs_labels
    inertia1 = eig_vals_c[0]/eig_vals_c.sum()*100 if eig_vals_c.sum()!=0 else 0
    inertia2 = eig_vals_c[1]/eig_vals_c.sum()*100 if eig_vals_c.sum()!=0 else 0
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_obs['Comp1'], y=df_obs['Comp2'], mode='markers+text',
                             text=df_obs['label'], textposition='top center',
                             marker=dict(size=8, color='blue'), name='Observations'))
    scale = max(df_obs[['Comp1','Comp2']].abs().max().max(), 1.0)
    load_disp = loadings * scale * 0.9
    for i, var in enumerate(selected_vars):
        x, y = load_disp[i,0], load_disp[i,1]
        fig.add_trace(go.Scatter(x=[0, x], y=[0, y], mode='lines+markers+text',
                                 marker=dict(size=2), line=dict(color='red'),
                                 text=[None, var], textposition='top center', name=f'Loading {var}'))
    fig.update_layout(title=f'Compromise Biplot — PC1 ({inertia1:.1f}%) vs PC2 ({inertia2:.1f}%)',
                      xaxis_title='Comp1', yaxis_title='Comp2', width=900, height=700,
                      showlegend=False)
    fig.update_xaxes(zeroline=True)
    fig.update_yaxes(zeroline=True)
    return fig

def fig_trajectory(per_year_coords, obs_labels, sheet_names):
    rows = []
    for year in sheet_names: 
        coords = per_year_coords.get(year) 
        if coords is None:
            continue
        for i, lab in enumerate(obs_labels):
            rows.append({'Tahun': int(year), 'Comp1': coords[i,0], 'Comp2': coords[i,1], 'label': lab})
    df = pd.DataFrame(rows)
    fig = px.line(df, x='Comp1', y='Comp2', color='label', markers=True,
                  title='Trajectories of observations across years (projected)',
                  width=900, height=700)
    fig.update_layout(showlegend=True)
    return fig

# -----------------------------
# START: App Layout
# -----------------------------
app = Dash(__name__, external_stylesheets=['https://codepen.io/chriddyp/pen/bWLwgP.css'])

# ** PENTING UNTUK DEPLOY **
server = app.server

app.layout = html.Div([
    dcc.Store(id='global-data-store'), 
    dcc.Store(id='pca-results-store'),
    
    html.H2('Dashboard Integrasi PCA Biplot Interaktif', style={'textAlign': 'center'}),
    
    html.Div(id='upload-container', children=[
        dcc.Upload(
            id='upload-data',
            children=html.Div([
                'Seret (Drag) atau ',
                html.A('Pilih File Excel Anda (.xlsx)')
            ]),
            style={
                'width': '90%', 'height': '60px', 'lineHeight': '60px',
                'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
                'textAlign': 'center', 'margin': '10px auto'
            },
            multiple=False
        ),
        html.Div(id='output-data-upload')
    ]),

    html.Div(id='main-content', style={'display': 'none'}, children=[
        html.Div(className='row', children=[
            html.Div(className='three columns', children=[
                html.Label('Tipe Visualisasi:'),
                dcc.RadioItems(id='vis-type-radio-final',
                               options=[{'label': '2D','value':'2d'},{'label':'3D','value':'3d'},{'label':'Keduanya','value':'both'}],
                               value='both', labelStyle={'display':'block'}),
                
                html.Br(),
                html.Label('Pilih Variabel PCA (dan STATIS):'),
                dcc.Dropdown(
                    id='variable-dropdown-final',
                    options=[], value=[], 
                    multi=True,
                    placeholder="Pilih variabel..."
                )
            ]),
            html.Div(className='three columns', children=[
                html.Label('Kontrol Plot 2D:'),
                dcc.Dropdown(id='year-dropdown-2d-final', options=[], value=None),
                dcc.RadioItems(id='baseline-type-radio-2d-final',
                               options=[{'label':'Variabel (Loading)','value':'loading'},{'label':'Kab/Kota (Skor)','value':'skor'}],
                               value='loading', labelStyle={'display':'inline-block','margin-right':'10px'}),
                dcc.Dropdown(id='baseline-name-dropdown-2d-final', options=[], value=None)
            ]),
            html.Div(className='three columns', children=[
                html.Label('Filter Tahun untuk Plot 3D:'),
                dcc.Checklist(id='year-checklist-3d-final', options=[], value=[], labelStyle={'display':'block'}),
                html.Br(),
                html.Label('Tahun Dicerminkan (3D, terhadap PC2=0):'),
                dcc.Checklist(id='mirror-year-checklist-3d-final', options=[], value=[], labelStyle={'display':'block'}),
                html.Br(),
                html.Label('Baseline 3D:'),
                dcc.RadioItems(id='baseline-type-radio-3d-final',
                               options=[{'label':'Variabel (Loading)','value':'loading'},{'label':'Kab/Kota (Skor)','value':'skor'}],
                               value='loading', labelStyle={'display':'inline-block','margin-right':'10px'}),
                dcc.Dropdown(id='baseline-name-dropdown-3d-final', options=[], value=None)
            ]),
            html.Div(className='three columns', children=[
                html.Label('Trajektori (Kab/Kota atau Variabel):'),
                dcc.Dropdown(id='trajectory-dropdown-final', options=[], multi=True),
                html.Br(),
                html.Label('Scope Trajektori:'),
                dcc.RadioItems(id='trajectory-scope-final',
                               options=[{'label':'2D saja','value':'2d'},{'label':'3D saja','value':'3d'},{'label':'Keduanya','value':'both'}],
                               value='both', labelStyle={'display':'block'})
            ]),
            html.Div(className='three columns', children=[
                html.Label('Scope Vektor Loading:'),
                dcc.RadioItems(
                    id='loading-vector-scope-final',
                    options=[
                        {'label':'Tidak ditampilkan','value':'none'},
                        {'label':'2D saja','value':'2d'},
                        {'label':'3D saja','value':'3d'},
                        {'label':'Keduanya','value':'both'}
                    ],
                    value='both', labelStyle={'display':'block'}
                )
            ])
        ]),
        html.Hr(),
        dcc.Loading(id='loading-main-graphs', type='circle', children=[
            html.Div(id='graph-container-final')
        ]),
        html.Hr(),
        
        # --- Blok STATIS ---
        html.Div([
            STATS_SECTION_TITLE, 
            html.P("Analisis STATIS akan dijalankan menggunakan variabel yang dipilih di dropdown 'Pilih Variabel PCA (dan STATIS)' di atas."),
            html.Div([
                html.Button("Run STATIS", id="run-statis-btn", n_clicks=0, style={"backgroundColor":"#007ACC","color":"white"})
            ], style={"marginTop":"6px"}),
            html.Br(),
            html.Label("Pilih visualisasi:"),
            dcc.Dropdown(
                id='statis-vis-type',
                options=[
                    {'label':'Interstructure (Heatmap)','value':'interstructure'},
                    {'label':'Compromise map','value':'compromise'},
                    {'label':'Compromise biplot (variabel)','value':'biplot'},
                    {'label':'Trajectories per daerah','value':'trajectory'}
                ],
                value='compromise',
                clearable=False
            ),
            html.Br(),
            dcc.Loading(id='loading-statis', type='circle', children=[
                dcc.Graph(id='statis-graph', style={'height': '700px'})
            ]),
            html.Div(id='statis-summary', style={'whiteSpace':'pre-wrap', 'marginTop':'12px', 'fontFamily':'monospace'})
        ], style={'padding':'12px', 'border':'1px solid #ddd', 'borderRadius':'6px', 'marginBottom':'30px'})
    ])
])

# --------------------------------------------------
# ** CALLBACK 1: File Upload & Preprocessing (Sel 2-6) **
# --------------------------------------------------
@app.callback(
    Output('global-data-store', 'data'),
    Output('main-content', 'style'),
    Output('output-data-upload', 'children'),
    Output('upload-container', 'style'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    prevent_initial_call=True 
)
def process_uploaded_file(contents, filename):
    if contents is None:
        return dash.no_update, {'display': 'none'}, "Silakan upload file.", {'display': 'block'}

    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        excel_file_stream = io.BytesIO(decoded)
        all_sheets_dict = pd.read_excel(excel_file_stream, sheet_name=None)
        
        all_data = []
        sheet_names_final = [] 
        
        for sheet_name, df_year in all_sheets_dict.items():
            try:
                year_int = int(sheet_name)
                df_year['Tahun'] = year_int
                all_data.append(df_year)
                sheet_names_final.append(sheet_name) 
            except ValueError:
                pass 

        if not all_data:
            raise Exception("File Excel tidak mengandung sheet dengan nama tahun (misal: '2020', '2021').")

        df_long = pd.concat(all_data, ignore_index=True)
        df_wide = df_long.pivot(index=['Provinsi', 'Kabupaten/Kota'], columns='Tahun')
        df_wide.columns = [f'{col[0]}_{col[1]}' for col in df_wide.columns]
        df_wide = df_wide.reset_index()

        df = df_wide
        numerical_cols_raw = df.columns[2:]
        for col in numerical_cols_raw:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False).str.replace(' ', '')
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        kolom_dihapus = df.columns[df.isnull().any()].tolist()
        df.drop(columns=kolom_dihapus, inplace=True)
        
        years_final = sorted(list(set([int(col.split('_')[-1]) for col in df.columns if col.split('_')[-1].isdigit()])))
        base_features_all = sorted(list(set([col.rsplit('_', 1)[0] for col in df.columns[2:]])))
        
        fitur_tidak_lengkap = []
        for feature in base_features_all:
            kolom_tahunan = [f'{feature}_{year}' for year in years_final]
            if not all(col in df.columns for col in kolom_tahunan):
                fitur_tidak_lengkap.append(feature)

        if fitur_tidak_lengkap:
            kolom_untuk_dihapus = []
            for feature in fitur_tidak_lengkap:
                kolom_terkait = [col for col in df.columns if col.startswith(feature)]
                kolom_untuk_dihapus.extend(kolom_terkait)
            df.drop(columns=kolom_untuk_dihapus, inplace=True, errors='ignore')
        
        base_features_final = sorted(list(set([col.rsplit('_', 1)[0] for col in df.columns[2:]])))
        kab_kota_names_final = df['Kabupaten/Kota'].tolist()
        prov_names_final = df['Provinsi'].tolist()
        
        store_data = {
            'df_wide_json': df.to_json(orient='split'),
            'base_features': base_features_final,
            'kab_kota_names': kab_kota_names_final,
            'prov_names': prov_names_final,
            'years': years_final, 
            'sheet_names': sheet_names_final 
        }
        
        return store_data, {'display': 'block'}, html.Div(f"Sukses memproses: {filename}"), {'display': 'none'}

    except Exception as e:
        return None, {'display': 'none'}, html.Div(f"Error memproses file: {e}"), {'display': 'block'}


# --------------------------------------------------
# ** CALLBACK 2: Update Dropdown (Tahun, Variabel, Trajektori) **
# --------------------------------------------------
@app.callback(
    Output('variable-dropdown-final', 'options'),
    Output('variable-dropdown-final', 'value'),
    Output('trajectory-dropdown-final', 'options'),
    Output('year-dropdown-2d-final', 'options'),
    Output('year-dropdown-2d-final', 'value'),
    Output('year-checklist-3d-final', 'options'),
    Output('year-checklist-3d-final', 'value'),
    Output('mirror-year-checklist-3d-final', 'options'),
    Output('statis-section-title', 'children'), 
    Input('global-data-store', 'data')
)
def update_all_dropdowns(global_data):
    if global_data is None:
        raise exceptions.PreventUpdate

    base_features = global_data['base_features']
    kab_kota_names = global_data['kab_kota_names']
    years = global_data['years']
    sheet_names = global_data['sheet_names'] 
    
    var_opts = [{'label': f, 'value': f} for f in base_features]
    var_val = base_features
    
    traj_opts = ([{'label': f'(Kab/Kota) {name}', 'value': f'skor_{name}'} for name in kab_kota_names] +
                 [{'label': f'(Variabel) {name}', 'value': f'loading_{name}'} for name in base_features])
    
    year_opts = [{'label': str(y), 'value': y} for y in years]
    year_val_2d = years[0] if years else None
    year_val_3d = years
    mirror_opts = [{'label': str(y), 'value': y} for y in years]
    
    statis_title = f"STATIS Analysis ({min(sheet_names)}–{max(sheet_names)})"
    
    return var_opts, var_val, traj_opts, year_opts, year_val_2d, year_opts, year_val_3d, mirror_opts, statis_title

# --------------------------------------------------
# ** CALLBACK 3: Hitung Ulang PCA (Sel 7) **
# --------------------------------------------------
@app.callback(
    Output('pca-results-store', 'data'),
    Input('variable-dropdown-final', 'value'),
    State('global-data-store', 'data')
)
def update_pca_results(selected_features, global_data):
    if global_data is None or not selected_features:
        raise dash.exceptions.PreventUpdate

    df = pd.read_json(global_data['df_wide_json'], orient='split')
    kab_kota_names = global_data['kab_kota_names']
    prov_names = global_data['prov_names']
    years = global_data['years']

    results_dynamic = {}
    pc_score_list_dynamic = []
    loading_list_dynamic = []
        
    for year in years:
        year_cols = [f'{feat}_{year}' for feat in selected_features if f'{feat}_{year}' in df.columns]
        
        if not year_cols:
            continue
            
        df_year = df[year_cols]
        
        scaled_data = scaler.fit_transform(df_year)
        df_pc = pd.DataFrame(pca.fit_transform(scaled_data), columns=['PC1', 'PC2'])
        
        current_base_features = [col.rsplit('_', 1)[0] for col in year_cols]
        df_load = pd.DataFrame(pca.components_.T, columns=['PC1', 'PC2'])
        
        scalePC1 = 1.0 / (df_pc['PC1'].max() - df_pc['PC1'].min()) if (df_pc['PC1'].max() - df_pc['PC1'].min()) != 0 else 1.0
        scalePC2 = 1.0 / (df_pc['PC2'].max() - df_pc['PC2'].min()) if (df_pc['PC2'].max() - df_pc['PC2'].min()) != 0 else 1.0
        df_pc['PC1'] = df_pc['PC1'] * scalePC1
        df_pc['PC2'] = df_pc['PC2'] * scalePC2
        
        df_pc['Kabupaten/Kota'] = kab_kota_names
        df_pc['Provinsi'] = prov_names
        df_pc['Tahun'] = year
        pc_score_list_dynamic.append(df_pc)
        
        df_load['features'] = current_base_features 
        df_load['Tahun'] = year
        loading_list_dynamic.append(df_load)
        
        results_dynamic[year] = {
            'df': df_year,
            'prov': prov_names,
            'kab_kota': kab_kota_names,
            'pc_scores': df_pc,
            'loadings': df_load,
            'features': current_base_features, 
            'scalePC1': scalePC1,
            'scalePC2': scalePC2
        }

    if not results_dynamic:
         raise dash.exceptions.PreventUpdate

    df_pc_scores_dynamic = pd.concat(pc_score_list_dynamic, ignore_index=True)
    df_loadings_dynamic = pd.concat(loading_list_dynamic, ignore_index=True)

    results_json = {
        y: {k: v.to_json(orient='split') if isinstance(v, pd.DataFrame) else v
            for k, v in r.items()}
        for y, r in results_dynamic.items()
    }
    
    pc_scores_json = df_pc_scores_dynamic.to_json(orient='split')
    loadings_json = df_loadings_dynamic.to_json(orient='split')
    
    return {
        'results': results_json,
        'pc_scores': pc_scores_json,
        'loadings': loadings_json,
        'base_features': selected_features 
    }


# --------------------------------------------------
# ** CALLBACKS 4 & 5: Update Baseline Dropdowns **
# --------------------------------------------------
@app.callback(
    Output('baseline-name-dropdown-2d-final', 'options'),
    Output('baseline-name-dropdown-2d-final', 'value'),
    Input('pca-results-store', 'data'),
    Input('year-dropdown-2d-final', 'value'),
    Input('baseline-type-radio-2d-final', 'value')
)
def update_baseline_options_2d(pca_data, year, baseline_type):
    if pca_data is None:
        raise dash.exceptions.PreventUpdate
    results_dynamic = {}
    for y_str, r_json in pca_data['results'].items():
        y_int = int(y_str)
        r_dynamic = {}
        for k, v in r_json.items():
            if k in ['df', 'pc_scores', 'loadings']:
                r_dynamic[k] = pd.read_json(v, orient='split')
            else:
                r_dynamic[k] = v
        results_dynamic[y_int] = r_dynamic
    
    if year not in results_dynamic:
         return [], None 
        
    if baseline_type == 'loading':
        opts = results_dynamic[year]['features'] 
    else:
        opts = results_dynamic[year]['kab_kota']
        
    options = [{'label': str(o), 'value': o} for o in opts]
    return options, (options[0]['value'] if options else None)


@app.callback(
    Output('baseline-name-dropdown-3d-final', 'options'),
    Output('baseline-name-dropdown-3d-final', 'value'),
    Input('pca-results-store', 'data'),
    Input('year-checklist-3d-final', 'value'),
    Input('baseline-type-radio-3d-final', 'value')
)
def update_baseline_options_3d(pca_data, years_selected, baseline_type):
    if pca_data is None or not years_selected:
        raise dash.exceptions.PreventUpdate
    results_dynamic = {}
    for y_str, r_json in pca_data['results'].items():
        y_int = int(y_str)
        r_dynamic = {}
        for k, v in r_json.items():
            if k in ['df', 'pc_scores', 'loadings']:
                r_dynamic[k] = pd.read_json(v, orient='split')
            else:
                r_dynamic[k] = v
        results_dynamic[y_int] = r_dynamic
    
    base_features_dynamic = pca_data['base_features']
    
    first_year = None
    for y in years_selected:
        if y in results_dynamic:
            first_year = y
            break
    if first_year is None:
        return [], None
    
    kab_kota_names_dynamic = results_dynamic[first_year]['kab_kota']
            
    if baseline_type == 'loading':
        opts = base_features_dynamic
    else:
        opts = kab_kota_names_dynamic
        
    options = [{'label': str(o), 'value': o} for o in opts]
    return options, (options[0]['value'] if options else None)

# --------------------------------------------------
# ** CALLBACK 6: Update Graphs (Main Plotting) **
# --------------------------------------------------
@app.callback(
    Output('graph-container-final', 'children'),
    Input('pca-results-store', 'data'),
    Input('vis-type-radio-final', 'value'),
    Input('year-dropdown-2d-final', 'value'),
    Input('baseline-type-radio-2d-final', 'value'),
    Input('baseline-name-dropdown-2d-final', 'value'),
    Input('year-checklist-3d-final', 'value'),
    Input('mirror-year-checklist-3d-final', 'value'),
    Input('baseline-type-radio-3d-final', 'value'),
    Input('baseline-name-dropdown-3d-final', 'value'),
    Input('trajectory-dropdown-final', 'value'),
    Input('trajectory-scope-final', 'value'),
    Input('loading-vector-scope-final', 'value')
)
def update_graphs_final(pca_data, vis_type, year_2d, baseline_type_2d, baseline_name_2d,
                        years_3d, mirror_years, baseline_type_3d, baseline_name_3d,
                        trajectory_selections, traj_scope, loading_scope):
    
    if pca_data is None:
        return html.Div("Menunggu data PCA selesai dihitung...")

    # Deserialize
    results = {}
    for y_str, r_json in pca_data['results'].items():
        y_int = int(y_str)
        r_dynamic = {}
        for k, v in r_json.items():
            if k in ['df', 'pc_scores', 'loadings'] and isinstance(v, str):
                r_dynamic[k] = pd.read_json(v, orient='split')
            else:
                r_dynamic[k] = v
        results[y_int] = r_dynamic
    
    df_pc_scores = pd.read_json(pca_data['pc_scores'], orient='split')
    df_loadings = pd.read_json(pca_data['loadings'], orient='split')
    base_features = pca_data['base_features']
    years_available = sorted(results.keys())
    
    if not years_available:
         return html.Div("Tidak ada data untuk ditampilkan (mungkin tidak ada variabel terpilih untuk tahun ini).")

    kab_kota_names = results[years_available[0]]['kab_kota']
    
    children = []

    # ------------------ 2D plot ------------------
    fig_2d = None
    if vis_type in ['2d','both']:
        if year_2d not in results:
             children.append(html.Div(f"Data untuk tahun {year_2d} tidak tersedia dengan variabel terpilih.", className='six columns' if vis_type=='both' else 'twelve columns'))
        else:
            pc_scores_orig = results[year_2d]['pc_scores'].copy().reset_index(drop=True)
            loadings_orig = results[year_2d]['loadings'].copy() 
            kab_list = results[year_2d]['kab_kota']
            loading_list = results[year_2d]['features'] 

            angle2d = get_rotation_angle_for_2d(pc_scores_orig, loadings_orig, baseline_type_2d, baseline_name_2d, kab_list, loading_list)
            pc_scores_rot = rotate_df(pc_scores_orig, angle2d, cols_to_rotate=['PC1','PC2'])
            loadings_rot = rotate_df(loadings_orig, angle2d, cols_to_rotate=['PC1','PC2']) 

            fig_2d = go.Figure()
            
            if 'PC1' in pc_scores_rot.columns and 'PC2' in pc_scores_rot.columns:
                fig_2d.add_trace(go.Scatter(x=pc_scores_rot['PC1'], y=pc_scores_rot['PC2'],
                                            mode='markers+text', text=kab_list, textposition='top center', name='Skor'))

            if loading_scope in ['2d','both'] and 'PC1' in loadings_rot.columns and 'PC2' in loadings_rot.columns:
                for idx, row in loadings_rot.iterrows():
                    x = row['PC1']
                    y = row['PC2']
                    label = row['features'] 
                    
                    fig_2d.add_shape(
                        type="line", x0=0, y0=0, x1=x, y1=y,
                        line=dict(color="red", width=1, dash="solid"), opacity=0.5
                    )
                    fig_2d.add_annotation(
                        x=x*1.1, y=y*1.1, text=f"<b>{label}</b>",
                        showarrow=False, font=dict(color="black", size=9)
                    )

            if trajectory_selections and traj_scope in ['2d','both']:
                for selection in trajectory_selections:
                    sel_type, sel_name = selection.split('_',1)
                    if sel_type == 'skor':
                        traj_data = df_pc_scores[(df_pc_scores['Kabupaten/Kota'] == sel_name)].sort_values('Tahun')
                        if not traj_data.empty:
                            rotated_traj = rotate_df(traj_data, angle2d)
                            fig_2d.add_trace(go.Scatter(x=rotated_traj['PC1'], y=rotated_traj['PC2'], mode='lines+markers', name=f'Trajektori {sel_name} (skor)'))
                    else:
                        traj_data = df_loadings[(df_loadings['features'] == sel_name)].sort_values('Tahun')
                        if not traj_data.empty:
                            rotated_traj = rotate_df(traj_data, angle2d)
                            fig_2d.add_trace(go.Scatter(x=rotated_traj['PC1'], y=rotated_traj['PC2'], mode='lines+markers', name=f'Trajektori {sel_name} (loading)'))

            fig_2d.update_layout(title=f'Biplot 2D - {year_2d} (Baseline: {baseline_name_2d})',
                                 xaxis=dict(title='PC1'), yaxis=dict(title='PC2', scaleanchor='x', scaleratio=1),
                                 height=600)

            children.append(html.Div(dcc.Graph(figure=fig_2d), className='six columns' if vis_type=='both' else 'twelve columns'))

    # ------------------ 3D plot ------------------
    fig_3d = None
    if vis_type in ['3d','both'] and years_3d:
        years_3d_filtered = [y for y in years_3d if y in years_available]
        if not years_3d_filtered:
            children.append(html.Div("Tidak ada data untuk tahun 3D yang dipilih.", className='six columns' if vis_type=='both' else 'twelve columns'))
        else:
            angle_3d = get_rotation_angle_for_3d(df_pc_scores, df_loadings, baseline_type_3d, baseline_name_3d, years_3d_filtered)
            
            if not isinstance(angle_3d, (list, np.ndarray)):
                angle_3d = [float(angle_3d)] * len(years_3d_filtered)
            elif len(angle_3d) != len(years_3d_filtered):
                angle_3d = [0.0] * len(years_3d_filtered)

            score_list = []
            for i, y in enumerate(years_3d_filtered):
                filtered_3d_y = df_pc_scores[df_pc_scores['Tahun'] == y].copy()
                if filtered_3d_y.empty:
                    continue
                
                rot = rotate_df(filtered_3d_y[['PC1','PC2']].reset_index(drop=True), angle_3d[i])
                filtered_3d_rot_y = rot.copy()
                filtered_3d_rot_y['Tahun'] = filtered_3d_y['Tahun'].values
                filtered_3d_rot_y['Kabupaten/Kota'] = filtered_3d_y['Kabupaten/Kota'].values
                score_list.append(filtered_3d_rot_y)

            if score_list:
                filtered_3d_rot = pd.concat(score_list, ignore_index=True)
            else:
                filtered_3d_rot = pd.DataFrame(columns=['Tahun','PC1','PC2','Kabupaten/Kota'])
            
            mask = filtered_3d_rot['Tahun'].isin(mirror_years)
            filtered_3d_rot.loc[mask, 'PC2'] = -filtered_3d_rot.loc[mask, 'PC2']
            
            fig_3d = px.scatter_3d(filtered_3d_rot, x='Tahun', y='PC1', z='PC2', color='Kabupaten/Kota',
                                   hover_data=['Kabupaten/Kota','Tahun'])

            if loading_scope in ['3d','both']:
                for i, year_for_load in enumerate(years_3d_filtered):
                    if year_for_load not in results:
                        continue
                    
                    load3d = results[year_for_load]['loadings'].copy()
                    load3d_rot = rotate_df(load3d, angle_3d[i], cols_to_rotate=['PC1','PC2']) 

                    if year_for_load in mirror_years:
                         load3d_rot['PC2'] = -load3d_rot['PC2']
                    
                    for idx, row in load3d_rot.iterrows():
                        x = row['PC1']
                        yval = row['PC2']
                        label = row['features'] 
                        
                        fig_3d.add_trace(go.Scatter3d(
                            x=[year_for_load, year_for_load],
                            y=[0, x],
                            z=[0, yval],
                            mode='lines+text',
                            line=dict(color='red', width=1), opacity=0.5,
                            text=[None, str(label)], textposition='top center',
                            name=f"Loading {label}",
                            showlegend=False
                        ))

            if trajectory_selections and traj_scope in ['3d','both']:
                for selection in trajectory_selections:
                    sel_type, sel_name = selection.split('_',1)
                    if sel_type == 'skor':
                        traj_data = df_pc_scores[(df_pc_scores['Kabupaten/Kota'] == sel_name) & (df_pc_scores['Tahun'].isin(years_3d_filtered))].sort_values('Tahun')
                        if not traj_data.empty:
                            traj_list = []
                            for y in traj_data['Tahun'].values:
                                if y in years_3d_filtered:
                                    idx = years_3d_filtered.index(y)
                                    rot_xy = rotate_df(pd.DataFrame(traj_data[traj_data['Tahun']==y][['PC1','PC2']].values, columns=['PC1','PC2']), angle_3d[idx])
                                    traj_list.append({'Tahun': y, 'PC1': rot_xy.iloc[0]['PC1'], 'PC2': rot_xy.iloc[0]['PC2']})
                            
                            if traj_list:
                                traj_df = pd.DataFrame(traj_list).sort_values('Tahun')
                                mask_traj = traj_df['Tahun'].isin(mirror_years)
                                traj_df.loc[mask_traj, 'PC2'] = -traj_df.loc[mask_traj, 'PC2']
                                fig_3d.add_trace(go.Scatter3d(x=traj_df['Tahun'], y=traj_df['PC1'], z=traj_df['PC2'],
                                                             mode='lines+markers', name=f'Trajektori {sel_name} (skor)'))
                    else:
                        traj_data = df_loadings[(df_loadings['features'] == sel_name) & (df_loadings['Tahun'].isin(years_3d_filtered))].sort_values('Tahun')
                        if not traj_data.empty:
                            traj_list = []
                            for y in traj_data['Tahun'].values:
                                if y in years_3d_filtered: 
                                    idx = years_3d_filtered.index(y)
                                    rot_xy = rotate_df(pd.DataFrame(traj_data[traj_data['Tahun']==y][['PC1','PC2']].values, columns=['PC1','PC2']), angle_3d[idx])
                                    traj_list.append({'Tahun': y, 'PC1': rot_xy.iloc[0]['PC1'], 'PC2': rot_xy.iloc[0]['PC2']})
                            
                            if traj_list:
                                traj_df = pd.DataFrame(traj_list).sort_values('Tahun')
                                mask_load = traj_df['Tahun'].isin(mirror_years)
                                traj_df.loc[mask_load, 'PC2'] = -traj_df.loc[mask_load, 'PC2']
                                fig_3d.add_trace(go.Scatter3d(x=traj_df['Tahun'], y=traj_df['PC1'], z=traj_df['PC2'],
                                                             mode='lines+markers', name=f'Trajektori {sel_name} (loading)'))

            fig_3d.update_layout(scene=dict(xaxis_title='Tahun', yaxis_title='PC1', zaxis_title='PC2'),
                                 title=f'Biplot 3D (Baseline: {baseline_name_3d})', height=600)

            children.append(html.Div(dcc.Graph(figure=fig_3d), className='six columns' if fig_2d is not None else 'twelve columns'))

    return children

# --------------------------------------------------
# ** CALLBACK 7: STATIS (MODIFIED) **
# --------------------------------------------------
@app.callback(
    Output('statis-graph', 'figure'),
    Output('statis-summary', 'children'),
    Input('run-statis-btn', 'n_clicks'),
    State('variable-dropdown-final', 'value'), 
    State('statis-vis-type', 'value'),
    State('upload-data', 'contents'), 
    State('global-data-store', 'data')
)
def callback_run_statis(n_clicks, selected_vars, vis_type, uploaded_contents, global_data):
    if n_clicks is None or n_clicks == 0:
        fig = go.Figure()
        fig.update_layout(title="Tekan 'Run STATIS' untuk menjalankan analisis", xaxis={'visible':False}, yaxis={'visible':False}, height=300)
        return fig, ""
    
    if not selected_vars:
        fig = go.Figure()
        fig.update_layout(title="Pilih minimal 1 variabel terlebih dahulu di dropdown 'Pilih Variabel PCA (dan STATIS)'.", xaxis={'visible':False}, yaxis={'visible':False}, height=300)
        return fig, ""
        
    if uploaded_contents is None or global_data is None:
        fig = go.Figure()
        fig.update_layout(title="File belum di-upload.", xaxis={'visible':False}, yaxis={'visible':False}, height=300)
        return fig, ""
    
    sheet_names = global_data['sheet_names']
    
    try:
        res = run_statis(uploaded_contents, selected_vars, sheet_names) 
    except Exception as e:
        fig = go.Figure()
        fig.update_layout(title=f"Error saat menjalankan STATIS: {e}", xaxis={'visible':False}, yaxis={'visible':False}, height=300)
        return fig, str(e)

    if vis_type == 'interstructure':
        fig = fig_interstructure(res['R'], sheet_names)
    elif vis_type == 'compromise':
        fig = fig_compromise(res['scores'], res['obs_labels'], res['eig_vals_c'])
    elif vis_type == 'biplot':
        fig = fig_biplot(res['scores'], res['obs_labels'], res['loadings'], res['selected_vars'], res['eig_vals_c'])
    elif vis_type == 'trajectory':
        fig = fig_trajectory(res['per_year_coords'], res['obs_labels'], sheet_names)
    else:
        fig = fig_compromise(res['scores'], res['obs_labels'], res['eig_vals_c'])

    alpha_lines = "\n".join([f" {y}: {a:.4f}" for y,a in zip(sheet_names, res['alphas'])])
    eig_lines = "\n".join([f" PC{i+1}: {v:.4f} ({v/res['eig_vals_c'].sum()*100:.2f}%)" for i,v in enumerate(res['eig_vals_c'][:6])])
    summary = f"Years: {sheet_names}\nAlphas (weights):\n{alpha_lines}\n\nTop eigenvalues of compromise:\n{eig_lines}"
    return fig, summary

# --------------------------------------------------
# ** Server Run (Hanya jika dijalankan lokal) **
# --------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, port=3400)