"""
World Bank Procurement Notice Fetcher
Tracks IFB (Invitation for Bids) and REOI notices for African countries.
Countries are read from the `target_countries` DB table (falls back to
FALLBACK_COUNTRIES if the table is empty).

Incremental: only fetches notices newer than the last successful run.
Stores results in:  procurement_notices
Logs every run in:  fetch_runs

Setup:
    pip install requests psycopg2-binary python-dotenv beautifulsoup4 schedule

Usage:
    python fetcher.py          # runs once then schedules daily at 06:00

.env:
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=wb_tracker
    DB_USER=postgres
    DB_PASSWORD=yourpassword
"""

import os
import time
import traceback
import logging
import requests
import psycopg2
import psycopg2.extras
from psycopg2.extras import execute_values
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import schedule

load_dotenv()

log_handlers = [logging.StreamHandler()]
try:
    log_handlers.insert(0, logging.FileHandler("fetcher.log", encoding="utf-8"))
except OSError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=log_handlers
)
log = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

API_BASE       = "https://search.worldbank.org/api/v2/procnotices"
ABSOLUTE_START = date(2025, 1, 1)   # Keep enough history so lower-volume countries are not excluded
ROWS_PER_PAGE  = 50
FALLBACK_ROWS_PER_PAGE = 10
COUNTRY_BATCH  = 5                  # Countries per API request (avoids 500s)
REQUEST_DELAY  = 1.2                # Seconds between batch calls

FALLBACK_COUNTRIES = [
    "Zambia", "Sierra Leone", "Ethiopia", "Malawi", "Kenya",
    "Ghana", "Angola", "Central African Republic", "Guinea",
    "Gambia", "Botswana", "Benin", "Somalia, Federal Republic of", "Tanzania", "Mozambique",
    "Rwanda"
]

DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "dbname":   os.getenv("DB_NAME",     "wb_tracker"),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

COUNTRY_QUERY_ALIASES = {
    "Gambia": ["Gambia, The"],
    "Somalia, Federal Republic of": ["Somalia", "Somalia, Federal Republic of", "Federal Republic of Somalia"],
}

COUNTRY_STORAGE_NORMALIZATION = {
    "Gambia, The": "Gambia",
    "Somalia": "Somalia, Federal Republic of",
    "Federal Republic of Somalia": "Somalia, Federal Republic of",
    "Somalia, Federal Republic of": "Somalia, Federal Republic of",
}


# ── Database helpers ──────────────────────────────────────────────────────────

def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def status_label(success: bool, row_count: int, fetched: int, error_msg: str | None = None) -> str:
    if error_msg:
        return "failed"
    if success and fetched > 0:
        return "success"
    if success and row_count > 0:
        return "no_recent_notices"
    if success:
        return "no_data"
    return "failed"


def init_db():
    """Create all tables and indexes if they don't exist."""
    ddl = """
    CREATE TABLE IF NOT EXISTS target_countries (
        id    SERIAL PRIMARY KEY,
        name  TEXT UNIQUE NOT NULL
    );

    INSERT INTO target_countries (name)
    SELECT unnest(ARRAY[
        'Zambia','Sierra Leone','Ethiopia','Malawi','Kenya',
        'Ghana','Angola','Central African Republic','Guinea',
        'Gambia','Botswana','Benin','Somalia, Federal Republic of','Tanzania','Mozambique',
        'Rwanda'
    ])
    ON CONFLICT (name) DO NOTHING;

    DELETE FROM target_countries WHERE name IN ('Uganda');
    UPDATE target_countries
    SET name = 'Somalia, Federal Republic of'
    WHERE name = 'Somalia';

    CREATE TABLE IF NOT EXISTS procurement_notices (
        id                      TEXT PRIMARY KEY,
        project_id              TEXT,
        project_name            TEXT,
        country                 TEXT,
        notice_no               TEXT,
        notice_type             TEXT,
        notice_status           TEXT,
        procurement_method      TEXT,
        language                TEXT,
        title                   TEXT,
        description             TEXT,
        borrower_bid_reference  TEXT,
        notice_date             DATE,
        submission_deadline     TIMESTAMPTZ,
        submission_date         DATE,
        contract_amount         NUMERIC,
        currency                TEXT,
        borrower                TEXT,
        contact_name            TEXT,
        contact_org             TEXT,
        contact_address         TEXT,
        contact_city            TEXT,
        contact_phone           TEXT,
        contact_email           TEXT,
        contact_website         TEXT,
        url                     TEXT,
        status                  TEXT,
        fetched_at              TIMESTAMPTZ DEFAULT NOW(),
        updated_at              TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_country     ON procurement_notices (country);
    CREATE INDEX IF NOT EXISTS idx_notice_type ON procurement_notices (notice_type);
    CREATE INDEX IF NOT EXISTS idx_notice_date ON procurement_notices (notice_date);
    CREATE INDEX IF NOT EXISTS idx_status      ON procurement_notices (status);

    CREATE TABLE IF NOT EXISTS fetch_runs (
        id          SERIAL PRIMARY KEY,
        run_at      TIMESTAMPTZ DEFAULT NOW(),
        country     TEXT,
        notice_type TEXT,
        fetched     INT,
        new_records INT,
        success     BOOLEAN,
        error_msg   TEXT
    );

    CREATE TABLE IF NOT EXISTS country_fetch_status (
        country              TEXT PRIMARY KEY,
        status               TEXT NOT NULL DEFAULT 'not_started',
        last_started_at      TIMESTAMPTZ,
        last_finished_at     TIMESTAMPTZ,
        last_success_at      TIMESTAMPTZ,
        last_attempted_since DATE,
        last_page_size       INT,
        fetched_records      INT DEFAULT 0,
        new_records          INT DEFAULT 0,
        total_available      INT DEFAULT 0,
        row_count            INT DEFAULT 0,
        first_notice_date    DATE,
        last_notice_date     DATE,
        error_msg            TEXT,
        api_url              TEXT,
        retry_count          INT DEFAULT 0,
        updated_at           TIMESTAMPTZ DEFAULT NOW()
    );
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()
    log.info("Database initialised.")


def get_target_countries() -> list[str]:
    """Read active countries from the target_countries table."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM target_countries ORDER BY name")
            rows = cur.fetchall()
    countries = [r[0] for r in rows]
    if not countries:
        log.warning("target_countries table is empty — using fallback list.")
        return FALLBACK_COUNTRIES
    return countries


