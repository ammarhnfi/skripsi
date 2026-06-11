"""
compress_pdf.py — Kompresi PDF skripsi: kompres gambar tertanam, vektor/teks tetap utuh.

Strategi:
  - Temukan semua Image XObject di setiap halaman
  - Re-encode sebagai JPEG dengan kualitas & dimensi yang dipilih
  - Teks, persamaan, garis vektor TIDAK di-rasterize → tetap tajam & bisa di-copy

Output: induk_compressed.pdf di folder my/
"""

import os
import sys
import io
import subprocess
import importlib

INPUT_PDF  = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "induk_inti.pdf"))
OUTPUT_PDF = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "induk_inti_compressed.pdf"))


def ensure_pkg(pip_name, import_name=None):
    import_name = import_name or pip_name
    if importlib.util.find_spec(import_name) is None:
        print(f"  Menginstall {pip_name}...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", pip_name, "-q"],
            stdout=subprocess.DEVNULL,
        )
        print(f"  {pip_name} berhasil diinstall.")


def ukuran_mb(path):
    return os.path.getsize(path) / 1_048_576


# ── Kumpulkan semua image XObject (termasuk di dalam Form XObject) ────────────

def iter_images(page):
    """Yield semua Image XObject unik dari satu halaman PDF."""
    seen = set()

    def _walk(resources):
        if "/XObject" not in resources:
            return
        for name, xobj in resources["/XObject"].items():
            try:
                subtype = xobj.get("/Subtype")
                if subtype == "/Image":
                    key = (xobj.objgen[0], xobj.objgen[1])
                    if key not in seen:
                        seen.add(key)
                        yield xobj
                elif subtype == "/Form":
                    if "/Resources" in xobj:
                        yield from _walk(xobj["/Resources"])
            except Exception:
                continue

    try:
        if "/Resources" in page:
            yield from _walk(page["/Resources"])
    except Exception:
        return


# ── Kompresi gambar ───────────────────────────────────────────────────────────

def compress_images(pdf, max_dim, jpeg_quality, min_pixels=30_000):
    import pikepdf
    from PIL import Image

    n_compressed = 0
    n_skipped = 0
    bytes_saved = 0
    total = len(pdf.pages)

    for page_num, page in enumerate(pdf.pages):
        print(f"  Halaman {page_num + 1}/{total} ...", end="\r", flush=True)
        for image_obj in iter_images(page):
            try:
                w = int(image_obj.get("/Width", 0))
                h = int(image_obj.get("/Height", 0))
                if w * h < min_pixels:
                    n_skipped += 1
                    continue

                # Ukuran asli (encoded) dalam PDF
                raw_size = len(bytes(image_obj.read_raw_bytes()))

                # Decode via pikepdf → PIL
                pdfimage = pikepdf.PdfImage(image_obj)
                pil_img = pdfimage.as_pil_image()

                # Downscale jika melebihi max_dim
                if max(pil_img.width, pil_img.height) > max_dim:
                    ratio = max_dim / max(pil_img.width, pil_img.height)
                    pil_img = pil_img.resize(
                        (max(1, int(pil_img.width * ratio)),
                         max(1, int(pil_img.height * ratio))),
                        Image.LANCZOS,
                    )

                # Pilih mode warna untuk JPEG
                if pil_img.mode == "L":
                    colorspace = pikepdf.Name.DeviceGray
                elif pil_img.mode in ("RGBA", "LA", "PA", "P", "CMYK"):
                    pil_img = pil_img.convert("RGB")
                    colorspace = pikepdf.Name.DeviceRGB
                else:
                    pil_img = pil_img.convert("RGB")
                    colorspace = pikepdf.Name.DeviceRGB

                # Encode JPEG
                buf = io.BytesIO()
                pil_img.save(buf, "JPEG", quality=jpeg_quality, optimize=True, subsampling=2)
                jpeg_bytes = buf.getvalue()

                # Simpan hanya jika lebih kecil
                if len(jpeg_bytes) >= raw_size * 0.95:
                    n_skipped += 1
                    continue

                # Tulis kembali ke XObject
                image_obj.write(jpeg_bytes, filter=pikepdf.Name.DCTDecode)
                image_obj["/Width"]              = pikepdf.Integer(pil_img.width)
                image_obj["/Height"]             = pikepdf.Integer(pil_img.height)
                image_obj["/ColorSpace"]         = colorspace
                image_obj["/BitsPerComponent"]   = pikepdf.Integer(8)
                # Hapus DecodeParms sisa filter lama kalau ada
                if "/DecodeParms" in image_obj:
                    del image_obj["/DecodeParms"]

                bytes_saved += raw_size - len(jpeg_bytes)
                n_compressed += 1

            except Exception:
                n_skipped += 1
                continue

    print()
    return n_compressed, n_skipped, bytes_saved


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not os.path.exists(INPUT_PDF):
        print(f"[ERROR] File tidak ditemukan: {INPUT_PDF}")
        sys.exit(1)

    print("=" * 60)
    print("  compress_pdf.py — Kompresi PDF Skripsi")
    print("=" * 60)

    # Install pikepdf jika belum ada
    ensure_pkg("pikepdf")
    import pikepdf  # noqa: F401 (sudah pasti ada setelah ensure_pkg)

    ukuran_awal = ukuran_mb(INPUT_PDF)
    print(f"  Input  : {INPUT_PDF}")
    print(f"  Output : {OUTPUT_PDF}")
    print(f"  Ukuran : {ukuran_awal:.2f} MB  ({len(pikepdf.open(INPUT_PDF).pages)} halaman)")
    print()
    print("  Pilih level (target < 10 MB):")
    print("    1 = Ringan   JPEG 85%, maks 1800 px  — gambar masih sangat tajam")
    print("    2 = Sedang   JPEG 75%, maks 1500 px  — rekomendasi untuk e-thesis")
    print("    3 = Agresif  JPEG 60%, maks 1200 px  — terkecil")
    print()

    pilihan = input("Pilihan (1/2/3): ").strip()
    if pilihan not in ("1", "2", "3"):
        print("[ERROR] Pilihan tidak valid.")
        sys.exit(1)

    config = {"1": (85, 1800), "2": (75, 1500), "3": (60, 1200)}
    jpeg_quality, max_dim = config[pilihan]

    print()
    print("Membuka PDF...")
    pdf = pikepdf.open(INPUT_PDF)

    print("Memproses gambar tertanam (teks & vektor dibiarkan)...")
    n_comp, n_skip, saved = compress_images(pdf, max_dim=max_dim, jpeg_quality=jpeg_quality)

    print("Menyimpan...")
    pdf.save(
        OUTPUT_PDF,
        compress_streams=True,
        object_stream_mode=pikepdf.ObjectStreamMode.generate,
    )
    pdf.close()

    ukuran_akhir = ukuran_mb(OUTPUT_PDF)
    rasio = (1 - ukuran_akhir / ukuran_awal) * 100

    print()
    print("=" * 60)
    print(f"  Gambar dikompres : {n_comp}")
    print(f"  Gambar di-skip   : {n_skip}")
    print(f"  Sebelum          : {ukuran_awal:.2f} MB")
    print(f"  Sesudah          : {ukuran_akhir:.2f} MB")
    print(f"  Hemat            : {rasio:.1f}%")
    print(f"  Output           : {OUTPUT_PDF}")
    print("=" * 60)

    if ukuran_akhir > 10:
        print("\n[INFO] File masih > 10 MB. Coba level 3 (agresif) untuk pengurangan lebih.")


if __name__ == "__main__":
    main()
