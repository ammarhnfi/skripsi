# Mapping: `export_all.py` ↔ `web/app.py` ↔ `App.jsx`

Dokumen ini memetakan setiap file `.tex` dan `.png` yang disimpan oleh
`debug/export_all.py` ke bagian (section/callback) yang menghasilkan
output yang sama secara interaktif di `web/app.py`, dan ke komponen
`landing-page/src/App.jsx` yang menampilkannya.

**Direktori output (source):**
- `export_all.py` → `output_real/`, `output_real/scenario1/`, `output_real/scenario2/`

**Direktori serve (landing page):**
- `prepare_landing_assets.py` → `landing-page/public/output_real/`, `landing-page/public/output_sample/`
- Manifest: `output_real_manifest.json`, `output_sample_manifest.json`

**App.jsx manifest loading:** Fetch `/output_real_manifest.json` dan `/output_sample_manifest.json`

---

## 0. Cara File Dilayani ke App.jsx

```
output_real/
├── (file ROOT — sama untuk kedua skenario)
└── scenario1/ | scenario2/
    └── (file PER SKENARIO)

→ prepare_landing_assets.py meng-copy ke landing-page/public/output_real/
→ Manifest JSON menyimpan { name, src, caption, type, group, scenario }
→ App.jsx membaca manifest dan menampilkan file via <img src="/output_real/...">
```

**Grup di manifest (diset oleh `prepare_landing_assets.py → get_group()`):**

| Grup | Tipe File |
|------|-----------|
| `Distribusi Variabel` | `boxplot_*.png` |
| `Snapshot Biplot` | `biplot_tahun_*.png` |
| `Biplot Klaster` | `cluster_biplot_*.png`, `cluster_scatter_*.png` |
| `Peta Klaster` | `cluster_map_*.png`, `cluster_pie_*.png` |
| `Dendrogram` | `dendrogram_*.png` |
| `Elbow Plot` | `elbow_plot_*.png` |
| `Hasil Utama STATIS` | `compromise_map.png`, `compromise_scatter.png`, `compromise_biplot.png`, `compromise_pie.png`, `scree_plot.png`, `rv_heatmap.png`, `trajectory_*.png`, `variable_*.png`, `beta_trajectory.png`, `permutation_histogram.png` |
| `Korelasi & Diagnostik` | `corr_heatmap_*.png` |
| `Peta & Distribusi IPM` | `ipm_map_*.png`, `ipm_pie_*.png` |
| `Perbandingan Bersandingan` | `compare_*.png` |
| `Tabel Hasil (.tex)` | `output_table_*.tex` |
| `Lain-lain` | `matrix_*.tex`, `output_macros.tex`, `output_core_statis.tex`, `output_perm_statis.tex`, `output_moran.tex` |

---

## 1. ROOT `output_real/` — berlaku untuk kedua skenario

### Boxplot Indikator

| File | Lokasi | app.py | App.jsx |
|------|--------|--------|---------|
| `boxplot_{indicator}.png` | ROOT | Section 2: `cb_run_desc` (L5049) | CompareDashboard → tab "Boxplots" → `rootPngFiles` |

> Satu file per indikator, menampilkan distribusi semua tahun sekaligus. **Tidak ada suffix tahun.**

### Tabel Statistika Deskriptif

| File | Lokasi | app.py |
|------|--------|--------|
| `output_table_deskriptif_{yr}.tex` (2020–2024) | ROOT | Section 2: `cb_run_desc` (L5028) — Unweighted |
| `output_table_descriptive_{yr}.tex` (2020–2024) | ROOT | Section 2: `cb_run_desc_multi` (L5201) — Weighted demografis |

### Uji Diagnostik (KMO & Bartlett)

| File | Lokasi | app.py |
|------|--------|--------|
| `output_table_kmo_bartlett.tex` | ROOT | Section 3: `cb_diag_math` (L3220) |

### Heatmap Korelasi Pearson

| File | Lokasi | app.py | App.jsx |
|------|--------|--------|---------|
| `corr_heatmap_{yr}.png` (2020–2024) | ROOT | Section 3: baru — heatmap Pearson per tahun | Gallery → grup "Korelasi & Diagnostik" |

> **Grup App.jsx:** "Korelasi & Diagnostik". Judul: `Heatmap Korelasi Pearson Indikator Tahun {yr}`.

### Biplot Unweighted PCA (per tahun) — ROOT

