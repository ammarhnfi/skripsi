import json
import os

json_path = r"d:\Skripsi\my\landing-page\public\formulas_substitusi.json"
app_path = r"d:\Skripsi\my\landing-page\src\App.jsx"

# 1. Read formulas JSON
with open(json_path, "r", encoding="utf-8") as f:
    formulas_data = json.load(f)

# 2. Serialize as pretty JS array
formulas_js = json.dumps(formulas_data, indent=2, ensure_ascii=False)

# 3. Read App.jsx
with open(app_path, "r", encoding="utf-8") as f:
    app_content = f.read()

# Target block to replace: the start of FormulasDashboard function through the end of the fetch useEffect
target_start = "function FormulasDashboard({ onBack }) {"
target_end = "  const toggleExpand = (id) => {"

start_idx = app_content.find(target_start)
end_idx = app_content.find(target_end)

if start_idx == -1 or end_idx == -1:
    print("Error: Could not locate the target block in App.jsx.")
    exit(1)

# Extract original code to verify
original_block = app_content[start_idx:end_idx]
print("Found target block to replace.")

# Define the replacement code with inlined FORMULAS_DATA
replacement_block = f"""const FORMULAS_DATA = {formulas_js};

function FormulasDashboard({{ onBack }}) {{
  const [formulas, setFormulas] = useState(FORMULAS_DATA);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
  const [loading, setLoading] = useState(false);
  const [expandedCards, setExpandedCards] = useState({{}});
"""

# Reassemble App.jsx content
new_content = app_content[:start_idx] + replacement_block + app_content[end_idx:]

# Write updated App.jsx back to file
with open(app_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("Successfully inlined FORMULAS_DATA directly inside landing-page/src/App.jsx!")
