# Read formulas_dashboard.py with replacement of bad chars and write to a clean file
with open(r"d:\Skripsi\my\debug\formulas_dashboard.py", "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

output_lines = []
for idx in range(590, min(1300, len(lines))):
    output_lines.append(f"{idx+1}: {lines[idx]}")

with open(r"d:\Skripsi\my\debug\formulas_dashboard_slice.txt", "w", encoding="utf-8") as out:
    out.writelines(output_lines)

print(f"Successfully wrote slice of formulas_dashboard.py to d:\\Skripsi\\my\\debug\\formulas_dashboard_slice.txt")
