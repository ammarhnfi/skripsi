import json

log_path = r"C:\Users\ammar\.gemini\antigravity\brain\f596eaf4-6668-42d2-90be-18b1afd5f804\.system_generated\logs\overview.txt"
with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

found_tcs = []
for idx, line in enumerate(lines):
    try:
        obj = json.loads(line)
    except:
        continue
    
    tcs = obj.get("tool_calls") or []
    for tc in tcs:
        args = tc.get("args") or tc.get("parameters") or {}
        target = args.get("TargetFile") or args.get("AbsolutePath") or ""
        if "formulas_dashboard.py" in target:
            found_tcs.append((idx+1, tc.get("name") or tc.get("tool"), len(str(args))))

print(f"Found {len(found_tcs)} tool calls targeting formulas_dashboard.py:")
for idx, name, size in found_tcs:
    print(f"Line {idx}: tool={name}, args size={size}")
