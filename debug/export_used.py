"""
export_used.py

Regenerasi ulang HANYA gambar (PNG) yang benar-benar dipakai di induk.pdf,
dengan teks di dalam gambar diperbesar supaya mudah dibaca.

Skrip ini TIDAK menduplikasi logika analisis/plotting apa pun dari
export_all.py -- semua perhitungan (STATIS, PCA, klaster, dst) tetap
dijalankan lewat export_all.py apa adanya (persis seperti
`python export_all.py --real` / `--sampel`), supaya angka & gambar yang
dihasilkan tetap konsisten dengan yang sudah ada. Yang dilakukan skrip ini
hanya dua hal, lewat monkeypatch ke matplotlib & plotly (tanpa mengubah satu
baris pun di export_all.py):

  1. Cari daftar file gambar yang benar-benar di-\\includegraphics oleh
     induk.tex (bab1..bab5, abstract.tex, dst, diikuti secara rekursif).
  2. Saat export_all.py hendak menyimpan sebuah PNG:
       - Kalau path-nya TIDAK ada di daftar gambar terpakai -> proses
         render+simpan di-skip total (di sinilah waktu paling banyak
         dihemat, karena rendering figure -- terutama peta -- baru betul-
         betul terjadi saat disimpan, bukan saat objeknya dibuat).
       - Kalau path-nya ADA di daftar -> semua teks pada figure itu
         (judul, label sumbu, legenda, anotasi, tick label) diperbesar
         dengan faktor --scale (default 1.35x), baru disimpan seperti biasa.

Setelah selesai, langsung compile seperti biasa:
    pdflatex -interaction=nonstopmode induk.tex

Cara pakai:
    python debug/export_used.py                # jalankan --real dan --sampel
    python debug/export_used.py --real          # hanya gambar dari output_real/*
    python debug/export_used.py --sampel        # hanya gambar dari output_sample/*
    python debug/export_used.py --scale 1.6     # faktor perbesar teks (default 1.35)
"""

import os
import re
import sys
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORT_ALL = Path(__file__).resolve().parent / "export_all.py"
MAIN_TEX = ROOT / "induk.tex"


# ============================================================
# 1. Temukan gambar yang benar-benar dipakai di induk.pdf
# ============================================================
def _read(path):
    return path.read_text(encoding="utf-8", errors="ignore")


def find_included_tex(main_tex, seen=None):
    """Ikuti \\include / \\input dari induk.tex secara rekursif."""
    if seen is None:
        seen = set()
    if main_tex in seen or not main_tex.exists():
        return []
    seen.add(main_tex)
    files = [main_tex]
    for name in re.findall(r"\\(?:include|input)\{([^}]+)\}", _read(main_tex)):
        name = name.strip()
        if not name.endswith(".tex"):
            name += ".tex"
        files += find_included_tex((ROOT / name).resolve(), seen)
    return files


def find_used_images(tex_files):
    used = set()
    for tf in tex_files:
        for m in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", _read(tf)):
            m = m.strip().replace("\\", "/")
            if m.startswith("output_real/") or m.startswith("output_sample/"):
                used.add(m.lower())
    return used


USED_IMAGES = find_used_images(find_included_tex(MAIN_TEX))

print(f"[INFO] {len(USED_IMAGES)} gambar output_real/output_sample dipakai di induk.tex:")
for u in sorted(USED_IMAGES):
    print(f"   - {u}")
if not USED_IMAGES:
    print(f"[WARN] Tidak ada \\includegraphics ke output_real/output_sample ditemukan lewat {MAIN_TEX}.")
    print("       Cek apakah induk.tex ada di lokasi itu / strukturnya berubah.")


def _rel_target(fname):
    try:
        return os.path.relpath(os.path.abspath(str(fname)), ROOT).replace("\\", "/").lower()
    except Exception:
        return None


def _is_used(fname):
    rel = _rel_target(fname)
    return rel is not None and rel in USED_IMAGES


# ============================================================
# 2. Faktor perbesar teks
# ============================================================
FONT_SCALE = 1.35
if "--scale" in sys.argv:
    i = sys.argv.index("--scale")
    if i + 1 < len(sys.argv):
        try:
            FONT_SCALE = float(sys.argv[i + 1])
        except ValueError:
            print(f"[WARN] --scale butuh angka, dapat '{sys.argv[i + 1]}'. Pakai default {FONT_SCALE}.")
for arg in sys.argv:
    if arg.startswith("--scale="):
        try:
            FONT_SCALE = float(arg.split("=", 1)[1])
        except ValueError:
            pass

