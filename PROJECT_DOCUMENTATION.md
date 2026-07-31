# CSV Analyst AI - Project Documentation

## 1. Executive Summary

CSV Analyst AI is a production-minded, agentic data-analysis workbench for turning CSV data into decisions. It is not just a "chat with CSV" application. The product uploads tabular data, profiles it immediately, finds useful insights, runs transparent multi-step analyses, generates charts, validates results, trains explainable predictive models, simulates what-if scenarios, and exports reports.

The core product promise is:

> Upload a dataset and get a transparent AI analyst that investigates the data, explains what matters, validates its work, and helps the user decide what to do next.

The project is designed for a hackathon-grade demo while also moving toward production-grade reliability: deterministic analytics for common tasks, tested endpoints, sandboxed code execution, JSON/SSE API contracts, upload limits, rate limiting, structured observability metadata, visible answer trust badges, background job endpoints for heavy work, and CI checks. It is not yet production-scale because session state and the current job registry still live in process memory.

## 2. Problem Being Addressed

Most teams have CSVs but do not have immediate access to a data analyst. Business users often struggle with:

- Knowing which questions to ask.
- Understanding column meaning and data quality.
- Turning raw rows into charts, KPIs, and decisions.
- Trusting AI-generated answers.
- Moving from descriptive analysis to prediction and scenario planning.
- Creating shareable reports quickly.

Typical CSV chatbots answer one question at a time. They are reactive, opaque, and often depend entirely on a single LLM response.

CSV Analyst AI addresses this by acting like an analyst workspace:

- It proactively analyzes the dataset on upload.
- It runs deterministic analysis where possible.
- It streams visible analysis steps.
- It generates charts and reports.
- It explains confidence and validation evidence.
- It supports decision workflows like investigations, cleaning plans, dashboard blueprints, data contracts, prediction, and what-if simulation.

## 3. Target Users

Primary users:

- Hackathon judges evaluating AI usefulness and product completeness.
- Business analysts who need quick answers from CSVs.
- Founders and operators analyzing sales, users, revenue, marketing, or operations data.
- Students or researchers exploring datasets.
- Non-technical users who want charts and explanations without writing code.

Secondary users:

- Developers who want a reference architecture for an agentic analytics app.
- Data teams who want a starting point for trusted internal analytics tooling.

## 4. Product Positioning

CSV Analyst AI should be positioned as:

- An AI analyst, not a chatbot.
- A decision-intelligence workspace, not only a visualization tool.
- A transparent agent pipeline, not a hidden black-box answer generator.
- A production-minded prototype with tests and security controls.

Recommended one-line pitch:

> CSV Analyst AI turns any uploaded CSV into an analyst-grade briefing, dashboard blueprint, predictive model, and scenario simulator with transparent streamed reasoning.

## 5. Repository Structure

```text
csv-analyst-gemini/
  AGENTS.md
  README.md
  PROJECT_IMPROVEMENT_PLAN.md
  PROJECT_DOCUMENTATION.md
  sample_data/
    ecommerce_sales.csv
  backend/
    main.py
    sandbox_runner.py
    test_main.py
    benchmark.py
    requirements.txt
    Procfile
    railway.toml
  frontend/
    package.json
    package-lock.json
    index.html
    vercel.json
    vite.config.js
    src/
      main.jsx
      App.jsx
      App.css
      index.css
      icons.jsx
```

## 6. Technology Stack

Backend:

- FastAPI
- Uvicorn
- pandas
- numpy
- matplotlib
- seaborn
- Plotly
- SQLite
- scikit-learn
- SHAP
- Google Gemma 4 via the `google-genai` SDK
- Local HashingVectorizer retrieval for attached documents
- reportlab
- python-pptx
- pypdf
- openpyxl
- pytest

Frontend:

- React 18
- Vite
- Plotly.js loaded dynamically
- Custom CSS
- Local Vite proxy for backend API calls

Deployment:

- Railway backend config in `backend/railway.toml`
- Vercel frontend config in `frontend/vercel.json`

## 7. High-Level Architecture

```text
User
  |
  v
React + Vite Frontend
  |
  | REST JSON endpoints
  | SSE streaming endpoints
  v
FastAPI Backend
  |
  |-- In-memory session store
  |-- DataFrame profile and deterministic analytics
  |-- Gemma 4 multi-agent pipeline
  |-- Sandboxed pandas/Plotly code execution
  |-- SQLite query execution
  |-- Document vector store for RAG
  |-- Random Forest predictive modeling
  |-- Scenario simulation
  |-- Report generation
  v
JSON, SSE events, base64 exports, Plotly chart JSON
```

