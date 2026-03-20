import { useState, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import './App.css';

// Initialize PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

function App() {
  const [activeModal, setActiveModal] = useState(null);
  const [password, setPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [isShaking, setIsShaking] = useState(false);
  const [iframeLoading, setIframeLoading] = useState(true);

  // PDF Reader State
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [pdfScale, setPdfScale] = useState(1.2);

  // Gallery Lightbox State
  const [lightboxImage, setLightboxImage] = useState(null);

  // Gallery Data
  const galleryItems = [
    {
      src: "/images/pca_biplot_animation.gif",
      caption: "Animasi Perubahan Struktur (Dynamic Biplot)"
    },
    {
      src: "/images/titik_dan_vektor_v2.png",
      caption: "Detail Titik dan Vektor Korelasi STATIS"
    }
  ];

  // Re-run MathJax typesetting when a modal is opened, just in case MathJax missed it initially
  useEffect(() => {
    if (activeModal && window.MathJax) {
      window.MathJax.typesetPromise && window.MathJax.typesetPromise();
    }
  }, [activeModal]);

  const openModal = (id) => {
    setActiveModal(id);
    if (id === 'pdf-auth') {
      setPassword('');
      setPasswordError('');
      setIsShaking(false);
    }
    if (id === 'pdf-reader') {
      setPageNumber(1);
      setPdfScale(1.2);
    }
    if (id === 'web-app') {
      setIframeLoading(true);
    }
  };
  const closeModal = () => {
    setActiveModal(null);
    setLightboxImage(null);
  };

  const handlePdfSubmit = () => {
    if (password === '2206051582') {
      openModal('pdf-reader');
    } else {
      setPasswordError('Kata sandi salah. Silakan coba lagi.');
      setIsShaking(true);
      setTimeout(() => setIsShaking(false), 400); // Remove shake class after animation
    }
  };

  const onDocumentLoadSuccess = ({ numPages }) => {
    setNumPages(numPages);
  };

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
          <div
            className="card glass-effect"
            onClick={() => openModal('pdf-auth')}
          >
            <div className="card-icon">📄</div>
            <h2>Dokumen Skripsi (PDF)</h2>
            <p>
              Baca dokumen selengkapnya, memuat bab 1 hingga kesimpulan dan
              lampiran. (Dilindungi Kata Sandi)
            </p>
          </div>

          {/* Web App Card */}
          <div
            className="card glass-effect highlight"
            onClick={() => openModal('web-app')}
          >
            <div className="card-icon">🌐</div>
            <h2>Website Aplikasi</h2>
            <p>
              Jelajahi visualisasi interaktif (Trajectory, K-Means Clustering,
              Peta Tematik) secara langsung.
            </p>
          </div>

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
        className={`modal ${activeModal === 'pdf-auth' ? 'active' : ''}`}
        onClick={(e) => {
          if (e.target.classList.contains('modal')) closeModal();
        }}
      >
        <div className={`modal-content glass-effect ${isShaking ? 'shake' : ''}`} style={{ maxWidth: '400px', textAlign: 'center' }}>
          <button className="close-btn" onClick={closeModal} title="Tutup">
            &times;
          </button>
          <h2>Akses Terbatas</h2>
          <div className="modal-body">
            <p style={{ marginBottom: '1.5rem' }}>
              Masukkan kata sandi untuk membuka dokumen PDF Skripsi.
            </p>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handlePdfSubmit() }}
              placeholder="Kata Sandi..."
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                border: `1px solid ${passwordError ? 'rgba(248, 113, 113, 0.8)' : 'rgba(255,255,255,0.2)'}`,
                background: 'rgba(0,0,0,0.2)',
                color: '#fff',
                fontSize: '1rem',
                marginBottom: '1rem',
                outline: 'none',
                transition: 'border-color 0.3s'
              }}
            />
            {passwordError && (
              <p style={{ color: '#f87171', fontSize: '0.9rem', marginBottom: '1rem' }}>
                {passwordError}
              </p>
            )}
            <button
              onClick={handlePdfSubmit}
              style={{
                background: 'linear-gradient(to right, #3b82f6, #8b5cf6)',
                color: 'white',
                border: 'none',
                padding: '0.75rem 2rem',
                borderRadius: '8px',
                fontSize: '1rem',
                fontWeight: '600',
                cursor: 'pointer',
                width: '100%',
                transition: 'opacity 0.2s'
              }}
              onMouseOver={(e) => e.target.style.opacity = '0.9'}
              onMouseOut={(e) => e.target.style.opacity = '1'}
            >
              Buka Dokumen
            </button>
          </div>
        </div>
      </div>

      <div
        className={`modal ${activeModal === 'pdf-reader' ? 'active' : ''}`}
        onClick={(e) => {
          if (e.target.classList.contains('modal')) closeModal();
        }}
      >
        <div className="modal-content glass-effect pdf-reader-modal" style={{ maxWidth: '900px', width: '90vw', height: '90vh', display: 'flex', flexDirection: 'column', padding: '1rem' }}>
          <button className="close-btn" onClick={closeModal} title="Tutup" style={{ zIndex: 10, top: '1rem', right: '1rem' }}>
            &times;
          </button>
          <div className="pdf-toolbar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', background: 'rgba(0,0,0,0.3)', padding: '0.8rem', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)' }}>
            <div className="pdf-controls" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button disabled={pageNumber === '' || pageNumber <= 1} onClick={() => setPageNumber(p => Math.max(p - 1, 1))} className="pdf-btn">
                Sebelumnya
              </button>
              <span style={{ margin: '0 5px', fontWeight: 'bold', display: 'flex', alignItems: 'center' }}>
                Halaman <input
                  type="number"
                  value={pageNumber}
                  onChange={(e) => {
                    if (e.target.value === '') {
                      setPageNumber('');
                    } else {
                      const val = parseInt(e.target.value);
                      if (!isNaN(val)) setPageNumber(val);
                    }
                  }}
                  onBlur={() => {
                    let val = parseInt(pageNumber);
                    if (isNaN(val) || val < 1) val = 1;
                    if (val > numPages) val = numPages;
                    setPageNumber(val);
                  }}
                  style={{ width: '60px', textAlign: 'center', margin: '0 8px', background: 'rgba(0,0,0,0.5)', color: 'white', border: '1px solid rgba(255,255,255,0.2)', borderRadius: '4px', padding: '4px' }}
                  min={1}
                  max={numPages || 1}
                /> dari {numPages || '--'}
              </span>
              <button disabled={pageNumber === '' || pageNumber >= numPages} onClick={() => setPageNumber(p => Math.min(p + 1, numPages))} className="pdf-btn">
                Selanjutnya
              </button>
            </div>
            <div className="pdf-zoom" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <button onClick={() => setPdfScale(s => Math.max(s - 0.2, 0.5))} className="pdf-btn" title="Perkecil">➖</button>
              <span style={{ margin: '0 10px' }}>{Math.round(pdfScale * 100)}%</span>
              <button onClick={() => setPdfScale(s => Math.min(s + 0.2, 3))} className="pdf-btn" title="Perbesar">➕</button>
            </div>
          </div>

          <div
            className="pdf-viewer-container"
            style={{ flex: 1, overflowY: 'auto', background: '#333', borderRadius: '8px', display: 'flex', justifyContent: 'center', padding: '1rem' }}
            onContextMenu={(e) => e.preventDefault()}
          >
            {activeModal === 'pdf-reader' && (
              <Document
                file="/skrp_doc_vault_9x.dat"
                onLoadSuccess={onDocumentLoadSuccess}
                loading={
                  <div className="spinner-container" style={{ background: 'transparent' }}>
                    <div className="spinner"></div><p style={{ color: 'white' }}>Memuat Dokumen Rahasia...</p>
                  </div>
                }
                error={<p style={{ color: '#f87171' }}>Gagal memuat dokumen utama. Format tidak dikenali.</p>}
              >
                <Page
                  pageNumber={pageNumber === '' ? 1 : pageNumber}
                  scale={pdfScale}
                  renderTextLayer={false}
                  renderAnnotationLayer={false}
                  className="pdf-canvas-page"
                />
              </Document>
            )}
          </div>
          <div style={{ textAlign: 'center', fontSize: '0.8rem', color: '#94a3b8', marginTop: '0.8rem' }}>
            Dokumen ini dilindungi: Pengunduhan, Pencetakan, dan Klik Kanan dinonaktifkan.
          </div>
        </div>
      </div>

      <div
        className={`modal ${activeModal === 'web-app' ? 'active' : ''}`}
        onClick={(e) => {
          if (e.target.classList.contains('modal')) closeModal();
        }}
      >
        <div className="modal-content glass-effect" style={{ width: '90vw', maxWidth: 'none', height: '90vh', padding: '1rem', display: 'flex', flexDirection: 'column', position: 'relative' }}>
          <button className="close-btn" onClick={closeModal} style={{ zIndex: 10, top: '0.5rem', right: '0.5rem' }}>
            &times;
          </button>
          <div style={{ flex: 1, borderRadius: '12px', overflow: 'hidden', marginTop: '1rem', background: '#fff', position: 'relative' }}>
            {iframeLoading && (
              <div className="spinner-container">
                <div className="spinner"></div>
                <p style={{ color: '#64748b', fontWeight: '500' }}>Tunggu sebentar, sedang memuat Data Engine...</p>
              </div>
            )}
            {activeModal === 'web-app' && (
              <iframe
                src="https://ammarhnfi-skripsiv2.hf.space"
                style={{ width: '100%', height: '100%', border: 'none' }}
                title="Aplikasi Python Interaktif"
                onLoad={() => setIframeLoading(false)}
              />
            )}
          </div>
        </div>
      </div>

      <div
        className={`modal ${activeModal === 'docs' ? 'active' : ''}`}
        onClick={(e) => {
          if (e.target.classList.contains('modal')) closeModal();
        }}
      >
        <div className="modal-content glass-effect">
          <button className="close-btn" onClick={closeModal} title="Tutup">
            &times;
          </button>
          <h2>Dokumentasi & Hasil</h2>
          <div className="modal-body">
            <h3>Hasil Utama STATIS</h3>
            <p>
              Metode STATIS menghasilkan struktur kompromi yang merupakan rata-rata
              peta posisi ekonomi 41 kabupaten/kota selama 5 tahun. Dari nilai
              eigen utama (Principal Direction), kita dapat menganalisis struktur
              kemiripan karakteristik antar wilayah. Dimensi yang diekstrak kemudian
              digunakan sebagai kanvas biplot untuk melacak perubahan struktur dari
              tahun ke tahun.
            </p>

            <h3>Galeri Visualisasi</h3>
            <p style={{ fontSize: '0.9rem', color: '#94a3b8' }}>
              Klik gambar untuk melihat dalam ukuran penuh.
            </p>
            <div className="photo-grid">
              {galleryItems.map((item, index) => (
                <div
                  key={index}
                  className="thumbnail-container"
                  onClick={() => setLightboxImage(item)}
                >
                  <img src={item.src} alt={item.caption} className="thumbnail-img" />
                  <div className="thumbnail-caption">{item.caption}</div>
                </div>
              ))}
            </div>

          </div>
        </div>
      </div>

      {/* LIGHTBOX OVERLAY */}
      <div
        className={`lightbox ${lightboxImage ? 'active' : ''}`}
        onClick={() => setLightboxImage(null)}
      >
        {lightboxImage && (
          <>
            <button className="close-btn" onClick={() => setLightboxImage(null)} style={{ top: '2rem', right: '2rem' }}>
              &times;
            </button>
            <img src={lightboxImage.src} alt={lightboxImage.caption} />
            <div className="lightbox-caption">{lightboxImage.caption}</div>
          </>
        )}
      </div>

      <div
        className={`modal ${activeModal === 'formulas' ? 'active' : ''}`}
        onClick={(e) => {
          if (e.target.classList.contains('modal')) closeModal();
        }}
      >
        <div className="modal-content glass-effect">
          <button className="close-btn" onClick={closeModal} title="Tutup">
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
          <button className="close-btn" onClick={closeModal} title="Tutup">
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
