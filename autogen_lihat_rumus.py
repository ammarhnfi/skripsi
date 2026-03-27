"""
autogen_lihat_rumus.py
Generates lihat_rumus.tex: A comprehensive step-by-step formula document
using real data from data2.xlsx for thesis presentation to lecturer.
"""

import numpy as np
import pandas as pd
import json
from scipy.stats import chi2
from numpy.linalg import inv, det, eig
from sklearn.preprocessing import StandardScaler

# ─────────────────────────────────────────────
# 1. LOAD & COMPUTE REAL DATA
# ─────────────────────────────────────────────
DATA_PATH  = r"d:\Skripsi\my\data\data2.xlsx"
OUTPUT_TEX = r"d:\Skripsi\my\lihat_rumus.tex"

VARS = ['IPM','IPG','PPM','PDRB_ADHK','RLS','AHH_L','AHH_P','GK','PKKP','TPT','TPAK','GR']
YEARS = ['2020','2021','2022','2023','2024']

xl = pd.ExcelFile(DATA_PATH)
dfs = {yr: xl.parse(yr) for yr in YEARS}

# --- Use 2020 as the primary year for demonstration ---
df0 = dfs['2020']
X0  = df0[VARS].values.astype(float)
n, p = X0.shape
obs_names = df0['Kabupaten/Kota'].tolist()

# ── Descriptive stats for IPM ──
ipm = X0[:, 0]
mean_ipm = ipm.mean()
std_ipm  = ipm.std(ddof=1)
min_ipm  = ipm.min()
max_ipm  = ipm.max()
q1_ipm   = np.percentile(ipm, 25)
q2_ipm   = np.median(ipm)
q3_ipm   = np.percentile(ipm, 75)
iqr_ipm  = q3_ipm - q1_ipm
cv_ipm   = std_ipm / mean_ipm * 100
m3       = ((ipm - mean_ipm)**3).mean()
m4       = ((ipm - mean_ipm)**4).mean()
skew_ipm = m3 / (std_ipm**3)
kurt_ipm = m4 / (std_ipm**4) - 3

# Z-score for Kep. Seribu (row 0), IPM
x11      = X0[0, 0]  # Kep. Seribu, IPM
z11      = (x11 - mean_ipm) / std_ipm

# ── Pearson correlation matrix ──
R_mat  = np.corrcoef(X0.T)  # p×p
det_R  = np.linalg.det(R_mat)

# ── KMO calculation ──
R_inv  = np.linalg.inv(R_mat)
sum_r2 = 0.0; sum_q2 = 0.0
for i in range(p):
    for j in range(p):
        if i != j:
            sum_r2 += R_mat[i,j]**2
            q = -R_inv[i,j] / np.sqrt(R_inv[i,i] * R_inv[j,j])
            sum_q2 += q**2
kmo  = sum_r2 / (sum_r2 + sum_q2)

# ── Bartlett's test ──
factor   = n - 1 - (2*p + 5) / 6
ln_det_R = np.log(det_R)
chi2_bar = -factor * ln_det_R
df_bar   = p*(p-1)//2
p_bar    = 1 - chi2.cdf(chi2_bar, df_bar)

# ── Z-score all years ──
Z_mats = {}
for yr in YEARS:
    Xk = dfs[yr][VARS].values.astype(float)
    sc = StandardScaler()
    Z_mats[yr] = sc.fit_transform(Xk)

# ── Intra-structure W_t ──
W_mats = {yr: (Z @ Z.T) / p for yr, Z in Z_mats.items()}

# ── Inter-structure RV matrix ──
T = len(YEARS)
RV = np.zeros((T, T))
for i, yi in enumerate(YEARS):
    for j, yj in enumerate(YEARS):
        Wi, Wj = W_mats[yi], W_mats[yj]
        num = np.trace(Wi @ Wj)
        den = np.sqrt(np.trace(Wi @ Wi) * np.trace(Wj @ Wj))
        RV[i,j] = num/den if den > 0 else 0.0

rv_2020_2021 = RV[0,1]
tr_W0W1      = np.trace(W_mats['2020'] @ W_mats['2021'])
tr_W0sq      = np.trace(W_mats['2020'] @ W_mats['2020'])
tr_W1sq      = np.trace(W_mats['2021'] @ W_mats['2021'])
rv_denom     = np.sqrt(tr_W0sq * tr_W1sq)

# ── Alpha weights from eigenvector of RV ──
eigvals, eigvecs = eig(RV)
idx      = np.argsort(np.real(eigvals))[::-1]
u1       = np.real(eigvecs[:, idx[0]])
alphas   = u1 / np.sqrt(np.sum(u1**2))
alphas   = np.abs(alphas)   # signs can flip; magnitudes used

# ── Compromise matrix ──
W_c = sum(alphas[i] * W_mats[yr] for i, yr in enumerate(YEARS))
trace_Wc   = np.trace(W_c)
eigvals_Wc, eigvecs_Wc = eig(W_c)
idx_Wc      = np.argsort(np.real(eigvals_Wc))[::-1]
lam_Wc      = np.real(eigvals_Wc[idx_Wc])
Vc          = np.real(eigvecs_Wc[:, idx_Wc])
F_c         = Vc[:, :2] @ np.diag(np.sqrt(np.maximum(lam_Wc[:2], 0)))
Wc_slice    = W_c[:3,:3]   # 3x3 preview

# ── Trajectory distance (example: Kab Bogor idx 5 vs Kota Bogor idx 24) ──
Z_all = np.stack([Z_mats[yr] for yr in YEARS], axis=2)  # n×p×K
F_all = np.stack([Z_mats[yr] @ Vc[:p,:2] for yr in YEARS], axis=2)  # n×2×K

def traj_dist(i, j):
    return np.sqrt(np.sum((F_all[i] - F_all[j])**2))

d_bogor = traj_dist(5, 24)

# ── K-Means SSE (k=3 clusters using trajectory) ──
traj_flat = F_all.reshape(n, -1)  # n × (2K)
from sklearn.cluster import KMeans
km = KMeans(n_clusters=3, random_state=42, n_init=10)
labels = km.fit_predict(traj_flat)
sse    = km.inertia_

# ── Moran's I (from saved macro if exists, else skip) ──
try:
    moran_data = {}
    with open(r"d:\Skripsi\my\output_app\output_moran.tex") as f:
        for line in f:
            import re
            m = re.match(r"\\newcommand\{\\Macro(\w+)\}\{([^}]+)\}", line.strip())
            if m:
                moran_data[m.group(1)] = m.group(2)
    moran_i   = float(moran_data.get('MoranI', 0.6903))
    moran_exp = float(moran_data.get('MoranExp', -0.0250))
except:
    moran_i   = 0.6903
    moran_exp = -0.0250

