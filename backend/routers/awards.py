import csv
import io
import re
from datetime import datetime
from typing import Any

from auth import require_auth
from db import db, ensure_support_tables, q
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/award-alerts", tags=["awards"])


def ensure_award_alert_tables():
    ensure_support_tables()
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS award_alerts (
                    id SERIAL PRIMARY KEY,
                    source_notice_id TEXT NOT NULL REFERENCES procurement_notices(id) ON DELETE CASCADE,
                    award_notice_id TEXT NOT NULL REFERENCES procurement_notices(id) ON DELETE CASCADE,
                    match_status TEXT NOT NULL DEFAULT 'auto_matched',
                    match_score INT NOT NULL DEFAULT 0,
                    matched_reason TEXT,
                    seen_at TIMESTAMPTZ,
                    dismissed_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(source_notice_id, award_notice_id)
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_award_alerts_seen ON award_alerts (seen_at)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_award_alerts_status ON award_alerts (match_status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_award_alerts_award ON award_alerts (award_notice_id)")
            # These indexes support the two legitimate candidate paths: an exact
            # procurement reference, or a same-project comparison for review.
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_notices_award_match_reference
                ON procurement_notices
                ((regexp_replace(upper(COALESCE(borrower_bid_reference, '')), '[^A-Z0-9]+', '', 'g')))
                WHERE notice_type IN ('IFB', 'REOI')
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_notices_award_match_project
                ON procurement_notices (country, project_id, notice_date)
                WHERE notice_type IN ('IFB', 'REOI')
            """)
        conn.commit()


def _norm_match_value(value):
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _token_set(value):
    stop = {
        "the", "and", "for", "of", "to", "in", "on", "with", "a", "an", "no", "number",
        "contract", "award", "awarded", "procurement", "supply", "invitation", "bids", "bid",
        "request", "expressions", "expression", "interest", "services", "goods", "works",
    }
    return {
        token for token in re.findall(r"[a-z0-9]+", _norm_match_value(value)) if len(token) > 2 and token not in stop
    }


def _norm_reference(value):
    """Normalize a tender/lot reference without treating a notice ID as one."""
    return re.sub(r"[^A-Z0-9]+", "", str(value or "").upper())


def _has_exact_reference_match(source, award):
    source_ref = _norm_reference(source.get("borrower_bid_reference"))
    award_ref = _norm_reference(award.get("borrower_bid_reference"))
    return bool(source_ref and award_ref and source_ref == award_ref)


def _title_similarity(source, award):
    """Return a conservative 0-60 title score and the count of shared terms."""
    left = _token_set(source.get("title"))
    right = _token_set(award.get("title"))
    shared = len(left & right)
    if not left or not right or shared < 2:
        return 0, shared
    # Dice similarity avoids the old "all tokens from a short title match"
    # behaviour caused by dividing by the smaller title's token count.
    similarity = (2 * shared) / (len(left) + len(right))
    return min(60, int(similarity * 60)), shared


def score_award_match(source, award):
    if _has_exact_reference_match(source, award):
        return 100, "exact procurement reference"

    # A World Bank project contains many procurements.  It is useful to find
    # candidates, but never evidence that two procurement notices are the same.
    same_project = _norm_match_value(source.get("project_id")) == _norm_match_value(award.get("project_id"))
    if not same_project or not _norm_match_value(source.get("project_id")):
        return 0, "no exact procurement reference"

    title_score, shared_terms = _title_similarity(source, award)
    if title_score < 36:
        return 0, "same project only; title similarity is insufficient"

    score = 10 + title_score
    reasons = ["same project ID", f"strong title similarity {title_score}/60 ({shared_terms} shared terms)"]
    if _norm_match_value(source.get("borrower")) == _norm_match_value(award.get("borrower")) and source.get("borrower"):
        score += 15
        reasons.append("same borrower")
    return score, ", ".join(reasons)


def _deduplicate_equivalent_alerts(cur) -> int:
    """Keep one alert when the WB API has published duplicate notice records.

    The table's unique key correctly prevents the same two notice IDs from
    repeating.  This handles a different problem: several IDs can represent
    the same tender or contract and would otherwise create a grid of alerts.
    A procurement reference is preferred; an exact normalized title is used
    only while historical records have no reference.
    """
    cur.execute(
        """
        WITH ranked AS (
            SELECT
                aa.id,
                ROW_NUMBER() OVER (
                    PARTITION BY
                        src.country,
                        src.project_id,
                        COALESCE(
                            NULLIF(regexp_replace(upper(COALESCE(src.borrower_bid_reference, '')), '[^A-Z0-9]+', '', 'g'), ''),
                            NULLIF(lower(regexp_replace(trim(COALESCE(src.title, '')), '\\s+', ' ', 'g')), ''),
                            src.id
                        ),
                        award.country,
                        award.project_id,
                        COALESCE(
                            NULLIF(regexp_replace(upper(COALESCE(award.borrower_bid_reference, '')), '[^A-Z0-9]+', '', 'g'), ''),
                            NULLIF(lower(regexp_replace(trim(COALESCE(award.title, '')), '\\s+', ' ', 'g')), ''),
                            award.id
                        )
                    ORDER BY aa.match_score DESC, aa.created_at DESC, aa.id DESC
                ) AS rank
            FROM award_alerts aa
            JOIN procurement_notices src ON src.id = aa.source_notice_id
            JOIN procurement_notices award ON award.id = aa.award_notice_id
        )
        DELETE FROM award_alerts aa
        USING ranked
        WHERE aa.id = ranked.id AND ranked.rank > 1
        """
    )
    return cur.rowcount


def _keep_best_alert_per_award(cur) -> int:
    """An award represents one procurement outcome, so keep its best source."""
    cur.execute(
        """
        WITH ranked AS (
            SELECT
                aa.id,
                ROW_NUMBER() OVER (
                    PARTITION BY aa.award_notice_id
                    ORDER BY aa.match_score DESC, src.notice_date DESC NULLS LAST, aa.id DESC
                ) AS rank
            FROM award_alerts aa
            JOIN procurement_notices src ON src.id = aa.source_notice_id
        )
        DELETE FROM award_alerts aa
        USING ranked
        WHERE aa.id = ranked.id AND ranked.rank > 1
        """
    )
    return cur.rowcount


def sync_award_alerts():
    ensure_award_alert_tables()
    award_rows = q("""
        SELECT id, project_id, project_name, country, notice_no, notice_type, status,
               borrower_bid_reference, borrower, title, notice_date::text, fetched_at::text
        FROM procurement_notices
        WHERE notice_type IN ('Contract Award', 'Award') OR notice_type ILIKE '%Contract Award%'
        ORDER BY fetched_at DESC NULLS LAST, notice_date DESC NULLS LAST
    """)

    created = 0
    reviewed = 0
    duplicates_removed = 0
    competing_matches_removed = 0
    processed = 0
    with db() as conn:
        with conn.cursor() as cur:
            for award in award_rows:
                candidates = q(
                    """
                    SELECT id, project_id, project_name, country, notice_no, notice_type, status,
                           borrower_bid_reference, borrower, title, notice_date::text
                    FROM procurement_notices
                    WHERE id <> %s
                      AND notice_type IN ('IFB', 'REOI')
                      AND (NULLIF(%s, '') IS NULL OR country = %s)
                      AND (notice_date IS NULL OR %s::date IS NULL OR notice_date <= %s::date)
                      AND (
                          (%s <> '' AND regexp_replace(upper(COALESCE(borrower_bid_reference, '')), '[^A-Z0-9]+', '', 'g') = %s)
                          OR (%s <> '' AND project_id = %s)
                      )
                    ORDER BY
                        CASE WHEN %s <> '' AND regexp_replace(upper(COALESCE(borrower_bid_reference, '')), '[^A-Z0-9]+', '', 'g') = %s THEN 0 ELSE 1 END,
                        notice_date DESC NULLS LAST
                """,
                    [
                        award["id"],
                        award.get("country"),
                        award.get("country"),
                        award.get("notice_date"),
                        award.get("notice_date"),
                        _norm_reference(award.get("borrower_bid_reference")),
                        _norm_reference(award.get("borrower_bid_reference")),
                        _norm_match_value(award.get("project_id")),
                        award.get("project_id"),
                        _norm_reference(award.get("borrower_bid_reference")),
                        _norm_reference(award.get("borrower_bid_reference")),
                    ],
                )

                best_match = None
                for source in candidates:
                    score, reason = score_award_match(source, award)
                    if score < 40:
                        continue
                    candidate_key = (
                        int(_has_exact_reference_match(source, award)),
                        score,
                        source.get("notice_date") or "",
                        source["id"],
                    )
                    if best_match is None or candidate_key > best_match[0]:
                        best_match = (candidate_key, source, score, reason)

                if best_match:
                    _, source, score, reason = best_match
                    # Text-based matches are deliberately review-only.  Only a
                    # shared procurement reference can become an automatic alert.
                    status = "auto_matched" if _has_exact_reference_match(source, award) else "needs_review"
                    cur.execute(
                        """
                        INSERT INTO award_alerts
                            (source_notice_id, award_notice_id, match_status, match_score, matched_reason, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                        ON CONFLICT (source_notice_id, award_notice_id) DO UPDATE SET
                            match_status = EXCLUDED.match_status,
                            match_score = EXCLUDED.match_score,
                            matched_reason = EXCLUDED.matched_reason,
                            updated_at = NOW()
                        WHERE award_alerts.match_status <> 'rejected'
                        RETURNING id, (xmax = 0) AS inserted
                    """,
                        [source["id"], award["id"], status, score, reason],
                    )
                    row = cur.fetchone()
                    if row:
                        if row.get("inserted"):
                            created += 1
                        else:
                            reviewed += 1
                processed += 1
                if processed % 200 == 0:
                    conn.commit()
            duplicates_removed = _deduplicate_equivalent_alerts(cur)
            competing_matches_removed = _keep_best_alert_per_award(cur)
        conn.commit()

    return {
        "status": "ok",
        "created": created,
        "updated": reviewed,
        "duplicates_removed": duplicates_removed,
        "competing_matches_removed": competing_matches_removed,
        "awards_checked": len(award_rows),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/sync")
def sync_award_alerts_endpoint(_: dict = Depends(require_auth)):
    return sync_award_alerts()


@router.get("/")
def list_award_alerts(
    unread_only: bool = Query(False),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    ensure_award_alert_tables()
    filters = ["aa.dismissed_at IS NULL"]
    params: list[Any] = []
    if unread_only:
        filters.append("aa.seen_at IS NULL")
    if status:
        filters.append("aa.match_status = %s")
        params.append(status)
    where = " AND ".join(filters)
    offset = (page - 1) * page_size

    total_rows = q(f"SELECT COUNT(*) AS cnt FROM award_alerts aa WHERE {where}", params)
    unread_rows = q("SELECT COUNT(*) AS cnt FROM award_alerts aa WHERE aa.dismissed_at IS NULL AND aa.seen_at IS NULL")
    rows = q(
        f"""
        SELECT
            aa.id,
            aa.match_status,
            aa.match_score,
            aa.matched_reason,
            aa.seen_at::text,
            aa.created_at::text,
            src.id AS source_notice_id,
            src.notice_type AS source_notice_type,
            src.title AS source_title,
            src.project_id AS source_project_id,
            src.project_name AS source_project_name,
            src.country AS source_country,
            src.borrower AS source_borrower,
            src.notice_date::text AS source_notice_date,
            src.url AS source_url,
            award.id AS award_notice_id,
            award.notice_type AS award_notice_type,
            award.title AS award_title,
            award.project_id AS award_project_id,
            award.project_name AS award_project_name,
            award.country AS award_country,
            award.borrower AS award_borrower,
            award.notice_date::text AS award_notice_date,
            COALESCE((
                SELECT MAX(ba.award_amount) FROM bidder_awards ba
                WHERE ba.notice_id = award.id AND ba.won IS TRUE
            ), award.contract_amount) AS award_amount,
            COALESCE((
                SELECT ba.currency FROM bidder_awards ba
                WHERE ba.notice_id = award.id AND ba.won IS TRUE
                ORDER BY ba.award_amount DESC NULLS LAST LIMIT 1
            ), award.currency) AS award_currency,
            award.url AS award_url,
            award.description AS award_description,
            COALESCE((
                SELECT STRING_AGG(b.name, ', ' ORDER BY b.name ASC)
                FROM bidder_awards ba
                JOIN bidders b ON b.id = ba.bidder_id
                WHERE ba.notice_id = award.id AND ba.won IS TRUE
            ), '') AS awarded_bidders
        FROM award_alerts aa
        JOIN procurement_notices src ON src.id = aa.source_notice_id
        JOIN procurement_notices award ON award.id = aa.award_notice_id
        WHERE {where}
        ORDER BY aa.seen_at IS NOT NULL, award.notice_date DESC NULLS LAST, aa.created_at DESC, aa.match_score DESC
        LIMIT %s OFFSET %s
    """,
        params + [page_size, offset],
    )

    _AMOUNT_RE = re.compile(
        r"(?:Signed\s+Contract\s+[Pp]rice|Evaluated\s+Bid\s+Price|"
        r"Contract\s+Amount|Award\s+Amount|Total\s+Contract\s+Price)"
        r"\s*[:\n]?\s*(?:([A-Z]{3})\s+)?([\d,]+(?:\.\d+)?)",
        re.IGNORECASE,
    )
    # Pair an ISO-4217-ish currency code with the amount that follows it, so a
    # non-USD award (XOF, ETB, ...) is not silently reported as USD.
    _CURRENCY_AMOUNT_RE = re.compile(r"([A-Z]{3})\s*([\d,]+(?:\.\d+)?)", re.IGNORECASE)

    def _apply_parsed_amount(row, amount, currency=None):
        try:
            row["award_amount"] = float(amount.replace(",", ""))
        except (ValueError, TypeError):
            return
        if currency and not row.get("award_currency"):
            row["award_currency"] = currency.upper()

    for row in rows:
        if row.get("award_amount") is not None:
            continue
        desc = row.get("award_description") or ""
        if not desc:
            continue
        m = _AMOUNT_RE.search(desc)
        if m:
            _apply_parsed_amount(row, m.group(2), m.group(1))
        if row.get("award_amount") is None:
            for cm in _CURRENCY_AMOUNT_RE.finditer(desc):
                _apply_parsed_amount(row, cm.group(2), cm.group(1))
                break

        # Bidder imports run asynchronously after a fetch.  Do not hide a
        # winner merely because that import has not yet reached this notice.
        if not row.get("awarded_bidders") and row.get("award_description"):
            from services.bidder_extraction import extract_awarded_bidders

            row["awarded_bidders"] = ", ".join(extract_awarded_bidders(row["award_description"]))

    for row in rows:
        row.pop("award_description", None)

    return {
        "total": total_rows[0]["cnt"] if total_rows else 0,
        "unread": unread_rows[0]["cnt"] if unread_rows else 0,
        "page": page,
        "page_size": page_size,
        "data": [dict(row) for row in rows],
    }


@router.get("/export")
def export_award_alerts(
    unread_only: bool = Query(False),
    status: str | None = Query(None),
):
    ensure_award_alert_tables()
    filters = ["aa.dismissed_at IS NULL"]
    params: list[Any] = []
    if unread_only:
        filters.append("aa.seen_at IS NULL")
    if status:
        filters.append("aa.match_status = %s")
        params.append(status)
    where = " AND ".join(filters)

    sql = f"""
        SELECT
            aa.id,
            aa.match_status,
            aa.match_score,
            aa.matched_reason,
            aa.seen_at::text,
            aa.created_at::text,
            src.notice_type AS source_notice_type,
            src.title AS source_title,
            src.project_id AS source_project_id,
            src.project_name AS source_project_name,
            src.country AS source_country,
            src.borrower AS source_borrower,
            src.notice_date::text AS source_notice_date,
            src.url AS source_url,
            award.notice_type AS award_notice_type,
            award.title AS award_title,
            award.project_id AS award_project_id,
            award.project_name AS award_project_name,
            award.country AS award_country,
            award.borrower AS award_borrower,
            award.notice_date::text AS award_notice_date,
            COALESCE((
                SELECT MAX(ba.award_amount) FROM bidder_awards ba
                WHERE ba.notice_id = award.id AND ba.won IS TRUE
            ), award.contract_amount) AS award_amount,
            COALESCE((
                SELECT ba.currency FROM bidder_awards ba
                WHERE ba.notice_id = award.id AND ba.won IS TRUE
                ORDER BY ba.award_amount DESC NULLS LAST LIMIT 1
            ), award.currency) AS award_currency,
            award.url AS award_url,
            award.description AS award_description,
            COALESCE((
                SELECT STRING_AGG(b.name, ', ' ORDER BY b.name ASC)
                FROM bidder_awards ba
                JOIN bidders b ON b.id = ba.bidder_id
                WHERE ba.notice_id = award.id AND ba.won IS TRUE
            ), '') AS awarded_bidders
        FROM award_alerts aa
        JOIN procurement_notices src ON src.id = aa.source_notice_id
        JOIN procurement_notices award ON award.id = aa.award_notice_id
        WHERE {where}
        ORDER BY aa.seen_at IS NOT NULL, award.notice_date DESC NULLS LAST, aa.created_at DESC, aa.match_score DESC
    """

    amount_re = re.compile(
        r"(?:Signed\s+Contract\s+[Pp]rice|Evaluated\s+Bid\s+Price|"
        r"Contract\s+Amount|Award\s+Amount|Total\s+Contract\s+Price)"
        r"\s*[:\n]?\s*(?:([A-Z]{3})\s+)?([\d,]+(?:\.\d+)?)",
        re.IGNORECASE,
    )
    currency_amount_re = re.compile(r"([A-Z]{3})\s*([\d,]+(?:\.\d+)?)", re.IGNORECASE)

    def apply_parsed(row, amount, currency=None):
        try:
            row["award_amount"] = float(amount.replace(",", ""))
        except (ValueError, TypeError):
            return
        if currency and not row.get("award_currency"):
            row["award_currency"] = currency.upper()

    columns = [
        ("Alert ID", "id"),
        ("Match Status", "match_status"),
        ("Match Score", "match_score"),
        ("Match Reason", "matched_reason"),
        ("Seen At", "seen_at"),
        ("Alert Created", "created_at"),
        ("Source Type", "source_notice_type"),
        ("Source Title", "source_title"),
        ("Source Project ID", "source_project_id"),
        ("Source Project Name", "source_project_name"),
        ("Source Country", "source_country"),
        ("Source Borrower", "source_borrower"),
        ("Source Notice Date", "source_notice_date"),
        ("Source URL", "source_url"),
        ("Award Type", "award_notice_type"),
        ("Award Title", "award_title"),
        ("Award Project ID", "award_project_id"),
        ("Award Project Name", "award_project_name"),
        ("Award Country", "award_country"),
        ("Award Borrower", "award_borrower"),
        ("Award Notice Date", "award_notice_date"),
        ("Award URL", "award_url"),
        ("Awarded Bidder(s)", "awarded_bidders"),
        ("Award Amount", "award_amount"),
        ("Award Currency", "award_currency"),
    ]

    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([label for label, _ in columns])
        yield buf.getvalue()

        with db() as conn, conn.cursor(name="award_alerts_export_cur") as cur:
            cur.itersize = 2000
            cur.execute(sql, params)
            while True:
                batch = cur.fetchmany(2000)
                if not batch:
                    break
                buf.seek(0)
                buf.truncate()
                for row in batch:
                    if row.get("award_amount") is None:
                        desc = row.get("award_description") or ""
                        m = amount_re.search(desc)
                        if m:
                            apply_parsed(row, m.group(2), m.group(1))
                        if row.get("award_amount") is None:
                            for cm in currency_amount_re.finditer(desc):
                                apply_parsed(row, cm.group(2), cm.group(1))
                                break
                    writer.writerow([row.get(key, "") for _, key in columns])
                yield buf.getvalue()

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M")
    filename = f"WB_Award_Alerts_{timestamp}.csv"
    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.put("/{alert_id}/seen")
def mark_award_alert_seen(alert_id: int, _: dict = Depends(require_auth)):
    ensure_award_alert_tables()
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE award_alerts
                SET seen_at = COALESCE(seen_at, NOW()), updated_at = NOW()
                WHERE id = %s
                RETURNING id
            """,
                [alert_id],
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Award alert not found")
    return {"status": "ok", "id": alert_id}


@router.post("/mark-all-seen")
def mark_all_award_alerts_seen(_: dict = Depends(require_auth)):
    ensure_award_alert_tables()
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE award_alerts
                SET seen_at = COALESCE(seen_at, NOW()), updated_at = NOW()
                WHERE dismissed_at IS NULL AND seen_at IS NULL
            """)
            count = cur.rowcount
        conn.commit()
    return {"status": "ok", "updated": count}


@router.put("/{alert_id}/status")
def update_award_alert_status(
    alert_id: int,
    match_status: str = Query(..., regex="^(confirmed|rejected|needs_review|auto_matched)$"),
    _: dict = Depends(require_auth),
):
    ensure_award_alert_tables()
    dismissed_expr = "NOW()" if match_status == "rejected" else "NULL"
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE award_alerts
                SET match_status = %s,
                    dismissed_at = {dismissed_expr},
                    seen_at = COALESCE(seen_at, NOW()),
                    updated_at = NOW()
                WHERE id = %s
                RETURNING id
            """,
                [match_status, alert_id],
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Award alert not found")
    return {"status": "ok", "id": alert_id, "match_status": match_status}
