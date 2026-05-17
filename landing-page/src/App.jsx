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
    <div className="compare-card card" style={{ background: 'rgba(30, 41, 59, 0.4)', borderRadius: '20px', padding: '24px', marginBottom: '24px', border: '1px solid rgba(255,255,255,0.06)' }}>
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
          <div>
            <div style={{ fontWeight: '600', color: '#06B6D4', fontSize: '0.75rem', marginBottom: '10px', letterSpacing: '0.5px', textTransform: 'uppercase' }}>SKENARIO 1 (ACT KLASIK - HOST WILAYAH / MATRIKS W)</div>
            {hasLeft ? <LatexTable tex={leftTex} /> : <div className="placeholder-box" style={{ padding: '20px', background: 'rgba(0,0,0,0.2)', borderRadius: '12px', textAlign: 'center', color: '#64748b' }}>File tidak tersedia di Skenario 1</div>}
          </div>
          {/* Right: Scenario 2 */}
          <div>
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
    <div className="card" style={{ background: 'rgba(30, 41, 59, 0.3)', borderRadius: '20px', padding: '20px', border: '1px solid rgba(255,255,255,0.05)' }}>
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
    <div className="compare-card card" style={{ background: 'rgba(30, 41, 59, 0.4)', borderRadius: '20px', padding: '24px', marginBottom: '24px', border: '1px solid rgba(255,255,255,0.06)' }}>
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

  const currentResults = selectedFolder === 'output_sample' ? allResultsSample : allResultsReal;

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
              marginBottom: '14px',
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
        <div className="card" style={{ background: 'rgba(30, 41, 59, 0.25)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px', padding: '0', overflow: 'hidden' }}>
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
                    <div key={img.name} className="card" style={{ background: 'rgba(30, 41, 59, 0.3)', borderRadius: '20px', padding: '16px', border: '1px solid rgba(255,255,255,0.05)' }}>
                      <h5 style={{ fontSize: '13px', color: '#94A3B8', margin: '0 0 12px 0', textAlign: 'center', textTransform: 'uppercase' }}>{img.name.replace(/_/g, ' ').replace('.png', '')}</h5>
                      <div className="img-container" style={{ display: 'flex', justifyContent: 'center', background: 'rgba(15,23,42,0.4)', borderRadius: '12px', padding: '10px' }}>
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
        <div className="card" style={{ background: 'rgba(30, 41, 59, 0.25)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px', padding: '0', overflow: 'hidden' }}>
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


function App() {
  const [activeModal, setActiveModal] = useState(null);
  const [compareView, setCompareView] = useState(false);
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