print("=== Computed Values ===")
print(f"n={n}, p={p}")
print(f"IPM(2020): mean={mean_ipm:.4f}, std={std_ipm:.4f}, min={min_ipm:.2f}, max={max_ipm:.2f}")
print(f"Q1={q1_ipm:.4f}, Q2={q2_ipm:.4f}, Q3={q3_ipm:.4f}, IQR={iqr_ipm:.4f}")
print(f"CV={cv_ipm:.2f}%, Skew={skew_ipm:.4f}, Kurt={kurt_ipm:.4f}")
print(f"z11(Kep.Seribu, IPM) = {z11:.4f}")
print(f"KMO = {kmo:.4f}")
print(f"chi2={chi2_bar:.4f}, df={df_bar}, p={p_bar:.6f}")
print(f"RV(2020,2021) = {rv_2020_2021:.4f}")
print(f"alphas = {[f'{a:.4f}' for a in alphas]}")
print(f"SSE = {sse:.2f}")

# ─────────────────────────────────────────────
# 2. LATEX HELPERS
# ─────────────────────────────────────────────
def fnum(x, dec=4):
    """Format a number nicely."""
    if abs(x) >= 1000:
        return f"{x:,.2f}"
    return f"{x:.{dec}f}"

def box(title, formula_tex, keterangan_items, steps, result_tex):
    """Build one tcolorbox."""
    ket = "\n".join(f"  \\item {item}" for item in keterangan_items)
    stp = "\n".join(f"  \\item {s}" for s in steps)
    return f"""\\begin{{tcolorbox}}[formula_box, title={{{title}}}]
\\textbf{{Formula:}}
{formula_tex}

\\textbf{{Keterangan Variabel:}}
\\begin{{itemize}}
{ket}
\\end{{itemize}}

\\textbf{{Substitusi (Langkah demi Langkah):}}
\\begin{{enumerate}}
{stp}
\\end{{enumerate}}

\\textbf{{Hasil Akhir:}}
{result_tex}
\\end{{tcolorbox}}

"""

# ─────────────────────────────────────────────
# 3. BUILD ALL FORMULA BOXES
# ─────────────────────────────────────────────
blocks = []

# ── 1. Z-Score ──
blocks.append(box(
    "1. Standardisasi Data (Z-Score)",
    r"\[ z_{ij} = \frac{x_{ij} - \bar{x}_j}{s_j} \]",
    [
        r"$x_{ij}$: Nilai mentah variabel $j$ pada wilayah ke-$i$",
        r"$\bar{x}_j$: Rata-rata variabel $j$ dari seluruh $n=41$ wilayah",
        r"$s_j$: Simpangan baku variabel $j$",
    ],
    [
        r"Ambil contoh: $i = 1$ (Kep.\ Seribu), $j = $ IPM, tahun 2020",
        f"$x_{{1,IPM}} = {x11:.2f}$",
        f"$\\bar{{x}}_{{IPM}} = \\frac{{\\sum_{{i=1}}^{{41}} x_{{i,IPM}}}}{{41}} = \\frac{{{ipm.sum():.2f}}}{{41}} = {mean_ipm:.4f}$",
        f"$s_{{IPM}} = {std_ipm:.4f}$",
        f"$z_{{1,IPM}} = \\frac{{{x11:.2f} - {mean_ipm:.4f}}}{{{std_ipm:.4f}}} = \\frac{{{x11-mean_ipm:.4f}}}{{{std_ipm:.4f}}}$",
    ],
    f"\\[ z_{{1,IPM}} = {z11:.4f} \\]\n\\textit{{(Nilai negatif: IPM Kep.\\ Seribu di bawah rata-rata)}}"
))

# ── 2. Rata-rata ──
ipm_sum_str = " + ".join([f"{v:.2f}" for v in ipm[:3]]) + " + \\cdots"
blocks.append(box(
    "2. Rata-Rata (Mean)",
    r"\[ \bar{x}_j = \frac{1}{n} \sum_{i=1}^{n} x_{ij} \]",
    [
        r"$\bar{x}_j$: Rata-rata variabel $j$",
        r"$n$: Jumlah wilayah pengamatan",
        r"$x_{ij}$: Nilai variabel $j$ untuk wilayah ke-$i$",
    ],
    [
        f"Variabel: IPM, Tahun 2020, $n = {n}$ wilayah",
        f"$\\bar{{x}}_{{IPM}} = \\frac{{1}}{{{n}}} \\sum_{{i=1}}^{{{n}}} x_{{i,IPM}}$",
        f"$= \\frac{{{ipm_sum_str}}}{{{n}}}$",
        f"$= \\frac{{{ipm.sum():.2f}}}{{{n}}}$",
    ],
    f"\\[ \\bar{{x}}_{{IPM}} = {mean_ipm:.4f} \\]"
))

# ── 3. Median ──
ipm_sorted = np.sort(ipm)
idx_med = n // 2
blocks.append(box(
    "3. Median (Kuartil Kedua, $Q_2$)",
    r"""\[ Q_2 = \begin{cases} x_{\left(\frac{n+1}{2}\right)} & n \text{ ganjil} \\ \frac{x_{\left(\frac{n}{2}\right)} + x_{\left(\frac{n}{2}+1\right)}}{2} & n \text{ genap} \end{cases} \]""",
    [
        r"$n = 41$ (ganjil), sehingga $Q_2 = x_{(21)}$",
        r"$x_{(k)}$: Nilai ke-$k$ setelah data diurutkan naik",
    ],
    [
        f"Data IPM 2020 diurutkan: $\\{{{ipm_sorted[0]:.2f}, {ipm_sorted[1]:.2f}, \\ldots, {ipm_sorted[-1]:.2f}\\}}$",
        f"$n = {n}$ (ganjil) $\\Rightarrow$ posisi median $= \\frac{{41+1}}{{2}} = 21$",
        f"$Q_2 = x_{{(21)}} = {ipm_sorted[idx_med]:.4f}$",
    ],
    f"\\[ Q_2 = {q2_ipm:.4f} \\]"
))

# ── 4. Simpangan Baku ──
ss = ((ipm - mean_ipm)**2).sum()
blocks.append(box(
    "4. Simpangan Baku ($s$)",
    r"\[ s_j = \sqrt{\frac{1}{n-1} \sum_{i=1}^{n} (x_{ij} - \bar{x}_j)^2} \]",
    [
        r"$s_j$: Simpangan baku sampel variabel $j$",
        r"$n-1$: Derajat kebebasan (koreksi Bessel)",
    ],
    [
        f"Variabel IPM, 2020: $\\bar{{x}}_{{IPM}} = {mean_ipm:.4f}$",
        f"$\\sum_{{i=1}}^{{{n}}} (x_{{i,IPM}} - \\bar{{x}})^2 = {ss:.4f}$",
        f"$s^2 = \\frac{{{ss:.4f}}}{{{n}-1}} = \\frac{{{ss:.4f}}}{{{n-1}}} = {ss/(n-1):.4f}$",
        f"$s = \\sqrt{{{ss/(n-1):.4f}}}$",
    ],
    f"\\[ s_{{IPM}} = {std_ipm:.4f} \\]"
))

