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
    request_id: str | None = None,
    deadline_at: float | None = None,
    complexity_route: str = "standard",
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
        import time
        from backend.core.schemas import ROUTE_BUDGETS
        budget = ROUTE_BUDGETS.get(complexity_route)
        timeout_seconds = 10.0
        if deadline_at:
            timeout_seconds = max(0.1, deadline_at - time.monotonic())
        
        raw_text = llm_client.generate_content(
            system_instruction=SYNTHESIS_SYSTEM_PROMPT,
            contents=user_text,
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=GeneratedAnswer,
            max_output_tokens=384,
            evidence_payload=evidence.model_dump(),
            request_id=request_id,
            stage="synthesis",
            budget=budget,
            timeout_seconds=timeout_seconds,
            thinking_config={"thinking_level": "minimal"},
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
            from backend.core.schemas import GeneratedAnswer
            timeout_seconds = 10.0
            if deadline_at:
                timeout_seconds = max(0.1, deadline_at - time.monotonic())
            raw_text = llm_client.generate_content(
                system_instruction=SYNTHESIS_SYSTEM_PROMPT,
                contents=json.dumps(trimmed_payload, default=str),
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=GeneratedAnswer,
                max_output_tokens=384,
                evidence_payload=trimmed_payload["evidence"],
                request_id=request_id,
                stage="synthesis",
                budget=budget,
                timeout_seconds=timeout_seconds,
                thinking_config={"thinking_level": "minimal"},
            )
        except Exception as e2:
            logger.error("LLM synthesis attempt 2 failed: %s", e2)
            record.succeeded = False
            record.offline_mode = False
            record.error_detail = str(e2)
            from backend.core.errors import LLMSynthesisError
            raise LLMSynthesisError("answer_generation_failed")

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
        logger.warning("Failed to parse JSON response from LLM synthesis (%s).", parse_err)
        record.succeeded = False
        record.error_detail = str(parse_err)
        from backend.core.errors import LLMSynthesisError
        raise LLMSynthesisError("invalid_llm_response")
