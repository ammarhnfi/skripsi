"""
generate_manifest.py
====================
Menghasilkan output_real_manifest.json dan output_sample_manifest.json
untuk landing page, berdasarkan file yang ada di direktori output.

Struktur tiap item dalam manifest:
  {
    "src":      "/output_real/scenario1/biplot_tahun_2020.png",
    "caption":  "Biplot Tahunan Tahun 2020 (Skenario 1)",
    "name":     "biplot_tahun_2020.png",
    "type":     "image" | "tex",
    "group":    "Biplot & Skor",
    "scenario": "Scenario 1" | "Scenario 2" | "Shared"
  }

Jalankan:
    python debug/generate_manifest.py
"""

import os, json, sys

# ---------------------------------------------------------------------------
# KONFIGURASI DIREKTORI
# ---------------------------------------------------------------------------
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
LANDING_PUBLIC = os.path.join(PROJECT_ROOT, "landing-page", "public")

MODES = {
    "real":   os.path.join(PROJECT_ROOT, "output_real"),
    "sample": os.path.join(PROJECT_ROOT, "output_sample"),
}

# Fallback: gunakan output_manual jika output_real belum ada
if not os.path.isdir(MODES["real"]) and os.path.isdir(os.path.join(PROJECT_ROOT, "output_manual")):
    MODES["real"] = os.path.join(PROJECT_ROOT, "output_manual")
    print("  [INFO] output_real tidak ditemukan, fallback ke output_manual")

# ---------------------------------------------------------------------------
# ATURAN KLASIFIKASI
# Tiap rule: (glob_pattern_substring, group, scenario_override)
# scenario_override = None → otomatis dari path (root/s1/s2)
# ---------------------------------------------------------------------------
RULES = [
    # ---------- SHARED (ROOT) ----------
    # Statistika Deskriptif
    ("output_table_deskriptif_",     "Statistika Deskriptif",    "Shared"),
    ("output_table_descriptive_",    "Statistika Deskriptif",    "Shared"),
    ("boxplot_",                     "Statistika Deskriptif",    "Shared"),

    # Interstruktur & RV (selalu shared)
    ("output_table_rv_",             "Interstruktur & RV",       "Shared"),
    ("output_table_hw",              "Interstruktur & RV",       "Shared"),
    ("output_table_hs",              "Interstruktur & RV",       "Shared"),
    ("output_table_alpha_w",         "Interstruktur & RV",       "Shared"),
    ("output_table_alpha_s",         "Interstruktur & RV",       "Shared"),
    ("rv_heatmap",                   "Interstruktur & RV",       "Shared"),
    ("scree_plot",                   "Interstruktur & RV",       "Shared"),

    # KMO & Diagnostik
    ("output_table_kmo",             "Diagnostik KMO & Bartlett","Shared"),
    ("output_macros",                "Makro LaTeX",               "Shared"),
    ("output_perm_statis",           "Permutation Test",          "Shared"),
    ("output_core_statis",           "Makro LaTeX",               "Shared"),
    ("permutation_histogram",        "Permutation Test",          "Shared"),

    # Intra & Jarak (dihitung sekali di s1 tapi berlaku shared)
    ("output_table_skor_intra_",     "Tabel Intra",              "Shared"),
    ("output_table_loading_intra_",  "Tabel Intra",              "Shared"),
    ("output_table_matriks_intra_",  "Tabel Intra",              "Shared"),
    ("output_table_jarak_skor_",     "Perbandingan PCA vs STATIS","Shared"),
    ("output_table_jarak_loading_",  "Perbandingan PCA vs STATIS","Shared"),

    # Vektor Struktur
    ("output_table_struktur",        "Vektor Struktur",          "Shared"),
    ("output_table_beta",            "Vektor Struktur",          "Shared"),
    ("beta_trajectory",              "Vektor Struktur",          "Shared"),

    # ---------- SKENARIO SPESIFIK ----------
    # Alpha & Eigen
    ("output_table_alpha.tex",       "Alpha & Eigen",            None),
    ("output_table_eigen",           "Alpha & Eigen",            None),

    # Matriks Kompromi
    ("matrix_G_c",                   "Matriks Kompromi",         None),
    ("matrix_V_c",                   "Matriks Kompromi",         None),
    ("matrix_F_c",                   "Matriks Kompromi",         None),
    ("output_table_loadings",        "Biplot & Skor",            None),
    ("output_table_scores",          "Biplot & Skor",            None),

    # Biplot & Trajektori
    ("compromise_map",               "Biplot & Skor",            None),
    ("scatter_statis",               "Biplot & Skor",            None),
    ("compromise_biplot_matplotlib", "Biplot & Skor",            None),
    ("loading_plot",                 "Biplot & Skor",            None),
    ("variable_contribution",        "Biplot & Skor",            None),
    ("variable_cos2",                "Biplot & Skor",            None),
    ("biplot_tahun_",                "Biplot Tahunan",           None),
    ("statis_trajectories",          "Trajektori STATIS",        None),

    # Clustering
    ("cluster_scatter_statis_",      "Clustering K-Means",       None),
    ("cluster_scatter_biplot_",      "Clustering K-Means",       None),
    ("cluster_scatter_statis.png",   "Clustering K-Means",       None),
    ("cluster_map_statis_",          "Peta Cluster",             None),
    ("cluster_map_biplot_",          "Peta Cluster",             None),
    ("cluster_map_statis.png",       "Peta Cluster",             None),
    ("elbow_plot_",                  "Evaluasi Cluster",         None),
    ("dendrogram_",                  "Evaluasi Cluster",         None),
    ("output_table_cluster_members", "Clustering K-Means",       None),

    # Matriks Transisi
    ("output_table_transition_matrix_sum_",  "Matriks Transisi",   None),
    ("output_table_transition_matrix_name_", "Matriks Transisi",   None),
    ("compare_map_trans_",                   "Matriks Transisi",   None),
    ("compare_scatter_trans_",               "Matriks Transisi",   None),

    # IPM
    ("output_table_ipm_matrix_sum_",   "Transisi IPM",           None),
    ("output_table_ipm_matrix_name_",  "Transisi IPM",           None),
    ("output_table_cross_matrix_sum_",  "Cross-tab Cluster vs IPM", None),
    ("output_table_cross_matrix_name_", "Cross-tab Cluster vs IPM", None),
    ("output_table_statis_vs_ipm_",     "Cross-tab Cluster vs IPM", None),

    # Perbandingan Biplot vs STATIS
    ("output_table_biplot_vs_statis_compare_", "Perbandingan Biplot vs STATIS", None),
    ("output_table_biplot_vs_statis_sum_",     "Perbandingan Biplot vs STATIS", None),
    ("output_table_biplot_vs_statis_name_",    "Perbandingan Biplot vs STATIS", None),
    ("compare_map_biplot_vs_statis_",          "Perbandingan Biplot vs STATIS", None),
    ("compare_scatter_biplot_vs_statis_",      "Perbandingan Biplot vs STATIS", None),

    # Moran's I
    ("output_moran",                 "Moran's I Spasial",        None),
]

