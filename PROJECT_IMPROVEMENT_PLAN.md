# CSV Analyst AI Improvement Plan

## Project Purpose

CSV Analyst AI is an agentic data-analysis workbench for turning uploaded CSV data into useful decisions. The current product lets a user upload or paste tabular data, ask natural-language questions, watch a multi-step AI analysis pipeline run, inspect generated code, view charts, train predictive models, and export results.

The strongest hackathon story is:

> Upload any dataset and get a transparent AI data science teammate that profiles, reasons, writes code, validates itself, explains predictions, and turns insights into a report.

This should be positioned as more than a CSV chatbot. The winning version should feel like an explainable analyst session with visible reasoning, reliable fallback analysis, strong visual output, and a polished demo flow.

The improved hackathon focus should be proactive intelligence:

> The analyst should already have looked at the dataset before the user asks the first question.

That means the app should immediately surface likely KPIs, anomalies, data-quality issues, interesting questions, and recommended next actions after upload.

## Existing Project Map

### Backend

Main file: `backend/main.py`

Current backend capabilities:

- `GET /health`: health check.
- `POST /upload`: upload CSV files.
- `POST /upload_text`: paste CSV/TSV rows.
- `POST /upload_doc`: upload PDF, Excel, text, Markdown, or CSV documentation for RAG.
- `GET /docs/{session_id}`: list indexed documentation for a session.
- `GET /quality/{session_id}`: regenerate deterministic data-quality findings.
- `GET /brief/{session_id}`: regenerate the decision-readiness brief.
- `GET /cleaning_plan/{session_id}` and `POST /clean/{session_id}`: preview and export conservative cleaning actions.
- `GET /contract/{session_id}` and `POST /validate_rows/{session_id}`: generate and enforce a portable data contract.
- `GET /dashboard/{session_id}`: generate a dashboard blueprint.
- `POST /query`: stream a multi-agent analysis over Server-Sent Events.
- `POST /investigate`: stream an autonomous deterministic investigation brief.
- `POST /story`: stream a fact-first dataset story.
- `POST /predict`: train a Random Forest model and stream explainability results.
- `GET /model_info/{session_id}`: return trained model metadata.
- `POST /predict_input`: run inference for a new row.
- `POST /simulate`: compare baseline vs what-if model predictions without retraining.
- `POST /scenario_parse`: parse natural-language what-if prompts into simulator controls.
- `POST /report/{session_id}`: export PDF or PPTX report.
- `GET /benchmark/{session_id}`: run the benchmark question suite.

Important backend systems:

- Data is stored in memory through global dictionaries: `dataframes`, `models`, and `doc_stores`.
- The agent pipeline is prompt-driven with Planner, Analyst, SQL Analyst, Visualizer, Critic, and Reporter prompts.
- Generated pandas/Plotly code is executed through `execute_code`.
- SQL analysis uses in-memory SQLite through `execute_sql`.
- Overview charts are deterministic and generated immediately after upload.
- Predictive modeling uses scikit-learn Random Forest, SHAP, permutation importance, and partial dependence plots.

### Frontend

Main file: `frontend/src/App.jsx`

Current frontend capabilities:

- Upload screen with analysis lens selection.
- Paste-data modal.
- Three-panel workspace: schema/sidebar, chat area, insights panel.
- Domain lenses: General, Financial, Medical, Retail, Marketing, HR.
- Streamed agent steps from `/query` and `/predict`.
- Autonomous investigation launch from decision-action cards.
- Plotly chart rendering.
- Generated code display.
- Critique and plan display.
- Predictive model training and live inference form.
- Scenario simulator for what-if changes after a model is trained.
- Natural-language scenario setup for prompts like "increase discount by 10%".
- Benchmark modal.
- PDF/PPTX export controls.

### Tests

Main test file: `backend/test_main.py`

Current coverage:

- Upload and paste flows.
- Data profile generation.
- Overview chart generation.
- Sandbox AST checks.
- Plotly and matplotlib code execution.
- Basic SQL execution.
- Predictive model training.
- Predict input flow.
- Autonomous investigation stream.
- Error cases for missing sessions and bad targets.

## Current Strengths