The frontend is a single-page analytics workspace. The backend owns all data processing, model training, document indexing, report generation, and API contracts.

## 8. Backend Architecture

Main backend file:

- `backend/main.py`

Supporting sandbox file:

- `backend/sandbox_runner.py`

Test file:

- `backend/test_main.py`

Backend state is currently in memory:

- `dataframes`: session ID to uploaded pandas DataFrame.
- `models`: session ID to trained model metadata.
- `doc_stores`: session ID to RAG document vector store.
- `conversation_state`: session-level last question/result/context.
- `query_cache`: deterministic or LLM query result cache.
- `session_meta`: creation and last-access metadata.
- `rate_limit_buckets`: in-memory request rate-limiting buckets.

This makes the current project simple and fast for hackathon/demo use, but it means sessions do not survive process restarts.

## 9. Frontend Architecture

Main frontend file:

- `frontend/src/App.jsx`

Main stylesheet:

- `frontend/src/App.css`

Icons:

- `frontend/src/icons.jsx`

Frontend layout:

- Top navigation.
- Upload screen.
- Sidebar with schema, documents, and preview.
- Main chat/analysis area.
- Right insights panel with actions and tools.
- Modals for paste-data and benchmark evaluation.

Important frontend components:

- `PasteModal`
- `DocUploadPanel`
- `PredictInputCard`
- `ScenarioSimulatorCard`
- `BenchmarkModal`
- `ExportCard`
- `InsightsPanel`
- `ValidationPanel`
- `ExplainPanel`
- `ChatArea`

Frontend API calls use relative paths through the Vite proxy in local development.

## 10. Core Data Flow

### Upload Flow

1. User uploads or pastes tabular data.
2. Backend reads and validates upload size and dataframe shape.
3. Backend stores the dataframe in memory.
4. Backend generates:
   - profile
   - preview rows
   - dtypes
   - numeric stats
   - overview charts
   - proactive insights
   - column roles
   - quality report
   - decision brief
   - cleaning plan
   - data contract
   - dashboard blueprint
   - decision actions
5. Frontend renders the workspace immediately.

### Query Flow

1. User asks a question.
2. Backend checks cache.
3. Backend attempts deterministic answer first.
4. If deterministic route cannot answer, backend runs the Gemma 4 agent pipeline.
5. Response streams as Server-Sent Events.
6. Frontend renders each step, chart, validation panel, and report.

### Investigation Flow

1. User clicks "Investigate" on a decision action.
2. Backend streams an autonomous investigation.
3. Investigation computes evidence from:
   - profile
   - trend
   - segment drivers
   - anomalies
   - correlations
   - quality issues
   - persona-specific priorities
4. Frontend renders the investigation as an analyst brief.

### Prediction and Simulation Flow

1. User trains a Random Forest model for a target column.
2. Backend stores model metadata for the session.
3. User predicts a new case or runs a scenario.
4. Scenario simulator compares baseline prediction vs changed input prediction.
5. Frontend shows impact and chart.

## 11. Major Features

### 11.1 CSV Upload

Endpoint:

- `POST /upload`

Supports CSV file upload. The backend returns JSON with session ID, schema metadata, preview rows, overview charts, proactive insights, decision brief, quality report, cleaning plan, data contract, dashboard spec, and decision actions.

### 11.2 Paste Data

Endpoint:

- `POST /upload_text`

Allows users to paste CSV or TSV content from spreadsheets.

### 11.3 RAG Document Upload

Endpoints:

- `POST /upload_doc`
- `GET /docs/{session_id}`

Users can upload supporting documentation such as PDFs, Excel files, Markdown, text, or CSV documentation. The backend parses, chunks, embeds, and stores document chunks for retrieval during LLM analysis.

### 11.4 Instant Dataset Profile

The backend computes:

- row count
- column count
- dtypes
- numeric stats
- missing-value totals
- duplicate rows
- preview rows
- overview charts

This gives immediate value without requiring the LLM.

### 11.5 Proactive Insights

The app surfaces useful findings immediately after upload. These may include:

- dataset size
- top metric signals
- top segment breakdowns
- missing data warnings
- duplicate warnings
- correlation highlights

Purpose:

