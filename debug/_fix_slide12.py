import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'd:\Skripsi\my\Presentation\sidang_skripsi.html', 'r', encoding='utf-8') as f:
    html = f.read()

old = '''  // SLIDE 12 — DYNAMIC BIPLOT
  `<div class="slide" data-idx="11">
    <div class="slide-body">
      <div class="sec-label">BAB 2 · Tinjauan Pustaka</div>
      <div class="slide-h">Dynamic Biplot &amp; Trajektori</div>
      <div class="slide-sub">Visualisasi pergerakan objek dan indikator dalam ruang berdimensi rendah lintas waktu</div>
      <div class="g2">
        <div>
          <div class="card" style="margin-bottom:12px;">
            <h4>📈 Apa itu Biplot?</h4>
            <p>Biplot memproyeksikan <strong>skor objek</strong> (kabupaten/kota) dan <strong>loading variabel</strong> (indikator) ke dalam satu bidang 2D. Arah panah loading menunjukkan korelasi antar-indikator; posisi objek menggambarkan karakteristik relatifnya.</p>
          </div>
          <div class="card gold">
            <h4>🔄 Dynamic Biplot</h4>
            <p><em>Dynamic Biplot</em> menghubungkan posisi setiap kabupaten/kota <strong>dari tahun ke tahun</strong> dengan garis lintasan (trajectory), sehingga pergerakan struktural dapat divisualisasikan secara dinamis.</p>
            <ul style="margin-top:8px;">
              <li>F<sub>k</sub> = Z<sub>k</sub> · V → skor objek tahun k</li>
              <li>G<sub>k</sub> = W<sub>k</sub> · V → loading indikator tahun k</li>
            </ul>
          </div>
        </div>
        <div>
          <div class="card green" style="margin-bottom:12px;">
            <h4>3 Pola Trajektori yang Teridentifikasi</h4>
            <div style="margin-top:8px;">
              <div style="display:flex;gap:10px;align-items:center;margin-bottom:8px;"><span style="font-size:1.2rem;">📈</span><div style="font-size:.8rem;"><strong style="color:var(--blue)">V-Shape Rebound:</strong> Turun 2020→2021, naik kuat 2022→2024. Pola metropolitan berbasis jasa.</div></div>
              <div style="display:flex;gap:10px;align-items:center;margin-bottom:8px;"><span style="font-size:1.2rem;">📊</span><div style="font-size:.8rem;"><strong style="color:var(--blue)">Progresif Monoton:</strong> Peningkatan bertahap sepanjang 2020–2024. Kota penyangga berkembang.</div></div>
              <div style="display:flex;gap:10px;align-items:center;"><span style="font-size:1.2rem;">📉</span><div style="font-size:.8rem;"><strong style="color:#c0392b">Stagnasi/Inersia:</strong> PC1 stagnan atau turun. Kabupaten pedalaman selatan — kesenjangan melebar.</div></div>
            </div>
          </div>
          <div class="hl">
            <p><strong>Rotasi Baseline:</strong> Dalam dashboard interaktif, sumbu dapat dirotasi agar trajectory tampak lebih informatif. Jarak Euclidean antar-trajectory mengukur perbedaan pola pergerakan antar wilayah.</p>
          </div>
        </div>
      </div>
    </div>
  </div>`,'''

