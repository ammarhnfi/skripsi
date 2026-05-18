import json

log_path = r"C:\Users\ammar\.gemini\antigravity\brain\f596eaf4-6668-42d2-90be-18b1afd5f804\.system_generated\logs\overview.txt"
with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "formulas_dashboard.py" in line:
        try:
            obj = json.loads(line)
            # Print structure
            print(f"Line {idx+1}: type={obj.get('type')}, source={obj.get('source')}")
            # If there's content or tool calls, print their keys
            if "content" in obj:
                print(f"  content keys: {list(obj['content'].keys()) if isinstance(obj['content'], dict) else 'string'}")
            if "tool_calls" in obj:
                print(f"  tool_calls: {len(obj['tool_calls'])}")
                for tc in obj["tool_calls"]:
                    print(f"    tool={tc.get('name') or tc.get('tool')}")
        except Exception as e:
            print(f"Line {idx+1}: failed to parse json: {e}")
        print("-" * 50)