def get_app_settings() -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            cur.execute("""
                INSERT INTO app_settings (key, value)
                VALUES
                    ('baseline_date', '2025-01-01'),
                    ('country_batch', '5'),
                    ('request_delay', '1.2'),
                    ('auto_sync_hour', '06:00')
                ON CONFLICT (key) DO NOTHING
            """)
            cur.execute("SELECT key, value FROM app_settings")
            rows = cur.fetchall()
        conn.commit()
    return {row[0]: row[1] for row in rows}


def get_fetch_start_date() -> date:
    """
    Fetch from configured baseline date if it has changed,
    otherwise fall back to last successful run minus 2 days (incremental).
    """
    settings = get_app_settings()
    baseline = settings.get("baseline_date", "2025-01-01")
    last_run_baseline = settings.get("last_run_baseline_date")

    try:
        configured_start = datetime.strptime(baseline, "%Y-%m-%d").date()
    except ValueError:
        configured_start = ABSOLUTE_START

    # If baseline_date has changed since the last fetch run, force using the new baseline
    if last_run_baseline != baseline:
        log.info(f"Baseline Date changed from {last_run_baseline} to {baseline}. Forcing full fetch from new baseline.")
        return configured_start

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT run_at::date
                FROM fetch_runs
                WHERE success = TRUE
                ORDER BY run_at DESC
                LIMIT 1
            """)
            row = cur.fetchone()

    if row and row[0]:
        since = max(configured_start, row[0] - timedelta(days=2))
    else:
        since = configured_start

    log.info(f"Incremental fetch: fetching from {since} (configured baseline is {configured_start})")
    return since


def chunk(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def expand_country_names_for_query(country_names: list[str]) -> list[str]:
    expanded: list[str] = []
    for country in country_names:
        aliases = COUNTRY_QUERY_ALIASES.get(country, [country])
        for alias in aliases:
            if alias not in expanded:
                expanded.append(alias)
    return expanded


def normalize_country_name(country: str | None) -> str:
    value = (country or "").strip()
    return COUNTRY_STORAGE_NORMALIZATION.get(value, value)


BORROWER_INSTITUTION_MARKERS = [
    "ministry", "ministere", "ministère", "department", "agency", "authority",
    "commission", "bureau", "office", "secretariat", "directorate", "directorat",
    "municipality", "corporation", "board", "unit", "institute",
    "company", "council", "government", "republic", "city", "province", "state",
    "ministério", "ministerio", "agence", "direction", "organisation", "organization",
]

BORROWER_LABEL_PATTERNS = [
    r'Borrower',
    r'Client',
    r'Implemented by',
    r'Host Institution',
    r'Executing Agency',
    r'Implementing Agency',
    r'Procuring Entity',
    r'Contracting Authority',
    r'Employer',
    r'Purchaser',
    r'Agency',
    r'Organization/Department',
    r'Organization',
    r'Department',
    r'Buyer',
    r'Acheteur',
    r'Ma[iî]tre d[’\' ]Ouvrage',
    r'Autorit[eé] contractante',
    r'Entit[eé] adjudicante',
    r'[ÓO]rg[aã]o executor',
]

BORROWER_BLOCKED_PHRASES = [
    'world bank',
    'ida credit',
    'ida grant',
    'loan no',
    'credit no',
    'project id',
    'notice no',
    'published',
    'request for bids',
    'request for quotations',
    'expression of interest',
    'appel d’offres',
    'appel d\'offres',
]

BORROWER_BLOCKED_PREFIXES = [
    'project:',
    'projet :',
    'projet:',
    'marché :',
    'marche :',
    'marché:',
    'marche:',
    'market:',
    'pays :',
    'pays:',
    'country:',
]

BORROWER_SUSPICIOUS_PATTERNS = [
    r'^\d+[\.\)]\s',
    r'\bbid document can be obtained\b',
    r'\bbids? (?:must|shall|will)\b',
    r'\binterested bidders\b',
    r'\blate bids?\b',
    r'\bsubmitted\b',
    r'\bopened on\b',
    r'\bclosed in the presence\b',
    r'\bdelivery period\b',
    r'\bpayment of\b',
]


def is_suspicious_borrower_value(value: str | None) -> bool:
    if not value:
        return True

    import re

    lowered = value.lower().strip()
    if len(lowered) > 140:
        return True
    if lowered.count(',') >= 4:
        return True
    return any(re.search(pattern, lowered, re.IGNORECASE) for pattern in BORROWER_SUSPICIOUS_PATTERNS)


def clean_borrower_candidate(value: str) -> str | None:
    import re

    candidate = re.sub(r'\s+', ' ', (value or '')).strip(" :;,-")
    candidate = re.sub(r'^(the)\s+', '', candidate, flags=re.IGNORECASE)
    candidate = re.sub(r'^(buyer|acheteur|borrower|client)\s*[:\-]\s*', '', candidate, flags=re.IGNORECASE)
    candidate = candidate[:200]

    if not candidate or len(candidate) <= 3:
        return None
    if any(candidate.lower().startswith(prefix) for prefix in BORROWER_BLOCKED_PREFIXES):
        return None
    if is_suspicious_borrower_value(candidate):
        return None
    return candidate


def borrower_candidate_score(value: str | None, project_name: str = "", source: str = "") -> int:
    """Score borrower candidates so stronger institution signals win over generic contact labels."""
    if not value:
        return -1

    import re

    lowered = value.lower()
    project_lower = (project_name or "").strip().lower()

    if lowered in {'borrower', 'client', 'project', 'program', 'programme', 'initiative'}:
        return -1
    if any(token in lowered for token in BORROWER_BLOCKED_PHRASES):
        return -1
    if project_lower and lowered == project_lower:
        return -1
    if '@' in lowered or 'http://' in lowered or 'https://' in lowered:
        return -1

    score = {
        'contact_org': 120,
        'raw_borrower': 90,
        'raw_procuring': 85,
        'description_label': 80,
        'description_line': 65,
        'raw_contactish': 40,
    }.get(source, 0)

    if any(marker in lowered for marker in BORROWER_INSTITUTION_MARKERS):
        score += 25
    if '(' in value and ')' in value:
        score += 10
    if len(value.split()) >= 3:
        score += 10
    if re.search(r'\b(minist[eè]re|ministry|department|agency|authority|buyer|acheteur|ma[iî]tre)\b', lowered, re.IGNORECASE):
        score += 15

    return score


def extract_borrower_candidates_from_description(text: str) -> list[tuple[str, str]]:
    """Extract likely host institutions from structured and narrative notice text."""
    if not text:
        return []

    import re

    log.info(f"  Extracting borrower from description: {text[:200]}...")
    candidates: list[tuple[str, str]] = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    label_regex = "|".join(BORROWER_LABEL_PATTERNS)

    for idx, line in enumerate(lines):
        same_line_match = re.match(rf'^\s*(?:{label_regex})\s*[:\-]\s*(.+)$', line, re.IGNORECASE)
        if same_line_match:
            candidate = clean_borrower_candidate(same_line_match.group(1))
            if candidate:
                candidates.append(("description_label", candidate))
                continue

        label_only_match = re.match(rf'^\s*(?:{label_regex})\s*[:\-]?\s*$', line, re.IGNORECASE)
        if label_only_match and idx + 1 < len(lines):
            candidate = clean_borrower_candidate(lines[idx + 1])
            if candidate:
                candidates.append(("description_label", candidate))
                continue

        if any(marker in line.lower() for marker in BORROWER_INSTITUTION_MARKERS):
            candidate = clean_borrower_candidate(line)
            if candidate:
                candidates.append(("description_line", candidate))

    seen = set()
    unique_candidates: list[tuple[str, str]] = []
    for source, candidate in candidates:
        key = candidate.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append((source, candidate))

    if unique_candidates:
        log.info(f"  Borrower candidates from description: {[c for _, c in unique_candidates[:5]]}")
    else:
        log.info("  No borrower found in description")

    return unique_candidates


# ── Borrower extraction helper ──────────────────────────────────────────────────

def extract_borrower_from_description(text: str) -> str | None:
    """Extract borrower/host institution from description text."""
    candidates = extract_borrower_candidates_from_description(text)
    return candidates[0][1] if candidates else None


def normalize_borrower_candidate(value: str | None, project_name: str = "") -> str | None:
    """Accept only institution-like borrower values and reject noisy candidates."""
    candidate = clean_borrower_candidate(str(value) if value is not None else "")
    if not candidate:
        return None
    if borrower_candidate_score(candidate, project_name=project_name, source="") < 0:
        return None
    return candidate[:200]


def choose_borrower(raw: dict, description: str, contact: dict, project_name: str = "") -> str:
    """Pick the best borrower candidate using source-aware scoring."""
    scored_candidates: list[tuple[int, str]] = []

    raw_candidates = [
        ("contact_org", raw.get("contact_org")),
        ("contact_org", raw.get("contact_organization")),
        ("contact_org", raw.get("agency_name")),
        ("contact_org", raw.get("organization_department")),
        ("contact_org", raw.get("organization/department")),
        ("contact_org", contact.get("organization_department")),
        ("contact_org", contact.get("organization/department")),
        ("contact_org", contact.get("organization")),
        ("contact_org", contact.get("org")),
        ("contact_org", contact.get("department")),
        ("raw_borrower", raw.get("borrower")),
        ("raw_procuring", raw.get("implementing_agency")),
        ("raw_procuring", raw.get("procuring_entity")),
        ("raw_procuring", raw.get("organization")),
        ("raw_contactish", raw.get("agencyname")),
        ("raw_contactish", raw.get("contact_agency")),
        ("raw_contactish", raw.get("org_name")),
        ("contact_org", contact.get("agencyname")),
    ]

    for source, value in raw_candidates:
        normalized = normalize_borrower_candidate(value, project_name=project_name)
        if not normalized:
            continue
        score = borrower_candidate_score(normalized, project_name=project_name, source=source)
        if score >= 0:
            scored_candidates.append((score, normalized))

    for source, candidate in extract_borrower_candidates_from_description(description) if description else []:
        normalized = normalize_borrower_candidate(candidate, project_name=project_name)
        if not normalized:
            continue
        score = borrower_candidate_score(normalized, project_name=project_name, source=source)
        if score >= 0:
            scored_candidates.append((score, normalized))

    if not scored_candidates:
        return ""

    scored_candidates.sort(key=lambda item: (-item[0], -len(item[1])))
    return scored_candidates[0][1]


# ── HTML helper ───────────────────────────────────────────────────────────────

def strip_html(html: str) -> str | None:
    """Strip HTML tags, preserve structure as plain text."""
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(['br', 'p', 'div', 'li', 'tr', 'h1', 'h2', 'h3', 'h4', 'h5']):
        tag.insert_after('\n')
    text = soup.get_text(separator='\n', strip=True)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return '\n'.join(lines) or None


def build_procurement_detail_url(notice_id: str, fallback_url: str = "") -> str:
    if fallback_url and "procurement-detail" in fallback_url:
        return fallback_url
    if notice_id:
        return f"https://projects.worldbank.org/en/projects-operations/procurement-detail/{notice_id}"
    return fallback_url or ""


def fetch_notice_record_by_id(notice_id: str) -> dict | None:
    if not notice_id:
        return None

    try:
        resp = requests.get(
            "https://search.worldbank.org/api/v2/procnotices",
            params={"format": "json", "apilang": "en", "fl": "*", "id": notice_id},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        log.warning(f"  Failed to fetch full notice record for {notice_id}: {exc}")
        return None

    raw = data.get("procnotices", {})
    items = list(raw.values()) if isinstance(raw, dict) else (raw or [])
    return items[0] if items else None


def extract_contact_org_from_lines(lines: list[str]) -> str | None:
    label_variants = {
        "organization/department",
        "organization / department",
        "organisation/département",
        "organisation / département",
    }
    stop_markers = {"details", "notice at-a-glance", "summary"}

    contact_start = 0
    for idx, line in enumerate(lines):
        if line.strip().lower() == "contact information":
            contact_start = idx + 1
            break

    section = lines[contact_start:]
    for idx, line in enumerate(section):
        lowered = line.strip().lower()
        if lowered in stop_markers:
            break
        if lowered in label_variants:
            for candidate in section[idx + 1:]:
                candidate = candidate.strip()
                if not candidate:
                    continue
                if candidate.lower() in stop_markers:
                    return None
                return clean_borrower_candidate(candidate)
    return None


def fetch_contact_org_from_detail_page(notice_id: str, fallback_url: str = "") -> str | None:
    api_record = fetch_notice_record_by_id(notice_id)
    if api_record:
        api_contact_org = clean_borrower_candidate(
            api_record.get("contact_organization") or
            api_record.get("agency_name") or
            api_record.get("agencyname")
        )
        if api_contact_org:
            log.info(f"  Full notice API contact org for {notice_id}: {api_contact_org}")
            return api_contact_org

    detail_url = build_procurement_detail_url(notice_id, fallback_url)
    if not detail_url:
        return None

    try:
        resp = requests.get(detail_url, timeout=20)
        resp.raise_for_status()
    except Exception as exc:
        log.warning(f"  Failed to fetch detail page for {notice_id}: {exc}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    lines = [line.strip() for line in soup.get_text(separator="\n", strip=True).splitlines() if line.strip()]
    contact_org = extract_contact_org_from_lines(lines)
    if contact_org:
        log.info(f"  Detail page contact org for {notice_id}: {contact_org}")
    return contact_org


# ── Date / amount parsers ─────────────────────────────────────────────────────

def parse_date(val) -> date | None:
    """
    FIX: use s[:19] instead of s[:20] to avoid capturing timezone
    characters (e.g. the '+' in '2026-05-07 10:00:00+00') that silently
    break every strptime format.
    """
    if not val:
        return None
    s = str(val).strip()[:19]
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d", "%d-%b-%Y", "%m/%d/%Y", "%d-%B-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except (ValueError, TypeError):
            continue
    # last-resort: just the date portion
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def parse_deadline(val) -> tuple:
    """
    Return (datetime_or_None, date_or_None).
    FIX: use s[:19] to strip timezone chars before parsing.
    """
    if not val:
        return None, None
    s = str(val).strip()[:19]
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d", "%m/%d/%Y", "%d-%b-%Y"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt, dt.date()
        except (ValueError, TypeError):
            continue
    return None, None


def parse_amount(val) -> float | None:
    try:
        return float(str(val).replace(",", "").strip()) if val else None
    except (ValueError, TypeError):
        return None


# ── API fetching ──────────────────────────────────────────────────────────────

def fetch_page(country_names: list[str], since: date, start: int = 0, rows: int = ROWS_PER_PAGE) -> dict:
    """Fetch one page from the WB procnotices endpoint."""
    query_countries = expand_country_names_for_query(country_names)
    params = {
        "format":                  "json",
        "fl":                      "*",
        "rows":                    rows,
        "os":                      start,
        "apilang":                 "en",
        "strdate":                 since.strftime("%Y-%m-%d"),
        "project_ctry_name_exact": "^".join(query_countries),
        "srt":                     "noticedate",
        "order":                   "desc",
    }
    resp = requests.get(API_BASE, params=params, timeout=20)
    log.info(f"  GET {resp.url[:120]}...")
    resp.raise_for_status()
    return resp.json()


def fetch_page_with_fallback(country_names: list[str], since: date, start: int = 0) -> tuple[dict, int, int]:
    """Fetch a page, retrying smaller pages for single-country API 500s."""
    try:
        return fetch_page(country_names, since, start, ROWS_PER_PAGE), ROWS_PER_PAGE, 0
    except requests.HTTPError as exc:
        response = getattr(exc, "response", None)
        if len(country_names) != 1 or response is None or response.status_code < 500:
            raise
        log.warning(
            f"  Page failed for {country_names[0]} at rows={ROWS_PER_PAGE}; "
            f"retrying with rows={FALLBACK_ROWS_PER_PAGE}: {exc}"
        )
        return fetch_page(country_names, since, start, FALLBACK_ROWS_PER_PAGE), FALLBACK_ROWS_PER_PAGE, 1


# ── Data transformation ───────────────────────────────────────────────────────

def transform(raw: dict, is_existing: bool = False) -> dict | None:
    """
    Map a raw API record to our DB schema.
    Returns None if the record has no usable ID.
    """
    notice_id = str(
        raw.get("id") or raw.get("nid") or
        raw.get("notice_no") or raw.get("procurement_number") or
        raw.get("ref_no") or ""
    ).strip()
    if not notice_id:
        return None

    # Normalise notice type
    raw_type = raw.get("notice_type") or ""
    if "Invitation for Bids" in raw_type or raw_type == "IFB":
        notice_type = "IFB"
    elif "Expression of Interest" in raw_type or raw_type == "REOI":
        notice_type = "REOI"
    else:
        notice_type = raw_type

    # ── DEADLINE FIX ──────────────────────────────────────────────────────────
    # The procnotices API returns the deadline under "ndate" as the primary key.
    # "SubmissionDeadlineDate" is the capitalised variant seen in some responses.
    # The old keys (submission_date, bids_deadline, deadline_date) do not exist
    # in the procnotices endpoint and caused deadline_raw to always be empty.
    deadline_raw = (
        raw.get("ndate") or                       # PRIMARY — procnotices API
        raw.get("SubmissionDeadlineDate") or       # capitalised variant
        raw.get("submission_deadline_date") or     # fallback
        raw.get("bids_deadline") or ""
    )
    deadline_dt, deadline_date = parse_deadline(deadline_raw)

    # Notice date
    notice_date = (
        parse_date(raw.get("noticedate")) or
        parse_date(raw.get("notice_date")) or
        parse_date(raw.get("pdate")) or
        parse_date(raw.get("published_date"))
    )

    # Title
    title = (
        raw.get("notice_title") or raw.get("title") or
        raw.get("bid_description") or raw.get("project_name") or ""
    )

    # Description — strip HTML tags
    raw_desc = raw.get("notice_text") or raw.get("description") or raw.get("bid_description") or ""
    description = strip_html(raw_desc) if raw_desc else ""

    contact = dict(raw.get("contact") or {})
    contact_org = (
        raw.get("contact_org") or raw.get("contact_organization") or
        raw.get("agency_name") or raw.get("organization_department") or
        raw.get("organization/department") or raw.get("agencyname") or
        raw.get("organization") or contact.get("organization_department") or
        contact.get("organization/department") or contact.get("organization") or
        contact.get("org") or contact.get("department") or ""
    )

    if not contact_org and not is_existing:
        detail_contact_org = fetch_contact_org_from_detail_page(notice_id, raw.get("url") or "")
        if detail_contact_org:
            contact_org = detail_contact_org
            contact["organization"] = contact.get("organization") or detail_contact_org

    borrower = choose_borrower(
        {**raw, "contact_org": contact_org},
        description or "",
        contact,
        project_name=raw.get("project_name") or "",
    )

    return {
        "id":                     notice_id,
        "project_id":             raw.get("project_id") or "",
        "project_name":           raw.get("project_name") or "",
        "country":                normalize_country_name(raw.get("project_ctry_name") or raw.get("country") or ""),
        "notice_no":              raw.get("notice_no") or raw.get("ref_no") or notice_id,
        "notice_type":            notice_type,
        "notice_status":          raw.get("notice_status") or raw.get("procurement_status") or "Published",
        "procurement_method":     raw.get("procurement_method") or raw.get("procurement_method_name") or "",
        "language":               raw.get("language") or raw.get("notice_language") or raw.get("notice_lang_name") or "English",
        "title":                  title,
        "description":            (description or "")[:5000],
        "borrower_bid_reference": (raw.get("borrower_bid_reference") or
                                   raw.get("bid_reference") or raw.get("ref_no") or ""),
        "notice_date":            notice_date,
        "submission_deadline":    deadline_dt,
        "submission_date":        deadline_date,
        "contract_amount":        parse_amount(raw.get("contract_amount") or raw.get("total_contract_amount")),
        "currency":               raw.get("currency") or "",
        "borrower":               borrower,
        "contact_name":           raw.get("contact_name") or contact.get("name") or "",
        "contact_org":            contact_org,
        "contact_address":        raw.get("contact_address") or contact.get("address") or "",
        "contact_city":           raw.get("contact_city") or contact.get("city") or "",
        "contact_phone":          (raw.get("contact_phone") or raw.get("phone") or
                                   raw.get("contactphone") or raw.get("telephone") or
                                   raw.get("contact_phone_no") or
                                   contact.get("phone") or ""),
        "contact_email":          (raw.get("contact_email") or raw.get("email") or
                                   raw.get("contactemail") or contact.get("email") or ""),
        "contact_website":        raw.get("contact_website") or raw.get("website") or contact.get("website") or "",
        "url":                    raw.get("url") or "https://projects.worldbank.org/en/projects-operations/procurement",
        "status":                 raw.get("notice_status") or raw.get("procurement_status") or "Published",
    }


# ── Upsert ────────────────────────────────────────────────────────────────────

UPSERT_SQL = """
INSERT INTO procurement_notices
    (id, project_id, project_name, country, notice_no, notice_type, notice_status,
     procurement_method, language, title, description, borrower_bid_reference,
     notice_date, submission_deadline, submission_date, contract_amount, currency,
     borrower, contact_name, contact_org, contact_address, contact_city,
     contact_phone, contact_email, contact_website, url, status, updated_at)
