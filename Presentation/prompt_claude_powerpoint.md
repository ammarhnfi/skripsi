# Prompt untuk Claude AI di Ekstensi PowerPoint

Salin prompt di bawah ini ke kolom chat Claude di dalam PowerPoint.
Gunakan satu blok prompt sekaligus, atau per bagian sesuai kebutuhan.

---

## PROMPT UTAMA (Full Generation)

```
Create a professional academic thesis defense presentation in PowerPoint with exactly 15 slides.

THESIS CONTEXT:
- Title: "STATIS and Dynamic Biplot Approaches for Socio-Economic Spatio-Temporal Analysis (Case Study: Banten, DKI Jakarta, and West Java Provinces 2020–2024)"
- Author: Ammar Hanafi (NPM: 2206051582)
- Program: S1 Statistics, FMIPA, Universitas Indonesia
- Supervisor: Dr. Dra. Yekti Widyaningsih, M.Si.
- Examiner I: Sarini Abdullah, S.Si., M.Stats., Ph.D.
- Examiner II: Gianinna Ardaneswari, S.Si., M.Si.
- Defense: June 2026, Depok

DESIGN REQUIREMENTS:
- Color palette: UI (Universitas Indonesia) colors — primary navy blue (#003366), accent gold (#C8A951), white background
- Font: Calibri or similar sans-serif, minimum 24pt body text
- Style: Clean, academic, minimal text per slide — let visuals do the work
- Each content slide should have: clear heading, maximum 5 bullet points, space for a chart or table placeholder

SLIDE STRUCTURE (15 slides):

SLIDE 1 — Cover
Title in two lines, Author name and NPM, Universitas Indonesia logo placeholder, Program Studi Sarjana Statistika FMIPA UI, June 2026

SLIDE 2 — Presentation Outline
7 numbered sections: (1) Background & Motivation, (2) Problem Statement & Objectives, (3) Data & Indicators, (4) STATIS Method, (5) Results: Inter-Structure, (6) Results: Trajectories & Clusters, (7) Conclusion & Policy Implications

SLIDE 3 — Background: Why This Research Matters
Heading: "Persistent Regional Disparity in Western Java"
Bullets:
• These 3 provinces contribute >40% of national GDP — yet intra-provincial disparity is extreme
• COVID-19 (2020) created asymmetric structural shocks across 41 regencies/cities
• Recovery 2021–2024: metropolitan areas bounced back; southern regencies remained stagnant
• Conventional multivariate methods (annual PCA) cannot capture cross-time structural dynamics
• KEY QUESTION: Is this disparity temporary (pandemic-induced) or structural (persistent)?
Add placeholder for a map showing the three provinces.

SLIDE 4 — Problem Statement & Objectives
Two research questions:
1. How stable is the relative hierarchy of 41 regencies/cities during 2020–2024 despite the pandemic shock?
2. What are the spatio-temporal trajectory patterns when analyzed simultaneously across indicators and years?
Three objectives in bullet form: evaluate longitudinal stability via RV coefficients, map trajectories via Dynamic Biplot, cluster regions into policy-interpretable groups.

SLIDE 5 — Data: 41 Regions × 11 Indicators × 5 Years
Three-column layout:
Column 1 - Regions (N=41): 8 regencies/cities in Banten, 6 in DKI Jakarta, 27 in West Java. Source: BPS 2020–2024.
Column 2 - 11 Indicators table with two columns (Dimension | Indicator):
Economy: GRDP (ADHK)
Poverty: PPM, GK, PKKP
Employment: TPT, TPAK
Education: RLS (Mean Years Schooling)
Health: AHH Male, AHH Female
Equity: IPG, Gini Ratio
Column 3 - Pre-processing: Demographic weighting (population share) applied before Z-score standardization. KMO and Bartlett tests passed for all years (p < 0.001).

SLIDE 6 — Method: STATIS Framework (5 Stages)
Create a horizontal flowchart with 5 boxes and arrows:
Box 1: "Stage 1: Weighted Z-score Standardization (demographic weights)"
Box 2: "Stage 2: Inter-structure (RV Coefficients — 5×5 matrix)"
Box 3: "Stage 3: Compromise Wc (Optimal Spectral Weighting, Lavit 1994)"
Box 4: "Stage 4: Monte Carlo Permutation Test (B=1,000, p<0.001)"
Box 5: "Stage 5: Dynamic Biplot + K-Means Clustering (k=3)"
Below the flowchart add a note: "One shared reference space — all years projected into it — trajectories become visible."

SLIDE 7 — Results: Inter-Structure Stability (RV Coefficients)
Heading: "Relative Regional Hierarchy Remained Stable Throughout the Pandemic"
Insert a 5×5 table with years 2020–2024 as both row and column headers. Apply green color gradient — darker green for higher values.

Values:
       2020    2021    2022    2023    2024
2020  1.0000  0.9555  0.9429  0.9533  0.9545
2021  0.9555  1.0000  0.9534  0.9487  0.9396
2022  0.9429  0.9534  1.0000  0.9608  0.9497
2023  0.9533  0.9487  0.9608  1.0000  0.9827
2024  0.9545  0.9396  0.9497  0.9827  1.0000

Key finding callout box: "All RV > 0.90 (p < 0.001) — the pandemic shifted absolute positions, but not who was on top and who was at the bottom."

SLIDE 8 — Results: Compromise Structure — Two Main Dimensions
Heading: "Two Structural Axes Explain the Core of Regional Disparity"
Left: large placeholder for the Compromise Biplot image (label it: INSERT FIGURE — Compromise Biplot from thesis)
Right: annotation list:
• Dimension 1 (60.85%): "Socio-Economic Capacity" — strong positive loadings: GRDP, HDI, Mean Years Schooling
• Dimension 2 (11.03%): "Social & Health Resilience" — dominated by Life Expectancy (AHH), IPG
• Extreme positions:
  - Top right: Kota Jakarta Pusat (3.87, −1.19) — most advanced
  - Bottom left: Kab. Pangandaran (−3.17, −4.83) — most lagging
  - Left cluster: Lebak, Garut, Cianjur — structural red zone

SLIDE 9 — Results: Three Trajectory Patterns (Dynamic Biplot)
Heading: "The Pandemic Revealed Three Types of Regional Resilience"
Left: large placeholder for the Trajectory Plot image (label: INSERT FIGURE — Spatio-temporal Trajectories from thesis)
Right: table with three rows:
Pattern | Example Regions | Characteristic
V-Shape Recovery | Jakarta Pusat, Bandung | Contraction 2020–2021, strong rebound by 2024
Stagnant | Lebak (TPAK −2.12; −2.21), Garut, Pangandaran | Almost no movement over 5 years
Progressive Growth | Depok, Tangerang cities | Continuous upward trend, no notable contraction
Bottom callout: "Trajectory ≠ Level. Depok is not the most advanced, but it has the most consistent growth among buffer zones."

SLIDE 10 — Results: K-Means Clusters & UNDP HDI Validation
Heading: "Three Clusters Aligned with UNDP HDI Categories — Not a Statistical Artifact"
Left: placeholder for choropleth map (3 colors: Maju/Berkembang/Tertinggal)
Right: cluster summary table:
Cluster | Label | Key Characteristics
1 | Maju (Advanced) | High Dim1, all DKI Jakarta cities, UNDP HDI "Very High"
2 | Berkembang (Developing) | Mid Dim1, mixed West Java and northern Banten
3 | Tertinggal (Lagging) | Low Dim1 & Dim2, southern regencies: Lebak, Garut, Pangandaran, Cianjur
Bottom finding: "Cluster 1 = 100% overlap with UNDP 'Very High' HDI → disparity is structurally driven, not pandemic-induced."

SLIDE 11 — [OPTIONAL] Innovation: Interactive Python Dashboard
Heading: "Novel Contribution: Accessible Analytical Tool for Policymakers"
Four feature cards in 2×2 grid:
Card 1: "Diagnostic Tests" — KMO & Bartlett automated per year
Card 2: "Interactive Biplot" — Zoom, filter, hover tooltips on Plotly
Card 3: "Spatial Cluster Map" — Choropleth with trajectory overlay
Card 4: "Auto Export" — One-click LaTeX & Excel output
Bottom note: "Built with Python (Plotly + Dash) — the first STATIS dashboard for Indonesian regional development analysis."

SLIDE 12 — Conclusions
Heading: "Three Core Findings"
Three large numbered points with icons:
1. STRUCTURAL STABILITY PROVEN — All RV coefficients > 0.90, p < 0.001. The pandemic did not change the fundamental hierarchy of regional development.
2. TWO DEVELOPMENT AXES IDENTIFIED — Dimension 1 "Socio-Economic Capacity" (60.85%) and Dimension 2 "Social & Health Resilience" (11.03%) together explain the core of regional disparity.
3. THREE TRAJECTORY PATTERNS & THREE CLUSTERS — V-shape metropolitan, stagnant southern, progressive buffer zones. Clusters align with UNDP HDI — disparity is structural, not temporary.

SLIDE 13 — Limitations & Future Research
Two columns:
Left - Limitations:
• Coverage: Only 3 Western Java provinces (41 regencies) — generalization requires verification
• Time horizon: 5 years (2020–2024) — pre-pandemic baseline not captured
• Indicators: 11 BPS indicators — environmental and infrastructure dimensions not included

Right - Future Research Directions:
• Extend to 10 years (2015–2024) to capture pre-pandemic trends
• Include environmental and infrastructure indicators
• Replicate STATIS across all 34 Indonesian provinces for a national map
• Develop public real-time dashboard connected to BPS API

SLIDE 14 — Research Novelty & Contribution
Two large side-by-side boxes:
Box 1 - Methodological Contribution:
"First application of the STATIS method for post-pandemic regional development dynamics analysis in Western Java context"
Box 2 - Product Contribution:
"Interactive Python web dashboard integrating: automated KMO/Bartlett diagnostics, interactive biplot and trajectory visualization, automatic export to LaTeX and Excel — as an analytical instrument for researchers and policymakers"

SLIDE 15 — Closing & Acknowledgments
Thank you section:
• Dr. Dra. Yekti Widyaningsih, M.Si. — Thesis Supervisor
• Sarini Abdullah, S.Si., M.Stats., Ph.D. — Examiner I
• Gianinna Ardaneswari, S.Si., M.Si. — Examiner II
Closing quote box: "Behind the fluctuating economic numbers of the pandemic lies a far deeper and more persistent structural pattern. Understanding that pattern is a prerequisite for truly targeted policy."
Large "Q&A" text at the bottom.
```

