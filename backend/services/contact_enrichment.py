import os
import re
import requests
from typing import Optional, Dict, Any, List

import logging
logger = logging.getLogger(__name__)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")


def _search_tavily(company: str, country: str = "") -> Optional[List[str]]:
    if not TAVILY_API_KEY:
        return None
    query = f"{company} {country} contact email phone LinkedIn".strip()
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "search_depth": "basic",
                "max_results": 5,
                "include_answer": False,
                "include_raw_content": True,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        texts = []
        for r in results:
            raw = r.get("raw_content", "") or r.get("content", "")
            if raw:
                texts.append(raw)
        return texts
    except Exception as e:
        logger.warning(f"Tavily search failed: {e}")
        return None


EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}(?:\s*(?:ext|extension|x)\s*\d{1,5})?"
)
LINKEDIN_RE = re.compile(
    r"https?://(?:www\.)?linkedin\.com/(?:company|in)/[a-zA-Z0-9_-]+"
)


def _extract_contact_info(texts: List[str]) -> Dict[str, Any]:
    emails = set()
    phones = set()
    linkedins = set()

    for text in texts:
        if not text:
            continue
        for m in EMAIL_RE.finditer(text):
            email = m.group(0).lower().strip()
            if not email.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
                emails.add(email)
        for m in PHONE_RE.finditer(text):
            phone = m.group(0).strip()
            if 7 <= len(phone) <= 25:
                phones.add(phone)
        for m in LINKEDIN_RE.finditer(text):
            linkedins.add(m.group(0).rstrip("/"))

    result = {}
    if emails:
        sorted_emails = sorted(emails)
        result["contact_email"] = next(
            (e for e in sorted_emails if not e.endswith(("@example.com", "@domain.com"))),
            sorted_emails[0],
        )
    if phones:
        filtered = [p for p in sorted(phones) if re.match(r'^[\+\(]?\d[\d\s\-\(\)\.]{6,}\d$', p.strip())]
        if filtered:
            result["contact_phone"] = ", ".join(filtered[:3])
    if linkedins:
        result["linkedin_url"] = ", ".join(sorted(linkedins)[:2])
    return result


def search_company_contact(company: str, country: str = "") -> Dict[str, Any]:
    if not TAVILY_API_KEY:
        logger.warning("TAVILY_API_KEY not set. Set it in .env for contact enrichment.")
        return {}
    texts = _search_tavily(company, country)
    if not texts:
        return {}
    return _extract_contact_info(texts)
