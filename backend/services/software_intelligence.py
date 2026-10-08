"""Product-centric software opportunity classification."""

import json
import os
import time
from typing import Any

import requests

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
CLASSIFIER_NAME = "hybrid_software_classifier"
CLASSIFIER_VERSION = "2"
PROMPT_VERSION = "software-v2"
WORK_TYPES = {"new_build", "enhancement", "integration", "implementation", "support", "other"}
CONFIDENCE_LEVELS = {"high", "medium", "low"}
CLASSIFICATIONS = {
    "software",
    "hardware",
    "civil_works",
    "consulting",
    "training",
    "infrastructure",
    "telecommunications",
    "data_services",
    "general_services",
    "goods_supply",
    "mixed",
    "unclear",
}

POSITIVE_SIGNALS = {
    "custom_software": ("develop", "build", "web portal", "mobile application", "software platform"),
    "information_system": ("information system", "management information system", "digital system", "registry system"),
    "integration": ("api integration", "system integration", "interoperability", "integrate with"),
    "application_support": ("maintain application", "application support", "software support", "system maintenance"),
}
NEGATIVE_SIGNALS = {
    "civil_works": ("road construction", "bridge rehabilitation", "building construction", "water pipes"),
    "goods_supply": ("vehicle supply", "office furniture", "medical equipment", "solar panels"),
    "services_only": ("security guards", "cleaning services", "conference organization"),
}


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


def _rule_signals(context: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    normalized = context.lower()
    positive, negative = [], []
    for signal, terms in POSITIVE_SIGNALS.items():
        for term in terms:
            if term in normalized:
                positive.append({"signal": signal, "term": term})
    for signal, terms in NEGATIVE_SIGNALS.items():
        for term in terms:
            if term in normalized:
                negative.append({"signal": signal, "term": term})
    return positive, negative


def classify_software_opportunity_with_gemini(notice: dict[str, Any]) -> dict[str, Any]:
    """Classify by requested deliverable; product categories are deliberately open-ended."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is not configured.")
    context = _notice_context(notice)
    if not context:
        raise ValueError("The notice has no title, description, or project context to classify.")
    positive_signals, negative_signals = _rule_signals(context)
    instruction = """You classify procurement notices by the PRIMARY PRODUCT OR DELIVERABLE. Return JSON only:
{"classification":"software|hardware|civil_works|consulting|training|infrastructure|telecommunications|data_services|general_services|goods_supply|mixed|unclear","is_software_related":true,"technology_related":true,"classification_status":"classified|needs_review|insufficient_evidence","work_type":"new_build|enhancement|integration|implementation|support|other","primary_deliverable":"specific deliverable","product_category":"controlled reusable category such as health_information_system, enterprise_resource_planning, data_platform_and_analytics, e_government_platform, api_and_system_integration, mobile_application, web_application, registry_and_database, unknown_software, or null","product_subcategory":"more specific domain detail or null","product_name":"specific solution/product sought, or null","confidence":"high|medium|low","reason":"evidence-based explanation","evidence":[{"field":"title|description|project_name","quote":"short exact quote","signal":"why it matters"}]}
Classify the buyer's main deliverable, not incidental technology. Hardware-only, civil works, training-only, and general consulting are not software. Use needs_review for contradictory or borderline evidence and insufficient_evidence when the notice lacks enough text."""
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
    classification = result.get("classification") if result.get("classification") in CLASSIFICATIONS else "unclear"
    is_related = result.get("is_software_related") is True and classification == "software"
    status = result.get("classification_status")
    if status not in {"classified", "needs_review", "insufficient_evidence"}:
        status = "classified" if context else "insufficient_evidence"
    evidence = result.get("evidence") if isinstance(result.get("evidence"), list) else []
    return {
        "is_software_related": is_related,
        "classification": classification,
        "classification_status": status,
        "technology_related": result.get("technology_related") is True,
        "primary_deliverable": _clean_text(result.get("primary_deliverable")),
        "work_type": result.get("work_type") if is_related and result.get("work_type") in WORK_TYPES else "other",
        "product_category": _clean_text(result.get("product_category")) if is_related else None,
        "product_subcategory": _clean_text(result.get("product_subcategory")) if is_related else None,
        "product_name": _clean_text(result.get("product_name")) if is_related else None,
        "confidence": result.get("confidence") if result.get("confidence") in CONFIDENCE_LEVELS else "low",
        "reason": _clean_text(result.get("reason")) or "No rationale returned.",
        "evidence": evidence[:8],
        "rule_signals": {"positive": positive_signals, "negative": negative_signals},
        "classifier_name": CLASSIFIER_NAME,
        "classifier_version": CLASSIFIER_VERSION,
        "prompt_version": PROMPT_VERSION,
        "classification_model": GEMINI_MODEL,
    }
