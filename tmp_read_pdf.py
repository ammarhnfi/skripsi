import PyPDF2
try:
    with open(r"d:\Skripsi\my\referensi\notused\file.pdf", "rb") as f:
        reader = PyPDF2.PdfReader(f)
        text = ""
        for page in reader.pages[:3]:
            text += page.extract_text()
        print(text)
except Exception as e:
    import traceback
    traceback.print_exc()
