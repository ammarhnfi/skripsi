# Outline Presentasi Sidang Skripsi
**Ammar Hanafi — 2206051582**
**Pendekatan STATIS dan Dynamic Biplot untuk Analisis Spasio-Temporal Sosio-Ekonomi**
*(Studi Kasus: Provinsi Banten, DKI Jakarta, dan Jawa Barat 2020–2024)*

Pembimbing: Dr. Dra. Yekti Widyaningsih, M.Si.
Penguji I: Sarini Abdullah, S.Si., M.Stats., Ph.D.
Penguji II: Gianinna Ardaneswari, S.Si., M.Si.

---

## Slide 1 — Cover

- Judul lengkap (dua baris)
- Nama & NPM
- Logo UI
- Program Studi Sarjana Statistika, FMIPA UI
- Juni 2026

---

## Slide 2 — Outline Presentasi

1. Latar Belakang & Motivasi
2. Rumusan Masalah & Tujuan
3. Data & Indikator
4. Metode: Tahapan STATIS
5. Hasil: Inter-Struktur & Kompromi
6. Hasil: Trajektori & Klaster
7. Kesimpulan & Saran

> **Catatan narasi:** "Presentasi saya terbagi dalam 7 bagian. Saya akan mulai dari konteks masalah, lalu metodologi, kemudian langsung ke hasil utama, dan diakhiri kesimpulan serta implikasi kebijakan."

---

## Slide 3 — Latar Belakang: Mengapa Penelitian Ini Penting?

**Heading:** *Kesenjangan Regional yang Persisten di Jawa Bagian Barat*

**Visual:** Peta tiga provinsi (Banten, DKI Jakarta, Jawa Barat) — highlight posisi sebagai pusat ekonomi nasional

**Poin:**
- Tiga provinsi ini menyumbang >40% PDB nasional, tetapi kesenjangan antar-kabupaten/kota sangat besar
- Pandemi COVID-19 (2020) menciptakan guncangan struktural yang dampaknya tidak merata
- Pemulihan 2021–2024 bersifat asimetris: metropolitan cepat pulih, wilayah selatan stagnan
- Pendekatan multivariat konvensional (PCA, Faktor Analisis per tahun) tidak mampu menangkap dinamika **lintas waktu** sekaligus

> **Narasi kunci:** "Pertanyaan yang belum terjawab adalah: apakah ketimpangan ini bersifat sementara akibat pandemi, atau bersumber dari faktor struktural yang jauh lebih dalam?"

---

## Slide 4 — Rumusan Masalah & Tujuan

**Dua pertanyaan penelitian:**

1. Seberapa stabil hierarki relatif antar-kabupaten/kota selama 2020–2024 meskipun terjadi guncangan pandemi?
2. Bagaimana pola trajektori spasio-temporal 41 kabupaten/kota ketika dianalisis secara simultan lintas indikator dan lintas tahun?

**Tujuan:**
- Mengevaluasi stabilitas longitudinal menggunakan koefisien RV (inter-struktur)
- Memetakan trajektori spasio-temporal via Dynamic Biplot
- Mengelompokkan wilayah ke dalam klaster pembangunan yang dapat diinterpretasi secara kebijakan

---

## Slide 5 — Data: 41 Wilayah × 11 Indikator × 5 Tahun

**Visual utama:** Tabel atau infografik 3-panel

**Panel 1 — Wilayah (N = 41):**
- Provinsi Banten (8 kab/kota)
- DKI Jakarta (6 kota/kab)
- Jawa Barat (27 kab/kota)
- Sumber: BPS 2020–2024

**Panel 2 — 11 Indikator:**

| Dimensi | Indikator |
|---|---|
| Ekonomi | PDRB ADHK |
| Kemiskinan | PPM, GK, PKKP |
| Ketenagakerjaan | TPT, TPAK |
| Pendidikan | RLS |
| Kesehatan | AHH Laki-laki, AHH Perempuan |
| Kesetaraan | IPG, Gini Ratio |

**Panel 3 — Pra-pemrosesan:**
- Bobot demografis (proporsi jumlah penduduk) diterapkan sebelum standardisasi Z-score
- Uji kelayakan: KMO dan Bartlett per tahun — seluruhnya signifikan (p < 0,001)

---

## Slide 6 — Metode: Kerangka STATIS (Flowchart 5 Tahap)

**Visual:** Flowchart horizontal dengan 5 kotak

