import re

log_path = r"C:\Users\ammar\.gemini\antigravity\brain\f596eaf4-6668-42d2-90be-18b1afd5f804\.system_generated\logs\overview.txt"
with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
    text = f.read()

# Let's search for "formulas_dashboard.py" inside write_to_file or similar blocks
# In the log, model outputs are recorded, which include write_to_file or edit calls with formulas_dashboard.py content
# Let's find all occurrences of "formulas_dashboard.py"
print(f"Total length of log: {len(text)}")

matches = [m.start() for m in re.finditer(r"formulas_dashboard\.py", text)]
print(f"Number of occurrences of formulas_dashboard.py: {len(matches)}")

# Let's search backwards from the end of the file for a block that contains the large body of formulas_dashboard.py
# Let's look for a block that starts with import or has many characters.
# We know the file was written or modified. Let's find any large code blocks of python in the log.
# Python code blocks usually start with ```python and end with ```
code_blocks = re.findall(r"```python\n(.*?)\n```", text, re.DOTALL)
print(f"Found {len(code_blocks)} python code blocks.")

for i, block in enumerate(code_blocks):
    if "HIGH_FIDELITY_REFS" in block and "FORMULAS = []" in block:
        print(f"Block {i} matches formulas_dashboard.py! Length: {len(block)}")
        # Let's save it
        with open(r"d:\Skripsi\my\debug\formulas_dashboard_restored.py", "w", encoding="utf-8") as out:
            out.write(block)
        print(f"Saved to d:\\Skripsi\\my\\debug\\formulas_dashboard_restored.py")
