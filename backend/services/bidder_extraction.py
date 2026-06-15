"""Bidder extraction from World Bank procurement notice descriptions."""

import re
import json
from typing import Optional, List, Dict, Any, Tuple

import requests
from bs4 import BeautifulSoup


def _clean_name(text: str) -> str:
    """Strip noise and return a clean company name, or empty string."""
    if not text:
        return ''
    text = re.sub(r'^[\d\.\-\|\*\#\s]+', '', text.strip())
    text = re.sub(r'^(?:[A-Z]{2,4}\s+[\d,]+(?:\.\d+)?\s+)+', '', text.strip())
    text = re.sub(r'[\.\,\;\:\!\?]+$', '', text.strip())
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) < 4:
        return ''
    NOISE_WORDS = {
        'n/a', 'none', 'nil', 'not applicable', 'tbd', 'pending',
        'bid amount', 'firm name', 'company name', 'bidder name',
        'name', 'amount', 'currency', 'usd', 'eur', 'description',
        'evaluated', 'awarded', 'selected', 'contract', 'procurement',
        'total', 'subtotal', 'price', 'cost', 'value',
    }
    if text.lower() in NOISE_WORDS:
        return ''
    return text


def _dedupe(names: list) -> list:
    """Deduplicate preserving first-seen order, case-insensitive."""
    seen = set()
    result = []
    for name in names:
        key = name.lower().strip()
        if key and key not in seen:
            seen.add(key)
            result.append(name)
    return result


AWARD_BIDDER_SECTION_SPECS = [
    ("awarded", re.compile(r'Awarded\s+(?:Firm|Company|Bidder|Contractor|Consultant|Supplier)\(?s?\)?\s*[:\-]', re.IGNORECASE)),
    ("evaluated", re.compile(r'Evaluated\s+(?:Firm|Bidder|Company|Contractor|Consultant|Supplier)\(?s?\)?\s*[:\-]', re.IGNORECASE)),
    ("rejected", re.compile(r'Rejected\s+(?:Firm|Bidder|Company|Contractor|Consultant|Supplier)\(?s?\)?\s*[:\-]', re.IGNORECASE)),
    ("unsuccessful", re.compile(r'Unsuccessful\s+(?:Firm|Bidder|Company|Contractor|Consultant|Supplier)\(?s?\)?\s*[:\-]', re.IGNORECASE)),
    ("disqualified", re.compile(r'Disqualified\s+(?:Firm|Bidder|Company|Contractor|Consultant|Supplier)\(?s?\)?\s*[:\-]', re.IGNORECASE)),
    ("responsive", re.compile(r'Responsive\s+(?:Firm|Bidder|Company|Contractor|Consultant|Supplier)\(?s?\)?\s*[:\-]', re.IGNORECASE)),
    ("participating", re.compile(r'Participating\s+(?:Firms?|Bidders?|Companies|Contractors|Suppliers)\s*[:\-]', re.IGNORECASE)),
]

AWARD_SECTION_STOP_MARKERS = [
    re.compile(r'Country\s*:', re.IGNORECASE),
    re.compile(r'Registry\s+ID\s*:', re.IGNORECASE),
    re.compile(r'Beneficial\s+Ownership', re.IGNORECASE),
    re.compile(r'Bid\s+Price\s+at\s+Opening', re.IGNORECASE),
    re.compile(r'Evaluated\s+Bid\s+Price', re.IGNORECASE),
    re.compile(r'Signed\s+Contract\s+Price', re.IGNORECASE),
    re.compile(r'Final\s+Evaluation\s+Price', re.IGNORECASE),
    re.compile(r'Reason\s+for\s+Rejection', re.IGNORECASE),
    re.compile(r'Scores?\s+', re.IGNORECASE),
    re.compile(r'Rank\s*:', re.IGNORECASE),
    re.compile(r'Price\s*:\s*Currency', re.IGNORECASE),
]

NAME_WITH_ID_RE = re.compile(r'[A-Z0-9&.,\'"/\-]+(?:\s+[A-Z0-9&.,\'"/\-]+)*\s*\(\d{4,}\)')
COUNTRY_LINE_RE = re.compile(r'^Country\s*:\s*(.+)$', re.IGNORECASE)
AMOUNT_LINE_LABELS = {
    "opening_amount": re.compile(r'^Bid\s+Price\s+at\s+Opening\s*:?\s*(.*)$', re.IGNORECASE),
    "evaluated_amount": re.compile(r'^Evaluated\s+Bid\s+Price\s*:?\s*(.*)$', re.IGNORECASE),
    "signed_amount": re.compile(r'^Signed\s+Contract\s+Price\s*:?\s*(.*)$', re.IGNORECASE),
    "final_amount": re.compile(r'^Final\s+Evaluation\s+Price\s*:?\s*(.*)$', re.IGNORECASE),
}


