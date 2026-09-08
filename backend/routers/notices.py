from datetime import date, timedelta

from db import ensure_support_tables, get_app_settings_map, q
from fastapi import APIRouter, Query
from services.tech import build_tech_notice_condition, classify_notice_tech

router = APIRouter(prefix="/api", tags=["notices"])

# Module-level reference set by main.py / routers.fetch after import
_fetch_status = {
    "running": False,
    "last_triggered": None,
    "last_finished": None,
    "last_result": None,
}


# ── Helpers ───────────────────────────────────────────────────────────────────


def get_country_fetch_status_rows():
    ensure_support_tables()
    rows = q("""
        WITH notice_counts AS (
            SELECT country,
                   COUNT(*) AS current_row_count,
                   MIN(notice_date)::text AS current_first_notice_date,
                   MAX(notice_date)::text AS current_last_notice_date,
                   MAX(fetched_at)::text AS current_last_fetched_at
            FROM procurement_notices
            WHERE country IS NOT NULL AND TRIM(country) <> ''
            GROUP BY country
        )
        SELECT
            c.name AS country,
            COALESCE(s.status,
                CASE WHEN COALESCE(n.current_row_count, 0) > 0 THEN 'success' ELSE 'not_started' END
            ) AS status,
            s.last_started_at::text,
            s.last_finished_at::text,
            s.last_success_at::text,
            s.last_attempted_since::text,
            s.last_page_size,
            COALESCE(s.fetched_records, 0) AS fetched_records,
            COALESCE(s.new_records, 0) AS new_records,
            COALESCE(s.total_available, 0) AS total_available,
            COALESCE(n.current_row_count, s.row_count, 0) AS row_count,
            COALESCE(n.current_first_notice_date, s.first_notice_date::text) AS first_notice_date,
            COALESCE(n.current_last_notice_date, s.last_notice_date::text) AS last_notice_date,
            n.current_last_fetched_at AS last_fetched_at,
            s.error_msg,
            s.api_url,
            COALESCE(s.retry_count, 0) AS retry_count,
            s.updated_at::text
        FROM target_countries c
        LEFT JOIN country_fetch_status s ON s.country = c.name
        LEFT JOIN notice_counts n ON n.country = c.name
        ORDER BY c.name
    """)

    def explain(row):
        if row["status"] == "failed":
            return row["error_msg"] or "Last fetch failed."
        if row["status"] == "running":
            return "Fetch is currently running."
        if row["row_count"]:
            if row["fetched_records"]:
                return "Fetched successfully in the last run."
            return "Has stored notices; no new notices were added in the last run."
        if row["status"] == "no_recent_notices":
            return "No notices matched the current incremental date window."
        if row["status"] == "no_data":
            return "Fetch completed, but no notices were stored for this country."
        return "No fetch has been recorded for this country yet."

    output = []
    for row in rows:
        item = dict(row)
        item["explanation"] = explain(item)
        output.append(item)
    return output


