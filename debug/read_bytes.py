with open(r"d:\Skripsi\my\debug\formulas_dashboard.py", "rb") as f:
    data = f.read()

# Let's search for "HIGH_FIDELITY_REFS" in bytes
idx = data.find(b"HIGH_FIDELITY_REFS")
print(f"Index of HIGH_FIDELITY_REFS: {idx}")

# Print 100 bytes before and after
start = max(0, idx - 100)
end = min(len(data), idx + 200)
print(f"Bytes around HIGH_FIDELITY_REFS:\n{data[start:end]}")