def _extract_bidder_names_from_block(text: str) -> list:
    """Extract repeated bidder/company names from a single award section block."""
    if not text:
        return []
    normalized = re.sub(r'\s+', ' ', text).strip()
    names = []
    for match in NAME_WITH_ID_RE.finditer(normalized):
        name = _clean_name(match.group(0).strip())
        if name:
            names.append(name)
    return _dedupe(names)


def _clean_award_lines(text: str) -> List[str]:
    lines = []
    for raw_line in (text or "").splitlines():
        line = re.sub(r'^[\u2022\u25cf\u25aa\u25e6\uf0d8\-\*\t ]+', '', raw_line).strip()
        line = re.sub(r'\s+', ' ', line)
        if line:
            lines.append(line)
    return lines


def _parse_amount_value(text: str) -> tuple[Optional[float], Optional[str]]:
    if not text:
        return None, None
    normalized = re.sub(r'\s+', ' ', text).strip()
    match = re.search(r'([A-Z][A-Z\.\- ]{1,20})\s+([\d,]+(?:\.\d+)?)', normalized)
    if not match:
        return None, None
    currency = re.sub(r'\s+', ' ', match.group(1)).strip(" :")
    amount_text = match.group(2).replace(',', '')
    try:
        amount = float(amount_text)
    except ValueError:
        return None, currency or None
    return amount, currency or None


def _infer_notice_category(notice: Dict[str, Any], description: str = "") -> Optional[str]:
    reference = " ".join(filter(None, [
        str(notice.get("borrower_bid_reference") or ""),
        str(notice.get("title") or ""),
        str(notice.get("procurement_method") or ""),
        str(description or ""),
    ])).lower()

    if any(token in reference for token in ("-cw-", "construction", "rehabilitation", "civil works", "works")):
        return "Works"
    if any(token in reference for token in ("-go-", "supply of", "goods", "equipment", "vehicle", "camera", "computers", "furniture")):
        return "Goods"
    if any(token in reference for token in ("-cs-", "consultant", "consulting", "cqs", "qcbs", "individual consultant")):
        return "Consulting Services"
    if any(token in reference for token in ("-nc-", "non-consult", "service", "training", "maintenance", "installation")):
        return "Non-Consulting Services"
    return None


def _merge_categories(existing: Optional[str], new_value: Optional[str]) -> Optional[str]:
    values = []
    for raw in (existing, new_value):
        if not raw:
            continue
        for part in str(raw).split(","):
            cleaned = part.strip()
            if cleaned and cleaned.lower() not in {v.lower() for v in values}:
                values.append(cleaned)
    return ", ".join(values) if values else None


def parse_notice_bidder_details(text: str) -> List[Dict[str, Any]]:
    """Parse structured Contract Award bidder sections into bidder-level records."""
    lines = _clean_award_lines(text)
    if not lines:
        return []

    section_alias = {name: name for name, _ in AWARD_BIDDER_SECTION_SPECS}
    details: List[Dict[str, Any]] = []
    current_section: Optional[str] = None
    current: Optional[Dict[str, Any]] = None

    def start_bidder(name: str):
        nonlocal current
        if current and current.get("name"):
            details.append(current)
        current = {
            "name": name,
            "section": current_section,
            "country": None,
            "opening_amount": None,
            "opening_currency": None,
            "evaluated_amount": None,
            "evaluated_currency": None,
            "signed_amount": None,
            "signed_currency": None,
            "final_amount": None,
            "final_currency": None,
        }

    index = 0
    while index < len(lines):
        line = lines[index]
        matched_section = False
        for section_name, pattern in AWARD_BIDDER_SECTION_SPECS:
            if pattern.match(line):
                current_section = section_alias[section_name]
                matched_section = True
                remainder = pattern.sub("", line).strip(" :.-")
                if remainder:
                    match = NAME_WITH_ID_RE.search(remainder)
                    if match:
                        start_bidder(_clean_name(match.group(0)))
                break
        if matched_section:
            index += 1
            continue

        name_match = NAME_WITH_ID_RE.search(line)
        if current_section and name_match:
            start_bidder(_clean_name(name_match.group(0)))
            index += 1
            continue

        if current:
            country_match = COUNTRY_LINE_RE.match(line)
            if country_match:
                current["country"] = country_match.group(1).strip()
                index += 1
                continue

            for amount_key, pattern in AMOUNT_LINE_LABELS.items():
                amount_match = pattern.match(line)
                if not amount_match:
                    continue
                raw_amount = amount_match.group(1).strip()
                if not raw_amount and index + 1 < len(lines):
                    raw_amount = lines[index + 1].strip()
                    index += 1
                amount, currency = _parse_amount_value(raw_amount)
                current[amount_key] = amount
                current[amount_key.replace("_amount", "_currency")] = currency
                break

        index += 1

    if current and current.get("name"):
        details.append(current)

    finalized = []
    seen = set()
    for item in details:
        name = item.get("name")
        if not name:
            continue
        key = name.lower().strip()
        if key in seen:
            continue
        seen.add(key)
        section = item.get("section")
        preferences = (
            ("signed_amount", "signed_currency"),
            ("final_amount", "final_currency"),
            ("evaluated_amount", "evaluated_currency"),
            ("opening_amount", "opening_currency"),
        ) if section == "awarded" else (
            ("evaluated_amount", "evaluated_currency"),
            ("final_amount", "final_currency"),
            ("opening_amount", "opening_currency"),
            ("signed_amount", "signed_currency"),
        )
        chosen_amount = None
        chosen_currency = None
        for amount_key, currency_key in preferences:
            if item.get(amount_key) is not None:
                chosen_amount = item.get(amount_key)
                chosen_currency = item.get(currency_key)
                break
        finalized.append({
            "name": name,
            "section": section,
            "country": item.get("country"),
            "opening_amount": item.get("opening_amount"),
            "opening_currency": item.get("opening_currency"),
            "evaluated_amount": item.get("evaluated_amount"),
            "evaluated_currency": item.get("evaluated_currency"),
            "signed_amount": item.get("signed_amount"),
            "signed_currency": item.get("signed_currency"),
            "final_amount": item.get("final_amount"),
            "final_currency": item.get("final_currency"),
            "amount": chosen_amount,
            "currency": chosen_currency,
            "role": section.replace("_", " ").title() if section else None,
        })

    return finalized