# ---------------------------------------------------------------------------
CAPTION_MAP = {
    # Shared
    "output_table_deskriptif_":       "Statistika Deskriptif (Tanpa Bobot) Tahun {yr}",
    "output_table_descriptive_":      "Statistika Deskriptif (Dengan Bobot) Tahun {yr}",
    "output_table_rv_w":              "Matriks RV Antar-Tahun (Host = Wilayah)",
    "output_table_rv_s":              "Matriks RV Antar-Tahun (Host = Indikator)",
    "output_table_hw":                "Matriks Interstruktur H_W",
    "output_table_hs":                "Matriks Interstruktur H_S",
    "output_table_alpha_w":           "Bobot Alpha (Wilayah)",
    "output_table_alpha_s":           "Bobot Alpha (Indikator)",
    "rv_heatmap":                     "Heatmap Koefisien RV Antar-Tahun",
    "scree_plot":                     "Scree Plot Nilai Eigen",
    "output_table_kmo":               "Uji KMO dan Bartlett per Tahun",
    "permutation_histogram":          "Distribusi Null Permutasi (Uji Signifikansi)",
    "output_perm_statis":             "Makro LaTeX: Permutation Test",
    "output_core_statis":             "Makro LaTeX: Core STATIS",
    "output_macros":                  "Makro LaTeX: Ringkasan Hasil",
    "boxplot_":                       "Boxplot Distribusi {var} (Perbandingan Tahunan)",
    # Intra
    "output_table_skor_intra_":       "Skor Intra F_k Tahun {yr}",
    "output_table_loading_intra_":    "Loading Intra G_k Tahun {yr}",
    "output_table_matriks_intra_":    "Matriks Korelasi Terbobot S_k Tahun {yr}",
    "output_table_jarak_skor_":       "Jarak PCA vs STATIS (Skor) Tahun {yr}",
    "output_table_jarak_loading_":    "Jarak PCA vs STATIS (Loading) Tahun {yr}",
    # Vektor Struktur
    "output_table_struktur":          "Tabel Diagnostik Vektor Struktur",
    "output_table_beta":              "Komponen Vektor Struktur Beta per Provinsi",
    "beta_trajectory":                "Lintasan Temporal Vektor Struktur Beta",
    # Scenario specific
    "output_table_alpha.tex":         "Bobot Alpha per Tahun",
    "output_table_eigen":             "Dekomposisi Nilai Eigen Kompromi",
    "matrix_G_c":                     "Matriks Loadings Kompromi (G_c)",
    "matrix_V_c":                     "Matriks Eigenvector Kompromi (V_c)",
    "matrix_F_c":                     "Matriks Skor Kompromi (F_c)",
    "output_table_loadings":          "Tabel Loadings Kompromi",
    "output_table_scores":            "Tabel Skor Kompromi",
    "compromise_map":                 "Peta Sebaran Kompromi (Skor)",
    "scatter_statis":                 "Biplot Kompromi STATIS",
    "compromise_biplot_matplotlib":   "Biplot Kompromi (Matplotlib)",
    "loading_plot":                   "Loading Plot Compromise",
    "variable_contribution":          "Kontribusi Variabel terhadap Dimensi 1",
    "variable_cos2":                  "Kualitas Representasi Variabel (Cos²)",
    "biplot_tahun_":                  "Biplot Tahunan Tahun {yr}",
    "statis_trajectories.png":        "Trajektori STATIS (Semua Objek)",
    "statis_trajectories_highlight":  "Trajektori STATIS (Highlight)",
    "cluster_scatter_statis_":        "Scatter Plot Cluster K-Means STATIS Tahun {yr}",
    "cluster_scatter_biplot_":        "Scatter Plot Cluster K-Means Biplot Tahun {yr}",
    "cluster_scatter_statis.png":     "Scatter Plot Cluster Trajektori Keseluruhan",
    "cluster_map_statis_":            "Peta Cluster STATIS Tahun {yr}",
    "cluster_map_biplot_":            "Peta Cluster Biplot Tahun {yr}",
    "cluster_map_statis.png":         "Peta Cluster STATIS Keseluruhan",
    "elbow_plot_":                    "Kurva Elbow K-Means Tahun {yr}",
    "dendrogram_":                    "Dendrogram Hierarki Tahun {yr}",
    "dendrogram_compromise":          "Dendrogram Cluster Trajektori Keseluruhan",
    "output_table_cluster_members":   "Anggota Cluster Trajektori Keseluruhan",
    "output_table_transition_matrix_sum_":  "Matriks Transisi Cluster (Jumlah) {pair}",
    "output_table_transition_matrix_name_": "Matriks Transisi Cluster (Nama Daerah) {pair}",
    "compare_map_trans_":             "Perbandingan Peta Transisi {pair}",
    "compare_scatter_trans_":         "Perbandingan Scatter Transisi {pair}",
    "output_table_ipm_matrix_sum_":   "Matriks Transisi Kategori IPM (Jumlah) {pair}",
    "output_table_ipm_matrix_name_":  "Matriks Transisi Kategori IPM (Nama) {pair}",
    "output_table_cross_matrix_sum_":  "Cross-tab Cluster vs IPM (Jumlah) Tahun {yr}",
    "output_table_cross_matrix_name_": "Cross-tab Cluster vs IPM (Nama) Tahun {yr}",
    "output_table_statis_vs_ipm_avg_sum": "Perbandingan Cluster STATIS vs IPM Rata-rata",
    "output_table_statis_vs_ipm_avg_name":"Nama Daerah: Cluster STATIS vs IPM Rata-rata",
    "output_table_biplot_vs_statis_compare_sum_":  "Cross-tab Biplot vs STATIS (Jumlah) Tahun {yr}",
    "output_table_biplot_vs_statis_compare_name_": "Cross-tab Biplot vs STATIS (Nama) Tahun {yr}",
    "output_table_biplot_vs_statis_sum_":  "Perbandingan Cluster Biplot vs STATIS Tahun {yr}",
    "output_table_biplot_vs_statis_name_": "Nama Daerah: Biplot vs STATIS Tahun {yr}",
    "compare_map_biplot_vs_statis_":  "Perbandingan Peta Biplot vs STATIS Tahun {yr}",
    "compare_scatter_biplot_vs_statis_": "Perbandingan Scatter Biplot vs STATIS Tahun {yr}",
    "output_moran":                   "Hasil Uji Moran's I Autokorelasi Spasial",
}

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}


