# CSV Analyst AI — Autonomous Data Science Workbench for Emerging Economies

> **Powered Exclusively by Google Gemma 4 (`gemma-4-31b-it`)**

A production-grade AI data analyst for spreadsheets and relational datasets. Upload CSV, Excel (`.xlsx`), Parquet, or JSON files (or paste a Google Sheets URL), ask questions in plain English, and a **Gemma 4 multi-agent pipeline** reasons over your data like a senior analyst — profiling, joining, forecasting, predicting, critiquing, and exporting reports.

---

## Tech Stack & Gemma 4 Integration

| Layer | Technology |
|---|---|
| Core LLM | **Google Gemma 4 (`gemma-4-31b-it`) via `google-genai` SDK** |
| Embeddings | Pure Local `sklearn.feature_extraction.text.HashingVectorizer` (Zero External LLM API calls) |
| Backend | FastAPI + uvicorn |
| Data & Parsers | pandas, numpy, openpyxl, pyarrow, statsmodels |
| ML & Forecasting | scikit-learn (Random Forest), Holt-Winters Exponential Smoothing |
| Explainability | SHAP, sklearn.inspection |
| Charts | Plotly (interactive) + matplotlib/seaborn |
| Security | AST Scanner, Restricted Builtins, DNS IP-Pinning Guard, Session Token Auth |
| Tests | **110+ pytest tests** (backend) + **7 Vitest tests** (frontend) |

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
