# Spatio-Temporal Analysis of Socio-Economic Dynamics (STATIS & Dynamic Biplot)

**Skripsi (Undergraduate Thesis) Project**
*Studi Kasus: Provinsi Banten, DKI Jakarta, dan Jawa Barat (2020-2024)*

## 📌 Project Overview
Penelitian ini bertujuan untuk memetakan dinamika pembangunan ekonomi regional pasca-pandemi COVID-19 menggunakan metode statistika multivariat lanjut. Mengingat kompleksitas data yang melibatkan tiga dimensi (Wilayah x Indikator x Waktu), metode konvensional seperti PCA statis atau Regresi Data Panel dianggap kurang memadai untuk memvisualisasikan perubahan struktural.

Oleh karena itu, proyek ini mengimplementasikan metode **STATIS** (*Structuration des Tableaux à Trois Indices de la Statistique*) yang dikombinasikan dengan **Dynamic Biplot** untuk menghasilkan visualisasi lintasan (*trajectory*) pergerakan ekonomi setiap kabupaten/kota dari masa krisis menuju pemulihan.

## 🛠️ Technology Stack
Proyek ini terdiri dari dua komponen utama:
1.  **Analisis & Dashboard (Python):**
    *   **Backend Analisis:** `numpy`, `pandas`, `scikit-learn` (Implementasi manual algoritma STATIS).
    *   **Visualisasi:** `plotly` (Grafik interaktif 3D & 2D).
    *   **Dashboard Framework:** `dash` (Web-based interface).
    *   **Geospatial:** `geopandas` (Peta Choropleth).

2.  **Laporan Skripsi (LaTeX):**
    *   Struktur dokumen formal Universitas Indonesia (UI).
    *   Automasi sitasi dengan `bibtex`.

## 📂 Project Structure
```
d:/Skripsi/my/
├── web/                   # IMPLEMENTASI PYTHON
│   ├── final.py           # Main Application Code (Dashboard)
│   ├── requirements.txt   # Python Dependencies
│   ├── gadm41_IDN_2.shp   # Shapefile Peta Indonesia (Level Kabupaten)
│   └── FINAL DATA.xlsx    # Dataset Input (Multisheet per Tahun)
│
├── induk.tex              # LEAF DOCUMENT (Main LaTeX File)
├── bab1.tex               # Pendahuluan
├── bab2.tex               # Landasan Teori
├── bab3.tex               # Metodologi
├── bab4.tex               # Hasil dan Pembahasan
├── bab5.tex               # Kesimpulan dan Saran
├── pustaka.bib            # Referensi
└── ...                    # File pendukung lainnya
```

## 🚀 How to Run (Dashboard)
1.  **Prerequisites:** Pastikan Python 3.8+ terinstall.
2.  **Install Dependencies:**
    ```bash
    pip install -r web/requirements.txt
    ```
    *(Note: Butuh library `scipy` untuk fitur Clustering)*
3.  **Run Application:**
    Masuk ke direktori `web` dan jalankan:
    ```bash
    python final.py
    ```
4.  **Access:** Buka browser di `http://127.0.0.1:8050/`.

## 🤖 Automasi LaTeX (export_all.py)
Skrip `export_all.py` digunakan untuk menghasilkan seluruh aset visual (PNG) dan tabel (TEX) secara otomatis agar dapat langsung di-include oleh file LaTeX (`induk.tex`).

### Cara Penggunaan:
1.  **Run Default (Interactive):**
    ```bash
    python export_all.py
    ```
    *Anda akan diminta memilih tipe rotasi biplot, tahun dasar, dan wilayah yang di-highlight via terminal.*

2.  **Run Headless (Automated - Rekomendasi):**
    ```bash
    python export_all.py --headless
    ```
    *Gunakan flag ini untuk melewati semua input manual. Skrip akan menggunakan pengaturan default (PC1-ranking, no highlight) dan langsung menyimpan semua aset (150+ file) ke folder `output_app/`.*

3.  **Kustomisasi Data & Output:**
    ```bash
    python export_all.py path/ke/data_anda.xlsx folder_output_kustom
    ```
    *Secara default, data diambil dari `data/data2.xlsx` dan hasil disimpan di `output_app/`. Tersedia juga `data/data2_sample.xlsx` untuk uji coba cepat.*

### Apa yang dihasilkan?
Seluruh file di `output_app/` dirancang agar nama filenya sinkron dengan perintah `\input{...}` atau `\includegraphics{...}` di dalam `bab3.tex` dan `bab4.tex`. Pastikan folder ini selalu terupdate sebelum melakukan kompilasi PDF akhir.

## 📊 SWOT Analysis (Self-Evaluation)
Analisis kekuatan, kelemahan, peluang, dan ancaman dari penelitian skripsi ini.

| **STRENGTHS (Kekuatan)** | **WEAKNESSES (Kelemahan)** |
| :--- | :--- |
| **1. Metode Advanced & Robust:** Penggunaan metode STATIS mampu menangani data 3-arah tanpa merusak struktur tahunan, lebih unggul dari metode konvensional. <br> **2. Output Visualisasi Kuat:** Dashboard interaktif (*Dynamic Biplot 3D*) memberikan nilai tambah signifikan dibandingkan laporan statis biasa. <br> **3. Relevansi Tinggi:** Topik pemulihan pasca-pandemi sangat relevan dengan isu terkini. | **1. Ketergantungan Data Sekunder:** Validitas sangat bergantung pada kualitas data publikasi BPS (Macro-level). <br> **2. Kompleksitas Interpretasi:** Hasil *Biplot* & *Compromise Plane* membutuhkan pemahaman statistik mendalam untuk dipahami orang awam. <br> **3. Resolusi Data Terbatas:** Data tahunan ($T=5$) mungkin kurang sensitif menangkap fluktuasi jangka pendek (bulanan). |

| **OPPORTUNITIES (Peluang)** | **THREATS (Ancaman)** |
| :--- | :--- |
| **1. Publikasi Jurnal:** Metodologi ini masih jarang digunakan di studi regional Indonesia, potensi tinggi untuk tembus jurnal Sinta 2/Scopus. <br> **2. Alat Bantu Kebijakan:** Dashboard dapat dikembangkan menjadi *Early Warning System* bagi Pemda untuk memantau ketimpangan. <br> **3. Skalabilitas:** Model mudah direplikasi untuk menganalisis provinsi lain atau sektor lain (misal: Pertanian). | **1. Perubahan Definisi BPS:** Jika BPS mengubah metode perhitungan indikator (misal: Garis Kemiskinan) di tengah jalan, konsistensi data terganggu. <br> **2. Pertanyaan Penguji:** Risiko pertanyaan menjebak seputar "Signifikansi Ekonomi vs Signifikansi Statistik". <br> **3. Technical Debt:** Kode Python perlu *maintenance* jika di-deploy jangka panjang (update library). |

---
*Created automatically by AI Assistant as part of Thesis Mentoring.*
