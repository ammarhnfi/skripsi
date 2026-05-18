import json

with open(r"d:\Skripsi\my\landing-page\public\formulas_substitusi.json", "r", encoding="utf-8") as f:
    formulas = json.load(f)

print(f"Total formulas loaded: {len(formulas)}")

# Print keys
if len(formulas) > 0:
    print(f"Keys: {list(formulas[0].keys())}")

# Search for ** in any values
print("\n--- Formulas with '**' inside ---")
found_star = 0
for fm in formulas:
    has_star = False
    for k, v in fm.items():
        if isinstance(v, str) and "**" in v:
            has_star = True
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str) and "**" in item:
                    has_star = True
    if has_star:
        found_star += 1
        print(f"ID: {fm.get('id')}, Title: {fm.get('title')}")

# Search for empty or missing or placeholder "hasil" or "substitusi"
print("\n--- Formulas with missing/placeholder 'hasil' or 'substitusi' ---")
found_missing = 0
for fm in formulas:
    sub = fm.get("substitusi", [])
    hasil = fm.get("hasil", "")
    
    # Check if substitusi contains placeholder-like strings, or is too short, or hasil is empty/placeholder
    is_placeholder = False
    if not sub or len(sub) == 0:
        is_placeholder = True
    else:
        for s in sub:
            if "belum" in s.lower() or "placeholder" in s.lower() or "tbd" in s.lower() or "substitusi" in s.lower() and len(sub) <= 1:
                is_placeholder = True
    
    if not hasil or "belum" in hasil.lower() or "placeholder" in hasil.lower() or "tbd" in hasil.lower() or hasil == "$$" or hasil.strip() == "":
        is_placeholder = True
        
    if is_placeholder:
        found_missing += 1
        print(f"ID: {fm.get('id')}, Title: {fm.get('title')}, Sub len: {len(sub)}, Hasil: {hasil}")

print(f"\nSummary: {found_star} formulas have '**', {found_missing} formulas have missing/placeholder values.")