| File | Lokasi | app.py |
|------|--------|--------|
| `biplot_tahun_{yr}.png` (ROOT) | ROOT | Section 3: `cb_update_plots` (L3248) — PCA tanpa bobot |

### Clustering Tahunan Unweighted (Biplot PCA) — ROOT

| File | Lokasi | app.py |
|------|--------|--------|
| `cluster_scatter_biplot_{yr}.png` | ROOT | Section 6: `cb_render_trans_plots` (L5634) |
| `cluster_map_biplot_{yr}.png` | ROOT | Section 6: peta choropleth klaster Biplot |
| `cluster_pie_biplot_{yr}.png` | ROOT | Section 6: pie proporsi klaster Biplot |

> Identik untuk kedua skenario (unweighted PCA). Disimpan di ROOT, bukan scenario1/2.

### Evaluasi Jumlah Klaster — Unweighted (ROOT)

| File | Lokasi | app.py |
|------|--------|--------|
| `elbow_plot_{yr}.png` (ROOT) | ROOT | Section 5: `cb_eval_cluster` (L5393) |
| `dendrogram_{yr}.png` (ROOT) | ROOT | Section 5: `cb_eval_cluster` (L5403) |

### Matriks Transisi Klaster Biplot (ROOT)

| File | Lokasi | app.py |
|------|--------|--------|
| `output_table_biplot_transition_sum_{pair}.tex` | ROOT | Section 6: `cb_calc_trans` (L5420) |
| `output_table_biplot_transition_name_{pair}.tex` | ROOT | Section 6: nama kabupaten per sel |

> Pair format: `{y1}x{y2}` (mis. `2020x2021`, …, `2023x2024`).
> App.jsx: `isRootFile = activeFilename.startsWith('output_table_biplot_transition_')` — ditampilkan tanpa split skenario.

### Peta & Distribusi Kategori IPM (ROOT)

| File | Lokasi | app.py |
|------|--------|--------|
| `ipm_map_{yr}.png` (2020–2024) | ROOT | Section 8: peta choropleth kategori IPM |
| `ipm_pie_{yr}.png` (2020–2024) | ROOT | Section 8: pie proporsi kategori IPM |

### Matriks Korelasi Inter-Struktur (ROOT — sama s1 dan s2)

| File | Lokasi | app.py |
|------|--------|--------|
| `output_table_rv_w.tex` | ROOT | Section 4 → tab "Matriks RV (R_W)" |
| `output_table_rv_s.tex` | ROOT | Section 4 → tab "Matriks RV (R_S)" |
| `output_table_hw.tex` | ROOT | Section 4 → tab "Matriks H_W" |
| `output_table_hs.tex` | ROOT | Section 4 → tab "Matriks H_S" |
| `output_table_alpha_w.tex` | ROOT | Section 4 → tab "Bobot (α_W)" |
| `output_table_alpha_s.tex` | ROOT | Section 4 → tab "Bobot (α_S)" |

---

## 2. Per-Skenario `scenario1/` dan `scenario2/`

> Skenario 1 = Host Wilayah (`H_W`, `R_W`, `alphas_W`)
> Skenario 2 = Host Indikator (`H_S`, `R_S`, `alphas_S`)

### Tabel Hasil STATIS (Kompromi)

| File | app.py |
|------|--------|
| `output_table_alpha.tex` | Section 4 → tab "Bobot (α)" per skenario |
| `output_table_eigen.tex` | Section 4 → tab "Nilai Eigen (Λ_c)" |
| `output_table_loadings.tex` | Section 4 → tab "Loadings Kompromi (G_c)" |
| `output_table_scores.tex` | Section 4 → tab "Skor Kompromi (F_c)" |

### Matriks Kompromi (pmatrix LaTeX)

| File | app.py |
|------|--------|
| `matrix_G_c.tex` | Section 4 → formula panel `render_statis_formulas` (L231) |
| `matrix_V_c.tex` | Section 4 → matriks eigenvalue diagonal V_c |
| `matrix_F_c.tex` | Section 4 → matriks skor kompromi F_c |

### Makro LaTeX Numerik