new = '''  // SLIDE 12 — DYNAMIC BIPLOT
  `<div class="slide" data-idx="11">
    <div class="slide-body">
      <div class="sec-label">BAB 2 · Tinjauan Pustaka</div>
      <div class="slide-h">Dynamic Biplot &amp; Trajektori</div>
      <div class="slide-sub">Perbedaan rumus antara Biplot PCA biasa (Pers. 2.27) dan Biplot STATIS per tahun (Pers. 2.39–2.42)</div>
      <div class="g2" style="gap:16px;align-items:start;">
        <div>
          <div class="card" style="margin-bottom:11px;">
            <h4>📊 Biplot PCA (Pers. 2.27)</h4>
            <p style="font-size:.85em;margin-bottom:7px;">Diterapkan pada <strong>satu matriks data</strong> tunggal. Skor &amp; loading dari dekomposisi spektral <strong>S = V&Lambda;V<sup>T</sup></strong>:</p>
            <table style="width:100%;font-size:.83em;border-collapse:collapse;">
              <tr><td style="padding:3px 6px;font-weight:700;color:var(--blue);">Skor objek</td><td style="padding:3px 6px;font-family:monospace;"><strong>F = XV</strong></td><td style="padding:3px 6px;font-size:.79em;color:#666;">X: data std, V: vektor eigen</td></tr>
              <tr style="background:rgba(0,0,0,.03);"><td style="padding:3px 6px;font-weight:700;color:var(--blue);">Loading variabel</td><td style="padding:3px 6px;font-family:monospace;"><strong>G = V</strong></td><td style="padding:3px 6px;font-size:.79em;color:#666;">kolom = vektor loading</td></tr>
            </table>
            <p style="font-size:.79em;margin-top:6px;color:#888;">&#9888; Statis — hanya 1 periode, tidak menangkap perubahan lintas waktu.</p>
          </div>
          <div class="card gold">
            <h4>🔄 Biplot STATIS Skenario 1 (Pers. 2.39–2.42)</h4>
            <p style="font-size:.83em;margin-bottom:7px;">Tiap tahun k diproyeksikan ke <strong>ruang kompromi</strong> bersama. Bobot D = diag(m<sub>i</sub>):</p>
            <table style="width:100%;font-size:.81em;border-collapse:collapse;">
              <tr><td style="padding:3px 5px;font-weight:700;color:#b45309;white-space:nowrap;">Skor kompromi (2.39)</td><td style="padding:3px 5px;font-family:monospace;"><strong>F<sub>c</sub> = D<sup>-1/2</sup>P&Lambda;<sub>c</sub><sup>1/2</sup></strong></td></tr>
              <tr style="background:rgba(0,0,0,.03);"><td style="padding:3px 5px;font-weight:700;color:#b45309;white-space:nowrap;">Skor parsial thn k (2.40)</td><td style="padding:3px 5px;font-family:monospace;"><strong>F<sub>k</sub> = W<sub>k</sub>DP&Lambda;<sub>c</sub><sup>-1/2</sup></strong></td></tr>
              <tr><td style="padding:3px 5px;font-weight:700;color:#b45309;white-space:nowrap;">Loading parsial (2.41)</td><td style="padding:3px 5px;font-family:monospace;"><strong>G<sub>k</sub> = Z<sub>k</sub><sup>T</sup>DF<sub>c</sub>&Lambda;<sub>c</sub><sup>-1/2</sup></strong></td></tr>
              <tr style="background:rgba(0,0,0,.03);"><td style="padding:3px 5px;font-weight:700;color:#b45309;white-space:nowrap;">Loading kompromi (2.42)</td><td style="padding:3px 5px;font-family:monospace;"><strong>G<sub>c</sub> = &Sigma;&alpha;<sub>k</sub>G<sub>k</sub></strong></td></tr>
            </table>
            <p style="font-size:.79em;margin-top:6px;color:#92400e;">W<sub>k</sub> = Z<sub>k</sub>Z<sub>k</sub><sup>T</sup> (prod. skalar); P,&Lambda;<sub>c</sub> dari SVD W<sub>c</sub> terbobot D.</p>
          </div>
        </div>
        <div>
          <div class="card green" style="margin-bottom:11px;">
            <h4>📍 Kunci Perbedaan PCA vs STATIS</h4>
            <table style="width:100%;font-size:.81em;border-collapse:collapse;margin-top:6px;">
              <thead><tr style="background:rgba(39,174,96,.15);"><th style="padding:4px 6px;text-align:left;">Aspek</th><th style="padding:4px 6px;text-align:left;">PCA Biasa</th><th style="padding:4px 6px;text-align:left;">STATIS</th></tr></thead>
              <tbody>
                <tr><td style="padding:3px 6px;">Data</td><td style="padding:3px 6px;">1 tabel Z</td><td style="padding:3px 6px;">K tabel Z<sub>k</sub> per tahun</td></tr>
                <tr style="background:rgba(0,0,0,.03);"><td style="padding:3px 6px;">Skor</td><td style="padding:3px 6px;">F = XV (statis)</td><td style="padding:3px 6px;">F<sub>k</sub> berbeda tiap k</td></tr>
                <tr><td style="padding:3px 6px;">Bobot</td><td style="padding:3px 6px;">Tidak ada</td><td style="padding:3px 6px;">D = diag(m<sub>i</sub>)</td></tr>
                <tr style="background:rgba(0,0,0,.03);"><td style="padding:3px 6px;">Ruang acuan</td><td style="padding:3px 6px;">S = V&Lambda;V<sup>T</sup></td><td style="padding:3px 6px;">W<sub>c</sub> = &Sigma;&alpha;<sub>k</sub>W<sub>k</sub></td></tr>
                <tr><td style="padding:3px 6px;">Output</td><td style="padding:3px 6px;">1 biplot</td><td style="padding:3px 6px;">K biplot → trajektori</td></tr>
              </tbody>
            </table>
          </div>
          <div class="card red" style="margin-bottom:11px;">
            <h4>📈 3 Pola Trajektori</h4>
            <div style="font-size:.83em;margin-top:5px;">
              <div style="display:flex;gap:8px;align-items:center;margin-bottom:5px;"><span>📈</span><div><strong>V-Shape Rebound:</strong> Turun 2020→2021, naik kuat 2022→2024. Metropolitan berbasis jasa.</div></div>
              <div style="display:flex;gap:8px;align-items:center;margin-bottom:5px;"><span>📊</span><div><strong>Progresif Monoton:</strong> Peningkatan bertahap. Kota penyangga &amp; koridor industri.</div></div>
              <div style="display:flex;gap:8px;align-items:center;"><span>📉</span><div><strong>Stagnasi/Inersia:</strong> PC1 stagnan atau turun — pedalaman selatan, kesenjangan melebar.</div></div>
            </div>
          </div>
          <div class="hl" style="font-size:.83em;">
            <strong>Trajektori = lintasan F<sub>k</sub></strong> tiap wilayah dihubungkan berurutan 2020→…→2024. Jarak antar-titik mengukur besarnya perubahan posisi struktural relatif.
          </div>
        </div>
      </div>
    </div>
  </div>`,'''

if old not in html:
    print("NOT FOUND — checking nearby...")
    idx = html.find('SLIDE 12')
    print(repr(html[idx:idx+200]))
    import sys; sys.exit(1)

html = html.replace(old, new, 1)
with open(r'd:\Skripsi\my\Presentation\sidang_skripsi.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Done. {len(html)} chars.")