def build_where(country, notice_type, status, from_date, to_date, search, tech_only=False, borrower=None):
    filters = ["1=1"]
    params = []

    if country:
        filters.append("country = %s")
        params.append(country)
    if notice_type:
        filters.append("""(
            notice_type = %s OR
            notice_type ILIKE %s OR
            notice_type ILIKE %s
        )""")
        full = {
            "IFB": "%Invitation for Bids%",
            "REOI": "%Expression of Interest%",
            "Contract Award": "%Contract Award%",
            "Award": "%Contract Award%",
        }
        params.append(notice_type)
        params.append(full.get(notice_type, f"%{notice_type}%"))
        params.append(f"%{notice_type}%")
    if status:
        filters.append("status ILIKE %s")
        params.append(status)
    if from_date:
        filters.append("notice_date >= %s")
        params.append(from_date)
    if to_date:
        filters.append("notice_date <= %s")
        params.append(to_date)
    if search:
        filters.append("(title ILIKE %s OR description ILIKE %s OR project_name ILIKE %s)")
        like = f"%{search}%"
        params.extend([like, like, like])
    if borrower:
        filters.append("borrower = %s")
        params.append(borrower)
    if tech_only:
        tech_filter, tech_params = build_tech_notice_condition()
        filters.append(tech_filter)
        params.extend(tech_params)

    return " AND ".join(filters), params


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/notices")
def get_notices(
    country: str | None = Query(None),
    notice_type: str | None = Query(None),
    status: str | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    search: str | None = Query(None),
    borrower: str | None = Query(None),
    tech_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, le=100),
    sort_by: str = Query("notice_date", regex="^(notice_date|award_date)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
):
    where, params = build_where(country, notice_type, status, from_date, to_date, search, tech_only, borrower)
    offset = (page - 1) * page_size

    country_rows = q("SELECT name FROM target_countries ORDER BY name")
    if country_rows:
        available_countries = [r["name"] for r in country_rows]
    else:
        available_countries = [
            r["country"]
            for r in q("""
            SELECT DISTINCT country FROM procurement_notices
            WHERE country IS NOT NULL AND TRIM(country) <> ''
            ORDER BY country
        """)
        ]

    dir = "DESC" if sort_order == "desc" else "ASC"

    award_date_subq = "(SELECT MAX(ba.award_date) FROM bidder_awards ba WHERE ba.notice_id = procurement_notices.id)"
    order_clause = f"{award_date_subq} {dir} NULLS LAST" if sort_by == "award_date" else f"notice_date {dir} NULLS LAST"

    award_amount_subq = "(SELECT MAX(ba.award_amount) FROM bidder_awards ba WHERE ba.notice_id = procurement_notices.id AND ba.won IS TRUE)"
    award_currency_subq = """
        (SELECT ba.currency FROM bidder_awards ba
         WHERE ba.notice_id = procurement_notices.id AND ba.won IS TRUE
         ORDER BY ba.award_amount DESC NULLS LAST LIMIT 1)
    """

    rows = q(
        f"""SELECT
                id, project_id, project_name, country, notice_type,
                procurement_method, title, description,
                COALESCE(submission_date, submission_deadline::date)::text AS submission_date,
                notice_date::text,
                contract_amount, currency, borrower, contact_email, url, status,
                fetched_at,
                {award_date_subq}::text AS award_date,
                {award_amount_subq} AS award_amount,
                {award_currency_subq} AS award_currency
            FROM procurement_notices
            WHERE {where}
            ORDER BY {order_clause}
            LIMIT %s OFFSET %s""",
        params + [page_size, offset],
    )
    total = q(f"SELECT COUNT(*) as cnt FROM procurement_notices WHERE {where}", params)

    output_rows = []
    for row in rows:
        item = dict(row)
        item.update(classify_notice_tech(item))
        if tech_only and not item["is_tech"]:
            continue
        output_rows.append(item)

    return {
        "total": total[0]["cnt"],
        "page": page,
        "page_size": page_size,
        "available_countries": available_countries,
        "data": output_rows,
    }


