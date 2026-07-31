# Analytico AI: Gemma 4 CSV Analyst for Trusted Data Decisions

## Subtitle
An AI data analyst that turns messy spreadsheets into verified insights, charts, predictive models, and action plans using Gemma 4 as the primary reasoning model.

## Problem
Across Bangladesh and other emerging markets, many small businesses, student teams, clinics, NGOs, and local operators store their most important data in CSV or Excel files. They often know the data matters, but they do not have a data analyst available to profile quality, build charts, explain trends, or turn rows into decisions.

Most "chat with CSV" tools are also difficult to trust. They can give polished answers while hiding whether the answer came from real computation, a guessed column mapping, or a failed model response. For high-impact domains like finance, healthcare, education, and operations, this creates a serious adoption barrier.

## Solution
Analytico AI is a Gemma 4-powered data science workbench for non-technical users. A user uploads a CSV, Excel, JSON, or Parquet dataset, then asks plain-English questions such as:

- "What is the highest blood pressure value?"
- "Who has the highest performance score?"
- "How can I make this dataset better?"
- "Plot salary by department."
- "Train a model to predict attrition."

The application responds with verified evidence, charts, execution steps, confidence metadata, and a concise natural-language answer. If the LLM wording fails, the verified computation is still shown as a partial success instead of becoming a red total failure.

## Gemma 4 Integration
Gemma 4 is the primary and only large language model used for generative AI behavior in the app.

Gemma 4 is used for:

- Intent understanding and schema-aware planning when deterministic routing is insufficient.
- Answer synthesis from bounded verified evidence.
- Clarification wording when a user request is ambiguous.
- Multi-agent analytical workflows, including planner, analyst, critic, and reporter-style stages.
- Executive summaries and decision-oriented narratives.

The system deliberately separates deterministic computation from generated wording. Pandas, NumPy, scikit-learn, statsmodels, Plotly, and matplotlib compute facts, charts, forecasts, and models. Gemma 4 explains those facts, but it is not allowed to invent unsupported numbers. The backend validates generated answers for JSON structure, numeric grounding, repetition, HTML, markdown fences, and unsupported claims.

No other LLM is used. Document retrieval uses a local `HashingVectorizer` instead of external embedding models, keeping the project compliant with the Gemma-only rule.

## Architecture
The project has a FastAPI backend and a React/Vite frontend.

Backend pipeline:

1. Upload and profile the dataset.
2. Infer schema roles, identifiers, numeric measures, categorical dimensions, quality issues, and use cases.
3. Route simple questions through deterministic resolvers.
4. Use Gemma 4 for planning only when deterministic resolution cannot safely answer.
5. Execute pandas, SQL, chart, forecasting, ML, or quality-analysis steps.
6. Package verified evidence.
7. Ask Gemma 4 to produce a concise grounded answer.
8. Stream progress and final events to the frontend using Server-Sent Events.

Frontend workflow:

- Upload panel with schema preview.
- Lens selector for general, finance, medical, retail, marketing, and HR analysis.
- Live multi-step analysis cards.
- Verified evidence panel.
- Chart and table rendering.
- Partial-success warning with retry-explanation action.
- Dataset insights tabs for quality, modeling, and export workflows.

## Technical Implementation
Important engineering choices:

- Canonical column matching resolves names like `BloodPressure`, `blood_pressure`, and `blood pressure` consistently.
- Conservative ambiguity handling prevents vague terms like "diabetes" from silently mapping to the wrong column when both `Outcome` and `DiabetesPedigreeFunction` exist.
- Separate intents distinguish scalar extreme values from row rankings. For example, "highest BMI value" returns a scalar, while "which row has the highest BMI" returns all tied rows.
- Direct answers use a compact response schema to reduce truncated JSON.
- Synthesis retry preserves request id, deadline, schema, thinking level, and evidence grounding.
- If deterministic computation succeeds but Gemma answer generation fails, the app returns `analysis_partial` with evidence still visible.
- Generated pandas code is sandboxed with restricted builtins and AST validation.
- API responses are JSON or SSE.

## Demo Scenario
A judge can upload a healthcare, HR, retail, or finance CSV and try:

1. "What is the highest blood pressure value?"
2. "Who has the highest blood pressure?"
3. "How to make this dataset good?"
4. "Plot performance score by department."
5. "Train a model to predict outcome."
6. "Export a report."

The demo shows Gemma 4 explaining verified facts while the UI exposes the computation path and evidence.

## Challenges
The hardest challenge was reliability. Early versions sometimes lost useful deterministic evidence when the LLM returned malformed JSON or timed out. We fixed this by introducing partial-success terminal events, deterministic evidence caching, compact direct schemas, and an explanation-only retry endpoint.

Another challenge was column resolution. Human phrases rarely match spreadsheet column names exactly. The app now uses canonical name matching, conservative fuzzy matching, and ambiguity evidence to avoid polished but wrong answers.

## Impact
Analytico AI can help small teams make better data-backed decisions without hiring a full data team. It is useful for:

- Small businesses analyzing sales, inventory, or revenue.
- Clinics reviewing patient and operations data.
- NGOs summarizing program outcomes.
- Students learning data analysis from real datasets.
- Founders preparing quick investor or operations reports.

The real-world value is not only faster analysis. It is trusted analysis: users can see the evidence, the chart, the calculation route, and the confidence behind the final answer.

## Future Work
Future improvements include local Gemma 4 deployment through vLLM or Ollama, persistent multi-user storage, team workspaces, stronger dashboard editing, and deeper domain templates for healthcare, agriculture, education, and microfinance.

## Repository and Demo
Public code repository: add your GitHub or Kaggle Notebook link here.

Live demo or video: add your hosted app, demo video, or runnable notebook link here.
