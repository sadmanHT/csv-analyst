# CSV Analyst AI — Gemini Edition

A domain-aware AI data analyst that lets you upload a CSV and ask questions in plain English. Powered by **Google Gemini 2.0 Flash**, it writes and executes pandas/matplotlib code on your data in a secure sandbox, streams every step live, and renders publication-quality charts — no coding required.

Built for the **MLH Gemini Prize** track.

---

## Features

- **Natural language analysis** — ask any question; Gemini writes the pandas code, runs it, and narrates the result
- **Domain lenses** — switch between General, Financial, Medical, Retail, Marketing, and HR modes to get expert-framed answers
- **Instant overview dashboard** — correlation heatmap, distributions, and top-category charts auto-generated the moment your CSV loads (no LLM call)
- **Predictive ML** — train a Random Forest classifier or regressor on any column with one click; see feature importance and live inference on new cases
- **Paste data** — paste rows copied from Excel or Google Sheets directly, no file needed
- **Self-correcting agent** — if generated code fails, the agent automatically retries with the error context
- **Secure sandbox** — generated code runs in a whitelisted exec environment; `os`, `sys`, `subprocess` and friends are blocked
- **Streaming UI** — every agent step (analyze → think → code → execute → done) streamed live via SSE
- **24 pytest tests** covering upload, text paste, overview charts, sandbox, and the full ML predict flow

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Google Gemini 2.0 Flash (`google-genai`) |
| Backend | FastAPI + uvicorn |
| Data | pandas, numpy, matplotlib, seaborn, scikit-learn |
| Frontend | React 18 + Vite |
| Tests | pytest + FastAPI TestClient |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- A [Google AI Studio](https://aistudio.google.com/) API key

### 1. Clone and set up the backend

```bash
git clone https://github.com/sadmanHT/csv-analyst.git
cd csv-analyst/backend

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory:

```
GEMINI_API_KEY=your_api_key_here
```

### 2. Start the backend

```bash
uvicorn main:app --reload --port 8001
```

### 3. Start the frontend

```bash
cd ../frontend
npm install
npm run dev
```

Open [http://localhost:5174](http://localhost:5174) in your browser.

> The Vite dev server proxies `/upload`, `/query`, `/predict`, etc. to `localhost:8001` automatically.

---

## Usage

1. **Pick a lens** — choose General, Financial, Medical, Retail, Marketing, or HR
2. **Upload a CSV** — drag and drop, click to browse, or paste rows from Excel/Sheets
3. **Explore the overview** — instant charts appear as soon as your data loads
4. **Ask questions** — type in plain English; the agent writes code, runs it, and shows the chart
5. **Train a model** — click "Train & Predict" in the right panel, pick a target column
6. **Predict new cases** — after training, enter values in the inference form to get live predictions

### Sample dataset

A sample e-commerce CSV is included at `sample_data/ecommerce_sales.csv` to try right away.

---

## Running Tests

```bash
cd backend
pytest test_main.py -v
```

24 tests cover:
- CSV and text upload endpoints
- Instant overview chart generation
- Data profiling (missing values, duplicates, numeric stats)
- Sandbox security (blocked imports)
- Random Forest classifier and regressor training
- Full predict → model_info → predict_input flow
- Error cases (unknown session, bad target column, too few rows)

---

## Project Structure

```
csv-analyst/
├── backend/
│   ├── main.py           # FastAPI app, Gemini agent, sandbox, ML training
│   ├── test_main.py      # 24 pytest tests
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx       # React UI (upload, chat, insights panel, predict)
│       ├── App.css       # Styles
│       └── icons.jsx     # SVG icon components
├── sample_data/
│   └── ecommerce_sales.csv
└── AGENTS.md             # Agent behavior rules
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/upload` | Upload a CSV file |
| `POST` | `/upload_text` | Paste CSV/TSV rows as text |
| `POST` | `/query` | Ask a question (SSE stream) |
| `POST` | `/predict` | Train a Random Forest model (SSE stream) |
| `GET` | `/model_info/{session_id}` | Get trained model metadata |
| `POST` | `/predict_input` | Run inference on a new row |

---

## License

MIT
