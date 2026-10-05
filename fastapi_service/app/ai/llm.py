"""Optional LLM polish. The model only rewords facts the permission-checked tools already produced;
it never receives database access. Without AI_API_KEY the factual answer is returned unchanged."""
import httpx

from ..config import settings

SYSTEM = ("You are Dayflow's HR assistant. Rewrite the FACTS into a short, friendly answer. Use ONLY the facts provided, "
          "never invent numbers, and never make or suggest hiring, firing, pay, promotion or disciplinary decisions.")


def polish(question: str, facts: str) -> str:
    if not settings.ai_api_key:
        return facts
    try:
        r = httpx.post("https://api.anthropic.com/v1/messages", timeout=12,
                       headers={"x-api-key": settings.ai_api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                       json={"model": settings.ai_model, "max_tokens": 300, "system": SYSTEM,
                             "messages": [{"role": "user", "content": f"Question: {question}\nFACTS: {facts}"}]})
        r.raise_for_status()
        return r.json()["content"][0]["text"].strip() or facts
    except Exception:
        return facts
