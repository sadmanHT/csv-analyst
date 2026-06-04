# CSV Analyst AI — Agentic Data Scientist

> **Powered by Google Gemini 2.5 Flash-Lite · Built for the MLH Gemini Prize**

A production-grade, domain-aware AI data analyst. Upload a CSV (or paste rows from Excel/Sheets), ask questions in plain English, and a **multi-agent pipeline** reasons over your data like a senior analyst — planning, computing, visualising, critiquing, and reporting.

---

## What Makes This Different

| Feature | Most CSV chatbots | This project |
|---|---|---|
| Architecture | Single LLM call | 5-agent pipeline (Planner → Analyst → Visualizer → Critic → Reporter) |
| Charts | Static PNG | Interactive Plotly (zoom, hover, pan) |
| ML | None | Random Forest + SHAP + Permutation Importance + PDP |
| SQL | Never | Planner auto-routes to SQLite when appropriate |
| RAG | None | Gemini embeddings over uploaded PDFs / Excel docs |
| Security | `exec()` sandbox | AST scan + restricted builtins + 30s timeout |
| Export | None | PDF (reportlab) + PPTX (python-pptx) with all charts |
| Evaluation | None | 49-question benchmark suite with live metrics dashboard |

---

## Features

### Multi-Agent Pipeline
Every question runs through 5 chained Gemini agents:
1. **Planner** — maps the question to relevant columns, picks analysis strategy and chart type, decides pandas vs SQL
2. **Analyst** — writes and executes pandas code for numerical findings (with self-repair on failure)
3. **Visualizer** — generates interactive Plotly charts (bar, line, scatter, histogram, heatmap, box…)
4. **Critic** — reviews statistical soundness, returns `pass/warn/fail` verdict + confidence score + issues
5. **Reporter** — writes a structured executive summary (Headline · Key Findings · Implication · Caveat)

### Domain Lenses
6 expert modes that change how the agent reasons: **General · Financial · Medical · Retail · Marketing · HR**

### RAG over Documentation
Upload PDFs, Excel files, or data dictionaries alongside your CSV. Gemini `text-embedding-004` indexes them into a per-session vector store (numpy cosine similarity). Relevant chunks are retrieved and injected into the Planner and Analyst prompts.

### Explainable ML
One-click Random Forest training with full explainability:
- **SHAP beeswarm** — global feature impact with directionality
- **Permutation importance** — statistically robust, test-set importance with error bars
- **Partial Dependence Plots** — how the top 2 features affect the prediction
- Live inference form for predicting new cases

### SQL Generation
The Planner automatically routes filter/group-by/top-N questions to a SQL agent that generates SQLite queries run against an in-memory database.

### Instant Overview Dashboard
Auto-generated correlation heatmap + distribution plots + top-category chart the moment a CSV loads — zero LLM calls.

### Secure Sandbox (3 Layers)
1. **AST scan** — blocks `__class__`, `__globals__`, `eval`, `exec`, `compile`, `open`, `subprocess` before execution
2. **Restricted namespace** — `__builtins__` replaced with a 40-entry whitelist
3. **Thread timeout** — hard 30-second wall-clock limit via `ThreadPoolExecutor`

### Export
- **PDF** — cover page, dataset profile table, numeric stats, per-message sections with charts, SHAP plots, critique verdicts
- **PPTX** — branded title slide, KPI card slide, one slide per message with chart + summary

### Benchmark Evaluation
49-question suite across 8 domains. Metrics: success rate, chart rate, SQL routing accuracy, repair rate, avg response time. Run from the UI or CLI:
```bash
python benchmark.py --csv data.csv --n 30 --out results.json
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Gemini 2.5 Flash-Lite (`google-genai`) |
| Embeddings | Gemini `text-embedding-004` |
| Backend | FastAPI + uvicorn |
| Data | pandas, numpy, matplotlib, seaborn |
| ML | scikit-learn (Random Forest) |
| Explainability | SHAP, sklearn.inspection |
| Charts | Plotly (interactive) + matplotlib/seaborn (static) |
| SQL | SQLite (stdlib) |
| RAG | numpy cosine similarity |
| PDF export | reportlab |
| PPTX export | python-pptx |
| Chart → image | kaleido |
| Doc parsing | pypdf, openpyxl |
| Frontend | React 18 + Vite |
| Tests | pytest + FastAPI TestClient (42 tests) |

---

## Quick Start (Local)

### Prerequisites
- Python 3.11+, Node.js 18+
- A [Google AI Studio](https://aistudio.google.com/) API key

### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

Create `backend/.env`:
```
GEMINI_API_KEY=your_key_here
```

```bash
uvicorn main:app --reload --port 8001
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5174**

---

## Deploy to Production

### Backend → Railway

1. New project at [railway.app](https://railway.app) → GitHub repo → **Root Directory: `backend/`**
2. Railway auto-detects Python via `railway.toml` (included)
3. Add environment variables in Railway dashboard:
   ```
   GEMINI_API_KEY=your_key_here
   ALLOWED_ORIGINS=https://your-app.vercel.app
   ```
4. Copy your Railway public URL

### Frontend → Vercel

1. Import repo at [vercel.com/new](https://vercel.com/new) → **Root Directory: `frontend/`**
2. Add environment variable:
   ```
   VITE_API_BASE_URL=https://your-railway-url.up.railway.app
   ```
3. Deploy — `frontend/vercel.json` is picked up automatically

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/upload` | Upload CSV file |
| `POST` | `/upload_text` | Paste CSV/TSV rows |
| `POST` | `/upload_doc?session_id=` | Upload PDF/Excel for RAG |
| `POST` | `/query` | Ask a question (SSE stream) |
| `POST` | `/predict` | Train RF + SHAP (SSE stream) |
| `GET` | `/model_info/{id}` | Trained model metadata |
| `POST` | `/predict_input` | Inference on a new row |
| `POST` | `/report/{id}?format=pdf\|pptx` | Generate business report |
| `GET` | `/benchmark/{id}?n=15` | Run benchmark suite |

Full Swagger UI at `/docs`.

---

## Tests

```bash
cd backend && pytest test_main.py -v
```

42 tests covering: upload, RAG, sandbox security (AST blocks `eval`/`exec`/dunders), Plotly charts, SQL generation, ML training, full predict flow, error cases.

---

## CV Bullet

> **Agentic Data Scientist (Gemini 2.5 Flash-Lite)** — Autonomous data-analysis platform with multi-agent reasoning (Planner→Analyst→Visualizer→Critic→Reporter), interactive Plotly charts, RAG via Gemini embeddings, explainable ML (SHAP + permutation importance + PDP), SQL auto-generation, 3-layer AST security sandbox, PDF/PPTX export, and a 49-question benchmark evaluation suite.

---

## License

MIT
