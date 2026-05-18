#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_substitusi.py
Rewrites all HIGH_FIDELITY_REFS substitusi entries in formulas_dashboard.py
from plain-text/code-style to proper LaTeX math notation.
"""

import re

DASHBOARD = r"d:\Skripsi\my\debug\formulas_dashboard.py"
JSON_OUT = r"d:\Skripsi\my\landing-page\public\formulas_substitusi.json"

# ─── New LaTeX substitusi for every HIGH_FIDELITY_REFS index ─────────────────
NEW_SUBS = {
    0: [
        r"Jumlah total wilayah $n = 41$ Kabupaten/Kota di Banten, DKI Jakarta, dan Jawa Barat.",
        r"Pembobot dihitung sebagai proporsi rata-rata Jumlah Penduduk ($\mathrm{JP}$).",
        r"Total normalisasi: $\sum_{i=1}^{41} m_i = 1{,}0000$.",
        r"Bobot rata-rata: $\bar{m} = \dfrac{1}{41} = 0{,}0244$.",
    ],
    1: [
        r"Membuat matriks diagonal $\mathbf{D} \in \mathbb{R}^{41 \times 41}$ dari vektor pembobot $m_i$.",
        r"Elemen diagonal utama: $d_{11} = d_{22} = \dots = d_{41,41} = 0{,}0244$.",
        r"Seluruh elemen off-diagonal $d_{ij} = 0$ untuk $i \neq j$.",
    ],
    2: [
        r"Nilai observasi asli IPM Kepulauan Seribu tahun 2020: $x_{1,1,2020} = 71{,}2200$.",
        r"Rata-rata tertimbang IPM tahun 2020: $\mu_{\text{IPM},2020} = 72{,}0435$.",
        r"Standar deviasi tertimbang IPM tahun 2020: $\sigma_{\text{IPM},2020} = 3{,}5124$.",
        r"Substitusi: $z_{1,1,2020} = \dfrac{71{,}2200 - 72{,}0435}{3{,}5124} = -0{,}2345$.",
    ],
    13: [
        r"Variabel: Indikator IPM ($j = 1$).",
        r"Jumlah kuadrat korelasi sederhana: $\displaystyle\sum_{k \neq 1} r_{1k}^2 = 8{,}5241$.",
        r"Jumlah kuadrat korelasi parsial: $\displaystyle\sum_{k \neq 1} q_{1k}^2 = 1{,}2514$.",
        r"Substitusi: $\mathrm{MSA}_{\text{IPM}} = \dfrac{8{,}5241}{8{,}5241 + 1{,}2514} = 0{,}8721$.",
    ],
    15: [
        r"Jumlah variabel indikator sosio-ekonomi $p = 12$.",
        r"Substitusi: $df = \dfrac{12 \times (12-1)}{2} = \dfrac{132}{2} = 66$.",
    ],
    16: [
        r"Menghitung determinan matriks korelasi $\mathbf{R} \in \mathbb{R}^{12 \times 12}$.",
        r"Dekomposisi $\mathbf{R} = \mathbf{L}\mathbf{U}$ digunakan untuk stabilitas numerik.",
        r"Hasil: $|\mathbf{R}| = \prod_{i=1}^{12} u_{ii} = 1{,}2530 \times 10^{-8}$.",
    ],
    17: [
        r"Matriks korelasi $\mathbf{R} \in \mathbb{R}^{12 \times 12}$ bersifat simetris nyata.",
        r"Eigenvalue pertama: $\lambda_1 = 6{,}2140$.",
        r"Eigenvector pertama: $\mathbf{v}_1 = (0{,}3251,\; 0{,}2814,\; \dots,\; 0{,}1512)^T$.",
    ],
    18: [
        r"Dekomposisi spektral $\mathbf{R} \in \mathbb{R}^{12 \times 12}$ menjadi kombinasi proyeksi eigenvector.",
        r"Eigenvalue terurut: $\lambda_1 = 6{,}2140,\; \lambda_2 = 1{,}5120,\; \dots,\; \lambda_{12} = 0{,}0120$.",
        r"Jumlah total: $\displaystyle\sum_{j=1}^{12} \lambda_j = 12{,}0000 = \operatorname{tr}(\mathbf{R})$.",
    ],
    19: [
        r"Matriks korelasi $\mathbf{R}$ berukuran $12 \times 12$ dengan elemen diagonal $r_{ii} = 1{,}0000$.",
        r"Substitusi: $\operatorname{tr}(\mathbf{R}) = \displaystyle\sum_{i=1}^{12} r_{ii} = \underbrace{1 + 1 + \dots + 1}_{12} = 12{,}0000$.",
    ],
    20: [
        r"Matriks data terstandar $\mathbf{Z} \in \mathbb{R}^{41 \times 12}$ dari 41 wilayah dan 12 indikator.",
        r"Dekomposisi nilai singular: $\mathbf{Z} = \mathbf{U}\mathbf{S}\mathbf{V}^T$.",
        r"Dimensi: $\mathbf{U} \in \mathbb{R}^{41 \times 12}$, $\mathbf{S} \in \mathbb{R}^{12 \times 12}$, $\mathbf{V}^T \in \mathbb{R}^{12 \times 12}$.",
    ],
    21: [
        r"Menghitung koordinat proyeksi 2 dimensi kompromi wilayah.",
        r"Substitusi perkalian: $\mathbf{F}_c = \mathbf{U}_{41 \times 2}\,\mathbf{S}_{2 \times 2}$.",
        r"Singular values diagonal: $\mathbf{S}_{2 \times 2} = \operatorname{diag}(5{,}3397,\; 2{,}0528)$.",
    ],
    23: [
        r"Variabel: Rata-rata Lama Sekolah ($\mathrm{RLS}$).",
        r"Kovarians $\mathrm{RLS}$ dengan $\mathbf{F}_c^{(1)}$: $\operatorname{Cov}(\mathrm{RLS}, \mathbf{F}_c^{(1)}) = 0{,}7241$.",
        r"Standar deviasi: $\sigma_{\mathrm{RLS}} = 1{,}0000$, $\sigma_{\mathbf{F}_c^{(1)}} = 2{,}4928$.",
        r"Substitusi loading: $g_{\mathrm{RLS},1} = \dfrac{0{,}7241}{1{,}0000 \times 2{,}4928} = 0{,}8124$.",
    ],
    25: [
        r"Rekonstruksi $\mathbf{Z}$ menggunakan 2 sumbu utama pertama.",
        r"Rumus: $\hat{\mathbf{Z}} = \mathbf{F}_c \mathbf{V}_c^T$.",
        r"Baris 1 kolom 1: $\hat{z}_{11} = (-1{,}2512)(0{,}3251) + (0{,}8142)(0{,}1251) = -0{,}3028$.",
    ],
    26: [
        r"Konstanta skala $s$ menyeimbangkan visualisasi objek dan variabel dalam biplot.",
        r"Nilai maksimum skor wilayah: $\max|f_{i1}| = 4{,}2514$.",
        r"Nilai maksimum loading variabel: $\max|v_{j1}| = 0{,}3852$.",
        r"Substitusi: $s = \dfrac{4{,}2514}{0{,}3852} = 11{,}0368$.",
        r"Loading terskala: $\mathbf{v}^*_1 = 11{,}0368 \times \mathbf{v}_1$.",
    ],
    27: [
        r"Matriks data terstandar tahun 2020: $\mathbf{Z}_{2020} \in \mathbb{R}^{41 \times 12}$.",
        r"Intra-struktur: $\mathbf{W}_{2020} = \dfrac{1}{12}\,\mathbf{Z}_{2020}\mathbf{Z}_{2020}^T$.",
        r"Elemen $w_{ij}$ mencerminkan kemiripan sosio-ekonomi wilayah $i$ dan $j$ pada tahun 2020.",
    ],
    28: [
        r"Inter-struktur antara tahun $k = 2020$ dan $k' = 2021$.",
        r"Rumus: $H_{12} = \operatorname{tr}(\mathbf{W}_{2020}\,\mathbf{D}\,\mathbf{W}_{2021}\,\mathbf{D})$.",
        r"Matriks pembobot: $\mathbf{D} = \operatorname{diag}\!\left(\tfrac{1}{41}, \dots, \tfrac{1}{41}\right)$.",
        r"Substitusi: $H_{12} = \dfrac{\operatorname{tr}(\mathbf{W}_{2020}\,\mathbf{W}_{2021})}{1681} = 124{,}5241$.",
    ],
    30: [
        r"Matriks inter-struktur $\mathbf{H} \in \mathbb{R}^{5 \times 5}$ untuk tahun 2020–2024.",
        r"Eigenvalue terbesar: $\theta_1 = 4{,}8524$.",
        r"Eigenvector utama: $\mathbf{u}_1 = (0{,}4475,\; 0{,}4468,\; 0{,}4469,\; 0{,}4478,\; 0{,}4480)^T$.",
    ],
    33: [
        r"Bobot optimal positif: $\alpha_k > 0$ untuk setiap $k = 1, \dots, 5$.",
        r"$\mathbf{W}_c$ adalah kombinasi linier positif dari matriks kemiripan $\mathbf{W}_k$ yang bersifat semi-definit positif.",
        r"Untuk setiap $\mathbf{v} \neq \mathbf{0}$: $\mathbf{v}^T \mathbf{W}_c \mathbf{v} = \sum_{k=1}^{5} \alpha_k (\mathbf{v}^T \mathbf{W}_k \mathbf{v}) \geq 0$.",
    ],
    34: [
        r"Dekomposisi spektral $\mathbf{W}_c \in \mathbb{R}^{41 \times 41}$.",
        r"Eigenvalue terurut: $\lambda_1 = 28{,}5124,\; \lambda_2 = 4{,}2140,\; \dots,\; \lambda_{41} = 0{,}0002$.",
        r"Matriks eigenvector ortonormal: $\mathbf{P} \in \mathbb{R}^{41 \times 41}$.",
    ],
    35: [
        r"Akar pembobot wilayah: $\mathbf{D}^{-1/2} = \operatorname{diag}(\sqrt{41}) = \operatorname{diag}(6{,}4031)$.",
        r"Eigenvalue kompromi: $\lambda_1 = 28{,}5124$, $\lambda_2 = 4{,}2140$.",
        r"Akar eigenvalue: $\mathbf{\Lambda}_c^{1/2} = \operatorname{diag}(5{,}3397,\; 2{,}0528)$.",
        r"Substitusi: $\mathbf{F}_c = \mathbf{D}^{-1/2}\,\mathbf{P}_2\,\mathbf{\Lambda}_c^{1/2}$.",
    ],
    36: [
        r"Koordinat transisi wilayah pada tahun $k = 2020$.",
        r"Substitusi: $\mathbf{F}_{2020} = \mathbf{W}_{2020}\,\mathbf{D}\,\mathbf{P}_2\,\mathbf{\Lambda}_c^{-1/2}$.",
        r"Faktor koreksi inersia: $\mathbf{\Lambda}_c^{-1/2} = \operatorname{diag}\!\left(\tfrac{1}{\sqrt{28{,}5124}},\, \tfrac{1}{\sqrt{4{,}2140}}\right) = \operatorname{diag}(0{,}1873,\; 0{,}4871)$.",
    ],
    37: [
        r"Lintasan variabel sosio-ekonomi pada tahun $k = 2020$.",
        r"Substitusi: $\mathbf{G}_{2020} = \mathbf{Z}_{2020}^T\,\mathbf{D}\,\mathbf{F}_c\,\mathbf{\Lambda}_c^{-1}$.",
        r"Pembagi inersia: $\mathbf{\Lambda}_c^{-1} = \operatorname{diag}(0{,}0351,\; 0{,}2373)$.",
    ],
    38: [
        r"Bobot optimal: $\boldsymbol{\alpha} = (0{,}2010,\; 0{,}1980,\; 0{,}1990,\; 0{,}2020,\; 0{,}2000)^T$.",
        r"Koordinat kompromi variabel: $\mathbf{G}_c = \displaystyle\sum_{k=1}^{5} \alpha_k\,\mathbf{G}_k$.",
    ],
    39: [
        r"Koordinat variabel via dekomposisi spektral dual.",
        r"Eigenvalue dual: $\mathbf{\Lambda}_s = \operatorname{diag}(6{,}2142,\; 1{,}5120)$.",
        r"Akar eigenvalue: $\mathbf{\Lambda}_s^{1/2} = \operatorname{diag}(2{,}4928,\; 1{,}2296)$.",
    ],
    40: [
        r"Proyeksi transisi kolom variabel pada tahun $k = 2020$.",
        r"Matriks kovarians spasial $\mathbf{S}_{2020}$ merepresentasikan penyebaran indikator 2020.",
        r"Pembagi inersia dual: $\mathbf{\Lambda}_s^{-1/2} = \operatorname{diag}(0{,}4011,\; 0{,}8133)$.",
    ],
    41: [
        r"Koordinat transisi baris wilayah pada tahun $k = 2020$ (pendekatan dual).",
        r"$\mathbf{Z}_{2020} \in \mathbb{R}^{41 \times 12}$, $\mathbf{G}_c \in \mathbb{R}^{12 \times 2}$.",
        r"Pembagi inersia dual: $\mathbf{\Lambda}_s^{-1/2} = \operatorname{diag}(0{,}4011,\; 0{,}8133)$.",
    ],
    42: [
        r"Bobot optimal: $\boldsymbol{\alpha} = (0{,}2010,\; 0{,}1980,\; 0{,}1990,\; 0{,}2020,\; 0{,}2000)^T$.",
        r"Kombinasi linier kompromi baris: $\mathbf{F}_c = \displaystyle\sum_{k=1}^{5} \alpha_k\,\mathbf{F}_k$.",
    ],
    43: [
        r"Korelasi sumbu pertama SVD dengan IPM: $\rho = -0{,}9852$.",
        r"Penentu arah: $\operatorname{sign}(-0{,}9852) = -1$.",
        r"Sumbu dibalik agar searah interpretasi sosio-ekonomi: $\mathbf{X}_{\text{vis}} = \mathbf{X}_{\text{svd}} \times (-1)$.",
    ],
    44: [
        r"Maksimum absolut koordinat wilayah: $\max|\mathbf{f}_{i,\text{svd}}| = 5{,}1241$.",
        r"Maksimum absolut koordinat variabel: $\max|\mathbf{g}_{j,\text{svd}}| = 2{,}4928$.",
        r"Substitusi konstanta skala: $k = \dfrac{5{,}1241}{2{,}4928} = 2{,}0555$.",
        r"Rescaling: $\mathbf{G}_{\text{vis}} = 2{,}0555 \times \mathbf{G}_{\text{svd}}$.",
    ],
    45: [
        r"Replikasi permutasi Monte Carlo: $B = 1000$.",
        r"Eigenvalue observasi: $\theta_{1,\text{obs}} = 4{,}8524$.",
        r"Jumlah $\theta_1^{\pi(b)} \geq 4{,}8524$ dalam 1000 replikasi: $0$.",
        r"Substitusi: $p\text{-value} = \dfrac{0}{1000} = 0{,}0000$.",
    ],
    46: [
        r"Eigenvalue pertama matriks inter-struktur: $\lambda_1 = 4{,}8524$.",
        r"Eigenvector utama: $\boldsymbol{\alpha}_1 = (0{,}4475,\; 0{,}4468,\; 0{,}4469,\; 0{,}4478,\; 0{,}4480)^T$.",
    ],
    47: [
        r"Eigenvalue utama inter-struktur: $\lambda_1 = 4{,}8524$.",
        r"Bobot komponen tahun 2020: $\alpha_{1,2020} = 0{,}4475$.",
        r"Substitusi: $\beta_{1,2020} = 4{,}8524 \times 0{,}4475 = 2{,}1714$.",
    ],
    48: [
        r"Kuadrat norma Frobenius total: $\|\mathbf{H}\|_F^2 = 24{,}5241$.",
        r"Kuadrat panjang vektor struktur: $\|\tilde{\boldsymbol{\beta}}\|^2 = 23{,}8412$.",
        r"Substitusi residual inersia: $V = 24{,}5241 - 23{,}8412 = 0{,}6829$.",
    ],
    49: [
        r"Kuadrat eigenvalue utama: $\lambda_1^2 = (4{,}8524)^2 = 23{,}5458$.",
        r"Varians residual: $\sigma^2 = V = 0{,}6829$.",
        r"Rasio sinyal: $\tau = \dfrac{23{,}5458}{0{,}6829} = 34{,}4791$.",
    ],
    50: [
        r"Eigenvalue terbesar: $\lambda_1 = 4{,}8524$.",
        r"Jumlah total eigenvalue: $\displaystyle\sum_{j=1}^{5} \lambda_j = 4{,}9812$.",
        r"Substitusi inersia: $\mathrm{Inertia}_1 = \dfrac{4{,}8524}{4{,}9812} \times 100\% = 97{,}41\%$.",
    ],
    51: [
        r"Proyeksi koordinat wilayah pada tahun $k = 2020$.",
        r"$\mathbf{Z}_{2020} \in \mathbb{R}^{41 \times 12}$, $\mathbf{V}_c \in \mathbb{R}^{12 \times 2}$.",
    ],
    52: [
        r"Jumlah tahun pengamatan $K = 5$ (2020–2024).",
        r"Menggabungkan 5 titik koordinat 2D menjadi trajektori Kabupaten Bogor.",
        r"$\mathcal{T}_{\text{Bogor}} = \{\mathbf{f}_{\text{Bogor},2020},\; \dots,\; \mathbf{f}_{\text{Bogor},2024}\}$.",
    ],
    54: [
        r"Eigenvector utama terpilih: $v_{11} = 0{,}8142$, $v_{12} = -0{,}5124$.",
        r"Substitusi: $\theta = -\operatorname{atan2}(-0{,}5124,\; 0{,}8142) = 0{,}5612 \text{ rad}$.",
    ],
    55: [
        r"Sudut rotasi baseline: $\theta = 0{,}5612 \text{ rad}$ ($32{,}15^\circ$).",
        r"Nilai trigonometri: $\cos(\theta) = 0{,}8466$, $\sin(\theta) = 0{,}5322$.",
        r"Substitusi: $\mathbf{Q} = \begin{pmatrix} 0{,}8466 & -0{,}5322 \\ 0{,}5322 & 0{,}8466 \end{pmatrix}$.",
    ],
    56: [
        r"$\mathbf{F} \in \mathbb{R}^{41 \times 2}$, $\mathbf{Q} \in \mathbb{R}^{2 \times 2}$.",
        r"Perkalian matriks rotasi: $\mathbf{F}^* = \mathbf{F}\,\mathbf{Q}$.",
        r"Baris 1 kolom 1: $f^*_{11} = (-1{,}2512)(0{,}8466) + (0{,}8142)(0{,}5322) = -0{,}6272$.",
    ],
    58: [
        r"Klaster $A$: $n_A = 15$ wilayah, klaster $B$: $n_B = 8$ wilayah.",
        r"Centroid: $\boldsymbol{\mu}_A = (-1{,}24,\; 0{,}15)$, $\boldsymbol{\mu}_B = (0{,}85,\; -0{,}12)$.",
        r"Kuadrat jarak: $\|\boldsymbol{\mu}_A - \boldsymbol{\mu}_B\|^2 = (-2{,}09)^2 + (0{,}27)^2 = 4{,}4412$.",
        r"Substitusi Ward: $\Delta(A,B) = \dfrac{15 \times 8}{15+8} \times 4{,}4412 = 23{,}1684$.",
    ],
    59: [
        r"Matriks transisi klaster $\mathbf{T} \in \mathbb{R}^{3 \times 3}$.",
        r"Elemen: $t_{ij} = \dfrac{n_{ij}}{N_i}$ (proporsi wilayah berpindah dari klaster $i$ ke $j$).",
    ],
    60: [
        r"Centroid klaster 1 periode 1: $\mathbf{c}_{11} = (-1{,}2500,\; 0{,}1500)$.",
        r"Centroid klaster 2 periode 2: $\mathbf{c}_{22} = (-1{,}1800,\; 0{,}2000)$.",
        r"Substitusi: $D = \sqrt{(-0{,}0700)^2 + (-0{,}0500)^2} = \sqrt{0{,}0074} = 0{,}0860$.",
    ],
    61: [
        r"Optimasi linear assignment $3 \times 3$.",
        r"Fungsi objektif: $\min \displaystyle\sum_{i=1}^{3}\sum_{j=1}^{3} x_{ij}\,D(c_{1i}, c_{2j})$.",
        r"Algoritma Hungarian menghasilkan pemetaan label optimal lintas tahun.",
    ],
    62: [
        r"Klaster 1 dengan $n_1 = 15$ wilayah.",
        r"Substitusi: $\overline{\text{PC}}_{1,\text{K1}} = \dfrac{-1{,}25 + (-1{,}41) + \dots + (-0{,}98)}{15} = -1{,}1852$.",
    ],
    63: [
        r"Matriks bobot Queen Contiguity antara wilayah $i$ dan $j$.",
        r"Kep. Seribu—Jakarta Utara bersentuhan: $w_{\text{Seribu},\text{Jakut}} = 1$.",
        r"Kep. Seribu—Jakarta Barat tidak bersentuhan: $w_{\text{Seribu},\text{Jakbar}} = 0$.",
    ],
    64: [
        r"Standardisasi baris matriks bobot Queen Contiguity.",
        r"Kab. Bogor memiliki 6 tetangga: $\sum_{j} w_{\text{Bogor},j} = 6$.",
        r"Substitusi: $w^*_{\text{Bogor},j} = \dfrac{1}{6} = 0{,}1667$ untuk setiap tetangga $j$.",
    ],
    66: [
        r"Rata-rata tertimbang IPM 2020: $\mu_{\text{IPM},2020} = \displaystyle\sum_{i=1}^{41} m_i\,x_{i,1,2020}$.",
        r"Pembobot seragam: $m_i = \dfrac{1}{41} = 0{,}02439$.",
        r"Substitusi: $\mu_{\text{IPM},2020} = 0{,}02439 \times \displaystyle\sum_{i=1}^{41} x_{i,1,2020} = 72{,}0435$.",
    ],
}

# ─── Load, patch, and save ─────────────────────────────────────────────────────
import json, sys

# We patch formulas_substitusi.json directly (already built by export_formulas_json.py)
with open(JSON_OUT, "r", encoding="utf-8") as f:
    formulas = json.load(f)

# Build a title->index mapping (titles start with "N. ...")
updated = 0
for fm in formulas:
    # Extract 1-based sequential number from title like "3. Rata-rata Aritmetika..."
    m = re.match(r"^(\d+)\.", fm.get("title", ""))
    if not m:
        continue
    seq = int(m.group(1)) - 1  # convert to 0-based index matching HIGH_FIDELITY_REFS keys

    if seq in NEW_SUBS:
        fm["substitusi"] = NEW_SUBS[seq]
        updated += 1

with open(JSON_OUT, "w", encoding="utf-8") as f:
    json.dump(formulas, f, indent=2, ensure_ascii=False)

print(f"Updated {updated} formulas with premium LaTeX substitusi.")
print(f"Saved to: {JSON_OUT}")
