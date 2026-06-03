import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import './App.css'
import {
  Logo, Sparkles, FileIcon, Search, Send, Paperclip, Check, X,
  Rows, Columns, AlertDot, Activity, Layers, Code, ChartUp, Brain,
  DollarSign, HeartPulse, ShoppingCart, Megaphone, Users,
} from './icons.jsx'

// ─── Domain categories (the differentiator) ────────────────────────────────────

const CATEGORIES = [
  {
    key: 'general', label: 'General', icon: ChartUp,
    blurb: 'Neutral statistical analysis',
    examples: [
      'Summarize the key statistics of this dataset',
      'What is the distribution of the first numeric column?',
      'Show a correlation heatmap of numeric columns',
      'Show a bar chart of the top categories by count',
    ],
    suggested: [
      { label: 'Correlation Analysis', q: 'Show a correlation heatmap of all numeric columns' },
      { label: 'Distribution',         q: 'Plot the distribution of the first numeric column' },
      { label: 'Top Categories',       q: 'Show a bar chart of the top categories by count' },
      { label: 'Outlier Detection',    q: 'Show a box plot to detect outliers in numeric columns' },
    ],
  },
  {
    key: 'financial', label: 'Financial', icon: DollarSign,
    blurb: 'Revenue, growth, risk & ratios',
    examples: [
      'Plot total revenue over time as a line chart',
      'Which category generates the most revenue?',
      'Calculate the period-over-period growth rate',
      'Show the volatility (std dev) of the key numeric columns',
    ],
    suggested: [
      { label: 'Revenue Trend',        q: 'Plot total revenue over time as a line chart' },
      { label: 'Growth Rate',          q: 'Calculate and chart the period-over-period growth rate' },
      { label: 'Top Revenue Drivers',  q: 'Show a bar chart of total revenue by category' },
      { label: 'Risk / Volatility',    q: 'Show the standard deviation of the main numeric columns as a risk measure' },
    ],
  },
  {
    key: 'medical', label: 'Medical', icon: HeartPulse,
    blurb: 'Risk factors & patient cohorts',
    examples: [
      'Which features correlate most with the outcome?',
      'Compare the mean of each numeric feature between outcome groups',
      'Show the distribution of age split by outcome',
      'Show a correlation heatmap of clinical measurements',
    ],
    suggested: [
      { label: 'Risk Factors',         q: 'Which features correlate most with the outcome variable?' },
      { label: 'Cohort Comparison',    q: 'Compare the mean of each numeric feature between the outcome groups' },
      { label: 'Distribution by Group',q: 'Plot the distribution of the first numeric feature split by outcome' },
      { label: 'Correlation Heatmap',  q: 'Show a correlation heatmap of all numeric columns' },
    ],
  },
  {
    key: 'retail', label: 'Retail', icon: ShoppingCart,
    blurb: 'Sales, products & customers',
    examples: [
      'Show a bar chart of revenue by product category',
      'Which region has the highest total sales?',
      'What is the average order value?',
      'Show the relationship between rating and revenue',
    ],
    suggested: [
      { label: 'Sales by Category',    q: 'Show a bar chart of total revenue by category' },
      { label: 'Top Regions',          q: 'Which region has the highest total revenue? Show a bar chart' },
      { label: 'Basket Size',          q: 'What is the average quantity and revenue per order?' },
      { label: 'Ratings vs Revenue',   q: 'Show a scatter plot of rating versus revenue' },
    ],
  },
  {
    key: 'marketing', label: 'Marketing', icon: Megaphone,
    blurb: 'Conversion, segments & channels',
    examples: [
      'Break down the data by segment',
      'Which channel or category performs best?',
      'Show conversion rates across groups',
      'Compare performance between segments',
    ],
    suggested: [
      { label: 'Segment Breakdown',    q: 'Break down totals by each categorical column' },
      { label: 'Best Performing',      q: 'Which category has the highest total? Show a ranked bar chart' },
      { label: 'Rate Analysis',        q: 'Show rates or proportions across the main categorical column' },
      { label: 'Segment Comparison',   q: 'Compare the mean numeric values across segments' },
    ],
  },
  {
    key: 'hr', label: 'HR', icon: Users,
    blurb: 'Attrition, tenure & demographics',
    examples: [
      'Show the distribution of age across the workforce',
      'Compare numeric features between groups',
      'What is the headcount by department or category?',
      'Show a correlation heatmap of the numeric columns',
    ],
    suggested: [
      { label: 'Headcount',            q: 'Show a bar chart of counts by the main categorical column' },
      { label: 'Demographics',         q: 'Plot the distribution of age across the dataset' },
      { label: 'Group Comparison',     q: 'Compare the mean of each numeric feature between groups' },
      { label: 'Pay / Value Equity',   q: 'Compare the average of the main numeric column across groups' },
    ],
  },
]

const catByKey = (key) => CATEGORIES.find((c) => c.key === key) || CATEGORIES[0]

const STEP_META = {
  analyzing: { icon: '🔍', color: '#4F46E5' },
  thinking:  { icon: '🧠', color: '#8B5CF6' },
  code:      { icon: '💻', color: '#06B6D4' },
  executing: { icon: '⚡', color: '#F59E0B' },
  done:      { icon: '✅', color: '#10B981' },
  error:     { icon: '⚠️', color: '#EF4444' },
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

function UploadScreen({ onUpload, uploading, setUploading, category, setCategory }) {
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
      </div>
    </div>
  )
}

// ─── Sidebar ───────────────────────────────────────────────────────────────────

function Sidebar({ upload, category, setCategory, onReset }) {
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

function InsightsPanel({ upload, category, onAsk, loading }) {
  const cat = catByKey(category)
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
  const cat = catByKey(msg.category)

  return (
    <div className="chat-msg">
      <div className="bubble-user"><p>{msg.question}</p></div>

      <div className={`bubble-agent ${isError ? 'is-error' : isDone ? 'is-done' : 'is-loading'}`}>
        <div className="agent-head">
          <Sparkles width={14} height={14} /> Analyst Agent
          <span className="agent-lens"><cat.icon width={11} height={11} /> {cat.label}</span>
        </div>

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

function ChatArea({ upload, category, messages, onAsk, loading, question, setQuestion, inputRef }) {
  const cat = catByKey(category)
  const bottomRef = useRef()
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  return (
    <main className="chat-area">
      {messages.length === 0 ? (
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
  const inputRef = useRef()

  const ask = useCallback(async (q) => {
    const text = (typeof q === 'string' ? q : question).trim()
    if (!text || !upload || loading) return
    setQuestion('')
    setLoading(true)

    const msgId = Date.now()
    setMessages((prev) => [...prev, { id: msgId, question: text, category, steps: [], code: null, result: null, chart: null }])

    try {
      const res = await fetch('/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: upload.session_id, question: text, category }),
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
  }, [question, upload, loading, category])

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
        />
      ) : (
        <div className="workspace">
          <Sidebar
            upload={upload}
            category={category}
            setCategory={setCategory}
            onReset={() => { setUpload(null); setMessages([]) }}
          />
          <ChatArea
            upload={upload}
            category={category}
            messages={messages}
            onAsk={ask}
            loading={loading}
            question={question}
            setQuestion={setQuestion}
            inputRef={inputRef}
          />
          <InsightsPanel upload={upload} category={category} onAsk={ask} loading={loading} />
        </div>
      )}
    </div>
  )
}