def classify(name: str, rel_dir: str) -> tuple[str, str]:
    """Return (group, scenario)."""
    name_lower = name.lower()

    # Tentukan scenario dari path
    if "scenario1" in rel_dir:
        auto_scenario = "Scenario 1"
    elif "scenario2" in rel_dir:
        auto_scenario = "Scenario 2"
    else:
        auto_scenario = "Shared"

    # Match rule (case-insensitive)
    for pattern, group, scen_override in RULES:
        if pattern.lower() in name_lower:
            scenario = scen_override if scen_override else auto_scenario
            return group, scenario

    return "Lain-lain", auto_scenario


def make_caption(name: str) -> str:
    """Buat caption human-readable dari nama file."""
    base = os.path.splitext(name)[0]  # strip extension

    for prefix, caption_tmpl in CAPTION_MAP.items():
        pbase = os.path.splitext(prefix)[0]
        if pbase in base:
            # Coba ekstrak tahun atau pair dari nama
            suffix = base.replace(pbase.rstrip("_"), "").strip("_")
            caption = caption_tmpl
            if "{yr}" in caption:
                caption = caption.replace("{yr}", suffix or "?")
            if "{pair}" in caption:
                caption = caption.replace("{pair}", suffix.replace("x", " → ") or "?")
            if "{var}" in caption:
                caption = caption.replace("{var}", suffix.replace("_", " ").title() or "?")
            return caption

    # Fallback: prettify filename
    pretty = base.replace("output_table_", "").replace("_", " ").replace(".tex", "").title()
    return pretty