- Prevent blank-state confusion.
- Help users know what questions to ask.
- Make the product feel like an analyst that has already started working.

### 11.6 Column Role Inference

The backend infers semantic column roles:

- metrics
- numeric columns
- time columns
- dimensions
- IDs
- target candidates

This drives deterministic charting, dashboard blueprints, follow-ups, decision briefs, and investigations.

### 11.7 Deterministic Analytics

Common queries are answered deterministically when possible; Gemma 4 is used for planning or grounded wording when needed.

Supported examples:

- dataset shape
- missing values
- duplicate count
- numeric summary
- correlation heatmap
- distribution chart
- category counts
- group-by metric analysis
- follow-up split using conversation memory

Benefits:

- More reliable than pure LLM output.
- Faster responses.
- Lower cost.
- Easier to test.

### 11.8 Multi-Agent Query Pipeline

Endpoint:

- `POST /query`

For questions that are not handled deterministically, the system runs an agent pipeline:

1. Planner
2. Analyst
3. SQL Analyst when appropriate
4. Visualizer
5. Critic
6. Reporter

The endpoint streams SSE events such as:

- analyzing
- planning
- plan
- analyst
- code
- executing
- visualizing
- critiquing
- critique
- reporting
- done
- error

Every SSE event includes observability metadata:

- request ID
- endpoint
- session ID
- sequence number
- elapsed milliseconds

### 11.9 Interactive Charts

The app supports:

- Plotly JSON charts for interactive frontend rendering.
- Matplotlib/seaborn PNG charts for static outputs.
- Base64-encoded chart payloads where needed.

Chart types include:

- bar
- line
- scatter
- histogram
- box plot
- heatmap
- feature importance
- SHAP summary
- permutation importance
- partial dependence

### 11.10 Fact-First Dataset Story

Endpoint:

- `POST /story`

The dataset story is generated from deterministic facts before narrative wording. It uses:

- profile facts
- quality facts
- top breakdowns
- relationships
- inferred roles

Purpose:

- Avoid unsupported storytelling.
- Give an executive narrative grounded in computed evidence.

### 11.11 Autonomous Investigation

Endpoint:

- `POST /investigate`

This is one of the most important product upgrades. Instead of asking one question, the system runs a goal-driven investigation.

Investigation includes:

- goal scoping
- investigation tree
- persona lens
- trend scan
- segment driver scan
- anomaly scan
- correlation scan
- quality risk scan
- recommended actions
- validation metadata
- chart JSON

Supported persona lenses:

- General / Analytics Lead
- Financial / CFO
- Healthcare Analyst
- Retail Operator
- Marketing / Growth Strategist
- HR / People Analytics Lead

This moves the product from "CSV chatbot" toward "AI consultant."

### 11.12 Decision Brief

Endpoint:

- `GET /brief/{session_id}`

The decision brief summarizes:

- readiness score
- readiness label
- best use cases
- blocked use cases
- priority questions
- next actions
- risk flags
- automation opportunities
- column dictionary
- decision actions

Purpose:

- Tell the user what the dataset is good for.
- Make business value visible immediately.

### 11.13 Decision Actions

Decision actions are generated from deterministic evidence.

Each action may include:

- title
- priority
- implication
- recommended action
- estimated impact
- confidence
- evidence
- risks and assumptions
- supporting columns
- suggested investigation question

Frontend buttons launch autonomous investigations from these actions.

### 11.14 Data Quality Report

Endpoint:

- `GET /quality/{session_id}`

The quality report includes:

- score
- status
- summary
- issues
- severity levels
- affected columns
- recommended fixes

### 11.15 Cleaning Plan and Cleaned Export

Endpoints:

- `GET /cleaning_plan/{session_id}`
- `POST /clean/{session_id}`

The cleaning plan recommends conservative actions such as:

- remove duplicate rows
- drop empty columns
- trim whitespace
- fill missing numeric values with median
- fill missing categorical values with mode

The clean endpoint returns a JSON response with a base64 CSV payload, not raw binary.

### 11.16 Data Contract

Endpoints:

- `GET /contract/{session_id}`
- `POST /validate_rows/{session_id}`

The data contract contains:

- column names
- portable types
- inferred roles
- required columns
- constraints
- validation policy
- version

The validation endpoint checks new rows against the inferred contract.

Purpose:

- Help turn an uploaded CSV into a repeatable pipeline interface.
- Support downstream automation and data quality checks.

### 11.17 Dashboard Blueprint

Endpoint:

