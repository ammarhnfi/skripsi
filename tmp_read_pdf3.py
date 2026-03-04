import fitz

try:
    doc = fitz.open(r"d:\Skripsi\my\referensi\notused\file.pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    
    with open(r"d:\Skripsi\my\pdf_text.txt", "w", encoding="utf-8") as f:
        f.write(text)
except Exception as e:
    print(f"Error reading PDF: {e}")
