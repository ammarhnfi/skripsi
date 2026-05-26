"""
rename_kab.py — Konversi nama kabupaten/kota ↔ indeks pada file _name di output_real/

Skenario 1: Nama -> Indeks  (mis. "Kep. Seribu" -> [1])
Skenario 2: Indeks -> Nama  (mis. [1] -> "Kep. Seribu")

Indeks sesuai Lampiran 1 skripsi (41 kabupaten/kota Jabodetabek-Banten).

Dua jenis file yang diproses:
  A) File *_name*.tex          — nama muncul di mana saja dalam teks (full-text replace)
  B) File dengan kolom pertama "Kabupaten/Kota" — nama hanya di sel kolom pertama (sebelum & pertama)
"""

import os
import re

# ── Tabel indeks (sesuai urutan Lampiran 1) ──────────────────────────────────
INDEX_TO_NAME = {
    1:  "Kep. Seribu",
    2:  "Kota Jakarta Selatan",
    3:  "Kota Jakarta Timur",
    4:  "Kota Jakarta Pusat",
    5:  "Kota Jakarta Barat",
    6:  "Kota Jakarta Utara",
    7:  "Bogor",
    8:  "Sukabumi",
    9:  "Cianjur",
    10: "Bandung",
    11: "Garut",
    12: "Tasikmalaya",
    13: "Ciamis",
    14: "Kuningan",
    15: "Cirebon",
    16: "Majalengka",
    17: "Sumedang",
    18: "Indramayu",
    19: "Subang",
    20: "Purwakarta",
    21: "Karawang",
    22: "Bekasi",
    23: "Bandung Barat",
    24: "Pangandaran",
    25: "Kota Bogor",
    26: "Kota Sukabumi",
    27: "Kota Bandung",
    28: "Kota Cirebon",
    29: "Kota Bekasi",
    30: "Kota Depok",
    31: "Kota Cimahi",
    32: "Kota Tasikmalaya",
    33: "Kota Banjar",
    34: "Pandeglang",
    35: "Lebak",
    36: "Tangerang",
    37: "Serang",
    38: "Kota Tangerang",
    39: "Kota Cilegon",
    40: "Kota Serang",
    41: "Kota Tangerang Selatan",
}

# Urutan penggantian: panjang nama descending supaya "Kota Tangerang Selatan"
# diganti sebelum "Kota Tangerang", dan "Kota Bekasi" sebelum "Bekasi", dst.
SORTED_NAMES = sorted(INDEX_TO_NAME.values(), key=len, reverse=True)
NAME_TO_INDEX = {v: k for k, v in INDEX_TO_NAME.items()}

OUTPUT_REAL_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "output_real")
)


# ── Fungsi pencarian file ─────────────────────────────────────────────────────

def find_name_files():
    """Kumpulkan semua file *_name*.tex (nama tersebar di seluruh teks)."""
    hasil = []
    for root, _dirs, files in os.walk(OUTPUT_REAL_DIR):
        for fname in files:
            if "_name" in fname and fname.endswith(".tex"):
                hasil.append(os.path.join(root, fname))
    return sorted(hasil)


def _kab_is_first_col(content: str) -> bool:
    """True jika ada baris di mana 'Kabupaten/Kota' muncul sebelum ' & ' pertama."""
    for line in content.splitlines():
        if "Kabupaten/Kota" in line and " & " in line:
            if line.find("Kabupaten/Kota") < line.find(" & "):
                return True
    return False


def find_kab_col_files(nama_files: list) -> list:
    """
    Kumpulkan file .tex yang punya kolom pertama 'Kabupaten/Kota'
    dan belum tercakup oleh find_name_files().
    """
    nama_set = set(nama_files)
    hasil = []
    for root, _dirs, files in os.walk(OUTPUT_REAL_DIR):
        for fname in files:
            if not fname.endswith(".tex"):
                continue
            fpath = os.path.join(root, fname)
            if fpath in nama_set:
                continue  # sudah ditangani jalur _name
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            if _kab_is_first_col(content):
                hasil.append(fpath)
    return sorted(hasil)


# ── Konversi full-text (untuk _name files) ───────────────────────────────────

def nama_ke_indeks(teks: str) -> str:
    """Ganti nama kabupaten/kota -> [indeks] di seluruh teks."""
    for nama in SORTED_NAMES:
        idx = NAME_TO_INDEX[nama]
        teks = teks.replace(nama, f"[{idx}]")
    return teks


def indeks_ke_nama(teks: str) -> str:
    """Ganti [indeks] -> nama kabupaten/kota di seluruh teks."""
    def ganti(m):
        idx = int(m.group(1))
        return INDEX_TO_NAME.get(idx, m.group(0))
    return re.sub(r"\[(\d+)\]", ganti, teks)


# ── Konversi kolom-pertama (untuk tabel Kabupaten/Kota) ──────────────────────