```
[Tahap 1]          [Tahap 2]          [Tahap 3]           [Tahap 4]          [Tahap 5]
Standardisasi  →  Inter-struktur  →  Kompromi Wc     →  Uji Permutasi  →  Dynamic Biplot
Z-score           Koefisien RV       Bobot Spektral      Monte Carlo        + K-Means
terbobot          antar tahun        Optimal             B = 1.000          Clustering
demografis        (5×5 matriks)      (Lavit, 1994)       p < 0,001
```

**Kalimat penjelas 1 baris per tahap:**
- T1: Standarisasi per tahun dengan bobot populasi agar perbandingan lintas waktu adil
- T2: RV mengukur "kemiripan konfigurasi spasial" antar dua tahun (range 0–1)
- T3: Wc adalah rata-rata tertimbang optimal dari semua matriks tahunan
- T4: B=1000 permutasi acak → validasi bahwa struktur bukan artefak
- T5: Proyeksi tiap tahun ke ruang Wc → lintasan pergerakan wilayah terlihat

> **Siap menjawab:** "Kenapa tidak PCA biasa?" → PCA per tahun tidak bisa dibandingkan lintas waktu karena rotasi berubah. STATIS membangun satu ruang referensi stabil (kompromi) lalu memproyeksikan semua tahun ke sana.

---

## Slide 7 — Hasil: Stabilitas Inter-Struktur (Koefisien RV)

**Heading:** *Hierarki Wilayah Tetap Stabil Sepanjang Pandemi dan Pemulihan*

**Visual utama:** Tabel 5×5 heatmap koefisien RV

| | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|
| 2020 | 1,0000 | 0,9555 | 0,9429 | 0,9533 | 0,9545 |
| 2021 | 0,9555 | 1,0000 | 0,9534 | 0,9487 | 0,9396 |
| 2022 | 0,9429 | 0,9534 | 1,0000 | 0,9608 | 0,9497 |
| 2023 | 0,9533 | 0,9487 | 0,9608 | 1,0000 | 0,9827 |
| 2024 | 0,9545 | 0,9396 | 0,9497 | 0,9827 | 1,0000 |

**Interpretasi (3 poin):**
- Seluruh koefisien RV > 0,90 — jauh di atas ambang "sangat konsisten"
- Semua signifikan: p < 0,001 (uji permutasi Monte Carlo, B = 1.000)
- RV terendah = 0,9396 (2021–2024): bahkan puncak-ke-pemulihan pun sangat stabil

**Kesimpulan satu kalimat:**
> "Pandemi menggeser posisi absolut, tetapi tidak mengubah siapa di atas dan siapa di bawah."

---

## Slide 8 — Hasil: Struktur Kompromi — Dua Dimensi Utama

**Visual:** Compromise Biplot (gambar dari skripsi halaman xiii / Gambar 1 Extended Abstract)

**Anotasi pada gambar:**
- Dim 1 (60,85%) = **"Kapasitas Sosio-Ekonomi"** → loading tinggi: PDRB, IPM, RLS
- Dim 2 (11,03%) = **"Resiliensi Sosial & Kesehatan"** → loading tinggi: AHH, IPG
- Total variansi tjelaskan dua dimensi: **>71%** (>85% jika gabungkan semua komponen)

**Posisi ekstrem wilayah:**
- Kanan jauh (Dim 1 tinggi): **Kota Jakarta Pusat** (3,87; −1,19) → paling maju secara ekonomi
- Bawah jauh (Dim 2 rendah): **Kab. Pangandaran** (−3,17; −4,83) → paling tertinggal
- Kiri tengah: Lebak, Garut, Cianjur — zona merah ketertinggalan struktural

> **Siap menjawab:** "Kenapa hanya 2 dimensi?" → Scree plot menunjukkan penurunan tajam setelah Dim 2. Dua dimensi sudah cukup untuk interpretasi substantif dan visualisasi.

---

## Slide 9 — Hasil: Tiga Pola Trajektori (Dynamic Biplot)

**Visual utama:** Trajectory Plot (gambar dari skripsi halaman xiv / Gambar 2 Extended Abstract)

**Tiga pola trajektori:**

| Pola | Wilayah Contoh | Karakteristik |
|---|---|---|
| **V-Shape Recovery** | Jakarta Pusat, Bandung | Kontraksi 2020–2021, rebound kuat ke 2024 |
| **Stagnant** | Lebak (TPAK −2,12; −2,21), Garut, Pangandaran | Hampir tidak bergerak selama 5 tahun |
| **Progressive Growth** | Kota-kota penyangga (Depok, Tangerang) | Pertumbuhan kontinu tanpa kontraksi berarti |