def _extract_bidders_by_section(text: str) -> Dict[str, List[str]]:
    """Parse structured award sections and return bidder names by section label."""
    if not text:
        return {}

    normalized = re.sub(r'\s+', ' ', text).strip()
    matches = []
    for section_name, pattern in AWARD_BIDDER_SECTION_SPECS:
        for match in pattern.finditer(normalized):
            matches.append((match.start(), match.end(), section_name))

    if not matches:
        return {}

    matches.sort(key=lambda item: item[0])
    sections: Dict[str, List[str]] = {}

    for index, (_, block_start, section_name) in enumerate(matches):
        next_start = matches[index + 1][0] if index + 1 < len(matches) else len(normalized)
        block = normalized[block_start:next_start].strip()
        names = _extract_bidder_names_from_block(block)
        if names:
            sections.setdefault(section_name, [])
            sections[section_name].extend(names)

    return {key: _dedupe(values) for key, values in sections.items()}


def _extract_from_json(data, depth=0) -> list:
    """Walk a JSON structure looking for company/firm name strings."""
    if depth > 6:
        return []
    results = []
    if isinstance(data, dict):
        for key, val in data.items():
            if any(kw in key.lower() for kw in ('firm', 'bidder', 'company', 'contractor', 'supplier')):
                if isinstance(val, str) and len(val) > 3:
                    name = _clean_name(val)
                    if name:
                        results.append(name)
            else:
                results += _extract_from_json(val, depth + 1)
    elif isinstance(data, list):
        for item in data:
            results += _extract_from_json(item, depth + 1)
    return results


