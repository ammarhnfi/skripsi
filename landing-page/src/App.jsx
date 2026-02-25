import { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [activeModal, setActiveModal] = useState(null);

  // Re-run MathJax typesetting when a modal is opened, just in case MathJax missed it initially
  useEffect(() => {
    if (activeModal && window.MathJax) {
      window.MathJax.typesetPromise && window.MathJax.typesetPromise();
    }
  }, [activeModal]);

  const openModal = (id) => setActiveModal(id);
  const closeModal = () => setActiveModal(null);

  return (
    <>
      <div className="background-animation"></div>

      <div className="container">
        <header>
          <h1 className="title">Analisis STATIS dan Biplot Dinamis</h1>
          <p className="subtitle">
            Studi Kasus: Indikator Sosio-Ekonomi di Banten, DKI Jakarta, dan
            Jawa Barat (2020-2024)
          </p>
          <div className="author">Oleh: Ammar Hanafi</div>
        </header>

        <div className="grid-menu">
          {/* PDF Card */}
          <a href="/induk.pdf" target="_blank" rel="noreferrer" className="card glass-effect">
            <div className="card-icon">📄</div>
            <h2>Dokumen Skripsi (PDF)</h2>
            <p>
              Baca dokumen selengkapnya, memuat bab 1 hingga kesimpulan dan
              lampiran.
            </p>
          </a>

          {/* Web App Card */}
          <a
            href="https://huggingface.co/spaces/ammarhnfi/skripsi"
            target="_blank"
            rel="noreferrer"
            className="card glass-effect highlight"
          >
            <div className="card-icon">🌐</div>
            <h2>Website Aplikasi</h2>
            <p>
              Jelajahi visualisasi interaktif (Trajectory, K-Means Clustering,
              Peta Tematik) secara langsung.
            </p>
          </a>

          {/* Documentation Card */}
          <div
            className="card glass-effect"
            onClick={() => openModal('docs')}
          >
            <div className="card-icon">📊</div>
            <h2>Dokumentasi & Hasil</h2>
            <p>
              Kumpulan hasil perhitungan STATIS, matriks kompromi, animasi GIF
              perubahan struktur.
            </p>
          </div>

          {/* Formulas Card */}
          <div
            className="card glass-effect"
            onClick={() => openModal('formulas')}
          >
            <div className="card-icon">🧮</div>
            <h2>Rumus & Referensi</h2>
            <p>
              Lihat secara mendetail formula matematika yang digunakan dan
              daftar pustaka.
            </p>
          </div>

          {/* Dataset Card */}
          <div
            className="card glass-effect"
            onClick={() => openModal('dataset')}
          >
            <div className="card-icon">💾</div>
            <h2>Dataset</h2>
            <p>
              Informasi struktur data panel (41 Kabupaten/Kota, 12 variabel, 5
              tahun).
            </p>
          </div>
        </div>
      </div>

      {/* MODALS */}
      <div
        className={`modal ${activeModal === 'docs' ? 'active' : ''}`}
        onClick={(e) => {
          if (e.target.classList.contains('modal')) closeModal();
        }}
      >
        <div className="modal-content glass-effect">
          <button className="close-btn" onClick={closeModal}>
            &times;
          </button>
          <h2>Dokumentasi & Hasil</h2>
          <div className="modal-body">
            <h3>Visualisasi Perubahan Struktur (GIF)</h3>
            <p>
              <i>
                (Tambahkan file konfigurasi_statis.gif ke dalam repositori utama
                untuk menampilkan animasi)
              </i>
            </p>
            <div className="gif-placeholder">
              <p>[Placeholder GIF / Gambar Hasil Analisis]</p>
            </div>
            <h3>Hasil Utama STATIS</h3>
            <p>
              Metode STATIS menghasilkan struktur kompromi yang merupakan rata-rata
              peta posisi ekonomi 41 kabupaten/kota selama 5 tahun. Dari nilai
              eigen utama (Principal Direction), kita dapat membedah struktur
              kemiripan karakteristik antar wilayah. Dimensi yang diekstrak kemudian
              digunakan sebagai kanvas biplot untuk melacak perubahan struktur dari
              tahun ke tahun.
            </p>
          </div>
        </div>
      </div>

      <div
        className={`modal ${activeModal === 'formulas' ? 'active' : ''}`}
        onClick={(e) => {
          if (e.target.classList.contains('modal')) closeModal();
        }}
      >
        <div className="modal-content glass-effect">
          <button className="close-btn" onClick={closeModal}>
            &times;
          </button>
          <h2>Rumus Utama dan Referensi</h2>
          <div className="modal-body">
            <h3>1. Standardisasi Data (Z-Score)</h3>
            <p>
              Digunakan untuk menyamakan skala unit antar variabel yang beragam
              sehingga tidak mendominasi komputasi multivariat:
            </p>
            <div className="math-formula">
              {`\\[ z_{ijt} = \\frac{x_{ijt} - \\bar{x}_{jt}}{s_{jt}} \\]`}
            </div>

            <h3>2. Tahap Intra-struktur (Pembentukan Matriks Posisi)</h3>
            <p>
              Mendapatkan peta kemiripan antar Kabupaten/Kota pada masing-masing
              tahun waktu (\( t \)):
            </p>
            <div className="math-formula">
              {`\\[ \\mathbf{W}_t = \\mathbf{Z}_t \\mathbf{Z}_t^T \\quad (t=2020, \\dots, 2024) \\]`}
            </div>

            <h3>3. Tahap Inter-struktur (Korelasi RV)</h3>
            <p>
              Menghitung derajat kemiripan global (<i>similarity</i>) secara
              keseluruhan dari matriks posisi antara satu tahun dengan tahun
              yang lain:
            </p>
            <div className="math-formula">
              {`\\[ RV(\\mathbf{W}_{2020}, \\mathbf{W}_{2021}) = \\frac{\\text{tr}(\\mathbf{W}_{2020} \\mathbf{W}_{2021})}{\\sqrt{\\text{tr}(\\mathbf{W}_{2020}^2) \\text{tr}(\\mathbf{W}_{2021}^2)}} \\]`}
            </div>

            <h3>4. Matriks Kompromi</h3>
            <p>
              Matriks stabil (representasi general) dari seluruh pengamatan waktu
              yang diberi beban optimal (\( \\alpha_t \)):
            </p>
            <div className="math-formula">
              {`\\[ \\mathbf{W}_c = \\alpha_{2020}\\mathbf{W}_{2020} + \\dots + \\alpha_{2024}\\mathbf{W}_{2024} \\]`}
            </div>

            <h3>5. Clustering Trajektori</h3>
            <p>
              Model K-Means mendeteksi kelenturan kelompok objek berdasarkan
              lintasan dinamikanya sepanjang tahun pengamatan:
            </p>
            <div className="math-formula">
              {`\\[ J = \\sum_{j=1}^{k} \\sum_{i \\in C_j} ||\\mathbf{x}_i^{(traj)} - \\boldsymbol{\\mu}_j||^2 \\]`}
            </div>

            <hr />
            <h3>Referensi Pilihan</h3>
            <ul className="reference-list">
              <li>
                <strong>Egido & Galindo (2015)</strong> - Dynamic Biplot.
                Evolution of the Economic Freedom in the European Union.
              </li>
              <li>
                <strong>Lavit et al. (1994)</strong> - The ACT (STATIS method).
                Computational Statistics & Data Analysis.
              </li>
              <li>
                <strong>Gabriel (1971)</strong> - The biplot graphic display of
                matrices with application to principal component analysis.
              </li>
              <li>
                <strong>Baltagi (2021)</strong> - Econometric Analysis of Panel
                Data.
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div
        className={`modal ${activeModal === 'dataset' ? 'active' : ''}`}
        onClick={(e) => {
          if (e.target.classList.contains('modal')) closeModal();
        }}
      >
        <div className="modal-content glass-effect">
          <button className="close-btn" onClick={closeModal}>
            &times;
          </button>
          <h2>Informasi Dataset</h2>
          <div className="modal-body">
            <p>
              Penelitian ini memanfaatkan kumpulan data empiris multivariat panel
              (tiga-arah).
            </p>
            <ul>
              <li>
                <strong>{`Unit Observasi (\\(n = 41\\)):`}</strong> Berfokus pada
                41 Kabupaten dan Kota yang merepresentasikan tiga provinsi signifikan:
                Banten, DKI Jakarta, dan Jawa Barat.
              </li>
              <li>
                <strong>{`Dimensi Waktu (\\(K = 5\\)):`}</strong> Pengamatan
                berlangsung selama lima tahun sekuensial (2020, 2021, 2022, 2023,
                2024), mencakup masa fluktuatif (pandemi hingga fase pemulihan
                berkelanjutan).
              </li>
              <li>
                <strong>{`Variabel Panel (\\(p = 12\\)):`}</strong> Terdiri atas
                12 variabel sosio-ekonomi kritis seperti IPM, PDRB per kapita,
                Tingkat Pengangguran Terbuka, Angka Harapan Hidup, dll.
              </li>
            </ul>
            <p>
              Data dikompilasi dari laporan resmi <b>Badan Pusat Statistik (BPS)</b>{' '}
              Republik Indonesia.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}

export default App;
