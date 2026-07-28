# CSV Analyst AI — Autonomous Data Science Workbench for Emerging Economies

## 1. Problem Statement & Real-World Impact
In developing economies like Bangladesh, non-technical small and medium enterprises (SMEs), educational institutions, healthcare providers, and local NGOs generate vast operational data stored in spreadsheets (CSV/Excel). However, over 92% of these organizations lack dedicated data science teams or access to expensive business intelligence tools. Key decisions regarding inventory turnover, financial cash flow, patient admission trends, and marketing campaign ROI are frequently made using intuition rather than empirical data.

**CSV Analyst AI** bridges this gap by turning raw tabular datasets into actionable, executive-ready intelligence using natural language. Built specifically to democratize data analytics, the workbench allows non-technical users in low-resource settings to upload raw datasets, run natural language queries, execute predictive forecasting, simulate "what-if" business scenarios, and generate executive PDF/PPTX briefs in seconds — without writing a single line of code.

---

## 2. Solution Overview
CSV Analyst AI is an autonomous, agentic data scientist powered **exclusively by Gemma 4 (`gemma-4-31b-it`)**. Rather than relying on simple text prompting, the application deploys a coordinated multi-agent orchestration pipeline that plans, writes sandboxed code, validates results, generates visualization charts, and synthesizes executive business narratives.

### Core Capabilities:
- **Autonomous Data Investigation (`/investigate`)**: Deep exploration of data quality, key driver correlations, distributions, and actionable recommendations through custom **Persona Lenses** (Financial/CFO, Retail/Operations, Clinical/Medical, Marketing/CMO, HR/People).
- **Fact-First Executive Storytelling (`/story`)**: Transforms tabular data into structured executive briefs using a deterministic fact-first streaming pipeline.
- **Predictive ML & What-If Simulation (`/predict`, `/simulate`)**: Automatically trains decision models, outputs SHAP/PDP feature importance charts, and allows users to simulate counterfactual business scenarios (e.g., *"What if advertising spend increases by 15%?"*).
- **Time-Series Forecasting (`/forecast`)**: Automated trend decomposition and 95% confidence interval modeling for financial and demand series.
- **Relational Joins & Drift Analysis (`/join`, `/compare`)**: Automatically infers foreign keys across multi-file datasets and detects schema drift and distribution shifts between dataset versions.

---

## 3. How Gemma 4 is Specifically Integrated
Gemma 4 serves as the primary brain across all stages of the analytical lifecycle. Every agent in the multi-agent pipeline is powered by `gemma-4-31b-it`:

```
                               ┌───────────────────────────────────┐
                               │     Gemma 4 (gemma-4-31b-it)      │
                               └─────────────────┬─────────────────┘
                                                 │
      ┌──────────────────┬───────────────────────┼───────────────────────┬──────────────────┐
      ▼                  ▼                       ▼                       ▼                  ▼
┌───────────┐   ┌─────────────────┐   ┌─────────────────────┐   ┌─────────────────┐   ┌───────────┐
│  Planner  │   │  Analyst Agent  │   │ Visualizer Agent    │   │  Critic Agent   │   │ Reporter  │
│  Agent    │   │ (Pandas / SQL)  │   │ (Seaborn / Plotly)  │   │ (Self-Correction│   │  Agent    │
└───────────┘   └─────────────────┘   └─────────────────────┘   └─────────────────┘   └───────────┘
```

1. **Planner Agent**: Parses user intent, analyzes the dataset schema profile, and generates a structured multi-step analytical plan.
2. **Analyst Agent**: Translates analytical steps into executable Pandas Python code or DuckDB SQL queries tailored to dataset column types.
3. **Visualizer Agent**: Selects harmonious color palettes and generates Plotly/Seaborn interactive chart objects returned as Base64 SSE streams.
4. **Critic Agent**: Inspects execution outputs for statistical anomalies, missing values, or potential hallucinated claims before presenting results.
5. **Reporter Agent**: Synthesizes complex analytical results into executive-ready markdown and structured slide decks customized to the selected persona lens.

---

## 4. System Architecture & Technical Stack

### Backend Infrastructure
- **Core LLM Engine**: Google AI Studio API serving **Gemma 4 (`gemma-4-31b-it`)**.
- **Embedding & Vector Store**: Pure local `sklearn.feature_extraction.text.HashingVectorizer` (768-dimensional normalized vectors) providing zero-latency, zero-cost RAG over attached policy documents without external LLM embedding calls.
- **Sandboxed Execution Sandbox**: Isolated Python process execution environment enforced by an `ast.NodeVisitor` security scanner (`_ASTSecurityVisitor`) blocking unauthorized builtins (`eval`, `exec`, `__import__`, `getattr`, `to_csv`, `read_csv`).
- **REST & SSE API**: FastAPI server providing real-time Server-Sent Events (SSE) for transparent agent observability.

### Frontend Application
- **Interface**: React 18 with Vite, styled using a high-contrast Vanilla CSS design system with HSL dynamic tokens, glassmorphism modals, and responsive layout grids.
- **Observability**: Live multi-agent execution step monitor showing agent thought chains, generated code snippets, and execution metrics.

---

## 5. Technical Challenges & Migration Learnings

### Migrating to Gemma 4 Structured Outputs
Transitioning the multi-agent pipeline from Gemini to Gemma 4 (`gemma-4-31b-it`) required tuning prompt contracts for strict JSON generation. We implemented a resilient AST/regex JSON extraction layer (`parse_json_safe`) that handles markdown code block fencing (` ```json `), trailing commas, and partial JSON chunks returned during SSE streaming.

### Sandboxed Code Execution Safety
Balancing analytical flexibility with system security was a primary technical challenge. By combining Python's `multiprocessing` sandbox workers with strict AST node validation, CSV Analyst AI allows full Pandas/NumPy/Seaborn analytical expressiveness while preventing filesystem tampering or dynamic reflection attacks.

### RAG Embedding Model Compliance & Local Trade-offs
To eliminate ambiguity under the hackathon rule requiring Gemma 4 as the sole model engine, external embedding APIs were replaced with a pure local `sklearn.feature_extraction.text.HashingVectorizer` (768-dimensional normalized vectors). This guarantees zero external LLM API calls and fast document retrieval. While local TF-IDF hashing relies on term overlap rather than deep semantic embeddings, it provides reliable local context retrieval without compromising model compliance. Fine-tuned Gemma embedding checkpoints are planned as future work for local Ollama deployments.

---

## 6. Future Work & Local/Offline Deployment
Because Gemma 4 is an open-weight foundation model family, future iterations of CSV Analyst AI can run **100% locally and offline** via Ollama or vLLM. This is a game-changer for rural schools, community clinics, and micro-finance NGOs in low-bandwidth regions of Bangladesh where internet connectivity is intermittent. Local Gemma 4 deployment ensures zero data egress, complete data privacy compliance, and uninterrupted analytical access.