- `GET /dashboard/{session_id}`

The dashboard blueprint recommends:

- KPI cards
- chart specs
- filters
- layout sections
- starter questions
- data requirements
- quality notes

Purpose:

- Help the user turn ad hoc analysis into a dashboard plan.

### 11.18 Predictive Modeling

Endpoint:

- `POST /predict`
- `POST /predict_job`
- `GET /jobs/{job_id}`

The backend trains a Random Forest model for a selected target column.

Supports:

- classification
- regression
- numeric feature preprocessing
- low-cardinality categorical encoding
- train/test split
- feature importance
- SHAP chart
- permutation importance chart
- partial dependence chart

The model is stored in memory for the session.

`/predict` streams training progress through SSE. `/predict_job` queues the same training work in a background task and returns a polling URL, reducing the chance that a long model-training request times out during demos or shared use.

### 11.19 Predict a New Case

Endpoints:

- `GET /model_info/{session_id}`
- `POST /predict_input`

After training, the frontend displays a form for predicting a new row.

`model_info` returns:

- target
- model type
- feature metadata
- defaults
- category options

`predict_input` returns:

- target
- prediction
- confidence for classification
- task type

### 11.20 Scenario Simulation

Endpoint:

- `POST /simulate`

Scenario simulation compares a baseline prediction against a changed input.

Supported change modes:

- set value
- add/subtract delta
- percent change

Returns:

- baseline values
- scenario values
- applied changes
- baseline prediction
- scenario prediction
- impact metadata
- chart JSON
- validation note

Purpose:

- Move from "what predicts this?" to "what happens if we change this?"
- Help users reason about business actions.

### 11.21 Natural-Language Scenario Parsing

Endpoint:

- `POST /scenario_parse`

Parses prompts such as:

- `increase discount by 10%`
- `decrease price by 5`
- `set region to Dhaka`

The parser maps explicit prompts to:

- feature
- mode
- value
- confidence
- interpretation
- candidates

It is deterministic and avoids guessing when the prompt is ambiguous.

### 11.22 Report Export

Endpoint:

- `POST /report/{session_id}?format=pdf`
- `POST /report/{session_id}?format=pptx`
- `POST /report_job/{session_id}?format=pdf`
- `POST /report_job/{session_id}?format=pptx`
- `GET /jobs/{job_id}`

Exports reports as JSON/base64 payloads.

Report content can include:

- dataset profile
- questions and answers
- charts
- validation
- critique
- predictive model visuals

The direct report endpoint is still available for compatibility. The job endpoint queues report generation and returns a polling URL.

### 11.23 Benchmark Evaluation

Endpoint:

- `GET /benchmark/{session_id}`
- `POST /benchmark_job/{session_id}`
- `GET /jobs/{job_id}`

CLI:

- `backend/benchmark.py`

Benchmark metrics include:

- success rate
- chart rate
- SQL routing accuracy
- repair success
- average response time

Purpose:

- Demonstrate reliability.
- Provide a quantitative demo artifact.
- Avoid tying longer benchmark runs to a single blocking request when the job endpoint is used.

### 11.24 Background Job Polling

Endpoint:

- `GET /jobs/{job_id}`

Background job records include:

- job ID
- kind
- session ID
- status
- created timestamp
- updated timestamp
- result
- error

Supported job kinds:

- predict
- report
- benchmark

Current statuses:

- queued
- running
- completed
- failed

## 12. API Reference

| Method | Endpoint | Response Type | Purpose |
|---|---|---|---|
| GET | `/health` | JSON | Health check |
| POST | `/upload` | JSON | Upload CSV |
| POST | `/upload_text` | JSON | Paste CSV/TSV text |
| POST | `/upload_doc` | JSON | Upload supporting docs for RAG |
| GET | `/docs/{session_id}` | JSON | List indexed docs |
| GET | `/quality/{session_id}` | JSON | Data quality report |
| GET | `/brief/{session_id}` | JSON | Decision brief |
| GET | `/cleaning_plan/{session_id}` | JSON | Cleaning recommendations |
| POST | `/clean/{session_id}` | JSON/base64 | Cleaned CSV export |
| GET | `/contract/{session_id}` | JSON | Inferred data contract |
| POST | `/validate_rows/{session_id}` | JSON | Validate rows against contract |
| GET | `/dashboard/{session_id}` | JSON | Dashboard blueprint |
| POST | `/investigate` | SSE | Autonomous investigation |
| POST | `/query` | SSE | Ask an analytics question |
| POST | `/story` | SSE | Fact-first dataset story |
| POST | `/predict` | SSE | Train predictive model |
| POST | `/predict_job` | JSON | Queue predictive model training |
| GET | `/model_info/{session_id}` | JSON | Model metadata |
| POST | `/predict_input` | JSON | Predict a new row |
| POST | `/simulate` | JSON | What-if scenario simulation |
| POST | `/scenario_parse` | JSON | Natural-language scenario parser |
| POST | `/report/{session_id}` | JSON/base64 | PDF/PPTX export |
| POST | `/report_job/{session_id}` | JSON | Queue PDF/PPTX export |
| GET | `/benchmark/{session_id}` | JSON | Benchmark evaluation |
| POST | `/benchmark_job/{session_id}` | JSON | Queue benchmark evaluation |
| GET | `/jobs/{job_id}` | JSON | Poll background job status |

