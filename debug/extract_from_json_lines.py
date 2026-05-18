import json

log_path = r"C:\Users\ammar\.gemini\antigravity\brain\f596eaf4-6668-42d2-90be-18b1afd5f804\.system_generated\logs\overview.txt"
with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

print(f"Parsed {len(lines)} lines from overview.")

# We want to find a tool call to write_to_file or replace_file_content where the target file is formulas_dashboard.py
# Let's inspect the keys and find the one containing the full code.
found_blocks = []
for idx, line in enumerate(lines):
    try:
        obj = json.loads(line)
    except Exception as e:
        continue
    
    # We look for "write_to_file" or "replace_file_content" in the JSON object
    # Let's search inside the entire json object recursively for string values containing "formulas_dashboard.py"
    # and a large string that looks like a python file.
    
    def find_python_code(val):
        if isinstance(val, str):
            if "import " in val and "HIGH_FIDELITY_REFS" in val and len(val) > 10000:
                found_blocks.append((idx, len(val), val))
        elif isinstance(val, dict):
            for k, v in val.items():
                find_python_code(v)
        elif isinstance(val, list):
            for item in val:
                find_python_code(item)
                
    find_python_code(obj)

print(f"Found {len(found_blocks)} matching python blocks in logs.")
for idx, (l_num, size, code) in enumerate(found_blocks):
    print(f"{idx}: Line {l_num}, Size: {size}")

# Save the largest block
if found_blocks:
    # Sort by size descending
    found_blocks.sort(key=lambda x: x[1], reverse=True)
    largest_code = found_blocks[0][2]
    
    # Write the largest block to formulas_dashboard_restored.py
    with open(r"d:\Skripsi\my\debug\formulas_dashboard_restored.py", "w", encoding="utf-8") as out:
        out.write(largest_code)
    print(f"Saved largest matching block of size {len(largest_code)} to formulas_dashboard_restored.py")
else:
    # Let's do a broader check for any dictionary/list containing the code
    print("No blocks found with 'import' and 'HIGH_FIDELITY_REFS' and size > 10000.")
