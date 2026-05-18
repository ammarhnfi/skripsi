with open(r"d:\Skripsi\my\debug\formulas_dashboard.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

output_lines = []
for idx in range(600, min(630, len(lines))):
    output_lines.append(f"{idx+1}: {lines[idx]}")

with open(r"d:\Skripsi\my\debug\inspect_lines_output.txt", "w", encoding="utf-8") as out:
    out.writelines(output_lines)

print("Wrote lines to txt file.")