VALUES %s
ON CONFLICT (id) DO UPDATE SET
    notice_status        = EXCLUDED.notice_status,
    title                = EXCLUDED.title,
    description          = EXCLUDED.description,
    borrower             = EXCLUDED.borrower,
    contact_org          = EXCLUDED.contact_org,
    submission_deadline  = EXCLUDED.submission_deadline,
    submission_date      = EXCLUDED.submission_date,
    status               = EXCLUDED.status,
    updated_at           = NOW()
WHERE
    procurement_notices.title IS DISTINCT FROM EXCLUDED.title
    OR procurement_notices.borrower IS DISTINCT FROM EXCLUDED.borrower
    OR procurement_notices.contact_org IS DISTINCT FROM EXCLUDED.contact_org
    OR procurement_notices.submission_date IS DISTINCT FROM EXCLUDED.submission_date
    OR procurement_notices.notice_status IS DISTINCT FROM EXCLUDED.notice_status;
"""

UPSERT_TEMPLATE = (
    "(%(id)s, %(project_id)s, %(project_name)s, %(country)s, %(notice_no)s, "
    "%(notice_type)s, %(notice_status)s, %(procurement_method)s, %(language)s, "
    "%(title)s, %(description)s, %(borrower_bid_reference)s, %(notice_date)s, "
    "%(submission_deadline)s, %(submission_date)s, %(contract_amount)s, %(currency)s, "
    "%(borrower)s, %(contact_name)s, %(contact_org)s, %(contact_address)s, "
    "%(contact_city)s, %(contact_phone)s, %(contact_email)s, %(contact_website)s, "
    "%(url)s, %(status)s, NOW())"
)


def upsert_notices(conn, notices: list[dict]) -> tuple[int, int]:
    """Upsert notices. Returns (total_upserted, genuinely_new)."""
    if not notices:
        return 0, 0

    ids = [n["id"] for n in notices]
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM procurement_notices WHERE id = ANY(%s)", (ids,))
        existing = {row[0] for row in cur.fetchall()}

    new_count = sum(1 for n in notices if n["id"] not in existing)
    execute_values(conn.cursor(), UPSERT_SQL, notices, template=UPSERT_TEMPLATE)
    conn.commit()
    return len(notices), new_count


def get_country_notice_summary(conn, country: str) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) AS row_count,
                   MIN(notice_date) AS first_notice_date,
                   MAX(notice_date) AS last_notice_date
            FROM procurement_notices
            WHERE country = %s
            """,
            (country,),
        )
        row = cur.fetchone()
    return {
        "row_count": int(row[0] or 0),
        "first_notice_date": row[1],
        "last_notice_date": row[2],
    }


