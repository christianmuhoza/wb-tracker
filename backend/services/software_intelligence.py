"""Product-centric software opportunity classification."""

import json
import os
import time
from typing import Any

import requests

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
WORK_TYPES = {"new_build", "enhancement", "integration", "implementation", "support", "other"}
CONFIDENCE_LEVELS = {"high", "medium", "low"}


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[:500] if text else None


def _notice_context(notice: dict[str, Any]) -> str:
    fields = (
        ("Title", notice.get("title")),
        ("Description", notice.get("description")),
        ("Project", notice.get("project_name")),
        ("Procurement method", notice.get("procurement_method")),
        ("Buyer reference", notice.get("borrower_bid_reference")),
    )
    return "\n".join(f"{label}: {value}" for label, value in fields if value)


def classify_software_opportunity_with_gemini(notice: dict[str, Any]) -> dict[str, Any]:
    """Classify by requested deliverable; product categories are deliberately open-ended."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is not configured.")
    context = _notice_context(notice)
    if not context:
        raise ValueError("The notice has no title, description, or project context to classify.")
    instruction = """You classify procurement notices by the PRODUCT OR DELIVERABLE being procured. Read all supplied context; do not require words such as software or development. A notice is software-related only when its main deliverable is building, enhancing, configuring, integrating, implementing, operating, or supporting a digital software system, application, platform, database, workflow, or API. Hardware supply, civil works, training, and general consulting are not software-related unless the requested deliverable is materially a software system. Return JSON only:
{"is_software_related":true,"work_type":"new_build|enhancement|integration|implementation|support|other","product_category":"concise reusable category inferred from the deliverable, or null","product_name":"specific solution/product sought, or null","confidence":"high|medium|low","reason":"concise evidence-based explanation"}
Product categories are open-ended; describe unfamiliar domain systems accurately rather than forcing a fixed taxonomy."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": f"{instruction}\n\nNOTICE:\n{context}"}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    for attempt in range(3):
        response = requests.post(url, json=payload, timeout=45)
        if response.status_code not in (429, 503) or attempt == 2:
            response.raise_for_status()
            break
        time.sleep(2**attempt)
    try:
        result = json.loads(response.json()["candidates"][0]["content"]["parts"][0]["text"].strip())
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Gemini returned an invalid software-classification response.") from exc
    is_related = result.get("is_software_related") is True
    return {
        "is_software_related": is_related,
        "work_type": result.get("work_type") if is_related and result.get("work_type") in WORK_TYPES else "other",
        "product_category": _clean_text(result.get("product_category")) if is_related else None,
        "product_name": _clean_text(result.get("product_name")) if is_related else None,
        "confidence": result.get("confidence") if result.get("confidence") in CONFIDENCE_LEVELS else "low",
        "reason": _clean_text(result.get("reason")) or "No rationale returned.",
    }