- The project already has a strong product story and broad feature surface.
- The streamed multi-agent pipeline makes the system feel transparent and demo-friendly.
- Deterministic overview charts provide immediate value before any LLM call.
- Domain lenses make the app feel specialized without requiring complex setup.
- Generated code visibility helps build trust.
- Predictive modeling and explainability are strong hackathon differentiators.
- Benchmark evaluation is a rare and compelling feature for an AI demo.
- Deployment config exists for Railway and Vercel.
- The backend test suite currently passes.

## Main Gaps To Address

### Reliability Gaps

- Many common questions depend on Gemini even when deterministic pandas logic would be more reliable.
- In-memory sessions are fragile and disappear on restart.
- The agent planner may choose weak columns or chart types when column names are ambiguous.
- SQL execution does not currently enforce a strict `SELECT`-only policy.
- The system treats most questions independently and does not remember the previous metric, grouping, chart, or analytical context.
- Chart selection is mostly LLM-driven instead of being backed by deterministic visualization rules.

### Security Gaps

- The code sandbox uses a thread timeout, which does not reliably stop runaway Python execution.
- Some allowed builtins, such as `getattr`, `hasattr`, and `type`, weaken AST-based protections.
- Uploaded files do not appear to have strict file size or row/column limits.
- Report export returns binary data, which conflicts with the current `AGENTS.md` rule requiring JSON or SSE responses.

### Testing Gaps

Per `AGENTS.md`, every endpoint should have a corresponding test. The project should add direct tests for:

- Successful `/upload_doc`
- `/docs/{session_id}`
- Successful `/query` SSE stream
- Successful `/report/{session_id}` for PDF and PPTX
- `/benchmark/{session_id}`
- SQL rejection for non-`SELECT` statements
- Sandbox timeout behavior

### Frontend Gaps

- Plotly is imported eagerly, making the production JavaScript bundle large.
- Follow-up suggestions after analysis are not generated yet.
- The UX has many features, but the central demo path could be made more dramatic and guided.
- There is no true dashboard-builder mode yet.
- The app does not yet show a rich execution timeline with elapsed time, route type, deterministic vs LLM path, and tool/code status.

### Intelligence Gaps

- The AI is reactive: it waits for the user instead of proactively discovering insights on upload.
- Story generation should be fact-first, with deterministic facts collected before the LLM writes narrative.
- Confidence values need a clear explanation instead of appearing as arbitrary model or LLM scores.
- The benchmark feature should expose more metrics that prove the system works reliably.
- There is no cache for repeated questions or repeated deterministic computations.

## Revised Hackathon Priorities

If development time is limited, prioritize features that judges can see immediately:

1. Deterministic intent handlers.
2. Automatic dataset story.
3. Proactive insights on upload.
4. Conversation memory.
5. Follow-up question generation.
6. Insight validation and confidence explanation.
7. Guided demo mode.
8. Dashboard builder with templates.
9. Security hardening.
10. Persistence and operational improvements.

Features such as two-dataset comparison, full persistence, and strict upload limits are still valuable, but they should not displace the core demo improvements unless the hackathon judging criteria specifically reward production infrastructure.

## Hackathon-Winning Roadmap

## Phase 1: Make The Demo Reliable

Goal: Ensure the core demo works even if the LLM is slow, imprecise, or unavailable.

### 1. Add Deterministic Intent Handlers

Add backend logic before the LLM pipeline for common analysis intents:

- Dataset shape: row and column count.
- Missing values summary.
- Duplicate row count.
- Numeric summary statistics.
- Correlation heatmap.
- Distribution charts.
- Top categories by count.
- Top-N by numeric metric.
- Group-by sum/average/count.

Implementation location:

- Add helper functions in `backend/main.py`.
- Call them at the start of `/query` before invoking Gemini.
- Return the same SSE event structure as the agent pipeline.

Why it matters:

- Makes demos safer.
- Reduces cost and latency.
- Gives judges confidence that the system is not just prompt theater.

### 2. Improve Column Understanding

Add a schema intelligence layer that identifies likely semantic roles:

- Metric columns: `revenue`, `sales`, `profit`, `cost`, `amount`, `quantity`, `price`, `rating`.
- Time columns: `date`, `created_at`, `month`, `year`, `timestamp`.
- Dimensions: `category`, `region`, `segment`, `product`, `department`.
- ID columns: `id`, `order_id`, `customer_id`, high-cardinality integer columns.
- Target candidates for ML.