| File | app.py |
|------|--------|
| `output_macros.tex` | Section 4 → nilai ringkasan (α, RV, Dim%, λ_obs, KMO); `export_core_latex` (L745) |
| `output_core_statis.tex` | Section 4 → `\newcommand` per skenario; `export_core_latex` (L745) |
| `output_perm_statis.tex` | Section 4 → Permutation Test (`\statisPValue`, `\statisKet`); `export_perm_latex` (L860) |
| `output_moran.tex` | Section 7 → Moran's I (`\{Pfx}MoranI`, etc.); `cb_run_clustering_trajectory` (L6040) |

### Visualisasi STATIS (Scree, Heatmap, Biplot)

| File | app.py |
|------|--------|
| `scree_plot.png` | Section 4 → Scree Plot |
| `rv_heatmap.png` | Section 4 → Interstructure RV Heatmap |
| `compromise_biplot.png` | Section 4 → Compromise Biplot (Matplotlib hi-res) |
| `compromise_scatter.png` | Section 7 → Scatter Klaster pada Ruang Kompromi |
| `compromise_map.png` | Section 7 → Peta Choropleth Klaster Keseluruhan |
| `compromise_pie.png` | Section 7 → Pie proporsi klaster kompromi |
| `variable_contribution.png` | Section 4 → Kontribusi Variabel (PC1) |
| `variable_cos2.png` | Section 4 → Kualitas Representasi Cos² |
| `permutation_histogram.png` | Section 4 → Histogram Distribusi Null Permutasi |
| `beta_trajectory.png` | Section 4 → Plot β̃_k Lintasan Temporal |

### Vektor Struktur β̃_k

| File | app.py |
|------|--------|
| `output_table_beta_vec.tex` | Section 4 → tab "Vektor Struktur (β) - Gabungan" |
| `output_table_struktur_diagnostik.tex` | Section 4 → tab "Diagnostik Vektor Struktur" |
| `output_table_beta_provinsi.tex` | Section 4 → tab "Vektor Struktur (β) - Per Provinsi" |

### Dynamic Biplot STATIS — Trajektori & Snapshot Intra

| File | app.py |
|------|--------|
| `trajectory_scores.png` | Section 3B → Trajektori Skor (Wildye 2D) |
| `trajectory_loadings.png` | Section 3B → Trajektori Loading Indikator |
| `biplot_tahun_{yr}.png` (scenario) | Section 3B → Snapshot Biplot Intra Berbobot per Tahun |

### Skor & Loading Intra-Tahun

| File | app.py |
|------|--------|
| `output_table_skor_intra_{yr}.tex` (2020–2024) | Section 3B → tab "Skor Intra F_k" |
| `output_table_loading_intra_{yr}.tex` (2020–2024) | Section 3B → tab "Loading Intra G_k" |
| `output_table_matriks_intra_loading_{yr}.tex` (2020–2024) | Section 3B → tab "Matriks Korelasi S_k" |
| `output_table_jarak_skor_{yr}.tex` (2020–2024) | Section 3C → Jarak Skor Euclidean |
| `output_table_jarak_loading_{yr}.tex` (2020–2024) | Section 3C → Jarak Loading Euclidean |

### Evaluasi Jumlah Klaster — Weighted STATIS (per skenario)

| File | app.py |
|------|--------|
| `elbow_plot_{yr}.png` (scenario) | Section 5: `cb_eval_cluster` (L5373) |
| `dendrogram_{yr}.png` (scenario) | Section 5: `cb_eval_cluster` (L5373) |

### Clustering Tahunan STATIS Berbobot

| File | app.py |
|------|--------|
| `cluster_scatter_statis_{yr}.png` (2020–2024) | Section 6B → Scatter K-Means Weighted |
| `cluster_map_statis_{yr}.png` (2020–2024) | Section 6B → Peta Choropleth Klaster per Tahun |
| `cluster_pie_statis_{yr}.png` (2020–2024) | Section 6B → Pie proporsi klaster STATIS per Tahun |
| `output_table_statis_transition_sum_{pair}.tex` | Section 6B → Matriks Transisi Klaster STATIS |
| `output_table_statis_transition_name_{pair}.tex` | Section 6B → Nama daerah per sel transisi |

> `cluster_map_statis_*.png` SELALU per skenario (berbeda Fk dan Gk antar skenario).
> Pair format: `{y1}x{y2}` (2020x2021, …, 2023x2024).

### Ringkasan Anggota Klaster Kompromi

| File | app.py | App.jsx |
|------|--------|---------|
| `output_table_compromise_cluster_sum_name.tex` | Section 7 → Tabel anggota klaster kompromi | Tab "Tabel Hasil (.tex)" di CompareDashboard |

