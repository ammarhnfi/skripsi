import json

json_path = r"d:\Skripsi\my\landing-page\public\formulas_substitusi.json"
with open(json_path, "r", encoding="utf-8") as f:
    formulas = json.load(f)

print(f"Total formulas: {len(formulas)}")

# Let's count and list the ones with "**"
star_formulas = []
for i, fm in enumerate(formulas):
    found = False
    for k, v in fm.items():
        if isinstance(v, str) and "**" in v:
            found = True
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str) and "**" in item:
                    found = True
    if found:
        star_formulas.append(i)

print(f"Formulas with '**' (total {len(star_formulas)}):")
for idx in star_formulas:
    print(f"Index {idx+1}: {formulas[idx]['title']}")

# Let's count and list the ones with 'Model Teoretis Terdaftar' or empty hasil
teori_formulas = []
for i, fm in enumerate(formulas):
    hasil = fm.get("hasil", "")
    if "Model Teoretis Terdaftar" in hasil or hasil.strip() == "$$" or not hasil:
        teori_formulas.append(i)

print(f"\nFormulas with 'Model Teoretis Terdaftar' or missing hasil (total {len(teori_formulas)}):")
for idx in teori_formulas:
    print(f"Index {idx+1}: {formulas[idx]['title']}")