@router.get("/stats")
def get_stats(country: str | None = Query(None)):
    try:
        selected_country = country.strip() if country else None

        general_total_count = q("SELECT COUNT(*) as total FROM procurement_notices")
        general_total_ifb = q("SELECT COUNT(*) as total FROM procurement_notices WHERE notice_type = 'IFB'")
        general_total_reoi = q("SELECT COUNT(*) as total FROM procurement_notices WHERE notice_type = 'REOI'")
        general_total_award = q("""
            SELECT COUNT(*) as total
            FROM procurement_notices
            WHERE notice_type = 'Contract Award' OR notice_type = 'Award'
        """)
        general_countries_count = q("""
            SELECT COUNT(DISTINCT country) as count
            FROM procurement_notices
            WHERE country IS NOT NULL
        """)
        last_fetched = q("""
            SELECT MAX(fetched_at) as last_fetched
            FROM procurement_notices
        """)

        available_countries = q("""
            SELECT DISTINCT country
            FROM procurement_notices
            WHERE country IS NOT NULL AND TRIM(country) <> ''
            ORDER BY country
        """)
        configured_countries = q("""
            SELECT name
            FROM target_countries
            ORDER BY name
        """)

        configured_country_names = [r["name"] for r in configured_countries] if configured_countries else []
        active_country_names = [r["country"] for r in available_countries] if available_countries else []
        inactive_country_names = [name for name in configured_country_names if name not in set(active_country_names)]

        country_filter = ""
        params = []
        if selected_country:
            country_filter = " AND country = %s"
            params.append(selected_country)

        summary_total = q(f"SELECT COUNT(*) as total FROM procurement_notices WHERE 1=1{country_filter}", params)
        summary_ifb = q(
            f"SELECT COUNT(*) as total FROM procurement_notices WHERE notice_type = 'IFB'{country_filter}", params
        )
        summary_reoi = q(
            f"SELECT COUNT(*) as total FROM procurement_notices WHERE notice_type = 'REOI'{country_filter}", params
        )
        summary_award = q(
            f"""
            SELECT COUNT(*) as total
            FROM procurement_notices
            WHERE (notice_type = 'Contract Award' OR notice_type = 'Award'){country_filter}
        """,
            params,
        )
        summary_statuses = q(
            f"""
            SELECT COUNT(DISTINCT status) as count
            FROM procurement_notices
            WHERE status IS NOT NULL AND TRIM(status) <> ''{country_filter}
        """,
            params,
        )
        summary_borrowers = q(
            f"""
            SELECT COUNT(DISTINCT borrower) as count
            FROM procurement_notices
            WHERE borrower IS NOT NULL AND TRIM(borrower) <> ''{country_filter}
        """,
            params,
        )

        by_country = q("""
            SELECT
                country,
                COUNT(*) as total_count,
                COUNT(CASE WHEN notice_type = 'IFB' THEN 1 END) as ifb_count,
                COUNT(CASE WHEN notice_type = 'REOI' THEN 1 END) as reoi_count,
                COUNT(CASE WHEN notice_type = 'Contract Award' OR notice_type = 'Award' THEN 1 END) as award_count
            FROM procurement_notices
            WHERE country IS NOT NULL
            GROUP BY country
            ORDER BY total_count DESC
            LIMIT 10
        """)

        by_month = q(
            f"""
            SELECT
                TO_CHAR(notice_date::date, 'YYYY-MM') as month,
                COUNT(*) as count
            FROM procurement_notices
            WHERE notice_date IS NOT NULL{country_filter}
            GROUP BY TO_CHAR(notice_date::date, 'YYYY-MM')
            ORDER BY month DESC
            LIMIT 12
        """,
            params,
        )

        by_type = q(
            f"""
            SELECT notice_type, COUNT(*) as count
            FROM procurement_notices
            WHERE notice_type IS NOT NULL{country_filter}
            GROUP BY notice_type
            ORDER BY count DESC
        """,
            params,
        )

        by_status = q(
            f"""
            SELECT status, COUNT(*) as count
            FROM procurement_notices
            WHERE status IS NOT NULL AND TRIM(status) <> ''{country_filter}
            GROUP BY status
            ORDER BY count DESC
        """,
            params,
        )

        top_borrowers = q(
            f"""
            SELECT borrower, COUNT(*) as count
            FROM procurement_notices
            WHERE borrower IS NOT NULL AND TRIM(borrower) <> ''{country_filter}
            GROUP BY borrower
            ORDER BY count DESC, borrower ASC
            LIMIT 8
        """,
            params,
        )

        recent = q(
            f"""
            SELECT id, country, title, project_id, notice_type, notice_date::text, url
            FROM procurement_notices
            WHERE 1=1{country_filter}
            ORDER BY fetched_at DESC
            LIMIT 5
        """,
            params,
        )

        return {
            "selected_country": selected_country,
            "available_countries": active_country_names,
            "countries_overview": {
                "configured": configured_country_names,
                "active": active_country_names,
                "inactive": inactive_country_names,
                "configured_count": len(configured_country_names),
                "active_count": len(active_country_names),
                "inactive_count": len(inactive_country_names),
            },
            "summary": {
                "total": general_total_count[0]["total"] if general_total_count else 0,
                "total_ifb": general_total_ifb[0]["total"] if general_total_ifb else 0,
                "total_reoi": general_total_reoi[0]["total"] if general_total_reoi else 0,
                "total_award": general_total_award[0]["total"] if general_total_award else 0,
                "countries": general_countries_count[0]["count"] if general_countries_count else 0,
                "last_fetched": last_fetched[0]["last_fetched"] if last_fetched else None,
            },
            "country_summary": {
                "country": selected_country,
                "total": summary_total[0]["total"] if summary_total else 0,
                "total_ifb": summary_ifb[0]["total"] if summary_ifb else 0,
                "total_reoi": summary_reoi[0]["total"] if summary_reoi else 0,
                "total_award": summary_award[0]["total"] if summary_award else 0,
                "statuses": summary_statuses[0]["count"] if summary_statuses else 0,
                "borrowers": summary_borrowers[0]["count"] if summary_borrowers else 0,
            },
            "by_country": [dict(r) for r in by_country] if by_country else [],
            "by_month": [dict(r) for r in by_month] if by_month else [],
            "by_type": [dict(r) for r in by_type] if by_type else [],
            "by_status": [dict(r) for r in by_status] if by_status else [],
            "top_borrowers": [dict(r) for r in top_borrowers] if top_borrowers else [],
            "recent": [dict(r) for r in recent] if recent else [],
        }

    except Exception as e:
        return {
            "summary": {"total": 0, "countries": 0},
            "country_summary": {
                "country": selected_country if "selected_country" in locals() else None,
                "total": 0,
                "total_ifb": 0,
                "total_reoi": 0,
                "total_award": 0,
                "statuses": 0,
                "borrowers": 0,
            },
            "available_countries": [],
            "countries_overview": {
                "configured": [],
                "active": [],
                "inactive": [],
                "configured_count": 0,
                "active_count": 0,
                "inactive_count": 0,
            },
            "selected_country": selected_country if "selected_country" in locals() else None,
            "by_country": [],
            "recent": [],
            "by_month": [],
            "by_type": [],
            "by_status": [],
            "top_borrowers": [],
            "error": str(e),
        }