def extract_bidders_list(text: str) -> list:
    """
    Return ordered deduplicated list of company/bidder names from a WB notice description.
    Covers multiple known World Bank Contract Award description formats.
    """
    if not text:
        return []

    section_bidders = _extract_bidders_by_section(text)
    if section_bidders:
        ordered = []
        for section_name in ("awarded", "evaluated", "rejected", "unsuccessful", "disqualified", "responsive", "participating"):
            ordered.extend(section_bidders.get(section_name, []))
        if ordered:
            return _dedupe(ordered)

    found = []

    for m in re.finditer(
        r'Bidder\s*\d+\s*[:\.\-]\s*(.+?)(?=\n|Bidder\s*\d+|$)',
        text, flags=re.IGNORECASE
    ):
        name = _clean_name(m.group(1))
        if name:
            found.append(name)

    label_patterns = [
        r'Awarded\s+(?:Firm|Company|Bidder|Contractor|Consultant|Supplier)\(?s?\)?[:\-]\s*(.+)',
        r'Evaluated\s+(?:Firm|Bidder|Company)\(?s?\)?[:\-]\s*(.+)',
        r'Selected\s+(?:Firm|Company|Bidder|Contractor)\(?s?\)?[:\-]\s*(.+)',
        r'Participating\s+(?:Firms?|Bidders?|Companies)\s*[:\-]\s*(.+)',
        r'(?:Firm|Company|Contractor|Consultant|Supplier)\s+Name\s*[:\-]\s*(.+)',
    ]
    for pat in label_patterns:
        for m in re.finditer(pat, text, flags=re.IGNORECASE | re.MULTILINE):
            block = m.group(1).strip()
            for part in re.split(r'[;\n]', block):
                name = _clean_name(part)
                if name and len(name) > 3:
                    found.append(name)

    for m in re.finditer(
        r'^\s*\d+\s*[\|\.]\s*([A-Z][A-Za-z\s&\.,\-\(\)\']{3,}?)\s*[\|,]',
        text, flags=re.MULTILINE
    ):
        name = _clean_name(m.group(1))
        if name and len(name) > 3:
            found.append(name)

    if not found:
        award_patterns = [
            r'contract\s+(?:was\s+)?awarded\s+to\s+([A-Z][A-Za-z\s&\.,\-\(\)\']{3,60}?)(?:\s+for|\s+in|\s+to|\.|,|$)',
            r'([A-Z][A-Za-z\s&\.,\-\(\)\']{3,60}?)\s+(?:was\s+)?(?:selected|awarded|chosen)\s+(?:as\s+)?(?:the\s+)?(?:winning|successful)',
        ]
        for pat in award_patterns:
            for m in re.finditer(pat, text, flags=re.IGNORECASE | re.MULTILINE):
                name = _clean_name(m.group(1))
                if name and len(name) > 3:
                    found.append(name)

    return _dedupe(found)


def extract_bidders_from_description(text: str) -> str | None:
    """Return semicolon-separated bidder names, or None if nothing found."""
    if not text:
        return None
    bidders = extract_bidders_list(text)
    return "; ".join(bidders) if bidders else None


def extract_awarded_bidders(text: str) -> list:
    """Return only companies explicitly identified as winners in the description."""
    if not text:
        return []

    section_bidders = _extract_bidders_by_section(text)
    if section_bidders.get("awarded"):
        return _dedupe(section_bidders["awarded"])

    winners = []
    winner_patterns = [
        r'Awarded\s+(?:Firm|Company|Bidder|Contractor|Consultant|Supplier)\(?s?\)?[:\-]\s*(.+)',
        r'Selected\s+(?:Firm|Company|Bidder|Contractor)\(?s?\)?[:\-]\s*(.+)',
        r'contract\s+(?:was\s+)?awarded\s+to\s+([A-Z][A-Za-z\s&\.,\-\(\)\']{3,60}?)(?:\s+for|\s+in|\.|,|$)',
        r'([A-Z][A-Za-z\s&\.,\-\(\)\']{3,60}?)\s+(?:was\s+)?(?:selected|awarded)\s+(?:as\s+)?(?:the\s+)?(?:winning|successful)',
    ]
    for pat in winner_patterns:
        for m in re.finditer(pat, text, flags=re.IGNORECASE | re.MULTILINE):
            block = m.group(1).strip()
            for part in re.split(r'[;\n]', block):
                name = _clean_name(part)
                if name and len(name) > 3:
                    winners.append(name)

    return _dedupe(winners)


def fetch_bidders_from_detail_page(notice_id: str, fallback_url: str = "") -> list:
    """Fetch the WB procurement detail page and extract ALL bidder company names."""
    if fallback_url and "procurement-detail" in fallback_url:
        detail_url = fallback_url
    elif notice_id:
        detail_url = f"https://projects.worldbank.org/en/projects-operations/procurement-detail/{notice_id}"
    else:
        return []

    try:
        resp = requests.get(
            detail_url,
            timeout=20,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; WBProcurementTracker/1.0)",
                "Accept": "text/html,application/xhtml+xml",
            }
        )
        resp.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    bidders = []

    for table in soup.find_all("table"):
        headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]
        name_col = None
        for i, h in enumerate(headers):
            if any(kw in h for kw in ("firm", "bidder", "company", "name", "contractor", "supplier")):
                name_col = i
                break
        if name_col is not None:
            for row in table.find_all("tr")[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) > name_col:
                    name = _clean_name(cells[name_col].get_text(strip=True))
                    if name and len(name) > 3:
                        bidders.append(name)

    if not bidders:
        page_text = soup.get_text(separator="\n", strip=True)
        bidders = extract_bidders_list(page_text)

    if not bidders:
        for script in soup.find_all("script", type="application/json"):
            try:
                data = json.loads(script.string or "")
                bidders += _extract_from_json(data)
            except Exception:
                pass

    return _dedupe(bidders)