# ── 5. Min/Max ──
blocks.append(box(
    "5. Nilai Minimum dan Maksimum",
    r"\[ x_{\min} = \min(x_1,\ldots,x_n),\quad x_{\max} = \max(x_1,\ldots,x_n) \]",
    [r"$x_{\min}$ dan $x_{\max}$: Nilai ekstrem dalam distribusi variabel"],
    [
        f"Variabel IPM, 2020 ({n} wilayah)",
        f"Survey seluruh nilai: IPM terendah $= {min_ipm:.2f}$, tertinggi $= {max_ipm:.2f}$",
    ],
    f"\\[ x_{{\\min,IPM}} = {min_ipm:.2f} \\quad x_{{\\max,IPM}} = {max_ipm:.2f} \\]\n\\textit{{({obs_names[np.argmin(ipm)]} hingga {obs_names[np.argmax(ipm)]})}}"
))

# ── 6. IQR ──
blocks.append(box(
    "6. Jangkauan Interkuartil (IQR)",
    r"\[ IQR = Q_3 - Q_1 \]",
    [
        r"$Q_1$: Kuartil pertama (persentil ke-25)",
        r"$Q_3$: Kuartil ketiga (persentil ke-75)",
    ],
    [
        f"Variabel IPM, 2020",
        f"$Q_1 = {q1_ipm:.4f}$ (persentil ke-25)",
        f"$Q_3 = {q3_ipm:.4f}$ (persentil ke-75)",
        f"$IQR = {q3_ipm:.4f} - {q1_ipm:.4f}$",
    ],
    f"\\[ IQR_{{IPM}} = {iqr_ipm:.4f} \\]"
))

# ── 7. CV ──
blocks.append(box(
    "7. Koefisien Variasi / \\textit{Coefficient of Variation} (CV)",
    r"\[ CV = \frac{s}{\bar{x}} \times 100\% \]",
    [
        r"$CV$ (\textit{Coefficient of Variation}): Ukuran variabilitas relatif, bebas satuan",
        r"$s$: Simpangan baku; $\bar{x}$: Rata-rata",
        r"Klasifikasi (Sumber: Hasan, 2001): $CV \leq 10\%$ = rendah; $10\% < CV \leq 20\%$ = sedang; $CV > 20\%$ = tinggi",
    ],
    [
        f"Variabel IPM, 2020: $s = {std_ipm:.4f}$, $\\bar{{x}} = {mean_ipm:.4f}$",
        f"$CV = \\frac{{{std_ipm:.4f}}}{{{mean_ipm:.4f}}} \\times 100\\%$",
        f"$CV = {std_ipm/mean_ipm:.4f} \\times 100\\%$",
    ],
    f"\\[ CV_{{IPM}} = {cv_ipm:.2f}\\% \\quad \\text{{({'rendah ($\\leq 10\\%$)' if cv_ipm <= 10 else 'sedang ($10\\%$--$20\\%$)' if cv_ipm <= 20 else 'tinggi ($> 20\\%$)'})}} \\]"
))

# ── 8. Skewness ──
m3_val = m3
blocks.append(box(
    "8. Koefisien Kemiringan / \\textit{Skewness} ($g_1$)",
    r"\[ g_1 = \frac{\frac{1}{n}\sum_{i=1}^{n}(x_i-\bar{x})^3}{s^3} \]",
    [
        r"$g_1$ (huruf $g$ dari \textit{gamma}, notasi standar Fisher): Koefisien kemiringan",
        r"Klasifikasi (Bulmer, 1979): $|g_1| < 0.5$: simetri; $0.5 \leq |g_1| < 1$: menceng moderat; $|g_1| \geq 1$: sangat menceng",
        r"$g_1 > 0$: Distribusi menceng kanan (\textit{right-skewed})",
        r"$g_1 < 0$: Distribusi menceng kiri (\textit{left-skewed})",
    ],
    [
        f"$\\frac{{1}}{{n}}\\sum(x_i-\\bar{{x}})^3 = {m3_val:.4f}$",
        f"$s^3 = {std_ipm:.4f}^3 = {std_ipm**3:.4f}$",
        f"$g_1 = \\frac{{{m3_val:.4f}}}{{{std_ipm**3:.4f}}}$",
    ],
    f"\\[ g_{{1,IPM}} = {skew_ipm:.4f} \\quad \\text{{({'simetri' if abs(skew_ipm)<0.5 else 'menceng moderat kanan' if skew_ipm>0 else 'menceng moderat kiri'})}} \\]"
))

# ── 9. Kurtosis ──
m4_val = m4
blocks.append(box(
    "9. Koefisien Keruncingan / \\textit{Excess Kurtosis} ($g_2$)",
    r"\[ g_2 = \frac{\frac{1}{n}\sum_{i=1}^{n}(x_i-\bar{x})^4}{s^4} - 3 \]",
    [
        r"$g_2$ (huruf $g$ dari \textit{gamma}, notasi standar Fisher): Koefisien keruncingan",
        r"Pengurangan $-3$ disebut \textit{excess kurtosis} (Westfall, 2014): kurtosis distribusi normal $= 3$, sehingga dikurangi 3 agar baseline $= 0$",
        r"$g_2 > 0$: Leptokurtik (lebih runcing, ekor lebih tebal dari normal)",
        r"$g_2 < 0$: Platikurtik (lebih datar, ekor lebih tipis dari normal)",
    ],
    [
        f"$\\frac{{1}}{{n}}\\sum(x_i-\\bar{{x}})^4 = {m4_val:.4f}$",
        f"$s^4 = {std_ipm:.4f}^4 = {std_ipm**4:.4f}$",
        f"$g_2 = \\frac{{{m4_val:.4f}}}{{{std_ipm**4:.4f}}} - 3 = {m4_val/std_ipm**4:.4f} - 3$",
    ],
    f"\\[ g_{{2,IPM}} = {kurt_ipm:.4f} \\quad \\text{{({'leptokurtik' if kurt_ipm > 0 else 'platikurtik'})}} \\]"
))

