import re
import os

files_in_order = [
    r"d:\Skripsi\my\web\skripsiv2\formulas.py",
    r"d:\Skripsi\my\web\skripsiv2\utils.py",
    r"d:\Skripsi\my\web\skripsiv2\statis_analysis.py",
    r"d:\Skripsi\my\web\skripsiv2\spatial_analysis.py",
    r"d:\Skripsi\my\web\skripsiv2\layout.py",
    r"d:\Skripsi\my\web\skripsiv2\callbacks.py",
    r"d:\Skripsi\my\web\skripsiv2\app.py"
]

all_lines = []

for fpath in files_in_order:
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            all_lines.extend(f.readlines())
        all_lines.append("\n\n# ==========================================\n\n")

# Process lines
final_lines = []

# Move imports to top
imports = set()
body = []

local_modules = ["formulas", "utils", "statis_analysis", "spatial_analysis", "layout", "callbacks", "app"]

for line in all_lines:
    line_str = line.strip()
    # Filter local imports completely
    is_local = False
    for mod in local_modules:
        if line_str.startswith(f"from {mod}") or line_str.startswith(f"import {mod}"):
            is_local = True
            break
    
    if is_local:
        continue
        
    if line.startswith("import ") or line.startswith("from "):
        imports.add(line)
    else:
        body.append(line)

# Also remove dash core component deprecation instances optionally, but keep everything standard.
# Reconstruct
with open(r"d:\Skripsi\my\web\final2.py", "w", encoding="utf-8") as out:
    for imp in sorted(list(imports)):
        out.write(imp)
    out.write("\n\n")
    for b in body:
        out.write(b)
    
    # Needs to end with run_server if not there
    out.write("\n\nif __name__ == '__main__':\n    app.run_server(debug=True, port=8050)\n")

print("Merge done!")
