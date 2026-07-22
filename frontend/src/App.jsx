import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import './App.css'
import {
  Logo, Sparkles, FileIcon, Search, Send, Paperclip, Check, X,
  Rows, Columns, AlertDot, Activity, Layers, Code, ChartUp, Brain,
  DollarSign, HeartPulse, ShoppingCart, Megaphone, Users,
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

function TopNav({ upload, category }) {
  const cat = catByKey(category)
  return (
    <header className="topnav">
      <div className="nav-left">
        <span className="brand-logo"><Logo width={20} height={20} /></span>
        <span className="brand-name">CSV Analyst <span className="brand-ai">AI</span></span>
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

function UploadScreen({ onUpload, uploading, setUploading, category, setCategory, onOpenPaste }) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef()

  const handleFile = useCallback(async (file) => {
    if (!file || !file.name.endsWith('.csv')) return
    setUploading(true)
    const fd = new FormData()
    fd.append('file', file)
    try {
      const res = await fetch(`${API}/upload`, { method: 'POST', body: fd })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Upload failed')
      onUpload({ ...data, uploadedAt: new Date() })
    } catch (e) {
      alert(e.message)
    } finally {
      setUploading(false)
    }
  }, [onUpload, setUploading])

  return (
    <div className="upload-screen">
      <div className="upload-hero">
        <div className="hero-badge"><Sparkles width={14} height={14} /> Domain-aware AI Data Analyst</div>
        <h1 className="hero-title">Analysis tuned to your domain</h1>
        <p className="hero-sub">
          Pick an analysis lens, upload a CSV, and ask in plain English. The agent reasons like a
          domain expert — financial, medical, retail and more — not a generic chatbot.
        </p>
      </div>

      <div className="category-picker">
        <div className="cp-label">1 · Choose an analysis lens</div>
        <div className="category-grid">
          {CATEGORIES.map((c) => (
            <button
              key={c.key}
              className={`category-card ${category === c.key ? 'active' : ''}`}
              onClick={() => setCategory(c.key)}
            >
              <span className="cc-icon"><c.icon width={18} height={18} /></span>
              <span className="cc-label">{c.label}</span>
              <span className="cc-blurb">{c.blurb}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="upload-step">
        <div className="cp-label">2 · Upload your dataset</div>
        <div
          className={`dropzone ${dragging ? 'drag-over' : ''} ${uploading ? 'uploading' : ''}`}
          onClick={() => !uploading && inputRef.current.click()}
          onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]) }}
        >
          <input ref={inputRef} type="file" accept=".csv" hidden onChange={(e) => handleFile(e.target.files[0])} />
          <div className="dropzone-icon">{uploading ? <span className="spinner big" /> : <FileIcon width={26} height={26} />}</div>
          <p className="dropzone-title">{uploading ? 'Analyzing your dataset…' : 'Drop a CSV file here'}</p>
          <p className="dropzone-sub">{uploading ? 'Building data profile' : 'or click to browse · .csv up to 50MB'}</p>
        </div>
        <div className="paste-divider"><span>or</span></div>
        <button className="paste-trigger" onClick={onOpenPaste} disabled={uploading}>
          <Code width={15} height={15} /> Paste data / rows instead
        </button>
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
      const res = await fetch(`${API}/upload_doc?session_id=${sessionId}`, { method: 'POST', body: fd })
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

function Sidebar({ upload, category, setCategory, onReset, docs, onDocsUpdated }) {
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
    <aside className="sidebar">
      <div className="dataset-card">
        <div className="dataset-card-top">
          <span className="ds-icon"><FileIcon width={18} height={18} /></span>
          <div className="ds-info">
            <div className="ds-name">{upload.filename}</div>
            <div className="ds-meta">{upload.rows.toLocaleString()} rows · {upload.columns.length} columns</div>
          </div>
          <button className="icon-btn" onClick={onReset} title="Change file"><X width={15} height={15} /></button>
        </div>
        <div className="ds-tags">
          <span className="ds-tag">{upload.numeric_features} numeric</span>
          <span className="ds-tag">{upload.columns.length - upload.numeric_features} categorical</span>
          {ts && <span className="ds-tag muted">Uploaded {ts}</span>}
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
    </aside>
  )
}

// ─── Insights Panel ────────────────────────────────────────────────────────────

export function PredictInputCard({ sessionId, modelInfo }) {
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
        headers: { 'Content-Type': 'application/json' },
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

export function ScenarioSimulatorCard({ sessionId, modelInfo, category }) {
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
        headers: { 'Content-Type': 'application/json' },
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
        headers: { 'Content-Type': 'application/json' },
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
      const res = await fetch(`${API}/benchmark/${sessionId}?n=${n}`)
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

function ExportCard({ upload, messages, category }) {
  const [busy, setBusy] = useState(null) // 'pdf' | 'pptx' | null

  const exportReport = async (format) => {
    setBusy(format)
    try {
      const body = {
        messages: messages.map(m => ({
          question:  m.question,
          report:    m.report,
          result:    m.result,
          chart:     m.chart,
          chart_json: m.chart_json,
          shap_chart: m.shap_chart,
          critique:  m.critique,
          validation: m.validation,
          code:      m.code,
          code_lang: m.code_lang,
        })),
        category,
        filename: upload.filename.replace('.csv', ''),
      }
      const res = await fetch(`${API}/report/${upload.session_id}?format=${format}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Export failed') }
      const payload = await res.json()
      downloadBase64Payload(payload, `${upload.filename.replace('.csv', '')}_report.${format}`)
    } catch (e) {
      alert(e.message)
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="insight-card export-card">
      <div className="ic-head">📄 Export Report</div>
      <p className="predict-hint">Download the full analytics report with all charts, summaries, and insights.</p>
      <div className="export-btns">
        <button className="export-btn pdf" onClick={() => exportReport('pdf')} disabled={!!busy || messages.length === 0}>
          {busy === 'pdf' ? <span className="spinner" style={{borderTopColor:'#EF4444',borderColor:'#FECACA'}} /> : '⬇ PDF'}
        </button>
        <button className="export-btn pptx" onClick={() => exportReport('pptx')} disabled={!!busy || messages.length === 0}>
          {busy === 'pptx' ? <span className="spinner" style={{borderTopColor:'#F59E0B',borderColor:'#FDE68A'}} /> : '⬇ PPTX'}
        </button>
      </div>
      {messages.length === 0 && <p className="predict-hint" style={{marginTop:4}}>Ask a question first to generate content for the report.</p>}
    </div>
  )
}

function InsightsPanel({ upload, category, onAsk, onStory, onInvestigate, onPredict, onOpenPaste, onOpenBenchmark, onCleanExport, onExportContract, onExportDashboard, cleaningBusy, modelInfo, loading, messages }) {
  const cat = catByKey(category)
  const numericCols = Object.keys(upload.numeric_stats || {})
  const [statCol, setStatCol] = useState(numericCols[0] || '')
  const stats = upload.numeric_stats?.[statCol]
  // default the prediction target to the last column (commonly the outcome/target)
  const [target, setTarget] = useState(upload.columns[upload.columns.length - 1] || '')

  const healthScore = useMemo(() => {
    let score = 100
    score -= Math.min(40, upload.missing_pct * 2)
    score -= Math.min(30, (upload.duplicate_rows / Math.max(1, upload.rows)) * 100)
    return Math.max(40, Math.round(score))
  }, [upload])

  const healthItems = [
    { label: 'Missing Values', ok: upload.missing_pct < 5, value: `${upload.missing_pct}%` },
    { label: 'Duplicate Rows', ok: upload.duplicate_rows === 0, value: upload.duplicate_rows },
    { label: 'Data Types',     ok: true, value: `${upload.numeric_features} numeric` },
  ]
  const qualityIssues = upload.quality_report?.issues || []
  const brief = upload.decision_brief
  const decisionActions = upload.decision_actions || brief?.decision_actions || []
  const cleaningPlan = upload.cleaning_plan
  const contract = upload.data_contract
  const dashboard = upload.dashboard_spec

  return (
    <aside className="insights">
      {brief && (
        <div className="insight-card decision-card">
          <div className="ic-head"><Layers width={15} height={15} /> Decision Brief</div>
          <div className="decision-top">
            <div className={`decision-score ${brief.readiness_label}`}>
              <span>{brief.readiness_score}</span>
              <small>readiness</small>
            </div>
            <div>
              <div className="decision-label">{(brief.readiness_label || '').replaceAll('_', ' ')}</div>
              <p className="decision-summary">{brief.summary}</p>
            </div>
          </div>
          {brief.recommended_use_cases?.length > 0 && (
            <div className="brief-section">
              <div className="brief-kicker">Best use cases</div>
              {brief.recommended_use_cases.slice(0, 3).map((item) => (
                <div key={item.name} className="brief-use">
                  <span>{item.name}</span>
                  <em>{item.fit}</em>
                </div>
              ))}
            </div>
          )}
          {brief.next_actions?.length > 0 && (
            <div className="brief-section">
              <div className="brief-kicker">Next actions</div>
              {brief.next_actions.slice(0, 3).map((item, i) => (
                <div key={`${item.action}-${i}`} className={`brief-action ${item.priority}`}>
                  <strong>{item.action}</strong>
                  <span>{item.impact}</span>
                </div>
              ))}
            </div>
          )}
          {brief.priority_questions?.length > 0 && (
            <div className="brief-question-row">
              {brief.priority_questions.slice(0, 2).map((q) => (
                <button key={q} className="brief-question" disabled={loading} onClick={() => onAsk(q)}>
                  <Sparkles width={12} height={12} /> {q}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {decisionActions.length > 0 && (
        <div className="insight-card action-card">
          <div className="ic-head"><Sparkles width={15} height={15} /> Decision Actions</div>
          <div className="action-list">
            {decisionActions.slice(0, 3).map((action, i) => (
              <div key={`${action.title}-${i}`} className={`decision-action ${action.priority}`}>
                <div className="action-top">
                  <strong>{action.title}</strong>
                  <em>{Math.round((action.confidence || 0) * 100)}%</em>
                </div>
                <p>{action.recommended_action}</p>
                <div className="action-impact">{action.estimated_impact}</div>
                {action.evidence?.length > 0 && (
                  <ul className="action-evidence">
                    {action.evidence.slice(0, 2).map((item) => <li key={item}>{item}</li>)}
                  </ul>
                )}
                {action.suggested_question && (
                  <button className="action-investigate" disabled={loading} onClick={() => onInvestigate(action.suggested_question)}>
                    Investigate
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="insight-card health">
        <div className="ic-head"><Activity width={15} height={15} /> Dataset Health</div>
        <div className="health-score">
          <div className="ring" style={{ '--score': healthScore }}><span>{healthScore}</span></div>
          <div className="health-list">
            {healthItems.map((h) => (
              <div key={h.label} className="health-item">
                <span className={`dot ${h.ok ? 'good' : 'warn'}`} />
                <span className="hi-label">{h.label}</span>
                <span className="hi-value">{h.value}</span>
              </div>
            ))}
          </div>
        </div>
        {qualityIssues.length > 0 && (
          <div className="quality-list">
            {qualityIssues.slice(0, 4).map((issue, i) => (
              <div key={`${issue.title}-${i}`} className={`quality-item ${issue.severity}`}>
                <div className="qi-title">{issue.title}</div>
                <div className="qi-detail">{issue.detail}</div>
                {issue.suggestion && <div className="qi-suggestion">{issue.suggestion}</div>}
              </div>
            ))}
          </div>
        )}
      </div>

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
          <button className="clean-export-btn" disabled={cleaningBusy} onClick={onCleanExport}>
            {cleaningBusy ? <span className="spinner" /> : <Check width={14} height={14} />}
            Download cleaned CSV
          </button>
        </div>
      )}

      {contract && (
        <div className="insight-card contract-card">
          <div className="ic-head"><Columns width={15} height={15} /> Data Contract</div>
          <div className="contract-stats">
            <div><strong>{contract.column_count}</strong><span>columns</span></div>
            <div><strong>{contract.required_columns?.length || 0}</strong><span>required</span></div>
          </div>
          <div className="contract-cols">
            {contract.columns.slice(0, 5).map((col) => (
              <div key={col.name} className="contract-col">
                <span>{col.name}</span>
                <em>{col.type}</em>
              </div>
            ))}
          </div>
          <button className="contract-export-btn" onClick={onExportContract}>
            <Code width={14} height={14} /> Export contract JSON
          </button>
        </div>
      )}

      {dashboard && (
        <div className="insight-card dashboard-card">
          <div className="ic-head"><ChartUp width={15} height={15} /> Dashboard Blueprint</div>
          <div className="dashboard-stats">
            <div><strong>{dashboard.kpis?.length || 0}</strong><span>KPIs</span></div>
            <div><strong>{dashboard.charts?.length || 0}</strong><span>charts</span></div>
            <div><strong>{dashboard.filters?.length || 0}</strong><span>filters</span></div>
          </div>
          <div className="dashboard-charts">
            {dashboard.charts?.slice(0, 4).map((chart) => (
              <button key={chart.id} disabled={loading} onClick={() => onAsk(chart.question)}>
                <span>{chart.title}</span>
                <em>{chart.type}</em>
              </button>
            ))}
          </div>
          <button className="dashboard-export-btn" onClick={onExportDashboard}>
            <Code width={14} height={14} /> Export dashboard JSON
          </button>
        </div>
      )}

      {numericCols.length > 0 && (
        <div className="insight-card">
          <div className="ic-head">
            <ChartUp width={15} height={15} /> Quick Statistics
            <select className="stat-select" value={statCol} onChange={(e) => setStatCol(e.target.value)}>
              {numericCols.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          {stats && (
            <div className="stat-grid">
              <Stat label="Mean"   v={stats.mean} />
              <Stat label="Median" v={stats.median} />
              <Stat label="Std Dev" v={stats.std} />
              <Stat label="Min"    v={stats.min} />
              <Stat label="Max"    v={stats.max} />
              <Stat label="Range"  v={stats.max != null && stats.min != null ? +(stats.max - stats.min).toFixed(2) : null} />
            </div>
          )}
        </div>
      )}

      <div className="insight-card custom-card">
        <div className="ic-head"><Code width={15} height={15} /> Custom Data</div>
        <p className="predict-hint">Paste your own rows or values to analyze them on the fly.</p>
        <button className="custom-btn" disabled={loading} onClick={onOpenPaste}>
          <Code width={14} height={14} /> Paste / input data
        </button>
      </div>

      <div className="insight-card story-card">
        <div className="ic-head"><Sparkles width={15} height={15} /> Dataset Story</div>
        <p className="predict-hint">Generate a fact-first narrative from computed profile, quality, segment, and relationship facts.</p>
        <button className="custom-btn" disabled={loading} onClick={onStory}>
          <Sparkles width={14} height={14} /> Generate dataset story
        </button>
      </div>

      <div className="insight-card predict-card">
        <div className="ic-head"><Brain width={15} height={15} /> Predictive Model</div>
        <p className="predict-hint">Train a model to predict a column and see what drives it.</p>
        <div className="predict-row">
          <span className="predict-label">Predict</span>
          <select className="predict-select" value={target} onChange={(e) => setTarget(e.target.value)}>
            {upload.columns.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <button className="predict-btn" disabled={loading || !target} onClick={() => onPredict(target)}>
          {loading ? <span className="spinner" /> : <>🔮 Train &amp; Predict</>}
        </button>
      </div>

      {modelInfo?.trained && (
        <>
          <PredictInputCard sessionId={upload.session_id} modelInfo={modelInfo} />
          <ScenarioSimulatorCard sessionId={upload.session_id} modelInfo={modelInfo} category={category} />
        </>
      )}

      <div className="insight-card benchmark-card">
        <div className="ic-head">🏆 Benchmark</div>
        <p className="predict-hint">Evaluate the system with a suite of analytics questions and measure accuracy, chart rate, SQL routing, and response time.</p>
        <button className="custom-btn" disabled={loading} onClick={() => onOpenBenchmark()}>
          ▶ Run evaluation benchmark
        </button>
      </div>

      <ExportCard upload={upload} messages={messages} category={category} />

      <div className="insight-card">
        <div className="ic-head"><cat.icon width={15} height={15} /> {cat.label} Analyses</div>
        <div className="suggest-list">
          {cat.suggested.map((s) => (
            <button key={s.label} className="suggest-btn" disabled={loading} onClick={() => onAsk(s.q)}>
              <span>{s.label}</span>
              <span className="suggest-arrow">→</span>
            </button>
          ))}
        </div>
      </div>
    </aside>
  )
}

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
  const meta = STEP_META[step.step] || { icon: '•', color: '#94A3B8' }
  const trace = step.meta || {}
  const elapsed = trace.elapsed_ms != null
    ? trace.elapsed_ms < 1000
      ? `${trace.elapsed_ms} ms`
      : `${(trace.elapsed_ms / 1000).toFixed(1)} s`
    : null
  const requestShort = trace.request_id ? trace.request_id.slice(0, 8) : null
  return (
    <div className="step-row" style={{ '--step-color': meta.color }}>
      <span className="step-icon">{meta.icon}</span>
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
  const v = VERDICT_META[critique.verdict] || VERDICT_META.pass
  const conf = critique.confidence != null ? `${Math.round(critique.confidence * 100)}%` : null
  return (
    <div className="critique-badge" style={{ '--vcolor': v.color, '--vbg': v.bg, '--vborder': v.border }}>
      <div className="cb-verdict">{v.label}{conf && <span className="cb-conf">{conf} confidence</span>}</div>
      {critique.issues?.length > 0 && (
        <ul className="cb-list cb-issues">
          {critique.issues.map((i, idx) => <li key={idx}>{i}</li>)}
        </ul>
      )}
      {critique.strengths?.length > 0 && (
        <ul className="cb-list cb-strengths">
          {critique.strengths.map((s, idx) => <li key={idx}>{s}</li>)}
        </ul>
      )}
      {critique.suggestion && <p className="cb-suggestion">💡 {critique.suggestion}</p>}
    </div>
  )
}

function ValidationPanel({ validation }) {
  if (!validation) return null
  return (
    <div className="validation-panel">
      <div className="vp-head">
        <Check width={13} height={13} />
        <span>{validation.confidence_label || 'High'} trust</span>
        {validation.confidence != null && (
          <em>{Math.round(validation.confidence * 100)}%</em>
        )}
      </div>
      <div className="vp-method">{validation.method}</div>
      <div className="vp-meta">
        <span>{Number(validation.row_support || 0).toLocaleString()} rows checked</span>
        {validation.source_columns?.length > 0 && (
          <span>{validation.source_columns.join(', ')}</span>
        )}
        {validation.missing_pct != null && validation.missing_pct > 0 && (
          <span>{validation.missing_pct}% missing in source fields</span>
        )}
      </div>
      {validation.reasons?.length > 0 && (
        <ul className="vp-reasons">
          {validation.reasons.slice(0, 3).map((reason, i) => <li key={i}>{reason}</li>)}
        </ul>
      )}
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
  const variant = route === 'deterministic' || route?.includes('deterministic')
    ? 'deterministic'
    : route === 'cache'
      ? 'cache'
      : 'agent'

  return (
    <span className={`answer-trust-badge ${variant}`} title={validation?.method || critique?.suggestion || routeLabel}>
      <span>{routeLabel}</span>
      {(level || confidenceText) && <em>{level}{confidenceText ? ` · ${confidenceText}` : ''}</em>}
    </span>
  )
}

function PlanBadge({ plan }) {
  const [open, setOpen] = useState(false)
  if (!plan?.strategy) return null
  return (
    <div className="plan-badge">
      <button className="plan-toggle" onClick={() => setOpen(v => !v)}>
        🗺️ Strategy: {plan.strategy}
        <span className="plan-arrow">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="plan-detail">
          {plan.persona && (
            <div className="persona-strip">
              <div>
                <strong>{plan.persona.name}</strong>
                <span>{plan.persona.focus}</span>
              </div>
              {plan.persona.priority_kpis?.length > 0 && (
                <div className="persona-kpis">
                  {plan.persona.priority_kpis.slice(0, 5).map((kpi) => <em key={kpi}>{kpi}</em>)}
                </div>
              )}
            </div>
          )}
          {plan.analysis_steps?.length > 0 && (
            <ol className="plan-steps">
              {plan.analysis_steps.map((s, i) => <li key={i}>{s}</li>)}
            </ol>
          )}
          {plan.relevant_columns?.length > 0 && (
            <div className="plan-cols">
              Columns: {plan.relevant_columns.map(c => <span key={c} className="plan-col">{c}</span>)}
            </div>
          )}
          {plan.rag_sources?.length > 0 && (
            <div className="plan-rag">
              📄 Context from: {plan.rag_sources.map(f => <span key={f} className="rag-source">{f}</span>)}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const EXPLAIN_TABS = [
  { key: 'importance', label: '📊 Feature Importance', field: 'chart' },
  { key: 'shap',       label: '🔬 SHAP Beeswarm',     field: 'shap_chart' },
  { key: 'perm',       label: '🎲 Permutation',        field: 'perm_chart' },
  { key: 'pdp',        label: '📈 Partial Dependence', field: 'pdp_chart' },
]

function ExplainPanel({ msg }) {
  const available = EXPLAIN_TABS.filter(t => msg[t.field])
  const [active, setActive] = useState(0)
  if (available.length === 0) return null
  const current = available[active]
  return (
    <div className="explain-panel">
      <div className="explain-label">🧠 Explainability</div>
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

function ChatMessage({ msg, onAsk }) {
  const [showCode, setShowCode] = useState(false)
  const isDone = msg.steps.some((s) => s.step === 'done')
  const isError = msg.steps.some((s) => s.step === 'error')
  const cat = catByKey(msg.category)
  const hasExplain = msg.shap_chart || msg.perm_chart || msg.pdp_chart
  const latestMeta = [...msg.steps].reverse().find((s) => s.meta)?.meta
  const route = latestMeta?.route || msg.plan?.query_type

  // Filter display steps — hide internal plan/critique/code steps from the track
  const displaySteps = msg.steps.filter(s => !['plan', 'critique', 'code'].includes(s.step))

  return (
    <div className="chat-msg">
      <div className="bubble-user"><p>{msg.question}</p></div>

      <div className={`bubble-agent ${isError ? 'is-error' : isDone ? 'is-done' : 'is-loading'}`}>
        <div className="agent-head">
          <Sparkles width={14} height={14} /> Multi-Agent Analyst
          <span className="agent-lens"><cat.icon width={11} height={11} /> {cat.label}</span>
          {msg.plan?.persona?.name && (
            <span className="persona-head-badge">{msg.plan.persona.name}</span>
          )}
          {isDone && !isError && (
            <AnswerTrustBadge route={route} validation={msg.validation} critique={msg.critique} />
          )}
          {latestMeta?.request_id && (
            <span className="trace-badge" title={`Request ${latestMeta.request_id}`}>
              {latestMeta.endpoint || 'stream'} #{latestMeta.request_id.slice(0, 8)}
            </span>
          )}
          <span className="security-badge" title="AST-validated · sandboxed execution · 30s timeout">🔒</span>
        </div>

        <div className="steps-track">
          {displaySteps.map((s, i) => <AgentStep key={i} step={s} />)}
        </div>

        {msg.plan && <PlanBadge plan={msg.plan} />}

        {msg.code && (
          <div className="code-section">
            <button className="code-toggle" onClick={() => setShowCode((v) => !v)}>
              <Code width={14} height={14} />
              {msg.code_lang === 'sql'
                ? <span className="code-lang-badge sql">SQL</span>
                : <span className="code-lang-badge py">Python</span>}
              {showCode ? 'Hide' : 'Show'} generated code
            </button>
            {showCode && <div className="code-block"><pre>{msg.code}</pre></div>}
          </div>
        )}

        {/* ML predict: explainability panel; otherwise Plotly or PNG chart */}
        {hasExplain ? (
          <ExplainPanel msg={msg} />
        ) : msg.chart_json ? (
          <PlotlyChart json={msg.chart_json} />
        ) : (
          msg.chart && <img className="chart-img" src={`data:image/png;base64,${msg.chart}`} alt="Generated chart" />
        )}

        {msg.report && !isError && (
          <div className="report-section">
            <div className="report-label"><Sparkles width={12} height={12} /> Executive Summary</div>
            <div className="report-body">{msg.report}</div>
          </div>
        )}

        {!msg.report && msg.result && !isError && (
          <div className="result-box"><pre className="result-text">{msg.result}</pre></div>
        )}

        {msg.critique && isDone && <CritiqueBadge critique={msg.critique} />}

        {msg.validation && isDone && !isError && <ValidationPanel validation={msg.validation} />}

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

function ChatArea({ upload, category, messages, onAsk, onStory, onInvestigate, onCleanExport, onExportContract, onExportDashboard, cleaningBusy, loading, question, setQuestion, inputRef }) {
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
          {messages.map((m) => <ChatMessage key={m.id} msg={m} onAsk={onAsk} />)}
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

export default function App() {
  const [upload, setUpload] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [category, setCategory] = useState('general')
  const [messages, setMessages] = useState([])
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPaste, setShowPaste] = useState(false)
  const [showBenchmark, setShowBenchmark] = useState(false)
  const [modelInfo, setModelInfo] = useState(null)
  const [docs, setDocs] = useState([])
  const [cleaningBusy, setCleaningBusy] = useState(false)
  const inputRef = useRef()

  const handlePasteSubmit = useCallback(async (text, hasHeader) => {
    if (!text.trim()) return
    setUploading(true)
    try {
      const res = await fetch(`${API}/upload_text`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, has_header: hasHeader, filename: 'pasted_data.csv' }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Could not parse the data')
      setShowPaste(false)
      setMessages([])
      setModelInfo(null)
      setDocs([])
      setUpload({ ...data, uploadedAt: new Date() })
    } catch (e) {
      alert(e.message)
    } finally {
      setUploading(false)
    }
  }, [])

  // Shared SSE consumer used by streaming analysis endpoints.
  const streamInto = useCallback(async (url, body, label) => {
    if (!upload || loading) return
    setLoading(true)
    const msgId = Date.now()
    setMessages((prev) => [...prev, { id: msgId, question: label, category, steps: [], code: null, code_lang: null, result: null, chart: null, chart_json: null, report: null, critique: null, validation: null, plan: null, followups: [], shap_chart: null, perm_chart: null, pdp_chart: null }])

    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Request failed')
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      const handleEvent = (block) => {
        const line = block.split('\n').find((l) => l.startsWith('data: '))
        if (!line) return
        try {
          const event = JSON.parse(line.slice(6))
          setMessages((prev) => prev.map((m) => m.id !== msgId ? m : {
            ...m,
            steps: [...m.steps, event],
            code: event.code ?? m.code,
            code_lang: event.code_lang ?? m.code_lang,
            result: event.result ?? m.result,
            chart: event.chart ?? m.chart,
            chart_json: event.chart_json ?? m.chart_json,
            report: event.report ?? m.report,
            critique: event.critique ?? m.critique,
            validation: event.validation ?? m.validation,
            plan: event.plan ?? m.plan,
            followups: event.followups ?? m.followups,
            shap_chart: event.shap_chart ?? m.shap_chart,
            perm_chart: event.perm_chart ?? m.perm_chart,
            pdp_chart:  event.pdp_chart  ?? m.pdp_chart,
          }))
        } catch (_) {}
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        // Buffer chunks; only parse complete SSE events (separated by a blank line).
        // Large payloads (e.g. a 90KB chart) span multiple chunks.
        buffer += decoder.decode(value, { stream: true })
        const blocks = buffer.split('\n\n')
        buffer = blocks.pop() ?? ''
        for (const block of blocks) handleEvent(block)
      }
      if (buffer.trim()) handleEvent(buffer)
    } catch (e) {
      setMessages((prev) => prev.map((m) => m.id === msgId
        ? { ...m, steps: [...m.steps, { step: 'error', message: e.message }] } : m))
    } finally {
      setLoading(false)
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
    // Load the trained-model metadata so the user can predict new cases.
    try {
      const res = await fetch(`${API}/model_info/${upload.session_id}`)
      if (res.ok) {
        const info = await res.json()
        if (info.trained) setModelInfo(info)
      }
    } catch (_) {}
  }, [upload, category, streamInto])

  const exportCleanedCsv = useCallback(async () => {
    if (!upload || cleaningBusy) return
    setCleaningBusy(true)
    try {
      const res = await fetch(`${API}/clean/${upload.session_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
      <TopNav upload={upload} category={category} />
      {!upload ? (
        <UploadScreen
          onUpload={setUpload}
          uploading={uploading}
          setUploading={setUploading}
          category={category}
          setCategory={setCategory}
          onOpenPaste={() => setShowPaste(true)}
        />
      ) : (
        <div className="workspace">
          <Sidebar
            upload={upload}
            category={category}
            setCategory={setCategory}
            onReset={() => { setUpload(null); setMessages([]); setModelInfo(null); setDocs([]) }}
            docs={docs}
            onDocsUpdated={setDocs}
          />
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
          />
          <InsightsPanel
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
            cleaningBusy={cleaningBusy}
            modelInfo={modelInfo}
            loading={loading}
            messages={messages}
          />
        </div>
      )}

      {showPaste && (
        <PasteModal uploading={uploading} onClose={() => setShowPaste(false)} onSubmit={handlePasteSubmit} />
      )}

      {showBenchmark && upload && (
        <BenchmarkModal sessionId={upload.session_id} onClose={() => setShowBenchmark(false)} />
      )}
    </div>
  )
}
