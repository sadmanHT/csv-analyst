import React, { Component, useState, useRef, useEffect, useCallback, useMemo } from 'react'
import './App.css'
import {
  Logo, Sparkles, FileIcon, Search, Send, Paperclip, Check, X,
  Rows, Columns, AlertDot, Activity, Layers, Code, ChartUp, Brain,
  DollarSign, HeartPulse, ShoppingCart, Megaphone, Users,
  Zap, Terminal, Lock, Award, Eye, Download, FileText,
  Sliders, SlidersHorizontal, TrendingUp,
} from './icons.jsx'

// In production VITE_API_BASE_URL points to the Railway backend.
// In local dev it is empty and Vite proxies all API calls automatically.
const API = import.meta.env.VITE_API_BASE_URL ?? ''

function downloadBase64Payload(payload, fallbackFilename) {
  const binary = atob(payload.content_base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i)
  const blob = new Blob([bytes], { type: payload.media_type || 'application/octet-stream' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = payload.filename || fallbackFilename
  a.click()
  URL.revokeObjectURL(url)
}

function downloadJsonPayload(payload, filename) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

// ─── Domain categories (the differentiator) ────────────────────────────────────

const CATEGORIES = [
  {
    key: 'general', label: 'General', icon: ChartUp,
    blurb: 'Neutral statistical analysis',
    examples: [
      'Summarize the key statistics of this dataset',
      'Show a correlation heatmap of numeric columns',
      'Plot the distribution of each numeric column',
      'Show a bar chart of the top categories by count',
    ],
    suggested: [
      { label: 'Correlation Heatmap',  q: 'Show an annotated correlation heatmap of all numeric columns' },
      { label: 'Distributions',        q: 'Plot histograms of the distribution of each numeric column' },
      { label: 'Top Categories',       q: 'Show a bar chart of the top categories by count' },
      { label: 'Outlier Detection',    q: 'Show box plots to detect outliers in the numeric columns' },
      { label: 'Summary Statistics',   q: 'Give me a full summary statistics table for every column' },
      { label: 'Missing Values',       q: 'Show a bar chart of the percentage of missing values per column' },
    ],
  },
  {
    key: 'financial', label: 'Financial', icon: DollarSign,
    blurb: 'Revenue, growth, risk & ratios',
    examples: [
      'Plot total revenue over time as a line chart',
      'Show a bar chart of total revenue by category',
      'Calculate the period-over-period growth rate',
      'Show the volatility of the key numeric columns',
    ],
    suggested: [
      { label: 'Revenue Trend',        q: 'Plot total revenue over time as a line chart' },
      { label: 'Growth Rate',          q: 'Calculate and chart the period-over-period growth rate' },
      { label: 'Revenue by Category',  q: 'Show a bar chart of total revenue by category, sorted descending' },
      { label: 'Revenue by Region',    q: 'Show a bar chart of total revenue by region, sorted descending' },
      { label: 'Top Contributors',     q: 'Show a Pareto chart of the top revenue contributors' },
      { label: 'Risk / Volatility',    q: 'Show the standard deviation of the main numeric columns as a risk measure' },
    ],
  },
  {
    key: 'medical', label: 'Medical', icon: HeartPulse,
    blurb: 'Risk factors & patient cohorts',
    examples: [
      'Which features correlate most with the outcome?',
      'Show the age distribution split by outcome',
      'Compare each numeric feature between outcome groups',
      'Show a correlation heatmap of clinical measurements',
    ],
    suggested: [
      { label: 'Risk Factors',         q: 'Show a bar chart of how strongly each feature correlates with the outcome' },
      { label: 'Correlation Heatmap',  q: 'Show an annotated correlation heatmap of all numeric columns' },
      { label: 'Outcome Prevalence',   q: 'Show a count plot of the outcome variable (how many in each group)' },
      { label: 'Age by Outcome',       q: 'Show a violin plot of age split by outcome group' },
      { label: 'Cohort Comparison',    q: 'Compare the mean of each numeric feature between outcome groups with a grouped bar chart' },
      { label: 'Feature Distributions',q: 'Plot the distribution of each clinical measurement split by outcome' },
    ],
  },
  {
    key: 'retail', label: 'Retail', icon: ShoppingCart,
    blurb: 'Sales, products & customers',
    examples: [
      'Show a bar chart of revenue by product category',
      'Which region has the highest total sales?',
      'Show the relationship between rating and revenue',
      'What is the average order value?',
    ],
    suggested: [
      { label: 'Sales by Category',    q: 'Show a bar chart of total revenue by category, sorted descending' },
      { label: 'Top Regions',          q: 'Show a bar chart of total revenue by region, sorted descending' },
      { label: 'Best-Selling Products',q: 'Show a bar chart of the top 10 products by revenue' },
      { label: 'Sales Trend',          q: 'Plot total revenue over time as a line chart' },
      { label: 'Ratings vs Revenue',   q: 'Show a scatter plot of rating versus revenue' },
      { label: 'Avg Order Value',      q: 'What is the average quantity and revenue per order? Show a chart' },
    ],
  },
  {
    key: 'marketing', label: 'Marketing', icon: Megaphone,
    blurb: 'Conversion, segments & channels',
    examples: [
      'Break down totals by each segment',
      'Which channel or category performs best?',
      'Compare performance between segments',
      'Show the share of each category as a chart',
    ],
    suggested: [
      { label: 'Segment Breakdown',    q: 'Show a bar chart breaking down totals by the main categorical column' },
      { label: 'Best Performing',      q: 'Show a ranked bar chart of which category has the highest total' },
      { label: 'Channel Share',        q: 'Show the share/proportion of each category as a chart' },
      { label: 'Rate Analysis',        q: 'Show rates or proportions across the main categorical column' },
      { label: 'Segment Comparison',   q: 'Compare the mean numeric values across segments with a grouped bar chart' },
      { label: 'Trend Over Time',      q: 'Plot the trend of the main metric over time by segment' },
    ],
  },
  {
    key: 'hr', label: 'HR', icon: Users,
    blurb: 'Attrition, tenure & demographics',
    examples: [
      'Show the headcount by department or category',
      'Plot the age distribution across the workforce',
      'Compare numeric features between groups',
      'Show a correlation heatmap of the numeric columns',
    ],
    suggested: [
      { label: 'Headcount',            q: 'Show a bar chart of counts by the main categorical column' },
      { label: 'Demographics',         q: 'Plot the age distribution across the workforce as a histogram' },
      { label: 'Attrition Analysis',   q: 'Show a count plot of attrition/turnover by group' },
      { label: 'Tenure Distribution',  q: 'Plot the distribution of tenure or years across the dataset' },
      { label: 'Group Comparison',     q: 'Compare the mean of each numeric feature between groups with a box plot' },
      { label: 'Pay / Value Equity',   q: 'Compare the average of the main numeric column across groups with a bar chart' },
    ],
  },
]

const catByKey = (key) => CATEGORIES.find((c) => c.key === key) || CATEGORIES[0]

const STEP_META = {
  analyzing:   { icon: '🔍', color: '#4F46E5' },
  planning:    { icon: '🗺️', color: '#7C3AED' },
  plan:        { icon: '📋', color: '#7C3AED' },
  analyst:     { icon: '🔬', color: '#0EA5E9' },
  thinking:    { icon: '🧠', color: '#8B5CF6' },
  code:        { icon: '💻', color: '#06B6D4' },
  executing:   { icon: '⚡', color: '#F59E0B' },
  visualizing: { icon: '📊', color: '#EC4899' },
  critiquing:  { icon: '🔎', color: '#64748B' },
  critique:    { icon: '🧾', color: '#64748B' },
  reporting:   { icon: '📝', color: '#10B981' },
  done:        { icon: '✅', color: '#10B981' },
  error:       { icon: '⚠️', color: '#EF4444' },
}

// ─── Top Navigation ────────────────────────────────────────────────────────────

function TopNav({ upload, category, leftPanelCollapsed, setLeftPanelCollapsed, rightPanelCollapsed, setRightPanelCollapsed }) {
  const cat = catByKey(category)
  return (
    <header className="topnav">
      <div className="nav-left">
        {upload && (
          <button
            className={`panel-toggle-btn ${leftPanelCollapsed ? 'active' : ''}`}
            title={leftPanelCollapsed ? "Expand Left Panel" : "Collapse Left Panel"}
            onClick={() => setLeftPanelCollapsed?.(prev => !prev)}
            style={{ marginRight: 8, padding: '4px 8px', fontSize: 11, cursor: 'pointer', borderRadius: 4, border: '1px solid var(--border-color, #CBD5E1)', background: 'var(--bg-subtle, #F8FAFC)' }}
          >
            {leftPanelCollapsed ? '▶ Schema' : '◀ Schema'}
          </button>
        )}
        <span className="brand-logo"><Logo width={20} height={20} /></span>
        <span className="brand-name">Analytico <span className="brand-ai">AI</span></span>
      </div>

      <div className="nav-center">
        {upload && (
          <span className="dataset-pill">
            <FileIcon width={14} height={14} />
            {upload.filename}
          </span>
        )}
      </div>

      <div className="nav-right">
        {upload ? (
          <div className="stat-pills">
            <span className="lens-badge"><cat.icon width={13} height={13} /> {cat.label} lens</span>
            <span className="stat-pill"><Rows width={13} height={13} /> {upload.rows.toLocaleString()} <em>rows</em></span>
            <span className="stat-pill"><Columns width={13} height={13} /> {upload.columns.length} <em>cols</em></span>
            <span className={`stat-pill ${upload.missing_pct > 0 ? 'warn' : 'ok'}`}>
              <AlertDot width={13} height={13} /> {upload.missing_pct}% <em>missing</em>
            </span>
            <button
              className={`panel-toggle-btn ${rightPanelCollapsed ? 'active' : ''}`}
              title={rightPanelCollapsed ? "Expand Insights Panel" : "Collapse Insights Panel"}
              onClick={() => setRightPanelCollapsed?.(prev => !prev)}
              style={{ marginLeft: 8, padding: '4px 8px', fontSize: 11, cursor: 'pointer', borderRadius: 4, border: '1px solid var(--border-color, #CBD5E1)', background: 'var(--bg-subtle, #F8FAFC)' }}
            >
              {rightPanelCollapsed ? 'Insights ◀' : 'Insights ▶'}
            </button>
          </div>
        ) : (
          <span className="nav-tag">Domain-aware data analysis</span>
        )}
      </div>
    </header>
  )
}

// ─── Upload Screen (with category selector) ────────────────────────────────────

function PasteModal({ uploading, onClose, onSubmit }) {
  const [pasteText, setPasteText] = useState('')
  const [hasHeader, setHasHeader] = useState(true)

  return (
    <div className="modal-overlay" onClick={() => !uploading && onClose()}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <h3>Paste your data</h3>
            <p>Paste rows copied from Excel, Google Sheets or a CSV — commas or tabs both work.</p>
          </div>
          <button className="icon-btn" onClick={onClose}><X width={16} height={16} /></button>
        </div>
        <textarea
          className="paste-area"
          placeholder={"date\tdepartment\trevenue\tprofit\n2025-01-01\tSoftware\t88956.3\t33440.91\n2025-02-01\tSoftware\t87270.5\t31980.20"}
          value={pasteText}
          onChange={(e) => setPasteText(e.target.value)}
          autoFocus
        />
        <div className="modal-foot">
          <label className="header-toggle">
            <input type="checkbox" checked={hasHeader} onChange={(e) => setHasHeader(e.target.checked)} />
            First row is a header
          </label>
          <button className="paste-submit" onClick={() => onSubmit(pasteText, hasHeader)} disabled={uploading || !pasteText.trim()}>
            {uploading ? <span className="spinner" /> : <>Analyze data →</>}
          </button>
        </div>
      </div>
    </div>
  )
}


function UrlImportModal({ uploading, onClose, onSubmit }) {
  const [url, setUrl] = useState('')

  return (
    <div className="modal-overlay" onClick={() => !uploading && onClose()}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <h3>Import Google Sheets or Public CSV URL</h3>
            <p>Paste a public Google Sheets sharing link or a direct CSV download URL.</p>
          </div>
          <button className="icon-btn" onClick={onClose}><X width={16} height={16} /></button>
        </div>
        <input
          className="paste-row-input"
          style={{ width: '100%', marginTop: '12px', padding: '10px 14px' }}
          placeholder="https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms/edit"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          autoFocus
        />
        <div className="modal-foot">
          <button className="paste-submit" onClick={() => onSubmit(url)} disabled={uploading || !url.trim()}>
            {uploading ? <span className="spinner" /> : <>Import & Profile →</>}
          </button>
        </div>
      </div>
    </div>
  )
}

function JoinModal({ datasets, activeSessionId, onClose, onJoined }) {
  const [session1, setSession1] = useState(activeSessionId || datasets[0]?.session_id)
  const [session2, setSession2] = useState(datasets.find(d => d.session_id !== (activeSessionId || datasets[0]?.session_id))?.session_id || datasets[1]?.session_id)
  const [candidates, setCandidates] = useState([])
  const [key1, setKey1] = useState('')
  const [key2, setKey2] = useState('')
  const [how, setHow] = useState('inner')
  const [loading, setLoading] = useState(false)
  const [joining, setJoining] = useState(false)
  const [error, setError] = useState(null)

  const ds1 = datasets.find(d => d.session_id === session1)
  const ds2 = datasets.find(d => d.session_id === session2)

  useEffect(() => {
    if (!session1 || !session2 || session1 === session2) return
    let isMounted = true
    setLoading(true)
    setError(null)
    const token = ds1?.token || ''
    fetch(`${API}/infer_join`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Session-Token': token },
      body: JSON.stringify({ session_id_1: session1, session_id_2: session2 }),
    })
      .then(res => res.json())
      .then(data => {
        if (!isMounted) return
        if (data.candidates && data.candidates.length > 0) {
          setCandidates(data.candidates)
          setKey1(data.candidates[0].column_1)
          setKey2(data.candidates[0].column_2)
        } else {
          setCandidates([])
          if (ds1?.columns?.[0] && ds2?.columns?.[0]) {
            setKey1(ds1.columns[0])
            setKey2(ds2.columns[0])
          }
        }
      })
      .catch(e => { if (isMounted) setError(e.message) })
      .finally(() => { if (isMounted) setLoading(false) })
    return () => { isMounted = false }
  }, [session1, session2])

  const executeJoin = async () => {
    if (!key1 || !key2) return
    setJoining(true)
    setError(null)
    try {
      const res = await fetch(`${API}/join`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Session-Token': ds1?.token || '' },
        body: JSON.stringify({
          session_id_1: session1,
          session_id_2: session2,
          join_key_1: key1,
          join_key_2: key2,
          how,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Join execution failed')
      onJoined({ ...data, uploadedAt: new Date() })
      onClose()
    } catch (e) {
      setError(e.message)
    } finally {
      setJoining(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={() => !joining && onClose()}>
      <div className="modal" style={{ maxWidth: '640px' }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <h3>🔗 Multi-Table Relational Join</h3>
            <p>Infer join keys and merge two datasets into a unified session.</p>
          </div>
          <button className="icon-btn" onClick={onClose} disabled={joining}><X width={16} height={16} /></button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', margin: '16px 0' }}>
          <div>
            <label className="scenario-prompt" style={{ fontSize: '12px', fontWeight: 600 }}>Table 1 (Left)</label>
            <select className="paste-row-input" value={session1} onChange={(e) => setSession1(e.target.value)}>
              {datasets.map(d => <option key={d.session_id} value={d.session_id}>{d.filename}</option>)}
            </select>
          </div>
          <div>
            <label className="scenario-prompt" style={{ fontSize: '12px', fontWeight: 600 }}>Table 2 (Right)</label>
            <select className="paste-row-input" value={session2} onChange={(e) => setSession2(e.target.value)}>
              {datasets.map(d => <option key={d.session_id} value={d.session_id}>{d.filename}</option>)}
            </select>
          </div>
        </div>

        {loading ? (
          <p className="predict-hint"><span className="spinner" /> Analyzing foreign key pairs & value overlaps…</p>
        ) : (
          <>
            {candidates.length > 0 && (
              <div style={{ background: 'var(--bg-card)', padding: '10px', borderRadius: '8px', marginBottom: '12px' }}>
                <span style={{ fontSize: '12px', fontWeight: 600 }}>Suggested Join Key Candidate:</span>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '6px' }}>
                  {candidates.map((c, idx) => (
                    <button
                      key={idx}
                      className={`stat-pill ${key1 === c.column_1 && key2 === c.column_2 ? 'ok' : ''}`}
                      onClick={() => { setKey1(c.column_1); setKey2(c.column_2) }}
                      style={{ cursor: 'pointer' }}
                    >
                      {c.column_1} = {c.column_2} ({c.confidence} overlap: {c.overlap_pct}%)
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 120px', gap: '10px' }}>
              <label>
                <span style={{ fontSize: '12px' }}>Left Key</span>
                <select className="paste-row-input" value={key1} onChange={(e) => setKey1(e.target.value)}>
                  {(ds1?.columns || []).map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </label>
              <label>
                <span style={{ fontSize: '12px' }}>Right Key</span>
                <select className="paste-row-input" value={key2} onChange={(e) => setKey2(e.target.value)}>
                  {(ds2?.columns || []).map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </label>
              <label>
                <span style={{ fontSize: '12px' }}>Join Type</span>
                <select className="paste-row-input" value={how} onChange={(e) => setHow(e.target.value)}>
                  <option value="inner">Inner</option>
                  <option value="left">Left</option>
                  <option value="right">Right</option>
                  <option value="outer">Outer</option>
                </select>
              </label>
            </div>
          </>
        )}

        {error && <p style={{ color: '#EF4444', fontSize: '13px', marginTop: '10px' }}>{error}</p>}

        <div className="modal-foot">
          <button className="paste-submit" onClick={executeJoin} disabled={joining || !key1 || !key2 || session1 === session2}>
            {joining ? <span className="spinner" /> : <>Execute Join →</>}
          </button>
        </div>
      </div>
    </div>
  )
}

function CompareModal({ datasets, activeSessionId, onClose }) {
  const [session1, setSession1] = useState(activeSessionId || datasets[0]?.session_id)
  const [session2, setSession2] = useState(datasets.find(d => d.session_id !== (activeSessionId || datasets[0]?.session_id))?.session_id || datasets[1]?.session_id)
  const [loading, setLoading] = useState(false)
  const [comparison, setComparison] = useState(null)
  const [error, setError] = useState(null)

  const ds1 = datasets.find(d => d.session_id === session1)

  const runCompare = async () => {
    if (!session1 || !session2 || session1 === session2) return
    setLoading(true)
    setError(null)
    setComparison(null)
    try {
      const res = await fetch(`${API}/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Session-Token': ds1?.token || '' },
        body: JSON.stringify({ session_id_1: session1, session_id_2: session2 }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Comparison failed')
      setComparison(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    runCompare()
  }, [session1, session2])

  return (
    <div className="modal-overlay" onClick={() => !loading && onClose()}>
      <div className="modal" style={{ maxWidth: '720px' }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <h3>📊 Dataset Comparison & Distribution Drift</h3>
            <p>Compare schema changes and statistical distribution shifts between versions.</p>
          </div>
          <button className="icon-btn" onClick={onClose} disabled={loading}><X width={16} height={16} /></button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', margin: '16px 0' }}>
          <div>
            <label className="scenario-prompt" style={{ fontSize: '12px', fontWeight: 600 }}>Base Dataset (v1)</label>
            <select className="paste-row-input" value={session1} onChange={(e) => setSession1(e.target.value)}>
              {datasets.map(d => <option key={d.session_id} value={d.session_id}>{d.filename}</option>)}
            </select>
          </div>
          <div>
            <label className="scenario-prompt" style={{ fontSize: '12px', fontWeight: 600 }}>Target Dataset (v2)</label>
            <select className="paste-row-input" value={session2} onChange={(e) => setSession2(e.target.value)}>
              {datasets.map(d => <option key={d.session_id} value={d.session_id}>{d.filename}</option>)}
            </select>
          </div>
        </div>

        {loading && <p className="predict-hint"><span className="spinner" /> Computing schema diff and statistical distribution drift…</p>}
        {error && <p style={{ color: '#EF4444', fontSize: '13px' }}>{error}</p>}

        {comparison && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', maxHeight: '420px', overflowY: 'auto' }}>
            <div className="stat-pill ok" style={{ padding: '8px 12px', fontSize: '13px' }}>
              {comparison.summary}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px' }}>
              <div className="stat-pill">Added Cols: <strong>{comparison.schema_changes.added_columns.join(', ') || 'None'}</strong></div>
              <div className="stat-pill">Removed Cols: <strong>{comparison.schema_changes.removed_columns.join(', ') || 'None'}</strong></div>
              <div className="stat-pill">Row Delta: <strong>{comparison.row_delta > 0 ? `+${comparison.row_delta}` : comparison.row_delta} ({comparison.row_pct_change}%)</strong></div>
            </div>

            {comparison.numeric_drift.length > 0 && (
              <div>
                <h4 style={{ margin: '8px 0', fontSize: '13px' }}>Numeric Distribution Drift Ranking</h4>
                <table className="bm-table">
                  <thead>
                    <tr>
                      <th>Column</th>
                      <th>v1 Mean</th>
                      <th>v2 Mean</th>
                      <th>Shift %</th>
                      <th>Drift Level</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comparison.numeric_drift.map(d => (
                      <tr key={d.column}>
                        <td><strong>{d.column}</strong></td>
                        <td>{d.v1_mean}</td>
                        <td>{d.v2_mean}</td>
                        <td>{d.pct_shift}%</td>
                        <td>
                          <span className={`stat-pill ${d.drift_level === 'Significant' ? 'warn' : d.drift_level === 'Moderate' ? '' : 'ok'}`}>
                            {d.drift_level}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function ExcelDataViewerModal({ upload, onClose }) {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)
  const [search, setSearch] = useState('')
  const [sortCol, setSortCol] = useState('')
  const [sortDir, setSortDir] = useState('asc')
  const [selectedCell, setSelectedCell] = useState(null)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchData = useCallback(async () => {
    if (!upload) return
    setLoading(true)
    let fetched = null

    if (upload.session_id) {
      try {
        const q = new URLSearchParams({
          page: String(page),
          page_size: String(pageSize),
          search: search.trim(),
          sort_col: sortCol,
          sort_dir: sortDir,
        })
        if (upload.token) q.set('token', upload.token)

        const headers = {}
        if (upload.token) headers['X-Session-Token'] = upload.token

        const res = await fetch(`${API}/dataset_rows/${upload.session_id}?${q}`, { headers })
        if (res.ok) {
          fetched = await res.json()
        }
      } catch (e) {
        console.warn('Dataset rows endpoint fallback:', e)
      }
    }

    // Fallback: build from upload object (preview or sample rows) so data ALWAYS renders
    if (!fetched || !fetched.rows || fetched.rows.length === 0) {
      const rawCols = upload.columns || []
      const rawRows = upload.preview || upload.sample_rows || []
      const totalCount = upload.rows || rawRows.length
      
      let filteredRows = rawRows
      if (search.trim()) {
        const qStr = search.toLowerCase().trim()
        filteredRows = rawRows.filter(r => Object.values(r || {}).some(v => String(v ?? '').toLowerCase().includes(qStr)))
      }

      if (sortCol && rawCols.includes(sortCol)) {
        filteredRows = [...filteredRows].sort((a, b) => {
          const valA = a[sortCol]
          const valB = b[sortCol]
          if (valA == null) return 1
          if (valB == null) return -1
          if (typeof valA === 'number' && typeof valB === 'number') {
            return sortDir === 'asc' ? valA - valB : valB - valA
          }
          return sortDir === 'asc' 
            ? String(valA).localeCompare(String(valB)) 
            : String(valB).localeCompare(String(valA))
        })
      }

      const pSize = pageSize > 0 ? pageSize : filteredRows.length
      const start = (page - 1) * pSize
      const end = start + pSize
      const sliced = filteredRows.slice(start, end)

      const colDtypes = {}
      rawCols.forEach(c => {
        const sampleVal = rawRows.find(r => r[c] != null)?.[c]
        colDtypes[c] = typeof sampleVal === 'number' ? (Number.isInteger(sampleVal) ? 'int64' : 'float64') : 'object'
      })

      fetched = {
        session_id: upload.session_id || 'local',
        total_rows: totalCount,
        filtered_count: filteredRows.length,
        page: page,
        page_size: pageSize,
        total_pages: Math.max(1, Math.ceil(filteredRows.length / (pSize || 1))),
        columns: rawCols,
        dtypes: colDtypes,
        row_indices: sliced.map((_, i) => start + i + 1),
        rows: sliced,
      }
    }

    setData(fetched)
    setLoading(false)
  }, [upload, page, pageSize, search, sortCol, sortDir])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleSort = (col) => {
    if (sortCol === col) {
      setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortCol(col)
      setSortDir('asc')
    }
  }

  const exportCsv = () => {
    if (!data?.rows || !data?.columns) return
    const headers = data.columns.join(',')
    const rowsText = data.rows.map(r => data.columns.map(c => JSON.stringify(r[c] ?? '')).join(',')).join('\n')
    const blob = new Blob([`${headers}\n${rowsText}`], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${upload.filename || 'dataset'}_view.csv`
    a.click()
  }

  const getColLetter = (idx) => {
    let letter = ''
    let n = idx
    while (n >= 0) {
      letter = String.fromCharCode((n % 26) + 65) + letter
      n = Math.floor(n / 26) - 1
    }
    return letter
  }

  return (
    <div className="modal-overlay excel-modal-overlay" onClick={onClose}>
      <div className="modal excel-viewer-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="excel-header">
          <div className="excel-title-group">
            <div className="excel-icon-box"><Rows width={18} height={18} /></div>
            <div>
              <h3>Spreadsheet Data Viewer — {upload.filename}</h3>
              <p>{upload.rows ? upload.rows.toLocaleString() : (data?.total_rows || 0)} total rows · {upload.columns?.length || 0} columns · Full File Inspection</p>
            </div>
          </div>

          <div className="excel-actions">
            <button className="btn-secondary-action" onClick={exportCsv}>
              <Download width={14} height={14} /> Download CSV
            </button>
            <button className="icon-btn" onClick={onClose} title="Close (Esc)"><X width={18} height={18} /></button>
          </div>
        </div>

        {/* Excel Formula & Filter Bar */}
        <div className="excel-toolbar">
          <div className="excel-search-box">
            <Search width={14} height={14} />
            <input
              placeholder="Filter values across all rows & columns..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            />
          </div>

          <div className="excel-formula-box">
            <span className="cell-ref-label">{selectedCell ? `${selectedCell.colLetter}${selectedCell.rowIndex}` : 'fx'}</span>
            <input
              readOnly
              className="cell-value-input"
              value={selectedCell ? `${selectedCell.colName} = ${selectedCell.value}` : 'Click any cell to inspect or copy value'}
            />
          </div>

          <div className="excel-page-size">
            <span>Show:</span>
            <select value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}>
              <option value={50}>50 rows</option>
              <option value={100}>100 rows</option>
              <option value={250}>250 rows</option>
              <option value={1000}>1,000 max</option>
              <option value={0}>All Rows ({upload.rows || data?.total_rows || 'All'})</option>
            </select>
          </div>
        </div>

        {/* Grid Table */}
        <div className="excel-table-container">
          {loading ? (
            <div className="excel-loading">
              <span className="spinner big" style={{ borderTopColor: '#107C41', borderColor: 'rgba(16,124,65,0.2)' }} />
              <span>Loading spreadsheet data...</span>
            </div>
          ) : (
            <table className="excel-table">
              <thead>
                <tr className="excel-col-letters-row">
                  <th className="excel-corner-hdr">#</th>
                  {data?.columns.map((col, idx) => (
                    <th key={idx} className="excel-col-letter">{getColLetter(idx)}</th>
                  ))}
                </tr>
                <tr className="excel-col-names-row">
                  <th className="excel-row-num-hdr">Row</th>
                  {data?.columns.map((col) => (
                    <th key={col} className="excel-col-hdr" onClick={() => handleSort(col)}>
                      <div className="col-hdr-content">
                        <span>{col}</span>
                        <em className="col-type-tag">{data.dtypes?.[col] || ''}</em>
                        {sortCol === col && <span className="sort-arrow">{sortDir === 'asc' ? '▲' : '▼'}</span>}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data?.rows.length === 0 ? (
                  <tr>
                    <td colSpan={(data?.columns.length || 0) + 1} className="excel-empty-td">
                      No matching records found for "{search}".
                    </td>
                  </tr>
                ) : (
                  data?.rows.map((row, rIdx) => {
                    const actualRowIndex = data.row_indices?.[rIdx] || (page - 1) * pageSize + rIdx + 1
                    return (
                      <tr key={rIdx}>
                        <td className="excel-row-num">{actualRowIndex}</td>
                        {data.columns.map((col, cIdx) => {
                          const val = row[col]
                          const valStr = val == null ? '—' : String(val)
                          const isSelected = selectedCell?.rowIndex === actualRowIndex && selectedCell?.colName === col
                          return (
                            <td
                              key={col}
                              className={`excel-cell ${isSelected ? 'selected' : ''}`}
                              onClick={() => setSelectedCell({
                                rowIndex: actualRowIndex,
                                colName: col,
                                colLetter: getColLetter(cIdx),
                                value: valStr
                              })}
                            >
                              {valStr}
                            </td>
                          )
                        })}
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer Status Bar */}
        <div className="excel-footer">
          <div className="excel-footer-info">
            <span>Ready</span>
            <span>Rows: <strong>{data?.filtered_count?.toLocaleString() || 0}</strong> of <strong>{data?.total_rows?.toLocaleString() || 0}</strong></span>
            <span>Columns: <strong>{data?.columns?.length || 0}</strong></span>
          </div>

          <div className="excel-pagination">
            <button disabled={page <= 1} onClick={() => setPage(1)}>|&lt;</button>
            <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}>&lt; Prev</button>
            <span className="page-indicator">Page <strong>{page}</strong> of <strong>{data?.total_pages || 1}</strong></span>
            <button disabled={page >= (data?.total_pages || 1)} onClick={() => setPage(p => p + 1)}>Next &gt;</button>
            <button disabled={page >= (data?.total_pages || 1)} onClick={() => setPage(data?.total_pages || 1)}>&gt;|</button>
          </div>
        </div>
      </div>
    </div>
  )
}

function UploadScreen({ onUpload, uploading, setUploading, category, setCategory, onOpenPaste, onOpenUrlImport }) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef()

  const handleFile = useCallback(async (file) => {
    if (!file) return
    // Accept case-insensitively so .CSV, .XLSX, etc. are not rejected
    const ext = file.name.split('.').pop()?.toLowerCase() || ''
    const ACCEPTED_EXTS = ['csv', 'xlsx', 'xls', 'parquet', 'json', 'jsonl']
    if (!ACCEPTED_EXTS.includes(ext)) {
      alert(`Unsupported file type: .${ext}\nAccepted: .csv, .xlsx, .xls, .parquet, .json, .jsonl`)
      return
    }
    setUploading(true)
    const fd = new FormData()
    fd.append('file', file)
    try {
      const res = await fetch(`${API}/upload`, { method: 'POST', body: fd })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Upload failed')
      onUpload(data)
    } catch (e) {
      alert(e.message)
    } finally {
      setUploading(false)
    }
  }, [onUpload, setUploading])

  return (
    <div className="upload-screen">
      {/* ── Centered Full-Width Hero Title Section ────────────────────── */}
      <div className="hero-center-header">
        <h1 className="hero-title">Analysis tuned to your domain</h1>
        <p className="hero-sub">
          Pick an analysis lens, upload a CSV, and ask in plain English. The multi-agent pipeline reasons like a domain expert — financial, medical, retail, marketing, or HR — not a generic chatbot.
        </p>

        <div className="hero-highlights">
          <span className="hh-pill"><Zap width={12} height={12} /> Multi-Agent Pipeline</span>
          <span className="hh-pill"><Lock width={12} height={12} /> AST Sandboxed Python</span>
          <span className="hh-pill"><Check width={12} height={12} /> Evidence-Backed Answers</span>
        </div>
      </div>

      {/* ── 2-Column Split: Lens Grid + Offset Upload Card ──────────────── */}
      <div className="upload-hero-layout">
        {/* Left Column: Lens Selector */}
        <div className="hero-left-col">
          <div className="category-picker-left">
            <div className="cp-label">1 · Select an analysis lens</div>
            <div className="category-grid-left">
              {CATEGORIES.map((c) => (
                <button
                  key={c.key}
                  className={`category-card ${category === c.key ? 'active' : ''}`}
                  onClick={() => setCategory(c.key)}
                >
                  <span className="cc-icon"><c.icon width={22} height={22} /></span>
                  <div className="cc-text-group">
                    <span className="cc-label">{c.label}</span>
                    <span className="cc-blurb">{c.blurb}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Upload Target Card with Background Image Artwork */}
        <div className="hero-right-col">
          <div className="upload-card-wrapper">
            <div className="upload-artwork-banner" style={{ backgroundImage: `url(/background.jpg)` }}>
              <div className="artwork-overlay" />
              <div className="artwork-badge"><ChartUp width={14} height={14} /> 3D Data Engine</div>
            </div>

            <div className="upload-step-inner">
              <div className="cp-label">2 · Upload your dataset</div>
              <div
                className={`dropzone ${dragging ? 'drag-over' : ''} ${uploading ? 'uploading' : ''}`}
                onClick={() => !uploading && inputRef.current.click()}
                onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
                onDragLeave={() => setDragging(false)}
                onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]) }}
              >
                <input ref={inputRef} type="file" accept=".csv,.xlsx,.xls,.parquet,.json,.jsonl" hidden onChange={(e) => handleFile(e.target.files[0])} />
                <div className="dropzone-icon">{uploading ? <span className="spinner big" /> : <FileIcon width={24} height={24} />}</div>
                <p className="dropzone-title">{uploading ? 'Analyzing your dataset…' : 'Drop CSV, Excel, Parquet, or JSON file'}</p>
                <p className="dropzone-sub">{uploading ? 'Building data profile & overview' : 'or click to browse · .csv, .xlsx, .parquet up to 25MB'}</p>
              </div>

              <div className="paste-divider"><span>or alternative inputs</span></div>
              
              <div className="upload-action-row">
                <button className="paste-trigger" onClick={onOpenPaste} disabled={uploading}>
                  <Code width={14} height={14} /> Paste rows
                </button>
                <button className="paste-trigger" onClick={onOpenUrlImport} disabled={uploading}>
                  <Sparkles width={14} height={14} /> Import Sheet / URL
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Scrollable Showcase Section ───────────────────────────────────── */}
      <div className="upload-showcase-section">
        <div className="showcase-banner" style={{ backgroundImage: `linear-gradient(180deg, rgba(9,9,11,0.85) 0%, rgba(9,9,11,0.96) 100%), url(/piqsels.com-id-jrreu.jpg)` }}>
          <div className="sb-content">
            <h2 className="sb-title">Deterministic precision & domain-aware intelligence</h2>
            <p className="sb-sub">Combining LLM intent mapping, AST-sandboxed execution, and self-auditing critic agents.</p>
          </div>

          <div className="sb-stats-right">
            <div className="sb-stat-box">
              <span className="sb-stat-num">100%</span>
              <span className="sb-stat-lbl">Deterministic Python</span>
            </div>
            <div className="sb-stat-box">
              <span className="sb-stat-num">&lt;30s</span>
              <span className="sb-stat-lbl">Execution Timeout</span>
            </div>
            <div className="sb-stat-box">
              <span className="sb-stat-num">0%</span>
              <span className="sb-stat-lbl">Hallucination Audit</span>
            </div>
          </div>
        </div>

        <div className="showcase-grid">
          <div className="showcase-card">
            <div className="sc-icon"><Layers width={20} height={20} /></div>
            <h3>Domain Lenses</h3>
            <p>Tailors computations, group comparisons, and key performance ratios to your specific domain (financial margins, clinical cohorts, retail conversions, HR tenure).</p>
          </div>

          <div className="showcase-card">
            <div className="sc-icon"><Terminal width={20} height={20} /></div>
            <h3>AST Sandboxed Python</h3>
            <p>Generated code is parsed via AST pre-scanners, executed under restricted builtins with 30s hard wall-clock timeouts to prevent memory or execution abuse.</p>
          </div>

          <div className="showcase-card">
            <div className="sc-icon"><Eye width={20} height={20} /></div>
            <h3>Self-Auditing Critic Agent</h3>
            <p>Every analysis step is cross-checked by an independent critic agent before presentation to flag domain mismatches and preserve 100% data trust.</p>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Sidebar ───────────────────────────────────────────────────────────────────

function DocUploadPanel({ sessionId, docs, onDocsUpdated }) {
  const [uploading, setUploading] = useState(false)
  const inputRef = useRef()

  const handleFile = useCallback(async (file) => {
    if (!file) return
    const allowed = ['.pdf', '.xlsx', '.xls', '.txt', '.md', '.csv']
    if (!allowed.some(ext => file.name.toLowerCase().endsWith(ext))) {
      alert('Supported formats: PDF, Excel, TXT, MD, CSV')
      return
    }
    setUploading(true)
    const fd = new FormData()
    fd.append('file', file)
    try {
      const res = await fetch(`${API}/upload_doc?session_id=${sessionId}`, { method: 'POST', headers: { 'X-Session-Token': upload?.token || '' }, body: fd })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Upload failed')
      onDocsUpdated(data.filenames)
    } catch (e) {
      alert(e.message)
    } finally {
      setUploading(false)
    }
  }, [sessionId, onDocsUpdated])

  return (
    <div className="panel-section">
      <div className="panel-head">📄 Documentation <span className="doc-count">{docs.length} file{docs.length !== 1 ? 's' : ''}</span></div>
      <p className="doc-hint">Upload PDFs, Excel, or text files to enrich analysis with domain context.</p>
      {docs.length > 0 && (
        <div className="doc-list">
          {docs.map(f => (
            <div key={f} className="doc-item">
              <span className="doc-icon">📄</span>
              <span className="doc-name">{f}</span>
            </div>
          ))}
        </div>
      )}
      <button className="doc-upload-btn" onClick={() => inputRef.current.click()} disabled={uploading}>
        <input ref={inputRef} type="file" hidden accept=".pdf,.xlsx,.xls,.txt,.md,.csv"
          onChange={e => handleFile(e.target.files[0])} />
        {uploading ? <span className="spinner" style={{borderTopColor:'var(--primary)',borderColor:'var(--primary-ring)'}} /> : '+ Attach document'}
      </button>
    </div>
  )
}

function Sidebar({ upload, category, setCategory, onReset, docs, onDocsUpdated, datasets, onSelectDataset, onOpenAddDataset, onOpenJoin, onOpenCompare, onOpenDataViewer, style }) {
  const [q, setQ] = useState('')
  const filtered = useMemo(
    () => upload.columns.filter((c) => c.toLowerCase().includes(q.toLowerCase())),
    [upload.columns, q]
  )
  const ts = upload.uploadedAt
    ? new Date(upload.uploadedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : ''

  const niceType = (t) => {
    if (t.includes('int')) return 'integer'
    if (t.includes('float')) return 'float'
    if (t.includes('bool')) return 'boolean'
    if (t.includes('date')) return 'datetime'
    return 'text'
  }

  return (
    <aside className="sidebar" style={style}>
      <div className="dataset-card dataset-card-interactive" onClick={onOpenDataViewer} title="Click to open Excel Spreadsheet Viewer">
        <div className="dataset-card-top">
          <span className="ds-icon"><FileIcon width={18} height={18} /></span>
          <div className="ds-info">
            <div className="ds-name">{upload.filename}</div>
            <div className="ds-meta">{upload.rows.toLocaleString()} rows · {upload.columns.length} columns</div>
          </div>
          <button className="icon-btn" onClick={(e) => { e.stopPropagation(); onReset() }} title="Change file"><X width={15} height={15} /></button>
        </div>
        <div className="ds-tags">
          <span className="ds-tag">{upload.numeric_features} numeric</span>
          <span className="ds-tag">{upload.columns.length - upload.numeric_features} categorical</span>
          <span className="ds-tag excel-viewer-tag">📊 Open Excel Viewer →</span>
        </div>
      </div>

      <div className="panel-section">
        <div className="panel-head">Analysis Lens</div>
        <div className="lens-chips">
          {CATEGORIES.map((c) => (
            <button
              key={c.key}
              className={`lens-chip ${category === c.key ? 'active' : ''}`}
              onClick={() => setCategory(c.key)}
              title={c.blurb}
            >
              <c.icon width={14} height={14} />
              {c.label}
            </button>
          ))}
        </div>
      </div>

      <DocUploadPanel sessionId={upload.session_id} docs={docs} onDocsUpdated={onDocsUpdated} />

      <div className="panel-section">
        <div className="panel-head">Schema</div>
        <div className="schema-search">
          <Search width={14} height={14} />
          <input placeholder="Search columns…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div className="schema-pills">
          {filtered.map((col) => (
            <div key={col} className="schema-pill">
              <span className="sp-name">{col}</span>
              <span className="sp-type">{niceType(upload.dtypes[col])}</span>
            </div>
          ))}
          {filtered.length === 0 && <div className="schema-empty">No columns match "{q}"</div>}
        </div>
      </div>

      <div className="panel-section">
        <div className="panel-head">Preview</div>
        <div className="preview-table">
          <table>
            <thead>
              <tr>{upload.columns.map((c) => <th key={c}>{c}</th>)}</tr>
            </thead>
            <tbody>
              {upload.preview.map((row, i) => (
                <tr key={i}>
                  {upload.columns.map((c) => <td key={c}>{row[c] == null ? '—' : String(row[c])}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    
      {datasets && datasets.length > 0 && (
        <div className="panel-section">
          <div className="panel-head">Datasets ({datasets.length})</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {datasets.map(d => (
              <button
                key={d.session_id}
                className={`stat-pill ${d.session_id === upload.session_id ? 'ok' : ''}`}
                style={{ cursor: 'pointer', textAlign: 'left', justifyContent: 'space-between' }}
                onClick={() => onSelectDataset(d)}
              >
                <span>{d.filename}</span>
                <em>{d.rows}r</em>
              </button>
            ))}
            <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
              <button className="doc-upload-btn" style={{ flex: 1 }} onClick={onOpenAddDataset}>+ Add file</button>
              {datasets.length >= 2 && (
                <>
                  <button className="doc-upload-btn" style={{ flex: 1 }} onClick={onOpenJoin}>🔗 Join</button>
                  <button className="doc-upload-btn" style={{ flex: 1 }} onClick={onOpenCompare}>📊 Compare</button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

    </aside>
  )
}

// ─── Insights Panel ────────────────────────────────────────────────────────────

export function PredictInputCard({ sessionId, modelInfo, upload }) {
  const features = modelInfo.features
  const [values, setValues] = useState(() =>
    Object.fromEntries(features.map((f) => [f.name, f.default ?? ''])))
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)

  const setVal = (name, v) => setValues((prev) => ({ ...prev, [name]: v }))

  const fillFromPaste = (text) => {
    const parts = text.split(/[\t,]/).map((s) => s.trim())
    if (parts.length < 2) return
    setValues((prev) => {
      const next = { ...prev }
      features.forEach((f, i) => { if (parts[i] !== undefined && parts[i] !== '') next[f.name] = parts[i] })
      return next
    })
  }

  const run = async () => {
    setBusy(true); setResult(null)
    try {
      const res = await fetch(`${API}/predict_input`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Session-Token': upload?.token || '' },
        body: JSON.stringify({ session_id: sessionId, values }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Prediction failed')
      setResult(data)
    } catch (e) {
      alert(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="insight-card infer-card">
      <div className="ic-head"><Sparkles width={15} height={15} /> Predict a New Case</div>
      <p className="predict-hint">Enter a new record to predict <strong>{modelInfo.target}</strong> with the trained model.</p>
      <input
        className="paste-row-input"
        placeholder="Paste a row (comma/tab) to autofill…"
        onChange={(e) => fillFromPaste(e.target.value)}
      />
      <div className="infer-fields">
        {features.map((f) => (
          <label key={f.name} className="infer-field">
            <span className="if-name">{f.name}</span>
            {f.type === 'category' ? (
              <select value={values[f.name]} onChange={(e) => setVal(f.name, e.target.value)}>
                {f.options.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            ) : (
              <input type="number" step="any" value={values[f.name]} onChange={(e) => setVal(f.name, e.target.value)} />
            )}
          </label>
        ))}
      </div>
      <button className="predict-btn" disabled={busy} onClick={run}>
        {busy ? <span className="spinner" /> : <>🔮 Predict {modelInfo.target}</>}
      </button>
      {result && (
        <div className="infer-result">
          <div className="ir-label">Predicted {result.target}</div>
          <div className="ir-value">{String(result.prediction)}</div>
          {result.confidence != null && (
            <div className="ir-conf">{Math.round(result.confidence * 100)}% confidence</div>
          )}
        </div>
      )}
    </div>
  )
}

export function ScenarioSimulatorCard({ sessionId, modelInfo, category, upload }) {
  const features = modelInfo.features
  const firstNumeric = features.find((f) => f.type === 'number')?.name || features[0]?.name || ''
  const [feature, setFeature] = useState(firstNumeric)
  const activeFeature = features.find((f) => f.name === feature) || features[0]
  const [mode, setMode] = useState(activeFeature?.type === 'number' ? 'delta' : 'set')
  const [value, setValue] = useState(activeFeature?.type === 'number' ? 10 : activeFeature?.options?.[0] || '')
  const [prompt, setPrompt] = useState('')
  const [parseNote, setParseNote] = useState(null)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [parseBusy, setParseBusy] = useState(false)

  const changeFeature = (name) => {
    const nextFeature = features.find((f) => f.name === name)
    setFeature(name)
    setMode(nextFeature?.type === 'number' ? 'delta' : 'set')
    setValue(nextFeature?.type === 'number' ? 10 : nextFeature?.options?.[0] || '')
    setParseNote(null)
  }

  const parsePrompt = async () => {
    const text = prompt.trim()
    if (!text) return
    setParseBusy(true); setParseNote(null)
    try {
      const res = await fetch(`${API}/scenario_parse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Session-Token': upload?.token || '' },
        body: JSON.stringify({ session_id: sessionId, prompt: text, category }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Could not parse scenario')
      if (!data.parsed) {
        setParseNote(data.reason || 'Could not parse that scenario.')
        return
      }
      setFeature(data.feature)
      setMode(data.mode)
      setValue(data.value)
      setResult(null)
      setParseNote(data.interpretation || 'Scenario parsed.')
    } catch (e) {
      alert(e.message)
    } finally {
      setParseBusy(false)
    }
  }

  const run = async () => {
    if (!feature) return
    setBusy(true); setResult(null)
    try {
      const res = await fetch(`${API}/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Session-Token': upload?.token || '' },
        body: JSON.stringify({
          session_id: sessionId,
          category,
          changes: { [feature]: { mode, value } },
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Simulation failed')
      setResult(data)
    } catch (e) {
      alert(e.message)
    } finally {
      setBusy(false)
    }
  }

  const impactText = result?.impact?.type === 'regression'
    ? `${result.impact.direction.replace('_', ' ')} ${Math.abs(result.impact.delta).toLocaleString()}`
    : result?.impact
      ? `${result.impact.baseline_label} -> ${result.impact.scenario_label}`
      : null

  return (
    <div className="insight-card scenario-card">
      <div className="ic-head"><Activity width={15} height={15} /> Scenario Simulator</div>
      <p className="predict-hint">Change one driver and estimate the predicted impact on <strong>{modelInfo.target}</strong>.</p>
      <div className="scenario-prompt">
        <input
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') parsePrompt() }}
          placeholder={`Try: increase ${firstNumeric || 'a driver'} by 10%`}
        />
        <button disabled={parseBusy || !prompt.trim()} onClick={parsePrompt}>
          {parseBusy ? <span className="spinner" /> : 'Parse'}
        </button>
      </div>
      {parseNote && <div className="scenario-note">{parseNote}</div>}
      <div className="scenario-controls">
        <label>
          <span>Driver</span>
          <select value={feature} onChange={(e) => changeFeature(e.target.value)}>
            {features.map((f) => <option key={f.name} value={f.name}>{f.name}</option>)}
          </select>
        </label>
        {activeFeature?.type === 'number' ? (
          <>
            <label>
              <span>Change</span>
              <select value={mode} onChange={(e) => setMode(e.target.value)}>
                <option value="delta">Add/subtract</option>
                <option value="percent">Percent</option>
                <option value="set">Set value</option>
              </select>
            </label>
            <label>
              <span>Value</span>
              <input type="number" step="any" value={value} onChange={(e) => setValue(e.target.value)} />
            </label>
          </>
        ) : (
          <label>
            <span>Value</span>
            <select value={value} onChange={(e) => setValue(e.target.value)}>
              {(activeFeature?.options || []).map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          </label>
        )}
      </div>
      <button className="scenario-btn" disabled={busy || !feature} onClick={run}>
        {busy ? <span className="spinner" /> : <>Run scenario</>}
      </button>
      {result && (
        <div className="scenario-result">
          <div className="scenario-impact">
            <span>Impact</span>
            <strong>{impactText}</strong>
          </div>
          <div className="scenario-pair">
            <div><span>Baseline</span><strong>{String(result.baseline_prediction.prediction)}</strong></div>
            <div><span>Scenario</span><strong>{String(result.scenario_prediction.prediction)}</strong></div>
          </div>
          {result.chart_json && <PlotlyChart json={result.chart_json} />}
          <p>{result.validation?.reasons?.[1]}</p>
        </div>
      )}
    </div>
  )
}

function BenchmarkModal({ sessionId, onClose }) {
  const [n, setN] = useState(10)
  const [running, setRunning] = useState(false)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  const run = async () => {
    setRunning(true); setData(null); setError(null)
    try {
      const res = await fetch(`${API}/benchmark/${sessionId}?n=${n}`, { headers: { 'X-Session-Token': upload?.token || '' } })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail || 'Benchmark failed')
      setData(json)
    } catch (e) {
      setError(e.message)
    } finally {
      setRunning(false)
    }
  }

  const pct = (v) => `${Math.round(v * 100)}%`
  const color = (v) => v >= 0.85 ? '#10B981' : v >= 0.65 ? '#F59E0B' : '#EF4444'

  return (
    <div className="modal-overlay" onClick={() => !running && onClose()}>
      <div className="modal bm-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <h3>🏆 Benchmark Evaluation</h3>
            <p>Run a suite of analytics questions and measure system performance.</p>
          </div>
          <button className="icon-btn" onClick={onClose} disabled={running}><X width={16} height={16} /></button>
        </div>

        <div className="bm-config">
          <label className="bm-n-label">Questions to run:</label>
          <input type="range" min={5} max={50} step={5} value={n}
            onChange={e => setN(+e.target.value)} disabled={running} />
          <span className="bm-n-val">{n}</span>
          <button className="paste-submit" onClick={run} disabled={running}>
            {running ? <><span className="spinner" /> Running…</> : '▶ Run benchmark'}
          </button>
        </div>

        {running && <div className="bm-progress">Running {n} questions through the multi-agent pipeline… this may take a few minutes.</div>}
        {error && <p style={{color:'#EF4444', fontSize:13, margin:'12px 0'}}>{error}</p>}

        {data && (
          <>
            <div className="bm-metrics">
              {[
                { label: 'Success Rate',     v: data.success_rate },
                { label: 'Chart Rate',       v: data.chart_rate },
                { label: 'SQL Routing',      v: data.sql_routing_accuracy },
                { label: 'Repair Success',   v: data.repair_success_rate },
              ].map(m => (
                <div key={m.label} className="bm-metric">
                  <div className="bm-pct" style={{ color: color(m.v) }}>{pct(m.v)}</div>
                  <div className="bm-mlabel">{m.label}</div>
                </div>
              ))}
              <div className="bm-metric">
                <div className="bm-pct" style={{ color: '#4F46E5' }}>{data.avg_time_s}s</div>
                <div className="bm-mlabel">Avg Time</div>
              </div>
            </div>

            <div className="bm-table-wrap">
              <table className="bm-table">
                <thead><tr>
                  <th>#</th><th>Category</th><th>Engine</th><th>Chart</th><th>OK</th><th>Time</th><th>Question</th>
                </tr></thead>
                <tbody>
                  {data.results.map((r, i) => (
                    <tr key={i} className={r.success ? '' : 'bm-fail'}>
                      <td>{i + 1}</td>
                      <td><span className="bm-cat">{r.category}</span></td>
                      <td><span className={`code-lang-badge ${r.query_type === 'sql' ? 'sql' : 'py'}`}>{r.query_type === 'sql' ? 'SQL' : 'py'}</span></td>
                      <td style={{textAlign:'center'}}>{r.has_chart ? '✓' : r.expects_chart ? '·' : ''}</td>
                      <td style={{textAlign:'center', color: r.success ? '#10B981' : '#EF4444', fontWeight:700}}>{r.success ? '✓' : '✗'}</td>
                      <td style={{textAlign:'right', fontVariantNumeric:'tabular-nums'}}>{r.time_s}s</td>
                      <td className="bm-q">{r.question}{r.used_repair ? <span className="bm-repaired"> (repaired)</span> : ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export function ExportCard({
  upload = {},
  messages = [],
  category = 'general',
  items = [],
  formats = [],
  files = [],
  exportResult = null,
  status = 'idle',
  onExport,
  dashboardBlueprint = null,
}) {
  const [busy, setBusy] = useState(null) // 'pdf' | 'pptx' | null

  const safeMessages = Array.isArray(messages) ? messages : []
  const safeItems = Array.isArray(items) ? items : []
  const safeFormats = Array.isArray(formats) ? formats : []
  const safeFiles = Array.isArray(files) ? files : []
  const safeKpis = Array.isArray(dashboardBlueprint?.kpis) ? dashboardBlueprint.kpis : []
  const safeCharts = Array.isArray(dashboardBlueprint?.charts) ? dashboardBlueprint.charts : []
  const safeFilters = Array.isArray(dashboardBlueprint?.filters) ? dashboardBlueprint.filters : []

  console.debug("[ExportCard] props", {
    upload,
    messagesCount: safeMessages.length,
    itemsCount: safeItems.length,
    formatsCount: safeFormats.length,
    status,
    exportResult,
  })

  const exportReport = async (format) => {
    setBusy(format)
    try {
      const filename = String(upload?.filename || 'dataset.csv').replace('.csv', '')
      const body = {
        messages: safeMessages.map(m => ({
          question:  m?.question,
          report:    m?.report,
          result:    m?.result,
          chart:     m?.chart,
          chart_json: m?.chart_json,
          shap_chart: m?.shap_chart,
          critique:  m?.critique,
          validation: m?.validation,
          code:      m?.code,
          code_lang: m?.code_lang,
        })),
        category,
        filename,
      }
      const sessionId = upload?.session_id || 'default'
      const res = await fetch(`${API}/report/${sessionId}?format=${format}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Session-Token': upload?.token || '' },
        body: JSON.stringify(body),
      })
      if (!res.ok) { const e = await res.json(); throw new Error(e?.detail || 'Export failed') }
      const payload = await res.json()
      downloadBase64Payload(payload, `${filename}_report.${format}`)
    } catch (e) {
      alert(e.message)
    } finally {
      setBusy(null)
    }
  }

  const isGenerating = status === 'generating' || !!busy

  return (
    <div className="insight-card export-card">
      <div className="ic-head">📄 Export Report</div>
      <p className="predict-hint">Download the full analytics report with all charts, summaries, and insights.</p>
      <div className="export-btns">
        <button
          type="button"
          className="export-btn pdf"
          onClick={() => (onExport ? onExport('pdf') : exportReport('pdf'))}
          disabled={isGenerating || safeMessages.length === 0}
        >
          {busy === 'pdf' ? <span className="spinner" style={{ borderTopColor: '#EF4444', borderColor: '#FECACA' }} /> : '⬇ PDF'}
        </button>
        <button
          type="button"
          className="export-btn pptx"
          onClick={() => (onExport ? onExport('pptx') : exportReport('pptx'))}
          disabled={isGenerating || safeMessages.length === 0}
        >
          {busy === 'pptx' ? <span className="spinner" style={{ borderTopColor: '#F59E0B', borderColor: '#FDE68A' }} /> : '⬇ PPTX'}
        </button>
      </div>
      {safeMessages.length === 0 && (
        <p className="predict-hint" style={{ marginTop: 4 }}>
          Export options will appear here when the dataset analysis is ready. Ask a question first to generate content for the report.
        </p>
      )}
    </div>
  )
}

export function TimeSeriesForecastCard({ sessionId, upload }) {
  const dateCols = useMemo(() => {
    return (upload?.columns || []).filter(c => {
      const lower = String(c).toLowerCase()
      return lower.includes('date') || lower.includes('time') || lower.includes('year') || lower.includes('month') || lower.includes('day')
    })
  }, [upload])

  const numericCols = Object.keys(upload?.numeric_stats || {})
  const [dateCol, setDateCol] = useState(dateCols[0] || upload?.columns?.[0] || '')
  const [targetCol, setTargetCol] = useState(numericCols[0] || upload?.columns?.[1] || '')
  const [periods, setPeriods] = useState(12)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)

  const runForecast = async () => {
    if (!dateCol || !targetCol) return
    setBusy(true); setResult(null)
    try {
      const res = await fetch(`${API}/forecast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Session-Token': upload?.token || '' },
        body: JSON.stringify({ session_id: sessionId, date_column: dateCol, target_column: targetCol, periods }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Forecast failed')
      setResult(data)
    } catch (e) {
      alert(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="insight-card forecast-card">
      <div className="ic-head"><ChartUp width={15} height={15} /> Time-Series Forecast</div>
      <p className="predict-hint">Extrapolate future trends and 95% confidence bounds for <strong>{targetCol || 'metrics'}</strong>.</p>
      <div className="scenario-controls">
        <label>
          <span>Date Column</span>
          <select value={dateCol} onChange={e => setDateCol(e.target.value)}>
            {(upload?.columns || []).map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <label>
          <span>Target Metric</span>
          <select value={targetCol} onChange={e => setTargetCol(e.target.value)}>
            {numericCols.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <label>
          <span>Horizon</span>
          <select value={periods} onChange={e => setPeriods(+e.target.value)}>
            <option value={6}>6 periods</option>
            <option value={12}>12 periods</option>
            <option value={24}>24 periods</option>
          </select>
        </label>
      </div>
      <button className="predict-btn" disabled={busy || !dateCol || !targetCol} onClick={runForecast}>
        {busy ? <span className="spinner" /> : <>📈 Forecast {targetCol}</>}
      </button>
      {result && (
        <div className="scenario-result">
          <div className="scenario-impact">
            <span>Trend</span>
            <strong>{result.metrics?.trend_direction} ({result.metrics?.growth_rate_pct}%)</strong>
          </div>
          {result.chart_json && <PlotlyChart json={result.chart_json} />}
        </div>
      )}
    </div>
  )
}

// ─── Dataset Insights Error Boundary & Helpers ─────────────────────────────────

export class InsightsErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    console.error("[DatasetInsights] render error", {
      error,
      componentStack: info?.componentStack,
    })
  }

  render() {
    if (this.state.hasError) {
      return (
        <section role="alert" className="insights-panel-error" style={{ padding: '16px', background: '#FEF2F2', border: '1px solid #FCA5A5', borderRadius: '8px', margin: '12px' }}>
          <strong style={{ display: 'block', fontSize: '14px', color: '#991B1B', marginBottom: '4px' }}>Dataset Insights could not be displayed</strong>
          <p style={{ margin: '0 0 12px', fontSize: '12px', color: '#7F1D1D' }}>The rest of the workspace is still available.</p>
          <button
            type="button"
            style={{ padding: '4px 10px', fontSize: '12px', borderRadius: '4px', border: '1px solid #DC2626', background: '#FFFFFF', color: '#DC2626', cursor: 'pointer' }}
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            Try again
          </button>
        </section>
      )
    }

    return this.props.children
  }
}

export const InsightsPanelErrorBoundary = InsightsErrorBoundary

export function formatNumber(value, digits = 1) {
  if (value == null || value === '') return "Not available"
  const number = Number(value)
  if (!Number.isFinite(number)) {
    return "Not available"
  }
  return number.toFixed(digits)
}

function InsightsTabPanel({ active, tabId, children }) {
  if (!active) return null
  return (
    <section
      role="tabpanel"
      id={`panel-${tabId}`}
      aria-labelledby={`tab-${tabId}`}
      tabIndex={0}
      className="tab-content-panel"
    >
      {children}
    </section>
  )
}

const TAB_CONFIG = [
  { id: 'overview', label: 'Overview' },
  { id: 'quality', label: 'Data Quality' },
  { id: 'analyze', label: 'Analyze & Model' },
  { id: 'export', label: 'Export & Build' },
]

export function DatasetInsightsPanel({ upload, category, onAsk, onStory, onInvestigate, onPredict, onOpenPaste, onOpenBenchmark, onCleanExport, onExportContract, onExportDashboard, cleaningBusy, modelInfo, loading, messages, datasets, onSelectDataset, onOpenAddDataset, onOpenJoin, onOpenCompare, style }) {
  const columns = Array.isArray(upload?.columns) ? upload.columns : []
  const numericCols = Object.keys(upload?.numeric_stats ?? {})
  const [statCol, setStatCol] = useState(numericCols[0] || '')
  const stats = upload?.numeric_stats?.[statCol]
  const [target, setTarget] = useState(columns[columns.length - 1] || '')
  const [activeTab, setActiveTab] = useState('overview')
  const [predictConfigured, setPredictConfigured] = useState(false)
  const [contractOpen, setContractOpen] = useState(false)
  const [statsOpen, setStatsOpen] = useState(false)
  const [advancedOpen, setAdvancedOpen] = useState(false)
  const [showAllQuestions, setShowAllQuestions] = useState(false)

  useEffect(() => {
    if (!target || !columns.includes(target)) {
      setTarget(columns[columns.length - 1] || '')
    }
  }, [columns, target])

  const handleTabChange = (nextTab) => {
    console.debug("[insights-tab] changing tab", {
      previousTab: activeTab,
      nextTab,
      currentUrl: window.location.href,
    })
    setActiveTab(nextTab)
  }

  // Unified Dataset Score Model
  const datasetScores = useMemo(() => {
    if (!upload) {
      return {
        readinessScore: 0,
        healthScore: 0,
        readinessLabel: 'not_ready',
        healthLabel: 'No dataset',
        totalRows: 0,
        totalCols: 0,
        totalIssueCount: 0,
        missingPct: 0,
        dupRows: 0,
        outlierColsCount: 0,
        totalOutliers: 0,
        numericColsCount: 0,
        rawIssues: [],
        outlierIssues: [],
      }
    }

    const totalRows = upload.rows || 0
    const totalCols = columns.length
    const missingPct = upload.missing_pct || 0
    const dupRows = upload.duplicate_rows || 0
    const dupPct = totalRows > 0 ? (dupRows / totalRows) * 100 : 0
    const rawIssues = upload.quality_report?.issues || []

    const outlierIssues = rawIssues.filter(i => i.type === 'outliers' || (i.title && i.title.toLowerCase().includes('outlier')))
    const outlierColsCount = outlierIssues.length
    const totalOutliers = outlierIssues.reduce((acc, curr) => acc + (curr.count || 1), 0)

    let healthScore = 100
    if (missingPct > 0) healthScore -= Math.min(30, Math.round(missingPct * 2))
    if (dupPct > 0) healthScore -= Math.min(25, Math.round(dupPct))
    if (outlierColsCount > 0) healthScore -= Math.min(25, outlierColsCount * 5)
    if (rawIssues.length > 0 && healthScore === 100) healthScore = 90
    healthScore = Math.max(35, healthScore)

    let readinessScore = upload.decision_brief?.readiness_score
    if (readinessScore == null) {
      readinessScore = Math.max(40, healthScore - 10)
    }

    let readinessLabel = 'usable_with_caution'
    if (healthScore >= 90 && readinessScore >= 85) readinessLabel = 'ready_for_analysis'
    else if (healthScore >= 70) readinessLabel = 'usable_with_caution'
    else readinessLabel = 'requires_remediation'

    let healthLabel = 'Healthy schema'
    if (healthScore < 70) healthLabel = 'Multiple quality issues'
    else if (healthScore < 90) healthLabel = 'Several values require review'

    const totalIssueCount = rawIssues.length + (dupRows > 0 ? 1 : 0) + (missingPct > 0 ? 1 : 0)

    return {
      readinessScore,
      healthScore,
      readinessLabel: readinessLabel.replaceAll('_', ' '),
      healthLabel,
      totalRows,
      totalCols,
      totalIssueCount,
      missingPct,
      dupRows,
      outlierColsCount,
      totalOutliers,
      numericColsCount: upload.numeric_features ?? 0,
      rawIssues,
      outlierIssues,
    }
  }, [upload, columns])

  // Deduplicated Recommended Actions (Max 3)
  const deduplicatedActions = useMemo(() => {
    if (!upload) return []
    const actions = []
    const seenTitles = new Set()

    if (upload.decision_brief?.next_actions) {
      for (const a of upload.decision_brief.next_actions) {
        if (!seenTitles.has(a.action.toLowerCase())) {
          seenTitles.add(a.action.toLowerCase())
          actions.push({
            id: `brief-${a.action}`,
            title: a.action,
            explanation: a.impact || 'Recommended to improve model reliability.',
            priority: a.priority || 'medium',
            actionLabel: 'Investigate',
            question: `Investigate ${a.action}`
          })
        }
      }
    }

    if (datasetScores.totalOutliers > 0 && !seenTitles.has('outliers')) {
      seenTitles.add('outliers')
      actions.push({
        id: 'action-outliers',
        title: `Review ${datasetScores.totalOutliers} potential outliers across ${datasetScores.outlierColsCount} columns`,
        explanation: 'Unusual extreme values may skew linear statistical summaries and tree splits.',
        priority: 'high',
        actionLabel: 'Inspect Outliers',
        question: 'Inspect columns with potential outliers and statistical ranges'
      })
    }

    return actions.slice(0, 3)
  }, [upload, datasetScores])

  // Date column detection for time-series forecasting
  const dateCol = useMemo(() => {
    if (!columns.length) return null
    const timeKeywords = ['date', 'time', 'timestamp', 'created_at', 'updated_at']
    return columns.find(c => timeKeywords.some(k => String(c).toLowerCase().includes(k)))
  }, [columns])

  const brief = upload?.decision_brief
  const cleaningPlan = upload?.cleaning_plan
  const contract = upload?.data_contract
  const dashboard = upload?.dashboard_spec

  const priorityQuestions = brief?.priority_questions || [
    'Which numeric columns are most strongly correlated?',
    'What data-quality issues should I fix first?',
    'Which columns have the most unusual distributions?'
  ]

  if (!upload) {
    return (
      <aside className="insights" style={style}>
        <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)' }}>
          Upload a dataset to view insights and modeling tools.
        </div>
      </aside>
    )
  }

  return (
    <aside className="insights" style={style}>
      {/* Sticky Panel Header & Filename */}
      <div className="insights-header-sticky">
        <div className="insights-title-row">
          <div>
            <h3 className="insights-main-title">Dataset Insights</h3>
            <span className="insights-filename">{upload.filename || 'dataset.csv'}</span>
          </div>
        </div>

        {/* 4-Tab Navigation */}
        <div className="tab-nav-4" role="tablist">
          {TAB_CONFIG.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              id={`tab-${t.id}`}
              aria-selected={activeTab === t.id}
              aria-controls={`panel-${t.id}`}
              className={`tab-btn ${activeTab === t.id ? 'active' : ''}`}
              onClick={(e) => { e.preventDefault(); handleTabChange(t.id); }}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* ── TAB 1: OVERVIEW ────────────────────────────────────────────── */}
      <InsightsTabPanel active={activeTab === 'overview'} tabId="overview">
        {/* Primary Summary Card */}
        <div className="insight-card decision-card">
          <div className="ic-head"><Layers width={15} height={15} /> Primary Summary</div>
          <div className="summary-score-grid">
            <div className="score-badge-box">
              <span className="score-num">{datasetScores.readinessScore}</span>
              <span className="score-lbl">Readiness ({datasetScores.readinessLabel})</span>
            </div>
            <div className="score-badge-box">
              <span className="score-num">{datasetScores.healthScore}/100</span>
              <span className="score-lbl">Data Health ({datasetScores.healthLabel})</span>
            </div>
          </div>

          <div className="dimensions-summary-row">
            <span><strong>{datasetScores.totalRows.toLocaleString()}</strong> rows</span>
            <span><strong>{datasetScores.totalCols}</strong> columns</span>
            <span><strong>{datasetScores.totalIssueCount}</strong> issues</span>
          </div>

          <p className="dataset-one-liner">
            {brief?.summary || `This dataset contains ${datasetScores.totalRows} rows and ${datasetScores.totalCols} columns, suitable for exploratory analysis and modeling after reviewing potential outliers.`}
          </p>

          {/* Best Use Cases */}
          {brief?.recommended_use_cases?.length > 0 && (
            <div className="brief-section">
              <div className="brief-kicker">Best Use Cases</div>
              {brief.recommended_use_cases.slice(0, 3).map((item) => (
                <div key={item.name} className="brief-use">
                  <span>{item.name}</span>
                  <em className="use-case-fit">{item.fit}</em>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Top Recommended Actions (Max 3 Deduplicated) */}
        {deduplicatedActions.length > 0 && (
          <div className="insight-card action-card">
            <div className="ic-head"><Sparkles width={15} height={15} /> Top Recommended Actions</div>
            <div className="action-list">
              {deduplicatedActions.map((act) => (
                <div key={act.id} className={`decision-action ${act.priority}`}>
                  <div className="action-top">
                    <strong>{act.title}</strong>
                    <span className={`priority-tag ${act.priority}`}>{act.priority}</span>
                  </div>
                  <p>{act.explanation}</p>
                  <button
                    type="button"
                    className="action-investigate"
                    disabled={loading}
                    onClick={() => onInvestigate(act.question)}
                  >
                    {act.actionLabel} →
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </InsightsTabPanel>

      {/* ── TAB 2: DATA QUALITY ────────────────────────────────────────── */}
      <InsightsTabPanel active={activeTab === 'quality'} tabId="quality">
        {/* Quality Summary Row */}
        <div className="insight-card quality-stats-card">
          <div className="ic-head"><Activity width={15} height={15} /> Quality Summary</div>
          <div className="quality-metrics-grid">
            <div className="qm-item"><span>Missing</span><strong>{datasetScores.missingPct}%</strong></div>
            <div className="qm-item"><span>Duplicates</span><strong>{datasetScores.dupRows}</strong></div>
            <div className="qm-item"><span>Numeric</span><strong>{datasetScores.numericColsCount} cols</strong></div>
            <div className="qm-item"><span>Outlier Cols</span><strong>{datasetScores.outlierColsCount}</strong></div>
            <div className="qm-item"><span>Total Outliers</span><strong>{datasetScores.totalOutliers}</strong></div>
          </div>
        </div>

        {/* Grouped Outliers Table */}
        <div className="insight-card">
          <div className="ic-head">
            <AlertDot width={15} height={15} className="status-icon" />
            <span>Potential Outliers ({datasetScores.totalOutliers} total)</span>
          </div>
          {datasetScores.outlierIssues.length === 0 ? (
            <p className="predict-hint">No severe potential outliers detected across numeric columns.</p>
          ) : (
            <div className="outliers-group-box">
              <table className="outliers-table">
                <thead>
                  <tr>
                    <th>Column</th>
                    <th>Count</th>
                    <th>Severity</th>
                  </tr>
                </thead>
                <tbody>
                  {datasetScores.outlierIssues.map((item, idx) => {
                    const colName = item.column || item.title?.replace(/outliers? in/i, '').trim() || `Col ${idx + 1}`
                    const count = item.count || 1
                    const severity = item.severity || (count > 20 ? 'high' : 'low')
                    return (
                      <tr key={idx}>
                        <td><strong>{colName}</strong></td>
                        <td>{count}</td>
                        <td><span className={`severity-chip ${severity}`}>{severity}</span></td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
              <button
                type="button"
                className="btn-secondary-action compact"
                style={{ marginTop: '10px', width: '100%' }}
                disabled={loading}
                onClick={() => onInvestigate('Inspect columns with potential outliers and statistical distributions')}
              >
                Inspect outliers
              </button>
            </div>
          )}
        </div>

        {/* Cleaning Plan */}
        {cleaningPlan?.actions?.length > 0 && (
          <div className="insight-card cleaning-card">
            <div className="ic-head"><Check width={15} height={15} /> Cleaning Plan</div>
            <p className="predict-hint">{cleaningPlan.summary}</p>
            <div className="cleaning-actions">
              {cleaningPlan.actions.slice(0, 4).map((action) => (
                <div key={action.id} className={`cleaning-action ${action.default ? 'default' : ''}`}>
                  <strong>{action.title}</strong>
                  <span>{action.impact}</span>
                </div>
              ))}
            </div>
            <button type="button" className="clean-export-btn" disabled={cleaningBusy} onClick={onCleanExport}>
              {cleaningBusy ? <span className="spinner" /> : <Check width={14} height={14} />}
              Download cleaned CSV
            </button>
          </div>
        )}

        {/* Collapsible Data Contract */}
        {contract && (
          <div className="insight-card contract-card">
            <div
              className="accordion-summary-clean"
              onClick={() => setContractOpen((v) => !v)}
              role="button"
              tabIndex={0}
              aria-expanded={contractOpen}
              onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setContractOpen((v) => !v)}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Columns width={15} height={15} style={{ color: 'var(--primary)' }} />
                <span>Data Contract</span>
              </div>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{contractOpen ? 'Hide ▲' : 'Show ▲'}</span>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-soft)', marginTop: '4px' }}>
              {contract.column_count || datasetScores.totalCols} columns · {contract.required_columns?.length || 0} required · All numeric
            </div>

            {contractOpen && (
              <div className="accordion-content" style={{ marginTop: '10px' }}>
                <div className="contract-cols">
                  {contract.columns?.slice(0, 10).map((col) => (
                    <div key={col.name} className="contract-col">
                      <span>{col.name}</span>
                      <em>{col.type}</em>
                    </div>
                  ))}
                </div>
                <button type="button" className="contract-export-btn" style={{ marginTop: '10px' }} onClick={onExportContract}>
                  <Code width={14} height={14} /> Export contract JSON
                </button>
              </div>
            )}
          </div>
        )}
      </InsightsTabPanel>

      {/* ── TAB 3: ANALYZE & MODEL ──────────────────────────────────────── */}
      <InsightsTabPanel active={activeTab === 'analyze'} tabId="analyze">
        {console.debug('[insights-tab] rendering AnalyzeModelTab', { columns, numericCols, dateCol, modelInfo })}
        {/* Section: Explore */}
        <div className="section-group-label">Explore</div>

        {/* Priority Questions */}
        <div className="insight-card">
          <div className="ic-head"><Sparkles width={15} height={15} /> Suggested Questions</div>
          <div className="suggest-list">
            {(showAllQuestions ? priorityQuestions : priorityQuestions.slice(0, 3)).map((q, idx) => {
              const questionText = typeof q === 'string' ? q : q.q || q.label
              return (
                <button key={idx} type="button" className="suggest-btn" disabled={loading} onClick={() => onAsk(questionText)}>
                  <span>{questionText}</span>
                  <span className="suggest-arrow">→</span>
                </button>
              )
            })}
          </div>
          {priorityQuestions.length > 3 && (
            <button
              type="button"
              className="btn-text-link"
              style={{ marginTop: '6px', fontSize: '12px' }}
              onClick={() => setShowAllQuestions(v => !v)}
            >
              {showAllQuestions ? 'Show less ▲' : 'Show more ▼'}
            </button>
          )}
        </div>

        {/* Quick Statistics with Column Selector */}
        {numericCols.length > 0 && (
          <div className="insight-card">
            <div
              className="accordion-summary-clean"
              onClick={() => setStatsOpen((v) => !v)}
              role="button"
              tabIndex={0}
              aria-expanded={statsOpen}
              onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setStatsOpen((v) => !v)}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ChartUp width={15} height={15} style={{ color: 'var(--primary)' }} />
                <span>Quick Statistics</span>
              </div>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{statsOpen ? 'Hide ▲' : 'Show ▲'}</span>
            </div>

            {statsOpen && (
              <div className="accordion-content" style={{ marginTop: '10px' }}>
                <div className="stat-select-row">
                  <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-soft)' }}>Select Column:</span>
                  <select className="stat-select" value={statCol} onChange={(e) => setStatCol(e.target.value)}>
                    {numericCols.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                {stats && (
                  <div className="stat-grid" style={{ marginTop: '10px' }}>
                    <Stat label="Mean" v={stats.mean} />
                    <Stat label="Median" v={stats.median} />
                    <Stat label="Std Dev" v={stats.std} />
                    <Stat label="Min" v={stats.min} />
                    <Stat label="Max" v={stats.max} />
                    <Stat label="Range" v={stats.max != null && stats.min != null ? +(stats.max - stats.min).toFixed(2) : null} />
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Dataset Story */}
        <div className="insight-card story-card">
          <div className="ic-head"><Sparkles width={15} height={15} /> Dataset Story</div>
          <p className="predict-hint">Generate a fact-first narrative from computed dataset profile facts.</p>
          <button type="button" className="custom-btn" disabled={loading} onClick={onStory}>
            <Sparkles width={14} height={14} /> Generate dataset story
          </button>
        </div>

        {/* Section: Model */}
        <div className="section-group-label" style={{ marginTop: '14px' }}>Model</div>

        {/* Predictive Model Form */}
        <div className="insight-card predict-card">
          <div className="ic-head"><Brain width={15} height={15} /> Predictive Model</div>
          <p className="predict-hint">Train a model to predict a selected column and see feature importance.</p>

          {columns.length < 2 ? (
            <p className="predict-hint" style={{ color: 'var(--text-muted)', marginTop: '8px' }}>
              Predictive modeling requires at least two usable columns.
            </p>
          ) : !predictConfigured ? (
            <button
              type="button"
              className="btn-secondary-action full"
              style={{ marginTop: '8px' }}
              onClick={() => setPredictConfigured(true)}
            >
              <Sliders width={14} height={14} /> Configure model
            </button>
          ) : (
            <div className="predict-form-expanded" style={{ marginTop: '10px' }}>
              <div className="predict-row">
                <span className="predict-label">Predict target</span>
                <select className="predict-select" value={target} onChange={(e) => setTarget(e.target.value)}>
                  {columns.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
                <button type="button" className="predict-btn" style={{ flex: 1 }} disabled={loading || !target} onClick={() => onPredict(target)}>
                  {loading ? <span className="spinner" /> : <>🔮 Train &amp; Predict</>}
                </button>
                <button type="button" className="btn-secondary-action" onClick={() => setPredictConfigured(false)}>Cancel</button>
              </div>
            </div>
          )}
        </div>

        {modelInfo?.trained && (
          <>
            <PredictInputCard sessionId={upload.session_id} modelInfo={modelInfo} upload={upload} />
            <ScenarioSimulatorCard sessionId={upload.session_id} modelInfo={modelInfo} category={category} upload={upload} />
          </>
        )}

        {/* Time-Series Forecast */}
        {dateCol ? (
          <TimeSeriesForecastCard sessionId={upload.session_id} upload={upload} dateCol={dateCol} />
        ) : (
          <div className="insight-card forecast-card disabled">
            <div className="ic-head"><TrendingUp width={15} height={15} /> Time-Series Forecast</div>
            <p className="predict-hint" style={{ color: 'var(--text-muted)' }}>
              Forecasting is unavailable because no date or time column was detected.
            </p>
          </div>
        )}

        {/* Section: Custom */}
        <div className="section-group-label" style={{ marginTop: '14px' }}>Custom</div>
        <div className="insight-card custom-card">
          <div className="ic-head"><Code width={15} height={15} /> Custom Data</div>
          <p className="predict-hint">Paste your own rows or values to analyze them on the fly.</p>
          <button type="button" className="custom-btn" disabled={loading} onClick={onOpenPaste}>
            <Code width={14} height={14} /> Paste / input data
          </button>
        </div>
      </InsightsTabPanel>

      {/* ── TAB 4: EXPORT & BUILD ───────────────────────────────────────── */}
      <InsightsTabPanel active={activeTab === 'export'} tabId="export">
        {console.debug('[insights-tab] rendering ExportBuildTab', { contract, dashboard })}
        {/* User-facing Reports (PDF, PPTX) */}
        <ExportCard upload={upload} messages={messages} category={category} />

        {/* Dashboard Blueprint */}
        {dashboard && (
          <div className="insight-card dashboard-card">
            <div className="ic-head"><ChartUp width={15} height={15} /> Dashboard Blueprint</div>
            <div className="dashboard-stats">
              <div><strong>{dashboard.kpis?.length ?? 4}</strong><span>KPIs</span></div>
              <div><strong>{dashboard.charts?.length ?? 2}</strong><span>charts</span></div>
              <div><strong>{dashboard.filters?.length ?? 0}</strong><span>filters</span></div>
            </div>
            <button type="button" className="dashboard-export-btn" onClick={onExportDashboard}>
              <Code width={14} height={14} /> Download dashboard configuration
            </button>
          </div>
        )}

        {/* Developer Exports */}
        <div className="insight-card">
          <div className="ic-head"><Code width={15} height={15} /> Developer Exports</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }}>
            {contract && (
              <button type="button" className="btn-secondary-action full" onClick={onExportContract}>
                <Code width={14} height={14} /> Export data contract JSON
              </button>
            )}
            {dashboard && (
              <button type="button" className="btn-secondary-action full" onClick={onExportDashboard}>
                <Code width={14} height={14} /> Export dashboard JSON
              </button>
            )}
          </div>
        </div>

        {/* Advanced Section Collapsible (Evaluation Benchmark) */}
        <div className="insight-card benchmark-card">
          <div
            className="accordion-summary-clean"
            onClick={() => setAdvancedOpen((v) => !v)}
            role="button"
            tabIndex={0}
            aria-expanded={advancedOpen}
            onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setAdvancedOpen((v) => !v)}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sparkles width={15} height={15} style={{ color: 'var(--primary)' }} />
              <span>Advanced Evaluation</span>
            </div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{advancedOpen ? 'Hide ▲' : 'Show ▲'}</span>
          </div>

          {advancedOpen && (
            <div className="accordion-content" style={{ marginTop: '10px' }}>
              <p className="predict-hint">Evaluate the system with 49 analytics questions measuring accuracy and latency.</p>
              <button type="button" className="custom-btn" disabled={loading} onClick={onOpenBenchmark}>
                ▶ Run evaluation benchmark
              </button>
            </div>
          )}
        </div>
      </InsightsTabPanel>
    </aside>
  )
}

export const InsightsPanel = DatasetInsightsPanel






function Stat({ label, v }) {
  return (
    <div className="stat-box">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{v == null ? '—' : v.toLocaleString()}</div>
    </div>
  )
}

// ─── Interactive Plotly chart ──────────────────────────────────────────────────

function PlotlyChart({ json }) {
  const ref = useRef()
  useEffect(() => {
    if (!ref.current || !json) return
    let alive = true
    let PlotlyLib = null

    const render = async () => {
      let fig
      try { fig = JSON.parse(json) } catch { return }
      const mod = await import('plotly.js-dist-min')
      PlotlyLib = mod.default ?? mod
      if (!alive || !ref.current) return
      PlotlyLib.newPlot(ref.current, fig.data, {
        ...fig.layout,
        paper_bgcolor: 'white',
        plot_bgcolor: 'white',
        font: { family: 'Inter, Segoe UI, Helvetica Neue, Arial, sans-serif', size: 12 },
        margin: fig.layout?.margin ?? { l: 60, r: 30, t: 60, b: 60 },
        autosize: true,
      }, { responsive: true, displayModeBar: true, displaylogo: false,
           modeBarButtonsToRemove: ['select2d', 'lasso2d'] })
    }

    render()
    return () => {
      alive = false
      if (ref.current && PlotlyLib) PlotlyLib.purge(ref.current)
    }
  }, [json])
  return <div ref={ref} className="plotly-chart" />
}

// ─── Chat ──────────────────────────────────────────────────────────────────────

function AgentStep({ step }) {
  const meta = STEP_META[step.step] || { icon: Activity, color: '#94A3B8' }
  const StepIcon = typeof meta.icon === 'function' ? meta.icon : Activity
  const trace = step.meta || {}
  const elapsed = trace.elapsed_ms != null
    ? trace.elapsed_ms < 1000
      ? `${trace.elapsed_ms} ms`
      : `${(trace.elapsed_ms / 1000).toFixed(1)} s`
    : null
  const requestShort = trace.request_id ? trace.request_id.slice(0, 8) : null
  return (
    <div className="step-row" style={{ '--step-color': meta.color }}>
      <span className="step-icon"><StepIcon width={14} height={14} /></span>
      <span className="step-content">
        <span className="step-label">{step.message}</span>
        {(trace.route || elapsed || requestShort) && (
          <span className="step-trace">
            {trace.route && <span>{trace.route}</span>}
            {elapsed && <span>{elapsed}</span>}
            {requestShort && <span>req {requestShort}</span>}
          </span>
        )}
      </span>
    </div>
  )
}

const VERDICT_META = {
  pass: { color: '#10B981', bg: '#F0FDF4', border: '#BBF7D0', label: 'PASS' },
  warn: { color: '#F59E0B', bg: '#FFFBEB', border: '#FDE68A', label: 'WARN' },
  fail: { color: '#EF4444', bg: '#FEF2F2', border: '#FECACA', label: 'FAIL' },
}

function CritiqueBadge({ critique }) {
  if (!critique || critique.verdict === 'pass') return null
  const suggestion = critique.suggestion || critique.issues?.[0]
  if (!suggestion) return null

  return (
    <div className="critique-simple-note">
      <Sparkles width={13} height={13} style={{ color: 'var(--primary)' }} />
      <span><strong>Note:</strong> {suggestion.replace(/^💡\s*/, '')}</span>
    </div>
  )
}

function ValidationPanel({ validation }) {
  if (!validation || (!validation.missing_pct && !validation.source_columns?.length)) return null
  return (
    <div className="validation-simple-note">
      <Check width={13} height={13} style={{ color: 'var(--primary)' }} />
      <span>Verified across {Number(validation.row_support || 0).toLocaleString()} rows ({validation.source_columns?.join(', ') || 'source data'})</span>
    </div>
  )
}

function AnswerTrustBadge({ route, validation, critique }) {
  const normalized = (route || '').replaceAll('_', ' ')
  const routeLabel = route === 'deterministic'
    ? 'Deterministic'
    : route === 'llm'
      ? 'AI Agent'
      : route === 'cache'
        ? 'Cached'
        : normalized
          ? normalized.replace(/\b\w/g, (c) => c.toUpperCase())
          : 'Analysis'
  const confidence = validation?.confidence ?? critique?.confidence
  const confidenceText = confidence != null ? `${Math.round(confidence * 100)}%` : validation?.confidence_label
  const level = validation?.confidence_label || (confidence >= 0.9 ? 'High' : confidence >= 0.7 ? 'Medium' : 'Review')

  return (
    <span className="answer-trust-badge" title={validation?.method || critique?.suggestion || routeLabel}>
      <span>{routeLabel}</span>
      {(level || confidenceText) && <em>{level}{confidenceText ? ` · ${confidenceText}` : ''}</em>}
    </span>
  )
}

function PlanBadge({ plan }) {
  const [open, setOpen] = useState(false)
  if (!plan?.strategy) return null
  return (
    <div className="accordion-row">
      <div
        className="accordion-summary-clean"
        onClick={() => setOpen(v => !v)}
        role="button"
        tabIndex={0}
        aria-expanded={open}
        onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setOpen(v => !v)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Layers width={13} height={13} style={{ color: 'var(--primary)' }} />
          <span>Strategy: {plan.strategy}</span>
        </div>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{open ? 'Hide ▲' : 'Details ▼'}</span>
      </div>
      {open && (
        <div className="accordion-content">
          {plan.persona && (
            <div className="plan-persona-row" style={{ marginBottom: '8px' }}>
              <strong>{plan.persona.name}</strong>: <span style={{ color: 'var(--text-soft)' }}>{plan.persona.focus}</span>
            </div>
          )}
          {plan.analysis_steps?.length > 0 && (
            <ol className="plan-steps" style={{ margin: '0 0 8px 16px', padding: 0 }}>
              {plan.analysis_steps.map((s, i) => <li key={i}>{s}</li>)}
            </ol>
          )}
          {plan.relevant_columns?.length > 0 && (
            <div className="plan-cols" style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', alignItems: 'center', fontSize: '11px', color: 'var(--text-muted)' }}>
              Columns: {plan.relevant_columns.map(c => <span key={c} className="plan-col">{c}</span>)}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const EXPLAIN_TABS = [
  { key: 'importance', label: 'Feature Importance', field: 'chart' },
  { key: 'shap',       label: 'SHAP Beeswarm',     field: 'shap_chart' },
  { key: 'perm',       label: 'Permutation',        field: 'perm_chart' },
  { key: 'pdp',        label: 'Partial Dependence', field: 'pdp_chart' },
]

function ExplainPanel({ msg }) {
  const available = EXPLAIN_TABS.filter(t => msg[t.field])
  const [active, setActive] = useState(0)
  if (available.length === 0) return null
  const current = available[active]
  return (
    <div className="explain-panel">
      <div className="explain-label"><Brain width={14} height={14} /> Explainability</div>
      <div className="explain-tabs">
        {available.map((t, i) => (
          <button key={t.key} className={`explain-tab ${i === active ? 'active' : ''}`}
            onClick={() => setActive(i)}>{t.label}</button>
        ))}
      </div>
      <img className="chart-img" src={`data:image/png;base64,${msg[current.field]}`}
        alt={current.label} />
    </div>
  )
}

function RowTableSection({ rowData }) {
  if (!rowData || !rowData.fields) return null
  return (
    <div className="row-lookup-card">
      <div className="row-lookup-header">
        <Layers width={14} height={14} style={{ color: 'var(--primary)' }} />
        <span>Row {rowData.display_row} Details</span>
        <span className="row-lookup-count">{rowData.fields.length} columns</span>
      </div>
      <div className="row-lookup-table-wrap">
        <table className="row-lookup-table">
          <thead>
            <tr>
              <th>Column</th>
              <th>Value</th>
            </tr>
          </thead>
          <tbody>
            {rowData.fields.map((f) => (
              <tr key={f.field}>
                <td><strong>{f.field}</strong></td>
                <td>{f.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function LiveExecutionLog({ steps, isDone, latestMeta, lensRes, isStreaming, onStop }) {
  const [open, setOpen] = useState(!isDone)
  const logRef = useRef(null)

  useEffect(() => {
    if (isDone) setOpen(false)
  }, [isDone])

  const displaySteps = useMemo(() => {
    return steps.filter(s => !['plan', 'critique', 'code'].includes(s.step))
  }, [steps])

  const totalMs = latestMeta?.elapsed_ms || (steps[steps.length - 1]?.meta?.elapsed_ms)
  const durationText = totalMs != null ? (totalMs < 1000 ? `${totalMs}ms` : `${(totalMs / 1000).toFixed(1)}s`) : null

  if (isDone && (!displaySteps || displaySteps.length === 0)) {
    return null
  }

  if (isDone && !open) {
    return (
      <div className="accordion-row">
        <div
          className="accordion-summary-clean"
          onClick={() => setOpen(true)}
          role="button"
          tabIndex={0}
          aria-expanded={false}
          aria-controls="execution-log-details"
          onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setOpen(true)}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Check width={13} height={13} style={{ color: 'var(--primary)' }} />
            <span>Execution details</span>
            {durationText && <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>({durationText})</span>}
          </div>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{displaySteps.length} steps ▼</span>
        </div>
      </div>
    )
  }

  return (
    <div className="accordion-row" id="execution-log-details">
      {isDone && (
        <div
          className="accordion-summary-clean"
          onClick={() => setOpen(false)}
          role="button"
          tabIndex={0}
          aria-expanded={true}
          onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setOpen(false)}
        >
          <span>Execution details</span>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Hide details ▲</span>
        </div>
      )}
      <div className="accordion-content">
        <div className="live-log-container" ref={logRef} role="region" aria-live="polite" aria-label="Live execution checklist">
          {displaySteps.map((s, idx) => {
            const isLast = idx === displaySteps.length - 1
            const isRunning = !isDone && isLast
            const isWarning = s.step === 'lens_switch' || s.step === 'warning'
            const isError = s.step === 'error'

            let icon = '✓'
            let statusClass = 'complete'
            if (isRunning) {
              icon = '⚡'
              statusClass = 'running'
            } else if (isWarning) {
              icon = '⚠️'
              statusClass = 'warning'
            } else if (isError) {
              icon = '✕'
              statusClass = 'error'
            }

            return (
              <div key={idx} className={`log-step-row ${statusClass}`}>
                <span className="log-step-icon">{isRunning ? <span className="running-pulse-dot" /> : icon}</span>
                <span className="log-step-text">{s.message || s.label || s.step}</span>
              </div>
            )
          })}
          {!isDone && (
            <div className="log-step-row running">
              <span className="log-step-icon"><span className="running-pulse-dot" /></span>
              <span className="log-step-text">Processing analysis pipeline…</span>
            </div>
          )}
        </div>
        {isStreaming && onStop && (
          <button className="btn-stop-analysis" onClick={onStop}>
            ■ Stop analysis
          </button>
        )}
      </div>
    </div>
  )
}

function getPrimitiveText(value) {
  if (typeof value === 'string') {
    const trimmed = value.trim()
    return trimmed.length > 0 ? trimmed : undefined
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  return undefined
}

function normalizeStepStatus(val) {
  const s = String(val || '').toLowerCase()
  if (s === 'complete' || s === 'completed' || s === 'success' || s === 'done') return 'complete'
  if (s === 'warning' || s === 'lens_switch') return 'warning'
  if (s === 'error' || s === 'failed') return 'failed'
  if (s === 'running' || s === 'executing' || s === 'pending') return 'running'
  return 'complete'
}

function normalizeExecutionStep(step, index) {
  return {
    id: String(step?.id || step?.step_id || step?.stepId || `step-${index + 1}`),
    label: String(step?.label || step?.name || step?.title || step?.message || step?.step || 'Analysis step'),
    detail: step?.detail || step?.description || step?.summary || step?.message,
    status: normalizeStepStatus(step?.status || step?.step),
    durationMs: step?.duration_ms || step?.durationMs || step?.meta?.elapsed_ms,
  }
}

function normalizeStatus(val) {
  const s = String(val || '').toLowerCase()
  if (s === 'complete' || s === 'completed' || s === 'success' || s === 'succeeded' || s === 'done') return 'complete'
  if (s === 'partial' || s === 'streaming') return 'partial'
  if (s === 'error' || s === 'failed' || s === 'failure') return 'failed'
  return 'running'
}

const PROGRESS_EVENT_TYPES = new Set([
  'analysis_started',
  'route_selected',
  'step_started',
  'step_completed',
  'execution_step',
  'progress',
  'log',
  'agent_started',
  'agent_completed',
  'strategy',
  'understanding',
  'lens_check',
  'thinking',
  'planning',
  'analyzing',
  'visualizing',
  'critiquing',
  'reporting',
  'code',
  'plan',
  'analyst',
  'critique',
])

const PARTIAL_RESULT_EVENT_TYPES = new Set([
  'partial_result',
  'section_updated',
  'answer_partial',
])

const TERMINAL_PARTIAL_EVENT_TYPES = new Set([
  'analysis_partial',
])

const SUCCESS_EVENT_TYPES = new Set([
  'analysis_completed',
  'completed',
  'done',
])

const FAILURE_EVENT_TYPES = new Set([
  'analysis_failed',
  'failed',
  'error',
])

function classifyStreamEvent(event) {
  const type = String(event?.type ?? event?.event ?? event?.step ?? '').toLowerCase()

  if (SUCCESS_EVENT_TYPES.has(type)) {
    return 'terminal-success'
  }
  if (FAILURE_EVENT_TYPES.has(type)) {
    return 'terminal-failure'
  }
  if (TERMINAL_PARTIAL_EVENT_TYPES.has(type)) {
    return 'terminal-partial'
  }
  if (PARTIAL_RESULT_EVENT_TYPES.has(type)) {
    return 'partial-result'
  }
  if (PROGRESS_EVENT_TYPES.has(type)) {
    return 'progress'
  }

  if (event?.status === 'complete' || event?.status === 'completed') {
    return 'terminal-success'
  }
  if (event?.status === 'failed' || event?.status === 'error') {
    return 'terminal-failure'
  }

  return 'progress'
}

function toDisplayText(value, fallback = '') {
  if (value == null) return fallback

  if (
    typeof value === 'string' ||
    typeof value === 'number' ||
    typeof value === 'boolean'
  ) {
    return String(value)
  }

  if (Array.isArray(value)) {
    return value
      .map((item) => toDisplayText(item))
      .filter(Boolean)
      .join('\n')
  }

  if (typeof value === 'object') {
    return (
      toDisplayText(value.message) ||
      toDisplayText(value.summary) ||
      toDisplayText(value.text) ||
      toDisplayText(value.detail) ||
      toDisplayText(value.code) ||
      fallback
    )
  }

  return fallback
}

function normalizeApiError(error) {
  if (!error) return null

  if (typeof error === 'string') {
    return {
      code: 'request_failed',
      message: error,
    }
  }

  return {
    code: toDisplayText(error.code, 'request_failed'),
    message: toDisplayText(
      error.message ?? error.detail,
      'The analysis could not be completed.'
    ),
  }
}

function normalizeStreamStatus(event) {
  const eventClass = classifyStreamEvent(event)
  if (eventClass === 'terminal-success') return 'complete'
  if (eventClass === 'terminal-partial') return 'partial'
  if (eventClass === 'terminal-failure') return 'failed'
  if (eventClass === 'partial-result') return 'partial'
  return 'running'
}

function normalizeQueryResponse(raw = {}, fallbackRequestId) {
  const rawIsObject = raw !== null && typeof raw === 'object'
  const isStreamEvent = Boolean(raw?.type || raw?.step)
  const error = normalizeApiError(raw?.error)
  const defaultStatus = isStreamEvent ? normalizeStreamStatus(raw) : (error ? 'failed' : 'complete')

  const nestedResult =
    rawIsObject && raw.result !== null && typeof raw.result === 'object'
      ? raw.result
      : rawIsObject && raw.data !== null && typeof raw.data === 'object'
        ? raw.data
        : rawIsObject && raw.analysis !== null && typeof raw.analysis === 'object'
          ? raw.analysis
          : rawIsObject
            ? raw
            : {}

  const answerObject =
    nestedResult.answer ??
    nestedResult.final_answer ??
    nestedResult.finalAnswer ??
    nestedResult.response ??
    nestedResult.output

  const primitiveResultText =
    getPrimitiveText(raw?.result) ??
    getPrimitiveText(nestedResult?.result)

  let answerText =
    toDisplayText(answerObject?.summary) ||
    toDisplayText(answerObject?.explanation) ||
    toDisplayText(answerObject?.text) ||
    toDisplayText(answerObject) ||
    primitiveResultText ||
    toDisplayText(raw?.report) ||
    toDisplayText(raw?.answer) ||
    toDisplayText(raw?.response) ||
    toDisplayText(raw?.output) ||
    error?.message ||
    ''

  let answerType =
    nestedResult.answer_type ??
    nestedResult.answerType

  let answerData

  if (typeof answerObject === 'string') {
    answerText = answerObject.trim() || answerText
  } else if (answerObject && typeof answerObject === 'object') {
    answerType = answerObject.type ?? answerType
    answerData =
      answerObject.data ??
      answerObject.payload ??
      answerObject.rows ??
      answerObject.values
  }

  if (!answerData) {
    answerData = raw?.row_data ?? raw?.payload?.row_data ?? nestedResult?.row_data
  }

  const rawSteps =
    nestedResult.execution_steps ??
    nestedResult.executionSteps ??
    nestedResult.steps ??
    nestedResult.trace ??
    nestedResult.agent_steps ??
    nestedResult.agentSteps ??
    nestedResult.logs ??
    raw?.execution_steps ??
    raw?.executionSteps ??
    raw?.steps ??
    raw?.trace ??
    raw?.agent_steps ??
    raw?.logs ??
    []

  return {
    requestId: String(
      nestedResult.request_id ??
      nestedResult.requestId ??
      raw?.request_id ??
      raw?.requestId ??
      fallbackRequestId
    ),
    status: normalizeStatus(nestedResult.status ?? raw?.status ?? defaultStatus),
    answer: raw?.answer ?? nestedResult.answer ?? null,
    error,
    answerText: typeof answerText === 'string' ? answerText : toDisplayText(answerText),
    answerType: answerType || (answerData?.fields ? 'row_lookup' : 'text'),
    answerData,
    executionSteps: Array.isArray(rawSteps)
      ? rawSteps.map(normalizeExecutionStep)
      : [],
    warnings: Array.isArray(nestedResult.warnings ?? raw?.warnings) ? (nestedResult.warnings ?? raw?.warnings) : [],
    generatedCode:
      nestedResult.generated_code ??
      nestedResult.generatedCode ??
      raw?.generated_code ??
      raw?.generatedCode ??
      raw?.code,
    effectiveLens:
      nestedResult.effective_lens ??
      nestedResult.effectiveLens ??
      raw?.effective_lens ??
      raw?.effectiveLens,
    raw,
  }
}

// ─── Number & Value Formatters for Non-Technical Readability ───────────────────

function formatValue(val) {
  if (val === null || val === undefined || val === '') return 'Not available'
  if (typeof val === 'boolean') return val ? 'Yes' : 'No'
  if (typeof val === 'number') {
    if (Number.isInteger(val)) return val.toLocaleString()
    return val.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 2 })
  }
  if (typeof val === 'string') {
    const trimmed = val.trim()
    if (/^-?\d+\.\d{3,}$/.test(trimmed)) {
      const num = parseFloat(trimmed)
      if (num >= 0 && num <= 1 && !trimmed.includes('%')) {
        return `${(num * 100).toFixed(1)}%`
      }
      return num.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 2 })
    }
    return trimmed
  }
  return String(val)
}

function parsePlainLanguageSections(rawText) {
  if (!rawText || typeof rawText !== 'string') return null

  const lines = rawText.split('\n')
  const result = {
    mainAnswer: '',
    explanation: '',
    findings: [],
    nextAction: '',
    caveats: [],
  }

  let currentSection = 'main'
  let currentList = []

  const flushList = () => {
    if (currentList.length > 0) {
      if (currentSection === 'findings') result.findings.push(...currentList)
      else if (currentSection === 'caveats') result.caveats.push(...currentList)
      currentList = []
    }
  }

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) continue

    const lower = trimmed.toLowerCase()

    if (lower.includes('recommended approach:') || lower.startsWith('**headline:**') || lower.startsWith('### main answer')) {
      flushList()
      currentSection = 'main'
      const clean = trimmed.replace(/^(###\s*main answer|\*\*headline:\*\*|\*\*recommended approach:\*\*)\s*/i, '')
      if (clean) result.mainAnswer = (result.mainAnswer ? result.mainAnswer + ' ' : '') + clean
    } else if (lower.includes('why this fits:') || lower.includes('key findings:') || lower.includes('what this means:')) {
      flushList()
      currentSection = 'findings'
    } else if (lower.includes('before training:') || lower.includes('important caveats:') || lower.includes('caveat & context')) {
      flushList()
      currentSection = 'caveats'
    } else if (lower.includes('recommended next step:') || lower.includes('what you should do next:')) {
      flushList()
      currentSection = 'nextAction'
      const clean = trimmed.replace(/^(###\s*what you should do next|\*\*recommended next step:\*\*)\s*/i, '')
      if (clean) result.nextAction = clean
    } else if (trimmed.startsWith('•') || trimmed.startsWith('-') || trimmed.startsWith('*') || /^\d+\./.test(trimmed)) {
      const bulletContent = trimmed.replace(/^([\bullet\-\*]|\d+\.)\s*/, '')
      if (currentSection === 'findings') result.findings.push(bulletContent)
      else if (currentSection === 'caveats') result.caveats.push(bulletContent)
      else if (currentSection === 'nextAction' && !result.nextAction) result.nextAction = bulletContent
      else currentList.push(bulletContent)
    } else {
      if (currentSection === 'main') {
        result.mainAnswer = (result.mainAnswer ? result.mainAnswer + ' ' : '') + trimmed
      } else if (currentSection === 'nextAction') {
        result.nextAction = (result.nextAction ? result.nextAction + ' ' : '') + trimmed
      } else if (currentSection === 'findings') {
        result.findings.push(trimmed)
      } else {
        result.explanation = (result.explanation ? result.explanation + '\n' : '') + trimmed
      }
    }
  }
  flushList()

  return result
}

function ReportFormatter({ content, text }) {
  const input = content ?? text
  if (input === null || input === undefined) return null

  const rawText = typeof input === 'string' ? input : JSON.stringify(input, null, 2)
  if (!rawText.trim()) return null

  const parsed = parsePlainLanguageSections(rawText)
  const cleanText = (str) => String(str || '').replace(/\*\*/g, '').trim()

  return (
    <div className="report-formatted-container">
      {/* 1. Main Answer */}
      <div className="report-headline-block">
        <h3 className="report-headline-text">
          {cleanText(parsed.mainAnswer || rawText.split('\n')[0])}
        </h3>
      </div>

      {/* 2. What This Means / Explanation */}
      {parsed.explanation && (
        <div className="report-explanation-block">
          <p className="report-explanation-text">{cleanText(parsed.explanation)}</p>
        </div>
      )}

      {/* 3. Key Findings */}
      {parsed.findings.length > 0 && (
        <div className="report-section-block">
          <div className="report-section-title">Key Findings</div>
          <ul className="report-findings-list">
            {parsed.findings.slice(0, 5).map((finding, idx) => (
              <li key={idx} className="finding-item">
                <span className="finding-bullet">•</span>
                <span className="finding-text">{cleanText(finding)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 4. Caveats */}
      {parsed.caveats.length > 0 && (
        <div className="report-section-block caveats">
          <div className="report-section-title">Important Caveats</div>
          <ul className="report-caveats-list">
            {parsed.caveats.map((c, idx) => (
              <li key={idx}>{cleanText(c)}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 5. Recommended Next Step */}
      {parsed.nextAction && (
        <div className="report-next-action-box">
          <div className="next-action-head">🎯 Recommended Next Step</div>
          <p className="next-action-body">{cleanText(parsed.nextAction)}</p>
        </div>
      )}
    </div>
  )
}

function AnalysisProgressState({ status, onStop, msgId }) {
  let title = "Analysis in progress"
  let description = "We are preparing your answer. Results will appear here as soon as they are available."

  if (status === 'planning') {
    title = "Understanding your question"
    description = "Understanding your question and selecting the best analysis approach..."
  } else if (status === 'validating') {
    title = "Checking accuracy"
    description = "Checking the answer against dataset statistical bounds for accuracy..."
  }

  return (
    <div className="analysis-progress-card" style={{ padding: '16px', background: '#F8FAFC', borderRadius: '10px', border: '1px solid #E2E8F0', margin: '8px 0' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="running-pulse-dot" style={{ width: '8px', height: '8px', background: 'var(--primary, #4F46E5)', borderRadius: '50%' }} />
          <strong style={{ color: '#0F172A', fontSize: '14px', fontWeight: 600 }}>{title}</strong>
        </div>
        {onStop && (
          <button
            onClick={() => onStop(msgId)}
            style={{ fontSize: '11px', padding: '3px 8px', borderRadius: '4px', border: '1px solid #CBD5E1', background: '#FFFFFF', cursor: 'pointer', color: '#475569' }}
          >
            Stop
          </button>
        )}
      </div>
      <p style={{ margin: 0, fontSize: '13px', color: '#475569', lineHeight: 1.5 }}>{description}</p>
    </div>
  )
}

function InlineProgressMessage({ message }) {
  return (
    <div className="inline-progress-msg" style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px', background: '#F1F5F9', borderRadius: '6px', fontSize: '12px', color: '#334155', marginTop: '10px' }}>
      <span className="running-pulse-dot" style={{ width: '6px', height: '6px', background: 'var(--primary, #4F46E5)', borderRadius: '50%' }} />
      <span>{message}</span>
    </div>
  )
}

function EmptyFinalAnswerError() {
  return (
    <div className="analysis-error-state warning" style={{ padding: '14px', background: '#FFFBEB', borderRadius: '8px', border: '1px solid #FDE68A', color: '#92400E' }}>
      <strong style={{ fontSize: '14px', display: 'block', marginBottom: '4px' }}>No answer was returned</strong>
      <p style={{ margin: 0, fontSize: '12px' }}>The analysis completed, but its result could not be displayed.</p>
    </div>
  )
}

function StructuredAnswerSection({ answer }) {
  if (!answer || typeof answer !== 'object') return null
  const { title, summary, explanation, findings = [], caveats = [], next_action } = answer

  return (
    <div className="report-formatted-container" style={{ padding: '4px 0' }}>
      {title && <div className="report-section-title" style={{ fontSize: '13px', color: 'var(--primary, #4F46E5)', fontWeight: 600, marginBottom: '6px' }}>{title}</div>}
      {summary && (
        <div className="report-headline-block" style={{ marginBottom: '8px' }}>
          <h3 className="report-headline-text" style={{ color: '#0F172A', fontWeight: 500, fontSize: '16px', lineHeight: 1.6, margin: 0 }}>
            {summary}
          </h3>
        </div>
      )}
      {explanation && (
        <div className="report-explanation-block" style={{ marginTop: '8px', marginBottom: '8px' }}>
          <p className="report-explanation-text" style={{ color: '#334155', fontSize: '14px', lineHeight: 1.6, margin: 0 }}>{explanation}</p>
        </div>
      )}
      {Array.isArray(findings) && findings.length > 0 && (
        <div className="report-section-block" style={{ marginTop: '10px' }}>
          <div className="report-section-title" style={{ fontSize: '13px', fontWeight: 600, color: '#1E293B', marginBottom: '4px' }}>Key Findings</div>
          <ul className="report-findings-list" style={{ paddingLeft: '16px', margin: 0 }}>
            {findings.map((f, idx) => (
              <li key={idx} className="finding-item" style={{ marginBottom: '4px', fontSize: '14px', color: '#334155' }}>
                {typeof f === 'object' && f !== null ? <span><strong>{f.label}:</strong> {f.detail}</span> : String(f)}
              </li>
            ))}
          </ul>
        </div>
      )}
      {Array.isArray(caveats) && caveats.length > 0 && (
        <div className="report-section-block caveats" style={{ marginTop: '10px' }}>
          <div className="report-section-title" style={{ fontSize: '13px', fontWeight: 600, color: '#B45309', marginBottom: '4px' }}>Important Caveats</div>
          <ul className="report-caveats-list" style={{ paddingLeft: '16px', margin: 0 }}>
            {caveats.map((c, idx) => (
              <li key={idx} style={{ marginBottom: '4px', fontSize: '13px', color: '#92400E' }}>{String(c)}</li>
            ))}
          </ul>
        </div>
      )}
      {next_action && (
        <div className="report-next-action-box" style={{ marginTop: '12px', padding: '10px 14px', background: '#F0FDF4', border: '1px solid #BBF7D0', borderRadius: '8px' }}>
          <div className="next-action-head" style={{ fontWeight: 600, fontSize: '13px', color: '#15803D', marginBottom: '2px' }}>🎯 Recommended Next Step</div>
          <p className="next-action-body" style={{ margin: 0, fontSize: '13px', color: '#166534' }}>{next_action}</p>
        </div>
      )}
    </div>
  )
}

function AnalysisAnswer({ msg, isError }) {
  const errorMessage = toDisplayText(msg?.error?.message || msg?.error)
  const summary = toDisplayText(msg?.answer?.summary)
  const explanation = toDisplayText(msg?.answer?.explanation)
  const legacyText = toDisplayText(msg?.answerText || msg?.report || msg?.result)
  const evidenceFacts = Array.isArray(msg?.evidence?.facts) ? msg.evidence.facts : []
  const hasEvidence = Boolean(msg?.evidence?.available) && evidenceFacts.length > 0
  const evidenceBlock = hasEvidence ? (
    <div className="analysis-evidence" style={{ padding: '16px', background: '#F8FAFC', borderRadius: '8px', border: '1px solid #E2E8F0' }}>
      <h4 style={{ margin: '0 0 12px 0', fontSize: '14px', color: '#334155', fontWeight: 600 }}>Verified Dataset Evidence</h4>
      <ul style={{ margin: 0, paddingLeft: '20px', color: '#475569', fontSize: '14px', lineHeight: '1.5' }}>
        {evidenceFacts.map((fact, i) => {
          const label = fact && typeof fact === 'object' ? fact.label : ''
          const value = fact && typeof fact === 'object' ? fact.value : fact
          return <li key={i}>{label ? `${label}: ${toDisplayText(value)}` : toDisplayText(value)}</li>
        })}
      </ul>
    </div>
  ) : null
  const generationWarning = msg?.warning?.message || msg?.rawResponse?.warning?.message || msg?.debugPayload?.warning?.message

  if (msg?.status === 'failed' || isError) {
    return (
      <div className="analysis-error-state" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {evidenceBlock}
        <div style={{ padding: '12px', background: '#FEF2F2', borderRadius: '8px', border: '1px solid #FCA5A5' }} role="alert">
          <strong style={{ color: 'var(--accent-red, #EF4444)', display: 'block', marginBottom: '4px' }}>
            {hasEvidence ? 'Answer Generation Failed' : 'Analysis failed'}
          </strong>
          <p style={{ color: 'var(--accent-red, #EF4444)', margin: 0, fontSize: hasEvidence ? '13px' : 'inherit' }}>
            {errorMessage || legacyText || 'The analysis could not be completed.'}
          </p>
          {import.meta.env.DEV && (msg.rawResponse || msg.debugPayload) && (
            <details className="debug-payload-details" style={{ marginTop: '8px', fontSize: '11px' }}>
              <summary style={{ cursor: 'pointer', color: 'var(--text-muted)' }}>Raw API response debug payload</summary>
              <pre style={{ background: '#F8FAFC', padding: '8px', borderRadius: '6px', overflow: 'auto', maxHeight: '200px', marginTop: '4px' }}>
                {JSON.stringify(msg.rawResponse || msg.debugPayload, null, 2)}
              </pre>
            </details>
          )}
        </div>
      </div>
    )
  }

  if (msg?.status === 'cancelled') {
    return (
      <div className="analysis-cancelled" style={{ padding: '12px', background: '#F3F4F6', borderRadius: '8px', border: '1px solid #E5E7EB' }} role="status">
        <p style={{ margin: 0, color: '#4B5563' }}>{errorMessage || legacyText || 'Analysis stopped.'}</p>
      </div>
    )
  }

  const ansObj = msg.answer && typeof msg.answer === 'object' ? msg.answer : null
  if (ansObj && (ansObj.summary || ansObj.title || ansObj.explanation)) {
    return (
      <>
        {evidenceBlock}
        <StructuredAnswerSection answer={ansObj} />
      </>
    )
  }

  const rowData = msg.answerData || msg.row_data
  if (rowData && (rowData.fields || rowData.values)) {
    return (
      <>
        {evidenceBlock}
        <RowTableSection rowData={rowData} />
      </>
    )
  }

  if (summary || explanation) {
    return (
      <div className="analysis-answer">
        {evidenceBlock}
        {summary && <p>{summary}</p>}
        {explanation && <p>{explanation}</p>}
      </div>
    )
  }

  if (typeof msg.answerText === 'string' && msg.answerText.trim()) {
    return (
      <>
        {evidenceBlock}
        <ReportFormatter content={msg.answerText} />
      </>
    )
  }

  if (typeof msg.report === 'string' && msg.report.trim()) {
    return (
      <>
        {evidenceBlock}
        <ReportFormatter content={msg.report} />
      </>
    )
  }

  if (typeof msg.result === 'string' && msg.result.trim()) {
    return (
      <>
        {evidenceBlock}
        <ReportFormatter content={msg.result} />
      </>
    )
  }

  if (msg.answerData !== undefined && msg.answerData !== null) {
    return (
      <>
        {evidenceBlock}
        <div className="generic-structured-result" style={{ background: '#F8FAFC', padding: '12px', borderRadius: '8px' }}>
          <pre style={{ margin: 0, fontSize: '12px', fontFamily: 'monospace', color: '#0F172A' }}>
            {typeof msg.answerData === 'object' ? JSON.stringify(msg.answerData, null, 2) : String(msg.answerData)}
          </pre>
        </div>
      </>
    )
  }

  if (evidenceBlock || generationWarning) {
    return (
      <div className="analysis-partial-state" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {evidenceBlock}
        {generationWarning && (
          <div style={{ padding: '12px', background: '#FFFBEB', borderRadius: '8px', border: '1px solid #FDE68A', color: '#92400E' }} role="status">
            {generationWarning}
          </div>
        )}
      </div>
    )
  }

  return null
}

function ChatMessage({ msg, onAsk, onStop, onRetryExplanation }) {
  const [showCode, setShowCode] = useState(false)
  const status = msg.status || 'running'
  const isDone = status === 'complete' || status === 'failed' || status === 'cancelled' || (status === 'partial' && !msg.streaming)
  const isError = status === 'failed' || msg.steps.some((s) => s.step === 'error' || s.type === 'analysis_failed')
  const isStreaming = msg.streaming && !isDone && !isError

  const cat = catByKey(msg.category)
  const hasExplain = msg.shap_chart || msg.perm_chart || msg.pdp_chart
  const latestMeta = [...msg.steps].reverse().find((s) => s.meta)?.meta
  const route = latestMeta?.route || msg.plan?.query_type

  const lensRes = msg.lens_resolution || latestMeta?.lens_resolution || msg.steps.find(s => s.lens_resolution)?.lens_resolution
  const effectiveCategory = lensRes?.effective_lens || msg.category
  const effectiveCatObj = catByKey(effectiveCategory)
  const wasAutoSwitched = lensRes?.was_auto_switched

  const hasRenderableAnswer = Boolean(msg.answerText?.trim()) ||
    msg.answerData !== undefined ||
    Boolean(msg.result?.trim()) ||
    Boolean(msg.report?.trim()) ||
    Boolean(msg.row_data)

  return (
    <div className="chat-msg">
      <div className="bubble-user"><p>{msg.question}</p></div>

      <div
        className={`bubble-agent ${isError ? 'is-error' : isDone ? 'is-done' : 'is-loading'}`}
        aria-live="polite"
        aria-busy={isStreaming}
      >
        <div className="agent-head">
          <div className="agent-title-group">
            <Sparkles width={14} height={14} />
            <span>Multi-Agent Analyst</span>
          </div>
          <span className="agent-lens" title={wasAutoSwitched ? `Originally selected: ${cat.label}` : undefined}>
            <effectiveCatObj.icon width={11} height={11} /> {effectiveCatObj.label}
            {wasAutoSwitched && <em className="auto-selected-tag"> · Auto-selected</em>}
          </span>

          {!isDone && (
            <span className="status-badge-progressive neutral">
              <span className="running-pulse-dot" />
              {status === 'planning' ? 'Planning' : status === 'validating' ? 'Checking accuracy' : status === 'partial' ? 'Initial answer' : 'Analyzing'}
            </span>
          )}

          {isDone && !isError && (
            <AnswerTrustBadge route={route} validation={msg.validation} critique={msg.critique} />
          )}

          {latestMeta?.request_id ? (
            <span className="trace-badge" title={`Request ${latestMeta.request_id}`}>
              #{latestMeta.request_id.slice(0, 8)}
            </span>
          ) : (
            <span className="security-badge" title="AST-validated · sandboxed execution">
              <Lock width={12} height={12} />
            </span>
          )}
        </div>

        <div className="card-divider" />

        {/* ── STATE-BASED ANSWER RENDERER ── */}
        {(status === 'queued' || status === 'planning' || status === 'running') && !hasRenderableAnswer && (
          <AnalysisProgressState status={status} onStop={onStop} msgId={msg.id} />
        )}

        {(status === 'queued' || status === 'planning' || status === 'running') && hasRenderableAnswer && (
          <>
            <AnalysisAnswer msg={msg} />
            <InlineProgressMessage message="Additional analysis is still running." />
          </>
        )}

        {status === 'partial' && (
          <>
            <AnalysisAnswer msg={msg} />
            <InlineProgressMessage message={msg.streaming ? 'Initial answer available. Additional checks are still running.' : 'Written explanation temporarily unavailable.'} />
            {!msg.streaming && msg.generation?.succeeded === false && (
              <button type="button" className="ghost-btn" onClick={() => onRetryExplanation && onRetryExplanation(msg)}>
                Retry explanation
              </button>
            )}
          </>
        )}

        {status === 'validating' && (
          <>
            <AnalysisAnswer msg={msg} />
            <InlineProgressMessage message="Checking the answer for accuracy." />
          </>
        )}

        {status === 'failed' && <AnalysisAnswer msg={msg} isError={true} />}

        {status === 'complete' && hasRenderableAnswer && <AnalysisAnswer msg={msg} />}

        {status === 'complete' && !hasRenderableAnswer && <EmptyFinalAnswerError />}

        {/* ── LIVE ACTIVITY LOG / CHECKLIST WITH STOP BUTTON WHEN PROCESSING ── */}
        <LiveExecutionLog
          steps={msg.steps}
          isDone={isDone}
          latestMeta={latestMeta}
          lensRes={lensRes}
          isStreaming={isStreaming}
          onStop={() => onStop && onStop(msg.id)}
        />

        {/* Strategy Row */}
        {msg.plan?.strategy && (
          <div className="strategy-row">
            <Layers width={13} height={13} style={{ color: 'var(--primary)', flexShrink: 0 }} />
            <span><strong>Strategy:</strong> {msg.plan.strategy}</span>
          </div>
        )}

        {/* Visualization */}
        {hasExplain ? (
          <ExplainPanel msg={msg} />
        ) : msg.chart_json ? (
          <PlotlyChart json={msg.chart_json} />
        ) : (
          msg.chart && <img className="chart-img" src={`data:image/png;base64,${msg.chart}`} alt="Generated chart" />
        )}

        {/* Code Accordion */}
        {msg.code && (
          <div className="code-accordion accordion-row">
            <div
              className="accordion-summary-clean"
              onClick={() => setShowCode((v) => !v)}
              role="button"
              tabIndex={0}
              aria-expanded={showCode}
              onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setShowCode((v) => !v)}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Code width={14} height={14} style={{ color: 'var(--primary)' }} />
                <span>Generated Code ({msg.code_lang === 'sql' ? 'SQL' : 'Python'})</span>
              </div>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{showCode ? 'Hide ▲' : 'Show ▲'}</span>
            </div>
            {showCode && (
              <div className="code-block-clean">
                <pre>{msg.code}</pre>
              </div>
            )}
          </div>
        )}

        {/* Critique Note & Validation Accordion */}
        {msg.critique && isDone && <CritiqueBadge critique={msg.critique} />}

        {msg.validation && isDone && !isError && <ValidationPanel validation={msg.validation} />}

        {/* Subtle Lens Note at Bottom */}
        {wasAutoSwitched && isDone && (
          <div className="lens-note-compact">
            <Sparkles width={13} height={13} style={{ color: 'var(--primary)', flexShrink: 0 }} />
            <span>
              <strong>Lens note:</strong> This dataset appears to contain {effectiveCatObj.label.toLowerCase()} data. The analysis was completed using the {effectiveCatObj.label} lens instead of the selected {cat.label} lens. For future questions about this dataset, choose the {effectiveCatObj.label} or General lens.
            </span>
          </div>
        )}

        {/* Follow-up Question Chips */}
        {msg.followups?.length > 0 && isDone && !isError && (
          <div className="followup-row">
            {msg.followups.map((text) => (
              <button key={text} className="followup-chip" onClick={() => onAsk(text)}>
                <Sparkles width={12} height={12} /> {text}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function ChatArea({ upload, category, messages, onAsk, onStory, onInvestigate, onCleanExport, onExportContract, onExportDashboard, cleaningBusy, loading, question, setQuestion, inputRef, onStop, onRetryExplanation }) {
  const cat = catByKey(category)
  const bottomRef = useRef()
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  return (
    <main className="chat-area">
      {messages.length === 0 ? (
        (upload.overview && upload.overview.length > 0) ? (
          <div className="overview-scroll">
            <div className="overview-header">
              <div className="empty-icon sm"><cat.icon width={22} height={22} /></div>
              <div>
                <h2>Instant overview of {upload.filename}</h2>
                <p>Auto-generated the moment your data loaded · ask a question below for a deeper dive.</p>
              </div>
            </div>

            {upload.proactive_insights?.length > 0 && (
              <div className="proactive-grid">
                {upload.proactive_insights.map((insight, i) => (
                  <article key={`${insight.title}-${i}`} className={`proactive-card ${insight.kind || 'profile'}`}>
                    <div className="pi-top">
                      <span className="pi-kind">{insight.kind || 'insight'}</span>
                      <span className="pi-confidence">{insight.confidence || 'High'} confidence</span>
                    </div>
                    <h3>{insight.title}</h3>
                    <p>{insight.finding}</p>
                    {insight.validation && <div className="pi-validation">{insight.validation}</div>}
                  </article>
                ))}
              </div>
            )}

            {upload.decision_brief && (
              <section className="overview-brief">
                <div className="overview-brief-score">
                  <span>{upload.decision_brief.readiness_score}</span>
                  <small>readiness</small>
                </div>
                <div className="overview-brief-body">
                  <h3>Decision readiness: {(upload.decision_brief.readiness_label || '').replaceAll('_', ' ')}</h3>
                  <p>{upload.decision_brief.summary}</p>
                  <div className="overview-brief-actions">
                    {upload.decision_brief.priority_questions?.slice(0, 3).map((q) => (
                      <button key={q} disabled={loading} onClick={() => onAsk(q)}>
                        <Sparkles width={12} height={12} /> {q}
                      </button>
                    ))}
                    {upload.cleaning_plan?.default_actions?.length > 0 && (
                      <button disabled={cleaningBusy} onClick={onCleanExport}>
                        <Check width={12} height={12} /> {cleaningBusy ? 'Preparing cleaned CSV' : 'Download cleaned CSV'}
                      </button>
                    )}
                    {upload.data_contract && (
                      <button onClick={onExportContract}>
                        <Code width={12} height={12} /> Export data contract
                      </button>
                    )}
                    {upload.dashboard_spec && (
                      <button onClick={onExportDashboard}>
                        <ChartUp width={12} height={12} /> Export dashboard JSON
                      </button>
                    )}
                  </div>
                </div>
              </section>
            )}

            {(upload.decision_actions || upload.decision_brief?.decision_actions)?.length > 0 && (
              <section className="overview-actions">
                <div className="overview-actions-head">
                  <Sparkles width={15} height={15} />
                  <h3>What to do next</h3>
                </div>
                <div className="overview-action-grid">
                  {(upload.decision_actions || upload.decision_brief.decision_actions).slice(0, 3).map((action, i) => (
                    <article key={`${action.title}-${i}`} className={`overview-action ${action.priority}`}>
                      <div className="oa-top">
                        <span>{action.priority}</span>
                        <em>{Math.round((action.confidence || 0) * 100)}% confidence</em>
                      </div>
                      <h4>{action.title}</h4>
                      <p>{action.implication}</p>
                      <strong>{action.estimated_impact}</strong>
                      {action.suggested_question && (
                        <button disabled={loading} onClick={() => onInvestigate(action.suggested_question)}>
                          Investigate this
                        </button>
                      )}
                    </article>
                  ))}
                </div>
              </section>
            )}

            <div className="overview-grid">
              {upload.overview.map((oc) => (
                <figure key={oc.title} className="overview-card">
                  <img src={`data:image/png;base64,${oc.chart}`} alt={oc.title} />
                  <figcaption>{oc.title}</figcaption>
                </figure>
              ))}
            </div>

            <div className="overview-examples">
              <div className="oe-label">Try a {cat.label} question</div>
              <div className="oe-chips">
                <button className="oe-chip story" disabled={loading} onClick={onStory}>
                  <Sparkles width={13} height={13} /> Generate dataset story
                </button>
                {cat.examples.map((text) => (
                  <button key={text} className="oe-chip" disabled={loading} onClick={() => onAsk(text)}>
                    <Sparkles width={13} height={13} /> {text}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="chat-empty">
            <div className="empty-icon"><cat.icon width={30} height={30} /></div>
            <h2>{cat.label} analysis with natural language</h2>
            <p>{cat.blurb} — ask questions, create charts, and get a domain-expert read on your data.</p>
            <div className="example-grid">
              {cat.examples.map((text) => (
                <button key={text} className="example-card" disabled={loading} onClick={() => onAsk(text)}>
                  <span className="ex-icon"><Sparkles width={15} height={15} /></span>
                  <span>{text}</span>
                </button>
              ))}
            </div>
          </div>
        )
      ) : (
        <div className="message-list">
          {messages.map((m) => <ChatMessage key={m.id} msg={m} onAsk={onAsk} onStop={onStop} onRetryExplanation={onRetryExplanation} />)}
          <div ref={bottomRef} />
        </div>
      )}

      <div className="composer">
        <div className="composer-inner">
          <button className="composer-attach" title="Attach (coming soon)" tabIndex={-1}>
            <Paperclip width={18} height={18} />
          </button>
          <input
            ref={inputRef}
            className="composer-input"
            placeholder={`Ask a ${cat.label.toLowerCase()} question about ${upload.filename}…`}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && onAsk()}
            disabled={loading}
            autoFocus
          />
          <button className="composer-send" onClick={() => onAsk()} disabled={loading || !question.trim()}>
            {loading ? <span className="spinner" /> : <Send width={17} height={17} />}
          </button>
        </div>
        <div className="composer-hint">Analyzing through the <strong>{cat.label}</strong> lens · generated code shown for every answer</div>
      </div>
    </main>
  )
}

// ─── App ───────────────────────────────────────────────────────────────────────

function App() {
  const [upload, setUpload] = useState(null)
  const [datasets, setDatasets] = useState([])
  const [uploading, setUploading] = useState(false)
  const [category, setCategory] = useState('general')
  const [messages, setMessages] = useState([])
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [leftPanelCollapsed, setLeftPanelCollapsed] = useState(false)
  const [rightPanelCollapsed, setRightPanelCollapsed] = useState(false)
  const requestTimeoutsRef = useRef(new Map())
  const isAnalyzing = useMemo(() => {
    return loading || (messages || []).some((m) => m.status === 'queued' || m.status === 'running' || (m.status === 'partial' && m.streaming))
  }, [loading, messages])
  const [showPaste, setShowPaste] = useState(false)
  const [showUrlImport, setShowUrlImport] = useState(false)
  const [showJoin, setShowJoin] = useState(false)
  const [showCompare, setShowCompare] = useState(false)
  const [showBenchmark, setShowBenchmark] = useState(false)
  const [showDataViewer, setShowDataViewer] = useState(false)
  const [modelInfo, setModelInfo] = useState(null)
  const [docs, setDocs] = useState([])
  const [cleaningBusy, setCleaningBusy] = useState(false)
  const inputRef = useRef()

  const [sidebarWidth, setSidebarWidth] = useState(320)
  const [insightsWidth, setInsightsWidth] = useState(400)
  const isDraggingSidebar = useRef(false)
  const isDraggingInsights = useRef(false)

  const handleSidebarMouseDown = useCallback((e) => {
    e.preventDefault()
    isDraggingSidebar.current = true
    const startX = e.clientX
    const startWidth = sidebarWidth

    const handleMouseMove = (moveEvent) => {
      if (!isDraggingSidebar.current) return
      const delta = moveEvent.clientX - startX
      const newWidth = Math.max(280, Math.min(600, startWidth + delta))
      setSidebarWidth(newWidth)
    }

    const handleMouseUp = () => {
      isDraggingSidebar.current = false
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
      document.body.classList.remove('is-resizing')
    }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    document.body.classList.add('is-resizing')
  }, [sidebarWidth])

  const handleInsightsMouseDown = useCallback((e) => {
    e.preventDefault()
    isDraggingInsights.current = true
    const startX = e.clientX
    const startWidth = insightsWidth

    const handleMouseMove = (moveEvent) => {
      if (!isDraggingInsights.current) return
      const delta = startX - moveEvent.clientX
      // Size in Picture 2 (380px+) is the minimum safe width; panel is expandable only and NOT shrinkable below this bound!
      const newWidth = Math.max(380, Math.min(750, startWidth + delta))
      setInsightsWidth(newWidth)
    }

    const handleMouseUp = () => {
      isDraggingInsights.current = false
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
      document.body.classList.remove('is-resizing')
    }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    document.body.classList.add('is-resizing')
  }, [insightsWidth])

  const handleUpload = useCallback((data) => {
    const item = { ...data, uploadedAt: data.uploadedAt || new Date() }
    setUpload(item)
    setDatasets((prev) => {
      const idx = prev.findIndex(d => d.session_id === item.session_id)
      if (idx >= 0) {
        const next = [...prev]; next[idx] = item; return next
      }
      return [...prev, item]
    })
  }, [])

  const handleUrlImportSubmit = useCallback(async (urlStr) => {
    if (!urlStr.trim()) return
    setUploading(true)
    try {
      const res = await fetch(`${API}/import_url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: urlStr.trim(), filename: 'imported_dataset.csv' }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Import failed')
      setShowUrlImport(false)
      setMessages([])
      setModelInfo(null)
      setDocs([])
      handleUpload(data)
    } catch (e) {
      alert(e.message)
    } finally {
      setUploading(false)
    }
  }, [handleUpload])

  const handlePasteSubmit = useCallback(async (text, hasHeader) => {
    if (!text.trim()) return
    setUploading(true)
    try {
      const res = await fetch(`${API}/upload_text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Session-Token': upload?.token || '' },
        body: JSON.stringify({ text, has_header: hasHeader, filename: 'pasted_data.csv' }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Could not parse the data')
      setShowPaste(false)
      setMessages([])
      setModelInfo(null)
      setDocs([])
      handleUpload(data)
    } catch (e) {
      alert(e.message)
    } finally {
      setUploading(false)
    }
  }, [])

  // Per-request abort controller map: requestId → {controller, timeoutId}
  // This prevents a new request from cancelling an older in-flight request.
  const requestManagerRef = useRef(new Map())

  const handleStop = useCallback((msgId) => {
    const entry = requestManagerRef.current.get(msgId)
    if (entry) {
      clearTimeout(entry.timeoutId)
      entry.controller.abort('user_cancelled')
      requestManagerRef.current.delete(msgId)
    }
    fetch(`${API}/cancel/${msgId}`, { method: 'POST' }).catch(() => {})
    setMessages((prev) => prev.map((m) => m.id === msgId ? {
      ...m,
      streaming: false,
      status: 'cancelled',
      steps: [...m.steps, { step: 'stopped', message: 'Stopped by user — partial results preserved' }]
    } : m))
    setLoading(false)
  }, [])

  const handleAnalysisStreamEvent = useCallback((rawEvent, clientRequestId) => {
    const eventClass = classifyStreamEvent(rawEvent)
    const normalized = normalizeQueryResponse(rawEvent, clientRequestId)
    const currentReqId = String(clientRequestId).toLowerCase()

    console.debug('[query-stream] event classification', {
      eventType: rawEvent?.type || rawEvent?.step,
      eventClass,
      clientRequestId,
      rawEvent,
    })

    setMessages((prev) => prev.map((m) => {
      if (String(m.id).toLowerCase() !== currentReqId) return m

      const combinedSteps = [...(m.steps || []), rawEvent]
      const newExecutionSteps = normalized.executionSteps.length > 0
        ? normalized.executionSteps
        : (m.executionSteps || combinedSteps.map(normalizeExecutionStep))

      if (eventClass === 'progress') {
        return {
          ...m,
          status: 'running',
          streaming: true,
          steps: combinedSteps,
          executionSteps: newExecutionSteps,
          plan: rawEvent.plan ?? m.plan,
          code: rawEvent.code ?? m.code,
        }
      }

      if (eventClass === 'partial-result') {
        return {
          ...m,
          status: 'partial',
          streaming: true,
          steps: combinedSteps,
          executionSteps: newExecutionSteps,
          answerText: normalized.answerText ?? m.answerText,
          answerType: normalized.answerType ?? m.answerType,
          answerData: normalized.answerData ?? m.answerData,
          result: normalized.answerText ?? m.result,
          report: normalized.answerText ?? m.report,
          row_data: normalized.answerData ?? m.row_data,
          code: normalized.generatedCode ?? rawEvent.code ?? m.code,
          code_lang: rawEvent.code_lang ?? m.code_lang,
          chart: rawEvent.chart ?? m.chart,
          chart_json: rawEvent.chart_json ?? m.chart_json,
        }
      }

      if (eventClass === 'terminal-partial') {
        return {
          ...m,
          status: 'partial',
          streaming: false,
          steps: combinedSteps,
          executionSteps: newExecutionSteps,
          answerText: normalized.answerText?.trim() ? normalized.answerText : m.answerText,
          answerType: normalized.answerType ?? m.answerType,
          answerData: normalized.answerData ?? rawEvent.evidence?.table ?? m.answerData,
          result: normalized.answerText?.trim() ? normalized.answerText : m.result,
          report: normalized.answerText?.trim() ? normalized.answerText : m.report,
          row_data: normalized.answerData ?? rawEvent.evidence?.table ?? m.row_data,
          code: normalized.generatedCode ?? rawEvent.code ?? m.code,
          code_lang: rawEvent.code_lang ?? m.code_lang,
          chart: rawEvent.chart ?? m.chart,
          chart_json: rawEvent.chart_json ?? m.chart_json,
          critique: rawEvent.critique ?? m.critique,
          validation: rawEvent.validation ?? m.validation,
          plan: rawEvent.plan ?? m.plan,
          followups: rawEvent.followups ?? m.followups,
          evidence: rawEvent.evidence ?? m.evidence,
          warning: rawEvent.warning ?? m.warning,
          generation: rawEvent.generation ?? m.generation,
          error: null,
          debugPayload: import.meta.env.DEV ? rawEvent : undefined,
        }
      }

      if (eventClass === 'terminal-failure') {
        return {
          ...m,
          status: 'failed',
          streaming: false,
          error: rawEvent.error || rawEvent.message || 'Analysis failed',
          debugPayload: import.meta.env.DEV ? rawEvent : undefined,
          steps: combinedSteps,
          executionSteps: newExecutionSteps,
          evidence: rawEvent.evidence ?? m.evidence,
        }
      }

      if (eventClass === 'terminal-success') {
        const hasAnswer = Boolean(normalized.answerText?.trim()) || normalized.answerData !== undefined || Boolean(rawEvent.result) || Boolean(rawEvent.report) || Boolean(rawEvent.row_data)

        if (!hasAnswer) {
          console.error('[query-stream] terminal-success has no renderable answer', { normalized, rawEvent })
          return {
            ...m,
            status: 'failed',
            streaming: false,
            error: 'The server completed the analysis but returned no displayable answer.',
            debugPayload: import.meta.env.DEV ? rawEvent : undefined,
            steps: combinedSteps,
            executionSteps: newExecutionSteps,
          }
        }

        return {
          ...m,
          status: 'complete',
          streaming: false,
          steps: combinedSteps,
          executionSteps: newExecutionSteps,
          answerText: normalized.answerText ?? m.answerText,
          answerType: normalized.answerType ?? m.answerType,
          answerData: normalized.answerData ?? m.answerData,
          code: normalized.generatedCode ?? rawEvent.code ?? m.code,
          code_lang: rawEvent.code_lang ?? m.code_lang,
          result: normalized.answerText ?? rawEvent.result ?? m.result,
          chart: rawEvent.chart ?? m.chart,
          chart_json: rawEvent.chart_json ?? m.chart_json,
          report: normalized.answerText ?? rawEvent.report ?? m.report,
          critique: rawEvent.critique ?? m.critique,
          validation: rawEvent.validation ?? m.validation,
          plan: rawEvent.plan ?? m.plan,
          followups: rawEvent.followups ?? m.followups,
          row_data: normalized.answerData ?? rawEvent.row_data ?? m.row_data,
          evidence: rawEvent.evidence ?? m.evidence,
          warning: rawEvent.warning ?? m.warning,
          generation: rawEvent.generation ?? m.generation,
          error: null,
          debugPayload: import.meta.env.DEV ? rawEvent : undefined,
        }
      }

      return m
    }))
  }, [])

  // Shared SSE consumer used by streaming analysis endpoints.
  const streamInto = useCallback(async (url, body, label) => {
    if (!upload || loading) return
    setLoading(true)
    const clientRequestId = typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID()
      : `req-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`

    const controller = new AbortController()
    const timeoutId = window.setTimeout(() => {
      console.warn('[query] request timed out after 120s', { clientRequestId })
      controller.abort('timeout')
    }, 120000)

    // Register this request in the per-request manager map
    requestManagerRef.current.set(clientRequestId, { controller, timeoutId })

    console.debug('[query] submitting request', {
      clientRequestId,
      question: label,
      category,
      url,
    })

    setMessages((prev) => [...prev, {
      id: clientRequestId,
      request_id: clientRequestId,
      question: label,
      category,
      status: 'running',
      streaming: true,
      steps: [],
      code: null,
      code_lang: null,
      result: null,
      chart: null,
      chart_json: null,
      report: null,
      critique: null,
      validation: null,
      plan: null,
      followups: [],
      shap_chart: null,
      perm_chart: null,
      pdp_chart: null,
      row_data: null,
      error: null,
    }])

    try {
      const requestPayload = { ...body, request_id: clientRequestId }
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Session-Token': upload?.token || '' },
        body: JSON.stringify(requestPayload),
        signal: controller.signal,
      })

      const contentType = res.headers.get('content-type') || ''
      console.debug('[query] response received', {
        clientRequestId,
        status: res.status,
        contentType,
      })

      if (!res.ok) {
        const errText = await res.text()
        let detail = `Query failed with status ${res.status}`
        let parsed = null
        try {
          parsed = JSON.parse(errText)
          detail = parsed.detail || detail
        } catch (_) {}

        if (res.status === 404 || parsed?.error?.code === 'session_not_found' || String(detail).includes('Session not found')) {
          setUpload(null)
          setMessages([])
          alert('The backend session expired or restarted. Please upload the dataset again.')
          return
        }

        throw new Error(detail)
      }

      if (contentType.includes('application/json')) {
        const raw = await res.json()
        handleAnalysisStreamEvent(raw, clientRequestId)
        return
      }

      if (!res.body) {
        throw new Error('Streaming response has no body.')
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let terminalReceived = false

      const parseSseBlock = (block) => {
        const lines = block.split(/\r?\n/)
        const dataLine = lines.find((l) => l.startsWith('data: '))
        if (!dataLine) return null
        try {
          return JSON.parse(dataLine.slice(6))
        } catch (_) {
          return null
        }
      }

      try {
        while (true) {
          const { value, done } = await reader.read()
          buffer += decoder.decode(value, { stream: !done })

          const blocks = buffer.split(/\r?\n\r?\n/)
          buffer = blocks.pop() ?? ''

          for (const block of blocks) {
            const event = parseSseBlock(block)
            if (!event) continue

            const eventReqId = String(event.request_id ?? event.requestId ?? '').toLowerCase()
            if (eventReqId && eventReqId !== String(clientRequestId).toLowerCase()) {
              continue
            }

            handleAnalysisStreamEvent(event, clientRequestId)
            const classification = classifyStreamEvent(event)
            if (classification === 'terminal-success' || classification === 'terminal-failure' || classification === 'terminal-partial') {
              terminalReceived = true
            }
          }

          if (done) break
        }

        if (buffer.trim()) {
          const finalEvent = parseSseBlock(buffer)
          if (finalEvent) {
            handleAnalysisStreamEvent(finalEvent, clientRequestId)
            const classification = classifyStreamEvent(finalEvent)
            if (classification === 'terminal-success' || classification === 'terminal-failure' || classification === 'terminal-partial') {
              terminalReceived = true
            }
          }
        }

        if (!terminalReceived) {
          setMessages((prev) => prev.map((m) => {
            if (String(m.id).toLowerCase() !== String(clientRequestId).toLowerCase()) return m
            if (m.status === 'complete' || m.status === 'failed') return m
            const hasAnswer = Boolean(m.answerText) || m.answerData !== undefined || Boolean(m.result) || Boolean(m.report)
            return {
              ...m,
              status: hasAnswer ? 'complete' : 'failed',
              streaming: false,
              error: hasAnswer ? null : 'The stream ended without a terminal completion event.',
            }
          }))
        }
      } finally {
        reader.releaseLock()
      }
    } catch (e) {
      if (e.name === 'AbortError') {
        console.warn('[query] request aborted or timed out', { clientRequestId })
        setMessages((prev) => prev.map((m) => {
          if (String(m.id).toLowerCase() !== String(clientRequestId).toLowerCase()) return m
          const hasPartial = m.steps.length > 0 || m.result != null || m.row_data != null
          return {
            ...m,
            status: hasPartial ? 'partial' : 'failed',
            streaming: false,
            error: 'The server did not send a completion response. Any available partial results have been preserved.',
          }
        }))
      } else {
        console.error('[query] request error', { clientRequestId, error: e.message })
        setMessages((prev) => prev.map((m) => {
          if (String(m.id).toLowerCase() !== String(clientRequestId).toLowerCase()) return m
          return {
            ...m,
            status: 'failed',
            streaming: false,
            error: e.message || 'The analysis could not be completed.',
          }
        }))
      }
    } finally {
      window.clearTimeout(timeoutId)
      requestManagerRef.current.delete(clientRequestId)
      setLoading(false)
      console.debug('[query] completing request cleanup', { clientRequestId })
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [upload, loading, category])

  const ask = useCallback((q) => {
    const text = (typeof q === 'string' ? q : question).trim()
    if (!text) return
    setQuestion('')
    return streamInto(`${API}/query`, { session_id: upload.session_id, question: text, category }, text)
  }, [question, upload, category, streamInto])

  const story = useCallback(() => {
    if (!upload) return
    return streamInto(`${API}/story`, { session_id: upload.session_id, category }, 'Dataset Story')
  }, [upload, category, streamInto])

  const investigate = useCallback((goal) => {
    if (!upload) return
    const text = (goal || 'Investigate the strongest decision opportunity in this dataset.').trim()
    return streamInto(`${API}/investigate`, { session_id: upload.session_id, goal: text, category }, `Investigation: ${text}`)
  }, [upload, category, streamInto])

  const predict = useCallback(async (target) => {
    if (!target) return
    await streamInto(`${API}/predict`, { session_id: upload.session_id, target, category }, `🔮 Predict "${target}"`)
    try {
      const res = await fetch(`${API}/model_info/${upload.session_id}`, { headers: { 'X-Session-Token': upload?.token || '' } })
      if (res.ok) {
        const info = await res.json()
        if (info.trained) setModelInfo(info)
      }
    } catch (_) {}
  }, [upload, category, streamInto])

  const retryExplanation = useCallback(async (msg) => {
    if (!upload || !msg) return
    const requestId = msg.request_id || msg.requestId || msg.id
    if (!requestId) return

    setMessages((prev) => prev.map((m) => {
      if (String(m.id).toLowerCase() !== String(requestId).toLowerCase()) return m
      return {
        ...m,
        status: 'partial',
        streaming: true,
        warning: { message: 'Retrying written explanation...' },
      }
    }))

    try {
      const res = await fetch(`${API}/query/${encodeURIComponent(requestId)}/retry-answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Session-Token': upload?.token || '' },
        body: JSON.stringify({ session_id: upload.session_id, category }),
      })
      const raw = await res.json()
      if (!res.ok) {
        throw new Error(raw.detail || 'Could not retry the written explanation.')
      }
      handleAnalysisStreamEvent(raw, requestId)
    } catch (e) {
      setMessages((prev) => prev.map((m) => {
        if (String(m.id).toLowerCase() !== String(requestId).toLowerCase()) return m
        return {
          ...m,
          status: 'partial',
          streaming: false,
          warning: {
            code: 'answer_generation_unavailable',
            message: e.message || 'Written explanation is still temporarily unavailable.',
          },
        }
      }))
    }
  }, [upload, category, handleAnalysisStreamEvent])

  const exportCleanedCsv = useCallback(async () => {
    if (!upload || cleaningBusy) return
    setCleaningBusy(true)
    try {
      const res = await fetch(`${API}/clean/${upload.session_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Session-Token': upload?.token || '' },
        body: JSON.stringify({}),
      })
      const payload = await res.json()
      if (!res.ok) throw new Error(payload.detail || 'Could not clean dataset')
      downloadBase64Payload(payload, `${upload.filename.replace('.csv', '')}_cleaned.csv`)
    } catch (e) {
      alert(e.message)
    } finally {
      setCleaningBusy(false)
    }
  }, [upload, cleaningBusy])

  const exportDataContract = useCallback(() => {
    if (!upload?.data_contract) return
    downloadJsonPayload(upload.data_contract, `${upload.filename.replace('.csv', '')}_data_contract.json`)
  }, [upload])

  const exportDashboardSpec = useCallback(() => {
    if (!upload?.dashboard_spec) return
    downloadJsonPayload(upload.dashboard_spec, `${upload.filename.replace('.csv', '')}_dashboard_blueprint.json`)
  }, [upload])

  return (
    <div className="app">
      <TopNav
        upload={upload}
        category={category}
        leftPanelCollapsed={leftPanelCollapsed}
        setLeftPanelCollapsed={setLeftPanelCollapsed}
        rightPanelCollapsed={rightPanelCollapsed}
        setRightPanelCollapsed={setRightPanelCollapsed}
      />
      {!upload ? (
        <UploadScreen
          onUpload={setUpload}
          uploading={uploading}
          setUploading={setUploading}
          category={category}
          setCategory={setCategory}
          onOpenPaste={() => setShowPaste(true)}
          onOpenUrlImport={() => setShowUrlImport(true)}
        />
      ) : (
        <div className={`workspace ${leftPanelCollapsed ? 'collapsed-left' : ''} ${rightPanelCollapsed ? 'collapsed-right' : ''}`}>
          {!leftPanelCollapsed && (
            <>
              <Sidebar
                style={{ width: `${sidebarWidth}px` }}
                upload={upload}
                category={category}
                setCategory={setCategory}
                onReset={() => { setUpload(null); setMessages([]); setModelInfo(null); setDocs([]) }}
                docs={docs}
                onDocsUpdated={setDocs}
                datasets={datasets}
                onSelectDataset={(d) => setUpload(d)}
                onOpenAddDataset={() => setUpload(null)}
                onOpenJoin={() => setShowJoin(true)}
                onOpenCompare={() => setShowCompare(true)}
                onOpenDataViewer={() => setShowDataViewer(true)}
              />
              <div
                className="panel-resizer panel-resizer-left"
                onMouseDown={handleSidebarMouseDown}
                onDoubleClick={() => setSidebarWidth(320)}
                title="Drag to resize left panel (Double-click to reset)"
              >
                <div className="resizer-handle-line" />
              </div>
            </>
          )}
          <ChatArea
            upload={upload}
            category={category}
            messages={messages}
            onAsk={ask}
            onStory={story}
            onInvestigate={investigate}
            onCleanExport={exportCleanedCsv}
            onExportContract={exportDataContract}
            onExportDashboard={exportDashboardSpec}
            cleaningBusy={cleaningBusy}
            loading={loading}
            question={question}
            setQuestion={setQuestion}
            inputRef={inputRef}
            onRetryExplanation={retryExplanation}
          />
          {!rightPanelCollapsed && (
            <>
              <div
                className="panel-resizer panel-resizer-right"
                onMouseDown={handleInsightsMouseDown}
                onDoubleClick={() => setInsightsWidth(400)}
                title="Drag to expand right panel (Double-click to reset)"
              >
                <div className="resizer-handle-line" />
              </div>
              <InsightsErrorBoundary>
                <DatasetInsightsPanel
                  style={{ width: `${insightsWidth}px`, minWidth: '380px', maxWidth: '750px' }}
                  upload={upload}
                  category={category}
                  onAsk={ask}
                  onStory={story}
                  onInvestigate={investigate}
                  onPredict={predict}
                  onOpenPaste={() => setShowPaste(true)}
                  onOpenBenchmark={() => setShowBenchmark(true)}
                  onCleanExport={exportCleanedCsv}
                  onExportContract={exportDataContract}
                  onExportDashboard={exportDashboardSpec}
                />
              </InsightsErrorBoundary>
            </>
          )}
        </div>
      )}

            {showUrlImport && (
        <UrlImportModal uploading={uploading} onClose={() => setShowUrlImport(false)} onSubmit={handleUrlImportSubmit} />
      )}

      {showJoin && datasets.length >= 2 && (
        <JoinModal
          datasets={datasets}
          activeSessionId={upload?.session_id}
          onClose={() => setShowJoin(false)}
          onJoined={handleUpload}
        />
      )}

      {showCompare && datasets.length >= 2 && (
        <CompareModal
          datasets={datasets}
          activeSessionId={upload?.session_id}
          onClose={() => setShowCompare(false)}
        />
      )}

      {showPaste && (
        <PasteModal uploading={uploading} onClose={() => setShowPaste(false)} onSubmit={handlePasteSubmit} />
      )}

      {showBenchmark && upload && (
        <BenchmarkModal sessionId={upload.session_id} onClose={() => setShowBenchmark(false)} />
      )}

      {showDataViewer && upload && (
        <ExcelDataViewerModal upload={upload} onClose={() => setShowDataViewer(false)} />
      )}
    </div>
  )
}

class AppErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('Application rendering error', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <main className="fatal-error" role="alert" style={{ padding: '32px', textAlign: 'center' }}>
          <h1>Something went wrong</h1>
          <p>The interface encountered an unexpected rendering error.</p>
          <button onClick={() => window.location.reload()} style={{ padding: '8px 16px', marginTop: '16px', cursor: 'pointer' }}>
            Reload application
          </button>
        </main>
      )
    }

    return this.props.children
  }
}

export default function AppWithBoundary() {
  return (
    <AppErrorBoundary>
      <App />
    </AppErrorBoundary>
  )
}
export { App, AppErrorBoundary }
