import json
import re

with open(r"d:\Skripsi\my\landing-page\public\formulas_substitusi.json", "r", encoding="utf-8") as f:
    formulas = json.load(f)

print("Check first 5 formulas:")
for i in range(5):
    fm = formulas[i]
    print(f"ID: {fm.get('id')}")
    print(f"Title: {fm.get('title')}")
    print(f"Formula: {fm.get('formula')}")
    print(f"Keterangan: {fm.get('keterangan')}")
    print(f"Substitusi: {fm.get('substitusi')}")
    print(f"Hasil: {fm.get('hasil')}")
    print("-" * 50)

# Check how many formulas actually have real data in "hasil" vs generic equations.
# E.g. which ones have hasil that is just an equation or empty or TBD or similar.
print("\nCheck all 67 formulas' results:")
for i, fm in enumerate(formulas):
    sub = fm.get("substitusi", [])
    hasil = fm.get("hasil", "")
    title = fm.get("title", "")
    print(f"{i+1:02d}. Title: {title[:40]:<40} | Sub count: {len(sub)} | Hasil: {hasil}")