def scan_dir(root_output_dir: str, url_prefix: str) -> list[dict]:
    """Scan direktori output dan return list manifest items."""
    items = []
    seen_names = {}  # name -> item, untuk dedup

    for dirpath, _, filenames in os.walk(root_output_dir):
        for fname in sorted(filenames):
            ext = os.path.splitext(fname)[1].lower()
            if ext not in IMAGE_EXTS and ext != ".tex":
                continue

            rel_dir = os.path.relpath(dirpath, root_output_dir).replace("\\", "/")
            if rel_dir == ".":
                rel_dir = ""

            ftype = "image" if ext in IMAGE_EXTS else "tex"
            group, scenario = classify(fname, rel_dir)

            # URL path
            src_path = f"{url_prefix}/{rel_dir}/{fname}" if rel_dir else f"{url_prefix}/{fname}"
            src_path = src_path.replace("//", "/")

            caption = make_caption(fname)

            # Deduplikasi: jika file identik nama sudah ada di Shared, skip
            key = fname
            if key in seen_names:
                existing = seen_names[key]
                # Prioritaskan Shared atas scenario-spesifik
                if existing["scenario"] == "Shared":
                    continue
                # Jika yang baru Shared, ganti yang lama
                if scenario == "Shared":
                    items.remove(existing)
            seen_names[key] = {
                "src": src_path, "caption": caption, "name": fname,
                "type": ftype, "group": group, "scenario": scenario
            }
            items.append(seen_names[key])

    return items


def build_and_write(mode: str, output_dir: str):
    if not os.path.isdir(output_dir):
        print(f"  [SKIP] Direktori tidak ditemukan: {output_dir}")
        return

    url_prefix = f"/output_{mode}"
    items = scan_dir(output_dir, url_prefix)

    out_path = os.path.join(LANDING_PUBLIC, f"output_{mode}_manifest.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    groups   = sorted(set(i["group"]    for i in items))
    scenarios = sorted(set(i["scenario"] for i in items))
    print(f"  [{mode.upper()}] {len(items)} items -> {out_path}")
    print(f"    Groups:    {groups}")
    print(f"    Scenarios: {scenarios}")


if __name__ == "__main__":
    print("=" * 60)
    print("  GENERATE MANIFEST")
    print("=" * 60)
    for mode, path in MODES.items():
        build_and_write(mode, path)
    print("\nSelesai.")