print(f"[INFO] Faktor perbesar teks: {FONT_SCALE}x")


# ============================================================
# 3. Monkeypatch matplotlib & plotly (sekali saja untuk seluruh proses)
# ============================================================
_state = {"mpl_saved": 0, "mpl_skipped": 0, "ply_saved": 0, "ply_skipped": 0}


def _scale_plotly_fonts(fig):
    base = (fig.layout.font.size if fig.layout.font and fig.layout.font.size else 12) * FONT_SCALE
    fig.update_layout(font=dict(size=base))

    if fig.layout.title and fig.layout.title.font and fig.layout.title.font.size:
        fig.update_layout(title_font_size=fig.layout.title.font.size * FONT_SCALE)
    if fig.layout.legend and fig.layout.legend.font and fig.layout.legend.font.size:
        fig.update_layout(legend_font_size=fig.layout.legend.font.size * FONT_SCALE)

    for ax_name in ("xaxis", "yaxis"):
        ax = getattr(fig.layout, ax_name, None)
        if ax is None:
            continue
        if ax.tickfont and ax.tickfont.size:
            ax.tickfont.size = ax.tickfont.size * FONT_SCALE
        if ax.title and ax.title.font and ax.title.font.size:
            ax.title.font.size = ax.title.font.size * FONT_SCALE

    if fig.layout.annotations:
        for ann in fig.layout.annotations:
            if ann.font and ann.font.size:
                ann.font.size = ann.font.size * FONT_SCALE
            else:
                ann.update(font=dict(size=base))

    for tr in fig.data:
        if not hasattr(tr, "textfont"):
            continue
        if tr.textfont is not None and tr.textfont.size:
            tr.textfont.size = tr.textfont.size * FONT_SCALE
        else:
            try:
                tr.update(textfont=dict(size=base))
            except Exception:
                pass


def _patch_all():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.figure
    import matplotlib.text
    import plotly.graph_objects as go

    orig_savefig = matplotlib.figure.Figure.savefig
    orig_write_image = go.Figure.write_image

    def patched_savefig(self, fname, *args, **kwargs):
        if _is_used(fname):
            for t in self.findobj(match=lambda o: isinstance(o, matplotlib.text.Text)):
                try:
                    fs = t.get_fontsize()
                    if fs:
                        t.set_fontsize(fs * FONT_SCALE)
                except Exception:
                    pass
            _state["mpl_saved"] += 1
            return orig_savefig(self, fname, *args, **kwargs)
        _state["mpl_skipped"] += 1
        plt.close(self)
        return None

    def patched_write_image(self, file, *args, **kwargs):
        if _is_used(file):
            try:
                _scale_plotly_fonts(self)
            except Exception as e:
                print(f"  [WARN] Gagal perbesar font plotly untuk {file}: {e}")
            _state["ply_saved"] += 1
            return orig_write_image(self, file, *args, **kwargs)
        _state["ply_skipped"] += 1
        return None

    matplotlib.figure.Figure.savefig = patched_savefig
    go.Figure.write_image = patched_write_image


# ============================================================
# 4. Jalankan export_all.py headless (--real dan/atau --sampel)
# ============================================================
def run_mode(flag):
    print("\n" + "#" * 60)
    print(f"#  export_all.py {flag}  (headless, gambar terpakai saja, font {FONT_SCALE}x)")
    print("#" * 60)
    before = dict(_state)
    sys.argv = ["export_all.py", flag]
    try:
        runpy.run_path(str(EXPORT_ALL), run_name="__main__")
    except SystemExit as e:
        print(f"  [WARN] export_all.py keluar lebih awal (SystemExit {e.code}) saat mode {flag}.")
    after = dict(_state)
    print(f"\n[DONE {flag}] matplotlib: {after['mpl_saved']-before['mpl_saved']} disimpan / "
          f"{after['mpl_skipped']-before['mpl_skipped']} dilewati  |  "
          f"plotly: {after['ply_saved']-before['ply_saved']} disimpan / "
          f"{after['ply_skipped']-before['ply_skipped']} dilewati")


if __name__ == "__main__":
    if not USED_IMAGES:
        sys.exit(1)

    modes = [m for m in ("--real", "--sampel") if m in sys.argv]
    if not modes:
        modes = ["--real", "--sampel"]

    _patch_all()
    for m in modes:
        run_mode(m)

    print("\nSelesai. Sekarang jalankan:  pdflatex -interaction=nonstopmode induk.tex")
