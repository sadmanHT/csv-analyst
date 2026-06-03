import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import './App.css'
import {
  Logo, Sparkles, FileIcon, Search, Send, Paperclip, Check, X,
  Rows, Columns, AlertDot, Activity, Layers, Code, ChartUp, Brain,
} from './icons.jsx'

const EXAMPLE_PROMPTS = [
  { icon: ChartUp,  text: 'Show a bar chart of revenue by category' },
  { icon: Activity, text: 'What is the distribution of customer age?' },
  { icon: Layers,   text: 'Which region has the highest total revenue?' },
  { icon: Brain,    text: 'Show a correlation heatmap of numeric columns' },
]

const SUGGESTED = [
  { label: 'Correlation Analysis', q: 'Show a correlation heatmap of all numeric columns' },
  { label: 'Distribution',         q: 'Plot the distribution of the first numeric column' },
  { label: 'Top Categories',       q: 'Show a bar chart of the top categories by count' },
  { label: 'Outlier Detection',    q: 'Show a box plot to detect outliers in numeric columns' },
]

const STEP_META = {
  analyzing: { icon: '🔍', color: '#4F46E5' },
  thinking:  { icon: '🧠', color: '#8B5CF6' },
  code:      { icon: '💻', color: '#06B6D4' },
  executing: { icon: '⚡', color: '#F59E0B' },
  done:      { icon: '✅', color: '#10B981' },
  error:     { icon: '⚠️', color: '#EF4444' },
}

// ─── Top Navigation ────────────────────────────────────────────────────────────

function TopNav({ upload }) {
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
            <span className="stat-pill"><Rows width={13} height={13} /> {upload.rows.toLocaleString()} <em>rows</em></span>
            <span className="stat-pill"><Columns width={13} height={13} /> {upload.columns.length} <em>cols</em></span>
            <span className={`stat-pill ${upload.missing_pct > 0 ? 'warn' : 'ok'}`}>
              <AlertDot width={13} height={13} /> {upload.missing_pct}% <em>missing</em>
            </span>
          </div>
        ) : (
          <span className="nav-tag">AI-powered data analysis</span>
        )}
      </div>
    </header>
  )
}

// ─── Upload Screen ─────────────────────────────────────────────────────────────