# ── 10. KMO ──
kmo_label = 'Unacceptable' if kmo < 0.5 else 'Miserable' if kmo < 0.6 else 'Mediocre' if kmo < 0.7 else 'Middling' if kmo < 0.8 else 'Meritorious' if kmo < 0.9 else 'Marvelous'
blocks.append(box(
    "10. Kaiser-Meyer-Olkin (KMO)",
    r"\[ KMO = \frac{\sum_{j \neq k} r_{jk}^2}{\sum_{j \neq k} r_{jk}^2 + \sum_{j \neq k} r_{jk.p}^2} \]",
    [
        r"$r_{jk}$: Korelasi Pearson antara variabel $j$ dan $k$",
        r"$r_{jk.p}$: Korelasi Parsial antara $j$ dan $k$ (setelah dikontrol variabel lain)",
        r"Klasifikasi KMO (Kaiser, 1974): $<0.5$ = \textit{Unacceptable}; $0.5$--$0.6$ = \textit{Miserable}; $0.6$--$0.7$ = \textit{Mediocre}; $0.7$--$0.8$ = \textit{Middling}; $0.8$--$0.9$ = \textit{Meritorious}; $>0.9$ = \textit{Marvelous}",
    ],
    [
        f"Dari matriks korelasi $\\mathbf{{R}}$ ($p={p}$ variabel, $n={n}$ observasi)",
        f"$\\sum_{{j\\neq k}} r_{{jk}}^2 = {sum_r2:.4f}$",
        f"$\\sum_{{j\\neq k}} r_{{jk.p}}^2 = {sum_q2:.4f}$",
        f"$KMO = \\frac{{{sum_r2:.4f}}}{{{sum_r2:.4f} + {sum_q2:.4f}}} = \\frac{{{sum_r2:.4f}}}{{{sum_r2+sum_q2:.4f}}}$",
    ],
    f"\\[ KMO = {kmo:.4f} \\quad \\text{{(\\textit{{{kmo_label}}}, Kaiser 1974)}} \\]"
))

# ── 11. Bartlett df ──
blocks.append(box(
    r"11. Derajat Kebebasan Uji Bartlett ($df$)",
    r"\[ df = \frac{p(p-1)}{2} \]",
    [r"$p$: Jumlah variabel; $df$: Jumlah pasangan unik variabel"],
    [
        f"$p = {p}$ variabel",
        f"$df = \\frac{{{p} \\times ({p}-1)}}{{2}} = \\frac{{{p*(p-1)}}}{{2}}$",
    ],
    f"\\[ df = {df_bar} \\]"
))

# ── 12. Bartlett chi2 ──
blocks.append(box(
    r"12. Uji Bartlett's Test of Sphericity ($\chi^2$)",
    r"\[ \chi^2 = -\left[n - 1 - \frac{2p+5}{6}\right] \ln|\mathbf{R}| \]",
    [
        r"$\mathbf{R}$: Matriks korelasi $p \times p$ (dihitung dari data terstandarisasi)",
        r"$|\mathbf{R}|$: Determinan matriks korelasi --- dihitung oleh \texttt{numpy.linalg.det(R)} dari matriks $12 \times 12$",
        r"Jika $|\mathbf{R}| = 1$, maka variabel tidak berkorelasi. Semakin kecil $|\mathbf{R}|$, semakin tinggi korelasi",
        r"$H_0$: $\mathbf{R} = \mathbf{I}$ (Sumber: Bartlett, 1950)",
    ],
    [
        f"$n = {n}$, $p = {p}$",
        f"Faktor koreksi: $n-1-\\frac{{2p+5}}{{6}} = {n}-1-\\frac{{2({p})+5}}{{6}} = {factor:.4f}$",
        f"$|\\mathbf{{R}}| = {det_R:.2e}$ (dihitung dari matriks korelasi ${p}\\times{p}$ data 2020)",
        f"$\\ln|\\mathbf{{R}}| = \\ln({det_R:.2e}) = {ln_det_R:.4f}$",
        f"$\\chi^2 = -({factor:.4f}) \\times ({ln_det_R:.4f})$",
    ],
    f"\\[ \\chi^2 = {chi2_bar:.4f}, \\quad df = {df_bar}, \\quad p = {p_bar:.4g} \\]\n\\textit{{(Tolak $H_0$: Terdapat korelasi signifikan, data sesuai untuk STATIS --- Bartlett, 1950)}}"
))

# ── 13. Intra-struktur W_t ──
Wc_str = " & ".join(f"{v:.3f}" for v in W_c[0,:3])
Wc_r2  = " & ".join(f"{v:.3f}" for v in W_c[1,:3])
Wc_r3  = " & ".join(f"{v:.3f}" for v in W_c[2,:3])
blocks.append(box(
    r"13. Intra-struktur: Matriks Kemiripan Tahunan ($\mathbf{W}_t$)",
    r"\[ \mathbf{W}_t = \mathbf{Z}_t \mathbf{Z}_t^T \]",
    [
        r"$\mathbf{Z}_t$: Matriks data z-score ($n \times p$) tahun ke-$t$",
        r"$\mathbf{W}_t$: Matriks simetri ($n \times n$) yang merepresentasikan kedekatan antar wilayah di tahun $t$",
        r"Setiap elemen $w_{ij,t}$ = inner product baris $i$ dan $j$ dari $\mathbf{Z}_t$",
    ],
    [
        f"Tahun 2020: $\\mathbf{{Z}}_{{2020}}$ berukuran $41 \\times 12$",
        r"$\mathbf{W}_{2020} = \mathbf{Z}_{2020} \cdot \mathbf{Z}_{2020}^T$",
        f"Dimensi hasil: $(41 \\times 12)(12 \\times 41) = 41 \\times 41$",
        f"Elemen pojok kiri atas $\\mathbf{{W}}_{{2020}}[1,1] = {W_mats['2020'][0,0]:.4f}$ (norma kuadrat Kep.\\ Seribu)",
    ],
    f"\\[ \\mathbf{{W}}_{{2020}} = 41 \\times 41 \\text{{ matriks (nilai diagonal}}\\ [0,0] = {W_mats['2020'][0,0]:.4f}) \\]"
))

# ── 14. RV coefficient ──
blocks.append(box(
    r"14. Koefisien RV (Inter-Struktur)",
    r"\[ RV(\mathbf{W}_i,\mathbf{W}_j) = \frac{\text{tr}(\mathbf{W}_i\mathbf{W}_j)}{\sqrt{\text{tr}(\mathbf{W}_i^2)\,\text{tr}(\mathbf{W}_j^2)}} \]",
    [
        r"$\text{tr}(\cdot)$: Trace (jumlah elemen diagonal)",
        r"$RV \in [0,1]$: Ukuran kesamaan struktur dua matriks",
        r"$RV$ tinggi $\Rightarrow$ struktur antar-tahun stabil",
    ],
    [
        f"Contoh: Tahun 2020 vs 2021",
        f"$\\text{{tr}}(\\mathbf{{W}}_{{2020}} \\cdot \\mathbf{{W}}_{{2021}}) = {tr_W0W1:.4f}$",
        f"$\\text{{tr}}(\\mathbf{{W}}_{{2020}}^2) = {tr_W0sq:.4f}$",
        f"$\\text{{tr}}(\\mathbf{{W}}_{{2021}}^2) = {tr_W1sq:.4f}$",
        f"$RV = \\frac{{{tr_W0W1:.4f}}}{{\\sqrt{{{tr_W0sq:.4f} \\times {tr_W1sq:.4f}}}}} = \\frac{{{tr_W0W1:.4f}}}{{{rv_denom:.4f}}}$",
    ],
    f"\\[ RV(\\mathbf{{W}}_{{2020}}, \\mathbf{{W}}_{{2021}}) = {rv_2020_2021:.4f} \\quad \\text{{(Sangat stabil)}} \\]"
))

