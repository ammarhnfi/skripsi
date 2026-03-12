import os
import re

formulas_file = r'd:\Skripsi\my\web\skripsiv2\formulas.py'
with open(formulas_file, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace all $$ to ensure they have an empty line before and after.
# Wait, replacing $$ with \n\n$$\n\n might result in:
# \n\n$$\n\n KMO = ... \n\n$$\n\n
# This is totally fine for MathJax block display.
text = text.replace('$$', '\n\n$$\n\n')

# Clean up multiple newlines safely
text = re.sub(r'\n{3,}', '\n\n', text)

with open(formulas_file, 'w', encoding='utf-8') as f:
    f.write(text)

# 2. FIX CALLBACKS.PY
callbacks_file = r'd:\Skripsi\my\web\skripsiv2\callbacks.py'
with open(callbacks_file, 'r', encoding='utf-8') as f:
    cb_text = f.read()

# Replace res['labels_R'] to res['sheet_names']
cb_text = cb_text.replace("res['labels_R']", "res['sheet_names']")

with open(callbacks_file, 'w', encoding='utf-8') as f:
    f.write(cb_text)

print("Patch applied.")
