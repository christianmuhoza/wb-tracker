"""Tech classification logic for procurement notices."""

import re
from typing import Any

TECH_CATEGORY_KEYWORDS = {
    "Software / Platforms": [
        "software",
        "application",
        "app development",
        "application development",
        "software platform",
        "digital platform",
        "website",
        "portal",
        "erp",
        "mis",
        "management information system",
        "database",
        "cloud",
        "e-government",
        "e government",
        "digital system",
        "api",
        "programming",
        "system integration",
        "systems integration",
        "software development",
        "web development",
        "mobile application",
        "mobile app",
        "saas",
        "middleware",
        "microservice",
        "api integration",
    ],
    "ICT Equipment": [
        "ict",
        "computer",
        "computers",
        "laptop",
        "laptops",
        "tablet",
        "tablets",
        "server",
        "servers",
        "hardware",
        "printer",
        "scanner",
        "data center",
        "datacenter",
        "workstation",
        "peripheral",
        "peripherals",
        "it equipment",
    ],
    "Connectivity / Telecom": [
        "network",
        "networking",
        "internet",
        "connectivity",
        "telecom",
        "telecommunication",
        "telecommunications",
        "fiber",
        "fibre",
        "broadband",
        "lan",
        "wan",
        "radio communication",
        "voip",
        "vpn",
        "5g",
        "4g",
        "lte",
        "wifi",
        "wireless",
        "satellite communication",
        "vsat",
        "router",
        "modem",
        "gateway",
    ],
    "Cybersecurity / Data": [
        "cybersecurity",
        "cyber security",
        "security information",
        "firewall",
        "backup",
        "disaster recovery",
        "data protection",
        "biometric",
        "gis",
        "geographic information system",
        "penetration testing",
        "penetration test",
        "vulnerability assessment",
        "encryption",
        "identity management",
        "access control",
        "threat intelligence",
        "security operations center",
        "zero trust",
        "endpoint security",
        "network security",
        "cloud security",
    ],
    "Digital Services": [
        "digital",
        "digitization",
        "digitisation",
        "automation",
        "call center",
        "call centre",
        "cctv",
        "surveillance",
        "smart",
        "information technology",
        "it infrastructure",
        "it services",
        "it consulting",
        "it support",
        "help desk",
        "managed services",
        "business intelligence",
        "data analytics",
        "digital transformation",
        "technical support",
    ],
    "AI & Emerging Tech": [
        "artificial intelligence",
        "machine learning",
        "deep learning",
        "neural network",
        "nlp",
        "natural language processing",
        "computer vision",
        "robotics",
        "big data",
        "data science",
        "iot",
        "internet of things",
        "blockchain",
        "predictive analytics",
        "intelligent system",
        "autonomous",
        "drone",
        "uav",
    ],
}

TECH_NOTICE_KEYWORDS = sorted(
    {keyword for keywords in TECH_CATEGORY_KEYWORDS.values() for keyword in keywords} | {"i.t."}
)

TECH_BIDDER_NAME_KEYWORDS = [
    "technology",
    "technologies",
    "tech",
    "systems",
    "solutions",
    "software",
    "computer",
    "computers",
    "network",
    "networks",
    "telecom",
    "digital",
    "ict",
    "information technology",
    "data",
    "cyber",
    "communications",
    "ai",
    "analytics",
    "cloud",
    "internet",
    "security",
    "intelligence",
    "robotics",
    "blockchain",
    "infrastructure",
    "integration",
    "programming",
    "managed services",
]


def _keyword_pattern(keyword: str) -> str:
    escaped = re.escape(keyword.lower())
    escaped = escaped.replace(r"\ ", r"\s+")
    return rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"


def _sql_keyword_core(keyword: str) -> str:
    escaped = re.escape(keyword.lower())
    return escaped.replace(r"\ ", r"[[:space:]]+")


TECH_CATEGORY_PATTERNS = {
    category: [re.compile(_keyword_pattern(keyword), re.IGNORECASE) for keyword in keywords]
    for category, keywords in TECH_CATEGORY_KEYWORDS.items()
}

TECH_NOTICE_SQL_PATTERN = (
    rf"(^|[^a-z0-9])({'|'.join(_sql_keyword_core(keyword) for keyword in TECH_NOTICE_KEYWORDS)})([^a-z0-9]|$)"
)

TECH_BIDDER_PATTERNS = [re.compile(_keyword_pattern(keyword), re.IGNORECASE) for keyword in TECH_BIDDER_NAME_KEYWORDS]

TECH_BIDDER_SQL_PATTERN = (
    rf"(^|[^a-z0-9])({'|'.join(_sql_keyword_core(keyword) for keyword in TECH_BIDDER_NAME_KEYWORDS)})([^a-z0-9]|$)"
)


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
    return f"({expr} ~* %s)", [TECH_NOTICE_SQL_PATTERN]


def build_tech_bidder_condition(alias: str = ""):
    prefix = f"{alias}." if alias else ""
    expr = (
        "LOWER(CONCAT_WS(' ', "
        f"{prefix}name, {prefix}contact_org, {prefix}category, "
        f"{prefix}business_model, {prefix}core_products, {prefix}corporate_activities"
        "))"
    )
    return f"({expr} ~* %s)", [TECH_BIDDER_SQL_PATTERN]


def classify_notice_tech(notice: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(
        str(notice.get(key) or "")
        for key in ("title", "project_name", "description", "procurement_method", "borrower_bid_reference")
    ).lower()

    matched_categories = []
    for category, patterns in TECH_CATEGORY_PATTERNS.items():
        if any(pattern.search(text) for pattern in patterns):
            matched_categories.append(category)

    return {
        "is_tech": bool(matched_categories),
        "tech_category": ", ".join(matched_categories) if matched_categories else None,
    }


def looks_like_tech_bidder(row: dict[str, Any]) -> bool:
    text = " ".join(
        str(row.get(key) or "")
        for key in ("name", "contact_org", "category", "business_model", "core_products", "corporate_activities")
    ).lower()
    return any(pattern.search(text) for pattern in TECH_BIDDER_PATTERNS)
