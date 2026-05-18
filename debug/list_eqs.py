import json

with open("landing-page/public/equations.json", encoding="utf-8") as f:
    eqs = json.load(f)

for i, eq in enumerate(eqs):
    print(f"{i}: {eq['section']} || {eq['latex'][:80]}")
