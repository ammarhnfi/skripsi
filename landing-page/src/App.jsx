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


function SideBySideTexCard({ filename, folder, hasLeft, hasRight }) {
  const [leftTex, setLeftTex] = useState('');
  const [rightTex, setRightTex] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    async function fetchData() {
      try {
        setLoading(true);
        const leftPath = `/` + folder + `/scenario1/` + filename;
        const rightPath = `/` + folder + `/scenario2/` + filename;

        const promises = [];
        if (hasLeft) promises.push(fetch(leftPath).then(r => r.text()));
        else promises.push(Promise.resolve(''));

        if (hasRight) promises.push(fetch(rightPath).then(r => r.text()));
        else promises.push(Promise.resolve(''));

        const [leftData, rightData] = await Promise.all(promises);

        if (active) {
          setLeftTex(leftData);
          setRightTex(rightData);
          setLoading(false);
        }
      } catch (err) {
        console.error("Error fetching side-by-side tables:", err);
        if (active) setLoading(false);
      }
    }
    fetchData();
    return () => { active = false; };
  }, [filename, folder, hasLeft, hasRight]);

  const cleanTitle = filename.replace('output_table_', '').replace(/_/g, ' ').replace('.tex', '').toUpperCase();

  return (
    <div style={{ background: 'rgba(30, 41, 59, 0.4)', borderRadius: '20px', padding: '24px', marginBottom: '24px', border: '1px solid rgba(255,255,255,0.06)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '12px' }}>
        <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#f8fafc', fontWeight: '600' }}>{cleanTitle}</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ background: 'rgba(6, 182, 212, 0.1)', color: '#06b6d4', border: '1px solid rgba(6, 182, 212, 0.2)', borderRadius: '20px', padding: '3px 10px', fontSize: '0.75rem', fontWeight: '600' }}>DATA MATRIX/TABLE</span>
          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Filename: {filename}</span>
        </div>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '120px' }}>
          <div className="spinner" style={{ width: '30px', height: '30px' }}></div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px' }}>
          {/* Left: Scenario 1 */}
          <div style={{ minWidth: 0, overflow: 'hidden' }}>
            <div style={{ fontWeight: '600', color: '#06B6D4', fontSize: '0.75rem', marginBottom: '10px', letterSpacing: '0.5px', textTransform: 'uppercase' }}>SKENARIO 1 (ACT KLASIK - HOST WILAYAH / MATRIKS W)</div>
            {hasLeft ? <LatexTable tex={leftTex} /> : <div className="placeholder-box" style={{ padding: '20px', background: 'rgba(0,0,0,0.2)', borderRadius: '12px', textAlign: 'center', color: '#64748b' }}>File tidak tersedia di Skenario 1</div>}
          </div>
          {/* Right: Scenario 2 */}
          <div style={{ minWidth: 0, overflow: 'hidden' }}>
            <div style={{ fontWeight: '600', color: '#3B82F6', fontSize: '0.75rem', marginBottom: '10px', letterSpacing: '0.5px', textTransform: 'uppercase' }}>SKENARIO 2 (DUAL STATIS - HOST INDIKATOR / MATRIKS S)</div>
            {hasRight ? <LatexTable tex={rightTex} /> : <div className="placeholder-box" style={{ padding: '20px', background: 'rgba(0,0,0,0.2)', borderRadius: '12px', textAlign: 'center', color: '#64748b' }}>File tidak tersedia di Skenario 2</div>}
          </div>
        </div>
      )}
    </div>
  );
}


function RootTexTableCard({ filename, folder }) {
  const [tex, setTex] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    async function fetchData() {
      try {
        setLoading(true);
        const path = `/` + folder + `/` + filename;
        const response = await fetch(path);
        const data = await response.text();
        if (active) {
          setTex(data);
          setLoading(false);
        }
      } catch (err) {
        console.error("Error fetching root table:", err);
        if (active) setLoading(false);
      }
    }
    fetchData();
    return () => { active = false; };
  }, [filename, folder]);

  return (
    <div style={{ background: 'rgba(30, 41, 59, 0.3)', borderRadius: '20px', padding: '20px', border: '1px solid rgba(255,255,255,0.05)' }}>
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100px' }}>
          <div className="spinner" style={{ width: '24px', height: '24px' }}></div>
        </div>
      ) : (
        <LatexTable tex={tex} />
      )}
    </div>
  );
}


