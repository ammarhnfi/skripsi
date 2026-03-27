import { useState, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import './App.css';

// Initialize PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

/* UTILITY: Renders LaTeX Table string as Visual HTML Table */
function LatexTable({ tex }) {
  if (!tex) return null;

  // 1. IMPROVED MACRO EXTRACTION (e.g. \newcommand{\Name}{Value})
  if (!tex.includes('\\begin{')) {
    const macros = [...tex.matchAll(/\\newcommand\{\\(.*?)\}\{(.*?)\}/g)];
    if (macros.length > 0) {
      return (
        <div style={{ display: 'grid', gap: '8px', padding: '1rem', background: 'rgba(0,0,0,0.2)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.1)' }}>
          {macros.map((m, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.05)', padding: '8px 0' }}>
              <span style={{ color: '#60a5fa', fontWeight: 'bold' }}>{m[1].replace('Macro', '')}:</span>
              <span style={{ color: '#e2e8f0' }}>{m[2]}</span>
            </div>
          ))}
        </div>
      );
    }
  }

  // 2. IMPROVED TABULAR EXTRACTION: Strip environments around tabular/longtable
  const beginMatch = tex.match(/\\begin\{(?:tabular|longtable)\}/);
  if (!beginMatch) {
    return (
      <div style={{ background: '#0f172a', color: '#60a5fa', padding: '20px', borderRadius: '8px', fontFamily: 'monospace', fontSize: '0.85rem', whiteSpace: 'pre-wrap', border: '1px solid rgba(255,255,255,0.1)' }}>
        <pre>{tex}</pre>
      </div>
    );
  }

  // Find actual tabular start (including col spec)
  const realStartMatch = tex.match(/\\begin\{(?:tabular|longtable)\}(?:\[.*?\])?\{/);
  const specStart = realStartMatch.index + realStartMatch[0].length;
  let specEnd = specStart;
  let counter = 1;
  while (counter > 0 && specEnd < tex.length) {
    if (tex[specEnd] === '{') counter++;
    else if (tex[specEnd] === '}') counter--;
    specEnd++;
  }

  const colSpec = tex.substring(specStart, specEnd - 1);
  const expectedCols = colSpec.replace(/[| ]|{[^{}]*}/g, '').length || 2;
  const bodyWithEnd = tex.substring(specEnd);
  const endTagMatch = bodyWithEnd.match(/(.*?)\\end\{(?:tabular|longtable)\}/s);
  if (!endTagMatch) return <pre style={{ whiteSpace: 'pre-wrap' }}>{tex}</pre>;
  
  const body = endTagMatch[1];

  // 3. ROBUST CLEANING
  const rowsRaw = body.split(/\\\\/).filter(r => r.trim().length > 0 && !r.trim().startsWith('%'));
  const rows = rowsRaw.map(rowStr => {
    let cleanRow = rowStr
      .replace(/\\rowcolor\{.*?\}/g, '')
      .replace(/\\multicolumn\{.*?\}/g, (m) => m.match(/\{(?:[^}]*)\}\{(?:[^}]*)\}\{(.*)\}/)?.[1] || '')
      .replace(/\\hline/g, '').replace(/\\arraybackslash/g, '').replace(/\\raggedright/g, '').replace(/\\centering/g, '')
      .replace(/\\toprule/g, '').replace(/\\midrule/g, '').replace(/\\bottomrule/g, '')
      .replace(/\\makecell\[?.*?\]?\{(.*?)\}/sg, '$1')
      .trim();
    
    if (!cleanRow || cleanRow === '}') return null;

    let cells = cleanRow.split('&').map(cell => {
      let content = cell.trim()
        .replace(/\\textbf\{(.*?)\}/g, '$1').replace(/\\textit\{(.*?)\}/g, '<i>$1</i>')
        .replace(/\\bfseries/g, '').replace(/\\small/g, '').replace(/\\scriptsize/g, '')
        .replace(/\\%/g, '%').replace(/\\&/g, '&').replace(/\\\$/g, '$').replace(/\\_/g, '_')
        .replace(/\\rightarrow/g, '→').replace(/\\textrightarrow/g, '→')
        .replace(/\\\(|\\\)/g, '').replace(/\\text\{(.*?)\}/g, '$1')
        .replace(/\{/g, '').replace(/\}/g, '');
      return content;
    });

    if (cells.length > expectedCols) {
      const fixedCells = cells.slice(0, expectedCols - 1);
      const mergedExtra = cells.slice(expectedCols - 1).join(': ');
      fixedCells.push(mergedExtra);
      cells = fixedCells;
    }
    return cells;
  }).filter(r => r !== null && r.length > 0);

  return (
    <div style={{ overflowX: 'auto', width: '100%', borderRadius: '12px', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
        <tbody>
          {rows.map((row, rI) => (
            <tr key={rI} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', background: rI === 0 ? 'rgba(59, 130, 246, 0.1)' : 'transparent' }}>
              {row.map((cell, cI) => (
                <td key={cI} style={{ padding: '12px 14px', borderRight: '1px solid rgba(255,255,255,0.05)', color: rI === 0 ? '#60a5fa' : '#e2e8f0', fontWeight: rI === 0 ? '700' : '400', textAlign: cI === 0 ? 'left' : 'center' }} dangerouslySetInnerHTML={{ __html: cell }} />
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

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

  const [allResults, setAllResults] = useState([]);
  const [equations, setEquations] = useState([]);
  const [currentTime, setCurrentTime] = useState("");
  const [selectedGroup, setSelectedGroup] = useState('Hasil Utama STATIS');
  const [texContent, setTexContent] = useState(null);
  const [lightboxImage, setLightboxImage] = useState(null);
  const [currentGalleryIndex, setCurrentGalleryIndex] = useState(-1);

  // Helper: Get filtered documentation list based on active group
  const getFilteredDocs = () => (allResults || []).filter(item => item && String(item.group || 'Lain-lain') === selectedGroup);

  useEffect(() => {
    // Current Time Update (WIB)
    const updateTime = () => {
      const options = { 
        timeZone: 'Asia/Jakarta',
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      };
      const formatter = new Intl.DateTimeFormat('id-ID', options);
      setCurrentTime(formatter.format(new Date()) + " WIB");
    };
    updateTime();
    const timer = setInterval(updateTime, 1000);
    
    // Fetch Gallery
    fetch('/output_app_manifest.json')
      .then(res => res.json())
      .then(data => {
        const staticItems = [
          {
            src: "/images/pca_biplot_animation.gif",
            caption: "Animasi Perubahan Struktur (Dynamic Biplot)",
            type: 'image',
            group: 'Highlights'
          },
          {
            src: "/images/titik_dan_vektor_v2.png",
            caption: "Detail Titik dan Vektor Korelasi STATIS",
            type: 'image',
            group: 'Highlights'
          }
        ];
        setAllResults([...staticItems, ...data]);
      })
      .catch(err => console.error("Failed to load results manifest:", err));

    // Fetch Equations
    fetch('/equations.json')
      .then(res => res.json())
      .then(data => setEquations(data))
      .catch(err => console.error("Failed to load equations:", err));

    return () => clearInterval(timer);
  }, []);

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
    setTexContent(null);
  };

  const openTexPreview = async (src, index = -1) => {
    try {
      const response = await fetch(src);
      const text = await response.text();
      setTexContent(text);
      setCurrentGalleryIndex(index);
      setActiveModal('tex-preview');
    } catch (err) {
      console.error("Failed to load .tex file:", err);
    }
  };

  const navigateGallery = (direction) => {
    const filtered = getFilteredDocs();
    if (filtered.length === 0) return;

    let nextIndex = (currentGalleryIndex + direction + filtered.length) % filtered.length;
    const nextItem = filtered[nextIndex];

    if (nextItem.type === 'image') {
      setLightboxImage(nextItem);
      setTexContent(null);
      setActiveModal(null); // Lightbox is handled separately by lightboxImage state
      setCurrentGalleryIndex(nextIndex);
    } else {
      setLightboxImage(null);
      openTexPreview(nextItem.src, nextIndex);
    }
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

        <footer>
          <div className="update-note">
            🚀 Terakhir Diperbarui: <span className="timestamp">{currentTime}</span>
          </div>
          <p className="copyright">&copy; 2026 Universitas Indonesia</p>
        </footer>
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
        <div className="modal-content glass-effect" style={{ maxWidth: '1000px', width: '95vw' }}>
          <button className="close-btn" onClick={closeModal} title="Tutup">
            &times;
          </button>
          <h2>Dokumentasi & Hasil Analisis</h2>
          <div className="modal-body">
            <p>
              Hasil pengolahan data STATIS, K-Means Clustering, dan Uji Spasial
              Moran's I yang dihasilkan secara otomatis oleh sistem.
            </p>

            {/* Group Selector Tags */}
            <div className="group-selector" style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '20px', padding: '10px 0' }}>
              {[...new Set(allResults.map(r => String(r.group || 'Lain-lain')))].sort().map(group => (
                <button
                  key={group}
                  onClick={() => setSelectedGroup(group)}
                  style={{
                    padding: '6px 14px',
                    borderRadius: '20px',
                    border: '1px solid rgba(255,255,255,0.2)',
                    background: selectedGroup === group ? 'rgba(59, 130, 246, 0.6)' : 'rgba(255,255,255,0.05)',
                    color: 'white',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                    transition: 'all 0.2s'
                  }}
                >
                  {group}
                </button>
              ))}
            </div>

            <div className="photo-grid" style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', 
              gap: '20px',
              maxHeight: '60vh',
              overflowY: 'auto',
              paddingRight: '10px'
            }}>
              {(allResults || []).filter(item => item && String(item.group || 'Lain-lain') === selectedGroup).map((item, index) => (
                <div
                  key={index}
                  className="thumbnail-container"
                  onClick={() => item && item.type === 'image' ? (setLightboxImage(item), setCurrentGalleryIndex(index)) : openTexPreview(item.src, index)}
                  style={{ transition: 'transform 0.2s', cursor: 'pointer' }}
                >
                  {item && item.type === 'image' ? (
                    <img src={item.src} alt={String(item.caption || '')} className="thumbnail-img" style={{ width: '100%', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }} />
                  ) : (
                    <div style={{ 
                      width: '100%', 
                      aspectRatio: '3/2', 
                      background: 'rgba(0,0,0,0.3)', 
                      display: 'flex', 
                      flexDirection: 'column',
                      alignItems: 'center', 
                      justifyContent: 'center', 
                      borderRadius: '8px',
                      border: '1px solid rgba(255,255,255,0.2)',
                      padding: '10px',
                      textAlign: 'center'
                    }}>
                      <div style={{ fontSize: '2rem', marginBottom: '5px' }}>📄</div>
                      <div style={{ fontSize: '0.75rem', fontWeight: 'bold' }}>{String(item ? (item.name || item.caption) : '')}</div>
                    </div>
                  )}
                  <div className="thumbnail-caption" style={{ marginTop: '8px', fontSize: '0.8rem', textAlign: 'center', color: '#cbd5e1' }}>
                    {String((item ? item.caption : '') || '')}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* TEX PREVIEW MODAL */}
      <div
        className={`modal ${activeModal === 'tex-preview' ? 'active' : ''}`}
        onClick={(e) => {
          if (e.target.classList.contains('modal')) setActiveModal('docs');
        }}
      >
        <div className="modal-content glass-effect" style={{ maxWidth: '1000px', width: '95vw', height: '90vh', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '1rem' }}>
            <button 
              className="back-lib-btn" 
              onClick={() => { setActiveModal('docs'); setTexContent(null); }}
              style={{ background: 'rgba(255,255,255,0.1)', border: 'none', color: '#60a5fa', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer', fontSize: '0.8rem', fontWeight: 'bold' }}
            >
              ⬅ Kembali ke Galeri
            </button>
            <h2 style={{ margin: 0, border: 'none', padding: 0 }}>Visualisasi Tabel Hasil</h2>
            <div className="nav-controls" style={{ display: 'flex', gap: '8px' }}>
              <button className="pdf-btn" onClick={() => navigateGallery(-1)}>Sebelumnya</button>
              <button className="pdf-btn" onClick={() => navigateGallery(1)}>Selanjutnya</button>
            </div>
          </div>
          <div className="modal-body" style={{ flex: 1, overflowY: 'auto' }}>
            <LatexTable tex={texContent} />
          </div>
        </div>
      </div>

      {/* LIGHTBOX OVERLAY */}
      <div
        className={`lightbox ${lightboxImage ? 'active' : ''}`}
        onClick={() => { setLightboxImage(null); if (currentGalleryIndex !== -1) setActiveModal('docs'); }}
      >
        {lightboxImage && (
          <>
            <button className="close-btn" onClick={() => { setLightboxImage(null); setActiveModal('docs'); }} style={{ top: '2rem', right: '2rem' }}>
              &times;
            </button>
            
            <div className="lightbox-nav-top" style={{ position: 'fixed', top: '2rem', left: '50%', transform: 'translateX(-50%)', display: 'flex', gap: '20px', z_index: 2001 }}>
               <button className="pdf-btn" onClick={(e) => { e.stopPropagation(); navigateGallery(-1); }}>⬅ Sebelumnya</button>
               <button className="pdf-btn" onClick={(e) => { e.stopPropagation(); navigateGallery(1); }}>Selanjutnya ➡</button>
            </div>

            <img src={lightboxImage.src} alt={lightboxImage.caption} onClick={(e) => e.stopPropagation()} />
            <div className="lightbox-caption">{lightboxImage.caption}</div>
            
            <button 
              onClick={(e) => { e.stopPropagation(); setLightboxImage(null); setActiveModal('docs'); }}
              style={{ position: 'fixed', bottom: '2rem', background: 'rgba(59, 130, 246, 0.5)', color: 'white', border: 'none', padding: '10px 20px', borderRadius: '30px', cursor: 'pointer', backdropFilter: 'blur(5px)' }}
            >
              Kembali ke Galeri
            </button>
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
          <div className="modal-body" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
            <p style={{ marginBottom: '1.5rem', color: '#94a3b8' }}>
              Formula matematika yang digunakan dalam landasan teori (@bab2.tex).
            </p>
            {equations.length > 0 ? (
              <div className="equation-grid">
                {equations.map((eq, i) => (
                  <div key={i} className="eq-item" style={{ marginBottom: '2rem', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '1rem' }}>
                    <div className="eq-label" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', color: '#60a5fa', fontWeight: 'bold' }}>{eq.section}</span>
                      <span style={{ fontSize: '0.6rem', color: '#64748b' }}>#{i + 1}</span>
                    </div>
                    <div className="math-formula" style={{ background: 'rgba(0,0,0,0.2)', padding: '1.5rem', borderRadius: '8px', overflow: 'hidden' }}>
                      {eq.latex}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p>Sedang mengekstrak rumus dari dokumen...</p>
            )}

            <hr style={{ borderColor: 'rgba(255,255,255,0.1)', margin: '2rem 0' }} />
            <h3>Referensi Pilihan (Ekonometrika & Multivariat)</h3>
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