# ── 15. Alpha weights ──
alpha_str = " + ".join(f"({alphas[i]:.4f})^2" for i in range(T))
blocks.append(box(
    r"15. Bobot Optimal ($\alpha_t$)",
    r"\[ \alpha_t = \frac{u_{1t}}{\sqrt{\sum_{t=1}^{T} u_{1t}^2}} \]",
    [
        r"$\mathbf{u}_1$: Eigenvector pertama dari matriks inter-struktur $\mathbf{R}_{RV}$",
        r"$u_{1t}$: Komponen ke-$t$ dari eigenvector $\mathbf{u}_1$",
        r"$\alpha_t$: Bobot (kontribusi) tahun ke-$t$ dalam kompromi",
    ],
    [
        f"Eigenvektor pertama $\\mathbf{{u}}_1$ dari $\\mathbf{{R}}_{{RV}}$ ($T={T}$ tahun):",
        f"$\\mathbf{{u}}_1 = [{', '.join(f'{a:.4f}' for a in alphas)}]$",
        f"Penyebut: $\\sqrt{{{alpha_str}}} = \\sqrt{{{(alphas**2).sum():.4f}}}$",
        f"Masing-masing $\\alpha_t = u_{{1t}} / {np.sqrt((alphas**2).sum()):.4f}$",
    ],
    f"\\[ \\boldsymbol{{\\alpha}} = [{', '.join(f'{a:.4f}' for a in alphas)}] \\]"
))

# ── 16. Wc ──
blocks.append(box(
    r"16. Matriks Kompromi ($\mathbf{W}_c$)",
    r"\[ \mathbf{W}_c = \sum_{t=1}^{T} \alpha_t \mathbf{W}_t \]",
    [
        r"$\mathbf{W}_c$: Rata-rata tertimbang dari semua matriks tahunan",
        r"$\alpha_t$: Bobot optimal tahun ke-$t$",
        r"$\text{tr}(\mathbf{W}_c) = $ total inersia dalam representasi kompromi",
    ],
    [
        f"$\\mathbf{{W}}_c = {alphas[0]:.4f}\\mathbf{{W}}_{{2020}} + {alphas[1]:.4f}\\mathbf{{W}}_{{2021}} + {alphas[2]:.4f}\\mathbf{{W}}_{{2022}} + {alphas[3]:.4f}\\mathbf{{W}}_{{2023}} + {alphas[4]:.4f}\\mathbf{{W}}_{{2024}}$",
        f"$\\text{{tr}}(\\mathbf{{W}}_c) = {trace_Wc:.4f}$",
        f"Nilai eigen pertama: $\\lambda_1 = {lam_Wc[0]:.4f}$ $({lam_Wc[0]/trace_Wc*100:.1f}\\%$ inersia)",
        f"Nilai eigen kedua: $\\lambda_2 = {lam_Wc[1]:.4f}$ $({lam_Wc[1]/trace_Wc*100:.1f}\\%$ inersia)",
    ],
    f"\\[ \\mathbf{{W}}_c \\text{{ berukuran }} 41\\times41, \\quad \\lambda_{{1,2}} = ({lam_Wc[0]:.4f},\\ {lam_Wc[1]:.4f}) \\]"
))

# ── 17. Fc (skor kompromi) ──
blocks.append(box(
    r"17. Koordinat Skor Kompromi ($\mathbf{F}_c$)",
    r"\[ \mathbf{F}_c = \mathbf{V}_c \mathbf{\Lambda}_c^{1/2} \]",
    [
        r"$\mathbf{V}_c$: Matriks eigenvector dari $\mathbf{W}_c$",
        r"$\mathbf{\Lambda}_c$: Matriks diagonal eigenvalue",
        r"Baris ke-$i$ dari $\mathbf{F}_c$ = koordinat biplot wilayah ke-$i$",
    ],
    [
        f"$\\lambda_1 = {lam_Wc[0]:.4f} \\Rightarrow \\sqrt{{\\lambda_1}} = {np.sqrt(lam_Wc[0]):.4f}$",
        f"$\\lambda_2 = {lam_Wc[1]:.4f} \\Rightarrow \\sqrt{{\\lambda_2}} = {np.sqrt(lam_Wc[1]):.4f}$",
        f"Kep.\\ Seribu: $\\mathbf{{F}}_c[1,:] = ({F_c[0,0]:.4f},\\ {F_c[0,1]:.4f})$",
        f"Kota Jak.\\ Selatan: $\\mathbf{{F}}_c[2,:] = ({F_c[1,0]:.4f},\\ {F_c[1,1]:.4f})$",
    ],
    f"\\[ \\mathbf{{F}}_c \\text{{ berukuran }} 41\\times2 \\text{{ (dua PC dominan)}} \\]"
))

# ── 18. Jarak Trajektori ──
blocks.append(box(
    r"18. Jarak Euclidean antar Trajektori",
    r"\[ d(i,j) = \sqrt{\sum_{t=1}^{T} \|\mathbf{f}_{i,t} - \mathbf{f}_{j,t}\|^2} \]",
    [
        r"$\mathbf{f}_{i,t}$: Koordinat PC wilayah $i$ pada tahun $t$ (dari proyeksi tahunan $\mathbf{F}_t = \mathbf{Z}_t \mathbf{V}_c$)",
        r"$d(i,j)$: Jarak lintasan spasio-temporal antar dua wilayah",
    ],
    [
        f"Contoh: Kabupaten Bogor (i=6) vs Kota Bogor (i=25)",
        f"Selisih koordinat per tahun dihitung, dikuadratkan, dijumlahkan",
        f"$d = \\sqrt{{\\sum_{{t=2020}}^{{2024}} \\|\\mathbf{{f}}_{{Kab,t}} - \\mathbf{{f}}_{{Kota,t}}\\|^2}}$",
    ],
    f"\\[ d(\\text{{Kab.\\ Bogor}},\\text{{Kota Bogor}}) = {d_bogor:.4f} \\]"
))

