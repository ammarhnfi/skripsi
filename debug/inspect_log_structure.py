log_path = r"C:\Users\ammar\.gemini\antigravity\brain\f596eaf4-6668-42d2-90be-18b1afd5f804\.system_generated\logs\overview.txt"
with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

print(f"Total lines in log: {len(lines)}")

# Print lines containing formulas_dashboard.py
found = 0
for idx, line in enumerate(lines):
    if "formulas_dashboard.py" in line:
        found += 1
        print(f"Line {idx+1}: {line[:120].strip()}")
        if found > 20:
            print("Truncated search...")
            break