Implementation location:

- Add `infer_column_roles(df)` in `backend/main.py`.
- Include role metadata in upload response.
- Use role metadata in prompts and frontend suggestions.

### 3. Add Deterministic Chart Selection

Add a chart-selection helper that chooses the best chart from data roles before asking Gemini.

Rules:

- Time column + numeric metric -> line chart.
- Category column + numeric metric -> bar chart.
- Two numeric columns -> scatter plot.
- Numeric column only -> histogram or box plot.
- Many numeric columns -> heatmap.
- Part-to-whole category breakdown -> bar chart first, pie only for very small category counts.
- High-cardinality category -> top-N bar chart.
- Geography-like fields such as country, city, region -> map only if geocoding or known coordinates are available; otherwise grouped bar chart.

Implementation location:

- Add `choose_chart_spec(question, df, column_roles)` in `backend/main.py`.
- Use the chart spec in deterministic handlers and Visualizer prompts.
- Add tests for common chart-routing cases.

Why it matters:

- Reduces chart hallucination.
- Makes dashboard generation more consistent.
- Gives judges a concrete explanation for why each visualization was chosen.

### 4. Add Lightweight Conversation Memory

Store minimal per-session analytical context:

- Last question.
- Last metric.
- Last grouping column.
- Last chart type.
- Last result summary.
- Last generated SQL or Python code.
- Last follow-up suggestions.

Example:

- User asks: "Show revenue by region."
- Then asks: "Now split by product."
- The system understands that "split" refers to the previous revenue-by-region analysis.

Implementation location:

- Add a `conversation_state` dictionary in `backend/main.py`.
- Update state at the end of `/query`.
- Inject relevant state into Planner prompts.
- Add frontend support for displaying context-aware follow-ups.

### 5. Harden SQL Execution

Before running generated SQL:

- Strip markdown fences and semicolons.
- Allow only a single statement.
- Require the query to start with `SELECT` or `WITH`.
- Block keywords such as `DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`, `ATTACH`, `PRAGMA`.
- Add tests for blocked SQL.

Implementation location:

- Add `validate_sql(sql: str) -> str` before `execute_sql`.

### 6. Add Query Result Caching

Cache deterministic and completed agent results by:

- Session ID.
- Normalized question.
- Category.
- Dataset fingerprint.

Implementation location:

- Add an in-memory `query_cache` for hackathon use.
- Return cached results through the same SSE event format.
- Show a "cached result" marker in the execution timeline.

Why it matters:

- Reduces latency during demos.
- Reduces Gemini API cost.
- Makes repeated judge questions feel instant.

## Phase 2: Add Wow Features

Goal: Make the project memorable and easy to demo.

### 1. Proactive Insights On Upload

After upload, automatically compute and display:

- Likely KPIs.
- Most important numeric metrics.
- Main dimensions.
- Top changes or extremes.
- Missing-value and duplicate warnings.
- Outlier candidates.
- Interesting questions to ask.

Implementation location:

- Extend `register_dataframe` in `backend/main.py` to return `proactive_insights`.
- Use deterministic profiling first.
- Let Gemini polish wording only after facts are computed.
- Display the insights in `ChatArea` or `InsightsPanel` before the first user question.

Why it matters:

- The first impression changes from "ask me something" to "your analyst has already reviewed the data."

### 2. Auto Dataset Story

Add a one-click or automatic feature:

> "What story does this dataset tell?"

Output:

- 3 key insights.
- 2 anomalies or suspicious patterns.
- 2 recommended follow-up questions.
- 1 suggested business action.
- 1 chart.

Implementation options:

- Deterministic pre-analysis creates a facts JSON object.
- Reporter agent turns only those facts into a polished story.
- Frontend displays story as insight cards.

Fact-first pipeline:

1. Profile dataset.
2. Infer column roles.
3. Compute candidate insights.
4. Rank insights by strength and relevance.
5. Produce facts JSON with source columns and row counts.
6. Ask Gemini to write narrative from those facts only.

Suggested endpoint:

- `POST /story`

Frontend location:

