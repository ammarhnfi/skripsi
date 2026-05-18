import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import formulas_dashboard

print("Type of FORMULAS:", type(formulas_dashboard.FORMULAS))
print("Length of FORMULAS:", len(formulas_dashboard.FORMULAS))

# Let's inspect the keys and a sample entry
if len(formulas_dashboard.FORMULAS) > 0:
    print("Sample entry keys:", formulas_dashboard.FORMULAS[0].keys())

# Let's find where FORMULAS is declared in formulas_dashboard.py
with open("formulas_dashboard.py", "r", encoding="utf-8") as f:
    content = f.read()

print("\n--- Search for FORMULAS in code ---")
matches = [m.start() for m in re.finditer(r"\bFORMULAS\b", content)] if "re" in sys.modules else []
import re
matches = [m.start() for m in re.finditer(r"\bFORMULAS\b", content)]
for m in matches:
    start = max(0, m - 50)
    end = min(len(content), m + 150)
    print(f"Match at {m}:\n{content[start:end]}\n" + "-"*40)
