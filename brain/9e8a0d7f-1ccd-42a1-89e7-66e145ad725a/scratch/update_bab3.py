import re

with open(r"d:\Skripsi\my\bab3.tex", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Replace hardcoded X matrices
content = re.sub(r'\\mathbf{X}_{2020} = \\begin{pmatrix}.*?\\end{pmatrix}', r'\\mathbf{X}_{2020} = \\input{output_sample/matrix_X_2020.tex}', content, flags=re.DOTALL)
content = re.sub(r'\\mathbf{X}_{2021} = \\begin{pmatrix}.*?\\end{pmatrix}', r'\\mathbf{X}_{2021} = \\input{output_sample/matrix_X_2021.tex}', content, flags=re.DOTALL)
content = re.sub(r'\\mathbf{X}_{2022} = \\begin{pmatrix}.*?\\end{pmatrix}', r'\\mathbf{X}_{2022} = \\input{output_sample/matrix_X_2022.tex}', content, flags=re.DOTALL)

# 2. Replace hardcoded Z matrices
content = re.sub(r'\\mathbf{Z}_{2020} = \\begin{pmatrix}.*?\\end{pmatrix}', r'\\mathbf{Z}_{2020} = \\input{output_sample/matrix_Z_2020.tex}', content, flags=re.DOTALL)
content = re.sub(r'\\mathbf{Z}_{2021} = \\begin{pmatrix}.*?\\end{pmatrix}', r'\\mathbf{Z}_{2021} = \\input{output_sample/matrix_Z_2021.tex}', content, flags=re.DOTALL)
content = re.sub(r'\\mathbf{Z}_{2022} = \\begin{pmatrix}.*?\\end{pmatrix}', r'\\mathbf{Z}_{2022} = \\input{output_sample/matrix_Z_2022.tex}', content, flags=re.DOTALL)

# 3. Replace RV and Alpha tables/values
content = re.sub(r'\\mathbf{R}_{\\mathrm{RV}} = \\begin{pmatrix}.*?\\end{pmatrix}', r'\\input{output_sample/output_table_rv.tex}', content, flags=re.DOTALL)
content = re.sub(r'\\alpha_1 = 0{,}328, \\alpha_2 = 0{,}327, dan \\alpha_3 = 0{,}345', r'\\alpha_k sesuai dengan \\input{output_sample/output_table_alpha.tex}', content)

# 4. Replace Gc, Vc, Fc
content = re.sub(r'\\mathbf{G}_c = \\begin{pmatrix}.*?\\end{pmatrix}', r'\\mathbf{G}_c = \\input{output_sample/matrix_G_c.tex}', content, flags=re.DOTALL)
content = re.sub(r'\\mathbf{V}_c = \\begin{pmatrix}.*?\\end{pmatrix} = \\begin{pmatrix}.*?\\end{pmatrix}', r'\\mathbf{V}_c = \\input{output_sample/matrix_V_c.tex}', content, flags=re.DOTALL)
content = re.sub(r'\\mathbf{F}_c = \\begin{pmatrix}.*?\\end{pmatrix}', r'\\mathbf{F}_c = \\input{output_sample/matrix_F_c.tex}', content, flags=re.DOTALL)

# 5. Use Sample Macros
content = content.replace("\\Macro", "\\Sample")

with open(r"d:\Skripsi\my\bab3.tex", "w", encoding="utf-8") as f:
    f.write(content)
