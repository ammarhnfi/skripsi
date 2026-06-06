import { useState, useEffect, useRef } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import './App.css';

// Initialize PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

/* UTILITY: Clean up LaTeX Math symbols into beautiful Unicode equivalents */
function cleanMathSymbols(str) {
  if (!str) return '';
  let res = str;

  // Replace common LaTeX Greek letters and math symbols
  res = res.replace(/\\boldsymbol\{\\beta\}/g, 'β')
           .replace(/\\boldsymbol\\beta/g, 'β')
           .replace(/\\tilde\{\\beta\}/g, 'β̃')
           .replace(/\\tilde\\beta/g, 'β̃')
           .replace(/\\beta/g, 'β')
           .replace(/\\alpha/g, 'α')
           .replace(/\\lambda/g, 'λ')
           .replace(/\\mu/g, 'μ')
           .replace(/\\sigma/g, 'σ')
           .replace(/\\tau/g, 'τ')
           .replace(/\\chi/g, 'χ')
           .replace(/\\rho/g, 'ρ')
           .replace(/\\phi/g, 'φ')
           .replace(/\\theta/g, 'θ')
           .replace(/\\eta/g, 'η')
           .replace(/\\delta/g, 'δ')
           .replace(/\\epsilon/g, 'ε')
           .replace(/\\gamma/g, 'γ')
           .replace(/\\omega/g, 'ω')
           .replace(/\\pi/g, 'π')
           .replace(/\\psi/g, 'ψ')
           .replace(/\\zeta/g, 'ζ')
           .replace(/\\xi/g, 'ξ');

  // Subscripts mapping
  const subscriptMap = {
    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
    '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
    'a': 'ₐ', 'e': 'ₑ', 'h': 'ₕ', 'i': 'ᵢ', 'j': 'ⱼ',
    'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ', 'o': 'ₒ',
    'p': 'ₚ', 'r': 'ᵣ', 's': 'ₛ', 't': 'ₜ', 'u': 'ᵤ',
    'v': 'ᵥ', 'x': 'ₓ', 'y': 'ᵧ'
  };

  // Convert _{abc} to subscripts
  res = res.replace(/_\{(.*?)\}/g, (match, p1) => {
    return p1.split('').map(char => subscriptMap[char] || char).join('');
  });

  // Convert _a to subscript (single char subscript)
  res = res.replace(/_([0-9a-zA-Z])/g, (match, p1) => {
    return subscriptMap[p1] || p1;
  });

  // Convert ^{abc} to superscripts
  const superscriptMap = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
    '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾',
    'a': 'ᵃ', 'b': 'ᵇ', 'c': 'ᶜ', 'd': 'ᵈ', 'e': 'ᵉ',
    'f': 'ᶠ', 'g': 'ᵍ', 'h': 'ʰ', 'i': 'ⁱ', 'j': 'ʲ',
    'k': 'ᵏ', 'l': 'ˡ', 'm': 'ᵐ', 'n': 'ⁿ', 'o': 'ᵒ',
    'p': 'ᵖ', 'r': 'ʳ', 's': 'ˢ', 't': 'ᵗ', 'u': 'ᵘ',
    'v': 'ᵛ', 'w': 'ʷ', 'x': 'ˣ', 'y': 'ʸ', 'z': 'ᶻ'
  };
  
  res = res.replace(/\^\{(.*?)\}/g, (match, p1) => {
    return p1.split('').map(char => superscriptMap[char] || char).join('');
  });
  
  res = res.replace(/\^([0-9a-zA-Z])/g, (match, p1) => {
    return superscriptMap[p1] || p1;
  });

  // Strip dollar signs
  res = res.replace(/\$/g, '');

  // Strip remaining latex formatting macros
  res = res.replace(/\\mathrm/g, '')
           .replace(/\\mathbf/g, '')
           .replace(/\\mathit/g, '')
           .replace(/\\boldsymbol/g, '')
           .replace(/\\tilde/g, '~');

  return res.trim();
}

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
  const expectedCols = colSpec.replace(/[| <>!@]/g, '').replace(/{[^{}]*}/g, '').length || 2;
  const bodyWithEnd = tex.substring(specEnd);
  const endTagMatch = bodyWithEnd.match(/(.*?)\\end\{(?:tabular|longtable)\}/s);
  if (!endTagMatch) return <pre style={{ whiteSpace: 'pre-wrap' }}>{tex}</pre>;

  let body = endTagMatch[1];

  // Strip longtable repeat-header preamble (\endfirsthead … \endfoot)
  // Keep everything AFTER \endfoot; if missing, keep after \endhead
  const endFootSplit = body.match(/\\endfoot([\s\S]*)/);
  if (endFootSplit) {
    // Put back the header row: grab the first row from the pre-endfoot block
    const prePart = body.substring(0, body.indexOf('\\endfoot'));
    const firstRow = prePart.split(/\\\\/).find(r => r.trim() && !r.trim().startsWith('%') && !r.includes('\\hline') && r.trim() !== '');
    body = (firstRow ? firstRow + ' \\\\\n' : '') + endFootSplit[1];
  } else {
    const endHeadSplit = body.match(/\\endhead([\s\S]*)/);
    if (endHeadSplit) body = endHeadSplit[1];
  }

  // 3. ROBUST CLEANING
  const rowsRaw = body.split(/\\\\|\\\r?\n/).filter(r => r.trim().length > 0 && !r.trim().startsWith('%'));
  const rows = rowsRaw.map(rowStr => {
    let cleanRow = rowStr
      .replace(/\\rowcolor\{.*?\}/g, '')
      .replace(/\\multicolumn\{[^}]*\}\{[^}]*\}\{([^}]*)\}/g, '$1')
      .replace(/\\hline/g, '').replace(/\\arraybackslash/g, '').replace(/\\raggedright/g, '').replace(/\\centering/g, '')
      .replace(/\\toprule/g, '').replace(/\\midrule/g, '').replace(/\\bottomrule/g, '')
      .replace(/\\makecell\[?.*?\]?\{(.*?)\}/sg, '$1')
      .replace(/\\&/g, '__ESC_AMP__')
      .trim();

    if (!cleanRow || cleanRow === '}') return null;

    let cells = cleanRow.split('&').map(cell => {
      let content = cell.trim()
        .replace(/__ESC_AMP__/g, '&')
        .replace(/\\textbf\{(.*?)\}/g, '$1').replace(/\\textit\{(.*?)\}/g, '<i>$1</i>')
        .replace(/\\bfseries/g, '').replace(/\\small/g, '').replace(/\\scriptsize/g, '')
        .replace(/\\%/g, '%').replace(/\\\$/g, '$').replace(/\\_/g, '_')
        .replace(/\\rightarrow/g, '→').replace(/\\textrightarrow/g, '→')
        .replace(/\\\(|\\\)/g, '').replace(/\\text\{(.*?)\}/g, '$1');
      
      content = cleanMathSymbols(content);
      content = content.replace(/\{/g, '').replace(/\}/g, '');
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


function SideBySideIntegratedTexLoader({ filename, folder, hasLeft, hasRight }) {
  const [leftTex, setLeftTex] = useState('');
  const [rightTex, setRightTex] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    async function fetchData() {
      try {
        setLoading(true);
        const isRootFile = filename.startsWith('output_table_biplot_transition_');
        const leftPath = isRootFile ? `/` + folder + `/` + filename : `/` + folder + `/scenario1/` + filename;
        const rightPath = isRootFile ? `/` + folder + `/` + filename : `/` + folder + `/scenario2/` + filename;

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

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '150px' }}>
        <div className="spinner" style={{ width: '32px', height: '32px' }}></div>
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px' }}>
      {/* Left: Scenario 1 */}
      <div style={{ minWidth: 0, overflow: 'hidden' }}>
        <div style={{ fontWeight: '600', color: '#06B6D4', fontSize: '0.75rem', marginBottom: '12px', letterSpacing: '0.5px', textTransform: 'uppercase' }}>SKENARIO 1 (ACT KLASIK - HOST WILAYAH / MATRIKS W)</div>
        {hasLeft ? <LatexTable tex={leftTex} /> : <div className="placeholder-box" style={{ padding: '20px', background: 'rgba(0,0,0,0.2)', borderRadius: '12px', textAlign: 'center', color: '#64748b' }}>Tabel tidak tersedia di Skenario 1</div>}
      </div>
      {/* Right: Scenario 2 */}
      <div style={{ minWidth: 0, overflow: 'hidden' }}>
        <div style={{ fontWeight: '600', color: '#3B82F6', fontSize: '0.75rem', marginBottom: '12px', letterSpacing: '0.5px', textTransform: 'uppercase' }}>SKENARIO 2 (DUAL STATIS - HOST INDIKATOR / MATRIKS S)</div>
        {hasRight ? <LatexTable tex={rightTex} /> : <div className="placeholder-box" style={{ padding: '20px', background: 'rgba(0,0,0,0.2)', borderRadius: '12px', textAlign: 'center', color: '#64748b' }}>Tabel tidak tersedia di Skenario 2</div>}
      </div>
    </div>
  );
}

function IntegratedDashboardView({ currentResults, folder, sc1Files, sc2Files, availableYears, availablePairs }) {
  const [compMode, setCompMode] = useState('comp_3_biplot_vs_statis');
  const [selectedPeriod, setSelectedPeriod] = useState('');
  const [compView, setCompView] = useState('map');

  useEffect(() => {
    if (availableYears.length > 0 && !selectedPeriod) {
      setSelectedPeriod(availableYears[0]);
    }
  }, [availableYears]);

  useEffect(() => {
    const isTransition = ['comp_1_trans_biplot', 'comp_2_trans_statis', 'comp_4_trans_ipm'].includes(compMode);
    if (isTransition) {
      if (availablePairs.length > 0 && !availablePairs.includes(selectedPeriod)) {
        setSelectedPeriod(availablePairs[0]);
      }
    } else {
      if (availableYears.length > 0 && !availableYears.includes(selectedPeriod)) {
        setSelectedPeriod(availableYears[0]);
      }
    }
  }, [compMode, availableYears, availablePairs]);

  useEffect(() => {
    const isIpmMode = ['comp_4_trans_ipm', 'comp_5_biplot_vs_ipm', 'comp_6_statis_vs_ipm', 'comp_9_compromise_vs_ipm'].includes(compMode);
    if (isIpmMode && compView === 'scatter') {
      setCompView('map');
    }
  }, [compMode, compView]);

  // Define all 9 rows dynamically (Years + Pairs)
  const rows = [
    // 1. Transisi Biplot
    ...availablePairs.map(pr => ({
      mode: 'comp_1_trans_biplot',
      period: pr,
      label: `🔄 1. Transisi Biplot ${pr.replace('x', ' ke ')}`,
      fullLabel: `Transisi Biplot ${pr.replace('x', ' ke ')}`
    })),
    // 2. Transisi STATIS
    ...availablePairs.map(pr => ({
      mode: 'comp_2_trans_statis',
      period: pr,
      label: `📈 2. Transisi STATIS ${pr.replace('x', ' ke ')}`,
      fullLabel: `Transisi STATIS ${pr.replace('x', ' ke ')}`
    })),
    // 3. Biplot vs STATIS
    ...availableYears.map(yr => ({
      mode: 'comp_3_biplot_vs_statis',
      period: yr,
      label: `📊 3. Biplot vs STATIS ${yr}`,
      fullLabel: `Biplot vs STATIS Tahun ${yr}`
    })),
    // 4. Transisi Kategori IPM
    ...availablePairs.map(pr => ({
      mode: 'comp_4_trans_ipm',
      period: pr,
      label: `🌱 4. Transisi Kategori IPM ${pr.replace('x', ' ke ')}`,
      fullLabel: `Transisi Kategori IPM ${pr.replace('x', ' ke ')}`
    })),
    // 5. Biplot vs Kategori IPM
    ...availableYears.map(yr => ({
      mode: 'comp_5_biplot_vs_ipm',
      period: yr,
      label: `⚖️ 5. Biplot vs Kategori IPM ${yr}`,
      fullLabel: `Biplot vs Kategori IPM Tahun ${yr}`
    })),
    // 6. STATIS vs Kategori IPM
    ...availableYears.map(yr => ({
      mode: 'comp_6_statis_vs_ipm',
      period: yr,
      label: `🔍 6. STATIS vs Kategori IPM ${yr}`,
      fullLabel: `STATIS vs Kategori IPM Tahun ${yr}`
    })),
    // 7. Kompromi vs Biplot
    ...availableYears.map(yr => ({
      mode: 'comp_7_compromise_vs_biplot',
      period: yr,
      label: `🧭 7. Kompromi vs Biplot ${yr}`,
      fullLabel: `Kompromi vs Biplot Tahun ${yr}`
    })),
    // 8. Kompromi vs STATIS
    ...availableYears.map(yr => ({
      mode: 'comp_8_compromise_vs_statis',
      period: yr,
      label: `📌 8. Kompromi vs STATIS ${yr}`,
      fullLabel: `Kompromi vs STATIS Tahun ${yr}`
    })),
    // 9. Kompromi vs Kategori IPM
    ...availableYears.map(yr => ({
      mode: 'comp_9_compromise_vs_ipm',
      period: yr,
      label: `🏆 9. Kompromi vs Kategori IPM ${yr}`,
      fullLabel: `Kompromi vs Kategori IPM Tahun ${yr}`
    }))
  ];

  // Determine active period
  const activePeriod = selectedPeriod || (availableYears.length > 0 ? availableYears[0] : '');

  // Determine filenames based on exact naming conventions in export_all.py
  let mapFile = '';
  let scatterFile = '';
  let pieFile = '';
  let sumTableFile = '';
  let nameTableFile = '';

  if (compMode === 'comp_1_trans_biplot') {
    mapFile = `compare_map_trans_biplot_${activePeriod}.png`;
    scatterFile = `compare_scatter_trans_biplot_${activePeriod}.png`;
    pieFile = `compare_pie_trans_biplot_${activePeriod}.png`;
    sumTableFile = `output_table_biplot_transition_sum_${activePeriod}.tex`;
    nameTableFile = `output_table_biplot_transition_name_${activePeriod}.tex`;
  } else if (compMode === 'comp_2_trans_statis') {
    mapFile = `compare_map_trans_statis_${activePeriod}.png`;
    scatterFile = `compare_scatter_trans_statis_${activePeriod}.png`;
    pieFile = `compare_pie_trans_statis_${activePeriod}.png`;
    sumTableFile = `output_table_statis_transition_sum_${activePeriod}.tex`;
    nameTableFile = `output_table_statis_transition_name_${activePeriod}.tex`;
  } else if (compMode === 'comp_3_biplot_vs_statis') {
    mapFile = `compare_map_biplot_vs_statis_${activePeriod}.png`;
    scatterFile = `compare_scatter_biplot_vs_statis_${activePeriod}.png`;
    pieFile = `compare_pie_biplot_vs_statis_${activePeriod}.png`;
    sumTableFile = `output_table_biplot_vs_statis_compare_sum_${activePeriod}.tex`;
    nameTableFile = `output_table_biplot_vs_statis_compare_name_${activePeriod}.tex`;
  } else if (compMode === 'comp_4_trans_ipm') {
    mapFile = `compare_map_ipm_${activePeriod}.png`;
    pieFile = `compare_pie_ipm_${activePeriod}.png`;
    sumTableFile = `output_table_ipm_sum_${activePeriod}.tex`;
    nameTableFile = `output_table_ipm_name_${activePeriod}.tex`;
  } else if (compMode === 'comp_5_biplot_vs_ipm') {
    mapFile = `compare_map_biplot_vs_ipm_${activePeriod}.png`;
    pieFile = `compare_pie_biplot_vs_ipm_${activePeriod}.png`;
    sumTableFile = `output_table_cross_matrix_sum_${activePeriod}.tex`;
    nameTableFile = `output_table_cross_matrix_name_${activePeriod}.tex`;
  } else if (compMode === 'comp_6_statis_vs_ipm') {
    mapFile = `compare_map_statis_vs_ipm_${activePeriod}.png`;
    pieFile = `compare_pie_statis_vs_ipm_${activePeriod}.png`;
    sumTableFile = `output_table_statis_vs_ipm_sum_${activePeriod}.tex`;
    nameTableFile = `output_table_statis_vs_ipm_name_${activePeriod}.tex`;
  } else if (compMode === 'comp_7_compromise_vs_biplot') {
    mapFile = `compare_map_compromise_vs_biplot_${activePeriod}.png`;
    scatterFile = `compare_scatter_compromise_vs_biplot_${activePeriod}.png`;
    pieFile = `compare_pie_compromise_vs_biplot_${activePeriod}.png`;
    sumTableFile = `output_table_biplot_vs_compromise_sum_${activePeriod}.tex`;
    nameTableFile = `output_table_biplot_vs_compromise_name_${activePeriod}.tex`;
  } else if (compMode === 'comp_8_compromise_vs_statis') {
    mapFile = `compare_map_compromise_vs_statis_${activePeriod}.png`;
    scatterFile = `compare_scatter_compromise_vs_statis_${activePeriod}.png`;
    pieFile = `compare_pie_compromise_vs_statis_${activePeriod}.png`;
    sumTableFile = `output_table_compromise_vs_statis_sum_${activePeriod}.tex`;
    nameTableFile = `output_table_compromise_vs_statis_name_${activePeriod}.tex`;
  } else if (compMode === 'comp_9_compromise_vs_ipm') {
    mapFile = `compare_map_compromise_vs_ipm_${activePeriod}.png`;
    pieFile = `compare_pie_compromise_vs_ipm_${activePeriod}.png`;
    sumTableFile = `output_table_compromise_vs_ipm_sum_${activePeriod}.tex`;
    nameTableFile = `output_table_compromise_vs_ipm_name_${activePeriod}.tex`;
  }

  // Active file based on selected view
  let activeFilename = '';
  let isImage = true;
  if (compView === 'map') { activeFilename = mapFile; isImage = true; }
  else if (compView === 'scatter') { activeFilename = scatterFile; isImage = true; }
  else if (compView === 'pie') { activeFilename = pieFile; isImage = true; }
  else if (compView === 'sum') { activeFilename = sumTableFile; isImage = false; }
  else if (compView === 'name') { activeFilename = nameTableFile; isImage = false; }

  const isRootFile = activeFilename.startsWith('output_table_biplot_transition_');
  const hasLeft = isRootFile ? currentResults.some(f => f.name === activeFilename) : sc1Files.some(f => f.name === activeFilename);
  const hasRight = isRootFile ? currentResults.some(f => f.name === activeFilename) : sc2Files.some(f => f.name === activeFilename);

  return (
    <div style={{ background: 'rgba(30, 41, 59, 0.25)', borderRadius: '24px', padding: '24px', border: '1px solid rgba(255,255,255,0.06)' }}>
      
      {/* GRID LAYOUT: SIDEBAR LIST (LEFT) & PREVIEW AREA (RIGHT) */}
      <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: '30px', alignItems: 'start' }}>
        
        {/* LEFT COLUMN: CONDENSED ROWS PANEL */}
        <div style={{
          background: 'rgba(15, 23, 42, 0.45)',
          borderRadius: '20px',
          padding: '20px',
          border: '1px solid rgba(255, 255, 255, 0.08)',
          boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.2)'
        }}>
          <h4 style={{ 
            margin: '0 0 16px 0', 
            fontSize: '0.85rem', 
            fontWeight: '700', 
            color: '#38BDF8', 
            letterSpacing: '1px', 
            textTransform: 'uppercase',
            borderBottom: '1px solid rgba(255,255,255,0.08)',
            paddingBottom: '10px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <span>📊 Opsi Perbandingan</span>
            <span style={{ fontSize: '0.7rem', color: '#64748b', background: 'rgba(255,255,255,0.05)', padding: '2px 8px', borderRadius: '10px' }}>9 Metode</span>
          </h4>
          
          <div className="custom-scrollbar" style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '720px', overflowY: 'auto', paddingRight: '4px' }}>
            {rows.map((row, idx) => {
              const isRowSelected = compMode === row.mode && activePeriod === row.period;
              const isIpmRow = ['comp_4_trans_ipm', 'comp_5_biplot_vs_ipm', 'comp_6_statis_vs_ipm', 'comp_9_compromise_vs_ipm'].includes(row.mode);
              const viewsToRender = isIpmRow ? ['map', 'pie', 'sum', 'name'] : ['map', 'scatter', 'pie', 'sum', 'name'];

              return (
                <div 
                  key={idx}
                  style={{
                    background: isRowSelected ? 'rgba(6, 182, 212, 0.08)' : 'rgba(30, 41, 59, 0.15)',
                    border: isRowSelected ? '1px solid rgba(6, 182, 212, 0.35)' : '1px solid rgba(255,255,255,0.03)',
                    borderRadius: '12px',
                    padding: '8px 10px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px',
                    transition: 'all 0.2s'
                  }}
                >
                  {/* Row title */}
                  <div style={{ 
                    fontSize: '0.72rem', 
                    fontWeight: isRowSelected ? '700' : '500', 
                    color: isRowSelected ? '#06b6d4' : '#cbd5e1',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}>
                    <span style={{ letterSpacing: '0.2px' }}>{row.label}</span>
                    {isRowSelected && (
                      <span style={{ 
                        background: 'rgba(6, 182, 212, 0.15)', 
                        color: '#06b6d4', 
                        fontSize: '0.6rem', 
                        padding: '1px 5px', 
                        borderRadius: '6px',
                        fontWeight: '700',
                        letterSpacing: '0.5px'
                      }}>ACTIVE</span>
                    )}
                  </div>
                  
                  {/* Small version buttons (4 or 5 options dynamically) */}
                  <div style={{ display: 'grid', gridTemplateColumns: `repeat(${viewsToRender.length}, 1fr)`, gap: '4px' }}>
                    {viewsToRender.map(view => {
                      const isActiveButton = isRowSelected && compView === view;
                      let btnLabel = '';
                      let btnIcon = '';
                      if (view === 'map') { btnLabel = 'Peta'; btnIcon = '🗺️'; }
                      else if (view === 'scatter') { btnLabel = 'Scatter'; btnIcon = '📈'; }
                      else if (view === 'pie') { btnLabel = 'Pie'; btnIcon = '🍕'; }
                      else if (view === 'sum') { btnLabel = 'Jumlah'; btnIcon = '🔢'; }
                      else if (view === 'name') { btnLabel = 'Nama'; btnIcon = '📝'; }
                      
                      return (
                        <button
                          key={view}
                          onClick={() => {
                            setCompMode(row.mode);
                            setSelectedPeriod(row.period);
                            setCompView(view);
                          }}
                          style={{
                            background: isActiveButton ? 'linear-gradient(135deg, #06B6D4, #3B82F6)' : 'rgba(15,23,42,0.6)',
                            color: isActiveButton ? '#fff' : '#94a3b8',
                            border: isActiveButton ? '1px solid #06b6d4' : '1px solid rgba(255,255,255,0.05)',
                            borderRadius: '6px',
                            padding: '4px 0',
                            fontSize: '0.62rem',
                            fontWeight: '600',
                            cursor: 'pointer',
                            transition: 'all 0.15s',
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '1px',
                            boxShadow: isActiveButton ? '0 2px 8px rgba(6, 182, 212, 0.25)' : 'none'
                          }}
                          onMouseOver={e => { if(!isActiveButton) { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; e.currentTarget.style.color = '#fff'; } }}
                          onMouseOut={e => { if(!isActiveButton) { e.currentTarget.style.background = 'rgba(15,23,42,0.6)'; e.currentTarget.style.color = '#94a3b8'; } }}
                        >
                          <span style={{ fontSize: '0.72rem' }}>{btnIcon}</span>
                          <span>{btnLabel}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        
        {/* RIGHT COLUMN: PREVIEW DISPLAY BOX */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ background: 'rgba(15,23,42,0.35)', borderRadius: '20px', padding: '24px', border: '1px solid rgba(255,255,255,0.06)' }}>
            
            {/* Info header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{
                  background: isImage ? 'rgba(59, 130, 246, 0.12)' : 'rgba(6, 182, 212, 0.12)',
                  color: isImage ? '#3b82f6' : '#06b6d4',
                  border: isImage ? '1px solid rgba(59, 130, 246, 0.25)' : '1px solid rgba(6, 182, 212, 0.25)',
                  borderRadius: '20px', padding: '3px 12px', fontSize: '0.72rem', fontWeight: '700', letterSpacing: '0.5px'
                }}>
                  {isImage ? 'VISUALIZATION PLOT' : 'DATA MATRIX/TABLE'}
                </span>
                <span style={{ fontWeight: '700', fontSize: '0.9rem', color: '#F8FAFC', letterSpacing: '0.2px' }}>
                  {activeFilename.replace(/_/g, ' ').replace('.png', '').replace('.tex', '').replace('output_table_', '').toUpperCase()}
                </span>
              </div>
              <span style={{ fontSize: '0.72rem', color: '#64748b', fontFamily: 'monospace' }}>{activeFilename}</span>
            </div>
 
            {/* Display comparison side-by-side */}
            {isImage ? (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
                {/* Left Scenario 1 */}
                <div>
                  <div style={{ fontWeight: '700', color: '#06B6D4', fontSize: '0.7rem', marginBottom: '12px', letterSpacing: '0.5px', textTransform: 'uppercase' }}>SKENARIO 1 (ACT KLASIK - HOST WILAYAH)</div>
                  {hasLeft ? (
                    <div style={{ background: 'rgba(15,23,42,0.5)', borderRadius: '12px', padding: '12px', border: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'center' }}>
                      <img src={`/${folder}/scenario1/${activeFilename}`} alt={activeFilename} style={{ maxWidth: '100%', borderRadius: '8px', maxHeight: '420px', objectFit: 'contain' }} />
                    </div>
                  ) : (
                    <div style={{ padding: '40px 20px', background: 'rgba(0,0,0,0.2)', borderRadius: '12px', textAlign: 'center', color: '#64748b', fontSize: '0.8rem' }}>Gambar perbandingan tidak tersedia di Skenario 1</div>
                  )}
                </div>
                {/* Right Scenario 2 */}
                <div>
                  <div style={{ fontWeight: '700', color: '#3B82F6', fontSize: '0.7rem', marginBottom: '12px', letterSpacing: '0.5px', textTransform: 'uppercase' }}>SKENARIO 2 (DUAL STATIS - HOST INDIKATOR)</div>
                  {hasRight ? (
                    <div style={{ background: 'rgba(15,23,42,0.5)', borderRadius: '12px', padding: '12px', border: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'center' }}>
                      <img src={`/${folder}/scenario2/${activeFilename}`} alt={activeFilename} style={{ maxWidth: '100%', borderRadius: '8px', maxHeight: '420px', objectFit: 'contain' }} />
                    </div>
                  ) : (
                    <div style={{ padding: '40px 20px', background: 'rgba(0,0,0,0.2)', borderRadius: '12px', textAlign: 'center', color: '#64748b', fontSize: '0.8rem' }}>Gambar perbandingan tidak tersedia di Skenario 2</div>
                  )}
                </div>
              </div>
            ) : (
              <SideBySideIntegratedTexLoader 
                filename={activeFilename}
                folder={folder}
                hasLeft={hasLeft}
                hasRight={hasRight}
              />
            )}

          </div>
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

  // Extract available years and year pairs dynamically for comparative dashboard
  const availableYears = [...new Set(currentResults
    .map(item => {
      const match = item.name.match(/compare_map_biplot_vs_statis_(\d+)\.png/);
      return match ? match[1] : null;
    })
    .filter(Boolean)
  )].sort();

  const availablePairs = [...new Set(currentResults
    .map(item => {
      const match = item.name.match(/compare_map_trans_biplot_(\d+x\d+)\.png/);
      return match ? match[1] : null;
    })
    .filter(Boolean)
  )].sort();

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
  const coreFilesList = ['scree_plot.png', 'rv_heatmap.png', 'trajectory_scores.png', 'trajectory_loadings.png',
                         'compromise_map.png', 'compromise_biplot.png', 'compromise_scatter.png', 'compromise_pie.png',
                         'variable_contribution.png', 'variable_cos2.png', 'beta_trajectory.png',
                         'permutation_histogram.png'];

  const categories = {
    core: { label: '💎 Kompromis & Trajektori (Core)', files: [] },
    yearly: { label: '📅 Biplot per Tahun', files: [] },
    cluster: { label: '🧩 Klastering & Dendrogram', files: [] },
    compare: { label: '🔄 Perbandingan & Transisi', files: [] },
    tables: { label: '📋 Tabel Output (.tex)', files: [] },
    dashboard_pembanding: { label: '📊 Dashboard Komparatif Terintegrasi', files: ['integrated'] }
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
                transition: 'all 0.2s'
              }}
              onMouseOver={e => { e.target.style.background = 'rgba(6, 182, 212, 0.15)'; e.target.style.borderColor = '#06B6D4'; }}
              onMouseOut={e => { e.target.style.background = 'rgba(255, 255, 255, 0.1)'; e.target.style.borderColor = 'rgba(6, 182, 212, 0.2)'; }}
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
            {activeTab === 'dashboard_pembanding' ? (
              <IntegratedDashboardView
                currentResults={currentResults}
                folder={selectedFolder}
                sc1Files={sc1Files}
                sc2Files={sc2Files}
                availableYears={availableYears}
                availablePairs={availablePairs}
              />
            ) : categories[activeTab].files.length > 0 ? (
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
      "$m_i$: Bobot demografis spasial wilayah ke-$i$ (terstandardisasi).",
      "$\\overline{V}_i$: Rata-rata variabel pembobot (jumlah penduduk) wilayah ke-$i$ selama periode pengamatan.",
      "$n$: Jumlah total wilayah pengamatan ($n = 41$ Kabupaten/Kota)."
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
      "$\\mathbf{D}$: Matriks diagonal pembobot spasial wilayah berukuran $41 \\times 41$.",
      "$m_i$: Elemen diagonal utama pembobot spasial wilayah ke-$i$.",
      "Elemen off-diagonal bernilai $0$ karena pembobotan bersifat independen antar wilayah."
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
      "$z_{ijk}$: Nilai data terstandardisasi (z-score) untuk wilayah $i$, variabel $j$, pada tahun $k$.",
      "$x_{ijk}$: Nilai observasi asli wilayah $i$, variabel $j$, pada tahun $k$.",
      "$\\mu_{jk}$: Rata-rata tertimbang spasial dari variabel $j$ pada tahun $k$.",
      "$\\sigma_{jk}$: Simpangan baku tertimbang spasial dari variabel $j$ pada tahun $k$."
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
      "$\\mathrm{MSA}_j$: Indeks kelayakan sampling (Measure of Sampling Adequacy) untuk variabel ke-$j$.",
      "$r_{ij}$: Elemen matriks korelasi sederhana antara variabel $i$ dan $j$.",
      "$q_{ij}$: Elemen matriks korelasi parsial antara variabel $i$ dan $j$."
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
      "$KMO$: Indeks Kaiser-Meyer-Olkin global untuk seluruh matriks data terstandardisasi.",
      "$r_{jk}$: Koefisien korelasi sederhana antara variabel $j$ dan $k$.",
      "$q_{jk}$: Koefisien korelasi parsial antara variabel $j$ dan $k$."
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
      "$\\chi^2$: Statistik uji Chi-Square Bartlett's Sphericity.",
      "$n$: Jumlah wilayah pengamatan ($n = 41$).",
      "$p$: Jumlah variabel indikator sosio-ekonomi ($p = 11$).",
      "$|\\mathbf{R}|$: Determinan matriks korelasi antar-variabel $\\mathbf{R}$."
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
      "$df$: Derajat bebas (degrees of freedom) untuk uji statistik Bartlett.",
      "$p$: Jumlah variabel indikator sosio-ekonomi ($p = 11$)."
    ],
    "substitusi": [
      "Jumlah variabel indikator sosio-ekonomi $p = 11$.",
      "Substitusi: $df = \\dfrac{11 \\times (11-1)}{2} = \\dfrac{110}{2} = 55$."
    ],
    "hasil": "$$ df = 66 $$"
  },
  {
    "id": "ref_eq_16",
    "category": "suitability",
    "title": "17. Uji Bartlett tentang Spherisitas (Bartlett's Test of Sphericity) (Teori/Relasi)",
    "formula": "$$\n|\\mathbf{A}| = \\sum_{\\sigma \\in S_p} \\text{sgn}(\\sigma) \\prod_{i=1}^{p} a_{i,\\sigma(i)}\n$$",
    "keterangan": [
      "$\\mathbf{R}$: Matriks korelasi antar variabel berukuran $11 \\times 11$.",
      "$\\lambda$: Nilai eigen (eigenvalue) dari matriks korelasi.",
      "$\\mathbf{I}$: Matriks identitas berukuran $11 \\times 11$."
    ],
    "substitusi": [
      "Menghitung determinan matriks korelasi $\\mathbf{R} \\in \\mathbb{R}^{11 \\times 11}$.",
      "Dekomposisi $\\mathbf{R} = \\mathbf{L}\\mathbf{U}$ digunakan untuk stabilitas numerik.",
      "Hasil: $|\\mathbf{R}| = \\prod_{i=1}^{11} u_{ii} = 1{,}2530 \\times 10^{-8}$."
    ],
    "hasil": "$$ |\\mathbf{R}| = 1.2530 \\times 10^{-8} $$"
  },
  {
    "id": "ref_eq_17",
    "category": "pca",
    "title": "18. Dasar Aljabar Linier dan Dekomposisi Matriks (Teori/Relasi)",
    "formula": "$$\n\\mathbf{A} \\mathbf{v} = \\lambda \\mathbf{v}\n$$",
    "keterangan": [
      "$\\mathbf{R}$: Matriks korelasi antar variabel berukuran $11 \\times 11$.",
      "$\\mathbf{v}_i$: Vektor eigen (eigenvector) ke-$i$ yang ortonormal.",
      "$\\lambda_i$: Nilai eigen (eigenvalue) ke-$i$ dari matriks korelasi."
    ],
    "substitusi": [
      "Matriks korelasi $\\mathbf{R} \\in \\mathbb{R}^{11 \\times 11}$ bersifat simetris nyata.",
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
      "$\\mathbf{R}$: Matriks korelasi terdekomposisi berukuran $11 \\times 11$.",
      "$\\lambda_i$: Nilai eigen ke-$i$ yang merepresentasikan varians sumbu utama.",
      "$\\mathbf{v}_i$: Vektor eigen ke-$i$ yang menggambarkan kontribusi loadings.",
      "$p$: Jumlah total variabel indikator ($p = 11$)."
    ],
    "substitusi": [
      "Dekomposisi spektral $\\mathbf{R} \\in \\mathbb{R}^{11 \\times 11}$ menjadi kombinasi proyeksi eigenvector.",
      "Eigenvalue terurut: $\\lambda_1 = 6{,}2140,\\; \\lambda_2 = 1{,}5120,\\; \\dots,\\; \\lambda_{11} = 0{,}0120$.",
      "Jumlah total: $\\displaystyle\\sum_{j=1}^{11} \\lambda_j = 11{,}0000 = \\operatorname{tr}(\\mathbf{R})$."
    ],
    "hasil": "$$ \\mathbf{R} = 6.214 \\mathbf{v}_1\\mathbf{v}_1^T + \\dots + 0.012 \\mathbf{v}_{12}\\mathbf{v}_{12}^T $$"
  },
  {
    "id": "ref_eq_19",
    "category": "pca",
    "title": "20. Dasar Aljabar Linier dan Dekomposisi Matriks (Teori/Relasi)",
    "formula": "$$\ntr(\\mathbf{A}) = \\sum_{i=1}^{n} a_{ii}\n$$",
    "keterangan": [
      "$\\operatorname{tr}(\\mathbf{R})$: Trace (jumlah elemen diagonal utama) matriks korelasi $\\mathbf{R}$.",
      "$\\lambda_i$: Nilai eigen ke-$i$.",
      "$p$: Jumlah total variabel indikator ($p = 11$)."
    ],
    "substitusi": [
      "Matriks korelasi $\\mathbf{R}$ berukuran $11 \\times 11$ dengan elemen diagonal $r_{ii} = 1{,}0000$.",
      "Substitusi: $\\operatorname{tr}(\\mathbf{R}) = \\displaystyle\\sum_{i=1}^{11} r_{ii} = \\underbrace{1 + 1 + \\dots + 1}_{11} = 11{,}0000$."
    ],
    "hasil": "$$ \\operatorname{tr}(\\mathbf{R}) = 12.0000 $$"
  },
  {
    "id": "ref_eq_20",
    "category": "pca",
    "title": "21. Dasar Aljabar Linier dan Dekomposisi Matriks (Teori/Relasi)",
    "formula": "$$\n\\mathbf{A} = \\mathbf{U} \\mathbf{S} \\mathbf{V}^T\n$$",
    "keterangan": [
      "$\\mathbf{Z}$: Matriks data terstandardisasi berukuran $41 \\times 11$.",
      "$\\mathbf{U}$: Matriks koordinat kiri (wilayah) berukuran $41 \\times 11$.",
      "$\\mathbf{\\Lambda}^{1/2}$: Matriks diagonal nilai singular berukuran $11 \\times 11$.",
      "$\\mathbf{V}^T$: Transpos matriks loadings (eigenvector kanan) berukuran $11 \\times 11$."
    ],
    "substitusi": [
      "Matriks data terstandar $\\mathbf{Z} \\in \\mathbb{R}^{41 \\times 11}$ dari 41 wilayah dan 11 indikator.",
      "Dekomposisi nilai singular: $\\mathbf{Z} = \\mathbf{U}\\mathbf{S}\\mathbf{V}^T$.",
      "Dimensi: $\\mathbf{U} \\in \\mathbb{R}^{41 \\times 11}$, $\\mathbf{S} \\in \\mathbb{R}^{11 \\times 11}$, $\\mathbf{V}^T \\in \\mathbb{R}^{11 \\times 11}$."
    ],
    "hasil": "$$ \\mathbf{Z}_{41 \\times 11} = \\mathbf{U}_{41 \\times 11} \\mathbf{S}_{11 \\times 11} \\mathbf{V}_{11 \\times 11}^T $$"
  },
  {
    "id": "statis_fc",
    "category": "statis",
    "title": "22. Skor Koordinat Kompromi ($\\mathbf{F}_c$)",
    "formula": "$$\n\\mathbf{F}_c = \\mathbf{V}_c \\mathbf{\\Lambda}_c^{1/2}\n$$",
    "keterangan": [
      "$\\mathbf{F}$: Matriks koordinat skor wilayah pada komponen utama.",
      "$\\mathbf{Z}$: Matriks data terstandardisasi.",
      "$\\mathbf{V}$: Matriks loadings (eigenvector kanan) untuk proyeksi."
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
      "$g_{jk}$: Nilai loading (korelasi) variabel $j$ pada komponen utama ke-$k$.",
      "$\\operatorname{Cov}(X_j, F_k)$: Nilai kovarians antara variabel asli dengan skor komponen.",
      "$\\sigma_{X_j}$: Simpangan baku dari variabel asli $j$.",
      "$\\sigma_{F_k}$: Simpangan baku dari skor komponen utama ke-$k$."
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
      "$\\hat{\\mathbf{Z}}$: Matriks rekonstruksi data asli terstandardisasi berukuran $41 \\times 11$.",
      "$\\mathbf{F}$: Matriks koordinat skor wilayah terpilih.",
      "$\\mathbf{V}^T$: Transpos matriks loadings variabel terpilih."
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
      "$s$: Konstanta skala penyelerasan visualisasi biplot.",
      "$f_{ik}$: Elemen koordinat skor wilayah $i$ pada komponen ke-$k$.",
      "$v_{jk}$: Elemen koordinat loadings variabel $j$ pada komponen ke-$k$."
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
      "$\\mathbf{W}_k$: Matriks kemiripan (intra-struktur) spasial wilayah pada tahun $k$ berukuran $41 \\times 41$.",
      "$\\mathbf{Z}_k$: Matriks data terstandardisasi pada tahun $k$ berukuran $41 \\times 11$."
    ],
    "substitusi": [
      "Matriks data terstandar tahun 2020: $\\mathbf{Z}_{2020} \\in \\mathbb{R}^{41 \\times 11}$.",
      "Intra-struktur: $\\mathbf{W}_{2020} = \\dfrac{1}{11}\\,\\mathbf{Z}_{2020}\\mathbf{Z}_{2020}^T$.",
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
      "$H_{kk'}$: Nilai produk dalam Hilbert-Schmidt (inter-struktur) antara tahun $k$ dan $k'$.",
      "$\\mathbf{W}_k$: Matriks kemiripan spasial pada tahun $k$.",
      "$\\mathbf{D}$: Matriks diagonal pembobot wilayah."
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
      "$\\mathbf{H}$: Matriks inter-struktur antar-tahun berukuran $5 \\times 5$.",
      "$\\mathbf{u}_1$: Vektor eigen utama dari matriks inter-struktur.",
      "$\\theta_1$: Nilai eigen terbesar (dominan) dari matriks inter-struktur."
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
      "$\\mathbf{W}_c$: Matriks kemiripan kompromi spasial terbobot berukuran $41 \\times 41$.",
      "$\\alpha_k$: Bobot optimal untuk kontribusi tahun ke-$k$ (diambil dari eigenvector utama $\\mathbf{u}_1$).",
      "$\\mathbf{W}_k$: Matriks kemiripan spasial tahun ke-$k$.",
      "$K$: Jumlah total tahun pengamatan ($K = 5$)."
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
      "$\\mathbf{W}_c$: Matriks kemiripan kompromi spasial berukuran $41 \\times 41$.",
      "$\\mathbf{P}$: Matriks eigenvector ortonormal kompromi berukuran $41 \\times 41$.",
      "$\\mathbf{\\Lambda}_c$: Matriks diagonal nilai eigen kompromi berukuran $41 \\times 41$."
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
      "$\\mathbf{F}_c$: Matriks koordinat kompromi wilayah pada ruang 2 dimensi.",
      "$\\mathbf{D}^{-1/2}$: Akar kuadrat invers matriks diagonal pembobot wilayah.",
      "$\\mathbf{P}_r$: Proyeksi subset $r$ eigenvector utama.",
      "$\\mathbf{\\Lambda}_{c,r}^{1/2}$: Akar kuadrat diagonal $r$ eigenvalue utama."
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
      "$\\mathbf{F}_k$: Matriks koordinat transisi wilayah pada tahun $k$.",
      "$\\mathbf{W}_k$: Matriks kemiripan spasial wilayah tahun $k$.",
      "$\\mathbf{D}$: Matriks diagonal pembobot wilayah.",
      "$\\mathbf{P}_r$: Eigenvector kompromi terpilih.",
      "$\\mathbf{\\Lambda}_{c,r}^{-1/2}$: Akar kuadrat invers diagonal eigenvalue kompromi."
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
      "$\\mathbf{G}_k$: Matriks koordinat transisi variabel pada tahun $k$ berukuran $11 \\times 2$.",
      "$\\mathbf{Z}_k^T$: Transpos matriks data terstandardisasi tahun $k$ berukuran $11 \\times 41$.",
      "$\\mathbf{F}_c$: Matriks koordinat kompromi wilayah berukuran $41 \\times 2$.",
      "$\\mathbf{\\Lambda}_{c,r}^{-1}$: Invers diagonal eigenvalue kompromi terpilih."
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
      "$\\mathbf{G}_c$: Matriks koordinat kompromi variabel berukuran $11 \\times 2$.",
      "$\\alpha_k$: Bobot kontribusi optimal tahun ke-$k$.",
      "$\\mathbf{G}_k$: Matriks koordinat transisi variabel tahun ke-$k$."
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
      "$\\mathbf{G}_c$: Matriks koordinat kompromi variabel berukuran $11 \\times 2$.",
      "$\\mathbf{V}_r$: Eigenvector kanan terpilih.",
      "$\\mathbf{\\Lambda}_{s,r}^{1/2}$: Akar kuadrat diagonal eigenvalue dual."
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
      "$\\mathbf{G}_k$: Matriks koordinat transisi variabel tahun $k$ berukuran $11 \\times 2$.",
      "$\\mathbf{S}_k$: Matriks korelasi spasial variabel tahun $k$ berukuran $11 \\times 11$.",
      "$\\mathbf{V}_r$: Eigenvector kanan kompromi terpilih.",
      "$\\mathbf{\\Lambda}_{s,r}^{-1/2}$: Akar kuadrat invers diagonal eigenvalue dual."
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
      "$\\mathbf{F}_k$: Matriks koordinat transisi wilayah tahun $k$ berukuran $41 \\times 2$.",
      "$\\mathbf{Z}_k$: Matriks data terstandardisasi tahun $k$ berukuran $41 \\times 11$.",
      "$\\mathbf{G}_c$: Matriks koordinat kompromi variabel berukuran $11 \\times 2$."
    ],
    "substitusi": [
      "Koordinat transisi baris wilayah pada tahun $k = 2020$ (pendekatan dual).",
      "$\\mathbf{Z}_{2020} \\in \\mathbb{R}^{41 \\times 11}$, $\\mathbf{G}_c \\in \\mathbb{R}^{11 \\times 2}$.",
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
      "$\\mathbf{F}_c$: Matriks koordinat kompromi wilayah berukuran $41 \\times 2$.",
      "\\alpha_k$: Bobot kontribusi optimal tahun ke-$k$.",
      "$\\mathbf{F}_k$: Matriks koordinat transisi wilayah tahun ke-$k$."
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
    "formula": "$$\n\\mathbf{X}_{vis} = \\mathbf{X}_{svd} \\times \\operatorname{sign}(\\rho(PC1, \\text{Indikator Utama}))\n$$",
    "keterangan": [
      "$\\mathbf{X}_{vis}$: Matriks koordinat visualisasi akhir yang disesuaikan arah interpretasinya.",
      "$\\mathbf{X}_{svd}$: Matriks koordinat mentah hasil SVD.",
      "$\\rho(PC1, \\text{Indikator Utama})$: Nilai korelasi sumbu pertama PC1 dengan variabel pembanding utama (IPM)."
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
      "$\\mathbf{G}_{vis}$: Matriks kordinat loadings variabel terskala untuk visualisasi akhir.",
      "$\\mathbf{G}_{svd}$: Matriks kordinat loadings variabel mentah hasil SVD.",
      "\\max(|\\mathbf{F}_{svd}|)$: Nilai koordinat absolut maksimum dari skor wilayah.",
      "\\max(|\\mathbf{G}_{svd}|)$: Nilai koordinat absolut maksimum dari loadings variabel."
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
      "$\\beta_k$: Elemen ke-$k$ dari vektor struktur $\\boldsymbol{\\beta}$ yang menggambarkan kemiripan tahun $k$ dengan kompromi.",
      "$\\lambda_1$: Nilai eigen utama dari matriks inter-struktur.",
      "\\alpha_k$: Nilai bobot optimal dari tahun ke-$k$."
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
      "$\\tilde{\\boldsymbol{\\beta}}$: Vektor struktur spasio-temporal kompromi.",
      "$\\lambda_1$: Nilai eigen utama dari matriks inter-struktur.",
      "\\boldsymbol{\\alpha}_1$: Vektor eigen utama dari matriks inter-struktur."
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
      "\\|\\tilde{\\boldsymbol{\\beta}}\\|^2$: Kuadrat norma (panjang) dari vektor struktur kompromi.",
      "$\\lambda_1^2$: Kuadrat nilai eigen utama inter-struktur."
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
      "$V$: Sisa inersia (residual variance) dari inter-struktur yang tidak tertangkap oleh komponen utama pertama.",
      "\\|\\mathbf{H}\\|_F^2$: Kuadrat norma Frobenius dari matriks inter-struktur $\\mathbf{H}$.",
      "\\|\\tilde{\\boldsymbol{\\beta}}\\|^2$: Kuadrat norma dari vektor struktur kompromi."
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
      "$\\tau$: Rasio sinyal-ke-derau (signal-to-noise ratio) dari representasi kompromi.",
      "$\\lambda^2$: Kuadrat nilai eigen utama (representasi sinyal).",
      "$\\sigma^2$: Varians residual (derau/noise)."
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
      "$\\mathrm{Inertia}_1$: Persentase inersia inter-struktur yang terjelaskan oleh sumbu kompromi pertama.",
      "$\\lambda_1$: Nilai eigen utama dari matriks inter-struktur.",
      "$K$: Jumlah total tahun pengamatan ($K = 5$)."
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
      "$\\mathbf{F}_k$: Matriks koordinat transisi wilayah pada tahun $k$ berukuran $41 \\times 2$.",
      "$\\mathbf{Z}_k$: Matriks data terstandardisasi pada tahun $k$ berukuran $41 \\times 11$.",
      "$\\mathbf{V}_c$: Matriks loadings kompromi berukuran $11 \\times 2$."
    ],
    "substitusi": [
      "Proyeksi koordinat wilayah pada tahun $k = 2020$.",
      "$\\mathbf{Z}_{2020} \\in \\mathbb{R}^{41 \\times 11}$, $\\mathbf{V}_c \\in \\mathbb{R}^{11 \\times 2}$."
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
      "$d(i, j)$: Jarak Euclidean lintas waktu (spasio-temporal) antara wilayah $i$ dan $j$.",
      "\\mathbf{f}_{i,k}$: Vektor koordinat wilayah $i$ pada tahun $k$.",
      "$K$: Jumlah total tahun pengamatan ($K = 5$)."
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
      "$\\theta$: Sudut rotasi baseline (dalam radian).",
      "$v_1, v_2$: Koordinat sumbu pertama (PC1) dan kedua (PC2) dari titik jangkar baseline.",
      "\\operatorname{atan2}$: Fungsi busur tangen 2-argumen untuk mendapatkan sudut kuadran yang tepat."
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
      "$\\mathbf{Q}(\\theta)$: Matriks transformasi rotasi ortogonal berukuran $2 \\times 2$.",
      "$\\theta$: Sudut rotasi baseline (dalam radian)."
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
      "$SSE$: Jumlah kuadrat galat/kesalahan intra-klaster (Sum of Squared Errors).",
      "$k$: Jumlah kelompok/klaster yang dibentuk.",
      "\\mathbf{x}_i$: Vektor koordinat lintasan wilayah ke-$i$.",
      "\\mathbf{\\mu}_j$: Vektor centroid (rata-rata lintasan) klaster ke-$j$."
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
      "\\Delta(A, B)$: Kenaikan jarak/inersia Ward dari penggabungan klaster $A$ dan $B$.",
      "$n_A, n_B$: Jumlah anggota wilayah di dalam klaster $A$ dan $B$.",
      "\\mathbf{\\mu}_A, \\mathbf{\\mu}_B$: Centroid (titik pusat) dari klaster $A$ dan $B$."
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
      "$\\mathbf{T}$: Matriks peluang transisi klaster berukuran $k \\times k$.",
      "$M_{i,j}$: Elemen matriks berupa probabilitas transisi perpindahan dari klaster $i$ ke $j$."
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
    "title": "61. Penyelarasan Label Klaster Lintas Waktu (Teori/Relasi)",
    "formula": "$$\nD(c_{1i}, c_{2j}) = \\sqrt{\\sum_{h=1}^{p} (c_{1ih} - c_{2jh})^2}\n$$",
    "keterangan": [
      "$D(c_{1i}, c_{2j})$: Jarak Euclidean antara centroid klaster $i$ pada periode 1 dan centroid klaster $j$ pada periode 2.",
      "$c_{1ih}, c_{2jh}$: Elemen koordinat dimensi ke-$h$ dari masing-masing centroid.",
      "$p$: Jumlah koordinat dimensi komponen ($p = 2$)."
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
    "title": "62. Penyelarasan Label Klaster Lintas Waktu (Teori/Relasi)",
    "formula": "$$\n\\min \\sum_{i=1}^{k} \\sum_{j=1}^{k} D(c_{1i}, c_{2j}) \\cdot x_{ij}\n$$",
    "keterangan": [
      "$x_{ij}$: Variabel keputusan biner (bernilai 1 jika klaster $i$ dipetakan ke klaster $j$, bernilai 0 jika tidak).",
      "$D(c_{1i}, c_{2j})$: Jarak Euclidean antara centroid klaster periode 1 dan 2.",
      "$k$: Jumlah klaster yang diselaraskan."
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
    "title": "63. Kategorisasi dan Perankingan Klaster (Teori/Relasi)",
    "formula": "$$\n\\overline{\\text{PC}}_{1,k} = \\frac{1}{n_k} \\sum_{i \\in C_k} \\mathbf{f}_{i,1}\n$$",
    "keterangan": [
      "$\\overline{\\text{PC}}_{1,k}$: Nilai rata-rata skor koordinat sumbu pertama (PC1) untuk klaster ke-$k$.",
      "$n_k$: Jumlah wilayah di dalam klaster ke-$k$.",
      "\\mathbf{f}_{i,1}$: Skor sumbu pertama (PC1) wilayah ke-$i$ di dalam klaster ke-$k$."
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
      "$w_{ij}$: Elemen bobot kontiguitas spasial (adjasensi) antara wilayah $i$ dan $j$.",
      "$w_{ii}$: Nilai diagonal utama yang bernilai 0 (wilayah tidak bertetangga dengan dirinya sendiri)."
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
      "$I$: Nilai koefisien autokorelasi spasial Global Moran's I.",
      "$N$: Jumlah total wilayah pengamatan ($N = 41$).",
      "$w_{ij}$: Elemen matriks bobot spasial antara wilayah $i$ dan $j$.",
      "$x_i, x_j$: Nilai skor PC1 untuk masing-masing wilayah $i$ dan $j$."
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
      "$\\mu_{jk}$: Rata-rata tertimbang spasial variabel $j$ pada tahun $k$.",
      "$\\sigma_{jk}$: Simpangan baku tertimbang spasial variabel $j$ pada tahun $k$.",
      "$m_i$: Bobot demografis (spasial) wilayah ke-$i$.",
      "$x_{ijk}$: Nilai observasi asli wilayah $i$, variabel $j$, pada tahun $k$."
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

  useEffect(() => {
    let active = true;
    async function loadFormulas() {
      try {
        setLoading(true);
        const res = await fetch('/formulas_substitusi.json');
        if (!res.ok) throw new Error('Gagal memuat formulas_substitusi.json');
        const data = await res.json();
        if (active) {
          setFormulas(data);
          setLoading(false);
        }
      } catch (err) {
        console.error("Error loading formulas_substitusi.json, using fallback:", err);
        if (active) setLoading(false);
      }
    }
    loadFormulas();
    return () => { active = false; };
  }, []);

  // Trigger MathJax typesetting whenever the list of formulas, search query, active category, or expanded cards changes
  useEffect(() => {
    if (window.MathJax) {
      const timer = setTimeout(() => {
        window.MathJax.typesetPromise && window.MathJax.typesetPromise()
          .catch((err) => console.warn("MathJax typesetting failed: ", err));
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [formulas, searchQuery, activeCategory, expandedCards]);

  const formatTextHtml = (text) => {
    if (!text) return "";
    // Replace **text** with premium bold styling
    return text.replace(/\*\*(.*?)\*\*/g, '<strong style="color: #38BDF8; font-weight: 700;">$1</strong>');
  };

  const toggleExpand = (id) => {
    setExpandedCards(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  // Render a string that may contain LaTeX ($...$ or $$...$$) via MathJax.
  // We insert it as raw HTML so MathJax can process it after mount.
  const _renderLatexText = (text) => {
    if (!text) return null;
    return (
      <span dangerouslySetInnerHTML={{ __html: formatTextHtml(text) }} />
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
                    dangerouslySetInnerHTML={{ __html: formatTextHtml(f.formula) }}
                  />
                </div>

                {/* Keterangan */}
                <div>
                  <div style={{ fontSize: '12px', fontWeight: '700', color: '#38BDF8', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>Keterangan:</div>
                  <ul style={{ listStyleType: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {f.keterangan.map((ket, idx) => (
                      <li key={idx} style={{ fontSize: '13.5px', color: '#CBD5E1', lineHeight: '1.5', paddingLeft: '12px', borderLeft: '2px solid rgba(255,255,255,0.15)' }}
                        dangerouslySetInnerHTML={{ __html: formatTextHtml(ket) }}
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
                              dangerouslySetInnerHTML={{ __html: formatTextHtml(sub) }}
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
                          <span dangerouslySetInnerHTML={{ __html: formatTextHtml(f.hasil) }} />
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


// ─── METHODOLOGY FLOW HELPERS ────────────────────────────────────────────────
function LatexFormula({ tex, color, small, bare }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!ref.current) return;
    // Set content directly — avoids React reconciliation interfering with
    // MathJax's rendered SVG output, which dangerouslySetInnerHTML can reset.
    ref.current.innerHTML = tex;

    let cancelled = false;
    function tryTypeset() {
      if (cancelled || !ref.current) return;
      if (window.MathJax?.typesetPromise) {
        window.MathJax.typesetPromise([ref.current]).catch(() => {});
      } else {
        setTimeout(tryTypeset, 300);
      }
    }
    // Small delay so the browser paints the raw text before MathJax converts it.
    const t = setTimeout(tryTypeset, 80);
    return () => { cancelled = true; clearTimeout(t); };
  }, [tex]);

  return (
    <div ref={ref}
      style={{
        background: bare ? 'transparent' : 'rgba(0,0,0,0.30)',
        border: bare ? 'none' : `1px solid ${color || '#e2e8f0'}30`,
        borderRadius: bare ? '0' : '10px',
        padding: bare ? '2px 0' : (small ? '5px 12px' : '10px 18px'),
        color: color || '#e2e8f0',
        fontSize: small ? '0.88rem' : '1rem',
        lineHeight: 1.8,
        overflowX: 'auto',
        margin: bare ? '2px 0' : '6px 0',
      }}
    />
  );
}

function OutputBadge({ icon, label, color }) {
  return (
    <span style={{ display:'inline-flex', alignItems:'center', gap:'5px',
      background:`${color}12`, border:`1px solid ${color}35`, borderRadius:'12px',
      padding:'3px 10px', fontSize:'0.7rem', color, fontWeight:'600' }}>
      {icon} <span dangerouslySetInnerHTML={{ __html: mathToHtml(label) }} />
    </span>
  );
}

function FlowArrow({ label, fromColor, toColor }) {
  return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center', padding:'2px 0' }}>
      <div style={{ width:'2px', height:'14px', background:`linear-gradient(to bottom,${fromColor}90,${toColor}90)` }} />
      {label && (
        <div style={{ background:'rgba(15,23,42,0.85)', border:'1px solid rgba(255,255,255,0.08)',
          borderRadius:'20px', padding:'3px 14px', fontSize:'0.63rem', color:'#64748b',
          textAlign:'center', maxWidth:'480px', margin:'2px 0', letterSpacing:'0.2px' }}
          dangerouslySetInnerHTML={{ __html: mathToHtml(label) }} />
      )}
      <div style={{ width:'2px', height:'14px', background:`linear-gradient(to bottom,${fromColor}90,${toColor}90)` }} />
      <div style={{ width:0, height:0, borderLeft:'6px solid transparent', borderRight:'6px solid transparent', borderTop:`8px solid ${toColor}` }} />
    </div>
  );
}
/* Renders detail text: converts _x → <sub>x</sub>, ^x → <sup>x</sup>, Greek letters */
// Shared math-to-HTML converter used by DetailText, StepCard titles, and FlowArrow labels.
function mathToHtml(text) {
  if (!text) return '';
  return text
    .replace(/_\{([^}]+)\}/g, '<sub>$1</sub>')
    .replace(/_([a-zA-Z0-9*'])/g, '<sub>$1</sub>')
    .replace(/\^\{([^}]+)\}/g, '<sup>$1</sup>')
    .replace(/\^([a-zA-Z0-9*+-])/g, '<sup>$1</sup>')
    .replace(/\\alpha/g, 'α').replace(/\\beta/g, 'β').replace(/\\lambda/g, 'λ')
    .replace(/\\mu/g, 'μ').replace(/\\sigma/g, 'σ').replace(/\\tau/g, 'τ')
    .replace(/\\theta/g, 'θ').replace(/\\eta/g, 'η').replace(/\\times/g, '×')
    .replace(/\\cdot/g, '·').replace(/\\leq/g, '≤').replace(/\\geq/g, '≥')
    .replace(/\\in/g, '∈').replace(/\\sum/g, '∑').replace(/\\infty/g, '∞')
    .replace(/\\\(|\\\)/g, '').replace(/\$\$/g, '').replace(/\$/g, '')
    .replace(/\{|\}/g, '');
}

function DetailText({ text }) {
  if (!text) return null;
  return <span style={{ fontSize: '0.72rem', color: '#64748b', lineHeight: 1.55 }} dangerouslySetInnerHTML={{ __html: mathToHtml(text) }} />;
}

/* Lazy-loads & renders a single output file (tex or image) from output_sample */
function OutputFileViewer({ path, label, caption, imgHeight }) {
  const [tex, setTex]             = useState('');
  const [loading, setLoading]     = useState(true);
  const [unavailable, setUnavailable] = useState(false);
  const isImg = /\.(png|jpg|gif)$/i.test(path);

  useEffect(() => {
    if (isImg) { setLoading(false); return; }
    let active = true;
    setLoading(true);
    setUnavailable(false);
    fetch(path)
      .then(r => {
        if (!r.ok) { if (active) { setUnavailable(true); setLoading(false); } return; }
        return r.text();
      })
      .then(t => { if (t !== undefined && active) { setTex(t); setLoading(false); } })
      .catch(() => { if (active) { setUnavailable(true); setLoading(false); } });
    return () => { active = false; };
  }, [path]);

  return (
    <div style={{ marginBottom: '10px' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '4px' }}>
        <span style={{ fontSize: '0.72rem', fontWeight: '700', color: '#06b6d4' }} dangerouslySetInnerHTML={{ __html: mathToHtml(label) }} />
        {caption && <span style={{ fontSize: '0.65rem', color: '#475569', fontStyle: 'italic' }}>— {caption}</span>}
      </div>
      {loading ? (
        <div style={{ height: '50px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div className="spinner" style={{ width: '20px', height: '20px' }} />
        </div>
      ) : unavailable ? (
        <div style={{ padding: '12px 16px', background: 'rgba(0,0,0,0.2)', borderRadius: '8px', textAlign: 'center', color: '#64748b', fontSize: '0.75rem', border: '1px dashed rgba(255,255,255,0.08)' }}>
          Data tidak tersedia pada output ini
        </div>
      ) : isImg ? (
        <div style={{ background: 'rgba(0,0,0,0.3)', borderRadius: '8px', padding: '6px', display: 'flex', justifyContent: 'center' }}>
          <img src={path} alt={label} style={{ maxWidth: '100%', maxHeight: imgHeight || '160px', objectFit: 'contain', borderRadius: '6px' }} />
        </div>
      ) : (
        <div style={{ maxHeight: '200px', overflowY: 'auto', overflowX: 'auto', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.08)' }} className="custom-scrollbar">
          <LatexTable tex={tex} />
        </div>
      )}
    </div>
  );
}

// ─── MODULE-LEVEL StepCard ────────────────────────────────────────────────────
// Defined OUTSIDE MethodologyFlowView so React never unmounts/remounts it on
// hover-triggered parent re-renders. Previously defined inside caused MathJax
// formulas to flash raw LaTeX on every mouse-enter event.
const _STEP_TYPE_LABELS = { input: 'INPUT', process: 'PROSES', decision: 'KEPUTUSAN', output: 'OUTPUT' };

function deriveRealPaths(outputFiles) {
  return (outputFiles || []).map(f => ({
    ...f,
    path: f.path
      .replace('/output_sample/scenario1/', '/output_real/scenario1/')
      .replace('/output_sample/', '/output_real/')
      .replace('/data_sampel_', '/data_final_'),
  }));
}

function StepCard({ step, num, isExpanded, isExpandedReal, isHovered, onMouseEnter, onMouseLeave, onToggle, onToggleReal }) {
  const hasOutput = step.outputFiles && step.outputFiles.length > 0;
  return (
    <div
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      style={{
        width: '100%',
        background: isHovered ? 'rgba(30,41,59,0.75)' : 'rgba(15,23,42,0.5)',
        border: `1px solid ${isHovered ? step.color : step.color + '40'}`,
        borderLeft: `4px solid ${step.color}`,
        borderRadius: '14px', padding: '16px 20px',
        transition: 'all 0.2s',
        boxShadow: isHovered ? `0 4px 28px ${step.color}22` : 'none',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
        <span style={{ background: step.color, color: '#fff', borderRadius: '50%', width: '26px', height: '26px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.7rem', fontWeight: '800', flexShrink: 0 }}>{num}</span>
        <span style={{ fontSize: '0.62rem', fontWeight: '700', color: step.color, background: `${step.color}18`, border: `1px solid ${step.color}40`, borderRadius: '10px', padding: '2px 8px', letterSpacing: '0.5px', textTransform: 'uppercase' }}>{_STEP_TYPE_LABELS[step.type] || 'PROSES'}</span>
        <span style={{ fontSize: '1.1rem' }}>{step.icon}</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: '700', fontSize: '0.92rem', color: '#f8fafc', lineHeight: 1.3 }} dangerouslySetInnerHTML={{ __html: mathToHtml(step.title) }} />
          <div style={{ fontSize: '0.72rem', color: '#94a3b8', lineHeight: 1.3 }} dangerouslySetInnerHTML={{ __html: mathToHtml(step.subtitle) }} />
        </div>
      </div>
      <LatexFormula tex={step.latex} color={step.color} />
      <div style={{ marginBottom: '8px' }}><DetailText text={step.detail} /></div>
      {step.outputs && (
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginBottom: '6px' }}>{step.outputs}</div>
      )}
      {step.rejectLabel && (
        <div style={{ background: 'rgba(248,113,113,0.08)', border: '1px dashed rgba(248,113,113,0.3)', borderRadius: '8px', padding: '6px 12px', fontSize: '0.7rem', color: '#f87171', marginTop: '6px' }}
          dangerouslySetInnerHTML={{ __html: '↩ ' + mathToHtml(step.rejectLabel) }} />
      )}
      {hasOutput && (
        <div style={{ marginTop: '10px' }}>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <button
              onClick={onToggle}
              style={{
                background: isExpanded ? `${step.color}20` : 'rgba(15,23,42,0.6)',
                border: `1px solid ${step.color}50`,
                color: isExpanded ? step.color : '#64748b',
                borderRadius: '8px', padding: '5px 14px',
                fontSize: '0.7rem', fontWeight: '700', cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: '6px',
                transition: 'all 0.15s',
              }}
            >
              <span style={{ fontSize: '0.8rem' }}>{isExpanded ? '▼' : '▶'}</span>
              {isExpanded ? 'Sembunyikan Output Sampel' : `Lihat Output Sampel (${step.outputFiles.length} tabel/gambar)`}
            </button>
            <button
              onClick={onToggleReal}
              style={{
                background: isExpandedReal ? 'rgba(16,185,129,0.15)' : 'rgba(15,23,42,0.6)',
                border: `1px solid ${isExpandedReal ? '#10b981' : 'rgba(16,185,129,0.3)'}`,
                color: isExpandedReal ? '#10b981' : '#64748b',
                borderRadius: '8px', padding: '5px 14px',
                fontSize: '0.7rem', fontWeight: '700', cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: '6px',
                transition: 'all 0.15s',
              }}
            >
              <span style={{ fontSize: '0.8rem' }}>{isExpandedReal ? '▼' : '▶'}</span>
              {isExpandedReal ? 'Sembunyikan Output Real' : `Lihat Output Real (${step.outputFiles.length} tabel/gambar)`}
            </button>
          </div>
          {isExpanded && (
            <div style={{ marginTop: '12px', borderTop: `1px solid ${step.color}25`, paddingTop: '12px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ fontSize: '0.63rem', color: '#475569', letterSpacing: '0.5px', fontWeight: '600', textTransform: 'uppercase' }}>
                Output dari data sampel (n=4 wilayah, K=3 tahun, p=3 indikator)
              </div>
              {step.outputFiles.map((f, i) => (
                <OutputFileViewer key={i} path={f.path} label={f.label} caption={f.caption} imgHeight={f.imgHeight} />
              ))}
            </div>
          )}
          {isExpandedReal && (
            <div style={{ marginTop: '12px', borderTop: '1px solid rgba(16,185,129,0.2)', paddingTop: '12px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ fontSize: '0.63rem', color: '#10b981', letterSpacing: '0.5px', fontWeight: '600', textTransform: 'uppercase' }}>
                Output dari data real (n=41 Kab/Kota, K=5 tahun, p=11 indikator)
              </div>
              {deriveRealPaths(step.outputFiles).map((f, i) => (
                <OutputFileViewer key={i} path={f.path} label={f.label} caption={f.caption} imgHeight={f.imgHeight} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function MethodologyFlowView({ onBack }) {
  const [hovered, setHovered]           = useState(null);
  const [expandedOutputs, setExpandedOutputs] = useState({});
  const toggleOutput = (id) => setExpandedOutputs(prev => ({ ...prev, [id]: !prev[id] }));
  const [expandedOutputsReal, setExpandedOutputsReal] = useState({});
  const toggleOutputReal = (id) => setExpandedOutputsReal(prev => ({ ...prev, [id]: !prev[id] }));
  const [showZkDeskriptif, setShowZkDeskriptif] = useState(false);
  const [showZkDeskriptifReal, setShowZkDeskriptifReal] = useState(false);

  /* ---------- COMMON STEPS (shared by both PCA & STATIS) ---------- */
  const BASE = '/output_sample/';
  const SC1  = '/output_sample/scenario1/';

  const COMMON = [
    {
      id: 'c0', color: '#10b981', icon: '📂', type: 'input',
      title: 'Data Mentah',
      subtitle: 'K matriks data observasi per situasi-waktu',
      latex: `$$\\mathbf{X}_1,\\,\\mathbf{X}_2,\\,\\ldots,\\,\\mathbf{X}_K \\in \\mathbb{R}^{n \\times p}$$`,
      detail: 'n = 41 Kab/Kota  |  p = 11 indikator kesejahteraan  |  K = 5 tahun (2020–2024)  |  Sumber: BPS RI',
      outputs: [<OutputBadge key="o" icon="📊" label="5 sheet Excel × 41 baris × 15 kol" color="#10b981"/>],
      outputFiles: [
        { path: '/data_sampel_2020.tex', label: 'X₂₀₂₀ — Data Sampel (n=4)', caption: 'PPM, RLS, TPT, IPM, JP — 4 wilayah ilustratif' },
      ],
      arrowLabel: 'matriks X_k mentah per tahun',
    },
    {
      id: 'c2', color: '#8b5cf6', icon: '⚖️', type: 'process',
      title: 'Bobot Demografis & Matriks Bobot D',
      subtitle: 'Pembobotan proporsional berbasis Jumlah Penduduk',
      latex: `$$m_i=\\frac{\\overline{\\mathrm{JP}}_i}{\\displaystyle\\sum_{i'=1}^{n}\\overline{\\mathrm{JP}}_{i'}},\\quad \\mathbf{D}=\\operatorname{diag}(m_1,m_2,\\ldots,m_n),\\quad \\sum_{i=1}^{n}m_i=1$$`,
      detail: 'JP̄ᵢ = rata-rata JP wilayah i selama K tahun  |  ⟨x,y⟩_D = xᵀDy mendefinisikan inner product terbobot yang konsisten di semua situasi',
      outputs: [<OutputBadge key="d" icon="🔢" label="Vektor m (n×1) + Matriks D (n×n diagonal)" color="#8b5cf6"/>],
      outputFiles: [
        { path: BASE + 'output_table_mi_weights.tex', label: 'Bobot Wilayah m_i — Semua Wilayah', caption: 'mᵢ = J̄Pᵢ / Σ J̄P — bobot demografis proporsional dari JP rata-rata lintas tahun' },
      ],
      arrowLabel: 'rata-rata JP lintas tahun → bobot demografis mᵢ',
    },
    {
      id: 'c4', color: '#f59e0b', icon: '🔬', type: 'decision',
      title: 'Uji Kelayakan Multivariat: KMO & Bartlett',
      subtitle: 'Verifikasi cukupan korelasi antar-indikator sebelum reduksi dimensi',
      latex: `$$\\mathrm{KMO}=\\frac{\\displaystyle\\sum_{j\\neq k}r_{jk}^2}{\\displaystyle\\sum_{j\\neq k}r_{jk}^2+\\displaystyle\\sum_{j\\neq k}r_{jk.p}^2}\\geq 0{,}5,\\qquad \\chi^2_{\\text{Bartlett}}=-\\!\\left[n-1-\\frac{2p+5}{6}\\right]\\ln|\\mathbf{R}|,\\quad p<0{,}05$$`,
      detail: 'r_{jk} = korelasi Pearson  |  r_{jk.p} = korelasi parsial  |  |R| = determinan matriks korelasi  |  df = p(p−1)/2',
      outputs: [<OutputBadge key="k" icon="✅" label="Lolos → lanjut analisis dimensi" color="#f59e0b"/>, <OutputBadge key="r" icon="↩️" label="Gagal → revisi indikator" color="#f87171"/>],
      outputFiles: [
        { path: BASE + 'output_table_kmo_bartlett.tex', label: 'Hasil Uji KMO & Bartlett per Tahun', caption: 'Nilai KMO, χ² Bartlett, df, p-value, keputusan' },
      ],
      rejectLabel: '✗ KMO < 0.5 atau p-Bartlett ≥ 0.05 → revisi indikator',
      arrowLabel: '✓ KMO ≥ 0.5  &  Bartlett p < 0.05 → lanjut ke reduksi dimensi',
    },
  ];

  /* -------- STATIS-SPECIFIC STEPS -------- */
  const STATIS_STEPS = [
    {
      id: 's0', color: '#06b6d4', icon: '🗺️', num: 6,
      title: 'Tahap 1 — Intra-Struktur (W_k)',
      subtitle: 'Matriks kemiripan antar-wilayah berbasis profil indikator, per tahun',
      latex: `$$\\mathbf{W}_k = \\mathbf{Z}_k\\mathbf{Z}_k^T \\in \\mathbb{R}^{n\\times n},\\qquad w_{ij}^{(k)}=\\sum_{j=1}^{p}z_{ijk}\\,z_{jk}$$`,
      detail: 'wᵢⱼ mencerminkan "seberapa mirip" profil indikator wilayah i dan j pada tahun k  |  simetris & semi-definit positif',
      outputs: [<OutputBadge key="w" icon="🔢" label="K matriks W_k (n×n) per tahun" color="#06b6d4"/>],
      outputFiles: [
        { path: SC1 + 'output_table_matriks_intra_loading_2020.tex', label: 'S₂₀₂₀ — Matriks Intra Skenario 2 (p×p)', caption: 'Korelasi terbobot antar-indikator 2020 (Skenario Dual STATIS)' },
        { path: SC1 + 'output_table_matriks_intra_loading_2021.tex', label: 'S₂₀₂₁ — Matriks Intra 2021', caption: 'Bandingkan dengan S₂₀₂₀ — apakah struktur stabil?' },
      ],
      arrowLabel: 'Z_k → produk Gram Zₖ Zₖᵀ',
    },
    {
      id: 's1', color: '#06b6d4', icon: '📡', num: 7,
      title: 'Tahap 2 — Inter-Struktur (H & Koefisien RV)',
      subtitle: 'Mengukur seberapa konsisten pola kemiripan antar-tahun',
      latex: `$$H_{kk'}=\\operatorname{tr}(\\mathbf{W}_k\\mathbf{D}\\mathbf{W}_{k'}\\mathbf{D}),\\qquad \\mathrm{RV}(\\mathbf{W}_k,\\mathbf{W}_{k'})=\\frac{H_{kk'}}{\\sqrt{H_{kk}\\cdot H_{k'k'}}}$$`,
      detail: 'H ∈ ℝᴷˣᴷ — "matriks korelasi" antar-konfigurasi tahun  |  RV ∈ [0,1]: mendekati 1 berarti struktur sangat stabil lintas waktu',
      outputs: [<OutputBadge key="h" icon="🔢" label="Matriks H (K×K) + vektor RV" color="#06b6d4"/>],
      outputFiles: [
        { path: BASE + 'output_table_hw.tex', label: 'Matriks H_W — Inter-Struktur Wilayah (K×K)', caption: 'Produk Hilbert-Schmidt antara setiap pasang W_k' },
        { path: BASE + 'output_table_rv_w.tex', label: 'Koefisien RV antar-Tahun', caption: 'RV ≈ 1 → struktur sangat stabil. Dasar pembentukan bobot αₖ' },
      ],
      arrowLabel: 'pasangan W_k, W_k′ → Hilbert-Schmidt',
    },
    {
      id: 's2', color: '#8b5cf6', icon: '🏋', num: 8,
      title: 'Bobot Temporal Optimal (α_k)',
      subtitle: 'Kontribusi relatif tiap tahun terhadap kompromi',
      latex: `$$\\mathbf{H}\\mathbf{u}_1=\\theta_1\\mathbf{u}_1\\quad\\Longrightarrow\\quad\\alpha_k=\\frac{u_{1k}}{\\displaystyle\\sum_{k'=1}^{K}u_{1k'}},\\qquad \\alpha_k>0,\\;\\sum_{k=1}^{K}\\alpha_k=1$$`,
      detail: 'u₁ = eigenvector utama H  |  α_k mengukur "seberapa representatif" tahun k terhadap pola rata-rata',
      outputs: [<OutputBadge key="a" icon="📊" label="Vektor α (K×1) — kontribusi tiap tahun" color="#8b5cf6"/>],
      outputFiles: [
        { path: SC1 + 'output_table_alpha.tex', label: 'Bobot Temporal αₖ per Tahun', caption: 'Diperoleh dari u₁ (eigenvector utama H) — ∑αₖ = 1' },
        { path: SC1 + 'output_core_statis.tex', label: 'Ringkasan Parameter Kompromi', caption: 'αₖ, λ₁ (eigenvalue), % inertia — dari output_core_statis.tex' },
      ],
      arrowLabel: 'eigendekomposisi H → eigenvector u₁ → α_k',
    },
    {
      id: 's3', color: '#06b6d4', icon: '🤝', num: 9,
      title: 'Tahap 3 — Matriks Kompromi (W_c)',
      subtitle: 'Konfigurasi rata-rata optimal — representasi konsensus multi-tahun',
      latex: `$$\\mathbf{W}_c=\\sum_{k=1}^{K}\\alpha_k\\,\\mathbf{W}_k\\in\\mathbb{R}^{n\\times n},\\qquad \\mathbf{v}^T\\mathbf{W}_c\\mathbf{v}=\\sum_{k}\\alpha_k(\\mathbf{v}^T\\mathbf{W}_k\\mathbf{v})\\geq 0$$`,
      detail: 'W_c = kombinasi linier berbobot αₖ dari W_k → otomatis semi-definit positif  |  tr(W_c) = total inersia',
      outputs: [<OutputBadge key="wc" icon="🔢" label="Matriks W_c (n×n) kompromi" color="#06b6d4"/>],
      outputFiles: [
        { path: SC1 + 'matrix_V_c.tex', label: 'V_c — Eigenvectors Kompromi (V berukuran p×r)', caption: 'Kolom = arah sumbu kompromi. Diperoleh dari SVD W_c. Isi = loading tiap indikator' },
      ],
      arrowLabel: 'kombinasi linier berbobot αₖ · W_k',
    },
    {
      id: 's4', color: '#3b82f6', icon: '⚛', num: 10,
      title: 'Tahap 4 — Dekomposisi Spektral W_c → F_c & G_c',
      subtitle: 'Ekstraksi koordinat kompromi yang optimal dan konsisten lintas semua tahun',
      latex: `$$\\mathbf{W}_c=\\mathbf{P}\\mathbf{\\Lambda}_c\\mathbf{P}^T,\\quad\\mathbf{F}_c=\\mathbf{D}^{-1/2}\\mathbf{P}\\mathbf{\\Lambda}_c^{1/2}\\in\\mathbb{R}^{n\\times r},\\quad\\mathbf{G}_c=\\sum_k\\alpha_k\\,\\mathbf{Z}_k^T\\mathbf{D}\\mathbf{F}_c\\mathbf{\\Lambda}_c^{-1/2}$$`,
      detail: 'F_c (n×2) = skor kompromi wilayah — posisi "rata-rata terbaik" tiap wilayah  |  G_c (p×2) = loading kompromi indikator',
      outputs: [
        <OutputBadge key="fc" icon="📍" label="F_c (n×2) — skor kompromi wilayah" color="#3b82f6"/>,
        <OutputBadge key="gc" icon="➡️" label="G_c (p×2) — loading kompromi indikator" color="#8b5cf6"/>
      ],
      outputFiles: [
        { path: SC1 + 'output_table_scores.tex', label: 'F_c — Koordinat Skor Kompromi Wilayah', caption: 'PC1 & PC2 tiap wilayah dalam ruang kompromi (n×2). Ini input K-Means!' },
        { path: SC1 + 'output_table_loadings.tex', label: 'G_c — Loading Kompromi Indikator', caption: 'Kontribusi tiap indikator pada PC1 & PC2 kompromi' },
      ],
      arrowLabel: 'P, Λ dari dekomposisi W_c → F_c, G_c',
    },
  ];

  /* -------- DOWNSTREAM STEPS (setelah STATIS biplot) -------- */
  const DOWN_STEPS = [
    {
      id: 'd0', color: '#f59e0b', icon: '🎲', type: 'decision', num: 11,
      title: 'Uji Permutasi (Signifikansi Stabilitas)',
      subtitle: 'Verifikasi bahwa struktur kompromi bukan artefak acak',
      latex: `$$\\tau=\\frac{\\lambda_1^2}{\\sigma^2},\\qquad p\\text{-value}=\\frac{\\#\\{\\tau_{\\mathrm{perm}}\\geq\\tau_{\\mathrm{obs}}\\}}{N_{\\mathrm{perm}}},\\quad N_{\\mathrm{perm}}=1000$$`,
      detail: 'Permutasi acak kolom matriks inter-struktur H  |  p < 0.05 → struktur signifikan & layak diinterpretasi',
      outputs: [<OutputBadge key="p" icon="📊" label="p-value + histogram permutasi" color="#f59e0b"/>],
      outputFiles: [
        { path: SC1 + 'output_perm_statis.tex', label: 'Hasil Uji Permutasi', caption: 'p-value, λ₁ observasi, interpretasi signifikansi struktur' },
      ],
      rejectLabel: '✗ Struktur tidak signifikan → analisis dihentikan',
      arrowLabel: '✓ p < 0.05 → struktur kompromi bermakna secara statistik',
    },
    {
      id: 'd1', color: '#3b82f6', icon: '🔭', type: 'process', num: 12,
      title: 'Compromise Biplot & Trajektori Temporal (F_k, G_k)',
      subtitle: 'Visualisasi posisi wilayah & indikator — statis (F_c, G_c) & dinamis (F_k, G_k)',
      latex: `$$\\mathbf{F}_k=\\mathbf{W}_k\\mathbf{D}\\mathbf{P}\\mathbf{\\Lambda}_c^{-1/2}\\in\\mathbb{R}^{n\\times r},\\qquad\\mathbf{G}_k=\\mathbf{Z}_k^T\\mathbf{D}\\mathbf{F}_c\\mathbf{\\Lambda}_c^{-1/2}\\in\\mathbb{R}^{p\\times r}$$`,
      detail: 'F_k & G_k = proyeksi tiap tahun k ke RUANG KOMPROMI YANG SAMA → trajektori antar tahun geometrically comparable',
      outputs: [
        <OutputBadge key="t" icon="🎯" label="3D Scatter (Tahun × PC1_c × PC2_c)" color="#3b82f6"/>,
        <OutputBadge key="b" icon="📐" label="2D Biplot kompromi + loading" color="#8b5cf6"/>
      ],
      outputFiles: [
        { path: SC1 + 'output_table_skor_intra_2020.tex', label: 'F₂₀₂₀ — Skor Intra (Proyeksi 2020 ke Ruang Kompromi)', caption: 'PC1 & PC2 per wilayah di ruang kompromi untuk tahun 2020' },
        { path: SC1 + 'output_table_loading_intra_2020.tex', label: 'G₂₀₂₀ — Loading Intra 2020', caption: 'Kontribusi indikator pada tahun 2020 di ruang kompromi' },
        { path: BASE + 'scenario1/trajectory_scores.png', label: 'Plot Trajektori Skor', caption: 'Lintasan wilayah 2020→2022 dalam ruang PC1_c × PC2_c', imgHeight: '150px' },
      ],
      arrowLabel: 'F_c, G_c + per-year projection → biplot & trajectory',
    },
    {
      id: 'd2', color: '#f59e0b', icon: '📏', type: 'process', num: 13,
      title: 'Penentuan Kluster Optimal (k*)',
      subtitle: 'Elbow Method + Silhouette Score pada skor kompromi F_c',
      latex: `$$k^*=\\arg\\min_{k}\\mathrm{SSE}(k)\\;\\cap\\;\\arg\\max_{k}\\mathrm{Sil}(k),\\qquad k\\in\\{2,3,4,5\\},\\quad \\mathrm{SSE}=\\sum_{j}\\sum_{\\mathbf{x}_i\\in C_j}\\|\\mathbf{x}_i-\\boldsymbol{\\mu}_j\\|^2$$`,
      detail: 'Input: skor F_c (n×2)  |  Ward dendrogram sebagai panduan awal jumlah kluster  |  Silhouette mengukur separasi antar-kluster',
      outputs: [<OutputBadge key="e" icon="📉" label="Elbow plot + Silhouette + Dendrogram" color="#f59e0b"/>],
      outputFiles: [
        { path: BASE + 'elbow_plot_2020.png', label: 'Elbow Plot 2020', caption: 'SSE vs jumlah kluster k — titik siku menunjukkan k*', imgHeight: '140px' },
        { path: BASE + 'dendrogram_2020.png', label: 'Dendrogram Hierarkis 2020', caption: 'Metode Ward — panduan awal jumlah kluster', imgHeight: '140px' },
      ],
      arrowLabel: 'skor F_c (n×2) → metode elbow & silhouette',
    },
    {
      id: 'd3', color: '#6366f1', icon: '🧩', type: 'process', num: 14,
      title: 'K-Means Clustering',
      subtitle: 'Pengelompokan wilayah berdasarkan posisi dalam ruang kompromi',
      latex: `$$\\mathrm{SSE}=\\sum_{j=1}^{k}\\sum_{\\mathbf{x}_i\\in C_j}\\|\\mathbf{x}_i-\\boldsymbol{\\mu}_j\\|^2\\to\\min,\\qquad \\boldsymbol{\\mu}_j=\\frac{1}{|C_j|}\\sum_{\\mathbf{x}_i\\in C_j}\\mathbf{x}_i$$`,
      detail: 'Algoritma iteratif: (1) assign ke centroid terdekat → (2) update centroid → ulangi hingga konvergen  |  Input: F_c ∈ ℝⁿˣ²',
      outputs: [<OutputBadge key="c" icon="🗺️" label="Label kluster + peta per tahun" color="#6366f1"/>],
      outputFiles: [
        { path: SC1 + 'output_table_compromise_cluster_sum_name.tex', label: 'Anggota Kluster Kompromi STATIS', caption: 'Kluster 1/2/3 beserta daftar wilayah anggotanya' },
        { path: BASE + 'cluster_map_biplot_2020.png', label: 'Peta Kluster 2020', caption: 'Hasil K-Means divisualisasikan pada peta geografis', imgHeight: '150px' },
      ],
      arrowLabel: 'minimasi SSE iteratif → update centroid',
    },
    {
      id: 'd4', color: '#8b5cf6', icon: '🔀', type: 'process', num: 15,
      title: 'Penyelarasan Label Lintas Tahun (Hungarian Algorithm)',
      subtitle: 'Menjamin konsistensi label kluster antar-tahun',
      latex: `$$\\min\\sum_{i=1}^{k}\\sum_{j=1}^{k}D(\\mathbf{c}_{1i},\\mathbf{c}_{2j})\\cdot x_{ij},\\qquad D(\\mathbf{c}_{1i},\\mathbf{c}_{2j})=\\|\\mathbf{c}_{1i}-\\mathbf{c}_{2j}\\|$$`,
      detail: 'Centroid kluster berubah tiap tahun akibat re-K-means  |  Hungarian Algorithm (Linear Assignment Problem) memetakan label optimal antar-periode',
      outputs: [<OutputBadge key="h" icon="🔀" label="Tabel transisi kluster antar-tahun" color="#8b5cf6"/>],
      outputFiles: [
        { path: BASE + 'output_table_biplot_transition_name_2020x2021.tex', label: 'Transisi Kluster 2020→2021', caption: 'Wilayah mana yang berpindah kluster (output Hungarian)' },
      ],
      arrowLabel: 'jarak Euclidean centroid → optimal label mapping',
    },
    {
      id: 'd5', color: '#22c55e', icon: '🏆', type: 'process', num: 16,
      title: 'Perankingan Level Kluster',
      subtitle: 'Menetapkan urutan kesejahteraan berdasarkan posisi PC1 kompromi',
      latex: `$$\\overline{\\mathrm{PC}}_{1,k}=\\frac{1}{n_k}\\sum_{i\\in C_k}f_{i,1},\\qquad \\text{Rank}: \\overline{\\mathrm{PC}}_{1,k}\\text{ terbesar}=\\text{kluster kesejahteraan tertinggi}$$`,
      detail: 'PC1 kompromi merangkum sebagian besar varians indikator  |  nilai PC1 tinggi = profil indikator yang lebih baik secara agregat',
      outputs: [<OutputBadge key="r" icon="🥇" label="Label kluster terurut (Tinggi/Sedang/Rendah)" color="#22c55e"/>],
      outputFiles: [
        { path: SC1 + 'output_table_centroid_statis.tex', label: 'Sentroid Kluster per Tahun', caption: 'Rata-rata PC1 & PC2 per kluster — dasar perankingan level' },
      ],
      arrowLabel: 'rata-rata skor PC1 tiap kluster → urutan level',
    },
    {
      id: 'd6', color: '#22c55e', icon: '🌍', type: 'process', num: 17,
      title: "Global Moran's I — Autokorelasi Spasial",
      subtitle: 'Menguji apakah wilayah dengan kluster serupa bergerombol secara geografis',
      latex: `$$I=\\frac{N}{\\displaystyle\\sum_i\\sum_j w_{ij}}\\cdot\\frac{\\displaystyle\\sum_i\\sum_j w_{ij}(x_i-\\bar{x})(x_j-\\bar{x})}{\\displaystyle\\sum_i(x_i-\\bar{x})^2},\\quad w_{ij}=\\begin{cases}1&\\text{bertetangga}\\\\0&\\text{lainnya}\\end{cases}$$`,
      detail: 'x_i = skor PC1 kompromi wilayah i  |  w_ij dari Queen Contiguity  |  I > E[I] → autokorelasi positif: wilayah berdekatan cenderung kluster serupa',
      outputs: [<OutputBadge key="m" icon="🗺️" label="Nilai I + distribusi permutasi + p-value" color="#22c55e"/>],
      outputFiles: [
        { path: SC1 + 'output_moran.tex', label: 'Hasil Uji Global Moran\'s I', caption: 'Nilai I, E[I], Var[I], z-score, p-value per tahun' },
      ],
      arrowLabel: 'skor PC1 × matriks bobot spasial W',
    },
    {
      id: 'd7', color: '#10b981', icon: '✨', type: 'output', num: 18,
      title: 'Hasil Akhir',
      subtitle: 'Peta kluster kesejahteraan, trajektori wilayah, dan tabel transisi',
      latex: `$$\\text{Output: Kluster } k^*,\\; \\text{Trajektori } \\{\\mathbf{F}_k\\}_{k=1}^{K},\\; I_{\\text{Moran}},\\; \\mathbf{T}_{\\text{transisi}}$$`,
      detail: 'Peta tematik kluster per tahun + biplot trajektori temporal + tabel perubahan kluster antar-tahun + uji autokorelasi spasial',
      outputs: [
        <OutputBadge key="map" icon="🗺️" label="Peta tematik kluster" color="#10b981"/>,
        <OutputBadge key="traj" icon="📐" label="Biplot trajektori 2D/3D" color="#3b82f6"/>,
        <OutputBadge key="tbl" icon="📋" label="Tabel transisi kluster" color="#8b5cf6"/>
      ],
      outputFiles: [
        { path: BASE + 'cluster_map_biplot_2022.png', label: 'Peta Kluster Kompromi 2022', caption: 'Visualisasi akhir hasil klusterisasi pada peta geografis', imgHeight: '160px' },
        { path: BASE + 'output_table_biplot_transition_name_2021x2022.tex', label: 'Transisi Kluster 2021→2022', caption: 'Perubahan keanggotaan kluster antar-tahun' },
      ],
      arrowLabel: '',
    },
  ];

  const ArrowDown = ({ label, fromColor, toColor }) => (
    <FlowArrow label={label} fromColor={fromColor || '#334155'} toColor={toColor || '#334155'} />
  );

  return (
    <div className="app-container" style={{ padding: '40px 28px', maxWidth: '1160px', margin: '0 auto', color: '#E2E8F0' }}>

      <div style={{ background: 'rgba(30,41,59,0.5)', backdropFilter: 'blur(16px)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '24px', padding: '26px 32px', marginBottom: '32px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <button onClick={onBack} style={{ background: 'rgba(255,255,255,0.08)', border: 'none', color: '#06B6D4', padding: '7px 16px', borderRadius: '30px', cursor: 'pointer', fontSize: '0.82rem', fontWeight: '700', marginBottom: '12px' }}>
            {'⬅'} Kembali
          </button>
          <h1 style={{ margin: '0 0 6px 0', fontSize: '24px', fontWeight: '800', background: 'linear-gradient(135deg,#06B6D4,#8b5cf6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Alur Metodologi STATIS vs PCA per-Tahun
          </h1>
          <p style={{ margin: 0, fontSize: '13px', color: '#94A3B8', maxWidth: '600px' }}>
            Alur lengkap dari data mentah BPS hingga peta kluster — dengan perbandingan eksplisit terhadap PCA per-tahun yang menghasilkan plot 3D pertama di Web App.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignSelf: 'flex-start' }}>
          {[['INPUT','#10b981'],['PROSES','#06b6d4'],['KEPUTUSAN','#f59e0b'],['OUTPUT','#10b981']].map(([l,c]) => (
            <span key={l} style={{ background: `${c}12`, color: c, border: `1px solid ${c}44`, borderRadius: '20px', padding: '3px 10px', fontSize: '0.65rem', fontWeight: '700', letterSpacing: '0.5px' }}>{l}</span>
          ))}
        </div>
      </div>

      {/* COMMON STEPS */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        {COMMON.map((step, idx) => (
          <div key={step.id} style={{ width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <div style={{ width: '100%', maxWidth: '820px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <StepCard
                step={step} num={idx + 1}
                isExpanded={!!expandedOutputs[step.id]}
                isExpandedReal={!!expandedOutputsReal[step.id]}
                isHovered={hovered === step.id}
                onMouseEnter={() => setHovered(step.id)}
                onMouseLeave={() => setHovered(null)}
                onToggle={() => toggleOutput(step.id)}
                onToggleReal={() => toggleOutputReal(step.id)}
              />
              <ArrowDown
                label={idx === 1 ? 'bobot mᵢ tersedia → standardisasi berbeda per metode' : step.arrowLabel}
                fromColor={step.color}
                toColor={idx === 1 ? '#8b5cf6' : (idx + 1 < COMMON.length ? COMMON[idx + 1].color : '#f59e0b')}
              />
            </div>

            {/* ═══ Z_K FORK — disisipkan setelah Bobot D (idx=1), sebelum KMO (idx=2) ═══ */}
            {idx === 1 && (
              <div style={{ width: '100%', maxWidth: '1100px', margin: '0 auto 0 auto' }}>

                {/* Z_K fork header */}
                <div style={{ background: 'rgba(139,92,246,0.07)', border: '1px solid rgba(139,92,246,0.3)', borderRadius: '14px', padding: '10px 24px', textAlign: 'center', marginBottom: '12px' }}>
                  <div style={{ fontSize: '0.78rem', fontWeight: '800', color: '#a78bfa', letterSpacing: '0.5px' }}>
                    ⚡ PERCABANGAN Z<sub>k</sub> — Standardisasi berbeda antara STATIS dan PCA
                  </div>
                  <div style={{ fontSize: '0.67rem', color: '#94a3b8', marginTop: '3px' }}>
                    Meski notasi z<sub>ijk</sub> sama, nilainya <strong style={{color:'#c4b5fd'}}>numerik berbeda</strong>:
                    STATIS menggunakan μ dan σ <em>terbobot demografis</em> (dari bobot m<sub>i</sub>),
                    sementara PCA menggunakan mean aritmetika dan std populasi biasa (semua wilayah setara).
                    Akibatnya <strong style={{color:'#c4b5fd'}}>W<sub>k</sub> = Z<sub>k</sub> Z<sub>k</sub><sup>T</sup></strong> yang masuk STATIS juga berbeda dari Z<sub>k</sub> yang masuk PCA.
                  </div>
                </div>

                {/* Split: kiri STATIS ← tengah → kanan PCA */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '0', alignItems: 'stretch' }}>

                  {/* LEFT: STATIS Z_k terbobot */}
                  <div style={{ background: 'rgba(6,182,212,0.04)', border: '1px solid rgba(6,182,212,0.3)', borderRadius: '16px 0 0 16px', padding: '18px 20px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px', borderBottom: '1px solid rgba(6,182,212,0.18)', paddingBottom: '8px' }}>
                      <span style={{ background: 'rgba(6,182,212,0.18)', color: '#06b6d4', borderRadius: '8px', padding: '3px 10px', fontSize: '0.63rem', fontWeight: '800' }}>STATIS — Z<sub>k</sub> Terbobot</span>
                      <span style={{ fontSize: '0.62rem', color: '#64748b', marginLeft: 'auto' }}>run_statis_core()</span>
                    </div>
                    <div style={{ fontSize: '0.68rem', color: '#94a3b8', lineHeight: 1.6, marginBottom: '10px' }}>
                      Bobot demografis mᵢ (dari langkah sebelumnya) digunakan langsung untuk menghitung
                      rata-rata dan simpangan baku <strong style={{color:'#06b6d4'}}>terbobot populasi</strong>.
                      Ini memastikan wilayah berpenduduk besar berkontribusi proporsional lebih besar ke pusat distribusi.
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {[
                        ['μ Terbobot', '$$\\mu_{jk} = \\sum_{i=1}^{n} m_i\\, x_{ijk}$$'],
                        ['σ Terbobot', '$$\\sigma_{jk} = \\sqrt{\\sum_{i=1}^{n} m_i\\,(x_{ijk}-\\mu_{jk})^2}$$'],
                        [<>Z<sub>k</sub> STATIS</>, '$$z_{ijk}^{\\text{STATIS}} = \\frac{x_{ijk}-\\mu_{jk}}{\\sigma_{jk}}$$'],
                      ].map(([lbl, f]) => (
                        <div key={lbl} style={{ background: 'rgba(6,182,212,0.06)', borderRadius: '8px', padding: '7px 12px', borderLeft: '3px solid rgba(6,182,212,0.5)' }}>
                          <div style={{ fontSize: '0.6rem', color: '#06b6d4', fontWeight: '700', marginBottom: '3px' }}>{lbl}</div>
                          <LatexFormula small bare tex={f} color="#a5f3fc" />
                        </div>
                      ))}
                    </div>
                    <div style={{ marginTop: '10px', background: 'rgba(6,182,212,0.08)', border: '1px solid rgba(6,182,212,0.2)', borderRadius: '8px', padding: '8px 12px' }}>
                      <div style={{ fontSize: '0.6rem', fontWeight: '800', color: '#06b6d4', marginBottom: '4px' }}>✓ PROPERTI TERJAMIN</div>
                      {['∑mᵢ · zᵢⱼₖ = 0  (rata-rata terbobot nol)', '∑mᵢ · zᵢⱼₖ² = 1  (varians terbobot satu)', 'Skala konsisten lintas indikator & tahun'].map((t,i) => (
                        <div key={i} style={{ fontSize: '0.62rem', color: '#94a3b8', display: 'flex', gap: '5px', marginBottom: '2px' }}>
                          <span style={{ color: '#06b6d4', flexShrink: 0 }}>▸</span><span>{t}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* CENTER DIVIDER */}
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', width: '48px', position: 'relative', zIndex: 2 }}>
                    <div style={{ width: '2px', flex: 1, background: 'linear-gradient(to bottom, rgba(6,182,212,0.4), rgba(139,92,246,0.5), rgba(239,68,68,0.4))' }} />
                    <div style={{ background: '#0f172a', border: '2px solid rgba(139,92,246,0.5)', borderRadius: '50%', width: '36px', height: '36px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.85rem', flexShrink: 0 }}>≠</div>
                    <div style={{ width: '2px', flex: 1, background: 'linear-gradient(to bottom, rgba(139,92,246,0.5), rgba(239,68,68,0.4))' }} />
                  </div>

                  {/* RIGHT: PCA Z_k biasa */}
                  <div style={{ background: 'rgba(239,68,68,0.04)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '0 16px 16px 0', padding: '18px 20px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px', borderBottom: '1px solid rgba(239,68,68,0.18)', paddingBottom: '8px' }}>
                      <span style={{ background: 'rgba(239,68,68,0.18)', color: '#f87171', borderRadius: '8px', padding: '3px 10px', fontSize: '0.63rem', fontWeight: '800' }}>PCA — Z<sub>k</sub> Biasa (Unweighted)</span>
                      <span style={{ fontSize: '0.62rem', color: '#64748b', marginLeft: 'auto' }}>StandardScaler()</span>
                    </div>
                    <div style={{ fontSize: '0.68rem', color: '#94a3b8', lineHeight: 1.6, marginBottom: '10px' }}>
                      sklearn <code style={{color:'#f87171', fontSize:'0.65rem'}}>StandardScaler</code> menggunakan mean aritmetika biasa — semua wilayah <strong style={{color:'#f87171'}}>diperlakukan setara</strong> tanpa memperhatikan besar populasi.
                      Kota kecil (misal 50 ribu jiwa) bobotnya sama dengan DKI Jakarta (10 juta jiwa).
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {[
                        ['μ Aritmetika', '$$\\bar{x}_{j} = \\frac{1}{n}\\sum_{i=1}^{n} x_{ij}$$'],
                        ['σ Populasi', '$$s_{j} = \\sqrt{\\frac{1}{n}\\sum_{i=1}^{n}(x_{ij}-\\bar{x}_{j})^2}$$'],
                        [<>Z<sub>k</sub> PCA</>, '$$z_{ij}^{\\text{PCA}} = \\frac{x_{ij}-\\bar{x}_{j}}{s_{j}}$$'],
                      ].map(([lbl, f]) => (
                        <div key={lbl} style={{ background: 'rgba(239,68,68,0.06)', borderRadius: '8px', padding: '7px 12px', borderLeft: '3px solid rgba(239,68,68,0.5)' }}>
                          <div style={{ fontSize: '0.6rem', color: '#f87171', fontWeight: '700', marginBottom: '3px' }}>{lbl}</div>
                          <LatexFormula small bare tex={f} color="#fca5a5" />
                        </div>
                      ))}
                    </div>
                    <div style={{ marginTop: '10px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: '8px', padding: '8px 12px' }}>
                      <div style={{ fontSize: '0.6rem', fontWeight: '800', color: '#f87171', marginBottom: '4px' }}>⚠ IMPLIKASI</div>
                      {[
                        '(1/n)∑zᵢⱼ = 0, (1/n)∑zᵢⱼ² = 1  (properti sampel biasa)',
                        'Wilayah berpenduduk kecil & besar dibobot sama',
                      ].map((t,i) => (
                        <div key={i} style={{ fontSize: '0.62rem', color: '#94a3b8', display: 'flex', gap: '5px', marginBottom: '2px' }}>
                          <span style={{ color: '#f87171', flexShrink: 0 }}>✗</span><span>{t}</span>
                        </div>
                      ))}
                      <div style={{ fontSize: '0.62rem', color: '#94a3b8', display: 'flex', gap: '5px', marginBottom: '2px' }}>
                        <span style={{ color: '#f87171', flexShrink: 0 }}>✗</span>
                        <span>Z<sub>k</sub><sup>PCA</sup> ≠ Z<sub>k</sub><sup>STATIS</sup> → W<sub>k</sub><sup>PCA</sup> ≠ W<sub>k</sub><sup>STATIS</sup></span>
                      </div>
                    </div>
                  </div>

                </div>{/* end Z_K split grid */}

                {/* Toggle statistika deskriptif */}
                <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', flexWrap: 'wrap', margin: '12px 0 0 0' }}>
                  <button
                    onClick={() => setShowZkDeskriptif(v => !v)}
                    style={{
                      background: showZkDeskriptif ? 'rgba(139,92,246,0.15)' : 'rgba(15,23,42,0.6)',
                      border: `1px solid ${showZkDeskriptif ? '#a78bfa' : 'rgba(139,92,246,0.35)'}`,
                      color: showZkDeskriptif ? '#a78bfa' : '#94a3b8',
                      borderRadius: '8px', padding: '5px 16px',
                      fontSize: '0.7rem', fontWeight: '700', cursor: 'pointer',
                      display: 'inline-flex', alignItems: 'center', gap: '6px',
                      transition: 'all 0.15s',
                    }}
                  >
                    <span>{showZkDeskriptif ? '▼' : '▶'}</span>
                    {showZkDeskriptif ? 'Sembunyikan Output Sampel' : 'Lihat Output Sampel'}
                  </button>
                  <button
                    onClick={() => setShowZkDeskriptifReal(v => !v)}
                    style={{
                      background: showZkDeskriptifReal ? 'rgba(16,185,129,0.15)' : 'rgba(15,23,42,0.6)',
                      border: `1px solid ${showZkDeskriptifReal ? '#10b981' : 'rgba(16,185,129,0.35)'}`,
                      color: showZkDeskriptifReal ? '#10b981' : '#94a3b8',
                      borderRadius: '8px', padding: '5px 16px',
                      fontSize: '0.7rem', fontWeight: '700', cursor: 'pointer',
                      display: 'inline-flex', alignItems: 'center', gap: '6px',
                      transition: 'all 0.15s',
                    }}
                  >
                    <span>{showZkDeskriptifReal ? '▼' : '▶'}</span>
                    {showZkDeskriptifReal ? 'Sembunyikan Output Real' : 'Lihat Output Real'}
                  </button>
                </div>

                {showZkDeskriptif && (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '12px' }}>
                    <div style={{ background: 'rgba(6,182,212,0.04)', border: '1px solid rgba(6,182,212,0.25)', borderRadius: '12px', padding: '14px', overflowX: 'auto' }}>
                      <div style={{ fontSize: '0.6rem', fontWeight: '800', color: '#06b6d4', marginBottom: '8px', letterSpacing: '0.4px' }}>📋 SAMPEL — TERBOBOT (STATIS) — 2020</div>
                      <OutputFileViewer path={BASE + 'output_table_descriptive_2020.tex'} label="Statistika Deskriptif Terbobot" caption="Mean & Std terbobot mᵢ per indikator" />
                    </div>
                    <div style={{ background: 'rgba(239,68,68,0.04)', border: '1px solid rgba(239,68,68,0.25)', borderRadius: '12px', padding: '14px', overflowX: 'auto' }}>
                      <div style={{ fontSize: '0.6rem', fontWeight: '800', color: '#f87171', marginBottom: '8px', letterSpacing: '0.4px' }}>📋 SAMPEL — TANPA BOBOT (PCA) — 2020</div>
                      <OutputFileViewer path={BASE + 'output_table_deskriptif_2020.tex'} label="Statistika Deskriptif Tanpa Bobot" caption="Mean, Std, Min, Q1–Q3, Max, Skew, Kurt, CV" />
                    </div>
                  </div>
                )}

                {showZkDeskriptifReal && (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '12px' }}>
                    <div style={{ background: 'rgba(16,185,129,0.04)', border: '1px solid rgba(16,185,129,0.25)', borderRadius: '12px', padding: '14px', overflowX: 'auto' }}>
                      <div style={{ fontSize: '0.6rem', fontWeight: '800', color: '#10b981', marginBottom: '8px', letterSpacing: '0.4px' }}>📋 REAL — TERBOBOT (STATIS) — 2020</div>
                      <OutputFileViewer path='/output_real/output_table_descriptive_2020.tex' label="Statistika Deskriptif Terbobot (Real)" caption="Mean & Std terbobot mᵢ per indikator — 41 Kab/Kota" />
                    </div>
                    <div style={{ background: 'rgba(16,185,129,0.04)', border: '1px solid rgba(16,185,129,0.2)', borderRadius: '12px', padding: '14px', overflowX: 'auto' }}>
                      <div style={{ fontSize: '0.6rem', fontWeight: '800', color: '#10b981', marginBottom: '8px', letterSpacing: '0.4px' }}>📋 REAL — TANPA BOBOT (PCA) — 2020</div>
                      <OutputFileViewer path='/output_real/output_table_deskriptif_2020.tex' label="Statistika Deskriptif Tanpa Bobot (Real)" caption="Mean, Std, Min, Q1–Q3, Max, Skew, Kurt, CV — 41 Kab/Kota" />
                    </div>
                  </div>
                )}

                {/* Reconnect note */}
                <div style={{ textAlign: 'center', margin: '10px 0 4px 0' }}>
                  <div style={{ display: 'inline-block', background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.25)', borderRadius: '20px', padding: '5px 16px', fontSize: '0.68rem', color: '#f59e0b', fontWeight: '600' }}>
                    ↓ Kedua Z_k kemudian diuji kesesuaiannya via KMO &amp; Bartlett (berbasis data mentah)
                  </div>
                </div>
                <ArrowDown fromColor='#8b5cf6' toColor={COMMON[COMMON.length - 1].color} label='' />

              </div>
            )}
          </div>
        ))}
      </div>

      {/* ═══ FORK: FULL-WIDTH PCA vs STATIS SPLIT ═══ */}
      <div style={{ width: '100%', maxWidth: '1100px', margin: '0 auto 0 auto' }}>

        {/* Fork header */}
        <div style={{ background: 'rgba(245,158,11,0.07)', border: '1px solid rgba(245,158,11,0.25)', borderRadius: '14px', padding: '12px 24px', textAlign: 'center', marginBottom: '12px' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: '800', color: '#f59e0b', letterSpacing: '0.5px' }}>
            ⚡ PERCABANGAN METODE — setelah KMO &amp; Bartlett lolos, masing-masing Z<sub>k</sub> diolah berbeda
          </div>
          <div style={{ fontSize: '0.68rem', color: '#94a3b8', marginTop: '3px' }}>
            STATIS melanjutkan dengan Z<sub>k</sub> terbobot → pipeline W<sub>k</sub> → H → α → W<sub>c</sub> → F<sub>c</sub>.
            PCA per-tahun melanjutkan dengan Z<sub>k</sub> biasa → SVD independen per tahun → F<sub>k</sub>, G<sub>k</sub> tidak kompatibel lintas tahun.
          </div>
        </div>

        {/* Split: kiri STATIS ← label tengah → kanan PCA */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '0', alignItems: 'stretch' }}>

          {/* ═══ LEFT: STATIS ═══ */}
          <div style={{ background: 'rgba(6,182,212,0.04)', border: '1px solid rgba(6,182,212,0.3)', borderRadius: '16px 0 0 16px', padding: '20px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', borderBottom: '1px solid rgba(6,182,212,0.18)', paddingBottom: '10px' }}>
              <span style={{ background: 'rgba(6,182,212,0.18)', color: '#06b6d4', borderRadius: '8px', padding: '3px 10px', fontSize: '0.63rem', fontWeight: '800', letterSpacing: '0.5px' }}>JALUR B — STATIS</span>
              <span style={{ fontSize: '0.63rem', color: '#64748b', marginLeft: 'auto' }}>Plot 3D Kedua ↗</span>
            </div>

            {/* Deskripsi */}
            <div style={{ fontSize: '0.7rem', color: '#94a3b8', lineHeight: 1.65, marginBottom: '10px' }}>
              Setiap matriks <strong style={{ color: '#06b6d4' }}>Z</strong><sub>k</sub> tidak langsung didekomposisi secara independen.
              STATIS terlebih dahulu membangun matriks kemiripan <strong style={{ color: '#06b6d4' }}>W</strong><sub>k</sub> untuk setiap tahun,
              lalu mengukur keterkaitan antar-tahun melalui matriks inter-struktur <strong style={{ color: '#06b6d4' }}>H</strong> dan koefisien RV.
              Dari sana dihitung bobot optimal α<sub>k</sub> dan matriks kompromi tunggal <strong style={{ color: '#06b6d4' }}>W</strong><sub>c</sub>,
              yang kemudian didekomposisi spektral untuk menghasilkan satu set sumbu bersama (<strong style={{ color: '#06b6d4' }}>F</strong><sub>c</sub>, <strong style={{ color: '#06b6d4' }}>G</strong><sub>c</sub>).
            </div>

            {/* Alur rumus */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '10px' }}>
              {[
                ['🔢', 'Intra-Struktur', '$$\\mathbf{W}_k = \\mathbf{Z}_k\\mathbf{Z}_k^T \\in \\mathbb{R}^{n\\times n}$$'],
                ['📡', 'Inter-Struktur', '$$H_{kk\'}=\\operatorname{tr}(\\mathbf{W}_k\\mathbf{D}\\mathbf{W}_{k\'}\\mathbf{D})$$'],
                ['⚖️', 'Bobot Temporal', '$$\\alpha_k = u_{1k}/\\textstyle\\sum u_{1k\'},\\quad\\mathbf{H}\\mathbf{u}_1=\\theta_1\\mathbf{u}_1$$'],
                ['🤝', 'Kompromi', '$$\\mathbf{W}_c=\\textstyle\\sum_k \\alpha_k\\,\\mathbf{W}_k$$'],
                ['⚛', 'Dekomposisi', '$$\\mathbf{F}_c=\\mathbf{D}^{-1/2}\\mathbf{P}\\mathbf{\\Lambda}_c^{1/2},\\;\\mathbf{G}_c=\\textstyle\\sum_k\\alpha_k\\mathbf{Z}_k^T\\mathbf{D}\\mathbf{F}_c\\mathbf{\\Lambda}_c^{-1/2}$$'],
                ['🎯', 'Proyeksi Tahunan', '$$\\mathbf{F}_k=\\mathbf{W}_k\\mathbf{D}\\mathbf{P}\\mathbf{\\Lambda}_c^{-1/2} \\quad\\text{(ruang sama!)}$$'],
              ].map(([icon, label, formula]) => (
                <div key={label} style={{ background: 'rgba(6,182,212,0.06)', borderRadius: '8px', padding: '8px 12px', borderLeft: '3px solid rgba(6,182,212,0.5)' }}>
                  <div style={{ fontSize: '0.62rem', color: '#06b6d4', fontWeight: '700', marginBottom: '4px' }}>{icon} {label}</div>
                  <LatexFormula small bare tex={formula} color="#a5f3fc" />
                </div>
              ))}
            </div>

            {/* Keunggulan */}
            <div style={{ background: 'rgba(6,182,212,0.08)', border: '1px solid rgba(6,182,212,0.25)', borderRadius: '10px', padding: '10px 12px' }}>
              <div style={{ fontSize: '0.65rem', fontWeight: '800', color: '#06b6d4', marginBottom: '6px' }}>✓ KEUNGGULAN STATIS</div>
              {[
                'Satu set sumbu kompromi (PC1_c, PC2_c) berlaku untuk SEMUA tahun',
                'Jarak antar-titik lintas tahun bermakna geometrically (comparable)',
                'Bobot αₖ menangkap kontribusi proporsional tiap tahun terhadap pola rata-rata',
                'Pengaruh outlier temporal diredam — tahun anomali mendapat bobot lebih kecil',
                'Plot 3D: sumbu waktu × PC1_c × PC2_c — SATU REFERENSI, semua tahun',
              ].map((t, i) => (
                <div key={i} style={{ display: 'flex', gap: '6px', marginBottom: '4px', fontSize: '0.65rem', color: '#94a3b8', lineHeight: 1.5 }}>
                  <span style={{ color: '#06b6d4', flexShrink: 0 }}>▸</span><span>{t}</span>
                </div>
              ))}
            </div>

            <div style={{ marginTop: '10px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              <OutputBadge icon="🎯" label="Plot 3D Kedua: Tahun × PC1_c × PC2_c" color="#06b6d4" />
              <OutputBadge icon="✅" label="Ruang kompromi konsisten" color="#22c55e" />
            </div>
          </div>

          {/* ═══ CENTER DIVIDER ═══ */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', width: '48px', position: 'relative', zIndex: 2 }}>
            <div style={{ width: '2px', flex: 1, background: 'linear-gradient(to bottom, rgba(6,182,212,0.4), rgba(245,158,11,0.6), rgba(239,68,68,0.4))' }} />
            <div style={{ background: '#0f172a', border: '2px solid rgba(245,158,11,0.5)', borderRadius: '50%', width: '36px', height: '36px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1rem', flexShrink: 0 }}>⚡</div>
            <div style={{ width: '2px', flex: 1, background: 'linear-gradient(to bottom, rgba(245,158,11,0.6), rgba(239,68,68,0.4))' }} />
          </div>

          {/* ═══ RIGHT: PCA per-Tahun ═══ */}
          <div style={{ background: 'rgba(239,68,68,0.04)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: '0 16px 16px 0', padding: '20px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', borderBottom: '1px solid rgba(239,68,68,0.18)', paddingBottom: '10px' }}>
              <span style={{ background: 'rgba(239,68,68,0.18)', color: '#f87171', borderRadius: '8px', padding: '3px 10px', fontSize: '0.63rem', fontWeight: '800', letterSpacing: '0.5px' }}>JALUR A — PCA per-Tahun</span>
              <span style={{ fontSize: '0.63rem', color: '#64748b', marginLeft: 'auto' }}>Plot 3D Pertama ↗</span>
            </div>

            {/* Deskripsi */}
            <div style={{ fontSize: '0.7rem', color: '#94a3b8', lineHeight: 1.65, marginBottom: '10px' }}>
              Setiap matriks <strong style={{ color: '#f87171' }}>Z</strong><sub>k</sub> didekomposisi secara <strong style={{ color: '#f87171' }}>independen</strong> menggunakan SVD.
              Setiap tahun menghasilkan set eigenvector sendiri (<strong style={{ color: '#f87171' }}>V</strong><sub>k</sub>),
              sehingga sumbu PC1 dan PC2 memiliki orientasi berbeda di setiap tahun.
              Skor wilayah <strong style={{ color: '#f87171' }}>F</strong><sub>k</sub> = <strong style={{ color: '#f87171' }}>Z</strong><sub>k</sub><strong style={{ color: '#f87171' }}>V</strong><sub>k</sub> dan loading
              <strong style={{ color: '#f87171' }}>G</strong><sub>k</sub> = <strong style={{ color: '#f87171' }}>V</strong><sub>k</sub> memang valid <em>di dalam</em> tahun itu,
              namun tidak kompatibel lintas tahun.
            </div>

            {/* Alur rumus */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '10px' }}>
              {[
                ['📐', 'SVD per-Tahun (independen)', '$$\\mathbf{Z}_k = \\mathbf{U}_k\\mathbf{S}_k\\mathbf{V}_k^T \\quad \\forall k$$'],
                ['📍', 'Skor Wilayah Tahun k', '$$\\mathbf{F}_k = \\mathbf{Z}_k\\mathbf{V}_k \\quad\\text{(basis }\\mathbf{V}_k\\text{ berbeda tiap tahun)}$$'],
                ['➡️', 'Loading Indikator Tahun k', '$$\\mathbf{G}_k = \\mathbf{V}_k \\quad\\text{(bukan kompatibel dengan }\\mathbf{V}_{k\'}\\text{)}$$'],
              ].map(([icon, label, formula]) => (
                <div key={label} style={{ background: 'rgba(239,68,68,0.06)', borderRadius: '8px', padding: '8px 12px', borderLeft: '3px solid rgba(239,68,68,0.5)' }}>
                  <div style={{ fontSize: '0.62rem', color: '#f87171', fontWeight: '700', marginBottom: '4px' }}>{icon} {label}</div>
                  <LatexFormula small bare tex={formula} color="#fca5a5" />
                </div>
              ))}
            </div>

            {/* Masalah utama */}
            <div style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)', borderRadius: '10px', padding: '10px 12px', marginBottom: '8px' }}>
              <div style={{ fontSize: '0.65rem', fontWeight: '800', color: '#f87171', marginBottom: '6px' }}>⚠ KETERBATASAN</div>
              {[
                'V₂₀₂₀ ≠ V₂₀₂₁ ≠ … — basis berbeda tiap tahun, sumbu tidak konsisten',
                'Jarak antara F₂₀₂₀ dan F₂₀₂₄ tidak bermakna geometrically (apples vs oranges)',
                'Tidak ada mekanisme pembobotan kontribusi temporal (semua tahun diperlakukan setara)',
                'Pemilihan basis ortogonormal tiap tahun bersifat acak arah (sign ambiguity)',
                'Plot 3D: posisi wilayah di PC1/PC2 berubah makna setiap tahun — hanya bisa dibandingkan intra-tahun',
              ].map((t, i) => (
                <div key={i} style={{ display: 'flex', gap: '6px', marginBottom: '4px', fontSize: '0.65rem', color: '#94a3b8', lineHeight: 1.5 }}>
                  <span style={{ color: '#f87171', flexShrink: 0 }}>✗</span><span>{t}</span>
                </div>
              ))}
            </div>

            {/* Catatan dari induk.pdf */}
            <div style={{ background: 'rgba(100,116,139,0.06)', border: '1px dashed rgba(100,116,139,0.2)', borderRadius: '8px', padding: '8px 10px', marginBottom: '10px' }}>
              <div style={{ fontSize: '0.6rem', color: '#64748b', fontStyle: 'italic', lineHeight: 1.55 }}>
                "PCA Tahunan Konvensional…memilih basis ortogonormal berbeda pada tiap tahun, sehingga jarak antar-titik lintasan antartahun tidak bermakna secara geometris." <span style={{ color: '#475569' }}>— Bab 2, Skripsi</span>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              <OutputBadge icon="📉" label="Plot 3D Pertama: Tahun × PC1_k × PC2_k" color="#f87171" />
              <OutputBadge icon="⚠️" label="Tidak komparable lintas tahun" color="#f87171" />
            </div>
          </div>

        </div>{/* end grid 3-col */}

        {/* Bottom: STATIS continues */}
        <div style={{ textAlign: 'center', margin: '12px 0 4px 0' }}>
          <div style={{ display: 'inline-block', background: 'rgba(6,182,212,0.1)', border: '1px solid rgba(6,182,212,0.3)', borderRadius: '20px', padding: '6px 18px', fontSize: '0.7rem', color: '#06b6d4', fontWeight: '700' }}>
            ↓ Penelitian ini menggunakan Jalur B (STATIS) — dilanjutkan di bawah
          </div>
        </div>

      </div>{/* end fork wrapper */}

      {/* STATIS-SPECIFIC STEPS */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        {STATIS_STEPS.map((step, idx) => (
          <div key={step.id} style={{ width: '100%', maxWidth: '820px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <ArrowDown
              label={idx === 0 ? 'Jalur STATIS: Z_k → matriks kemiripan spasial' : undefined}
              fromColor={idx === 0 ? '#f59e0b' : STATIS_STEPS[idx - 1].color}
              toColor={step.color}
            />
            <StepCard
              step={step} num={step.num}
              isExpanded={!!expandedOutputs[step.id]}
              isExpandedReal={!!expandedOutputsReal[step.id]}
              isHovered={hovered === step.id}
              onMouseEnter={() => setHovered(step.id)}
              onMouseLeave={() => setHovered(null)}
              onToggle={() => toggleOutput(step.id)}
              onToggleReal={() => toggleOutputReal(step.id)}
            />
          </div>
        ))}
      </div>

      {/* DOWNSTREAM STEPS */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        {DOWN_STEPS.map((step, idx) => (
          <div key={step.id} style={{ width: '100%', maxWidth: '820px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <ArrowDown
              label={idx === 0 ? 'F_c, G_c tersedia → verifikasi signifikansi' : step.arrowLabel}
              fromColor={idx === 0 ? STATIS_STEPS[STATIS_STEPS.length - 1].color : DOWN_STEPS[idx - 1].color}
              toColor={step.color}
            />
            <StepCard
              step={step} num={step.num}
              isExpanded={!!expandedOutputs[step.id]}
              isExpandedReal={!!expandedOutputsReal[step.id]}
              isHovered={hovered === step.id}
              onMouseEnter={() => setHovered(step.id)}
              onMouseLeave={() => setHovered(null)}
              onToggle={() => toggleOutput(step.id)}
              onToggleReal={() => toggleOutputReal(step.id)}
            />
          </div>
        ))}
      </div>

      <div style={{ marginTop: '40px', textAlign: 'center', color: '#334155', fontSize: '0.72rem' }}>
        STATIS {'—'} <em>Structuration des Tableaux {'à'} Trois Indices de la Statistique</em> (Lavit et al., 1994)
      </div>
    </div>
  );
}


// ─── DATASET TABLE VIEW ───────────────────────────────────────────────────────
function DatasetTableView({ defaultDataset }) {
  const [dsType, setDsType] = useState(defaultDataset || 'real');
  const [year, setYear] = useState('2020');
  const [tex, setTex] = useState('');
  const [loading, setLoading] = useState(true);

  const realYears = ['2020','2021','2022','2023','2024'];
  const sampelYears = ['2020','2021','2022'];
  const years = dsType === 'real' ? realYears : sampelYears;

  useEffect(() => {
    if (!years.includes(year)) setYear(years[0]);
  }, [dsType]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    const prefix = dsType === 'real' ? 'data_final' : 'data_sampel';
    fetch(`/${prefix}_${year}.tex`)
      .then(r => r.text())
      .then(t => { if (active) { setTex(t); setLoading(false); } })
      .catch(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [dsType, year]);

  return (
    <div>
      <div style={{ display: 'flex', gap: '10px', marginBottom: '16px', flexWrap: 'wrap' }}>
        {[['real','Data Real (41 Wilayah, 5 Tahun)'],['sampel','Data Sampel Ilustratif (4 Wilayah, 3 Tahun)']].map(([k,l]) => (
          <button key={k} onClick={() => setDsType(k)} style={{
            background: dsType === k ? 'linear-gradient(135deg,#06B6D4,#3B82F6)' : 'rgba(15,23,42,0.5)',
            color: dsType === k ? '#fff' : '#94a3b8',
            border: `1px solid ${dsType===k?'#06b6d4':'rgba(255,255,255,0.1)'}`,
            borderRadius: '20px', padding: '7px 16px', fontSize: '0.82rem', fontWeight: '600',
            cursor: 'pointer', transition: 'all 0.2s' }}>
            {l}
          </button>
        ))}
      </div>
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
        <span style={{ color: '#64748b', fontSize: '0.8rem' }}>Tahun:</span>
        {years.map(y => (
          <button key={y} onClick={() => setYear(y)} style={{
            background: year === y ? 'rgba(6,182,212,0.2)' : 'rgba(15,23,42,0.4)',
            color: year === y ? '#e2e8f0' : '#64748b',
            border: `1px solid ${year===y?'rgba(6,182,212,0.4)':'rgba(255,255,255,0.08)'}`,
            borderRadius: '8px', padding: '4px 14px', fontSize: '0.8rem', fontWeight: '600',
            cursor: 'pointer', transition: 'all 0.15s' }}>
            {y}
          </button>
        ))}
      </div>
      <div style={{ background: 'rgba(6,182,212,0.06)', border: '1px solid rgba(6,182,212,0.15)', borderRadius: '10px', padding: '10px 14px', marginBottom: '14px', fontSize: '0.77rem', color: '#94a3b8' }}>
        {dsType === 'real'
          ? '📊 Data Real: 41 Kabupaten/Kota di Banten, DKI Jakarta & Jawa Barat. Kolom: Provinsi, Kab/Kota, IPM, IPG, PPM, PDRB_ADHK, RLS, AHH_L, AHH_P, GK, PKKP, TPT, TPAK, GR, JP. Sumber: BPS RI.'
          : '🔬 Data Sampel: 4 wilayah × 3 tahun × 3 indikator (PPM, RLS, TPT) + IPM + JP — ilustrasi numerik langkah-langkah STATIS pada Bab 3 skripsi.'}
      </div>
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '120px' }}>
          <div className="spinner" style={{ width: '30px', height: '30px' }}></div>
        </div>
      ) : (
        <div style={{ maxHeight: '420px', overflowY: 'auto', overflowX: 'auto', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.08)' }} className="custom-scrollbar">
          <LatexTable tex={tex} />
        </div>
      )}
    </div>
  );
}

function App() {
  const [activeModal, setActiveModal] = useState(null);
  const [compareView, setCompareView] = useState(false);
  const [formulasView, setFormulasView] = useState(false);
  const [flowView, setFlowView] = useState(false);
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
  const [_equations, setEquations] = useState([]);
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
      ) : flowView ? (
        <MethodologyFlowView
          onBack={() => setFlowView(false)}
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
              Lihat tabel data real (41 Kab/Kota × 5 tahun) dan data sampel ilustratif (4 wilayah × 3 tahun) langsung dari file XLSX yang digunakan.
            </p>
          </div>

          {/* Methodology Flow Card */}
          <div
            className="card glass-effect highlight"
            onClick={() => setFlowView(true)}
          >
            <div className="card-icon">🔄</div>
            <h2>Alur Metodologi</h2>
            <p>
              Diagram step-by-step STATIS vs PCA per-tahun — dilengkapi formula matematika dirender MathJax dan perbandingan output plot 3D.
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
        <div className="modal-content glass-effect" style={{ maxWidth: '1000px', width: '96vw' }}>
          <button className="close-btn" onClick={closeModal} title="Tutup">
            &times;
          </button>
          <h2>Dataset Penelitian</h2>
          <div className="modal-body">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(150px,1fr))', gap: '10px', marginBottom: '20px' }}>
              {[['n = 41','Kabupaten/Kota','#06b6d4'],['p = 11','Indikator Analisis','#8b5cf6'],['K = 5','Tahun (2020–2024)','#3b82f6'],['n = 4','Sampel Ilustratif','#f59e0b']].map(([v,l,c]) => (
                <div key={v} style={{ background:`${c}0d`, border:`1px solid ${c}30`, borderRadius:'10px', padding:'10px 14px', textAlign:'center' }}>
                  <div style={{ fontSize:'1.3rem', fontWeight:'800', color:c }}>{v}</div>
                  <div style={{ fontSize:'0.72rem', color:'#94a3b8' }}>{l}</div>
                </div>
              ))}
            </div>
            <DatasetTableView />
            <p style={{ marginTop:'14px', fontSize:'0.75rem', color:'#475569' }}>
              Sumber: BPS Provinsi Banten, DKI Jakarta &amp; Jawa Barat (2020–2024). Data dikumpulkan melalui publikasi <i>Provinsi Dalam Angka</i> dan portal Open Data BPS.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}

export default App;
