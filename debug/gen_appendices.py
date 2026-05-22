"""
gen_appendices.py
Generate lampiran1.tex (Data Penelitian) and lampiran2.tex (Link Aplikasi + Screenshot).
Output saved directly into the LaTeX template folder.
"""

import pandas as pd
import os
import shutil

TEMPLATE_DIR = r'd:\Skripsi\my'
XLSX_PATH    = r'd:\Skripsi\my\data\Data Final.xlsx'
SCREENSHOT_SRC = r'd:\Skripsi\my\gambarku\screenshot_web.png'
SCREENSHOT_DEST_NAME = 'screenshot_web.png'          # will live in pics/ subfolder
HUGGINGFACE_URL = 'https://huggingface.co/spaces/ammarhnfi/skripsiv4/blob/main/app.py'

# -------------------------------------------------------------------
# Lampiran 1 – Data Penelitian
# -------------------------------------------------------------------

def generate_appendix_data():
    if not os.path.exists(XLSX_PATH):
        print(f"Error: {XLSX_PATH} not found")
        return

    # Read all sheets (2020-2024)
    xl = pd.ExcelFile(XLSX_PATH)
    sheets = xl.sheet_names   # e.g. ['2020', '2021', '2022', '2023', '2024']
    all_data = {s: xl.parse(s) for s in sheets}

    # Identify variables (all columns except Prov/Kab)
    first_sheet_df = all_data[sheets[0]]
    meta_cols = ['Provinsi', 'Kabupaten/Kota']
    variables = [c for c in first_sheet_df.columns if c not in meta_cols]

    tex_content = [
        r"\chapter*{Lampiran 1 Data Penelitian}",
        r"\addcontentsline{loa}{lampiran}{Lampiran 1 Data Penelitian}",
        r"\label{app:data}",
        r"Berikut adalah data penelitian untuk masing-masing indikator dari tahun "
        + sheets[0] + " hingga " + sheets[-1] + r".",
        r"\vspace{1em}"
    ]

    for idx, var in enumerate(variables):
        # Build consolidated DF: No, Provinsi, Kab/Kota, <year>...
        df_var = first_sheet_df[meta_cols].copy()
        df_var.insert(0, 'No', range(1, len(df_var) + 1))
        for s in sheets:
            df_var[s] = all_data[s][var].values

        clean_var_name = var.replace('_', r'\_')
        tex_content.append(r"\section*{Data Indikator " + clean_var_name + r"}")

        tex_content.append(r"\begin{spacing}{1.0}")
        tex_content.append(r"\scriptsize")
        tex_content.append(r"\setlength{\tabcolsep}{2pt}")
        tex_content.append(r"\begin{longtable}{|c|p{2.2cm}|p{2.8cm}|c|c|c|c|c|}")
        tex_content.append(r"\hline")
        header_cols = ['No', 'Provinsi', 'Kabupaten/Kota'] + sheets
        tex_content.append(
            " & ".join([r"\textbf{" + c + r"}" for c in header_cols]) + r" \\ \hline"
        )
        tex_content.append(r"\endhead")

        for _, row in df_var.iterrows():
            row_vals = []
            for col_name, val in row.items():
                if col_name == 'No':
                    row_vals.append(str(int(val)))
                elif isinstance(val, (float, int)):
                    if abs(val) > 1000:
                        formatted = f"{val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        row_vals.append(formatted)
                    else:
                        row_vals.append(f"{val:.2f}".replace('.', ','))
                else:
                    row_vals.append(
                        str(val).replace('_', r'\_').replace('%', r'\%')
                    )
            tex_content.append(" & ".join(row_vals) + r" \\ \hline")

        tex_content.append(r"\end{longtable}")
        tex_content.append(r"\end{spacing}")

        if idx < len(variables) - 1:
            tex_content.append(r"\newpage")

    out_path = os.path.join(TEMPLATE_DIR, 'lampiran1.tex')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(tex_content))
    print(f"Generated {out_path}  ({len(variables)} variabel tables)")


# -------------------------------------------------------------------
# Lampiran 2 – Link Aplikasi Dashboard + Screenshot
# -------------------------------------------------------------------

def generate_appendix_link():
    # Copy screenshot into the template's pics/ folder so LaTeX can find it
    pics_dir = os.path.join(TEMPLATE_DIR, 'pics')
    os.makedirs(pics_dir, exist_ok=True)
    dest = os.path.join(pics_dir, SCREENSHOT_DEST_NAME)
    shutil.copy2(SCREENSHOT_SRC, dest)
    print(f"Copied screenshot -> {dest}")

    # Escape the URL for LaTeX (% must be escaped, but URLs usually don't have %)
    url_escaped = HUGGINGFACE_URL  # \url{} handles most special chars automatically

    tex_content = [
        r"\chapter*{Lampiran 2 Kode Program Aplikasi Dashboard}",
        r"\addcontentsline{loa}{lampiran}{Lampiran 2 Kode Program Aplikasi Dashboard}",
        r"\label{app:code}",
        r"\vspace{0.5em}",
        r"Kode program aplikasi dashboard yang digunakan dalam penelitian ini dapat diakses secara",
        r"daring melalui tautan berikut:",
        r"\vspace{0.5em}",
        r"\begin{center}",
        r"\url{" + url_escaped + r"}",
        r"\end{center}",
        r"\vspace{1em}",
        r"Berikut adalah tampilan antarmuka aplikasi dashboard:",
        r"\vspace{0.5em}",
        r"\begin{figure}[h!]",
        r"  \centering",
        r"  \includegraphics[width=\textwidth]{pics/" + SCREENSHOT_DEST_NAME + r"}",
        r"  \caption{Tampilan Antarmuka Aplikasi Dashboard Analisis Spasio-Temporal Sosio-Ekonomi}",
        r"  \label{fig:screenshot_dashboard}",
        r"\end{figure}",
    ]

    out_path = os.path.join(TEMPLATE_DIR, 'lampiran2.tex')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(tex_content))
    print(f"Generated {out_path}")


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------

if __name__ == "__main__":
    generate_appendix_data()
    generate_appendix_link()
    print("\nDone! Compile induk_2025.tex to see the appendices.")