function UploadScreen({ onUpload, uploading, setUploading }) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef()

  const handleFile = useCallback(async (file) => {
    if (!file || !file.name.endsWith('.csv')) return
    setUploading(true)
    const fd = new FormData()
    fd.append('file', file)
    try {
      const res = await fetch('/upload', { method: 'POST', body: fd })
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
        <div className="hero-badge"><Sparkles width={14} height={14} /> AI Data Analyst</div>
        <h1 className="hero-title">Analyze your data with natural language</h1>
        <p className="hero-sub">
          Upload a CSV and ask questions in plain English. The agent writes the code,
          runs it on your data, and returns charts and insights instantly.
        </p>
      </div>

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

      <div className="trust-row">
        <span><Check width={13} height={13} /> Code is sandboxed</span>
        <span><Check width={13} height={13} /> Runs on your data</span>
        <span><Check width={13} height={13} /> Inspectable output</span>
      </div>
    </div>
  )
}

// ─── Sidebar ───────────────────────────────────────────────────────────────────

function Sidebar({ upload, onReset }) {
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
          {filtered.length === 0 && <div className="schema-empty">No columns match “{q}”</div>}
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

function InsightsPanel({ upload, onAsk, loading }) {
  const numericCols = Object.keys(upload.numeric_stats || {})
  const [statCol, setStatCol] = useState(numericCols[0] || '')
  const stats = upload.numeric_stats?.[statCol]

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

  return (
    <aside className="insights">
      <div className="insight-card health">
        <div className="ic-head"><Activity width={15} height={15} /> Dataset Health</div>
        <div className="health-score">
          <div className="ring" style={{ '--score': healthScore }}>
            <span>{healthScore}</span>
          </div>
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
      </div>

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

      <div className="insight-card">
        <div className="ic-head"><Sparkles width={15} height={15} /> Suggested Analyses</div>
        <div className="suggest-list">
          {SUGGESTED.map((s) => (
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

// ─── Chat ──────────────────────────────────────────────────────────────────────

function AgentStep({ step }) {
  const meta = STEP_META[step.step] || { icon: '•', color: '#94A3B8' }
  return (
    <div className="step-row" style={{ '--step-color': meta.color }}>
      <span className="step-icon">{meta.icon}</span>
      <span className="step-label">{step.message}</span>
    </div>
  )
}

function ChatMessage({ msg }) {
  const [showCode, setShowCode] = useState(false)
  const isDone = msg.steps.some((s) => s.step === 'done')
  const isError = msg.steps.some((s) => s.step === 'error')

  return (
    <div className="chat-msg">
      <div className="bubble-user"><p>{msg.question}</p></div>

      <div className={`bubble-agent ${isError ? 'is-error' : isDone ? 'is-done' : 'is-loading'}`}>
        <div className="agent-head"><Sparkles width={14} height={14} /> Analyst Agent</div>

        <div className="steps-track">
          {msg.steps.map((s, i) => <AgentStep key={i} step={s} />)}
        </div>

        {msg.code && (
          <div className="code-section">
            <button className="code-toggle" onClick={() => setShowCode((v) => !v)}>
              <Code width={14} height={14} /> {showCode ? 'Hide' : 'Show'} generated code
            </button>
            {showCode && <div className="code-block"><pre>{msg.code}</pre></div>}
          </div>
        )}

        {msg.result && !isError && (
          <div className="result-box"><pre className="result-text">{msg.result}</pre></div>
        )}

        {msg.chart && (
          <img className="chart-img" src={`data:image/png;base64,${msg.chart}`} alt="Generated chart" />
        )}
      </div>
    </div>
  )
}

function ChatArea({ upload, messages, onAsk, loading, question, setQuestion, inputRef }) {
  const bottomRef = useRef()
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  return (
    <main className="chat-area">
      {messages.length === 0 ? (
        <div className="chat-empty">
          <div className="empty-icon"><Sparkles width={30} height={30} /></div>
          <h2>Analyze your data with natural language</h2>
          <p>Ask questions, create charts, discover patterns, and generate insights instantly.</p>
          <div className="example-grid">
            {EXAMPLE_PROMPTS.map((ex) => (
              <button key={ex.text} className="example-card" disabled={loading} onClick={() => onAsk(ex.text)}>
                <span className="ex-icon"><ex.icon width={16} height={16} /></span>
                <span>{ex.text}</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="message-list">
          {messages.map((m) => <ChatMessage key={m.id} msg={m} />)}
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
            placeholder={`Ask anything about ${upload.filename}…`}
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
        <div className="composer-hint">AI can make mistakes — generated code is shown for every answer.</div>
      </div>
    </main>
  )
}

// ─── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const [upload, setUpload] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [messages, setMessages] = useState([])
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const inputRef = useRef()

  const ask = useCallback(async (q) => {
    const text = (typeof q === 'string' ? q : question).trim()
    if (!text || !upload || loading) return
    setQuestion('')
    setLoading(true)

    const msgId = Date.now()
    setMessages((prev) => [...prev, { id: msgId, question: text, steps: [], code: null, result: null, chart: null }])

    try {
      const res = await fetch('/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: upload.session_id, question: text }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Query failed')
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const lines = decoder.decode(value).split('\n').filter((l) => l.startsWith('data: '))
        for (const line of lines) {
          try {
            const event = JSON.parse(line.slice(6))
            setMessages((prev) => prev.map((m) => m.id !== msgId ? m : {
              ...m,
              steps: [...m.steps, event],
              code: event.code ?? m.code,
              result: event.result ?? m.result,
              chart: event.chart ?? m.chart,
            }))
          } catch (_) {}
        }
      }
    } catch (e) {
      setMessages((prev) => prev.map((m) => m.id === msgId
        ? { ...m, steps: [...m.steps, { step: 'error', message: e.message }] } : m))
    } finally {
      setLoading(false)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [question, upload, loading])

  return (
    <div className="app">
      <TopNav upload={upload} />
      {!upload ? (
        <UploadScreen onUpload={setUpload} uploading={uploading} setUploading={setUploading} />
      ) : (
        <div className="workspace">
          <Sidebar upload={upload} onReset={() => { setUpload(null); setMessages([]) }} />
          <ChatArea
            upload={upload}
            messages={messages}
            onAsk={ask}
            loading={loading}
            question={question}
            setQuestion={setQuestion}
            inputRef={inputRef}
          />
          <InsightsPanel upload={upload} onAsk={ask} loading={loading} />
        </div>
      )}
    </div>
  )
}
