"""
perbedaan.py - Bandingkan induk_lama.pdf vs induk_baru.pdf dan tandai perbedaannya.

Cara pakai:
    python perbedaan.py
    python perbedaan.py path/ke/lama.pdf path/ke/baru.pdf

Hasil:
    induk_lama_markah.pdf   -> salinan PDF lama dengan highlight MERAH pada
                               teks yang dihapus/diubah (tidak ada lagi di versi baru)
    induk_baru_markah.pdf   -> salinan PDF baru dengan highlight KUNING pada
                               teks yang ditambah/diubah (baru muncul di versi baru)

File asli (induk_lama.pdf, induk_baru.pdf) tidak pernah ditimpa/diubah.
"""

import sys
import re
import difflib
import fitz  # PyMuPDF


def load_words(path):
    """Ambil semua kata dari PDF beserta lokasinya, urut sesuai urutan baca."""
    doc = fitz.open(path)
    words = []  # list of dict: page, block, line, rect, text
    for pno in range(doc.page_count):
        page = doc[pno]
        for x0, y0, x1, y1, text, block_no, line_no, word_no in page.get_text("words"):
            text = text.strip()
            if not text:
                continue
            words.append({
                "page": pno,
                "block": block_no,
                "line": line_no,
                "rect": fitz.Rect(x0, y0, x1, y1),
                "text": text,
            })
    return doc, words


def normalize(text):
    """Normalisasi ringan supaya diff tidak berisik karena tanda baca/kapital."""
    text = text.lower()
    text = re.sub(r"[^\w]", "", text)
    return text


def group_runs(words, changed_idx):
    """
    Gabungkan kata-kata yang berubah dan bersebelahan (indeks berurutan,
    di halaman/blok/baris yang sama) menjadi satu kotak highlight.
    """
    runs = []
    current = None
    for idx, w in enumerate(words):
        if idx in changed_idx:
            key = (w["page"], w["block"], w["line"])
            if current is not None and current["key"] == key and current["last_idx"] == idx - 1:
                current["rect"] |= w["rect"]
                current["last_idx"] = idx
            else:
                if current is not None:
                    runs.append(current)
                current = {"key": key, "page": w["page"], "rect": fitz.Rect(w["rect"]), "last_idx": idx}
        else:
            if current is not None:
                runs.append(current)
                current = None
    if current is not None:
        runs.append(current)
    return runs


def apply_highlights(doc, runs, color, pad=1.5):
    for run in runs:
        page = doc[run["page"]]
        rect = run["rect"] + (-pad, -pad, pad, pad)
        annot = page.add_highlight_annot(rect)
        annot.set_colors(stroke=color)
        annot.set_opacity(0.45)
        annot.update()
    return len(runs)


def main():
    lama_path = sys.argv[1] if len(sys.argv) > 1 else "induk_lama.pdf"
    baru_path = sys.argv[2] if len(sys.argv) > 2 else "induk_baru.pdf"

    print(f"Membaca kata + posisi dari '{lama_path}' ...")
    doc_lama, words_lama = load_words(lama_path)
    print(f"  {len(words_lama)} kata, {doc_lama.page_count} halaman")

    print(f"Membaca kata + posisi dari '{baru_path}' ...")
    doc_baru, words_baru = load_words(baru_path)
    print(f"  {len(words_baru)} kata, {doc_baru.page_count} halaman")

    tokens_lama = [normalize(w["text"]) for w in words_lama]
    tokens_baru = [normalize(w["text"]) for w in words_baru]

    print("Menghitung perbedaan (difflib)...")
    sm = difflib.SequenceMatcher(None, tokens_lama, tokens_baru, autojunk=False)
    opcodes = sm.get_opcodes()

    changed_lama = set()
    changed_baru = set()
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            continue
        if tag in ("delete", "replace"):
            changed_lama.update(range(i1, i2))
        if tag in ("insert", "replace"):
            changed_baru.update(range(j1, j2))

    print(f"Kata berubah/hilang di versi lama : {len(changed_lama)}")
    print(f"Kata baru/berubah di versi baru   : {len(changed_baru)}")

    runs_lama = group_runs(words_lama, changed_lama)
    runs_baru = group_runs(words_baru, changed_baru)

    print("Menandai PDF lama dengan highlight MERAH...")
    n_lama = apply_highlights(doc_lama, runs_lama, color=(1, 0, 0))
    print("Menandai PDF baru dengan highlight KUNING...")
    n_baru = apply_highlights(doc_baru, runs_baru, color=(1, 1, 0))

    out_lama = "induk_lama_markah.pdf"
    out_baru = "induk_baru_markah.pdf"
    doc_lama.save(out_lama, garbage=4, deflate=True)
    doc_baru.save(out_baru, garbage=4, deflate=True)

    print()
    print(f"Selesai. {n_lama} area ditandai merah di '{out_lama}'")
    print(f"         {n_baru} area ditandai kuning di '{out_baru}'")


if __name__ == "__main__":
    main()