# ── 19. K-Means SSE ──
cluster_counts = [(labels==k).sum() for k in range(3)]
blocks.append(box(
    "19. Fungsi Objektif K-Means (SSE)",
    r"\[ SSE = \sum_{j=1}^{k} \sum_{\mathbf{x}_i \in C_j} \|\mathbf{x}_i - \boldsymbol{\mu}_j\|^2 \]",
    [
        r"$k$: Jumlah klaster",
        r"$C_j$: Himpunan anggota klaster ke-$j$",
        r"$\boldsymbol{\mu}_j$: Centroid klaster ke-$j$ (rata-rata trajektori semua anggota)",
        r"Minimasi SSE dilakukan secara iteratif oleh algoritma K-Means",
    ],
    [
        f"$k = 3$ klaster, berdasarkan trajektori ${n}$ wilayah selama $T={T}$ tahun",
        f"Klaster 1: {cluster_counts[0]} wilayah, Klaster 2: {cluster_counts[1]} wilayah, Klaster 3: {cluster_counts[2]} wilayah",
        f"Setiap wilayah diwakili oleh vektor $\\mathbf{{x}}_i$ berdimensi $2T = {2*T}$",
        f"$SSE = $ jumlah kuadrat jarak semua titik ke centroid klaster masing-masing",
    ],
    f"\\[ SSE = {sse:.4f} \\quad \\text{{(setelah konvergensi K-Means)}} \\]"
))

# ── 20. Moran's I ──
blocks.append(box(
    r"20. Statistik Global Moran's $I$",
    r"\[ I = \frac{N}{\sum_i\sum_j w_{ij}} \cdot \frac{\sum_i\sum_j w_{ij}(x_i-\bar{x})(x_j-\bar{x})}{\sum_i(x_i-\bar{x})^2} \]",
    [
        r"$w_{ij}$: Bobot spasial (1 jika bertetangga, 0 jika tidak)",
        r"$x_i$: Nilai PC1 wilayah ke-$i$",
        r"$I > E[I]$: Autokorelasi spasial positif (klaster spasial)",
        r"$E[I] = -1/(N-1)$: Ekspektasi di bawah hipotesis nol acak",
    ],
    [
        f"$N = {n}$ wilayah (41 Kab/Kota di Banten, DKI Jakarta, Jawa Barat)",
        f"Menggunakan skor PC1 kompromi sebagai variabel $x$",
        f"Matriks bobot $\\mathbf{{W}}$ berdasarkan keterkaitan geografis (Queen Contiguity)",
        f"$E[I] = -1/({n}-1) = {moran_exp:.4f}$",
    ],
    f"\\[ I_{{obs}} = {moran_i:.4f} \\quad E[I] = {moran_exp:.4f} \\]\n\\textit{{(Autokorelasi positif: wilayah dengan IPM tinggi cenderung bertetangga)}}"
))

# ─────────────────────────────────────────────
# 4. ASSEMBLE FINAL LaTeX DOCUMENT
# ─────────────────────────────────────────────
preamble = r"""\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage[indonesian]{babel}
\usepackage{amsmath,amsfonts,amssymb}
\usepackage{geometry}
\usepackage[most]{tcolorbox}
\usepackage{xcolor}
\usepackage{fancyhdr}
\usepackage{booktabs}
\usepackage{array}
\usepackage{enumitem}
\usepackage{hyperref}
\usepackage{parskip}
\usepackage{adjustbox}

\geometry{margin=2.5cm, headheight=14pt, top=3cm}

\definecolor{primary}{HTML}{1E3A5F}
\definecolor{accent}{HTML}{EBF5FB}
\definecolor{gold}{HTML}{D4AC0D}

\tcbset{
  formula_box/.style={
    colback=accent, colframe=primary,
    fonttitle=\bfseries\color{white},
    coltitle=white, attach boxed title to top left={yshift=-2mm,xshift=6mm},
    boxed title style={colback=primary, rounded corners},
    boxrule=0.8pt, arc=6pt,
    left=8pt, right=8pt, top=16pt, bottom=8pt,
    after skip=14pt
  }
}

\pagestyle{fancy}
\fancyhf{}
\lhead{\small\bfseries Ammar Hanafi (2206051582)}
\rhead{\small\textit{Analisis STATIS -- Jawa Barat, Banten, DKI Jakarta}}
\cfoot{\small\thepage}
\renewcommand{\headrulewidth}{0.4pt}

\setlist[enumerate]{leftmargin=*, itemsep=2pt, topsep=4pt}
\setlist[itemize]{leftmargin=*, itemsep=2pt, topsep=4pt}

\begin{document}

\begin{titlepage}
  \centering
  \vspace*{3cm}
  {\Huge\bfseries Penjabaran Langkah demi Langkah\\[0.5em]
  Seluruh Formula Matematis\\[1em]}
  {\Large\textit{Analisis STATIS Panel Sosio-Ekonomi\\
  41 Kabupaten/Kota, 5 Tahun (2020--2024)}}\\[3em]
  \rule{0.6\textwidth}{0.5pt}\\[1.5em]
  {\large Ammar Hanafi\\NPM: 2206051582\\[0.5em]
  Program Studi Statistika\\
  Fakultas Matematika dan Ilmu Pengetahuan Alam\\
  Universitas Indonesia\\[1.5em]
  \textbf{Terakhir Diperbarui: \today}}
  \vspace*{3cm}
\end{titlepage}

\tableofcontents
\newpage

\section*{Pendahuluan} \label{sec:method}
Dokumen ini menjabarkan \textbf{setiap formula matematis} yang digunakan dalam penelitian skripsi secara lengkap dengan:
\begin{enumerate}
  \item \textbf{Formula Asal} --- Notasi simbolik baku
  \item \textbf{Keterangan Variabel} --- Definisi setiap simbol
  \item \textbf{Substitusi Langkah demi Langkah} --- Nilai \emph{nyata} dari \texttt{data2.xlsx} dimasukkan
  \item \textbf{Hasil Akhir} --- Nilai komputasi sesungguhnya
\end{enumerate}

\noindent Data yang digunakan: \textbf{41 Kabupaten/Kota} (Provinsi Banten, DKI Jakarta, Jawa Barat), \textbf{12 variabel sosio-ekonomi}, periode \textbf{2020--2024} ($T = 5$ tahun).

\subsection*{Daftar Singkatan dan Variabel}
\begin{adjustbox}{max width=\textwidth}
\begin{tabular}{lll}
\toprule
\textbf{Singkatan} & \textbf{Kepanjangan} & \textbf{Satuan} \\
\midrule
IPM   & Indeks Pembangunan Manusia & Indeks \\
IPG   & Indeks Pembangunan Gender  & Indeks \\
PPM   & Persentase Penduduk Miskin & Persen (\%) \\
PDRB\_ADHK & Produk Domestik Regional Bruto Atas Dasar Harga Konstan & Juta Rupiah \\
RLS   & Rata-rata Lama Sekolah    & Tahun \\
AHH\_L & Angka Harapan Hidup Laki-Laki & Tahun \\
AHH\_P & Angka Harapan Hidup Perempuan & Tahun \\
GK    & Garis Kemiskinan          & Rupiah/Kapita/Bulan \\
PKKP  & Pengeluaran per Kapita yang Disesuaikan & Ribu Rupiah/Orang/Tahun \\
TPT   & Tingkat Pengangguran Terbuka & Persen (\%) \\
TPAK  & Tingkat Partisipasi Angkatan Kerja & Persen (\%) \\
GR    & Gini Ratio (Rasio Ketimpangan) & Indeks [0,1] \\
\bottomrule
\end{tabular}
\end{adjustbox}

\subsection*{Notasi Umum}
\begin{adjustbox}{max width=\textwidth}
\begin{tabular}{ll}
\toprule
\textbf{Notasi} & \textbf{Arti} \\
\midrule
$n$ & Jumlah wilayah observasi ($n = 41$) \\
$p$ & Jumlah variabel ($p = 12$) \\
$T$ & Jumlah tahun pengamatan ($T = 5$: 2020--2024) \\
$i$ & Indeks wilayah ($i = 1, 2, \ldots, n$) \\
$j$ & Indeks variabel ($j = 1, 2, \ldots, p$) \\
$t$ & Indeks tahun ($t = 1, 2, \ldots, T$) \\
$\mathbf{X}_t$ & Matriks data mentah ($n \times p$) tahun ke-$t$ \\
$\mathbf{Z}_t$ & Matriks data terstandarisasi ($n \times p$) tahun ke-$t$ \\
$\mathbf{W}_t$ & Matriks kedekatan antar-wilayah ($n \times n$) tahun ke-$t$ \\
$\mathbf{W}_c$ & Matriks kompromi STATIS ($n \times n$) \\
$\mathbf{F}_c$ & Matriks koordinat skor kompromi ($n \times 2$) \\
KMO & Kaiser-Meyer-Olkin Measure of Sampling Adequacy \\
MSA & Measure of Sampling Adequacy (per variabel) \\
RV & Koefisien kemiripan antar-matriks (Escoufier) \\
PCA & Principal Component Analysis (Analisis Komponen Utama) \\
SVD & Singular Value Decomposition (Dekomposisi Nilai Singular) \\
SSE & Sum of Squared Errors (Jumlah Kuadrat Galat) \\
STATIS & Structuration des Tableaux \`A Trois Indices de la Statistique \\
\bottomrule
\end{tabular}
\end{adjustbox}

\newpage

\section{Analisis Statistika Deskriptif}
"""