@router.get("/dashboard")
def get_dashboard(
    country: str | None = Query(None),
    notice_type: str | None = Query(None),
    status: str | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    search: str | None = Query(None),
):
    try:
        ensure_support_tables()
        where, params = build_where(country, notice_type, status, from_date, to_date, search)
        settings = get_app_settings_map()

        configured_rows = q("SELECT name FROM target_countries ORDER BY name")
        configured = [row["name"] for row in configured_rows]
        active_rows = q("""
            SELECT DISTINCT country
            FROM procurement_notices
            WHERE country IS NOT NULL AND TRIM(country) <> ''
            ORDER BY country
        """)
        active = [row["country"] for row in active_rows]
        active_set = set(active)
        inactive = [name for name in configured if name not in active_set]

        summary = q(
            f"""
            SELECT
                COUNT(*) AS total,
                COUNT(CASE WHEN notice_type = 'IFB' THEN 1 END) AS total_ifb,
                COUNT(CASE WHEN notice_type = 'REOI' THEN 1 END) AS total_reoi,
                COUNT(CASE WHEN notice_type = 'Contract Award' OR notice_type = 'Award' THEN 1 END) AS total_award,
                COUNT(DISTINCT country) AS countries,
                COUNT(DISTINCT borrower) FILTER (WHERE borrower IS NOT NULL AND TRIM(borrower) <> '') AS borrowers,
                COUNT(DISTINCT status) FILTER (WHERE status IS NOT NULL AND TRIM(status) <> '') AS statuses,
                MAX(fetched_at) AS last_fetched
            FROM procurement_notices
            WHERE {where}
        """,
            params,
        )[0]

        by_country = q(
            f"""
            SELECT
                country,
                COUNT(*) AS total_count,
                COUNT(CASE WHEN notice_type = 'IFB' THEN 1 END) AS ifb_count,
                COUNT(CASE WHEN notice_type = 'REOI' THEN 1 END) AS reoi_count,
                COUNT(CASE WHEN notice_type = 'Contract Award' OR notice_type = 'Award' THEN 1 END) AS award_count
            FROM procurement_notices
            WHERE {where} AND country IS NOT NULL AND TRIM(country) <> ''
            GROUP BY country
            ORDER BY total_count DESC, country ASC
            LIMIT 12
        """,
            params,
        )

        by_type = q(
            f"""
            SELECT notice_type, COUNT(*) AS count
            FROM procurement_notices
            WHERE {where} AND notice_type IS NOT NULL AND TRIM(notice_type) <> ''
            GROUP BY notice_type
            ORDER BY count DESC, notice_type ASC
        """,
            params,
        )

        by_status = q(
            f"""
            SELECT status, COUNT(*) AS count
            FROM procurement_notices
            WHERE {where} AND status IS NOT NULL AND TRIM(status) <> ''
            GROUP BY status
            ORDER BY count DESC, status ASC
        """,
            params,
        )

        by_month = q(
            f"""
            SELECT TO_CHAR(notice_date::date, 'YYYY-MM') AS month, COUNT(*) AS count
            FROM procurement_notices
            WHERE {where} AND notice_date IS NOT NULL
            GROUP BY TO_CHAR(notice_date::date, 'YYYY-MM')
            ORDER BY month DESC
        """,
            params,
        )

        top_borrowers = q(
            f"""
            SELECT borrower, COUNT(*) AS count, MAX(notice_date)::text AS last_notice_date
            FROM procurement_notices
            WHERE {where} AND borrower IS NOT NULL AND TRIM(borrower) <> ''
            GROUP BY borrower
            ORDER BY count DESC, borrower ASC
            LIMIT 10
        """,
            params,
        )

        recent = q(
            f"""
            SELECT id, country, title, project_id, notice_type, notice_date::text, url, borrower, status
            FROM procurement_notices
            WHERE {where}
            ORDER BY fetched_at DESC
            LIMIT 8
        """,
            params,
        )

        data_quality = q(
            f"""
            SELECT
                COUNT(*) FILTER (WHERE borrower IS NULL OR TRIM(borrower) = '') AS missing_borrower,
                COUNT(*) FILTER (WHERE contact_email IS NULL OR TRIM(contact_email) = '') AS missing_contact_email,
                COUNT(*) FILTER (WHERE submission_date IS NULL) AS missing_submission_date,
                COUNT(*) FILTER (WHERE procurement_method IS NULL OR TRIM(procurement_method) = '') AS missing_procurement_method
            FROM procurement_notices
            WHERE {where}
        """,
            params,
        )[0]

        deadlines = q(
            f"""
            SELECT
                COUNT(*) FILTER (WHERE COALESCE(submission_date, submission_deadline::date) BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days') AS upcoming_7_days,
                COUNT(*) FILTER (WHERE COALESCE(submission_date, submission_deadline::date) BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days') AS upcoming_30_days,
                COUNT(*) FILTER (WHERE COALESCE(submission_date, submission_deadline::date) < CURRENT_DATE AND status ILIKE 'Active') AS overdue_active
            FROM procurement_notices
            WHERE {where}
        """,
            params,
        )[0]

        upcoming_deadlines = q(
            f"""
            SELECT country, title, project_id, COALESCE(submission_date, submission_deadline::date)::text AS submission_date, notice_type, url
            FROM procurement_notices
            WHERE {where}
              AND COALESCE(submission_date, submission_deadline::date) IS NOT NULL
              AND COALESCE(submission_date, submission_deadline::date) BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days'
            ORDER BY COALESCE(submission_date, submission_deadline::date) ASC
            LIMIT 10
        """,
            params,
        )

        recent_changes = q(
            f"""
            SELECT country, title, project_id, notice_type, status, updated_at::text, notice_date::text
            FROM procurement_notices
            WHERE {where}
              AND updated_at IS NOT NULL
            ORDER BY updated_at DESC
            LIMIT 10
        """,
            params,
        )

        activity_scores = q("""
            SELECT
                c.name AS country,
                COUNT(p.id) FILTER (WHERE p.notice_date >= CURRENT_DATE - INTERVAL '30 days') AS recent_count
            FROM target_countries c
            LEFT JOIN procurement_notices p ON p.country = c.name
            GROUP BY c.name
            ORDER BY c.name
        """)
        scored = []
        for row in activity_scores:
            recent_count = int(row["recent_count"] or 0)
            if recent_count >= 15:
                score = "High"
            elif recent_count >= 5:
                score = "Moderate"
            elif recent_count >= 1:
                score = "Low"
            else:
                score = "Inactive"
            scored.append({"country": row["country"], "recent_count": recent_count, "score": score})

        fetch_runs = q("""
            SELECT run_at::text, country, fetched, new_records, success, error_msg
            FROM fetch_runs
            ORDER BY run_at DESC
            LIMIT 8
        """)

        fetch_health = {
            "running": _fetch_status["running"],
            "last_triggered": _fetch_status["last_triggered"],
            "last_finished": _fetch_status["last_finished"],
            "last_result": _fetch_status["last_result"],
            "recent_runs": [dict(r) for r in fetch_runs],
            "country_statuses": get_country_fetch_status_rows(),
        }

        return {
            "filters": {
                "country": country,
                "notice_type": notice_type,
                "status": status,
                "from_date": str(from_date) if from_date else "",
                "to_date": str(to_date) if to_date else "",
                "search": search or "",
            },
            "settings": {
                "baseline_date": settings.get("baseline_date", (date.today() - timedelta(days=730)).isoformat()),
                "country_batch": int(float(settings.get("country_batch", 5))),
                "request_delay": float(settings.get("request_delay", 1.2)),
                "auto_sync_hour": settings.get("auto_sync_hour", "06:00"),
            },
            "available_countries": active,
            "countries_overview": {
                "configured": configured,
                "active": active,
                "inactive": inactive,
                "configured_count": len(configured),
                "active_count": len(active),
                "inactive_count": len(inactive),
            },
            "summary": dict(summary),
            "by_country": [dict(r) for r in by_country],
            "by_type": [dict(r) for r in by_type],
            "by_status": [dict(r) for r in by_status],
            "by_month": [dict(r) for r in by_month],
            "top_borrowers": [dict(r) for r in top_borrowers],
            "recent": [dict(r) for r in recent],
            "data_quality": dict(data_quality),
            "deadlines": {
                **dict(deadlines),
                "upcoming": [dict(r) for r in upcoming_deadlines],
            },
            "recent_changes": [dict(r) for r in recent_changes],
            "activity_scores": scored,
            "fetch_health": fetch_health,
        }
    except Exception as e:
        return {
            "summary": {"total": 0, "countries": 0},
            "available_countries": [],
            "countries_overview": {
                "configured": [],
                "active": [],
                "inactive": [],
                "configured_count": 0,
                "active_count": 0,
                "inactive_count": 0,
            },
            "by_country": [],
            "by_type": [],
            "by_status": [],
            "by_month": [],
            "top_borrowers": [],
            "recent": [],
            "data_quality": {},
            "deadlines": {"upcoming": []},
            "recent_changes": [],
            "activity_scores": [],
            "fetch_health": {"recent_runs": [], "country_statuses": []},
            "error": str(e),
        }


