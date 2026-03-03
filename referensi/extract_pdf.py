import fitz  # PyMuPDF
import sys
import os
import glob

def extract_text(pdf_path, output_path):
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Successfully extracted text to {output_path}")
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {e}")

if __name__ == "__main__":
    pdf_dir = r"d:\Skripsi\my\referensi"
    pdf_files = glob.glob(os.path.join(pdf_dir, "*.pdf"))
    for pdf_path in pdf_files:
        output_path = pdf_path.replace(".pdf", ".txt")
        extract_text(pdf_path, output_path)
