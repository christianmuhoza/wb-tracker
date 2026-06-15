"""Tech classification logic for procurement notices."""

from typing import Dict, Any

TECH_CATEGORY_KEYWORDS = {
    "Software / Platforms": [
        "software", "application", "app development", "platform", "website",
        "portal", "erp", "mis", "management information system", "database",
        "cloud", "e-government", "e government", "digital system",
    ],
    "ICT Equipment": [
        "ict", "computer", "computers", "laptop", "laptops", "tablet",
        "tablets", "server", "servers", "hardware", "printer", "scanner",
        "data center", "datacenter", "equipment",
    ],
    "Connectivity / Telecom": [
        "network", "networking", "internet", "connectivity", "telecom",
        "telecommunication", "fiber", "fibre", "broadband", "lan", "wan",
        "radio communication",
    ],
    "Cybersecurity / Data": [
        "cybersecurity", "cyber security", "security information", "firewall",
        "backup", "disaster recovery", "data protection", "biometric",
        "gis", "geographic information system",
    ],
    "Digital Services": [
        "digital", "digitization", "digitisation", "automation", "call center",
        "call centre", "cctv", "surveillance", "smart", "information technology",
    ],
}

TECH_NOTICE_KEYWORDS = sorted({
    keyword
    for keywords in TECH_CATEGORY_KEYWORDS.values()
    for keyword in keywords
} | {"it ", " i.t", "ict "})

TECH_BIDDER_NAME_KEYWORDS = [
    "technology", "technologies", "tech", "systems", "solutions", "software",
    "computer", "computers", "network", "networks", "telecom", "digital",
    "ict", "information technology", "data", "cyber", "communications",
]


def _tech_text_expr(alias: str = "") -> str:
    prefix = f"{alias}." if alias else ""
    return (
        "LOWER(CONCAT_WS(' ', "
        f"{prefix}title, {prefix}project_name, {prefix}description, "
        f"{prefix}procurement_method, {prefix}borrower_bid_reference"
        "))"
    )


def build_tech_notice_condition(alias: str = ""):
    expr = _tech_text_expr(alias)
    return "(" + " OR ".join([f"{expr} LIKE %s" for _ in TECH_NOTICE_KEYWORDS]) + ")", [
        f"%{keyword.lower()}%" for keyword in TECH_NOTICE_KEYWORDS
    ]


def classify_notice_tech(notice: Dict[str, Any]) -> Dict[str, Any]:
    text = " ".join(str(notice.get(key) or "") for key in (
        "title", "project_name", "description", "procurement_method", "borrower_bid_reference"
    )).lower()

    matched_categories = []
    for category, keywords in TECH_CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            matched_categories.append(category)

    return {
        "is_tech": bool(matched_categories),
        "tech_category": ", ".join(matched_categories) if matched_categories else None,
    }


def looks_like_tech_bidder(row: Dict[str, Any]) -> bool:
    text = " ".join(str(row.get(key) or "") for key in ("name", "contact_org", "category")).lower()
    return any(keyword in text for keyword in TECH_BIDDER_NAME_KEYWORDS)
