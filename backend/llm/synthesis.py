"""
LLM Answer Synthesis Module over Verified Evidence
"""

import json
import logging
from pydantic import BaseModel, Field
from backend.core.schemas import AnalysisEvidence, GeneratedAnswer
from backend.llm.client import llm_client

logger = logging.getLogger(__name__)

SYNTHESIS_SYSTEM_PROMPT = """You are an expert dataset analysis assistant. Answer the user's question using ONLY the verified dataset evidence provided.

Requirements:
- Give the direct answer first in plain language suitable for a non-technical user.
- Do not invent the dataset's intended purpose or unverified facts.
- Distinguish observations from assumptions.
- Do not claim that a model, method, or use case is best unless it was explicitly tested in the evidence.
- Format important numbers clearly and include relevant data-quality limitations.
- Never guess or change computed numeric values.
- Return your answer as a JSON object adhering strictly to this schema:
{
  "title": "<short descriptive title or null>",
  "summary": "<main direct answer in plain language>",
  "explanation": "<detailed explanation or context>",
  "findings": [{"label": "<key observation>", "detail": "<value or detail>"}],
  "caveats": ["<caveat or limitation if any>"],
  "next_action": "<suggested follow-up question or action>"
}
"""

class LLMCallRecord(BaseModel):
    succeeded: bool = True
    offline_mode: bool = False
    attempts: int = 1
    duration_ms: int = 0
    error_detail: str | None = None

def synthesize_llm_answer(
    question: str,
    evidence: AnalysisEvidence,
    effective_lens: str = "general",
    response_style: str = "plain_language",
) -> tuple[GeneratedAnswer, LLMCallRecord]:
    """Synthesize a natural-language answer using LLM over structured evidence facts."""
    user_payload = {
        "user_question": question,
        "effective_lens": effective_lens,
        "response_style": response_style,
        "evidence": evidence.model_dump(),
    }
    user_text = json.dumps(user_payload, default=str, indent=2)

    record = LLMCallRecord()
    raw_text = ""
    try:
        raw_text = llm_client.generate_content(
            system_instruction=SYNTHESIS_SYSTEM_PROMPT,
            contents=user_text,
            temperature=0.1,
        )
    except Exception as e:
        logger.warning("LLM synthesis attempt 1 failed: %s. Retrying with trimmed payload.", e)
        record.attempts = 2
        try:
            trimmed_payload = {
                "user_question": question,
                "effective_lens": effective_lens,
                "evidence": {
                    "intent": evidence.intent,
                    "dataset_name": evidence.dataset_name,
                    "facts": {k: v for k, v in list(evidence.facts.items())[:10]},
                    "warnings": evidence.warnings,
                },
            }
            raw_text = llm_client.generate_content(
                system_instruction=SYNTHESIS_SYSTEM_PROMPT,
                contents=json.dumps(trimmed_payload, default=str),
                temperature=0.1,
            )
        except Exception as e2:
            logger.error("LLM synthesis attempt 2 failed: %s", e2)
            record.succeeded = False
            record.offline_mode = True
            record.error_detail = str(e2)

            facts_summary_lines: list[str] = []
            for k, v in list(evidence.facts.items())[:12]:
                if isinstance(v, dict) and v:
                    facts_summary_lines.append(f"- **{k}**: {', '.join(f'{ck}: {cv}' for ck, cv in list(v.items())[:5])}")
                elif isinstance(v, list) and v:
                    facts_summary_lines.append(f"- **{k}**: {', '.join(str(x) for x in v[:5])}")
                elif v is not None and str(v).strip():
                    facts_summary_lines.append(f"- **{k}**: {v}")
            facts_text = "\n".join(facts_summary_lines) or "Dataset facts were computed but cannot be displayed."
            fallback_summary = (
                f"The analysis for '{question}' was completed using verified dataset evidence, "
                f"but the natural-language answer generator is temporarily unavailable (network error). "
                f"Here are the key facts computed directly from your data:\n\n{facts_text}"
            )
            ans = GeneratedAnswer(
                title="Analysis Complete (Offline Mode)",
                summary=fallback_summary,
                explanation="The LLM synthesis step failed due to a network connectivity error. "
                            "The figures above are computed deterministically from your dataset and are accurate.",
                findings=[
                    {"label": str(k).replace("_", " ").title(), "detail": str(v)[:200]}
                    for k, v in list(evidence.facts.items())[:8]
                    if v is not None and str(v).strip()
                ],
                caveats=(evidence.warnings or []) + ["Natural-language synthesis unavailable. Retry when network is restored."],
                next_action="Retry this question or ask a simpler follow-up.",
            )
            return ans, record

    try:
        clean = raw_text
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1]
        if "```" in clean:
            clean = clean.rsplit("```", 1)[0]
        clean = clean.strip()
        parsed = json.loads(clean)
        ans = GeneratedAnswer(
            title=parsed.get("title"),
            summary=parsed.get("summary") or "Analysis completed.",
            explanation=parsed.get("explanation"),
            findings=parsed.get("findings") if isinstance(parsed.get("findings"), list) else [],
            caveats=parsed.get("caveats") if isinstance(parsed.get("caveats"), list) else [],
            next_action=parsed.get("next_action"),
        )
        return ans, record
    except Exception as parse_err:
        logger.warning("Failed to parse JSON response from LLM synthesis (%s). Using fallback wrapper.", parse_err)
        ans = GeneratedAnswer(
            title="Analysis Result",
            summary=raw_text if raw_text else "Analysis complete based on verified evidence.",
            explanation=None,
            findings=[],
            caveats=evidence.warnings,
            next_action="Explore further dataset columns or ask a follow-up question.",
        )
        return ans, record
