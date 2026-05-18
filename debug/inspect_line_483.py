import json

log_path = r"C:\Users\ammar\.gemini\antigravity\brain\f596eaf4-6668-42d2-90be-18b1afd5f804\.system_generated\logs\overview.txt"
with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

line_483 = lines[482] # 0-indexed is 482
obj = json.loads(line_483)

print("Line 483 details:")
print(f"type: {obj.get('type')}")
print(f"source: {obj.get('source')}")

# Print tool calls info
if "tool_calls" in obj:
    for tc in obj["tool_calls"]:
        print(f"Tool name: {tc.get('name') or tc.get('tool')}")
        args = tc.get("args") or tc.get("parameters")
        if args:
            print(f"Args keys: {list(args.keys())}")
            if "TargetFile" in args:
                print(f"TargetFile: {args['TargetFile']}")
            if "CodeContent" in args:
                code = args["CodeContent"]
                print(f"Code size: {len(code)}")
                with open(r"d:\Skripsi\my\debug\formulas_dashboard_restored.py", "w", encoding="utf-8") as out:
                    out.write(code)
                print("Successfully restored formulas_dashboard.py to formulas_dashboard_restored.py!")
            elif "ReplacementChunks" in args:
                print(f"Chunks: {len(args['ReplacementChunks'])}")
