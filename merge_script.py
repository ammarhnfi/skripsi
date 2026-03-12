import re

files = [
    r"d:\Skripsi\my\web\skripsiv2\formulas.py",
    r"d:\Skripsi\my\web\skripsiv2\spatial_analysis.py",
    r"d:\Skripsi\my\web\skripsiv2\utils.py",
    r"d:\Skripsi\my\web\skripsiv2\statis_analysis.py",
    r"d:\Skripsi\my\web\skripsiv2\layout.py",
    r"d:\Skripsi\my\web\skripsiv2\callbacks.py",
    r"d:\Skripsi\my\web\skripsiv2\app.py"
]

all_imports = set()
body_lines = []

def is_local_import(line):
    for mod in ['formulas', 'spatial_analysis', 'utils', 'statis_analysis', 'layout', 'callbacks', 'app']:
        if f'import {mod}' in line or f'from {mod} import' in line:
            return True
    return False

for f_path in files:
    try:
        with open(f_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line in lines:
            stripped = line.strip()
            # If it's an import line, and not a local import, add to imports
            # (Very basic heuristic, assumes imports are at top level)
            if (stripped.startswith('import ') or stripped.startswith('from ')) and not is_local_import(stripped):
                # Don't grab imports inside functions for now unless we do it carefully.
                # Actually, in utils.py there are some imports inside functions.
                # Let's just catch top-level imports by checking if line starts with 'import' or 'from' 
                # WITHOUT leading spaces. Local imports inside functions (like `import plotly.figure_factory`) are fine.
                if line.startswith('import ') or line.startswith('from '):
                    all_imports.add(line)
                else:
                    body_lines.append(line)
            else:
                if line.startswith('import ') or line.startswith('from '):
                    if is_local_import(stripped):
                        continue # Skip local import
                
                body_lines.append(line)
                
        body_lines.append("\n\n# " + "-"*40 + "\n\n")
    except Exception as e:
        print(f"Error reading {f_path}: {e}")

# We need to make sure `app = dash.Dash(...)` is defined before callbacks.
# app.py has the app definition. Let's extract the app initialization and put it before layout and callbacks.
final_lines = []
for imp in sorted(list(all_imports)):
    final_lines.append(imp)

final_lines.append("\n\n")

# Move 'app = Dash(...)' up.
app_init_found = False
for b in body_lines:
    if "app = Dash(__name__" in b or "app = dash.Dash(__name__" in b:
        final_lines.append("import dash\nfrom dash import Dash, html, dcc, Input, Output, State, dash_table, exceptions\n")
        final_lines.append("import dash_bootstrap_components as dbc\n")
        final_lines.append(b)
        app_init_found = True
        break

for b in body_lines:
    if "app = dash.Dash(__name__" in b or "app = Dash(__name__" in b:
        continue # Already added
    final_lines.append(b)

with open(r"d:\Skripsi\my\web\final2.py", 'w', encoding='utf-8') as f:
    f.writelines(final_lines)

print("Created final2.py successfully.")