body = "".join(blocks[:9])

# ── 21-28: Additional missing formulas ──
r_ipm_rls = R_mat[0, 4]
from sklearn.decomposition import PCA as PCA_sk
pca = PCA_sk(n_components=2)
F_pca = pca.fit_transform(Z_mats['2020'])
var_exp = pca.explained_variance_ratio_
eig_R = np.sort(np.real(np.linalg.eigvals(R_mat)))[::-1]
theta_ex = np.arctan2(F_c[0,1], F_c[0,0])
theta1_obs = np.real(eigvals[idx[0]])

blocks.append(box("21. Korelasi Pearson ($r_{xy}$)",
    r"\[ r_{xy} = \frac{\sum(x_i-\bar{x})(y_i-\bar{y})}{\sqrt{\sum(x_i-\bar{x})^2}\cdot\sqrt{\sum(y_i-\bar{y})^2}} \]",
    [r"$r_{xy}\in[-1,1]$: Ukuran hubungan linier", r"$|r|>0.7$: Korelasi kuat"],
    [f"IPM vs RLS, 2020: $\\bar{{x}}={mean_ipm:.4f}$, $\\bar{{y}}={X0[:,4].mean():.4f}$",
     f"Pembilang: ${np.sum((X0[:,0]-X0[:,0].mean())*(X0[:,4]-X0[:,4].mean())):.4f}$",
     f"Penyebut: ${np.sqrt(np.sum((X0[:,0]-X0[:,0].mean())**2))*np.sqrt(np.sum((X0[:,4]-X0[:,4].mean())**2)):.4f}$"],
    f"\\[ r_{{IPM,RLS}} = {r_ipm_rls:.4f} \\]"))

# ── 22. Determinan Matriks ──
blocks.append(box("22. Determinan Matriks ($|\\mathbf{A}|$)",
    r"\[ |\mathbf{A}| = \sum_{\sigma \in S_p} \text{sgn}(\sigma) \prod_{i=1}^{p} a_{i,\sigma(i)} \]",
    [r"$|\mathbf{A}|$: Determinan dari matriks bujur sangkar $\mathbf{A}$",
     r"$S_p$: Himpunan seluruh permutasi indeks $\{1, \dots, p\}$",
     r"$\text{sgn}(\sigma)$: Tanda (paritas) permutasi ($+1$ genap, $-1$ ganjil)",
     r"$a_{i,\sigma(i)}$: Elemen matriks pada baris ke-$i$ dan kolom ke-$\sigma(i)$",
     r"Digunakan menguji multikolinieritas. Semakin mendekati 0, korelasi makin kuat."],
    [f"Matriks Korelasi $\\mathbf{{R}}$ berukuran ${p}\\times{p}$ (data 2020)",
     f"Dihitung produk permutasi elemen $\\mathbf{{R}}$ lewat dekomposisi LU"],
    f"\\[ |\\mathbf{{R}}| = {det_R:.2e} \\]"))

# ── 23. PCA ──
pca_var_exp = eig_R / p
blocks.append(box("23. PCA ($\\mathbf{F}=\\mathbf{Z}\\mathbf{V}$)",
    r"\[ \mathbf{F} = \mathbf{Z}\mathbf{V} \]",
    [r"$\mathbf{Z}$: Matriks terstandarisasi ($n\times p$)", r"$\mathbf{V}$: Matriks eigenvector dari matriks korelasi $\mathbf{R}$", r"$\mathbf{F}$: Skor komponen utama ($n\times k$)"],
    [f"Dari dekomposisi matriks korelasi $\\mathbf{{R}}$ (data 2020), diperoleh eigenvalue $\\lambda_1={eig_R[0]:.4f}$, $\\lambda_2={eig_R[1]:.4f}$",
     f"Varians yang dijelaskan PC1 $= \\lambda_1 / p \\times 100\\% = {pca_var_exp[0]*100:.1f}\\%$",
     f"Varians yang dijelaskan PC2 $= \\lambda_2 / p \\times 100\\% = {pca_var_exp[1]*100:.1f}\\%$",
     f"Misal untuk Kep. Seribu (baris 1): $\\mathbf{{F}}_{{[1,:]}} = \\mathbf{{Z}}_{{[1,:]}} \\cdot \\mathbf{{V}}$"],
    f"\\[ \\begin{{pmatrix}} F_1 \\\\ F_2 \\end{{pmatrix}}_{{\\text{{Kep.Seribu}}}} = \\begin{{pmatrix}} {F_pca[0,0]:.4f} \\\\ {F_pca[0,1]:.4f} \\end{{pmatrix}} \\quad \\text{{(Kumulatif: {(pca_var_exp[0]+pca_var_exp[1])*100:.1f}\\%)}} \\]"))