def _proses_kolom1(teks: str, fn_konversi) -> str:
    """
    Terapkan fn_konversi hanya pada sel kolom pertama (sebelum ' & ' pertama)
    di setiap baris data tabel LaTeX.
    Baris header (mengandung \\textbf) dan \\hline dilewati.
    """
    baris = teks.splitlines(keepends=True)
    hasil = []
    for b in baris:
        stripped = b.lstrip()
        if (
            " & " in b
            and r"\textbf" not in b
            and r"\hline" not in stripped
            and r"\caption" not in b
        ):
            # Pisahkan kolom pertama dari sisanya
            idx_amp = b.index(" & ")
            col1 = b[:idx_amp]
            sisa = b[idx_amp:]          # " & kolom2 & ... \\\n"
            col1_baru = fn_konversi(col1)
            b = col1_baru + sisa
        hasil.append(b)
    return "".join(hasil)


def nama_ke_indeks_kolom(teks: str) -> str:
    """Ganti nama kab/kota -> [indeks] hanya di kolom pertama tabel."""
    return _proses_kolom1(teks, nama_ke_indeks)


def indeks_ke_nama_kolom(teks: str) -> str:
    """Ganti [indeks] -> nama kab/kota hanya di kolom pertama tabel."""
    return _proses_kolom1(teks, indeks_ke_nama)


# ── Preview perubahan ─────────────────────────────────────────────────────────

def tampilkan_preview(path: str, lama: str, baru: str, maks_baris: int = 5):
    rel = os.path.relpath(path, OUTPUT_REAL_DIR)
    baris_lama = lama.splitlines()
    baris_baru = baru.splitlines()
    tampil = 0
    for i, (bl, bb) in enumerate(zip(baris_lama, baris_baru)):
        if bl != bb:
            print(f"    baris {i+1}:")
            print(f"      - {bl.strip()}")
            print(f"      + {bb.strip()}")
            tampil += 1
            if tampil >= maks_baris:
                print(f"      ... (dan lebih banyak perubahan)")
                break


# ── Proses satu kelompok file ─────────────────────────────────────────────────

def proses_files(files: list, konversi_fn, label_jenis: str) -> int:
    """Jalankan konversi pada daftar file, cetak status, kembalikan jumlah yang diubah."""
    if not files:
        return 0
    print(f"\n─── {label_jenis} ({len(files)} file) ───")
    diubah = 0
    for fpath in files:
        with open(fpath, "r", encoding="utf-8") as f:
            isi_lama = f.read()
        isi_baru = konversi_fn(isi_lama)
        rel = os.path.relpath(fpath, OUTPUT_REAL_DIR)
        if isi_baru != isi_lama:
            tampilkan_preview(fpath, isi_lama, isi_baru)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(isi_baru)
            print(f"  [DIUBAH] {rel}")
            diubah += 1
        else:
            print(f"  [SKIP]   {rel}  (tidak ada perubahan)")
    return diubah


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  rename_kab.py -- Konversi Nama Kabupaten/Kota <-> Indeks")
    print("=" * 60)
    print(f"  Direktori : {OUTPUT_REAL_DIR}")
    print()
    print("  Pilih skenario:")
    print("    1 = Nama Kabupaten/Kota -> Indeks  (mis. Kep. Seribu -> [1])")
    print("    2 = Indeks -> Nama Kabupaten/Kota  (mis. [1] -> Kep. Seribu)")
    print()

    pilihan = input("Masukkan pilihan (1/2): ").strip()
    if pilihan not in ("1", "2"):
        print("[ERROR] Pilihan tidak valid. Harus 1 atau 2.")
        return

    label_arah = "Nama -> Indeks" if pilihan == "1" else "Indeks -> Nama"
    print()
    print(f"Skenario dipilih: {label_arah}")
    print()

    # Kumpulkan file
    name_files = find_name_files()
    kab_col_files = find_kab_col_files(name_files)

    total = len(name_files) + len(kab_col_files)
    if total == 0:
        print(f"[PERINGATAN] Tidak ada file ditemukan di:\n  {OUTPUT_REAL_DIR}")
        return

    print(f"Ditemukan {len(name_files)} file *_name* (full-text):")
    for f in name_files:
        print(f"  {os.path.relpath(f, OUTPUT_REAL_DIR)}")

    print()
    print(f"Ditemukan {len(kab_col_files)} file kolom 'Kabupaten/Kota' (kolom-pertama):")
    for f in kab_col_files:
        print(f"  {os.path.relpath(f, OUTPUT_REAL_DIR)}")

    print()
    konfirmasi = input("Lanjutkan konversi? (y/n): ").strip().lower()
    if konfirmasi != "y":
        print("Dibatalkan.")
        return

    # Pilih fungsi konversi
    if pilihan == "1":
        fn_name    = nama_ke_indeks
        fn_kolom   = nama_ke_indeks_kolom
    else:
        fn_name    = indeks_ke_nama
        fn_kolom   = indeks_ke_nama_kolom

    # Proses
    diubah_name  = proses_files(name_files,    fn_name,  "File *_name* (full-text)")
    diubah_kolom = proses_files(kab_col_files, fn_kolom, "File kolom Kabupaten/Kota")

    total_diubah = diubah_name + diubah_kolom
    print()
    print(f"Selesai. {total_diubah} dari {total} file diubah.")


if __name__ == "__main__":
    main()
