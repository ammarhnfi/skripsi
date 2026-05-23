"""
rename_kab.py — Konversi nama kabupaten/kota ↔ indeks pada file _name di output_real/

Skenario 1: Nama → Indeks  (mis. "Kep. Seribu" → [1])
Skenario 2: Indeks → Nama  (mis. [1] → "Kep. Seribu")

Indeks sesuai Lampiran 1 skripsi (41 kabupaten/kota Jabodetabek-Banten).
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
    """Kumpulkan semua file yang mengandung '_name' dalam nama file di output_real."""
    hasil = []
    for root, _dirs, files in os.walk(OUTPUT_REAL_DIR):
        for fname in files:
            if "_name" in fname:
                hasil.append(os.path.join(root, fname))
    return sorted(hasil)


# ── Konversi ─────────────────────────────────────────────────────────────────

def nama_ke_indeks(teks: str) -> str:
    """Ganti nama kabupaten/kota → [indeks]."""
    for nama in SORTED_NAMES:
        idx = NAME_TO_INDEX[nama]
        teks = teks.replace(nama, f"[{idx}]")
    return teks


def indeks_ke_nama(teks: str) -> str:
    """Ganti [indeks] → nama kabupaten/kota."""
    def ganti(m):
        idx = int(m.group(1))
        return INDEX_TO_NAME.get(idx, m.group(0))
    return re.sub(r"\[(\d+)\]", ganti, teks)


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


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  rename_kab.py — Konversi Nama Kabupaten/Kota ↔ Indeks")
    print("=" * 60)
    print(f"  Direktori : {OUTPUT_REAL_DIR}")
    print()
    print("  Pilih skenario:")
    print("    1 = Nama Kabupaten/Kota → Indeks  (mis. Kep. Seribu → [1])")
    print("    2 = Indeks → Nama Kabupaten/Kota  (mis. [1] → Kep. Seribu)")
    print()

    pilihan = input("Masukkan pilihan (1/2): ").strip()
    if pilihan not in ("1", "2"):
        print("[ERROR] Pilihan tidak valid. Harus 1 atau 2.")
        return

    konversi_fn = nama_ke_indeks if pilihan == "1" else indeks_ke_nama
    label_arah = "Nama → Indeks" if pilihan == "1" else "Indeks → Nama"

    print()
    print(f"Skenario dipilih: {label_arah}")
    print()

    files = find_name_files()
    if not files:
        print(f"[PERINGATAN] Tidak ada file _name ditemukan di:\n  {OUTPUT_REAL_DIR}")
        return

    print(f"Ditemukan {len(files)} file _name:")
    for f in files:
        print(f"  {os.path.relpath(f, OUTPUT_REAL_DIR)}")
    print()

    konfirmasi = input("Lanjutkan konversi? (y/n): ").strip().lower()
    if konfirmasi != "y":
        print("Dibatalkan.")
        return

    print()
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

    print()
    print(f"Selesai. {diubah} dari {len(files)} file diubah.")


if __name__ == "__main__":
    main()
