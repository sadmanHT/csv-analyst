# Skill: Add a New Chart Type

Use this skill when asked to support a new chart type (e.g. pie, scatter, heatmap, box plot, line chart).

## Steps

1. **Update the system prompt** in `backend/main.py`:
   - Add the new chart type to the examples or instructions in `SYSTEM_PROMPT`
   - Make sure the agent knows when to use this chart type

2. **Add a sample question** in `frontend/src/App.jsx`:
   - Add to the `SAMPLE_QUESTIONS` array so users can discover it
   - Example: `'Show a pie chart of the distribution of <column>'`

3. **Test manually**:
   - Upload a CSV that has appropriate data for the new chart type
   - Ask a question that should trigger that chart
   - Verify the chart renders in the UI

4. **Write a regression test** in `backend/test_main.py`:
   - Test that `/upload` still works
   - Test that `/query` returns a valid SSE stream

5. **Run pytest**:
   ```bash
   cd backend && pytest -v
   ```
   All tests must pass before completing.

## Notes
- Charts are returned as base64 PNG via the `chart` field in the SSE `done` event
- Always call `plt.close()` after saving to buffer to avoid memory leaks
- Use `dpi=120` and `bbox_inches='tight'` for clean output