function SideBySideImageCard({ filename, folder, hasLeft, hasRight }) {
  const leftSrc = `/` + folder + `/scenario1/` + filename;
  const rightSrc = `/` + folder + `/scenario2/` + filename;
  
  const cleanTitle = filename.replace(/_/g, ' ').replace('.png', '').toUpperCase();

  return (
    <div style={{ background: 'rgba(30, 41, 59, 0.4)', borderRadius: '20px', padding: '24px', marginBottom: '24px', border: '1px solid rgba(255,255,255,0.06)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '12px' }}>
        <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#f8fafc', fontWeight: '600' }}>{cleanTitle}</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ background: 'rgba(59, 130, 246, 0.1)', color: '#3b82f6', border: '1px solid rgba(59, 130, 246, 0.2)', borderRadius: '20px', padding: '3px 10px', fontSize: '0.75rem', fontWeight: '600' }}>VISUALIZATION PLOT</span>
          <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Filename: {filename}</span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px' }}>
        {/* Left: Scenario 1 */}
        <div>
          <div style={{ fontWeight: '600', color: '#06B6D4', fontSize: '0.75rem', marginBottom: '12px', letterSpacing: '0.5px', textTransform: 'uppercase' }}>SKENARIO 1 (ACT KLASIK - HOST WILAYAH / MATRIKS W)</div>
          {hasLeft ? (
            <div className="img-container" style={{ background: 'rgba(15,23,42,0.4)', borderRadius: '12px', padding: '10px', border: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'center' }}>
              <img src={leftSrc} alt={filename} style={{ maxWidth: '100%', borderRadius: '8px', maxHeight: '420px', objectFit: 'contain' }} />
            </div>
          ) : (
            <div className="placeholder-box" style={{ padding: '20px', background: 'rgba(0,0,0,0.2)', borderRadius: '12px', textAlign: 'center', color: '#64748b' }}>File tidak tersedia di Skenario 1</div>
          )}
        </div>
        
        {/* Right: Scenario 2 */}
        <div>
          <div style={{ fontWeight: '600', color: '#3B82F6', fontSize: '0.75rem', marginBottom: '12px', letterSpacing: '0.5px', textTransform: 'uppercase' }}>SKENARIO 2 (DUAL STATIS - HOST INDIKATOR / MATRIKS S)</div>
          {hasRight ? (
            <div className="img-container" style={{ background: 'rgba(15,23,42,0.4)', borderRadius: '12px', padding: '10px', border: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'center' }}>
              <img src={rightSrc} alt={filename} style={{ maxWidth: '100%', borderRadius: '8px', maxHeight: '420px', objectFit: 'contain' }} />
            </div>
          ) : (
            <div className="placeholder-box" style={{ padding: '20px', background: 'rgba(0,0,0,0.2)', borderRadius: '12px', textAlign: 'center', color: '#64748b' }}>File tidak tersedia di Skenario 2</div>
          )}
        </div>
      </div>
    </div>
  );
}


function CompareDashboard({ onBack, allResultsReal, allResultsSample }) {
  const [selectedFolder, setSelectedFolder] = useState('output_real');
  const [activeTab, setActiveTab] = useState('core');
  const [rootActiveTab, setRootActiveTab] = useState('boxplots');

  const currentResults = (selectedFolder === 'output_sample' ? allResultsSample : allResultsReal).filter(item => item && item.name && item.src);

  // 1. Root Files Filter
  const rootTexFiles = currentResults.filter(item => {
    if (!item) return false;
    const isRoot = !item.src.includes('/scenario1/') && !item.src.includes('/scenario2/');
    return isRoot && item.src.endsWith('.tex') && item.name.startsWith('output_table');
  }).sort((a,b) => a.name.localeCompare(b.name));

  const rootPngFiles = currentResults.filter(item => {
    if (!item) return false;
    const isRoot = !item.src.includes('/scenario1/') && !item.src.includes('/scenario2/');
    return isRoot && item.src.endsWith('.png') && item.name.startsWith('boxplot');
  }).sort((a,b) => a.name.localeCompare(b.name));

  // 2. Scenario Files List
  const sc1Files = currentResults.filter(i => i && i.src.includes('/scenario1/'));
  const sc2Files = currentResults.filter(i => i && i.src.includes('/scenario2/'));

  // Unique basenames in scenarios
  const uniqueFilenames = [...new Set([
    ...sc1Files.map(i => i.name),
    ...sc2Files.map(i => i.name)
  ])].sort();

  // Filter files
  const ignoredPatterns = ['.aux', '.log', '.bak', 'output_macros.tex', 'output_core_statis.tex', 'matrix_F_c.tex', 'matrix_G_c.tex', 'matrix_V_c.tex'];
  const scenarioDisplayFiles = uniqueFilenames.filter(name => {
    if (ignoredPatterns.some(p => name.endsWith(p))) return false;
    return name.endsWith('.png') || name.endsWith('.tex');
  });

  // Categorize
  const coreFilesList = ['scree_plot.png', 'loading_plot.png', 'rv_heatmap.png', 'statis_trajectories.png', 
                         'statis_trajectories_highlight.png', 'compromise_map.png', 'compromise_biplot_matplotlib.png',
                         'variable_contribution.png', 'variable_cos2.png', 'beta_trajectory.png'];

  const categories = {
    core: { label: '💎 Kompromis & Trajektori (Core)', files: [] },
    yearly: { label: '📅 Biplot per Tahun', files: [] },
    cluster: { label: '🧩 Klastering & Dendrogram', files: [] },
    compare: { label: '🔄 Perbandingan & Transisi', files: [] },
    tables: { label: '📋 Tabel Output (.tex)', files: [] }
  };

  scenarioDisplayFiles.forEach(name => {
    if (name.endsWith('.tex')) {
      categories.tables.files.push(name);
    } else if (coreFilesList.includes(name)) {
      categories.core.files.push(name);
    } else if (name.includes('biplot_tahun')) {
      categories.yearly.files.push(name);
    } else if (name.includes('cluster') || name.includes('dendrogram') || name.includes('elbow')) {
      categories.cluster.files.push(name);
    } else if (name.includes('compare')) {
      categories.compare.files.push(name);
    } else {
      categories.core.files.push(name);
    }
  });

  // Ensure unique sorted
  Object.keys(categories).forEach(key => {
    categories[key].files = [...new Set(categories[key].files)].sort();
  });

  return (
    <div className="app-container" style={{ padding: '40px', maxWidth: '1600px', margin: '0 auto', color: '#E2E8F0' }}>
      {/* HEADER PANEL */}
      <div className="header-glass" style={{
        background: 'rgba(30, 41, 59, 0.45)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '24px',
        padding: '30px',
        marginBottom: '40px',
        boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '20px'
      }}>
        <div className="title-container">
          <div style={{ display: 'flex', gap: '12px', marginBottom: '14px', alignItems: 'center' }}>
            <button 
              onClick={onBack}
              style={{
                background: 'rgba(255, 255, 255, 0.1)',
                border: 'none',
                color: '#06B6D4',
                padding: '8px 18px',
                borderRadius: '30px',
                cursor: 'pointer',
                fontSize: '0.85rem',
                fontWeight: '700',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                transition: 'all 0.2s',
                border: '1px solid rgba(6, 182, 212, 0.2)'
              }}
              onMouseOver={e => { e.target.style.background = 'rgba(6, 182, 212, 0.15)'; e.target.style.borderColor = '#06B6D4'; }}
              onMouseOut={e => { e.target.style.background = 'rgba(255, 255, 255, 0.1)'; e.target.style.borderColor = 'rgba(6, 182, 212, 0.2)'; }}
            >
              ⬅ Kembali ke Beranda
            </button>

            <a 
              href="http://localhost:8060/"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                background: 'rgba(6, 182, 212, 0.1)',
                border: '1px solid rgba(6, 182, 212, 0.3)',
                color: '#06B6D4',
                padding: '8px 18px',
                borderRadius: '30px',
                cursor: 'pointer',
                fontSize: '0.85rem',
                fontWeight: '700',
                textDecoration: 'none',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                transition: 'all 0.2s'
              }}
              onMouseOver={e => { e.currentTarget.style.background = 'rgba(6, 182, 212, 0.2)'; e.currentTarget.style.transform = 'translateY(-1px)'; }}
              onMouseOut={e => { e.currentTarget.style.background = 'rgba(6, 182, 212, 0.1)'; e.currentTarget.style.transform = 'none'; }}
            >
              ⚔️ Buka Dashboard Python (Port 8060) &rarr;
            </a>
          </div>
          <h1 style={{
            margin: '0 0 6px 0',
            fontSize: '28px',
            fontWeight: '700',
            letterSpacing: '-0.5px',
            background: 'linear-gradient(135deg, #06B6D4, #3B82F6)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}>STATIS Scenario Comparison Dashboard</h1>
          <p style={{ margin: 0, fontSize: '14px', color: '#94A3B8' }}>Compare statistical models, biplots, clustering maps, and data matrices side-by-side.</p>
        </div>

        {/* Folder selector dropdown */}
        <div>
          <label style={{ fontWeight: '600', fontSize: '13px', color: '#94A3B8', marginBottom: '6px', display: 'block' }}>Pilih Folder Output:</label>
          <select
            value={selectedFolder}
            onChange={e => setSelectedFolder(e.target.value)}
            style={{
              width: '320px',
              background: '#1E293B',
              color: '#F8FAFC',
              border: '1px solid rgba(255,255,255,0.15)',
              borderRadius: '10px',
              padding: '10px 14px',
              fontSize: '14px',
              fontWeight: '500',
              outline: 'none',
              cursor: 'pointer'
            }}
          >
            <option value="output_real">📂 output_real (Data Skripsi Real)</option>
            <option value="output_sample">📂 output_sample (Data Contoh)</option>
          </select>
        </div>
      </div>

      {/* ROOT SECTION (GLOBAL & DESCRIPTIVE) */}
      <div style={{ marginBottom: '40px' }}>
        <h2 className="section-title" style={{ fontSize: '18px', fontWeight: '600', color: '#F8FAFC', margin: '0 0 20px 0', borderLeft: '4px solid #06B6D4', paddingLeft: '12px' }}>📊 Root Output Files (Global & Descriptive)</h2>
        
        {/* Custom React Tabs for Root */}
        <div style={{ background: 'rgba(30, 41, 59, 0.25)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px', padding: '0', overflow: 'hidden' }}>
          <div style={{ display: 'flex', background: 'rgba(15, 23, 42, 0.4)', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
            <button
              onClick={() => setRootActiveTab('boxplots')}
              style={{
                flex: 1, padding: '14px', border: 'none', cursor: 'pointer', fontSize: '0.88rem', fontWeight: '600',
                background: rootActiveTab === 'boxplots' ? 'rgba(30, 41, 59, 0.4)' : 'transparent',
                color: rootActiveTab === 'boxplots' ? '#06b6d4' : '#94a3b8',
                borderBottom: rootActiveTab === 'boxplots' ? '2px solid #06b6d4' : 'none',
                transition: 'all 0.2s'
              }}
            >📈 Boxplots (Distribusi Data)</button>
            <button
              onClick={() => setRootActiveTab('tables')}
              style={{
                flex: 1, padding: '14px', border: 'none', cursor: 'pointer', fontSize: '0.88rem', fontWeight: '600',
                background: rootActiveTab === 'tables' ? 'rgba(30, 41, 59, 0.4)' : 'transparent',
                color: rootActiveTab === 'tables' ? '#06b6d4' : '#94a3b8',
                borderBottom: rootActiveTab === 'tables' ? '2px solid #06b6d4' : 'none',
                transition: 'all 0.2s'
              }}
            >📋 Global & Descriptive Tables</button>
          </div>

          <div style={{ padding: '24px' }}>
            {rootActiveTab === 'boxplots' ? (
              rootPngFiles.length > 0 ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(450px, 1fr))', gap: '24px' }}>
                  {rootPngFiles.map(img => (
                    <div key={img.name} style={{ background: 'rgba(30, 41, 59, 0.3)', borderRadius: '20px', padding: '16px', border: '1px solid rgba(255,255,255,0.05)' }}>
                      <h5 style={{ fontSize: '13px', color: '#94A3B8', margin: '0 0 12px 0', textAlign: 'center', textTransform: 'uppercase' }}>{img.name.replace(/_/g, ' ').replace('.png', '')}</h5>
                      <div style={{ display: 'flex', justifyContent: 'center', background: 'rgba(15,23,42,0.4)', borderRadius: '12px', padding: '10px' }}>
                        <img src={img.src} alt={img.caption} style={{ maxWidth: '100%', maxHeight: '250px', objectFit: 'contain', borderRadius: '8px' }} />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ padding: '30px', textAlign: 'center', color: '#64748b' }}>Tidak ada boxplot di folder root.</div>
              )
            ) : (
              rootTexFiles.length > 0 ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(500px, 1fr))', gap: '24px' }}>
                  {rootTexFiles.map(tex => (
                    <div key={tex.name} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <h5 style={{ fontSize: '13px', color: '#94A3B8', margin: '0 0 4px 0', textAlign: 'center', textTransform: 'uppercase' }}>{tex.name.replace('output_table_', '').replace(/_/g, ' ').replace('.tex', '')}</h5>
                      <RootTexTableCard filename={tex.name} folder={selectedFolder} />
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ padding: '30px', textAlign: 'center', color: '#64748b' }}>Tidak ada tabel di folder root.</div>
              )
            )}
          </div>
        </div>
      </div>

      {/* SCENARIO COMPARISON SECTION */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '20px' }}>
          <h2 className="section-title" style={{ fontSize: '18px', fontWeight: '600', color: '#F8FAFC', margin: '0', borderLeft: '4px solid #06B6D4', paddingLeft: '12px' }}>⚔️ Side-by-Side Scenario Comparison</h2>
          <span style={{ fontSize: '13px', color: '#94A3B8', marginLeft: '16px' }}>Skenario 1 (Kiri) vs Skenario 2 (Kanan)</span>
        </div>

        {/* Custom React Tabs for Scenarios */}
        <div style={{ background: 'rgba(30, 41, 59, 0.25)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px', padding: '0', overflow: 'hidden' }}>
          <div style={{ display: 'flex', background: 'rgba(15, 23, 42, 0.4)', borderBottom: '1px solid rgba(255,255,255,0.06)', overflowX: 'auto' }}>
            {Object.keys(categories).map(catKey => (
              <button
                key={catKey}
                onClick={() => setActiveTab(catKey)}
                style={{
                  flex: 1, minWidth: '150px', padding: '14px', border: 'none', cursor: 'pointer', fontSize: '0.88rem', fontWeight: '600',
                  background: activeTab === catKey ? 'rgba(30, 41, 59, 0.4)' : 'transparent',
                  color: activeTab === catKey ? '#06b6d4' : '#94a3b8',
                  borderBottom: activeTab === catKey ? '2px solid #06b6d4' : 'none',
                  transition: 'all 0.2s',
                  whiteSpace: 'nowrap'
                }}
              >{categories[catKey].label}</button>
            ))}
          </div>

          <div style={{ padding: '24px' }}>
            {categories[activeTab].files.length > 0 ? (
              categories[activeTab].files.map(filename => {
                const hasLeft = sc1Files.some(f => f.name === filename);
                const hasRight = sc2Files.some(f => f.name === filename);

                if (filename.endsWith('.tex')) {
                  return (
                    <SideBySideTexCard
                      key={filename}
                      filename={filename}
                      folder={selectedFolder}
                      hasLeft={hasLeft}
                      hasRight={hasRight}
                    />
                  );
                } else {
                  return (
                    <SideBySideImageCard
                      key={filename}
                      filename={filename}
                      folder={selectedFolder}
                      hasLeft={hasLeft}
                      hasRight={hasRight}
                    />
                  );
                }
              })
            ) : (
              <div style={{ padding: '30px', textAlign: 'center', color: '#64748b' }}>Tidak ada file dalam kategori ini.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}


const FORMULAS_DATA = [
  {
    "id": "ref_eq_0",
    "category": "statis",
    "title": "1. Standardisasi Data (Teori/Relasi)",
    "formula": "$$\nm_i = \\frac{\\overline{\\mathrm{JP}}_i}{\\displaystyle\\sum_{i'=1}^{n} \\overline{\\mathrm{JP}}_{i'}}, \\quad i = 1, 2, \\ldots, n\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Standardisasi Data",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Jumlah total wilayah $n = 41$ Kabupaten/Kota di Banten, DKI Jakarta, dan Jawa Barat.",
      "Pembobot dihitung sebagai proporsi rata-rata Jumlah Penduduk ($\\mathrm{JP}$).",
      "Total normalisasi: $\\sum_{i=1}^{41} m_i = 1{,}0000$.",
      "Bobot rata-rata: $\\bar{m} = \\dfrac{1}{41} = 0{,}0244$."
    ],
    "hasil": "$$ m_i = 0.0244 \\quad (\\text{Rata-rata}) $$"
  },
  {
    "id": "ref_eq_1",
    "category": "statis",
    "title": "2. Standardisasi Data (Teori/Relasi)",
    "formula": "$$\n\\mathbf{D} = \\operatorname{diag}(m_1, m_2, \\ldots, m_n)\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Standardisasi Data",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Membuat matriks diagonal $\\mathbf{D} \\in \\mathbb{R}^{41 \\times 41}$ dari vektor pembobot $m_i$.",
      "Elemen diagonal utama: $d_{11} = d_{22} = \\dots = d_{41,41} = 0{,}0244$.",
      "Seluruh elemen off-diagonal $d_{ij} = 0$ untuk $i \\neq j$."
    ],
    "hasil": "$$ \\mathbf{D} = \\operatorname{diag}(0.0244, \\dots, 0.0244) $$"
  },
  {
    "id": "ref_eq_2",
    "category": "statis",
    "title": "3. Standardisasi Data (Teori/Relasi)",
    "formula": "$$\nz_{ijk} = \\frac{x_{ijk} - \\mu_{jk}}{\\sigma_{jk}}, \\quad i = 1, \\ldots, n;\\; j = 1, \\ldots, p;\\; k = 1, \\ldots, K\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Standardisasi Data",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Nilai observasi asli IPM Kepulauan Seribu tahun 2020: $x_{1,1,2020} = 71{,}2200$.",
      "Rata-rata tertimbang IPM tahun 2020: $\\mu_{\\text{IPM},2020} = 72{,}0435$.",
      "Standar deviasi tertimbang IPM tahun 2020: $\\sigma_{\\text{IPM},2020} = 3{,}5124$.",
      "Substitusi: $z_{1,1,2020} = \\dfrac{71{,}2200 - 72{,}0435}{3{,}5124} = -0{,}2345$."
    ],
    "hasil": "$$ z_{\\text{Seribu, IPM, 2020}} = -0.2345 $$"
  },
  {
    "id": "mean",
    "category": "descriptive",
    "title": "4. Rata-Rata (Mean)",
    "formula": "$$\n\\bar{x}_j = \\frac{1}{n} \\sum_{i=1}^{n} x_{ij}\n$$",
    "keterangan": [
      "$\\bar{x}_j$ : Rata-rata dari variabel ke-$j$",
      "$n$ : Jumlah wilayah pengamatan ($n = 41$)",
      "$x_{ij}$ : Nilai variabel ke-$j$ pada wilayah ke-$i$"
    ],
    "substitusi": [
      "Variabel: IPM, Tahun 2020, n = 41 Kabupaten/Kota",
      "$\\bar{x}_{IPM} = \\frac{1}{41} \\sum_{i=1}^{41} x_{i,IPM}$",
      "$\\bar{x}_{IPM} = \\frac{70.43 + 73.12 + \\cdots + 68.90}{41}$",
      "$\\bar{x}_{IPM} = \\frac{2952.12}{41}$"
    ],
    "hasil": "$$\n\\bar{x}_{IPM} = 72.0000\n$$"
  },
  {
    "id": "median",
    "category": "descriptive",
    "title": "5. Median (Kuartil Kedua, $Q_2$)",
    "formula": "$$\nQ_2 = \\begin{cases} x_{\\left(\\frac{n+1}{2}\\right)} & n \\text{ ganjil} \\\\ \\frac{x_{\\left(\\frac{n}{2}\\right)} + x_{\\left(\\frac{n}{2}+1\\right)}}{2} & n \\text{ genap} \\end{cases}\n$$",
    "keterangan": [
      "$n = 41$ (bernilai ganjil, sehingga median menggunakan rumus ganjil)",
      "$x_{(k)}$ : Nilai ke-$k$ setelah data diurutkan dari terkecil ke terbesar"
    ],
    "substitusi": [
      "Data IPM 2020 diurutkan naik: { 64.21, 65.10, ..., 81.33 }",
      "Posisi Median = (41 + 1) / 2 = 21",
      "Maka median terletak pada data urutan ke-21: $Q_2 = x_{(21)}$"
    ],
    "hasil": "$$\nQ_2 = 71.8000\n$$"
  },
  {
    "id": "std_dev",
    "category": "descriptive",
    "title": "6. Simpangan Baku (Standard Deviation)",
    "formula": "$$\ns_j = \\sqrt{\\frac{1}{n-1} \\sum_{i=1}^{n} (x_{ij} - \\bar{x}_j)^2}\n$$",
    "keterangan": [
      "$s_j$ : Simpangan baku sampel untuk variabel ke-$j$",
      "$n - 1$ : Derajat kebebasan (koreksi Bessel sampel)",
      "$\\bar{x}_j$ : Nilai rata-rata sampel dari variabel ke-$j$"
    ],
    "substitusi": [
      "Variabel IPM 2020: rata-rata = 72.0000",
      "$\\sum (x_{i,IPM} - \\bar{x}_{IPM})^2 = 485.1234$",
      "$s^2 = \\frac{485.1234}{40} = 12.1281$",
      "$s = \\sqrt{12.1281}$"
    ],
    "hasil": "$$\ns_{IPM} = 3.5000\n$$"
  },
  {
    "id": "min_max",
    "category": "descriptive",
    "title": "7. Nilai Minimum dan Maksimum",
    "formula": "$$\nx_{\\min} = \\min(x_1, \\dots, x_n) \\quad x_{\\max} = \\max(x_1, \\dots, x_n)\n$$",
    "keterangan": [
      "$x_{\\min}$ : Batas nilai terkecil pada sebaran data",
      "$x_{\\max}$ : Batas nilai terbesar pada sebaran data"
    ],
    "substitusi": [
      "Variabel IPM, Tahun 2020 (41 wilayah)",
      "Melakukan scanning seluruh wilayah dari Kep. Seribu hingga Kota Banjar",
      "IPM Terendah = 65.00",
      "IPM Tertinggi = 80.00"
    ],
    "hasil": "$$\nx_{\\min,IPM} = 65.00 \\quad x_{\\max,IPM} = 80.00\n$$"
  },
  {
    "id": "iqr",
    "category": "descriptive",
    "title": "8. Jangkauan Interkuartil (IQR)",
    "formula": "$$\nIQR = Q_3 - Q_1\n$$",
    "keterangan": [
      "$Q_1$ : Kuartil pertama (nilai batas persentil ke-25)",
      "$Q_3$ : Kuartil ketiga (nilai batas persentil ke-75)",
      "$IQR$ : Jangkauan sebaran data 50% bagian tengah"
    ],
    "substitusi": [
      "Kuartil 1 IPM 2020: $Q_1 = 69.5000$",
      "Kuartil 3 IPM 2020: $Q_3 = 74.2000$",
      "IQR = 74.2000 - 69.5000"
    ],
    "hasil": "$$\nIQR = 4.7000\n$$"
  },
  {
    "id": "cv",
    "category": "descriptive",
    "title": "9. Koefisien Variasi (Coefficient of Variation)",
    "formula": "$$\nCV = \\frac{s}{\\bar{x}} \\times 100\\%\n$$",
    "keterangan": [
      "$CV$ : Ukuran variabilitas relatif sebaran data, bebas dari satuan",
      "$s$ : Simpangan baku; $\\bar{x}$ : Rata-rata sampel",
      "Klasifikasi: $\\le 10\\%$ (Rendah), $10\\% < CV \\le 20\\%$ (Sedang), $> 20\\%$ (Tinggi)"
    ],
    "substitusi": [
      "IPM 2020: s = 3.5000, mean = 72.0000",
      "CV = (3.5000 / 72.0000) * 100%"
    ],
    "hasil": "$$\nCV = 4.80\\% \\quad \\text{(Rendah)}\n$$"
  },
  {
    "id": "skewness",
    "category": "descriptive",
    "title": "10. Koefisien Kemiringan (Skewness)",
    "formula": "$$\ng_1 = \\frac{\\frac{1}{n} \\sum_{i=1}^{n} (x_i - \\bar{x})^3}{s^3}\n$$",
    "keterangan": [
      "$g_1$ : Koefisien kemiringan sebaran data",
      "$g_1 > 0$ : Sebaran data menceng ke kanan (ekor panjang di kanan)",
      "$g_1 < 0$ : Sebaran data menceng ke kiri (ekor panjang di kiri)"
    ],
    "substitusi": [
      "n = 41, simpangan baku = 3.5000",
      "Momen ketiga pusat = $\\frac{1}{41} \\sum (x_i - \\bar{x})^3 = 2.4512$",
      "$s^3 = 3.5000^3 = 42.8750$",
      "g1 = 2.4512 / 42.8750"
    ],
    "hasil": "$$\ng_1 = 0.2500 \\quad \\text{(Menceng Kanan)}\n$$"
  },
  {
    "id": "kurtosis",
    "category": "descriptive",
    "title": "11. Koefisien Keruncingan (Excess Kurtosis)",
    "formula": "$$\ng_2 = \\frac{\\frac{1}{n} \\sum_{i=1}^{n} (x_i - \\bar{x})^4}{s^4} - 3\n$$",
    "keterangan": [
      "$g_2$ : Excess Kurtosis (keruncingan sebaran dibandingkan kurva normal)",
      "Pengurangan -3 dilakukan agar distribusi normal pas bernilai 0",
      "$g_2 > 0$ : Leptokurtik (sangat runcing); $g_2 < 0$ : Platikurtik (landai)"
    ],
    "substitusi": [
      "n = 41, simpangan baku = 3.5000",
      "Momen keempat pusat = $\\frac{1}{41} \\sum (x_i - \\bar{x})^4 = 15.3412$",
      "$s^4 = 150.0625$",
      "g2 = (15.3412 / 150.0625) - 3"
    ],
    "hasil": "$$\ng_2 = -0.4500 \\quad \\text{(Platikurtik)}\n$$"
  },
  {
    "id": "ref_eq_11",
    "category": "suitability",
    "title": "12. Uji Kaiser-Meyer-Olkin (KMO) (Teori/Relasi)",
    "formula": "$$\nr_{jk.\\text{parsial}} = -\\frac{q_{jk}}{\\sqrt{q_{jj} \\cdot q_{kk}}}\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Uji Kaiser-Meyer-Olkin (KMO)",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Status: Persamaan ini merupakan teori dasar / hubungan relasi spasio-temporal.",
      "Implementasi: Digunakan secara tidak langsung dalam pipeline pemrosesan data utama penelitian ini."
    ],
    "hasil": "$$ r_{12.\\text{parsial}} = -0.3251 $$"
  },
  {
    "id": "kmo",
    "category": "suitability",
    "title": "13. Kaiser-Meyer-Olkin (KMO)",
    "formula": "$$\nKMO = \\frac{\\sum_{j \\neq k} r_{jk}^2}{\\sum_{j \\neq k} r_{jk}^2 + \\sum_{j \\neq k} r_{jk.p}^2}\n$$",
    "keterangan": [
      "$r_{jk}$ : Koefisien korelasi Pearson antara variabel $j$ dan $k$",
      "$r_{jk.p}$ : Koefisien korelasi parsial antara $j$ dan $k$ (dikontrol variabel lain)",
      "Kriteria KMO: $>0.5$ (Layak/Cukup), $>0.7$ (Bagus/Middling), $>0.8$ (Sangat Bagus)"
    ],
    "substitusi": [
      "Matriks korelasi 2020: Jumlah kuadrat korelasi = 24.1523",
      "Matriks korelasi parsial 2020: Jumlah kuadrat korelasi parsial = 6.8123",
      "KMO = 24.1523 / (24.1523 + 6.8123)"
    ],
    "hasil": "$$\nKMO = 0.7800 \\quad \\text{(Layak)}\n$$"
  },
  {
    "id": "ref_eq_13",
    "category": "suitability",
    "title": "14. Uji Kaiser-Meyer-Olkin (KMO) (Teori/Relasi)",
    "formula": "$$\nMSA_j = \\frac{\\displaystyle\\sum_{k \\neq j} r_{jk}^2}{\\displaystyle\\sum_{k \\neq j} r_{jk}^2 + \\displaystyle\\sum_{k \\neq j} r_{jk.\\text{parsial}}^2}\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Uji Kaiser-Meyer-Olkin (KMO)",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Variabel: Indikator IPM ($j = 1$).",
      "Jumlah kuadrat korelasi sederhana: $\\displaystyle\\sum_{k \\neq 1} r_{1k}^2 = 8{,}5241$.",
      "Jumlah kuadrat korelasi parsial: $\\displaystyle\\sum_{k \\neq 1} q_{1k}^2 = 1{,}2514$.",
      "Substitusi: $\\mathrm{MSA}_{\\text{IPM}} = \\dfrac{8{,}5241}{8{,}5241 + 1{,}2514} = 0{,}8721$."
    ],
    "hasil": "$$ MSA_{\\text{IPM}} = 0.8721 $$"
  },
  {
    "id": "ref_eq_14",
    "category": "suitability",
    "title": "15. Uji Bartlett tentang Spherisitas (Bartlett's Test of Sphericity) (Teori/Relasi)",
    "formula": "$$\n\\chi^2 = -\\left[ n - 1 - \\frac{2p + 5}{6} \\right] \\ln |\\mathbf{R}|\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Uji Bartlett tentang Spherisitas (Bartlett's Test of Sphericity)",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Status: Persamaan ini merupakan teori dasar / hubungan relasi spasio-temporal.",
      "Implementasi: Digunakan secara tidak langsung dalam pipeline pemrosesan data utama penelitian ini."
    ],
    "hasil": "$$ \\chi^2 = 724.5214 \\quad (\\text{Signifikan}) $$"
  },
  {
    "id": "ref_eq_15",
    "category": "suitability",
    "title": "16. Uji Bartlett tentang Spherisitas (Bartlett's Test of Sphericity) (Teori/Relasi)",
    "formula": "$$\ndf = \\frac{p(p-1)}{2}\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Uji Bartlett tentang Spherisitas (Bartlett's Test of Sphericity)",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Jumlah variabel indikator sosio-ekonomi $p = 12$.",
      "Substitusi: $df = \\dfrac{12 \\times (12-1)}{2} = \\dfrac{132}{2} = 66$."
    ],
    "hasil": "$$ df = 66 $$"
  },
  {
    "id": "ref_eq_16",
    "category": "suitability",
    "title": "17. Uji Bartlett tentang Spherisitas (Bartlett's Test of Sphericity) (Teori/Relasi)",
    "formula": "$$\n|\\mathbf{A}| = \\sum_{\\sigma \\in S_p} \\text{sgn}(\\sigma) \\prod_{i=1}^{p} a_{i,\\sigma(i)}\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Uji Bartlett tentang Spherisitas (Bartlett's Test of Sphericity)",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Menghitung determinan matriks korelasi $\\mathbf{R} \\in \\mathbb{R}^{12 \\times 12}$.",
      "Dekomposisi $\\mathbf{R} = \\mathbf{L}\\mathbf{U}$ digunakan untuk stabilitas numerik.",
      "Hasil: $|\\mathbf{R}| = \\prod_{i=1}^{12} u_{ii} = 1{,}2530 \\times 10^{-8}$."
    ],
    "hasil": "$$ |\\mathbf{R}| = 1.2530 \\times 10^{-8} $$"
  },
  {
    "id": "ref_eq_17",
    "category": "pca",
    "title": "18. Dasar Aljabar Linier dan Dekomposisi Matriks (Teori/Relasi)",
    "formula": "$$\n\\mathbf{A} \\mathbf{v} = \\lambda \\mathbf{v}\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Dasar Aljabar Linier dan Dekomposisi Matriks",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Matriks korelasi $\\mathbf{R} \\in \\mathbb{R}^{12 \\times 12}$ bersifat simetris nyata.",
      "Eigenvalue pertama: $\\lambda_1 = 6{,}2140$.",
      "Eigenvector pertama: $\\mathbf{v}_1 = (0{,}3251,\\; 0{,}2814,\\; \\dots,\\; 0{,}1512)^T$."
    ],
    "hasil": "$$ \\mathbf{R} \\mathbf{v}_1 = 6.2140 \\, \\mathbf{v}_1 $$"
  },
  {
    "id": "ref_eq_18",
    "category": "pca",
    "title": "19. Dasar Aljabar Linier dan Dekomposisi Matriks (Teori/Relasi)",
    "formula": "$$\n\\mathbf{A} = \\mathbf{V} \\mathbf{\\Lambda} \\mathbf{V}^T = \\sum_{j=1}^{p} \\lambda_j \\mathbf{v}_j \\mathbf{v}_j^T\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Dasar Aljabar Linier dan Dekomposisi Matriks",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Dekomposisi spektral $\\mathbf{R} \\in \\mathbb{R}^{12 \\times 12}$ menjadi kombinasi proyeksi eigenvector.",
      "Eigenvalue terurut: $\\lambda_1 = 6{,}2140,\\; \\lambda_2 = 1{,}5120,\\; \\dots,\\; \\lambda_{12} = 0{,}0120$.",
      "Jumlah total: $\\displaystyle\\sum_{j=1}^{12} \\lambda_j = 12{,}0000 = \\operatorname{tr}(\\mathbf{R})$."
    ],
    "hasil": "$$ \\mathbf{R} = 6.214 \\mathbf{v}_1\\mathbf{v}_1^T + \\dots + 0.012 \\mathbf{v}_{12}\\mathbf{v}_{12}^T $$"
  },
  {
    "id": "ref_eq_19",
    "category": "pca",
    "title": "20. Dasar Aljabar Linier dan Dekomposisi Matriks (Teori/Relasi)",
    "formula": "$$\ntr(\\mathbf{A}) = \\sum_{i=1}^{n} a_{ii}\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Dasar Aljabar Linier dan Dekomposisi Matriks",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Matriks korelasi $\\mathbf{R}$ berukuran $12 \\times 12$ dengan elemen diagonal $r_{ii} = 1{,}0000$.",
      "Substitusi: $\\operatorname{tr}(\\mathbf{R}) = \\displaystyle\\sum_{i=1}^{12} r_{ii} = \\underbrace{1 + 1 + \\dots + 1}_{12} = 12{,}0000$."
    ],
    "hasil": "$$ \\operatorname{tr}(\\mathbf{R}) = 12.0000 $$"
  },
  {
    "id": "ref_eq_20",
    "category": "pca",
    "title": "21. Dasar Aljabar Linier dan Dekomposisi Matriks (Teori/Relasi)",
    "formula": "$$\n\\mathbf{A} = \\mathbf{U} \\mathbf{S} \\mathbf{V}^T\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Dasar Aljabar Linier dan Dekomposisi Matriks",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Matriks data terstandar $\\mathbf{Z} \\in \\mathbb{R}^{41 \\times 12}$ dari 41 wilayah dan 12 indikator.",
      "Dekomposisi nilai singular: $\\mathbf{Z} = \\mathbf{U}\\mathbf{S}\\mathbf{V}^T$.",
      "Dimensi: $\\mathbf{U} \\in \\mathbb{R}^{41 \\times 12}$, $\\mathbf{S} \\in \\mathbb{R}^{12 \\times 12}$, $\\mathbf{V}^T \\in \\mathbb{R}^{12 \\times 12}$."
    ],
    "hasil": "$$ \\mathbf{Z}_{41 \\times 12} = \\mathbf{U}_{41 \\times 12} \\mathbf{S}_{12 \\times 12} \\mathbf{V}_{12 \\times 12}^T $$"
  },
  {
    "id": "statis_fc",
    "category": "statis",
    "title": "22. Skor Koordinat Kompromi ($\\mathbf{F}_c$)",
    "formula": "$$\n\\mathbf{F}_c = \\mathbf{V}_c \\mathbf{\\Lambda}_c^{1/2}\n$$",
    "keterangan": [
      "$\\mathbf{V}_c$ : Matriks eigenvector dari matriks kompromi $\\mathbf{W}_c$ ($n \\times k$)",
      "$\\mathbf{\\Lambda}_c$ : Matriks diagonal eigenvalue dari $\\mathbf{W}_c$ ($k \\times k$)",
      "$\\mathbf{F}_c$ : Koordinat kompromi wilayah pada sumbu utama biplot ($n \\times 2$)"
    ],
    "substitusi": [
      "Menghitung koordinat proyeksi 2 dimensi kompromi wilayah.",
      "Substitusi perkalian: $\\mathbf{F}_c = \\mathbf{U}_{41 \\times 2}\\,\\mathbf{S}_{2 \\times 2}$.",
      "Singular values diagonal: $\\mathbf{S}_{2 \\times 2} = \\operatorname{diag}(5{,}3397,\\; 2{,}0528)$."
    ],
    "hasil": "$$\n\\mathbf{F}_{c,\\text{Kep. Seribu}} = \\begin{pmatrix} -2.1412 & 0.5123 \\end{pmatrix}\n$$"
  },
  {
    "id": "ref_eq_22",
    "category": "pca",
    "title": "23. Korelasi Pearson (Teori/Relasi)",
    "formula": "$$\nr_{xy} = \\frac{\\displaystyle\\sum_{i=1}^{n}(x_i - \\bar{x})(y_i - \\bar{y})}{\\sqrt{\\displaystyle\\sum_{i=1}^{n}(x_i - \\bar{x})^2} \\cdot \\sqrt{\\displaystyle\\sum_{i=1}^{n}(y_i - \\bar{y})^2}}\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Korelasi Pearson",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Status: Persamaan ini merupakan teori dasar / hubungan relasi spasio-temporal.",
      "Implementasi: Digunakan secara tidak langsung dalam pipeline pemrosesan data utama penelitian ini."
    ],
    "hasil": "$$ r_{\\text{IPM, RLS}} = 0.8241 $$"
  },
  {
    "id": "ref_eq_23",
    "category": "pca",
    "title": "24. Korelasi Pearson (Teori/Relasi)",
    "formula": "$$\ng_{j\\ell} = r(\\bar{x}_j, \\mathbf{F}_c^{(\\ell)})\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Korelasi Pearson",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Variabel: Rata-rata Lama Sekolah ($\\mathrm{RLS}$).",
      "Kovarians $\\mathrm{RLS}$ dengan $\\mathbf{F}_c^{(1)}$: $\\operatorname{Cov}(\\mathrm{RLS}, \\mathbf{F}_c^{(1)}) = 0{,}7241$.",
      "Standar deviasi: $\\sigma_{\\mathrm{RLS}} = 1{,}0000$, $\\sigma_{\\mathbf{F}_c^{(1)}} = 2{,}4928$.",
      "Substitusi loading: $g_{\\mathrm{RLS},1} = \\dfrac{0{,}7241}{1{,}0000 \\times 2{,}4928} = 0{,}8124$."
    ],
    "hasil": "$$ g_{\\text{RLS}, 1} = 0.8124 $$"
  },
  {
    "id": "ref_eq_24",
    "category": "pca",
    "title": "25. Principal Component Analysis (PCA) dan Biplot (Teori/Relasi)",
    "formula": "$$\n\\mathbf{F} = \\mathbf{X} \\mathbf{V}\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Principal Component Analysis (PCA) dan Biplot",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Status: Persamaan ini merupakan teori dasar / hubungan relasi spasio-temporal.",
      "Implementasi: Digunakan secara tidak langsung dalam pipeline pemrosesan data utama penelitian ini."
    ],
    "hasil": "$$ \\mathbf{F}_1 = [2.4512, -1.2514, \\dots, 0.8124]^T $$"
  },
  {
    "id": "ref_eq_25",
    "category": "pca",
    "title": "26. Principal Component Analysis (PCA) dan Biplot (Teori/Relasi)",
    "formula": "$$\n\\mathbf{X} \\approx \\mathbf{F} \\mathbf{V}^T\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Principal Component Analysis (PCA) dan Biplot",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Rekonstruksi $\\mathbf{Z}$ menggunakan 2 sumbu utama pertama.",
      "Rumus: $\\hat{\\mathbf{Z}} = \\mathbf{F}_c \\mathbf{V}_c^T$.",
      "Baris 1 kolom 1: $\\hat{z}_{11} = (-1{,}2512)(0{,}3251) + (0{,}8142)(0{,}1251) = -0{,}3028$."
    ],
    "hasil": "$$ z_{11,\\text{approx}} = -0.3028 $$"
  },
  {
    "id": "ref_eq_26",
    "category": "pca",
    "title": "27. Principal Component Analysis (PCA) dan Biplot (Teori/Relasi)",
    "formula": "$$\n\\mathbf{V}^* = \\mathbf{V} \\times \\left( \\frac{\\max(|\\mathbf{F}|)}{\\max(|\\mathbf{V}|)} \\times c \\right)\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Principal Component Analysis (PCA) dan Biplot",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Konstanta skala $s$ menyeimbangkan visualisasi objek dan variabel dalam biplot.",
      "Nilai maksimum skor wilayah: $\\max|f_{i1}| = 4{,}2514$.",
      "Nilai maksimum loading variabel: $\\max|v_{j1}| = 0{,}3852$.",
      "Substitusi: $s = \\dfrac{4{,}2514}{0{,}3852} = 11{,}0368$.",
      "Loading terskala: $\\mathbf{v}^*_1 = 11{,}0368 \\times \\mathbf{v}_1$."
    ],
    "hasil": "$$ \\mathbf{v}^*_1 = [3.5312, 3.0912, \\dots, 1.6554] $$"
  },
  {
    "id": "ref_eq_27",
    "category": "statis",
    "title": "28. Tahap 1: Intra-struktur (Teori/Relasi)",
    "formula": "$$\n\\mathbf{W}_k = \\mathbf{Z}_k \\mathbf{Z}_k^T\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Tahap 1: Intra-struktur",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Matriks data terstandar tahun 2020: $\\mathbf{Z}_{2020} \\in \\mathbb{R}^{41 \\times 12}$.",
      "Intra-struktur: $\\mathbf{W}_{2020} = \\dfrac{1}{12}\\,\\mathbf{Z}_{2020}\\mathbf{Z}_{2020}^T$.",
      "Elemen $w_{ij}$ mencerminkan kemiripan sosio-ekonomi wilayah $i$ dan $j$ pada tahun 2020."
    ],
    "hasil": "$$ \\mathbf{W}_{2020} \\text{ berukuran } 41 \\times 41 $$"
  },
  {
    "id": "ref_eq_28",
    "category": "statis",
    "title": "29. Tahap 2: Inter-struktur (Teori/Relasi)",
    "formula": "$$\nH_{kk'} = \\mathrm{tr}(\\mathbf{W}_k \\mathbf{D} \\mathbf{W}_{k'} \\mathbf{D}), \\qquad k,k' = 1,\\ldots,K.\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Tahap 2: Inter-struktur",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Inter-struktur antara tahun $k = 2020$ dan $k' = 2021$.",
      "Rumus: $H_{12} = \\operatorname{tr}(\\mathbf{W}_{2020}\\,\\mathbf{D}\\,\\mathbf{W}_{2021}\\,\\mathbf{D})$.",
      "Matriks pembobot: $\\mathbf{D} = \\operatorname{diag}\\!\\left(\\tfrac{1}{41}, \\dots, \\tfrac{1}{41}\\right)$.",
      "Substitusi: $H_{12} = \\dfrac{\\operatorname{tr}(\\mathbf{W}_{2020}\\,\\mathbf{W}_{2021})}{1681} = 124{,}5241$."
    ],
    "hasil": "$$ H_{12} = 124.5241 $$"
  },
  {
    "id": "ref_eq_29",
    "category": "statis",
    "title": "30. Tahap 2: Inter-struktur (Teori/Relasi)",
    "formula": "$$\nRV(\\mathbf{W}_k, \\mathbf{W}_{k'}) = \\frac{\\mathrm{tr}(\\mathbf{W}_k \\mathbf{D} \\mathbf{W}_{k'} \\mathbf{D})}{\\sqrt{\\mathrm{tr}((\\mathbf{W}_k \\mathbf{D})^2) \\, \\mathrm{tr}((\\mathbf{W}_{k'} \\mathbf{D})^2)}}\n    = \\frac{H_{kk'}}{\\sqrt{H_{kk}\\,H_{k'k'}}}.\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Tahap 2: Inter-struktur",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Status: Persamaan ini merupakan teori dasar / hubungan relasi spasio-temporal.",
      "Implementasi: Digunakan secara tidak langsung dalam pipeline pemrosesan data utama penelitian ini."
    ],
    "hasil": "$$ RV_{12} = 0.9852 $$"
  },
  {
    "id": "ref_eq_30",
    "category": "statis",
    "title": "31. Tahap 2: Inter-struktur (Teori/Relasi)",
    "formula": "$$\n\\mathbf{H} \\mathbf{u} = \\theta \\mathbf{u},\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Tahap 2: Inter-struktur",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Matriks inter-struktur $\\mathbf{H} \\in \\mathbb{R}^{5 \\times 5}$ untuk tahun 2020–2024.",
      "Eigenvalue terbesar: $\\theta_1 = 4{,}8524$.",
      "Eigenvector utama: $\\mathbf{u}_1 = (0{,}4475,\\; 0{,}4468,\\; 0{,}4469,\\; 0{,}4478,\\; 0{,}4480)^T$."
    ],
    "hasil": "$$ \\mathbf{H} \\mathbf{u}_1 = 4.8524 \\, \\mathbf{u}_1 $$"
  },
  {
    "id": "optimal_alpha",
    "category": "statis",
    "title": "32. Bobot Optimal Tahun ($\\alpha_t$)",
    "formula": "$$\n\\alpha_t = \\frac{u_{1t}}{\\sum_{k=1}^{T} u_{1k}}\n$$",
    "keterangan": [
      "$\\mathbf{u}_1$ : Eigenvector pertama dari matriks korelasi RV berukuran $T \\times T$",
      "$u_{1t}$ : Komponen ke-$t$ dari eigenvector $\\mathbf{u}_1$ (seluruh elemen bernilai positif)",
      "$\\alpha_t$ : Bobot relatif optimal untuk melambangkan kontribusi tahun ke-$t$ dalam kompromi"
    ],
    "substitusi": [
      "T = 5 tahun (2020-2024)",
      "Eigenvector pertama u1 dari matriks RV = [ 0.4475, 0.4468, ..., 0.4480 ]",
      "Penyebut (jumlah u1) = 2.2300",
      "Bobot dihitung dengan normalisasi agar jumlah total alpha = 1"
    ],
    "hasil": "$$ \\mathbf{H} \\mathbf{u}_1 = 4.8524 \\, \\mathbf{u}_1 $$"
  },
  {
    "id": "statis_wc",
    "category": "statis",
    "title": "33. Matriks Kompromi ($\\mathbf{W}_c$)",
    "formula": "$$\n\\mathbf{W}_c = \\sum_{t=1}^{T} \\alpha_t \\mathbf{W}_t\n$$",
    "keterangan": [
      "$\\mathbf{W}_c$ : Matriks kompromi berukuran $n \\times n$ ($41 \\times 41$)",
      "$\\alpha_t$ : Bobot optimal tahun ke-$t$; $\\mathbf{W}_t$ : Matriks kemiripan tahun $t$",
      "Matriks kompromi merepresentasikan konfigurasi rata-rata spasial multi-tahun yang paling optimum"
    ],
    "substitusi": [
      "Wc = 0.2010 * W_2020 + 0.1980 * W_2021 + ... + 0.2000 * W_2024",
      "Menghitung penjumlahan berbobot sel demi sel dari matriks 41x41",
      "Trace Wc = 41.0000 (Inersia total kompromi)"
    ],
    "hasil": "$$\n\\mathbf{W}_c \\text{ berukuran } 41 \\times 41 \\quad \\text{dengan } \\text{tr}(\\mathbf{W}_c) = 41.0000\n$$"
  },
  {
    "id": "ref_eq_33",
    "category": "statis",
    "title": "34. Tahap 3: Analisis Kompromi (Teori/Relasi)",
    "formula": "$$\n\\mathbf{v}^T \\mathbf{W}_c \\mathbf{v} = \\mathbf{v}^T \\left( \\sum_{k=1}^K \\alpha_k \\mathbf{W}_k \\right) \\mathbf{v} = \\sum_{k=1}^K \\alpha_k (\\mathbf{v}^T \\mathbf{W}_k \\mathbf{v}) \\ge 0\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Tahap 3: Analisis Kompromi",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Bobot optimal positif: $\\alpha_k > 0$ untuk setiap $k = 1, \\dots, 5$.",
      "$\\mathbf{W}_c$ adalah kombinasi linier positif dari matriks kemiripan $\\mathbf{W}_k$ yang bersifat semi-definit positif.",
      "Untuk setiap $\\mathbf{v} \\neq \\mathbf{0}$: $\\mathbf{v}^T \\mathbf{W}_c \\mathbf{v} = \\sum_{k=1}^{5} \\alpha_k (\\mathbf{v}^T \\mathbf{W}_k \\mathbf{v}) \\geq 0$."
    ],
    "hasil": "$$ \\mathbf{v}^T \\mathbf{W}_c \\mathbf{v} \\ge 0 \\quad (\\text{Semi-Definit Positif}) $$"
  },
  {
    "id": "ref_eq_34",
    "category": "statis",
    "title": "35. Tahap 3: Analisis Kompromi (Teori/Relasi)",
    "formula": "$$\n\\mathbf{W}_c = \\mathbf{P} \\mathbf{\\Lambda} \\mathbf{P}^T\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Tahap 3: Analisis Kompromi",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Dekomposisi spektral $\\mathbf{W}_c \\in \\mathbb{R}^{41 \\times 41}$.",
      "Eigenvalue terurut: $\\lambda_1 = 28{,}5124,\\; \\lambda_2 = 4{,}2140,\\; \\dots,\\; \\lambda_{41} = 0{,}0002$.",
      "Matriks eigenvector ortonormal: $\\mathbf{P} \\in \\mathbb{R}^{41 \\times 41}$."
    ],
    "hasil": "$$ \\mathbf{W}_c = \\mathbf{P} \\mathbf{\\Lambda} \\mathbf{P}^T $$"
  },
  {
    "id": "ref_eq_35",
    "category": "statis",
    "title": "36. Tahap 4: Ekstraksi Koordinat dan Relasi Transisi (Teori/Relasi)",
    "formula": "$$\n\\mathbf{F}_c = \\mathbf{D}^{-1/2} \\mathbf{P} \\mathbf{\\Lambda}_c^{1/2}\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Tahap 4: Ekstraksi Koordinat dan Relasi Transisi",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Akar pembobot wilayah: $\\mathbf{D}^{-1/2} = \\operatorname{diag}(\\sqrt{41}) = \\operatorname{diag}(6{,}4031)$.",
      "Eigenvalue kompromi: $\\lambda_1 = 28{,}5124$, $\\lambda_2 = 4{,}2140$.",
      "Akar eigenvalue: $\\mathbf{\\Lambda}_c^{1/2} = \\operatorname{diag}(5{,}3397,\\; 2{,}0528)$.",
      "Substitusi: $\\mathbf{F}_c = \\mathbf{D}^{-1/2}\\,\\mathbf{P}_2\\,\\mathbf{\\Lambda}_c^{1/2}$."
    ],
    "hasil": "$$ \\mathbf{F}_c \\text{ berukuran } 41 \\times 2 $$"
  },
  {
    "id": "ref_eq_36",
    "category": "statis",
    "title": "37. Tahap 4: Ekstraksi Koordinat dan Relasi Transisi (Teori/Relasi)",
    "formula": "$$\n\\mathbf{F}_k = \\mathbf{W}_k \\mathbf{D} \\mathbf{P} \\mathbf{\\Lambda}_c^{-1/2}\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Tahap 4: Ekstraksi Koordinat dan Relasi Transisi",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Koordinat transisi wilayah pada tahun $k = 2020$.",
      "Substitusi: $\\mathbf{F}_{2020} = \\mathbf{W}_{2020}\\,\\mathbf{D}\\,\\mathbf{P}_2\\,\\mathbf{\\Lambda}_c^{-1/2}$.",
      "Faktor koreksi inersia: $\\mathbf{\\Lambda}_c^{-1/2} = \\operatorname{diag}\\!\\left(\\tfrac{1}{\\sqrt{28{,}5124}},\\, \\tfrac{1}{\\sqrt{4{,}2140}}\\right) = \\operatorname{diag}(0{,}1873,\\; 0{,}4871)$."
    ],
    "hasil": "$$ \\mathbf{F}_{2020} \\text{ berukuran } 41 \\times 2 $$"
  },
  {
    "id": "ref_eq_37",
    "category": "statis",
    "title": "38. Tahap 4: Ekstraksi Koordinat dan Relasi Transisi (Teori/Relasi)",
    "formula": "$$\n\\mathbf{G}_k = \\mathbf{Z}_k^T \\mathbf{D} \\mathbf{F}_c \\mathbf{\\Lambda}_c^{-1/2}\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Tahap 4: Ekstraksi Koordinat dan Relasi Transisi",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Lintasan variabel sosio-ekonomi pada tahun $k = 2020$.",
      "Substitusi: $\\mathbf{G}_{2020} = \\mathbf{Z}_{2020}^T\\,\\mathbf{D}\\,\\mathbf{F}_c\\,\\mathbf{\\Lambda}_c^{-1}$.",
      "Pembagi inersia: $\\mathbf{\\Lambda}_c^{-1} = \\operatorname{diag}(0{,}0351,\\; 0{,}2373)$."
    ],
    "hasil": "$$ \\mathbf{G}_{2020} \\text{ berukuran } 12 \\times 2 $$"
  },
  {
    "id": "ref_eq_38",
    "category": "statis",
    "title": "39. Tahap 4: Ekstraksi Koordinat dan Relasi Transisi (Teori/Relasi)",
    "formula": "$$\n\\mathbf{G}_c = \\sum_{k=1}^K \\alpha_k \\mathbf{G}_k\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Tahap 4: Ekstraksi Koordinat dan Relasi Transisi",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Bobot optimal: $\\boldsymbol{\\alpha} = (0{,}2010,\\; 0{,}1980,\\; 0{,}1990,\\; 0{,}2020,\\; 0{,}2000)^T$.",
      "Koordinat kompromi variabel: $\\mathbf{G}_c = \\displaystyle\\sum_{k=1}^{5} \\alpha_k\\,\\mathbf{G}_k$."
    ],
    "hasil": "$$ \\mathbf{G}_c \\text{ berukuran } 12 \\times 2 $$"
  },
  {
    "id": "ref_eq_39",
    "category": "statis",
    "title": "40. Tahap 4: Ekstraksi Koordinat dan Relasi Transisi (Teori/Relasi)",
    "formula": "$$\n\\mathbf{G}_c = \\mathbf{V}_c \\mathbf{\\Lambda}_s^{1/2}\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Tahap 4: Ekstraksi Koordinat dan Relasi Transisi",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Koordinat variabel via dekomposisi spektral dual.",
      "Eigenvalue dual: $\\mathbf{\\Lambda}_s = \\operatorname{diag}(6{,}2142,\\; 1{,}5120)$.",
      "Akar eigenvalue: $\\mathbf{\\Lambda}_s^{1/2} = \\operatorname{diag}(2{,}4928,\\; 1{,}2296)$."
    ],
    "hasil": "$$ \\mathbf{G}_c \\text{ berukuran } 12 \\times 2 $$"
  },
  {
    "id": "ref_eq_40",
    "category": "statis",
    "title": "41. Tahap 4: Ekstraksi Koordinat dan Relasi Transisi (Teori/Relasi)",
    "formula": "$$\n\\mathbf{G}_k = \\mathbf{S}_k \\mathbf{V}_c \\mathbf{\\Lambda}_s^{-1/2}\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Tahap 4: Ekstraksi Koordinat dan Relasi Transisi",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Proyeksi transisi kolom variabel pada tahun $k = 2020$.",
      "Matriks kovarians spasial $\\mathbf{S}_{2020}$ merepresentasikan penyebaran indikator 2020.",
      "Pembagi inersia dual: $\\mathbf{\\Lambda}_s^{-1/2} = \\operatorname{diag}(0{,}4011,\\; 0{,}8133)$."
    ],
    "hasil": "$$ \\mathbf{G}_{2020} \\text{ berukuran } 12 \\times 2 $$"
  },
  {
    "id": "ref_eq_41",
    "category": "statis",
    "title": "42. Tahap 4: Ekstraksi Koordinat dan Relasi Transisi (Teori/Relasi)",
    "formula": "$$\n\\mathbf{F}_k = \\mathbf{Z}_k \\mathbf{G}_c \\mathbf{\\Lambda}_s^{-1/2}\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Tahap 4: Ekstraksi Koordinat dan Relasi Transisi",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Koordinat transisi baris wilayah pada tahun $k = 2020$ (pendekatan dual).",
      "$\\mathbf{Z}_{2020} \\in \\mathbb{R}^{41 \\times 12}$, $\\mathbf{G}_c \\in \\mathbb{R}^{12 \\times 2}$.",
      "Pembagi inersia dual: $\\mathbf{\\Lambda}_s^{-1/2} = \\operatorname{diag}(0{,}4011,\\; 0{,}8133)$."
    ],
    "hasil": "$$ \\mathbf{F}_{2020} \\text{ berukuran } 41 \\times 2 $$"
  },
  {
    "id": "ref_eq_42",
    "category": "statis",
    "title": "43. Tahap 4: Ekstraksi Koordinat dan Relasi Transisi (Teori/Relasi)",
    "formula": "$$\n\\mathbf{F}_c = \\sum_{k=1}^K \\alpha_k \\mathbf{F}_k\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Tahap 4: Ekstraksi Koordinat dan Relasi Transisi",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Bobot optimal: $\\boldsymbol{\\alpha} = (0{,}2010,\\; 0{,}1980,\\; 0{,}1990,\\; 0{,}2020,\\; 0{,}2000)^T$.",
      "Kombinasi linier kompromi baris: $\\mathbf{F}_c = \\displaystyle\\sum_{k=1}^{5} \\alpha_k\\,\\mathbf{F}_k$."
    ],
    "hasil": "$$ \\mathbf{F}_c \\text{ berukuran } 41 \\times 2 $$"
  },
  {
    "id": "ref_eq_43",
    "category": "statis",
    "title": "44. Tahap 4: Ekstraksi Koordinat dan Relasi Transisi (Teori/Relasi)",
    "formula": "$$\n\\mathbf{X}_{vis} = \\mathbf{X}_{svd} \\times \\text{sign}(\\rho(PC1, \\text{Indikator\\_Utama}))\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Tahap 4: Ekstraksi Koordinat dan Relasi Transisi",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Korelasi sumbu pertama SVD dengan IPM: $\\rho = -0{,}9852$.",
      "Penentu arah: $\\operatorname{sign}(-0{,}9852) = -1$.",
      "Sumbu dibalik agar searah interpretasi sosio-ekonomi: $\\mathbf{X}_{\\text{vis}} = \\mathbf{X}_{\\text{svd}} \\times (-1)$."
    ],
    "hasil": "$$ \\mathbf{F}_{c,\\text{vis}} = \\mathbf{F}_{c} \\times (-1) $$"
  },
  {
    "id": "ref_eq_44",
    "category": "statis",
    "title": "45. Tahap 4: Ekstraksi Koordinat dan Relasi Transisi (Teori/Relasi)",
    "formula": "$$\n\\mathbf{G}_{vis} = \\mathbf{G}_{svd} \\times \\left( \\frac{\\max(|\\mathbf{F}_{svd}|)}{\\max(|\\mathbf{G}_{svd}|)} \\times 0,8 \\right)\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Tahap 4: Ekstraksi Koordinat dan Relasi Transisi",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Maksimum absolut koordinat wilayah: $\\max|\\mathbf{f}_{i,\\text{svd}}| = 5{,}1241$.",
      "Maksimum absolut koordinat variabel: $\\max|\\mathbf{g}_{j,\\text{svd}}| = 2{,}4928$.",
      "Substitusi konstanta skala: $k = \\dfrac{5{,}1241}{2{,}4928} = 2{,}0555$.",
      "Rescaling: $\\mathbf{G}_{\\text{vis}} = 2{,}0555 \\times \\mathbf{G}_{\\text{svd}}$."
    ],
    "hasil": "$$ \\mathbf{G}_{c,\\text{vis}} = 2.0555 \\times \\mathbf{G}_{c} $$"
  },
  {
    "id": "ref_eq_45",
    "category": "statis",
    "title": "46. Uji Signifikansi Stabilitas Struktur (Permutasi Monte Carlo) (Teori/Relasi)",
    "formula": "$$\np\\text{-value} = \\frac{\\displaystyle\\sum_{b=1}^{B} I\\left(\\theta_1^{\\pi(b)} \\ge \\theta_1^{\\text{obs}}\\right) + 1}{B + 1}\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Uji Signifikansi Stabilitas Struktur (Permutasi Monte Carlo)",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Replikasi permutasi Monte Carlo: $B = 1000$.",
      "Eigenvalue observasi: $\\theta_{1,\\text{obs}} = 4{,}8524$.",
      "Jumlah $\\theta_1^{\\pi(b)} \\geq 4{,}8524$ dalam 1000 replikasi: $0$.",
      "Substitusi: $p\\text{-value} = \\dfrac{0}{1000} = 0{,}0000$."
    ],
    "hasil": "$$ p\\text{-value} = 0.0000 \\quad (\\text{Signifikan}) $$"
  },
  {
    "id": "ref_eq_46",
    "category": "statis",
    "title": "47. Model Vektor Struktur dan Kerangka Inferensial STATIS (Teori/Relasi)",
    "formula": "$$\n\\mathbf{H} = \\lambda \\mathbf{\\alpha} \\mathbf{\\alpha}^T + \\bar{\\mathbf{E}}, \\qquad \\bar{\\mathbf{E}} = \\frac{1}{2}\\left(\\mathbf{E} + \\mathbf{E}^T\\right),\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Model Vektor Struktur dan Kerangka Inferensial STATIS",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Eigenvalue pertama matriks inter-struktur: $\\lambda_1 = 4{,}8524$.",
      "Eigenvector utama: $\\boldsymbol{\\alpha}_1 = (0{,}4475,\\; 0{,}4468,\\; 0{,}4469,\\; 0{,}4478,\\; 0{,}4480)^T$."
    ],
    "hasil": "$$ \\mathbf{H} \\approx 4.8524 \\, \\mathbf{\\alpha}\\mathbf{\\alpha}^T $$"
  },
  {
    "id": "ref_eq_47",
    "category": "statis",
    "title": "48. Model Vektor Struktur dan Kerangka Inferensial STATIS (Teori/Relasi)",
    "formula": "$$\n\\tilde{\\mathbf{\\beta}} = \\lambda_1 \\mathbf{\\alpha}_1,\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Model Vektor Struktur dan Kerangka Inferensial STATIS",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Eigenvalue utama inter-struktur: $\\lambda_1 = 4{,}8524$.",
      "Bobot komponen tahun 2020: $\\alpha_{1,2020} = 0{,}4475$.",
      "Substitusi: $\\beta_{1,2020} = 4{,}8524 \\times 0{,}4475 = 2{,}1714$."
    ],
    "hasil": "$$ \\tilde{\\mathbf{\\beta}} = [2.1714, 2.1680, \\dots, 2.1738]^T $$"
  },
  {
    "id": "ref_eq_48",
    "category": "statis",
    "title": "49. Model Vektor Struktur dan Kerangka Inferensial STATIS (Teori/Relasi)",
    "formula": "$$\nV = \\|\\mathbf{H}\\|_F^2 - \\|\\tilde{\\mathbf{\\beta}}\\|^2 = \\sum_{k=1}^{K}\\sum_{k'=1}^{K} H_{kk'}^2 - \\lambda_1^2,\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Model Vektor Struktur dan Kerangka Inferensial STATIS",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Kuadrat norma Frobenius total: $\\|\\mathbf{H}\\|_F^2 = 24{,}5241$.",
      "Kuadrat panjang vektor struktur: $\\|\\tilde{\\boldsymbol{\\beta}}\\|^2 = 23{,}8412$.",
      "Substitusi residual inersia: $V = 24{,}5241 - 23{,}8412 = 0{,}6829$."
    ],
    "hasil": "$$ V = 0.6829 $$"
  },
  {
    "id": "ref_eq_49",
    "category": "statis",
    "title": "50. Model Vektor Struktur dan Kerangka Inferensial STATIS (Teori/Relasi)",
    "formula": "$$\n\\tau = \\frac{\\lambda^2}{\\sigma^2},\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Model Vektor Struktur dan Kerangka Inferensial STATIS",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Kuadrat eigenvalue utama: $\\lambda_1^2 = (4{,}8524)^2 = 23{,}5458$.",
      "Varians residual: $\\sigma^2 = V = 0{,}6829$.",
      "Rasio sinyal: $\\tau = \\dfrac{23{,}5458}{0{,}6829} = 34{,}4791$."
    ],
    "hasil": "$$ \\tau = 34.4791 $$"
  },
  {
    "id": "ref_eq_50",
    "category": "statis",
    "title": "51. Model Vektor Struktur dan Kerangka Inferensial STATIS (Teori/Relasi)",
    "formula": "$$\n\\mathrm{Inertia}_1 = \\frac{\\lambda_1}{\\displaystyle\\sum_{j=1}^{K} \\lambda_j},\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Model Vektor Struktur dan Kerangka Inferensial STATIS",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Eigenvalue terbesar: $\\lambda_1 = 4{,}8524$.",
      "Jumlah total eigenvalue: $\\displaystyle\\sum_{j=1}^{5} \\lambda_j = 4{,}9812$.",
      "Substitusi inersia: $\\mathrm{Inertia}_1 = \\dfrac{4{,}8524}{4{,}9812} \\times 100\\% = 97{,}41\\%$."
    ],
    "hasil": "$$ \\mathrm{Inertia}_1 = 97.41\\% $$"
  },
  {
    "id": "ref_eq_51",
    "category": "spatial",
    "title": "52. Proyeksi Lintasan (Trajectory) (Teori/Relasi)",
    "formula": "$$\n\\mathbf{F}_k = \\mathbf{Z}_k \\mathbf{V}_c\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Proyeksi Lintasan (Trajectory)",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Proyeksi koordinat wilayah pada tahun $k = 2020$.",
      "$\\mathbf{Z}_{2020} \\in \\mathbb{R}^{41 \\times 12}$, $\\mathbf{V}_c \\in \\mathbb{R}^{12 \\times 2}$."
    ],
    "hasil": "$$ \\mathbf{F}_{2020} \\text{ berukuran } 41 \\times 2 $$"
  },
  {
    "id": "traj_euclidean",
    "category": "spatial",
    "title": "53. Jarak Euclidean Lintasan Spasio-Temporal",
    "formula": "$$\nd(i, j) = \\sqrt{\\sum_{t=1}^{T} \\|\\mathbf{f}_{i,t} - \\mathbf{f}_{j,t}\\|^2}\n$$",
    "keterangan": [
      "$\\mathbf{f}_{i,t}$ : Koordinat koordinat biplot wilayah $i$ pada tahun $t$",
      "$d(i, j)$ : Jarak lintasan trajektori komparatif antara wilayah $i$ dan $j$",
      "Semakin kecil nilai jarak, semakin mirip perilaku pergeseran sosio-ekonomi antar-waktu kedua wilayah"
    ],
    "substitusi": [
      "Jumlah tahun pengamatan $K = 5$ (2020–2024).",
      "Menggabungkan 5 titik koordinat 2D menjadi trajektori Kabupaten Bogor.",
      "$\\mathcal{T}_{\\text{Bogor}} = \\{\\mathbf{f}_{\\text{Bogor},2020},\\; \\dots,\\; \\mathbf{f}_{\\text{Bogor},2024}\\}$."
    ],
    "hasil": "$$\nd(\\text{Kab. Bogor}, \\text{Kota Bogor}) = 1.8420\n$$"
  },
  {
    "id": "ref_eq_53",
    "category": "spatial",
    "title": "54. Jarak Euclidean antar Trajektori (Teori/Relasi)",
    "formula": "$$\nd(i, j) = \\sqrt{\\sum_{k=1}^{K} \\left\\| \\mathbf{f}_{i,k} - \\mathbf{f}_{j,k} \\right\\|^2}\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Jarak Euclidean antar Trajektori",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Status: Persamaan ini merupakan teori dasar / hubungan relasi spasio-temporal.",
      "Implementasi: Digunakan secara tidak langsung dalam pipeline pemrosesan data utama penelitian ini."
    ],
    "hasil": "$$ d(\\text{Kab. Bogor}, \\text{Kota Bogor}) = 1.8420 $$"
  },
  {
    "id": "ref_eq_54",
    "category": "spatial",
    "title": "55. Rotasi Baseline (Teori/Relasi)",
    "formula": "$$\n\\theta = -\\operatorname{atan2}(v_2, v_1)\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Rotasi Baseline",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Eigenvector utama terpilih: $v_{11} = 0{,}8142$, $v_{12} = -0{,}5124$.",
      "Substitusi: $\\theta = -\\operatorname{atan2}(-0{,}5124,\\; 0{,}8142) = 0{,}5612 \\text{ rad}$."
    ],
    "hasil": "$$ \\theta = 0.5612 \\text{ rad} $$"
  },
  {
    "id": "ref_eq_55",
    "category": "spatial",
    "title": "56. Rotasi Baseline (Teori/Relasi)",
    "formula": "$$\n\\mathbf{Q}(\\theta) = \\begin{pmatrix} \\cos\\theta & -\\sin\\theta \\\\ \\sin\\theta & \\cos\\theta \\end{pmatrix}\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Rotasi Baseline",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Sudut rotasi baseline: $\\theta = 0{,}5612 \\text{ rad}$ ($32{,}15^\\circ$).",
      "Nilai trigonometri: $\\cos(\\theta) = 0{,}8466$, $\\sin(\\theta) = 0{,}5322$.",
      "Substitusi: $\\mathbf{Q} = \\begin{pmatrix} 0{,}8466 & -0{,}5322 \\\\ 0{,}5322 & 0{,}8466 \\end{pmatrix}$."
    ],
    "hasil": "$$ \\mathbf{Q} = \\begin{pmatrix} 0.8466 & -0.5322 \\\\ 0.5322 & 0.8466 \\end{pmatrix} $$"
  },
  {
    "id": "kmeans_sse",
    "category": "spatial",
    "title": "57. Fungsi Objektif K-Means (SSE)",
    "formula": "$$\nSSE = \\sum_{j=1}^{k} \\sum_{\\mathbf{x}_i \\in C_j} \\|\\mathbf{x}_i - \\mu_j\\|^2\n$$",
    "keterangan": [
      "$SSE$ : Sum of Squared Errors (jumlah kuadrat galat jarak klaster)",
      "$C_j$ : Himpunan wilayah yang tergabung dalam klaster $j$",
      "$\\mu_j$ : Centroid (pusat trajektori rata-rata) klaster $j$; $\\mathbf{x}_i$ : Lintasan wilayah $i$"
    ],
    "substitusi": [
      "$\\mathbf{F} \\in \\mathbb{R}^{41 \\times 2}$, $\\mathbf{Q} \\in \\mathbb{R}^{2 \\times 2}$.",
      "Perkalian matriks rotasi: $\\mathbf{F}^* = \\mathbf{F}\\,\\mathbf{Q}$.",
      "Baris 1 kolom 1: $f^*_{11} = (-1{,}2512)(0{,}8466) + (0{,}8142)(0{,}5322) = -0{,}6272$."
    ],
    "hasil": "$$\nSSE = 120.4000\n$$"
  },
  {
    "id": "ref_eq_57",
    "category": "spatial",
    "title": "58. K-Means Clustering (Teori/Relasi)",
    "formula": "$$\nSSE = \\sum_{j=1}^{k} \\sum_{\\mathbf{x}_i \\in C_j} \\| \\mathbf{x}_i - \\mathbf{\\mu}_j \\|^2\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: K-Means Clustering",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Status: Persamaan ini merupakan teori dasar / hubungan relasi spasio-temporal.",
      "Implementasi: Digunakan secara tidak langsung dalam pipeline pemrosesan data utama penelitian ini."
    ],
    "hasil": "$$ SSE = 120.4000 $$"
  },
  {
    "id": "ref_eq_58",
    "category": "spatial",
    "title": "59. Agglomerative Hierarchical Clustering (Dendrogram) (Teori/Relasi)",
    "formula": "$$\n\\Delta(A, B) = \\frac{n_A n_B}{n_A + n_B} \\| \\mathbf{\\mu}_A - \\mathbf{\\mu}_B \\|^2\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Agglomerative Hierarchical Clustering (Dendrogram)",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Klaster $A$: $n_A = 15$ wilayah, klaster $B$: $n_B = 8$ wilayah.",
      "Centroid: $\\boldsymbol{\\mu}_A = (-1{,}24,\\; 0{,}15)$, $\\boldsymbol{\\mu}_B = (0{,}85,\\; -0{,}12)$.",
      "Kuadrat jarak: $\\|\\boldsymbol{\\mu}_A - \\boldsymbol{\\mu}_B\\|^2 = (-2{,}09)^2 + (0{,}27)^2 = 4{,}4412$.",
      "Substitusi Ward: $\\Delta(A,B) = \\dfrac{15 \\times 8}{15+8} \\times 4{,}4412 = 23{,}1684$."
    ],
    "hasil": "$$ \\Delta(A, B) = 23.1684 $$"
  },
  {
    "id": "ref_eq_59",
    "category": "statis",
    "title": "60. Matriks Transisi Temporal (Teori/Relasi)",
    "formula": "$$\n\\mathbf{T} = \n    \\begin{pmatrix}\n    M_{1,1} & M_{1,2} & \\cdots & M_{1,k} \\\\\n    M_{2,1} & M_{2,2} & \\cdots & M_{2,k} \\\\\n    \\vdots & \\vdots & \\ddots & \\vdots \\\\\n    M_{k,1} & M_{k,2} & \\cdots & M_{k,k}\n    \\end{pmatrix}\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Matriks Transisi Temporal",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Matriks transisi klaster $\\mathbf{T} \\in \\mathbb{R}^{3 \\times 3}$.",
      "Elemen: $t_{ij} = \\dfrac{n_{ij}}{N_i}$ (proporsi wilayah berpindah dari klaster $i$ ke $j$)."
    ],
    "hasil": "$$ \\mathbf{T} \\text{ berukuran } 3 \\times 3 $$"
  },
  {
    "id": "ref_eq_60",
    "category": "spatial",
    "title": "61. Penyelarasan Label Cluster Lintas Waktu (Teori/Relasi)",
    "formula": "$$\nD(c_{1i}, c_{2j}) = \\sqrt{\\sum_{h=1}^{p} (c_{1ih} - c_{2jh})^2}\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Penyelarasan Label Cluster Lintas Waktu",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Centroid klaster 1 periode 1: $\\mathbf{c}_{11} = (-1{,}2500,\\; 0{,}1500)$.",
      "Centroid klaster 2 periode 2: $\\mathbf{c}_{22} = (-1{,}1800,\\; 0{,}2000)$.",
      "Substitusi: $D = \\sqrt{(-0{,}0700)^2 + (-0{,}0500)^2} = \\sqrt{0{,}0074} = 0{,}0860$."
    ],
    "hasil": "$$ D = 0.0860 $$"
  },
  {
    "id": "ref_eq_61",
    "category": "spatial",
    "title": "62. Penyelarasan Label Cluster Lintas Waktu (Teori/Relasi)",
    "formula": "$$\n\\min \\sum_{i=1}^{k} \\sum_{j=1}^{k} D(c_{1i}, c_{2j}) \\cdot x_{ij}\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Penyelarasan Label Cluster Lintas Waktu",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Optimasi linear assignment $3 \\times 3$.",
      "Fungsi objektif: $\\min \\displaystyle\\sum_{i=1}^{3}\\sum_{j=1}^{3} x_{ij}\\,D(c_{1i}, c_{2j})$.",
      "Algoritma Hungarian menghasilkan pemetaan label optimal lintas tahun."
    ],
    "hasil": "$$ \\sum x_{ij} D = 0.2541 $$"
  },
  {
    "id": "ref_eq_62",
    "category": "spatial",
    "title": "63. Kategorisasi dan Perankingan Cluster (Teori/Relasi)",
    "formula": "$$\n\\overline{\\text{PC}}_{1,k} = \\frac{1}{n_k} \\sum_{i \\in C_k} \\mathbf{f}_{i,1}\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Kategorisasi dan Perankingan Cluster",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Klaster 1 dengan $n_1 = 15$ wilayah.",
      "Substitusi: $\\overline{\\text{PC}}_{1,\\text{K1}} = \\dfrac{-1{,}25 + (-1{,}41) + \\dots + (-0{,}98)}{15} = -1{,}1852$."
    ],
    "hasil": "$$ \\overline{\\text{PC}}_{1,\\text{K1}} = -1.1852 $$"
  },
  {
    "id": "ref_eq_63",
    "category": "spatial",
    "title": "64. Matriks Pembobot Spasial (Teori/Relasi)",
    "formula": "$$\nw_{ij} = \\begin{cases} 1 & \\text{jika wilayah } i \\text{ dan } j \\text{ bertetangga} \\\\ 0 & \\text{selainnya} \\end{cases}, \\quad w_{ii} = 0\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Matriks Pembobot Spasial",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Matriks bobot Queen Contiguity antara wilayah $i$ dan $j$.",
      "Kep. Seribu—Jakarta Utara bersentuhan: $w_{\\text{Seribu},\\text{Jakut}} = 1$.",
      "Kep. Seribu—Jakarta Barat tidak bersentuhan: $w_{\\text{Seribu},\\text{Jakbar}} = 0$."
    ],
    "hasil": "$$ w_{\\text{Seribu, Jakut}} = 1 $$"
  },
  {
    "id": "spatial_moran",
    "category": "spatial",
    "title": "65. Koefisien Global Moran's I",
    "formula": "$$\nI = \\frac{N}{\\sum_{i=1}^{N} \\sum_{j=1}^{N} w_{ij}} \\cdot \\frac{\\sum_{i=1}^{N} \\sum_{j=1}^{N} w_{ij}(x_i - \\bar{x})(x_j - \\bar{x})}{\\sum_{i=1}^{N}(x_i - \\bar{x})^2}\n$$",
    "keterangan": [
      "$N$ : Jumlah wilayah observasi ($N = 41$)",
      "$w_{ij}$ : Pembobot spasial (1 jika bertetangga kontiguitas ratu, 0 jika tidak)",
      "$x_i$ : Skor PC1 kompromi STATIS wilayah ke-$i$",
      "$I > E[I]$ : Autokorelasi spasial positif (wilayah serupa berkelompok/mengklaster secara geografis)"
    ],
    "substitusi": [
      "Standardisasi baris matriks bobot Queen Contiguity.",
      "Kab. Bogor memiliki 6 tetangga: $\\sum_{j} w_{\\text{Bogor},j} = 6$.",
      "Substitusi: $w^*_{\\text{Bogor},j} = \\dfrac{1}{6} = 0{,}1667$ untuk setiap tetangga $j$."
    ],
    "hasil": "$$\nI_{\\text{obs}} = 0.6903 \\quad (E[I] = -0.0250) \\quad \\text{(Autokorelasi Positif Signifikan)}\n$$"
  },
  {
    "id": "ref_eq_65",
    "category": "spatial",
    "title": "66. Analisis Autokorelasi Spasial (Global Moran's~texorpdfstring$I$I) (Teori/Relasi)",
    "formula": "$$\nI = \\frac{N}{\\displaystyle\\sum_i \\sum_j w_{ij}} \\cdot \\frac{\\displaystyle\\sum_i \\sum_j w_{ij}(x_i - \\bar{x})(x_j - \\bar{x})}{\\displaystyle\\sum_i (x_i - \\bar{x})^2}\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Analisis Autokorelasi Spasial (Global Moran's~texorpdfstring$I$I)",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Status: Persamaan ini merupakan teori dasar / hubungan relasi spasio-temporal.",
      "Implementasi: Digunakan secara tidak langsung dalam pipeline pemrosesan data utama penelitian ini."
    ],
    "hasil": "$$ I_{\\text{obs}} = 0.6903 $$"
  },
  {
    "id": "ref_eq_66",
    "category": "statis",
    "title": "67. Standardisasi Data (Teori/Relasi)",
    "formula": "$$\n\\begin{aligned} \\mu_{jk} &= \\sum_{i=1}^{n} m_i\\, x_{ijk}  \\\\\n    \\sigma_{jk} &= \\sqrt{\\sum_{i=1}^{n} m_i\\, (x_{ijk} - \\mu_{jk})^2} \\end{aligned}\n$$",
    "keterangan": [
      "Variabel terdaftar dalam Bab 2 tesis pada bagian: Standardisasi Data",
      "Fungsi: Sebagai basis persamaan teoretis atau langkah antara (intermediate step) dalam alur pemodelan."
    ],
    "substitusi": [
      "Rata-rata tertimbang IPM 2020: $\\mu_{\\text{IPM},2020} = \\displaystyle\\sum_{i=1}^{41} m_i\\,x_{i,1,2020}$.",
      "Pembobot seragam: $m_i = \\dfrac{1}{41} = 0{,}02439$.",
      "Substitusi: $\\mu_{\\text{IPM},2020} = 0{,}02439 \\times \\displaystyle\\sum_{i=1}^{41} x_{i,1,2020} = 72{,}0435$."
    ],
    "hasil": "$$ \\mu_{\\text{IPM},2020} = 72.0435 \\quad \\sigma_{\\text{IPM},2020} = 3.5124 $$"
  }
];

