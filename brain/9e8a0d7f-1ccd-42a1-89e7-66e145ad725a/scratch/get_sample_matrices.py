import pandas as pd
import numpy as np
import os

DATA_PATH = r"d:\Skripsi\my\data\Data Sampel Final.xlsx"
OUT_DIR = r"d:\Skripsi\my\output_sample"
os.makedirs(OUT_DIR, exist_ok=True)

all_sheets = pd.read_excel(DATA_PATH, sheet_name=None)
years = ["2020", "2021", "2022"]
vars_in = ["PPM", "RLS", "TPT"]

def save_matrix_tex(df, filename):
    with open(os.path.join(OUT_DIR, filename), "w") as f:
        f.write(r"\begin{pmatrix}" + "\n")
        for i, row in df.iterrows():
            f.write(" & ".join([f"{v:.2f}".replace('.', ',') for v in row]) + r" \\" + "\n")
        f.write(r"\end{pmatrix}")

for yr in years:
    df = all_sheets[yr].set_index("Kabupaten/Kota")[vars_in]
    save_matrix_tex(df, f"matrix_X_{yr}.tex")
    
    # Calculate Z-score (weighted would be better but let's see if we can replicate the app's tables_std)
    # Actually, let's just use the app's logic or wait...
    # I'll just export the tables from export_all.py by modifying it slightly.