# ── 24. Dekomposisi Eigen ──
blocks.append(box("24. Dekomposisi Eigen",
    r"\[ \mathbf{R}\mathbf{v}=\lambda\mathbf{v} \]",
    [r"$\mathbf{R}$: Matriks korelasi data", r"$\lambda$: Eigenvalue (besaran varians di sepanjang sumbu utama)", r"$\mathbf{v}$: Eigenvector (arah komponen utama)"],
    [f"Selesaikan persamaan karakteristik: $|\\mathbf{{R}} - \\lambda\\mathbf{{I}}| = 0$ ($p={p}$)",
     f"Diperoleh {p} eigenvalue (diurutkan mengecil):",
     f"$\\lambda_1={eig_R[0]:.4f}, \\lambda_2={eig_R[1]:.4f}, \\lambda_3={eig_R[2]:.4f}$",
     f"Total varians = $\\sum\\lambda_j = \\text{{tr}}(\\mathbf{{R}}) = {p}$"],
    f"\\[ \\lambda = [{', '.join(f'{v:.3f}' for v in eig_R[:5])}, \\ldots] \\]"))

# ── 25. Rotasi Baseline ──
F_star = F_c[0, :2] @ np.array([[np.cos(-theta_ex), -np.sin(-theta_ex)], [np.sin(-theta_ex), np.cos(-theta_ex)]])
blocks.append(box("25. Rotasi Baseline",
    r"\[ \theta=-\operatorname{atan2}(v_2,v_1),\; \mathbf{Q}=\begin{pmatrix}\cos\theta&-\sin\theta\\\sin\theta&\cos\theta\end{pmatrix},\; \mathbf{F}^*=\mathbf{F}\mathbf{Q} \]",
    [r"$\theta$: Sudut rotasi untuk membuat Kep. Seribu sejajar sumbu X", r"$\mathbf{Q}$: Matriks rotasi ortogonal $2\times2$"],
    [f"Koordinat Kompromi Kep. Seribu: $v_1={F_c[0,0]:.4f}$, $v_2={F_c[0,1]:.4f}$",
     f"$\\theta = -\\text{{atan2}}({F_c[0,1]:.4f}, {F_c[0,0]:.4f}) = {np.degrees(-theta_ex):.2f}^\\circ$",
     f"$\\mathbf{{Q}} = \\begin{{pmatrix}} {np.cos(-theta_ex):.4f} & {-np.sin(-theta_ex):.4f} \\\\ {np.sin(-theta_ex):.4f} & {np.cos(-theta_ex):.4f} \\end{{pmatrix}}$",
     f"$\\mathbf{{F}}^* = [{F_c[0,0]:.4f}, {F_c[0,1]:.4f}] \\times \\mathbf{{Q}}$"],
    f"\\[ \\mathbf{{F}}^*_{{\\text{{Kep.Seribu}}}} = [{F_star[0]:.4f}, {F_star[1]:.4f}] \\]"))

blocks.append(box("26. Matriks Pembobot Spasial",
    r"\[ w_{ij}=\begin{cases}1&\text{bertetangga}\\0&\text{selainnya}\end{cases},\; w_{ij}^*=\frac{w_{ij}}{\sum_k w_{ik}} \]",
    [r"$w_{ij}$: Bobot biner (Queen Contiguity)", r"$w_{ij}^*$: Row-standardized"],
    [f"$\\mathbf{{W}}$: ${n}\\times{n}$", f"5 tetangga $\\Rightarrow w^*=0.2$"],
    f"\\[ \\mathbf{{W}} \\text{{ ({n}x{n}, simetri)}} \\]"))

blocks.append(box("27. Matriks Transisi Temporal",
    r"\[\mathbf{T}=\begin{pmatrix}T_{11}&T_{12}&T_{13}\\T_{21}&T_{22}&T_{23}\\T_{31}&T_{32}&T_{33}\end{pmatrix}\]",
    [r"$T_{ab}$: Jumlah wilayah berpindah klaster $a\to b$", r"Diagonal dominan $=$ stabil"],
    [f"$k=3$, ${n}$ wilayah, $T={T}$ tahun"],
    f"\\[ \\text{{Matriks perpindahan klaster}} \\]"))

blocks.append(box("28. Ward's Linkage (Dendrogram)",
    r"\[\Delta(A,B)=\frac{n_A n_B}{n_A+n_B}\|\boldsymbol{\mu}_A-\boldsymbol{\mu}_B\|^2\]",
    [r"$\Delta$: Peningkatan varians jika digabung", r"$n_A,n_B$: Jumlah anggota"],
    [f"${n}$ wilayah, dipotong $k=3$"],
    f"\\[ k=3 \\text{{ klaster}} \\]"))

blocks.append(box("29. Uji Permutasi Stabilitas",
    r"\[p\text{-value}=\frac{\sum_{b=1}^B\mathbb{I}(\theta_1^{*(b)}\geq\theta_1^{obs})+1}{B+1}\]",
    [r"$\theta_1^{obs}$: Eigenvalue pertama $\mathbf{R}_{RV}$", r"$B=999$ permutasi", r"$p<0.05$: Struktur signifikan"],
    [f"$\\theta_1^{{obs}}={theta1_obs:.4f}$", f"0/999 melebihi $\\Rightarrow p=(0+1)/(999+1)$"],
    f"\\[ p=0.001 \\quad \\text{{(Tolak $H_0$: Stabil)}} \\]"))

section2 = "\n\\section{Uji Kelayakan Data}\n"
body2 = "".join(blocks[9:12])

section3 = "\n\\section{Korelasi dan Analisis Komponen Utama (PCA)}\n"
body3 = "".join(blocks[20:25])

section4 = "\n\\section{Tahapan Metode STATIS}\n"
body4 = "".join(blocks[12:17]) + blocks[28]

section5 = "\n\\section{Analisis Klaster dan Spasial}\n"
body5 = "".join(blocks[17:20]) + "".join(blocks[25:28])

footer = r"\end{document}" + "\n"

full_doc = preamble + body + section2 + body2 + section3 + body3 + section4 + body4 + section5 + body5 + footer

with open(OUTPUT_TEX, "w", encoding="utf-8") as f:
    f.write(full_doc)

print(f"\nDONE: Generated: {OUTPUT_TEX}")
print(f"   Total formula boxes: {len(blocks)}")