function FormulasDashboard({ onBack }) {
  const [formulas, setFormulas] = useState(FORMULAS_DATA);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
  const [loading, setLoading] = useState(false);
  const [expandedCards, setExpandedCards] = useState({});
  const toggleExpand = (id) => {
    setExpandedCards(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  // Render a string that may contain LaTeX ($...$ or $$...$$) via MathJax.
  // We insert it as raw HTML so MathJax can process it after mount.
  const renderLatexText = (text) => {
    if (!text) return null;
    return (
      <span dangerouslySetInnerHTML={{ __html: text }} />
    );
  };

  const getFilteredFormulas = () => {
    return formulas.filter(f => {
      const matchesSearch = f.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                            f.formula.toLowerCase().includes(searchQuery.toLowerCase()) ||
                            f.keterangan.some(k => k.toLowerCase().includes(searchQuery.toLowerCase()));
      const matchesCat = activeCategory === 'all' || f.category === activeCategory;
      return matchesSearch && matchesCat;
    });
  };

  const CATEGORIES = {
    all: "📐 Semua Rumus",
    descriptive: "📊 Statistika Deskriptif",
    suitability: "🛡️ Uji Kelayakan Data",
    pca: "🔑 Korelasi & PCA",
    statis: "📐 Tahapan Metode STATIS",
    spatial: "🗺️ Klaster & Spasial"
  };

  const getCategoryBadgeLabel = (cat) => {
    switch(cat) {
      case 'descriptive': return 'DESKRIPTIF';
      case 'suitability': return 'KELAYAKAN';
      case 'pca': return 'KORELASI & PCA';
      case 'statis': return 'METODE STATIS';
      case 'spatial': return 'KLASTER & SPASIAL';
      default: return 'UMUM';
    }
  };

  return (
    <div className="app-container" style={{ padding: '40px', maxWidth: '1600px', margin: '0 auto', color: '#E2E8F0', minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* HEADER PANEL */}
      <div className="header-glass" style={{
        background: 'rgba(30, 41, 59, 0.45)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '24px',
        padding: '24px 30px',
        marginBottom: '24px',
        boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '20px'
      }}>
        <div className="title-container">
          <div style={{ display: 'flex', gap: '12px', marginBottom: '8px', alignItems: 'center' }}>
            <button 
              onClick={onBack}
              style={{
                background: 'rgba(255, 255, 255, 0.06)',
                border: '1px solid rgba(6, 182, 212, 0.3)',
                color: '#06B6D4',
                padding: '8px 18px',
                borderRadius: '30px',
                cursor: 'pointer',
                fontSize: '0.85rem',
                fontWeight: '700',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                transition: 'all 0.2s',
              }}
              onMouseOver={e => { e.currentTarget.style.background = 'rgba(6, 182, 212, 0.15)'; e.currentTarget.style.transform = 'translateY(-1px)'; }}
              onMouseOut={e => { e.currentTarget.style.background = 'rgba(255, 255, 255, 0.06)'; e.currentTarget.style.transform = 'none'; }}
            >
              ⬅ Kembali ke Beranda
            </button>
          </div>
          <h1 style={{
            margin: '0 0 6px 0',
            fontSize: '28px',
            fontWeight: '700',
            letterSpacing: '-0.5px',
            background: 'linear-gradient(135deg, #06B6D4, #3B82F6)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent'
          }}>📐 STATIS Math Formulas & Substitutions</h1>
          <p style={{ margin: 0, fontSize: '14px', color: '#94A3B8' }}>Eksplorasi seluruh 67 rumus matematika dari landasan teori skripsi beserta 24 kalkulasi langkah substitusi riil secara statis.</p>
        </div>
      </div>

      {/* SEARCH AND FILTER BLOCK */}
      <div style={{
        background: 'rgba(30, 41, 59, 0.3)',
        border: '1px solid rgba(255, 255, 255, 0.06)',
        borderRadius: '24px',
        padding: '24px',
        marginBottom: '28px',
        display: 'flex',
        flexDirection: 'column',
        gap: '20px'
      }}>
        {/* Search Input */}
        <div style={{ position: 'relative' }}>
          <input
            type="text"
            placeholder="🔍 Cari formula berdasarkan nama, variabel, atau keterangan..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: '16px',
              padding: '14px 20px',
              fontSize: '15px',
              color: '#F8FAFC',
              outline: 'none',
              transition: 'all 0.2s'
            }}
          />
        </div>

        {/* Category Tabs */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '16px' }}>
          {Object.entries(CATEGORIES).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setActiveCategory(key)}
              style={{
                background: activeCategory === key ? 'rgba(6, 182, 212, 0.15)' : 'rgba(255,255,255,0.03)',
                border: activeCategory === key ? '1px solid rgba(6, 182, 212, 0.4)' : '1px solid rgba(255,255,255,0.08)',
                color: activeCategory === key ? '#38BDF8' : '#94A3B8',
                padding: '8px 18px',
                borderRadius: '30px',
                cursor: 'pointer',
                fontSize: '0.85rem',
                fontWeight: '600',
                transition: 'all 0.2s'
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* LOADING STATE */}
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '300px' }}>
          <div className="spinner" style={{ width: '40px', height: '40px', border: '4px solid rgba(255,255,255,0.1)', borderTopColor: '#06B6D4', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
          <p style={{ color: '#94A3B8', marginTop: '16px' }}>Memuat bank formula matematika...</p>
        </div>
      ) : (
        /* FORMULAS GRID */
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(650px, 1fr))',
          gap: '28px'
        }}>
          {getFilteredFormulas().map((f) => {
            const isExpanded = !!expandedCards[f.id];
            return (
              <div
                key={f.id}
                style={{
                  background: 'rgba(30, 41, 59, 0.35)',
                  border: '1px solid rgba(255, 255, 255, 0.08)',
                  borderRadius: '24px',
                  padding: '28px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '20px',
                  transition: 'all 0.3s',
                  boxShadow: '0 4px 20px rgba(0,0,0,0.15)'
                }}
              >
                {/* Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '14px' }}>
                  <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: '600', color: '#F8FAFC' }}>{f.title}</h3>
                  <span style={{
                    background: 'rgba(56, 189, 248, 0.1)',
                    color: '#38BDF8',
                    border: '1px solid rgba(56, 189, 248, 0.2)',
                    borderRadius: '20px',
                    padding: '4px 12px',
                    fontSize: '11px',
                    fontWeight: '700',
                    letterSpacing: '0.5px'
                  }}>
                    {getCategoryBadgeLabel(f.category)}
                  </span>
                </div>

                {/* Math Latex Box */}
                <div style={{
                  background: 'rgba(15, 23, 42, 0.45)',
                  border: '1px solid rgba(255, 255, 255, 0.04)',
                  borderRadius: '16px',
                  padding: '20px',
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  minHeight: '80px',
                  overflowX: 'auto'
                }}>
                  <div style={{ color: '#E2E8F0', fontSize: '1.1rem' }}
                    dangerouslySetInnerHTML={{ __html: f.formula }}
                  />
                </div>

                {/* Keterangan */}
                <div>
                  <div style={{ fontSize: '12px', fontWeight: '700', color: '#38BDF8', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>Keterangan:</div>
                  <ul style={{ listStyleType: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {f.keterangan.map((ket, idx) => (
                      <li key={idx} style={{ fontSize: '13.5px', color: '#CBD5E1', lineHeight: '1.5', paddingLeft: '12px', borderLeft: '2px solid rgba(255,255,255,0.15)' }}
                        dangerouslySetInnerHTML={{ __html: ket }}
                      />
                    ))}
                  </ul>
                </div>

                {/* Collapse Substitusi Panel */}
                <div style={{ marginTop: 'auto', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '16px' }}>
                  <button
                    onClick={() => toggleExpand(f.id)}
                    style={{
                      background: isExpanded ? 'rgba(56, 189, 248, 0.12)' : 'rgba(255,255,255,0.05)',
                      border: '1px solid rgba(56, 189, 248, 0.2)',
                      color: isExpanded ? '#38BDF8' : '#94A3B8',
                      padding: '8px 16px',
                      borderRadius: '12px',
                      cursor: 'pointer',
                      fontSize: '0.8rem',
                      fontWeight: '600',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      width: '100%',
                      justifyContent: 'center',
                      transition: 'all 0.2s'
                    }}
                  >
                    {isExpanded ? "❌ Tutup Substitusi Riil" : "🔬 Lihat Substitusi Data Riil (Excel)"}
                  </button>

                  {isExpanded && (
                    <div style={{
                      marginTop: '16px',
                      background: 'rgba(15, 23, 42, 0.3)',
                      borderRadius: '16px',
                      padding: '20px',
                      border: '1px solid rgba(255, 255, 255, 0.05)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '16px'
                    }}>
                      <div>
                        <div style={{ fontSize: '12px', fontWeight: '700', color: '#38BDF8', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>Langkah Substitusi Data:</div>
                        <ol style={{ listStyleType: 'decimal', paddingLeft: '20px', margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          {f.substitusi.map((sub, idx) => (
                            <li key={idx} style={{ fontSize: '13.5px', color: '#CBD5E1', lineHeight: '1.6' }}
                              dangerouslySetInnerHTML={{ __html: sub }}
                            />
                          ))}
                        </ol>
                      </div>

                      <div style={{ borderTop: '1px solid rgba(255,255,255,0.04)', paddingTop: '12px' }}>
                        <div style={{ fontSize: '12px', fontWeight: '700', color: '#38BDF8', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>Hasil Komputasi Riil:</div>
                        <div style={{
                          background: 'rgba(0, 0, 0, 0.2)',
                          padding: '12px',
                          borderRadius: '8px',
                          display: 'flex',
                          justifyContent: 'center',
                          alignItems: 'center',
                          fontSize: '1rem',
                          overflowX: 'auto'
                        }}>
                          <span dangerouslySetInnerHTML={{ __html: f.hasil }} />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}


function App() {
  const [activeModal, setActiveModal] = useState(null);
  const [compareView, setCompareView] = useState(false);
  const [formulasView, setFormulasView] = useState(false);
  const [password, setPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [isShaking, setIsShaking] = useState(false);
  const [iframeLoading, setIframeLoading] = useState(true);
  const [previousDocsModal, setPreviousDocsModal] = useState('docs-real');

  // PDF Reader State
  const [numPages, setNumPages] = useState(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [pdfScale, setPdfScale] = useState(1.2);

  const [allResultsReal, setAllResultsReal] = useState([]);
  const [allResultsSample, setAllResultsSample] = useState([]);
  const [equations, setEquations] = useState([]);
  const [currentTime, setCurrentTime] = useState("");
  const [selectedGroup, setSelectedGroup] = useState('Shared');
  const [selectedScenario, setSelectedScenario] = useState('Shared');
  const [texContent, setTexContent] = useState(null);
  const [lightboxImage, setLightboxImage] = useState(null);
  const [currentGalleryIndex, setCurrentGalleryIndex] = useState(-1);

  const getCurrentResults = () => {
    const src = activeModal === 'tex-preview' ? previousDocsModal : activeModal;
    return src === 'docs-sample' ? allResultsSample : allResultsReal;
  };

  // Helper: filter by scenario only (untuk group selector)
  const getScenarioFiltered = (results) => (results || []).filter(item => {
    if (!item) return false;
    if (selectedScenario === 'All') return true;
    return item.scenario === selectedScenario || item.scenario === 'Shared';
  });

  // Helper: filter by both group AND scenario (untuk gallery)
  const getFilteredDocs = () => {
    return getScenarioFiltered(getCurrentResults()).filter(item =>
      String(item.group || 'Lain-lain') === selectedGroup
    );
  };

  // Groups yang tersedia sesuai scenario yang dipilih
  const getAvailableGroups = () => {
    const filtered = getScenarioFiltered(getCurrentResults());
    return [...new Set(filtered.map(r => String(r.group || 'Lain-lain')))].sort();
  };

  useEffect(() => {
    // Fetch Last Update (from deployment)
    fetch('/last_update.json')
      .then(res => res.json())
      .then(data => setCurrentTime(data.lastUpdate))
      .catch(() => {
          // Fallback if file not found
          setCurrentTime("Sedang diproses...");
      });
    
    // Fetch Real Gallery
    fetch('/output_real_manifest.json')
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
        setAllResultsReal([...staticItems, ...data]);
      })
      .catch(err => console.error("Failed to load real manifest:", err));

    // Fetch Sample Gallery
    fetch('/output_sample_manifest.json')
      .then(res => res.json())
      .then(data => {
        setAllResultsSample(data);
      })
      .catch(err => console.error("Failed to load sample manifest:", err));

    // Fetch Equations
    fetch('/equations.json')
      .then(res => res.json())
      .then(data => setEquations(data))
      .catch(err => console.error("Failed to load equations:", err));

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
      setPreviousDocsModal(activeModal); // ricorda quale modal era aperta
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

      {compareView ? (
        <CompareDashboard
          onBack={() => setCompareView(false)}
          allResultsReal={allResultsReal}
          allResultsSample={allResultsSample}
        />
      ) : formulasView ? (
        <FormulasDashboard
          onBack={() => setFormulasView(false)}
        />
      ) : (
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

          {/* Documentation Card (Unified) */}
          <div
            className="card glass-effect highlight"
            onClick={() => setCompareView(true)}
          >
            <div className="card-icon">⚔️</div>
            <h2>Dokumentasi & Perbandingan</h2>
            <p>
              Bandingkan hasil Skenario 1 (Kiri) vs Skenario 2 (Kanan) secara interaktif, data deskriptif, dan trajektori.
            </p>
          </div>

          {/* Formulas Card */}
          <div
            className="card glass-effect"
            onClick={() => setFormulasView(true)}
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
      )}

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
        className={`modal ${activeModal === 'docs-real' || activeModal === 'docs-sample' ? 'active' : ''}`}
        onClick={(e) => {
          if (e.target.classList.contains('modal')) closeModal();
        }}
      >
        <div className="modal-content glass-effect" style={{ maxWidth: '1000px', width: '95vw' }}>
          <button className="close-btn" onClick={closeModal} title="Tutup">
            &times;
          </button>
          <h2>Dokumentasi & Hasil Analisis {activeModal === 'docs-sample' ? '(Sample N=4)' : '(Real N=41)'}</h2>
          <div className="modal-body">
            <p style={{ marginBottom: '1.2rem' }}>
              Hasil pengolahan data STATIS, K-Means Clustering, dan Analisis Vektor Struktur yang dihasilkan secara otomatis oleh sistem.
            </p>

            {/* Real vs Sample Dataset Segment Selector Toggle */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '1.5rem', background: 'rgba(0,0,0,0.3)', padding: '5px', borderRadius: '30px', width: 'fit-content', border: '1px solid rgba(255,255,255,0.05)' }}>
              <button
                onClick={() => {
                  setActiveModal('docs-real');
                  setSelectedScenario('Shared');
                  setSelectedGroup('Highlights');
                }}
                style={{
                  padding: '6px 16px', borderRadius: '20px', cursor: 'pointer', border: 'none',
                  background: activeModal === 'docs-real' ? 'linear-gradient(to right, #3b82f6, #8b5cf6)' : 'transparent',
                  color: activeModal === 'docs-real' ? '#fff' : '#94a3b8',
                  fontWeight: '600', fontSize: '0.8rem', transition: 'all 0.3s'
                }}
              >
                📊 Data Riil (N=41)
              </button>
              <button
                onClick={() => {
                  setActiveModal('docs-sample');
                  setSelectedScenario('Shared');
                  setSelectedGroup('Shared');
                }}
                style={{
                  padding: '6px 16px', borderRadius: '20px', cursor: 'pointer', border: 'none',
                  background: activeModal === 'docs-sample' ? 'linear-gradient(to right, #3b82f6, #8b5cf6)' : 'transparent',
                  color: activeModal === 'docs-sample' ? '#fff' : '#94a3b8',
                  fontWeight: '600', fontSize: '0.8rem', transition: 'all 0.3s'
                }}
              >
                📈 Data Contoh (N=4)
              </button>
            </div>

            {/* Scenario Filter */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '14px', flexWrap: 'wrap' }}>
              {[
                { key: 'Shared',     label: '🔗 Shared (Root)', desc: 'Berlaku di kedua skenario' },
                { key: 'Scenario 1', label: '1️⃣ Skenario 1 (ACT)', desc: 'Host = Wilayah' },
                { key: 'Scenario 2', label: '2️⃣ Skenario 2 (Dual)', desc: 'Host = Indikator' },
                { key: 'All',        label: '📂 Semua', desc: 'Tanpa duplikat' },
              ].map(({ key, label, desc }) => (
                <button
                  key={key}
                  onClick={() => {
                    const allRes = getCurrentResults() || [];
                    const newFiltered = allRes.filter(i => !i ? false : key === 'All' ? true : i.scenario === key || i.scenario === 'Shared');
                    const uniq = [...new Set(newFiltered.map(r => String(r.group || 'Lain-lain')))].sort();
                    setSelectedScenario(key);
                    if (uniq.length > 0 && !uniq.includes(selectedGroup)) setSelectedGroup(uniq[0]);
                  }}
                  title={desc}
                  style={{
                    padding: '7px 14px', borderRadius: '20px', cursor: 'pointer',
                    border: selectedScenario === key ? '2px solid #60a5fa' : '1px solid rgba(255,255,255,0.2)',
                    background: selectedScenario === key ? 'rgba(59,130,246,0.3)' : 'rgba(255,255,255,0.05)',
                    color: selectedScenario === key ? '#60a5fa' : '#94a3b8',
                    fontWeight: selectedScenario === key ? '700' : '400',
                    fontSize: '0.85rem', transition: 'all 0.2s'
                  }}
                >{label}</button>
              ))}
            </div>

            {/* Group Selector Tags */}
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '14px' }}>
              {getAvailableGroups().map(group => (
                <button
                  key={group}
                  onClick={() => setSelectedGroup(group)}
                  style={{
                    padding: '5px 12px', borderRadius: '16px', cursor: 'pointer',
                    border: '1px solid rgba(255,255,255,0.15)',
                    background: selectedGroup === group ? 'rgba(99,102,241,0.5)' : 'rgba(255,255,255,0.04)',
                    color: selectedGroup === group ? '#c7d2fe' : '#94a3b8',
                    fontWeight: selectedGroup === group ? '700' : '400',
                    fontSize: '0.78rem', transition: 'all 0.2s'
                  }}
                >{group}</button>
              ))}
            </div>

            {/* Item count */}
            <div style={{ fontSize: '0.78rem', color: '#64748b', marginBottom: '10px' }}>
              Menampilkan <b style={{color:'#94a3b8'}}>{getFilteredDocs().length}</b> item
              {selectedScenario !== 'All' && <span> · <span style={{color:'#60a5fa'}}>{selectedScenario}</span></span>}
              {selectedGroup && <span> · <span style={{color:'#a5b4fc'}}>{selectedGroup}</span></span>}
            </div>

            <div className="photo-grid" style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fill, minmax(185px, 1fr))', 
              gap: '16px',
              maxHeight: '58vh',
              overflowY: 'auto',
              paddingRight: '8px'
            }}>
              {getFilteredDocs().map((item, index) => (
                <div
                  key={index}
                  className="thumbnail-container"
                  onClick={() => item && item.type === 'image' ? (setLightboxImage(item), setCurrentGalleryIndex(index)) : openTexPreview(item.src, index)}
                  style={{ transition: 'transform 0.2s', cursor: 'pointer', position: 'relative' }}
                >
                  {/* Scenario badge */}
                  {selectedScenario === 'All' && item.scenario && (
                    <div style={{
                      position: 'absolute', top: '6px', left: '6px', zIndex: 2,
                      fontSize: '0.6rem', fontWeight: '700', padding: '2px 6px',
                      borderRadius: '8px', backdropFilter: 'blur(4px)',
                      background: item.scenario === 'Shared' ? 'rgba(16,185,129,0.7)'
                                : item.scenario === 'Scenario 1' ? 'rgba(59,130,246,0.7)'
                                : 'rgba(168,85,247,0.7)',
                      color: 'white'
                    }}>
                      {item.scenario === 'Shared' ? 'Shared' : item.scenario === 'Scenario 1' ? 'S1' : 'S2'}
                    </div>
                  )}
                  {item && item.type === 'image' ? (
                    <img src={item.src} alt={String(item.caption || '')} className="thumbnail-img"
                      style={{ width: '100%', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)', display: 'block' }} />
                  ) : (
                    <div style={{ 
                      width: '100%', aspectRatio: '3/2', background: 'rgba(15,23,42,0.6)',
                      display: 'flex', flexDirection: 'column', alignItems: 'center',
                      justifyContent: 'center', borderRadius: '8px',
                      border: '1px solid rgba(255,255,255,0.15)', padding: '10px', textAlign: 'center'
                    }}>
                      <div style={{ fontSize: '1.8rem', marginBottom: '6px' }}>📄</div>
                      <div style={{ fontSize: '0.68rem', fontWeight: '700', color: '#60a5fa', lineHeight: 1.3 }}>
                        {String(item ? (item.name || item.caption) : '')}
                      </div>
                    </div>
                  )}
                  <div style={{ marginTop: '6px', fontSize: '0.72rem', textAlign: 'center', color: '#94a3b8', lineHeight: 1.3 }}>
                    {String((item ? item.caption : '') || '')}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div
        className={`modal ${activeModal === 'tex-preview' ? 'active' : ''}`}
        onClick={(e) => {
          // It was opening 'docs', but now we need to track WHICH docs modal was open
          // Since activeModal is 'tex-preview', we can't easily know if it came from real or sample
          // unless we add a state. Let's just default to docs-real, or we could add a state `previousModal`.
          // For simplicity, we just check if it was sample. Let's just always close the modal entirely on background click for safety.
          if (e.target.classList.contains('modal')) closeModal();
        }}
      >
        <div className="modal-content glass-effect" style={{ maxWidth: '1000px', width: '95vw', height: '90vh', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '1rem' }}>
            <button 
              className="back-lib-btn" 
              onClick={() => { closeModal(); }}
              style={{ background: 'rgba(255,255,255,0.1)', border: 'none', color: '#60a5fa', padding: '6px 12px', borderRadius: '6px', cursor: 'pointer', fontSize: '0.8rem', fontWeight: 'bold' }}
            >
              ⬅ Tutup Visualisasi
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

      <div
        className={`lightbox ${lightboxImage ? 'active' : ''}`}
        onClick={() => { setLightboxImage(null); }}
      >
        {lightboxImage && (
          <>
            <button className="close-btn" onClick={() => { setLightboxImage(null); }} style={{ top: '2rem', right: '2rem' }}>
              &times;
            </button>
            
            <div className="lightbox-nav-top" style={{ position: 'fixed', top: '2rem', left: '50%', transform: 'translateX(-50%)', display: 'flex', gap: '20px', zIndex: 2001 }}>
               <button className="pdf-btn" onClick={(e) => { e.stopPropagation(); navigateGallery(-1); }}>⬅ Sebelumnya</button>
               <button className="pdf-btn" onClick={(e) => { e.stopPropagation(); navigateGallery(1); }}>Selanjutnya ➡</button>
            </div>

            <img src={lightboxImage.src} alt={lightboxImage.caption} onClick={(e) => e.stopPropagation()} />
            <div className="lightbox-caption">{lightboxImage.caption}</div>
            
            <button 
              onClick={(e) => { e.stopPropagation(); setLightboxImage(null); }}
              style={{ position: 'fixed', bottom: '2rem', background: 'rgba(59, 130, 246, 0.5)', color: 'white', border: 'none', padding: '10px 20px', borderRadius: '30px', cursor: 'pointer', backdropFilter: 'blur(5px)' }}
            >
              Tutup Gambar
            </button>
          </>
        )}
      </div>

      {/* formulas modal removed — FormulasDashboard is rendered natively via formulasView state */}

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
