import sys
import base64
import json
import warnings
import os
import pandas as pd
import io
warnings.filterwarnings('ignore')

from final import (
    run_statis_core, 
    cb_eval_cluster, 
    cb_run_trans, 
    cb_run_clustering_trajectory,
    cb_run_ipm_trans,
    cb_run_cross_tab
)

def main():
    print("Reading data...")
    try:
        data_path = os.path.join('..', '..', 'data', 'FINAL DATA.xlsx')
        with open(data_path, 'rb') as f:
            content = base64.b64encode(f.read()).decode('utf-8')
        content_str = f"data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{content}"
    except Exception as e:
        print(f"Error reading {data_path}: {e}")
        return
    
    print("Running STATIS Core to generate base results...")
    vars_list = ['IPM', 'IPG', 'PPM', 'PDRB_ADHK', 'RLS', 'AHH_L', 'AHH_P', 'GK', 'PKKP', 'TPT', 'TPAK', 'GR']
    sheets = ['2020', '2021', '2022', '2023', '2024']
    
    res = run_statis_core(content_str, vars_list, sheets)
    if 'error' in res:
        print("Error from STATIS core:", res['error'])
        return
        
    print("1. Exporting yearly Elbow and Dendrograms...")
    for year in sheets:
        print(f"   -> Year {year}")
        cb_eval_cluster(year, res)
        
    print("2. Exporting Yearly Clustering Maps, Biplots, and Transition Matrices...")
    for i in range(1, len(sheets)):
        t1 = sheets[i-1]
        t2 = sheets[i]
        print(f"   -> Transition {t1} to {t2}")
        # Call cb_run_trans (it saves both map, biplot, sum_table, and name_table to huggingface)
        # N clicks = 1, view mode doesn't matter for files, t2_year = t2, k = 3
        cb_run_trans(1, 'count', t2, 3, res)

    print("3. Exporting Compromise Trajectory Clustering Outputs...")
    cb_run_clustering_trajectory(1, 3, res)
    
    # Kumpulkan global_data_store secara pseudo-manual untuk callback IPM & CrossTab
    print("Recreating global data store...")
    data_path = os.path.join('..', '..', 'data', 'FINAL DATA.xlsx')
    all_sheets = pd.read_excel(data_path, sheet_name=None)
    all_data = []
    for name, df in all_sheets.items():
        try:
            y = int(name)
            df['Tahun'] = y
            all_data.append(df)
        except: pass
    df_concat = pd.concat(all_data, ignore_index=True)
    cols = df_concat.columns.drop(['Provinsi', 'Kabupaten/Kota', 'Tahun'])
    for c in cols:
        if df_concat[c].dtype == 'object': 
            df_concat[c] = pd.to_numeric(df_concat[c].astype(str).str.replace(',', '.').str.replace(' ', ''), errors='coerce')
    df_concat.dropna(inplace=True)
    data_store = {
        'df_json': df_concat.to_json(orient='split'),
        'years': [int(y) for y in sheets]
    }
    
    print("4. Exporting IPM baseline matrices...")
    for i in range(1, len(sheets)):
        t1 = sheets[i-1]
        t2 = sheets[i]
        print(f"   -> IPM Transition {t1} to {t2}")
        cb_run_ipm_trans(1, 'count', int(t2), data_store)
        
    print("5. Exporting Cross-Tabulation matrices...")
    for year in sheets:
        print(f"   -> Cross-Tabulation {year}")
        # cb_run_cross_tab signature: n_clicks, view_mode, sel_year, k, data_store, statis_store
        cb_run_cross_tab(1, 'count', int(year), 3, data_store, res)
    
    print("\n-------------------------")
    print("All exports to ../huggingface completed successfully!")

if __name__ == '__main__':
    main()