**Kalimat kunci:**
> "Dynamic Biplot membuktikan bahwa trajectory ≠ level. Kota Depok bukan yang paling maju, tapi konsistensi pertumbuhannya adalah yang paling stabil di antara wilayah penyangga."

---

## Slide 10 — Hasil: Klaster K-Means dan Validasi IPM UNDP

**Visual:** Peta choropleth tiga warna (Maju/Berkembang/Tertinggal) + tabel validasi

**Klaster (k = 3, ditentukan via Elbow Method + Silhouette Score):**

| Klaster | Label | Karakteristik Utama |
|---|---|---|
| Klaster 1 | **Maju** | Dim1 tinggi, IPM "Sangat Tinggi" UNDP, semua kab/kota DKI Jakarta |
| Klaster 2 | **Berkembang** | Dim1 sedang, campuran kab/kota Jabar dan beberapa Banten utara |
| Klaster 3 | **Tertinggal** | Dim1 & Dim2 rendah, didominasi kab. selatan Banten & Jabar (Lebak, Garut, Pangandaran, Cianjur) |

**Validasi Eksternal:**
- Klaster Maju → konsisten 100% dengan kategori IPM "Sangat Tinggi" UNDP
- Ini membuktikan: klaster bukan artefak statistik, tapi mencerminkan struktur nyata

> **Implikasi kebijakan:** Pemerataan pembangunan tidak bisa dengan kebijakan seragam — klaster Tertinggal membutuhkan intervensi berbeda karena bersumber dari faktor struktural persisten, bukan sekadar dampak pandemi.

---

## Slide 11 — [OPSIONAL] Demo: Interactive Dashboard Python

**Heading:** *Kontribusi Kebaruan: Sistem Dashboard Interaktif*

**Konten (sambil buka browser/demo langsung):**
- Dibangun dengan Python (Plotly + Dash)
- Fitur: uji diagnostik KMO/Bartlett interaktif, biplot interaktif, peta spasial klaster, trajectory animation
- Output otomatis: ekspor ke LaTeX dan Excel
- Ditujukan untuk: peneliti dan pemangku kebijakan yang tidak berlatar statistik

> "Ini yang membedakan penelitian ini dari analisis STATIS sebelumnya — bukan hanya hasilnya, tapi aksesibilitasnya."

---

## Slide 12 — Kesimpulan

**Tiga temuan utama:**

1. **Stabilitas Struktural Terbukti**
   Seluruh koefisien RV > 0,90 (p < 0,001). Hierarki relatif antar-wilayah tetap konsisten sepanjang 2020–2024 meskipun terjadi pandemi global.

2. **Dua Dimensi Pembangunan Teridentifikasi**
   Dim 1 "Kapasitas Sosio-Ekonomi" (60,85%) dan Dim 2 "Resiliensi Sosial & Kesehatan" (11,03%) menjelaskan lebih dari 71% total variansi bersama.

3. **Tiga Pola Trajektori dan Tiga Klaster**
   Metropolitan: V-shape recovery. Selatan: stagnant. Penyangga: progresif. Klaster Maju/Berkembang/Tertinggal selaras dengan IPM UNDP → kesenjangan bersumber dari faktor struktural persisten.

---

## Slide 13 — Keterbatasan & Saran

**Keterbatasan:**
- Cakupan terbatas 3 provinsi Jawa bagian Barat (41 kab/kota) → generalisasi ke Jawa Timur, Sulawesi, dll. memerlukan verifikasi
- Rentang waktu 5 tahun (2020–2024) — tren sebelum pandemi tidak terlihat
- 11 indikator terpilih mewakili data BPS yang tersedia; ada dimensi (lingkungan, infrastruktur) yang belum masuk

**Saran Penelitian Lanjutan:**
- Perpanjang ke 10 tahun (2015–2024) untuk melihat tren pra-pandemi
- Integrasikan indikator lingkungan dan akses infrastruktur
- Replikasi metode STATIS ke 34 provinsi untuk peta nasional
- Kembangkan dashboard ke versi publik real-time berbasis API BPS

---

## Slide 14 — Kontribusi & Kebaruan Penelitian

**Dua kontribusi utama:**

1. **Metodologi:** Penerapan **pertama** metode STATIS untuk analisis dinamika pembangunan regional pascapandemi di konteks Jawa bagian Barat

2. **Produk:** Sistem dashboard web interaktif berbasis Python yang mengintegrasikan:
   - Uji diagnostik otomatis (KMO, Bartlett)
   - Visualisasi biplot dan trajektori interaktif
   - Ekspor otomatis ke LaTeX dan Excel

