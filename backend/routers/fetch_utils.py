"""Shared fetch pipeline helpers — used by both the job worker and HTTP triggers."""

import logging
from datetime import date, datetime

from db import get_app_settings_map, q

log = logging.getLogger(__name__)


def run_full_fetch(payload: dict) -> dict:
    """Full fetch: all countries from baseline, then bidder import + award alerts."""
    import fetcher
    from routers.awards import sync_award_alerts
    from routers.bidders import import_missing_awards_by_country

    since = _resolve_since(payload.get("since"))
    with_bidders = payload.get("with_bidders", True)

    fetcher.init_db()
    conn = fetcher.get_connection()
    try:
        country_rows = q("SELECT name FROM target_countries ORDER BY name")
        countries = [r["name"] for r in country_rows]
        upserted, new_records = fetcher.fetch_batch_resilient(conn, countries, since)
        failed_rows = q(
            "SELECT country FROM country_fetch_status WHERE country = ANY(%s) AND status = 'failed' ORDER BY country",
            (countries,),
        )
        failed_countries = [r["country"] for r in failed_rows]
        success = not failed_countries
        error_msg = ("Partial success: failed countries: " + ", ".join(failed_countries)) if failed_countries else None
        fetcher.log_run(conn, ",".join(countries), upserted, new_records, success, error_msg)
    finally:
        conn.close()

    bidder_result = None
    alert_result = None
    if success and with_bidders:
        bidder_result = {"countries": {}}
        for c in countries:
            try:
                bidder_result["countries"][c] = import_missing_awards_by_country(c)
            except Exception as e:
                bidder_result["countries"][c] = {"status": "error", "error": str(e)}
    try:
        alert_result = sync_award_alerts()
    except Exception as e:
        alert_result = {"status": "error", "error": str(e)}

    return {
        "exit_code": 0 if success else 1,
        "stdout": f"Full fetch finished: {upserted} upserted, {new_records} new across {len(countries)} countries",
        "stderr": error_msg or "",
        "success": success,
        "bidder_import": bidder_result,
        "award_alerts": alert_result,
    }


def run_country_backfill(payload: dict) -> dict:
    """Backfill a single country pipeline."""
    name = payload["name"]
    since = _resolve_since(payload.get("since"))
    with_bidders = payload.get("with_bidders", True)

    import fetcher
    from routers.awards import sync_award_alerts
    from routers.bidders import import_missing_awards_by_country

    fetcher.init_db()
    conn = fetcher.get_connection()
    try:
        upserted, new_records = fetcher.fetch_batch_resilient(conn, [name], since)
        rows = q("SELECT status, error_msg FROM country_fetch_status WHERE country = %s", [name])
        country_status = rows[0]["status"] if rows else "unknown"
        error_msg = rows[0]["error_msg"] if rows else None
        success = country_status != "failed"
        fetcher.log_run(conn, name, upserted, new_records, success, error_msg)
    finally:
        conn.close()

    bidder_result = None
    alert_result = None
    if success:
        if with_bidders:
            try:
                bidder_result = import_missing_awards_by_country(name)
            except Exception as e:
                bidder_result = {"status": "error", "error": str(e)}
        try:
            alert_result = sync_award_alerts()
        except Exception as e:
            alert_result = {"status": "error", "error": str(e)}

    return {
        "exit_code": 0 if success else 1,
        "stdout": f"{name} backfill finished from {since}: {upserted} fetched, {new_records} new, status={country_status}",
        "stderr": error_msg or "",
        "success": success,
        "bidder_import": bidder_result,
        "award_alerts": alert_result,
    }


def _resolve_since(since_str) -> date:
    if since_str:
        try:
            return datetime.strptime(str(since_str)[:10], "%Y-%m-%d").date()
        except ValueError:
            pass
    settings = get_app_settings_map()
    try:
        return datetime.strptime(settings.get("baseline_date", "2025-01-01"), "%Y-%m-%d").date()
    except ValueError:
        return date(2025, 1, 1)