@router.get("/notices/{notice_id}/bidders")
def get_notice_bidders(notice_id: str):
    """All bidders linked to a specific notice."""
    rows = q(
        """SELECT b.*, ba.won, ba.award_amount, ba.currency, ba.award_date
           FROM bidder_awards ba
           JOIN bidders b ON b.id = ba.bidder_id
           WHERE ba.notice_id = %s
           ORDER BY ba.won DESC, b.name ASC""",
        [notice_id],
    )
    return [dict(r) for r in rows]


@router.get("/notices/awards")
def get_award_notices(
    country: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, le=100),
):
    """
    List Contract Award notices with their bidder counts.
    Useful for seeing which notices have been processed and how many bidders were found.
    """
    filters = ["(notice_type = 'Contract Award' OR notice_type = 'Award')"]
    params = []

    if country:
        filters.append("pn.country = %s")
        params.append(country)
    if search:
        filters.append("(pn.title ILIKE %s OR pn.project_name ILIKE %s)")
        like = f"%{search}%"
        params.extend([like, like])

    where = " AND ".join(filters)
    offset = (page - 1) * page_size

    rows = q(
        f"""
        SELECT
            pn.id,
            pn.country,
            pn.title,
            pn.project_id,
            pn.project_name,
            pn.notice_date::text,
            pn.contract_amount,
            pn.currency,
            pn.borrower,
            pn.status,
            pn.url,
            COUNT(ba.id) AS bidder_count,
            COUNT(CASE WHEN ba.won THEN 1 END) AS winner_count
        FROM procurement_notices pn
        LEFT JOIN bidder_awards ba ON ba.notice_id = pn.id
        WHERE {where}
        GROUP BY pn.id
        ORDER BY pn.notice_date DESC NULLS LAST
        LIMIT %s OFFSET %s
    """,
        params + [page_size, offset],
    )

    total = q(f"SELECT COUNT(*) AS cnt FROM procurement_notices pn WHERE {where}", params)

    return {
        "total": total[0]["cnt"] if total else 0,
        "page": page,
        "page_size": page_size,
        "data": [dict(r) for r in rows],
    }