---

## Slide 15 — Penutup & Terima Kasih

**Ucapan terima kasih kepada:**
- Dr. Dra. Yekti Widyaningsih, M.Si. — Pembimbing
- Sarini Abdullah, S.Si., M.Stats., Ph.D. — Penguji I
- Gianinna Ardaneswari, S.Si., M.Si. — Penguji II

**Kalimat penutup:**
> "Penelitian ini menunjukkan bahwa di balik fluktuasi angka ekonomi selama pandemi, ada pola struktural yang jauh lebih dalam dan persisten. Memahami pola itu adalah prasyarat untuk kebijakan yang benar-benar tepat sasaran."

**Q&A**

---

## Lampiran: Antisipasi Pertanyaan Penguji

### Dari Penguji I — Sarini Abdullah (Statistikawan)

**Q: Kenapa menggunakan koefisien RV, bukan korelasi Pearson biasa antar matriks?**
> A: Korelasi Pearson hanya berlaku untuk vektor. Koefisien RV adalah generalisasi untuk membandingkan dua matriks SPD (symmetric positive definite) — ia mengukur kemiripan struktur dua konfigurasi multivariat sekaligus, bukan hanya dua variabel. RV = tr(S1·S2) / sqrt(tr(S1²)·tr(S2²)).

**Q: Mengapa k=3 pada K-Means? Apakah sudah divalidasi?**
> A: Ya. Dua metode digunakan: (1) Elbow Method — penurunan Within-Cluster Sum of Squares melandai setelah k=3; (2) Silhouette Score — nilai tertinggi ada di k=3. Selain itu, k=3 selaras secara substantif dengan kategori IPM UNDP (Sangat Tinggi / Tinggi / Sedang-Rendah), yang memperkuat validitas eksternal.

**Q: Apa bedanya Skenario 1 dan Skenario 2 dalam skripsi?**
> A: Skenario 1 menggunakan bobot intra-struktur berbasis korelasi antar-indikator (bobot wilayah). Skenario 2 menggunakan bobot berimbang (equal weighting) sebagai pembanding. Keduanya menghasilkan matriks inter-struktur yang identik, membuktikan robustness hasil terlepas dari skema pembobotan.

**Q: Apa interpretasi Dimensi 2 yang hanya 11%?**
> A: Walaupun proporsinya kecil, Dim 2 secara substantif penting karena memisahkan wilayah dengan AHH (Angka Harapan Hidup) tinggi dari yang rendah — ini dimensi kesehatan dan ketahanan pangan. Pangandaran yang unik: ekonominya lemah DAN AHH-nya rendah — jauh di sudut kiri bawah biplot.

### Dari Penguji II — Gianinna Ardaneswari (Kaprodi)

**Q: Apa implikasi kebijakan konkret dari hasil ini?**
> A: Ada tiga implikasi: (1) Jangan pakai kebijakan seragam — klaster Tertinggal (Lebak, Garut, Pangandaran) butuh intervensi berbeda dari klaster Berkembang. (2) Fokus pada Dim 2: kesehatan dan ketahanan pangan adalah bottleneck untuk naik kelas. (3) Wilayah penyangga (Depok, Tangerang) menunjukkan trajektori progresif — replikasi model pembangunannya.

**Q: Apakah ada uji autokorelasi spasial?**
> A: Ya, ada di Bab 4.9–4.10. Global Moran's I digunakan untuk menguji apakah klaster yang terbentuk juga menunjukkan pengelompokan spasial (wilayah maju cenderung berdekatan). Hasilnya signifikan — ada spatial autocorrelation, artinya efek tetangga (spillover) nyata.

**Q: Kenapa tidak menggunakan data per kecamatan untuk resolusi lebih tinggi?**
> A: Data 11 indikator BPS ini hanya tersedia lengkap di level kabupaten/kota. Data kecamatan tidak konsisten dan banyak missing value, sehingga akan merusak asumsi keseimbangan panel yang dibutuhkan STATIS.

---

## Catatan Teknis Presentasi

- **Durasi target:** 15 menit presentasi + 30 menit tanya jawab
- **Urutan navigasi darurat:** Jika penguji langsung tanya, lompat ke slide 7 (RV), 8 (Biplot), atau 10 (Klaster)
- **Satu gambar per slide hasil** — jangan ramai, biarkan visual bicara
- **Font minimal 24pt** untuk body text agar terbaca dari jarak 3 meter
- **Demo dashboard:** siapkan browser sudah terbuka di tab terpisah sebelum presentasi mulai
