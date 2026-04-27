import re

with open(r"d:\Skripsi\my\bab4.tex", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("\\Macro", "\\App")

with open(r"d:\Skripsi\my\bab4.tex", "w", encoding="utf-8") as f:
    f.write(content)