def mark_country_fetch_started(conn, country: str, since: date):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO country_fetch_status
                (country, status, last_started_at, last_attempted_since, updated_at)
            VALUES (%s, 'running', NOW(), %s, NOW())
            ON CONFLICT (country) DO UPDATE SET
                status = 'running',
                last_started_at = NOW(),
                last_attempted_since = EXCLUDED.last_attempted_since,
                error_msg = NULL,
                api_url = NULL,
                updated_at = NOW()
            """,
            (country, since),
        )
    conn.commit()


def mark_country_fetch_finished(
    conn,
    country: str,
    *,
    since: date,
    fetched: int = 0,
    new_records: int = 0,
    total_available: int = 0,
    page_size: int = ROWS_PER_PAGE,
    retry_count: int = 0,
    error_msg: str | None = None,
    api_url: str | None = None,
):
    summary = get_country_notice_summary(conn, country)
    success = error_msg is None
    status = status_label(success, summary["row_count"], fetched, error_msg)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO country_fetch_status
                (country, status, last_finished_at, last_success_at,
                 last_attempted_since, last_page_size, fetched_records,
                 new_records, total_available, row_count, first_notice_date,
                 last_notice_date, error_msg, api_url, retry_count, updated_at)
            VALUES
                (%s, %s, NOW(), CASE WHEN %s THEN NOW() ELSE NULL END,
                 %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (country) DO UPDATE SET
                status = EXCLUDED.status,
                last_finished_at = NOW(),
                last_success_at = CASE WHEN %s THEN NOW() ELSE country_fetch_status.last_success_at END,
                last_attempted_since = EXCLUDED.last_attempted_since,
                last_page_size = EXCLUDED.last_page_size,
                fetched_records = EXCLUDED.fetched_records,
                new_records = EXCLUDED.new_records,
                total_available = EXCLUDED.total_available,
                row_count = EXCLUDED.row_count,
                first_notice_date = EXCLUDED.first_notice_date,
                last_notice_date = EXCLUDED.last_notice_date,
                error_msg = EXCLUDED.error_msg,
                api_url = EXCLUDED.api_url,
                retry_count = EXCLUDED.retry_count,
                updated_at = NOW()
            """,
            (
                country, status, success, since, page_size, fetched, new_records,
                total_available, summary["row_count"], summary["first_notice_date"],
                summary["last_notice_date"], error_msg, api_url, retry_count, success,
            ),
        )
    conn.commit()