---

## PROMPT TAMBAHAN: Perbaikan Desain (Jalankan Setelah Generate)

```
Please refine the presentation design with these specific adjustments:
1. Make the slide headers consistently bold, navy blue (#003366), font size 28–32pt
2. On slides with tables, apply alternating row shading using very light blue (#E8F0F8) for even rows
3. Add a thin gold (#C8A951) horizontal line below each slide header as a visual divider
4. On the cover slide, add a decorative element (a light geometric shape or gradient) in the background using UI colors
5. Ensure all body text is minimum 22pt for readability in a presentation room
6. Add slide numbers in the bottom-right corner of every slide (except the cover)
7. Keep consistent left margin of 0.8 inch across all slides
```

---

## PROMPT TAMBAHAN: Buat Slide Khusus Flowchart STATIS

```
Replace slide 6 with a visually enhanced flowchart slide for the STATIS method.
Use SmartArt or shape-based design with these 5 stages connected by right-pointing arrows:

Stage 1 (dark blue box): 
Title: "Weighted Standardization"
Sub: "Z-score with demographic weights (population share)"
Icon idea: scale or balance symbol

Stage 2 (slightly lighter blue):
Title: "Inter-Structure (RV)"  
Sub: "5×5 RV coefficient matrix — measures similarity between yearly configurations"
Icon idea: grid or matrix symbol

Stage 3 (medium blue):
Title: "Compromise Wc"
Sub: "Optimal spectral weighting (Lavit, 1994) — one stable reference space"
Icon idea: converging arrows

Stage 4 (accent gold):
Title: "Permutation Test"
Sub: "Monte Carlo B=1,000 — validates structure is not random"
Icon idea: dice or distribution curve

Stage 5 (dark navy):
Title: "Dynamic Biplot + K-Means"
Sub: "Trajectory visualization + clustering k=3"
Icon idea: scatter plot with arrows

Below all boxes, add a note in italics: "All years projected into one shared compromise space — making cross-time comparison valid and structural patterns visible."
```

---

## TIPS PENGGUNAAN

1. **Mulai dengan prompt utama** — copy seluruh blok "PROMPT UTAMA" ke Claude di PowerPoint
2. **Tunggu sampai selesai generate**, lalu jalankan "PROMPT TAMBAHAN: Perbaikan Desain"
3. **Insert gambar manual** setelah generate: cari placeholder bertuliskan "INSERT FIGURE" dan replace dengan gambar dari skripsi kamu (screenshot dari induk.pdf halaman xiii dan xiv)
4. **Sesuaikan tabel RV** di slide 7 — angkanya sudah benar sesuai data di skripsi
5. **Slide 11 (Dashboard)** bisa dihapus jika waktu terbatas atau kamu tidak mau demo live