- Add a "Generate Dataset Story" button in `InsightsPanel`.
- Show story cards in `ChatArea` or a new dashboard section.

### 3. Insight Validation And Confidence

For every important insight, show why it should be trusted.

Example:

```text
Revenue increased 18%

Computed directly from 4,532 rows
Compared January vs February revenue totals
Statistical signal: strong
Critic agreement: pass
Confidence: High
```

Confidence should be based on explainable components:

- Deterministic computation: higher confidence than free-form LLM reasoning.
- Data support: number of rows used and missing-value rate.
- Statistical strength: effect size, correlation strength, or test result when applicable.
- Model confidence: prediction probability or validation score for ML outputs.
- Critic verdict: pass, warn, or fail.
- Execution success: no repair needed is stronger than repaired code.

Implementation location:

- Add `score_insight_confidence(...)` in `backend/main.py`.
- Include `validation` and `confidence_reason` fields in final SSE events and story cards.
- Render validation badges in `ChatMessage` or new Insight Cards.

Why it matters:

- It directly answers the judge question: "Why should I trust this insight?"

### 4. Smart Follow-Up Questions

After every `/query` result, generate three next questions:

- One drill-down question.
- One comparison question.
- One visualization or prediction question.

Example:

- "Break this down by region."
- "Show the trend over time."
- "Which product category is driving the difference?"

Implementation location:

- Add a Follow-Up agent prompt in `backend/main.py`.
- Include `followups` in the final SSE `done` event.
- Render clickable chips under each answer in `ChatMessage`.

### 5. Data Quality Doctor

Add a panel that diagnoses:

- Missing values.
- Duplicate rows.
- Outliers.
- Mixed data types.
- Suspicious ID columns.
- High-cardinality categorical fields.
- Date parsing opportunities.
- Skewed numeric distributions.

Output:

- Quality score.
- Issues grouped by severity.
- Suggested fixes.
- Optional generated pandas cleaning code.

Suggested endpoint:

- `GET /quality/{session_id}`

Frontend location:

- Upgrade the existing Dataset Health card in `InsightsPanel`.

### 6. Natural-Language Dashboard Builder

Allow prompts like:

> "Build me a sales dashboard."

Use constrained templates first, then customize them:

- Executive dashboard.
- Sales dashboard.
- Marketing dashboard.
- Finance dashboard.
- HR dashboard.
- Healthcare dashboard.
- General exploratory dashboard.

Output:

- KPI cards.
- Trend chart.
- Category breakdown.
- Region/segment breakdown.
- Anomaly card.
- Recommended action card.

Suggested endpoint:

- `POST /dashboard`

Frontend location:

- Add a dashboard view or dashboard message type.
- Reuse existing Plotly renderer and overview card styling.

### 7. Compare Two Datasets

Add a second upload slot and support:

> "What changed between these two CSVs?"

Output:

- Schema differences.
- Row count differences.
- Metric deltas.
- Distribution shifts.
- Category additions/removals.
- Top increases/decreases.

Suggested endpoint:

- `POST /compare_upload`
- `POST /compare_query`

Why it matters:

- This is highly demoable and useful for month-over-month sales, before/after experiments, and operational reporting.

Priority note:

- This is useful, but it should be treated as a stretch feature unless comparison is central to the hackathon theme.

## Phase 3: Make It Production-Credible

Goal: Make the project defensible when judges ask about safety, scaling, and reliability.

### 1. Replace Thread Sandbox Timeout

Move generated code execution into a separate process:

- Use `multiprocessing` or a worker process.
- Kill the process after timeout.
- Return a structured error if execution times out.

Implementation location:

- Refactor `execute_code` in `backend/main.py`.

Testing:

- Add a test for an infinite loop.
- Ensure the test completes quickly.

### 2. Tighten Sandbox Builtins

Remove or restrict:

- `getattr`
- `hasattr`
- `type`
- `iter`
- `next`
- `chr`
- `ord`

Keep only the minimum needed for generated pandas/chart code.

Testing:

- Add tests for string-based dunder access attempts.

### 3. Add Session Persistence

For hackathon production deployment, choose one lightweight persistence option:

- Store uploaded CSVs and metadata in temporary files keyed by session ID.
- Or use SQLite for session metadata and cached files.
- Or use Redis if available on the deployment platform.