## 13. Security and Reliability Controls

Current controls:

- Environment variables for secrets.
- No hardcoded Gemma/Gemini API key.
- Upload byte limit.
- Dataframe row and column limits.
- Session TTL cleanup.
- Maximum session count.
- Bounded query cache.
- In-memory rate limiting with JSON 429 responses.
- CORS remains open for local development.
- SQL validation blocks:
  - non-SELECT statements
  - multiple statements
  - mutation keywords
  - comments that may hide unsafe content
- Generated code validation blocks:
  - unsafe imports
  - dangerous calls such as `eval`, `exec`, `compile`, `open`
  - dunder and frame-introspection attributes
- Generated code execution is process-isolated through `backend/sandbox_runner.py`.
- SSE events include request tracing metadata.
- Report exports return JSON/base64 instead of raw binary.
- Frontend answer headers show route/trust badges so users can distinguish deterministic, autonomous, cached, and AI-agent responses.
- Background job endpoints exist for model training, report generation, and benchmark evaluation.

## 14. Production Readiness Boundary

The project is production-minded, but not yet production-scale.

What is production-minded today:

- API responses use JSON or SSE contracts.
- Common analytics paths are deterministic and tested.
- Generated code execution is isolated in a subprocess.
- SQL execution is read-only and validated.
- Upload size and dataframe shape are limited.
- Sessions expire after a configurable TTL.
- Rate limiting exists.
- Request IDs and timing metadata are streamed with SSE events.
- Backend tests and frontend build are covered by a GitHub Actions CI workflow.
- Model training, report export, and benchmark evaluation have background job endpoints with polling.

What is not production-scale yet:

- Uploaded dataframes, trained models, document stores, conversation memory, cache, and rate limits are still in process memory.
- A backend restart or redeploy clears active sessions.
- Multiple workers would not share session state.
- Background jobs are tracked in memory, not in a durable queue.
- The original direct model/report/benchmark endpoints still execute inside request handling for compatibility.
- Authentication and signed session tokens are not implemented.
- Deployed CORS should be locked to a specific frontend origin through `ALLOWED_ORIGINS`.

Recommended path to production scale:

1. Add persistent session storage with SQLite-on-disk, Redis, S3-compatible object storage, or a small database-backed repository layer.
2. Move the in-memory job registry to a persistent queue or database-backed job table.
3. Add session-scoped access tokens.
4. Lock CORS in deployed environments.
5. Add frontend component tests for the prediction and scenario workflows.

## 15. Testing Status

Backend tests:

```bash
pytest backend/
```

Current status:

- 89 backend tests passing.

Covered areas include:

- upload
- paste upload
- document upload
- docs listing
- profile generation
- overview chart generation
- quality endpoint
- decision brief endpoint
- cleaning plan
- cleaned CSV export
- data contract
- row validation
- dashboard blueprint
- deterministic query route
- story SSE endpoint
- investigation SSE endpoint
- report export
- benchmark endpoint
- sandbox AST security
- SQL validation
- predictive model training
- predict input
- scenario simulation
- scenario parsing
- background job polling
- queued prediction jobs
- queued report jobs
- queued benchmark jobs
- missing-session and bad-input errors

Frontend build:

```bash
cd frontend
npm run build
```

Current status:

- Build passes.
- Vite still warns about the large Plotly chunk. This is expected because Plotly is a large visualization dependency, although it is dynamically loaded.

