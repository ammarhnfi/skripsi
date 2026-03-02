import fitz  # PyMuPDF
import sys

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
        print(f"Error extracting text: {e}")

if __name__ == "__main__":
    pdf_path = r"d:\Skripsi\my\referensi\file.pdf"
    output_path = r"d:\Skripsi\my\referensi\file_content.txt"
    extract_text(pdf_path, output_path)