> **Format tabel:** 3 kolom — Kelompok (Cluster) | Jumlah Wilayah | Daftar Kabupaten/Kota  
> **Label LaTeX:** `tab:{prefix}compromclust` (mis. `tab:app1compromclust`, `tab:app2compromclust`)

---

## 3. Pemetaan 9 Perbandingan (SCENARIO_ONLY)

> - **ROOT**: ditulis sekali ke `output_real/` langsung  
> - **SCENARIO**: ditulis ke `output_real/scenario1/` DAN `output_real/scenario2/`
>
> App.jsx mengambil file dari manifest. Comparison panel (`ComparisonPanel`) menampilkan
> side-by-side: `/${folder}/scenario1/${file}` vs `/${folder}/scenario2/${file}`.

---

### Perbandingan 1 — Transisi STATIS Tahunan

**App.jsx mode:** `comp_2_trans_statis` | **Format:** `{pair}`

| File | Lokasi | Keterangan |
|------|--------|------------|
| `output_table_statis_transition_sum_{pair}.tex` | SCENARIO | Matriks transisi klaster STATIS berbobot (jumlah) |
| `output_table_statis_transition_name_{pair}.tex` | SCENARIO | Nama daerah per sel transisi klaster STATIS |
| `compare_map_trans_statis_{pair}.png` | SCENARIO | Peta klaster STATIS tahun t₁ dan t₂ |
| `compare_scatter_trans_statis_{pair}.png` | SCENARIO | Scatter klaster STATIS tahun t₁ dan t₂ |
| `compare_pie_trans_statis_{pair}.png` | SCENARIO | Pie proporsi klaster STATIS tahun t₁ dan t₂ |

---

### Perbandingan 2 — Transisi Biplot Tahunan

**App.jsx mode:** `comp_1_trans_biplot` | **Format:** `{pair}` = `{y1}x{y2}`

| File | Lokasi | Keterangan |
|------|--------|------------|
| `output_table_biplot_transition_sum_{pair}.tex` | ROOT | Matriks transisi klaster Biplot PCA (jumlah) |
| `output_table_biplot_transition_name_{pair}.tex` | ROOT | Nama daerah per sel transisi klaster Biplot |
| `compare_map_trans_biplot_{pair}.png` | SCENARIO | Peta klaster Biplot tahun t₁ dan t₂ |
| `compare_scatter_trans_biplot_{pair}.png` | SCENARIO | Scatter klaster Biplot tahun t₁ dan t₂ |
| `compare_pie_trans_biplot_{pair}.png` | SCENARIO | Pie proporsi klaster Biplot tahun t₁ dan t₂ |

---

### Perbandingan 3 — Klaster Biplot vs STATIS Tahunan

**App.jsx mode:** `comp_3_biplot_vs_statis` | **Format:** `{yr}`

| File | Lokasi | Keterangan |
|------|--------|------------|
| `output_table_biplot_vs_statis_compare_sum_{yr}.tex` | SCENARIO | Cross-tab Biplot vs STATIS (matriks utama) |
| `output_table_biplot_vs_statis_compare_name_{yr}.tex` | SCENARIO | Nama daerah (matriks utama) |
| 
| `compare_map_biplot_vs_statis_{yr}.png` | SCENARIO | Peta klaster Biplot (kiri) vs STATIS (kanan) |
| `compare_scatter_biplot_vs_statis_{yr}.png` | SCENARIO | Scatter Biplot vs STATIS |
| `compare_pie_biplot_vs_statis_{yr}.png` | SCENARIO | Pie proporsi Biplot vs STATIS |

---

### Perbandingan 4 — Transisi Kategori IPM UNDP

**App.jsx mode:** `comp_4_trans_ipm` | **Format:** `{pair}` | **Tanpa scatter**

| File | Lokasi | Keterangan |
|------|--------|------------|
| `output_table_ipm_sum_{pair}.tex` | SCENARIO | Matriks transisi kategori IPM UNDP (jumlah) |
| `output_table_ipm_name_{pair}.tex` | SCENARIO | Nama daerah per sel transisi IPM |
| `compare_map_ipm_{pair}.png` | SCENARIO | Peta kategori IPM tahun t₁ dan t₂ |
| `compare_pie_ipm_{pair}.png` | SCENARIO | Pie proporsi kategori IPM tahun t₁ dan t₂ |

