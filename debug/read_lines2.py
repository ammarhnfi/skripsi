with open(r"d:\Skripsi\my\debug\formulas_dashboard.py", "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

output_lines = []
for idx in range(635, min(800, len(lines))):
    output_lines.append(f"{idx+1}: {lines[idx]}")

with open(r"d:\Skripsi\my\debug\formulas_dashboard_slice2.txt", "w", encoding="utf-8") as out:
    out.writelines(output_lines)

print(f"Wrote slice2 to d:\\Skripsi\\my\\debug\\formulas_dashboard_slice2.txt")
