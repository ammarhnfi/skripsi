import pandas as pd
import os

def generate_appendix_data():
    xlsx_path = r'd:\Skripsi\my\data\data2.xlsx'
    if not os.path.exists(xlsx_path):
        print(f"Error: {xlsx_path} not found")
        return

    # Read all sheets (2020-2024)
    xl = pd.ExcelFile(xlsx_path)
    sheets = xl.sheet_names # ['2020', '2021', '2022', '2023', '2024']
    all_data = {s: xl.parse(s) for s in sheets}
    
    # Identify variables (all columns except Prov/Kab)
    first_sheet_df = all_data[sheets[0]]
    meta_cols = ['Provinsi', 'Kabupaten/Kota']
    variables = [c for c in first_sheet_df.columns if c not in meta_cols]
    
    tex_content = [
        r"\chapter*{Lampiran 1 Data Penelitian}",
        r"\addcontentsline{loa}{lampiran}{Lampiran 1 Data Penelitian}",
        r"\label{app:data}",
        r"Berikut adalah data penelitian untuk masing-masing variabel dari tahun 2020 hingga 2024.",
        r"\vspace{1em}"
    ]
    
    for idx, var in enumerate(variables):
        # Build consolidated DF for this variable
        # Base: No, Prov, Kab
        df_var = first_sheet_df[meta_cols].copy()
        df_var.insert(0, 'No', range(1, len(df_var) + 1))
        
        # Add yearly data
        for s in sheets:
            # We assume the order of kabupaten/kota is the same in every sheet
            df_var[s] = all_data[s][var]
            
        # Generate LaTeX table for this variable
        clean_var_name = var.replace('_', r'\_')
        tex_content.append(r"\section*{" + f"Data Variabel {clean_var_name}" + r"}")
        # tex_content.append(r"\addcontentsline{loa}{lampiran}{" + f"Data Variabel {clean_var_name}" + r"}")
        
        tex_content.append(r"\begin{spacing}{1.0}")
        tex_content.append(r"\scriptsize")
        tex_content.append(r"\setlength{\tabcolsep}{2pt}")
        # Column width estimation: 
        # No (0.5cm), Prov (2.2cm), Kab (2.8cm), 5 yr (auto)
        # Total approx 14cm (Fits in 15cm text width)
        tex_content.append(r"\begin{longtable}{|c|p{2.2cm}|p{2.8cm}|c|c|c|c|c|}")
        tex_content.append(r"\hline")
        # Header
        header_cols = ['No', 'Provinsi', 'Kabupaten/Kota'] + sheets
        tex_content.append(" & ".join([f"\\textbf{{{c}}}" for c in header_cols]) + r" \\ \hline")
        tex_content.append(r"\endhead")
        
        for i, row in df_var.iterrows():
            row_vals = []
            for col_name, val in row.items():
                if col_name == 'No':
                    row_vals.append(str(int(val)))
                elif isinstance(val, (float, int)):
                    if abs(val) > 1000: # Large values like PDRB or GK
                        # Format as 1.234,56
                        formatted = f"{val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                        row_vals.append(formatted)
                    else:
                        # Format as 71,63
                        row_vals.append(f"{val:.2f}".replace('.', ','))
                else:
                    row_vals.append(str(val).replace('_', r'\_').replace('%', r'\%'))
            
            line = " & ".join(row_vals) + r" \\ \hline"
            tex_content.append(line)
            
        tex_content.append(r"\end{longtable}")
        tex_content.append(r"\end{spacing}")
        
        if idx < len(variables) - 1:
            tex_content.append(r"\newpage")
    
    with open(r'd:\Skripsi\my\lampiran1.tex', 'w', encoding='utf-8') as f:
        f.write("\n".join(tex_content))
    print("Generated lampiran1.tex with 12 variable tables")

def clean_code_for_latex(text):
    # Remove characters that can break PDFLaTeX
    return "".join([c if ord(c) < 128 else "" for c in text])

def generate_appendix_code():
    code_path = r'd:\Skripsi\my\web\skripsiv2\app.py'
    if not os.path.exists(code_path):
        print(f"Error: {code_path} not found")
        return
        
    with open(code_path, 'r', encoding='utf-8') as f:
        code = f.read()
        
    tex_content = [
        r"\chapter*{Lampiran 2 Kode Program Aplikasi Dashboard}",
        r"\addcontentsline{loa}{lampiran}{Lampiran 2 Kode Program Aplikasi Dashboard}",
        r"\label{app:code}",
        r"\begin{singlespace}",
        r"\footnotesize",
        r"\begin{lstlisting}[language=Python, breaklines=true, basicstyle=\ttfamily\footnotesize, frame=single]",
        clean_code_for_latex(code),
        r"\end{lstlisting}",
        r"\end{singlespace}"
    ]
    
    with open(r'd:\Skripsi\my\lampiran2.tex', 'w', encoding='utf-8') as f:
        f.write("\n".join(tex_content))
    print("Generated lampiran2.tex")

if __name__ == "__main__":
    generate_appendix_data()
    generate_appendix_code()