## 16. Local Development Commands

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5174
```

Required backend environment variable:

```text
GEMINI_API_KEY=your_google_gemini_api_key
```

Optional production/local environment variables:

```text
ALLOWED_ORIGINS=*
MAX_UPLOAD_BYTES=26214400
MAX_DATAFRAME_ROWS=100000
MAX_DATAFRAME_COLUMNS=200
SESSION_TTL_SECONDS=14400
MAX_SESSIONS=50
MAX_QUERY_CACHE_ENTRIES=200
RATE_LIMIT_MAX_REQUESTS=600
RATE_LIMIT_WINDOW_SECONDS=60
```

## 17. Frontend Proxy Routes

Local frontend API calls go through Vite proxy routes in:

- `frontend/vite.config.js`

This avoids hardcoded backend ports in the React app and follows the project rule that frontend calls should use proxy paths such as `/upload`, `/query`, `/simulate`, and `/scenario_parse`.

## 18. Deployment

Backend:

- Deploy `backend/` to Railway.
- Configure `GEMINI_API_KEY`.
- Configure `ALLOWED_ORIGINS` for the deployed frontend domain.

Frontend:

- Deploy `frontend/` to Vercel.
- Configure `VITE_API_BASE_URL` to point at the Railway backend URL.

## 19. Demo Flow

Recommended demo:

1. Upload `sample_data/ecommerce_sales.csv`.
2. Show instant overview, proactive insights, decision brief, quality report, and decision actions.
3. Click a decision action's "Investigate" button.
4. Show the streamed autonomous investigation.
5. Ask a deterministic query such as revenue by category.
6. Generate a fact-first dataset story.
7. Train a predictive model for a target column.
8. Show feature importance, SHAP, permutation importance, and PDP.
9. Use "Predict a New Case."
10. Run the Scenario Simulator.
11. Type a natural-language what-if prompt and prefill the scenario controls.
12. Export PDF or PPTX report.
13. Run benchmark evaluation if time allows.

## 20. Architecture & Deployment Notes

Single-Instance vs Multi-Replica Storage:

- Sessions and jobs are stored on disk using SQLite (`backend/data/storage.db`) and Parquet files (`backend/data/sessions/`). This provides robust, restart-safe durability for single-instance deployments (such as Railway or single-container instances).
- If scaling horizontally across multiple stateless backend worker replicas, the state layer can be upgraded from disk-backed SQLite/Parquet to Redis (for sessions, cache, and job queues) + S3/Object Storage (for Parquet files and reports).

## 21. Current Limitations

Known limitations:

- Storage is currently single-instance disk/SQLite (multi-replica scale-out would require Redis + Object Storage).
- RAG is per-session and in-memory.
- Scenario simulation is predictive, not causal.
- Natural-language scenario parsing is deterministic and intentionally conservative.
- Plotly remains a large frontend bundle dependency.

Recommended one-line pitch:

> CSV Analyst AI is the AI Data Analyst for Spreadsheets & Relational Datasets: Profile, Join, Investigate, Forecast, Predict, & Compare.

---

## 22. Verification & Security Controls

- **SSRF Security Protection**: `/import_url` strictly enforces domain allowlisting (`docs.google.com` / `drive.google.com`) and resolves hostnames to block private IP CIDR ranges (`10.*`, `172.16-31.*`, `192.168.*`, `127.*`) and cloud metadata targets (`169.254.169.254`).
- **Backend Test Suite**: **105 passing pytest tests** covering API routes, AST security filters, SSRF URL guards, SQL validation, predictive modeling, time-series forecasting, relational join inference, dataset drift comparison, report export, session persistence, and startup orphan job recovery.
- **Frontend Test Suite**: **7 Vitest + React Testing Library unit tests** (`npm test`) covering key interactive components (`ScenarioSimulatorCard`, `PredictInputCard`, `TimeSeriesForecastCard`).
- **CI Workflow**: GitHub Actions workflow (`.github/workflows/ci.yml`) automatically executes `pytest backend/`, `npm test` in `frontend/`, and `npm run build` on every push.

## 22. Why This Is Strong for a Hackathon

The project has a strong judging story because it combines:

- immediate value after upload
- visible AI reasoning
- deterministic reliability
- interactive visualizations
- autonomous investigations
- explainable ML
- scenario simulation
- report export
- benchmark evaluation
- real tests and production hardening

The strongest framing is:

> Most CSV tools answer questions. CSV Analyst AI runs an analyst workflow: it profiles, investigates, validates, predicts, simulates, and reports.