def backfill_host_institutions(conn) -> int:
    """Repair borrower/contact_org for existing rows that were imported before the improved logic."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT id, url, project_name, description, borrower, contact_org
            FROM procurement_notices
            WHERE COALESCE(contact_org, '') = ''
               OR COALESCE(borrower, '') = ''
               OR LENGTH(COALESCE(borrower, '')) > 140
               OR borrower ~ '^[0-9]+[\\.) ]'
               OR borrower ILIKE '%bid document can be obtained%'
               OR borrower ILIKE '%interested bidders%'
               OR borrower ILIKE '%bids shall%'
        """)
        rows = cur.fetchall()

    updated = 0
    processed = 0
    for row in rows:
        processed += 1
        current_contact_org = row.get("contact_org") or ""
        detail_contact_org = current_contact_org or fetch_contact_org_from_detail_page(row["id"], row.get("url") or "")

        contact = {}
        if detail_contact_org:
            contact["organization"] = detail_contact_org

        new_borrower = choose_borrower(
            {"contact_org": detail_contact_org},
            row.get("description") or "",
            contact,
            project_name=row.get("project_name") or "",
        )

        if (detail_contact_org or "") == current_contact_org and (new_borrower or "") == (row.get("borrower") or ""):
            continue

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE procurement_notices
                SET borrower = %s,
                    contact_org = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (new_borrower or row.get("borrower") or "", detail_contact_org or current_contact_org, row["id"]),
            )
        updated += 1
        if updated % 25 == 0:
            conn.commit()
            log.info(f"  Backfill progress: {processed}/{len(rows)} checked, {updated} updated.")

    if updated:
        conn.commit()
    return updated