---

### Perbandingan 5 — Klaster Biplot vs Kategori IPM

**App.jsx mode:** `comp_5_biplot_vs_ipm` | **Format:** `{yr}` | **Tanpa scatter**

| File | Lokasi | Keterangan |
|------|--------|------------|
| `output_table_cross_matrix_sum_{yr}.tex` | SCENARIO | Cross-tab klaster Biplot vs kategori IPM (jumlah) |
| `output_table_cross_matrix_name_{yr}.tex` | SCENARIO | Nama daerah per sel |
| `compare_map_biplot_vs_ipm_{yr}.png` | SCENARIO | Peta klaster Biplot (kiri) vs kategori IPM (kanan) |
| `compare_pie_biplot_vs_ipm_{yr}.png` | SCENARIO | Pie proporsi Biplot vs kategori IPM |

---

### Perbandingan 6 — Klaster STATIS Tahunan vs Kategori IPM

**App.jsx mode:** `comp_6_statis_vs_ipm` | **Format:** `{yr}` | **Tanpa scatter**

| File | Lokasi | Keterangan |
|------|--------|------------|
| `output_table_statis_vs_ipm_sum_{yr}.tex` | SCENARIO | Cross-tab klaster STATIS vs kategori IPM (jumlah) |
| `output_table_statis_vs_ipm_name_{yr}.tex` | SCENARIO | Nama daerah per sel |
| `compare_map_statis_vs_ipm_{yr}.png` | SCENARIO | Peta klaster STATIS (kiri) vs peta IPM (kanan) |
| `compare_pie_statis_vs_ipm_{yr}.png` | SCENARIO | Pie proporsi STATIS vs kategori IPM |

---

### Perbandingan 7 — Klaster Kompromi STATIS vs Klaster Biplot

**App.jsx mode:** `comp_7_compromise_vs_biplot` | **Format:** `{yr}`

| File | Lokasi | Keterangan |
|------|--------|------------|
| `output_table_biplot_vs_compromise_sum_{yr}.tex` | SCENARIO | Cross-tab Biplot PCA vs Klaster Kompromi STATIS |
| `output_table_biplot_vs_compromise_name_{yr}.tex` | SCENARIO | Nama daerah per sel |
| `compare_map_compromise_vs_biplot_{yr}.png` | SCENARIO | Peta Kompromi STATIS (kiri) vs klaster Biplot (kanan) |
| `compare_scatter_compromise_vs_biplot_{yr}.png` | SCENARIO | Scatter Kompromi vs Biplot |
| `compare_pie_compromise_vs_biplot_{yr}.png` | SCENARIO | Pie proporsi Kompromi vs Biplot |

---

### Perbandingan 8 — Klaster Kompromi STATIS vs STATIS Tahunan

**App.jsx mode:** `comp_8_compromise_vs_statis` | **Format:** `{yr}`

| File | Lokasi | Keterangan |
|------|--------|------------|
| `output_table_compromise_vs_statis_sum_{yr}.tex` | SCENARIO | Cross-tab Kompromi STATIS vs STATIS tahunan |
| `output_table_compromise_vs_statis_name_{yr}.tex` | SCENARIO | Nama daerah per sel |
| `compare_map_compromise_vs_statis_{yr}.png` | SCENARIO | Peta Kompromi STATIS (kiri) vs STATIS tahunan (kanan) |
| `compare_scatter_compromise_vs_statis_{yr}.png` | SCENARIO | Scatter Kompromi vs STATIS tahunan |
| `compare_pie_compromise_vs_statis_{yr}.png` | SCENARIO | Pie proporsi Kompromi vs STATIS tahunan |

---

### Perbandingan 9 — Klaster Kompromi STATIS vs Kategori IPM

**App.jsx mode:** `comp_9_compromise_vs_ipm` | **Format:** `{yr}` | **Tanpa scatter**

| File | Lokasi | Keterangan |
|------|--------|------------|
| `output_table_compromise_vs_ipm_sum_{yr}.tex` | SCENARIO | Cross-tab Klaster Kompromi STATIS vs kategori IPM |
| `output_table_compromise_vs_ipm_name_{yr}.tex` | SCENARIO | Nama daerah per sel |
| `compare_map_compromise_vs_ipm_{yr}.png` | SCENARIO | Peta Kompromi STATIS (kiri) vs peta IPM (kanan) |
| `compare_pie_compromise_vs_ipm_{yr}.png` | SCENARIO | Pie proporsi Kompromi vs kategori IPM |

