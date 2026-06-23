import os
import time
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from services.contact_enrichment import _search_tavily

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")


def classify_and_enrich_with_gemini(
    company: str,
    country: str = "",
    bids: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Enrich bidder information using Gemini LLM.
    Combines Tavily web search results, bid history, and company name/country.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is not configured. Please add it to your .env file.")

    # 1. Gather context from web search
    search_texts = []
    try:
        texts = _search_tavily(company, country)
        if texts:
            search_texts = texts
    except Exception as e:
        logger.warning(f"Web search failed during Gemini enrichment: {e}")

    search_context = "\n---\n".join(search_texts) if search_texts else "No web search results available."

    # 2. Gather context from bid history
    bid_list = []
    if bids:
        for b in bids[:10]:  # Limit to 10 bids to save context window
            title = b.get("title") or b.get("latest_bid_title") or "Unnamed Bid"
            role = b.get("role") or "Bidder"
            won = "Won" if b.get("won") else "Participated"
            amount = f"{b.get('bid_amount') or b.get('award_amount') or ''} {b.get('bid_currency') or b.get('currency') or ''}".strip()
            bid_list.append(f"- {title} (Role: {role}, Status: {won}, Amount: {amount})")
    
    bids_context = "\n".join(bid_list) if bid_list else "No local bid history available."

    # 3. Build Prompt
    system_instruction = (
        "You are an expert corporate intelligence assistant.\n"
        "Your task is to classify and enrich a company/bidder based on their name, country, "
        "historical bids they bidded on, and search engine results.\n"
        "Analyze the company's business model, core products, and corporate activities.\n"
        "You MUST return a JSON object matching this schema:\n"
        "{\n"
        "  \"category\": \"Software Development\" | \"Construction & Civil Engineering\" | \"General Trading, Wholesale, & Institutional Procurement\" | \"Consulting & Advisory Services\" | \"ICT Hardware & Networking\" | \"Other\",\n"
        "  \"business_model\": \"A brief description of their business model (1-2 sentences).\",\n"
        "  \"core_products\": \"A brief list/description of their core products/services.\",\n"
        "  \"corporate_activities\": \"A brief summary of their main corporate activities.\",\n"
        "  \"contact_email\": \"The official contact email address of the company. Scan the web search results carefully for a real, specific email address (e.g. info@company.com or office@company.com). Avoid placeholder domains (like example.com or domain.com) or unrelated domain webmaster emails. If none is explicitly found, construct a standard info@ or contact@ email using their official website domain (if one is clearly listed in the search results). Otherwise, return null.\",\n"
        "  \"contact_phone\": \"The official company contact phone number (including country code) extracted from the search results, or null.\",\n"
        "  \"linkedin_url\": \"Official LinkedIn company profile URL if found in the search results, or null.\"\n"
        "}\n"
        "Choose the classification category strictly from the provided list. Ensure it accurately reflects the company's core operations.\n"
        "Ensure the response is valid JSON and contains only the JSON object."
    )

    prompt = (
        f"Company Name: {company}\n"
        f"Country of Origin: {country or 'Unknown'}\n\n"
        f"### Bid History:\n{bids_context}\n\n"
        f"### Web Search Results about this Company:\n{search_context}\n\n"
        "Analyze all the information above and produce the requested JSON."
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": f"{system_instruction}\n\n{prompt}"
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }

    max_retries = 4
    backoff = 1.0
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, json=payload, timeout=30)
            if resp.status_code in (429, 503):
                if attempt < max_retries - 1:
                    logger.warning(f"Gemini API returned {resp.status_code}. Retrying in {backoff} seconds...")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
            resp.raise_for_status()
            result_data = resp.json()
            break
        except requests.exceptions.RequestException as req_err:
            if attempt < max_retries - 1:
                logger.warning(f"Gemini API request failed ({req_err}). Retrying in {backoff} seconds...")
                time.sleep(backoff)
                backoff *= 2
                continue
            raise req_err

    try:
        text_response = result_data["candidates"][0]["content"]["parts"][0]["text"]
        enriched_info = json.loads(text_response.strip())
        return enriched_info
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        logger.error(f"Failed to parse Gemini response: {e}. Raw response: {result_data}")
        raise ValueError("Invalid response format received from Gemini API.")