def log_run(conn, countries: str, fetched: int, new_records: int,
            success: bool, error_msg: str | None = None):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO fetch_runs
               (run_at, country, notice_type, fetched, new_records, success, error_msg)
               VALUES (NOW(), %s, NULL, %s, %s, %s, %s)""",
            (countries, fetched, new_records, success, error_msg),
        )
    conn.commit()


# ── Fetch one batch of countries ──────────────────────────────────────────────

def fetch_batch(conn, batch: list[str], since: date) -> tuple[int, int]:
    """Paginate through all pages for a batch of countries."""
    total_upserted = 0
    total_new      = 0
    start          = 0
    page_size      = ROWS_PER_PAGE
    retry_count    = 0
    total_available = 0
    per_country_fetched = {country: 0 for country in batch}
    per_country_new = {country: 0 for country in batch}

    log.info(f"  Countries: {', '.join(batch)}")
    for country in batch:
        mark_country_fetch_started(conn, country, since)

    while True:
        log.info(f"  Page offset={start} ...")
        data, page_size, page_retries = fetch_page_with_fallback(batch, since, start)
        retry_count += page_retries
        total_available = int(data.get("total", 0))

        raw = data.get("procnotices", [])
        raw_items = list(raw.values()) if isinstance(raw, dict) else (raw or [])

        if not raw_items:
            log.info("  No more results.")
            break

        s = raw_items[0]
        log.info(
            f"  Sample — noticedate: {s.get('noticedate')} | "
            f"country: {s.get('project_ctry_name')} | "
            f"type: {s.get('notice_type')} | "
            f"borrower={s.get('borrower')} agencyname={s.get('agencyname')} "
            f"contact_agency={s.get('contact_agency')} | "
            f"org_name={s.get('org_name')} implementing_agency={s.get('implementing_agency')} | "
            f"ALL_KEYS: {list(s.keys())[:20]}"  # Show first 20 keys
        )
        # ── Deadline debug log — confirms which field the API is using ────────
        log.info(
            f"  Deadline fields — ndate={s.get('ndate')} | "
            f"SubmissionDeadlineDate={s.get('SubmissionDeadlineDate')} | "
            f"submission_deadline_date={s.get('submission_deadline_date')}"
        )

        # Collect all potential IDs in this page's items to check existing ones in a single query
        item_ids = []
        for item in raw_items:
            nid = str(
                item.get("id") or item.get("nid") or
                item.get("notice_no") or item.get("procurement_number") or
                item.get("ref_no") or ""
            ).strip()
            if nid:
                item_ids.append(nid)

        existing_ids = set()
        if item_ids:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM procurement_notices WHERE id = ANY(%s)", (item_ids,))
                existing_ids = {row[0] for row in cur.fetchall()}

        notices = []
        all_too_old = True
        for item in raw_items:
            notice_date = (
                parse_date(item.get("noticedate")) or
                parse_date(item.get("pdate")) or
                parse_date(item.get("published_date"))
            )
            if notice_date and notice_date >= since and notice_date >= ABSOLUTE_START:
                all_too_old = False
                nid = str(
                    item.get("id") or item.get("nid") or
                    item.get("notice_no") or item.get("procurement_number") or
                    item.get("ref_no") or ""
                ).strip()
                is_existing = nid in existing_ids
                transformed = transform(item, is_existing=is_existing)
                if transformed:
                    notices.append(transformed)

        if all_too_old:
            log.info(f"  All notices on this page are before {since}. Stopping.")
            break

        if notices:
            ids_by_country = {}
            for notice in notices:
                ids_by_country.setdefault(notice["country"], []).append(notice["id"])
            existing_by_country = {country: set() for country in ids_by_country}
            with conn.cursor() as cur:
                for notice_country, ids in ids_by_country.items():
                    cur.execute("SELECT id FROM procurement_notices WHERE id = ANY(%s)", (ids,))
                    existing_by_country[notice_country] = {row[0] for row in cur.fetchall()}

            upserted, new_count = upsert_notices(conn, notices)
            total_upserted += upserted
            total_new      += new_count
            for notice_country, ids in ids_by_country.items():
                if notice_country in per_country_fetched:
                    per_country_fetched[notice_country] += len(ids)
                    per_country_new[notice_country] += sum(
                        1 for notice_id in ids if notice_id not in existing_by_country[notice_country]
                    )
            log.info(
                f"  {upserted} upserted | {new_count} genuinely new "
                f"(batch total: {total_upserted} / {total_available})"
            )
        else:
            log.info("  0 notices passed date filter on this page.")

        start += page_size
        if start >= total_available:
            break

        time.sleep(REQUEST_DELAY)

    for country in batch:
        mark_country_fetch_finished(
            conn,
            country,
            since=since,
            fetched=per_country_fetched.get(country, 0),
            new_records=per_country_new.get(country, 0),
            total_available=total_available,
            page_size=page_size,
            retry_count=retry_count,
        )

    return total_upserted, total_new


def fetch_batch_resilient(conn, batch: list[str], since: date) -> tuple[int, int]:
    """Fetch a batch, splitting it into smaller groups if the API times out."""
    try:
        return fetch_batch(conn, batch, since)
    except Exception as exc:
        if len(batch) == 1:
            response = getattr(exc, "response", None)
            mark_country_fetch_finished(
                conn,
                batch[0],
                since=since,
                error_msg=str(exc),
                api_url=getattr(response, "url", None),
                retry_count=1,
            )
            log.error(f"  Country fetch failed for {batch[0]}: {exc}")
            return 0, 0

        mid = max(1, len(batch) // 2)
        left = batch[:mid]
        right = batch[mid:]
        log.warning(
            f"  Batch fetch failed for {', '.join(batch)}: {exc}. "
            f"Retrying as smaller batches: {', '.join(left)} | {', '.join(right)}"
        )

        left_upserted, left_new = fetch_batch_resilient(conn, left, since)
        right_upserted, right_new = fetch_batch_resilient(conn, right, since)
        return left_upserted + right_upserted, left_new + right_new


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    global COUNTRY_BATCH, REQUEST_DELAY
    log.info("═" * 60)
    log.info(f"World Bank Procurement Fetcher — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log.info("═" * 60)

    init_db()
    settings = get_app_settings()
    COUNTRY_BATCH = int(float(settings.get("country_batch", COUNTRY_BATCH)))
    REQUEST_DELAY = float(settings.get("request_delay", REQUEST_DELAY))

    since            = get_fetch_start_date()
    target_countries = get_target_countries()
    batches          = list(chunk(target_countries, COUNTRY_BATCH))

    log.info(f"Fetching {len(target_countries)} countries in {len(batches)} batch(es)")
    log.info(f"Date window: {since} → today\n")

    conn           = get_connection()
    total_upserted = 0
    total_new      = 0
    error_msg      = None
    success        = False

    try:
        repaired = backfill_host_institutions(conn)
        if repaired:
            log.info(f"Repaired host institution fields for {repaired} existing notice(s).")

        for i, batch in enumerate(batches, 1):
            log.info(f"\n── Batch {i}/{len(batches)} ──")
            upserted, new = fetch_batch_resilient(conn, batch, since)
            total_upserted += upserted
            total_new      += new
            time.sleep(REQUEST_DELAY)

        success = True
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT country
                FROM country_fetch_status
                WHERE country = ANY(%s)
                  AND status = 'failed'
                ORDER BY country
                """,
                (target_countries,),
            )
            failed_countries = [row[0] for row in cur.fetchall()]
        if failed_countries:
            success = False
            error_msg = "Partial success: failed countries: " + ", ".join(failed_countries)

        # Update last_run_baseline_date to match the baseline_date we just synced
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES ('last_run_baseline_date', %s, NOW())
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                """,
                (settings.get("baseline_date", "2025-01-01"),),
            )
        conn.commit()

    except Exception as exc:
        error_msg = str(exc)
        log.error(f"Fatal error: {error_msg}")
        traceback.print_exc()

    finally:
        log_run(conn, ",".join(target_countries), total_upserted, total_new, success, error_msg)
        conn.close()

    log.info("═" * 60)
    if success:
        log.info(f"Done. {total_upserted} upserted, {total_new} genuinely new.")
        log.info(f"Next run will fetch from {date.today() - timedelta(days=1)} onwards.")
    else:
        log.error("Run failed. Previous data is safe.")
    log.info("═" * 60)


if __name__ == "__main__":
    run()  # Run once immediately on startup
    schedule.every().day.at("06:00").do(run)
    log.info("Scheduler started — running daily at 06:00")
    while True:
        schedule.run_pending()
        time.sleep(60)
