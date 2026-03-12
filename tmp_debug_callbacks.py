import sys
import base64
import pandas as pd
import json

# Add current path to sys path to import app modules
sys.path.append(r'd:\Skripsi\my\web\skripsiv2')

from callbacks import cb_upload, cb_controls, cb_pca_calc, cb_statis_calc, cb_statis_viz, cb_diag_math, cb_run_clustering_trajectory
from statis_analysis import run_statis_core

# 1. TEST UPLOAD
file_path = r'd:\Skripsi\my\web\FINAL DATA.xlsx'
with open(file_path, "rb") as f:
    encoded_string = base64.b64encode(f.read()).decode("utf-8")
contents = f"data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{encoded_string}"

try:
    global_store, msg = cb_upload(contents, "FINAL DATA.xlsx")
    print("cb_upload SUCCESS")
except Exception as e:
    print("cb_upload ERROR:", e)

# 2. TEST CONTROLS
try:
    controls = cb_controls(global_store, "loading")
    print("cb_controls SUCCESS")
    vars_value = controls[1] # Output('variable-dropdown-final', 'value')
except Exception as e:
    print("cb_controls ERROR:", e)

# 3. TEST PCA
try:
    pca_store = cb_pca_calc(vars_value, global_store)
    print("cb_pca_calc SUCCESS")
except Exception as e:
    print("cb_pca_calc ERROR:", e)

# 4. TEST DIAGNOSTICS (Simulate click)
try:
    diag_res = cb_diag_math(1, global_store, vars_value)
    print("cb_diag_math SUCCESS")
except Exception as e:
    print("cb_diag_math ERROR:", e)

# 5. TEST STATIS CALC
try:
    statis_store = cb_statis_calc(1, vars_value, contents, global_store)
    print("cb_statis_calc SUCCESS")
except Exception as e:
    print("cb_statis_calc ERROR:", e)

# 6. TEST STATIS VIZ
try:
    viz_res = cb_statis_viz(statis_store, None, None, 10)
    print("cb_statis_viz SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
    print("cb_statis_viz ERROR:", e)

# 7. TEST TRAJ CLUSTER
try:
    clust_res = cb_run_clustering_trajectory(1, 3, statis_store)
    print("cb_run_clustering_trajectory SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
    print("cb_run_clustering_trajectory ERROR:", e)