Minimum improvement:

- Add session expiration and cleanup.
- Add maximum memory limits.

Priority note:

- For a hackathon, lightweight cleanup is usually enough. Full persistence should come after proactive insights, memory, validation, and demo polish.

### 4. Add Upload Limits

Add:

- Max file size.
- Max rows.
- Max columns.
- Sampling strategy for large datasets.

Return JSON errors with clear messages.

Priority note:

- Upload limits are important for production credibility, but they are lower demo impact than deterministic handlers, insight validation, and guided demo mode.

### 5. Add Endpoint Tests

Add tests to `backend/test_main.py` for every endpoint:

- `/upload_doc`
- `/docs/{session_id}`
- `/query`
- `/report/{session_id}`
- `/benchmark/{session_id}`

Run:

```bash
pytest backend/
```

### 6. Add Observability For Demos

Expose a transparent execution timeline:

- Total elapsed time.
- Time per step.
- Deterministic path vs LLM path.
- Cache hit or miss.
- Generated SQL.
- Generated Python.
- Code execution status.
- Repair attempts.
- Chart generation status.
- Approximate token usage when available.

Implementation location:

- Add timing around each `/query`, `/predict`, `/story`, and `/benchmark` step.
- Include `meta` fields in SSE events.
- Render timing badges in the frontend step timeline.

Why it matters:

- It reinforces the "transparent analyst" theme.
- It makes live demo debugging much easier.

### 7. Expand Benchmark Metrics

The benchmark should report more than success rate:

- Overall benchmark score.
- Average latency.
- Median latency.
- Deterministic answer rate.
- LLM answer rate.
- Cache hit rate.
- Code execution success rate.
- SQL routing accuracy.
- Visualization success rate.
- Repair rate.
- Critic pass/warn/fail distribution.

Implementation location:

- Extend `run_benchmark` in `backend/main.py`.
- Update `BenchmarkModal` in `frontend/src/App.jsx`.
- Add tests for the benchmark response shape.

## Phase 4: Frontend Polish

Goal: Make the project feel premium during a live demo.

### 1. Lazy-Load Plotly

Current issue:

- `frontend/src/App.jsx` imports Plotly at the top level.
- This makes the production bundle large.

Plan:

- Remove top-level `import Plotly from 'plotly.js-dist-min'`.
- Dynamically import Plotly inside `PlotlyChart`.
- Show a lightweight loading state while the chart library loads.

### 2. Add A Guided Demo Mode

Add a "Demo Mode" button for the included sample dataset:

- Load `sample_data/ecommerce_sales.csv`.
- Pre-fill suggested questions.
- Highlight the intended demo sequence.
- Show the best next action at each stage.
- Include a one-click reset for rehearsals.

Suggested demo sequence:

1. Upload or load sample e-commerce data.
2. Show instant overview.
3. Generate dataset story.
4. Ask for revenue by category.
5. Ask for trend over time.
6. Train prediction model.
7. Show explainability.
8. Export boardroom report.
9. Run benchmark.

### 3. Improve Report Export UX

Current report export works, but it can be positioned better:

- Rename to "Boardroom Report".
- Add report style options: Executive, Technical, Investor.
- Show a report preview summary before download.
- Include follow-up questions and quality diagnosis.

### 4. Add Insight Cards

Turn results into reusable cards:

- Title.
- Finding.
- Confidence.
- Source columns.
- Chart.
- Recommended action.
- Follow-up buttons.

This makes the app feel less like a chat transcript and more like an analyst workspace.

### 5. Add Curated Evaluation Datasets

Include several small demo-ready datasets with scripted question paths:

- E-commerce sales.
- Titanic survival.
- Iris classification.
- Superstore-style sales.
- Netflix/catalog dataset.
- Healthcare outcomes.
- HR attrition.

Implementation location:

- Add files under `sample_data/`.
- Add `sample_data/README.md` with recommended demo prompts.
- Add a frontend "Load sample dataset" path if time allows.

Why it matters:

- Judges can ask for different domains.
- The app can show that domain lenses are real, not only hardcoded around one sample file.

## Suggested New Endpoints

### `POST /story`

