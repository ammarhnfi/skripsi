import sys
import subprocess

try:
    import fitz
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyMuPDF", "--quiet"])
    import fitz

try:
    doc = fitz.open(r"d:\Skripsi\my\referensi\notused\file.pdf")
    text = ""
    for i in range(min(5, len(doc))):
        text += doc[i].get_text()
    print(text)
except Exception as e:
    print(f"Error reading PDF: {e}")
