# OUTPUT_APP.md — Katalog Output Dashboard & Pemetaan ke Bab 4

> **Konteks:** Dashboard di `web/skripsiv2/app.py` menganalisis data 41 kabupaten/kota di Provinsi Banten, DKI Jakarta, dan Jawa Barat tahun 2020–2024 menggunakan metode STATIS & Dynamic Biplot.
> **Tujuan dokumen ini:** Menginventarisasi *semua* output visual/tabel yang dihasilkan dashboard dan memetakannya ke rumusan masalah + struktur Bab 4.

> [!NOTE]
> Semua file di-generate otomatis oleh `export_all.py` dengan input `data/data2.xlsx`. Jalankan ulang script setiap kali data berubah:
> ```
> cd d:\Skripsi\my
> python export_all.py
> ```

---

## Pemetaan Rumusan Masalah → Seksi Bab 4

| # | Rumusan Masalah (Bab 1) | Seksi Bab 4 | Output |
|---|---|---|---|
| 1 | Karakteristik struktur kompromi STATIS | 4.3 Analisis Struktur Kompromi | Biplot Kompromi, Scree Plot, Loading Chart |
| 2 | Uji signifikansi struktur (permutasi) | 4.4 Uji Stabilitas | Histogram Permutasi |
| 3 | Pola lintasan (*trajectory*) 2020–2024 | 4.5 Analisis Trajektori | Dynamic Biplot 3D, Grafik 2D, Tabel Trajektori |
| 4 | Pengelompokan & transisi klaster | 4.6 Analisis Klaster | Peta Klaster, Scatter Klaster, Matriks Transisi |

---

## Rekomendasi Urutan Penulisan Bab 4

```
4.1  Eksplorasi Data Awal       → output_table_deskriptif_*.tex, boxplot_*_*.png
4.2  Analisis Inter-struktur    → rv_heatmap.png, output_table_rv.tex
4.3  Struktur Kompromi          → scree_plot.png, compromise_map.png, cluster_compromise_biplot.png,
                                   loading_plot.png, output_table_alpha.tex, output_table_eigen.tex,
                                   output_table_scores.tex, output_table_loadings.tex
4.4  Uji Stabilitas (Permutasi) → permutation_histogram.png, output_perm_statis.tex
4.5  Dinamika Trajektori        → statis_trajectories.png, biplot_tahun_*.png
4.6  Analisis Klaster           → elbow_plot_*.png, dendrogram_*.png, cluster_biplot_*.png,
                                   output_table_transition_matrix_*.tex,
                                   output_table_ipm_matrix_*.tex,
                                   output_table_cross_matrix_*.tex,
                                   output_table_cluster_members.tex
```

---

## Daftar File (129 total di folder ini)

### Gambar (PNG)

#### STATIS & Kompromi

| Seksi | Nama File | Keterangan |
|---|---|---|
| 4.2 | `rv_heatmap.png` | Heatmap koefisien RV antar-tahun |
| 4.3 | `scree_plot.png` | Scree plot eigenvalue + kumulatif variansi |
| 4.3 | `compromise_map.png` | Peta 41 kab/kota di ruang kompromi |
| 4.3 | `cluster_compromise_biplot.png` | Biplot kompromi: skor + vektor loading |
| 4.3 | `loading_plot.png` | Loading plot dalam correlation circle |
| 4.3 | `variable_contribution.png` | Kontribusi variabel ke Dimensi 1 (%) |
| 4.3 | `variable_cos2.png` | Kualitas representasi variabel (cos²) |
| 4.4 | `permutation_histogram.png` | Distribusi null vs λ_obs, **p = 0.0010** (Signifikan) |
| 4.5 | `statis_trajectories.png` | Lintasan 41 kab/kota 2020–2024 |

#### Biplot Snapshot per Tahun (5 file)

`biplot_tahun_2020.png` · `biplot_tahun_2021.png` · `biplot_tahun_2022.png` · `biplot_tahun_2023.png` · `biplot_tahun_2024.png`

#### Evaluasi & Klaster per Tahun

| Seksi | Nama File | Keterangan |
|---|---|---|
| 4.6.1 | `elbow_plot_2020.png` … `elbow_plot_2024.png` | Kurva Elbow (5 file) |
| 4.6.1 | `dendrogram_2020.png` … `dendrogram_2024.png` | Dendrogram Ward (5 file) |
| 4.6.1 | `dendrogram_compromise.png` | Dendrogram klaster trajektori keseluruhan |
| 4.6.2 | `cluster_biplot_2020.png` … `cluster_biplot_2024.png` | Biplot K-Means (5 file) |

#### Boxplot Variabel (60 file — Seksi 4.1)

Format: `boxplot_<variabel>_<tahun>.png` — 12 variabel × 5 tahun.

Variabel: `ipm`, `ipg`, `ppm`, `pdrb_adhk`, `rls`, `ahh_l`, `ahh_p`, `gk`, `pkkp`, `tpt`, `tpak`, `gr`

---

### Tabel (.tex) — Siap `\input{}` ke LaTeX

#### STATIS Core

| Seksi | Nama File | Isi |
|---|---|---|
| 4.2 | `output_table_rv.tex` | Matriks koefisien RV 5×5 |
| 4.3 | `output_table_alpha.tex` | Bobot α tiap tahun |
| 4.3 | `output_table_eigen.tex` | Eigenvalue, variansi %, kumulatif % |
| 4.3 | `output_table_scores.tex` | Skor kompromi Fc — longtable 41 baris |
| 4.3 | `output_table_loadings.tex` | Korelasi variabel vs PC1, PC2 |
| 4.6 | `output_table_cluster_members.tex` | Anggota klaster trajektori keseluruhan |

#### Statistika Deskriptif (5 file)

`output_table_deskriptif_2020.tex` … `output_table_deskriptif_2024.tex`

#### Matriks Transisi Klaster (8 file)

| Seksi | Nama File | Isi |
|---|---|---|
| 4.6.2 | `output_table_transition_matrix_sum_2020x2021.tex` … `_2023x2024.tex` | Jumlah perpindahan (4 file) |
| 4.6.2 | `output_table_transition_matrix_name_2020x2021.tex` … `_2023x2024.tex` | Nama daerah (4 file) |

#### Matriks Transisi IPM (8 file)

| Seksi | Nama File | Isi |
|---|---|---|
| 4.6.3 | `output_table_ipm_matrix_sum_2020x2021.tex` … `_2023x2024.tex` | Jumlah per kategori IPM (4 file) |
| 4.6.3 | `output_table_ipm_matrix_name_2020x2021.tex` … `_2023x2024.tex` | Nama daerah (4 file) |

#### Tabulasi Silang K-Means vs IPM (10 file)

| Seksi | Nama File | Isi |
|---|---|---|
| 4.6.3 | `output_table_cross_matrix_sum_2020.tex` … `_2024.tex` | Jumlah per sel (5 file) |
| 4.6.3 | `output_table_cross_matrix_name_2020.tex` … `_2024.tex` | Nama daerah per sel (5 file) |

#### Makro LaTeX

| File | Isi |
|---|---|
| `output_core_statis.tex` | `\statisAlphaTahunA`…`E`, `\statisEigenA`, `\statisInertiaA` |
| `output_perm_statis.tex` | `\statisPValue` (= 0.0010), `\statisKet` |
