import json

json_path = r"d:\Skripsi\my\landing-page\public\formulas_substitusi.json"
with open(json_path, "r", encoding="utf-8") as f:
    formulas = json.load(f)

with open(r"d:\Skripsi\my\debug\all_formulas_inspection.txt", "w", encoding="utf-8") as out:
    for idx, fm in enumerate(formulas):
        out.write(f"=== Formula {idx+1}: {fm.get('title')} ===\n")
        out.write(f"Formula: {fm.get('formula')}\n")
        out.write(f"Keterangan:\n")
        for ket in fm.get("keterangan", []):
            out.write(f"  - {ket}\n")
        out.write(f"Substitusi:\n")
        for sub in fm.get("substitusi", []):
            out.write(f"  - {sub}\n")
        out.write(f"Hasil: {fm.get('hasil')}\n")
        out.write("-" * 80 + "\n\n")

print("Wrote inspection of all 67 formulas to debug/all_formulas_inspection.txt")