---

## 4. Status Sinkronisasi App.jsx

### Comparison Panel (9 mode)

| # | Nama | App.jsx mode | Format | .tex ✓ | .png ✓ | Status |
|---|------|-------------|--------|---------|---------|--------|
| 1 | Transisi Biplot | `comp_1_trans_biplot` | pair | ✓ ROOT | ✓ SCENARIO | OK |
| 2 | Transisi STATIS | `comp_2_trans_statis` | pair | ✓ SCENARIO | ✓ SCENARIO | OK |
| 3 | Biplot vs STATIS | `comp_3_biplot_vs_statis` | year | ✓ SCENARIO | ✓ SCENARIO | OK |
| 4 | Transisi IPM | `comp_4_trans_ipm` | pair | ✓ SCENARIO | ✓ SCENARIO | OK |
| 5 | Biplot vs IPM | `comp_5_biplot_vs_ipm` | year | ✓ SCENARIO | ✓ SCENARIO | OK |
| 6 | STATIS vs IPM | `comp_6_statis_vs_ipm` | year | ✓ SCENARIO | ✓ SCENARIO | OK |
| 7 | Kompromi vs Biplot | `comp_7_compromise_vs_biplot` | year | ✓ SCENARIO | ✓ SCENARIO | OK |
| 8 | Kompromi vs STATIS | `comp_8_compromise_vs_statis` | year | ✓ SCENARIO | ✓ SCENARIO | OK |
| 9 | Kompromi vs IPM | `comp_9_compromise_vs_ipm` | year | ✓ SCENARIO | ✓ SCENARIO | OK |

### Perubahan dan Perbaikan yang Sudah Dilakukan

| Item | Perubahan | Status |
|------|-----------|--------|
| `output_table_cluster_members.tex` | Diganti ke `output_table_compromise_cluster_sum_name.tex` dengan format 3-kolom baru | ✓ Selesai |
| `cluster_map_statis_*.png` | Selalu di scenario1/scenario2 (TIDAK di root) | ✓ Selesai |
| `corr_heatmap_*.png` | Judul baru: `Heatmap Korelasi Pearson Indikator Tahun {yr}` | ✓ Selesai |
| `corr_heatmap_*.png` | Grup manifest: `Korelasi & Diagnostik` | ✓ Selesai |
| `loading_plot.png` | **DIHAPUS** — tidak ada di export_all.py; dihapus dari `coreFilesList` App.jsx | ✓ Selesai |
| `boxplot_*_2020.png` (year-suffixed) | **TIDAK ADA** — export_all.py hanya membuat satu file per indikator (tanpa suffix tahun) | ✓ Dikonfirmasi |
| `public/output_real/` | Sebelumnya kosong; sekarang terisi 632 file via `prepare_landing_assets.py` | ✓ Selesai |
| App.jsx `coreFilesList` | Ditambah `compromise_scatter.png`, `compromise_pie.png`, `permutation_histogram.png`; hapus `loading_plot.png` | ✓ Selesai |
| `prepare_landing_assets.py get_group()` | Tambah grup untuk `corr_heatmap`, `ipm_map`, `ipm_pie`, `cluster_pie`; hapus `loading_plot.png` | ✓ Selesai |

---

## 5. Catatan Perbedaan app.py vs export_all.py vs App.jsx

| Aspek | `app.py` (Dash) | `export_all.py` (batch) | `App.jsx` (landing) |
|-------|-----------------|------------------------|---------------------|
| Mode | Interaktif browser | Headless/batch | Statik (React) |
| Output | `../output_app/` | `output_real/`, `output_real/scenario{1,2}/` | `public/output_real/` (via prepare) |
| Skenario | Dropdown per skenario | Loop otomatis s1 & s2 | Dropdown `output_real` vs `output_sample` |
| Biplot kompromi | Plotly interaktif | Matplotlib hi-res + Plotly | Gallery dari manifest |
| Comparison view | — | Side-by-side per skenario | `ComparisonPanel` side-by-side |
| Download .tex | Tombol per-tabel di browser | Otomatis semua tabel | Preview in-page (modal) |
| `corr_heatmap` | Baru (ditambahkan) | Tersedia semua tahun | Gallery grup "Korelasi & Diagnostik" |
