import json

json_path = r"d:\Skripsi\my\landing-page\public\formulas_substitusi.json"
with open(json_path, "r", encoding="utf-8") as f:
    formulas = json.load(f)

# Update index 30 (Formula 31)
formulas[30]["hasil"] = r"$$ \mathbf{H} \mathbf{u}_1 = 4.8524 \, \mathbf{u}_1 $$"
print("Updated Formula 31 result successfully.")

# Clean any residual '**' from all formulas just in case
for idx, fm in enumerate(formulas):
    for key in ["title", "formula", "hasil"]:
        if isinstance(fm.get(key), str):
            fm[key] = fm[key].replace("**", "")
    if "keterangan" in fm:
        fm["keterangan"] = [item.replace("**", "") if isinstance(item, str) else item for item in fm["keterangan"]]
    if "substitusi" in fm:
        fm["substitusi"] = [item.replace("**", "") if isinstance(item, str) else item for item in fm["substitusi"]]

# Write back
with open(r"d:\Skripsi\my\landing-page\public\formulas_substitusi.json", "w", encoding="utf-8") as f:
    json.dump(formulas, f, indent=2, ensure_ascii=False)

with open(r"d:\Skripsi\my\landing-page\dist\formulas_substitusi.json", "w", encoding="utf-8") as f:
    json.dump(formulas, f, indent=2, ensure_ascii=False)

print("Verifying again...")
teori_formulas = []
for i, fm in enumerate(formulas):
    hasil = fm.get("hasil", "")
    if "Model Teoretis Terdaftar" in hasil or hasil.strip() == "$$" or not hasil:
        teori_formulas.append(i)

print(f"Formulas with 'Model Teoretis Terdaftar' or missing hasil: {len(teori_formulas)}")
