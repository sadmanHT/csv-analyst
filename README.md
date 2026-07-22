# CSV Analyst AI — The AI Analyst for Spreadsheets & Relational Data

> **Powered by Google Gemini 2.5 Flash-Lite · Built for the MLH Gemini Prize**

A production-grade AI data analyst for spreadsheets and relational datasets. Upload CSV, Excel (`.xlsx`), Parquet, or JSON files (or paste a Google Sheets URL), ask questions in plain English, and a **multi-agent pipeline** reasons over your data like a senior analyst — profiling, joining, forecasting, predicting, critiquing, and exporting reports.

---

## What Makes This Different

| Feature | Most Data Chatbots | CSV Analyst AI |
|---|---|---|
| Ingestion | Single CSV only | CSV, Excel (`.xlsx` multi-sheet), Parquet, JSON/JSONL, Google Sheets URL |
| Relational Support | Single file only | Multi-file join key inference & dataset merging |
| Architecture | Single LLM call | 5-agent pipeline (Planner → Analyst → Visualizer → Critic → Reporter) |
| Time-Series | None | Holt-Winters exponential smoothing + 95% confidence bounds |
| ML & What-If | None | Random Forest + SHAP + 90% prediction bounds + scenario simulator |
| Drift Analysis | None | Dataset v1 vs v2 schema diffing & numeric distribution shift detection |
| Security | Basic or `exec()` | AST scan + 40-builtin sandbox + SQLite/Parquet storage + **SSRF URL guard** |
| Export | None | PDF (reportlab) + PPTX (python-pptx) with all charts |
| Tests & Reliability | 0 tests | **105 backend pytest tests** + **7 Vitest frontend component tests** |

---

## Key Capabilities

### 1. Multi-Format & URL Ingestion
- **Formats**: Direct parsing for `.csv`, `.xlsx` (multi-sheet), `.xls`, `.parquet`, `.json`, `.jsonl`.
- **Google Sheets Import**: Paste public Google Sheets sharing URLs to import and profile dataset sessions directly.
- **SSRF Security Guard**: `/import_url` strictly validates URLs against Google domains (`docs.google.com`) and resolves hostnames to block private IP addresses, loopback, and cloud metadata targets (`169.254.169.254`).

### 2. Multi-Table Relational Join Inference
- **Automated Join Key Detection**: Ranks foreign key pairs (`customer_id`, `product_id`, matching columns) and value overlap ratios (`High`, `Medium`, `Low`).
- **Dataset Merging**: Joins datasets (`inner`, `left`, `right`, `outer`) into a unified, profiled session payload for downstream investigation.

### 3. Time-Series Trend Forecasting
- **Holt-Winters Smoothing**: Fits `ExponentialSmoothing` (with automatic linear fallback) to extrapolate future trends.
- **Uncertainty Bounds**: Generates 95% confidence intervals (`lower_95`, `upper_95`) and computes trend direction and growth metrics.

### 4. Dataset Comparison & Distribution Drift
- **Schema Diffing**: Detects added, removed, and type-changed columns between dataset v1 and v2.
- **Distribution Shift**: Ranks numeric columns by statistical drift level (`Significant`, `Moderate`, `Low`).

### 5. Multi-Agent Pipeline & Explainable ML
- **5 Chained Gemini Agents**: Planner → Analyst → Visualizer → Critic → Reporter.
- **Explainable ML**: Random Forest with SHAP beeswarm, permutation importance, PDP, and scenario simulator.

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Gemini 2.5 Flash-Lite (`google-genai`) |
| Embeddings | Gemini `text-embedding-004` |
| Backend | FastAPI + uvicorn |
| Data & Parsers | pandas, numpy, openpyxl, pyarrow, statsmodels |
| ML & Forecasting | scikit-learn (Random Forest), Holt-Winters Exponential Smoothing |
| Explainability | SHAP, sklearn.inspection |
| Charts | Plotly (interactive) + matplotlib/seaborn |
| Security | AST Scanner, Restricted Builtins, SSRF Domain/IP Filter |
| Tests | **105 pytest tests** (backend) + **7 Vitest tests** (frontend) |

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