Generate a dataset story from profile, overview facts, and optional documentation.

Response:

- SSE recommended, because story generation can stream steps.

### `GET /insights/{session_id}`

Return proactive deterministic insights after upload.

Response:

- JSON or SSE.
- Should include insight text, source columns, validation details, confidence, and suggested follow-ups.

### `GET /quality/{session_id}`

Return deterministic data-quality diagnostics.

Response:

- JSON.

### `POST /dashboard`

Generate a dashboard layout and chart specs from a natural-language request.

Response:

- SSE or JSON.
- Should choose a dashboard template before generating chart specs.

### `GET /timeline/{session_id}`

Return recent execution metadata for debugging and demo observability.

Response:

- JSON.

### `GET /cleaning_plan/{session_id}`

Generate a no-code deterministic cleaning plan.

Response:

- JSON with proposed steps, default actions, and estimated after-cleaning quality.

### `POST /clean/{session_id}`

Apply selected cleaning actions or safe defaults and export a cleaned CSV.

Apply selected safe cleaning operations.

Response:

- JSON profile for the cleaned dataset.

### `POST /compare_upload`

Upload a second dataset for comparison.

Response:

- JSON profile.

### `POST /compare_query`

Ask natural-language questions across two datasets.

Response:

- SSE.

## Best Hackathon Demo Script

1. Start with the pitch:

   "Most CSV chatbots give an answer. This one behaves like an analyst: it plans, writes code, checks itself, explains models, and produces a report."

2. Upload `sample_data/ecommerce_sales.csv`.

3. Show the instant overview dashboard and proactive insights.

4. Click "Generate Dataset Story" and explain that the story is written from deterministic facts.

5. Ask:

   "Show total revenue by category sorted descending as a bar chart."

6. Open generated code and explain transparency.

7. Show the critic badge and confidence.

8. Show insight validation: source rows, computation path, and confidence reason.

9. Ask:

   "Plot total revenue over time as a line chart."

10. Ask a context-aware follow-up:

   "Now split that by product."

11. Train a predictive model for `revenue` or `rating`.

12. Show feature importance, SHAP, permutation importance, and PDP tabs.

13. Export a Boardroom Report.

14. Run the benchmark modal with latency, deterministic answer rate, and visualization success rate.

15. End with:

   "This is not only a chatbot. It is a transparent, evaluated, explainable AI analyst for messy business data."

## Recommended Implementation Order

### Day 1: Reliability

- Add deterministic intent handlers.
- Add deterministic chart selection.
- Add lightweight conversation memory.
- Add SQL validation.
- Add query result caching.
- Add focused tests for deterministic paths and SQL validation.
- Run `pytest backend/`.

### Day 2: Proactive Intelligence

- Add proactive insights on upload.
- Add Auto Dataset Story.
- Make story generation fact-first.
- Add insight validation and confidence reasons.
- Add follow-up questions.

### Day 3: Demo Polish

- Add insight cards.
- Add guided demo mode.
- Lazy-load Plotly.
- Improve report export naming and UX.
- Expand benchmark metrics.
- Polish README with the final demo script.

### Day 4: Hardening

- Replace thread timeout with process timeout.
- Tighten sandbox builtins.
- Add missing endpoint tests.
- Add observability/timing metadata.
- Add upload limits and session cleanup if time remains.

## Current Implementation Status

Completed production-grade upgrades:

- Deterministic query routing for common analytical questions.
- Deterministic chart selection from inferred column roles.
- Proactive insight generation immediately after upload.
- Deterministic decision brief with readiness score, use cases, blocked workflows, next actions, priority questions, automation opportunities, and data dictionary.
- Decision-intelligence action board with business implication, recommended action, estimated impact, confidence, evidence, risks, and investigation prompt.
- Autonomous `/investigate` workflow that streams goal scoping, investigation planning, deterministic evidence computation, and an executive brief.
- Persona-aware autonomous investigations for General, Financial/CFO, Healthcare, Retail, Marketing, and HR lenses, including priority KPIs, domain cautions, and matched columns.
- What-if scenario simulation through `/simulate`, comparing baseline and changed model inputs with impact metadata and chart JSON.
- Deterministic natural-language scenario parser through `/scenario_parse`, mapping explicit user prompts to feature, mode, and value controls.
- Lightweight background job layer with `/predict_job`, `/report_job/{session_id}`, `/benchmark_job/{session_id}`, and `/jobs/{job_id}` polling.
- `/brief/{session_id}` endpoint for regenerating the decision brief by analysis lens.
- Deterministic cleaning plan with conservative defaults for duplicate rows, empty columns, whitespace trimming, and missing-value imputation.
- JSON/base64 cleaned CSV export through `/clean/{session_id}`.
- Inferred data contract with required columns, portable types, roles, constraints, and validation policy.
- `/contract/{session_id}` and `/validate_rows/{session_id}` for repeatable downstream data checks.
- Deterministic dashboard blueprint with KPI cards, chart specs, filters, starter questions, and JSON export.
- `/dashboard/{session_id}` for regenerating dashboard specs by analysis lens.
- Fact-first dataset story endpoint.
- Follow-up question suggestions and validation metadata.
- Conversation memory for context-aware follow-ups.
- Query result caching with bounded cache size.
- Strict SQL validation for read-only single-statement queries.
- Upload byte limits and dataframe row/column limits.
- Session TTL cleanup across dataframes, models, documents, conversations, and cache entries.
- Request IDs, endpoint names, sequence numbers, and elapsed timings on streamed SSE events.
- Frontend execution timeline surfaces route, elapsed time, and request IDs.
- Frontend answer headers show visible route/trust badges for deterministic, cached, autonomous, and AI-agent responses.
- Frontend shows decision readiness in the main overview and right-side workspace panel.
- Frontend centers "What to do next" actions in the overview and side panel.
- Frontend decision-action "Investigate" buttons now launch the autonomous investigation stream instead of a single reactive question.
- Frontend investigation plans now show the active analyst persona, focus area, and priority KPI vocabulary.
- Frontend scenario simulator lets users change a model driver and inspect baseline vs scenario predictions.
- Frontend scenario simulator can prefill controls from natural-language what-if prompts.
- Frontend shows cleaning recommendations and a cleaned CSV download action.
- Frontend shows data contract summary and exports contract JSON.
- Frontend shows dashboard blueprint recommendations and exports dashboard JSON.
- In-memory rate limiting with JSON 429 responses and retry metadata.
- Process-isolated generated-code execution through `backend/sandbox_runner.py`.
- Tighter sandbox builtins with reflection helpers removed.
- JSON-only report export using base64 payloads for PDF/PPTX.
- Frontend report download updated to consume the JSON report contract.
- Lazy Plotly loading so the initial frontend bundle stays small.
- GitHub Actions CI workflow runs backend tests and frontend build on push and pull request.
- Endpoint tests added for `/upload_doc`, `/docs/{session_id}`, `/investigate`, `/simulate`, `/scenario_parse`, `/report/{session_id}`, `/predict_job`, `/report_job/{session_id}`, `/benchmark_job/{session_id}`, `/jobs/{job_id}`, and `/benchmark/{session_id}`.

Verified:

- `pytest backend/` passes with 89 tests.
- `npm run build` passes for the frontend.

Next production-grade priorities:

- Add persistent session storage so uploads survive process restarts.
- Add authentication or signed session tokens before public deployment.
- Move the in-memory background job registry to a durable queue or database-backed job table.
- Replace in-memory global stores with an explicit repository/service layer.
- Add frontend error boundaries and retry states for streaming requests.
- Add frontend component tests for prediction, scenario simulation, and streaming message rendering.
- Add additional persona templates for Operations, Product, and Data Scientist workflows.
- Add multi-driver scenario simulation for compound changes.

## Success Criteria

The project is hackathon-ready when:

- The sample dataset demo works end to end without manual recovery.
- Common questions can be answered deterministically.
- The app shows useful proactive insights immediately after upload.
- The story feature is generated from deterministic facts.
- Follow-up questions understand previous context.
- Important insights include validation and confidence reasons.
- Every endpoint has a test.
- `pytest backend/` passes.
- `npm run build` passes.
- The app can generate a story, chart, model explanation, and report in one demo flow.
- The benchmark reports latency, deterministic answer rate, code success, and visualization success.
- The README clearly explains the value proposition and demo steps.
