"""Post-fetch summary email — sent after every full fetch / country backfill.

Best-effort by design: any failure here is logged and never allowed to break
the job that triggered it. Disabled when email is not configured.
"""

import logging
from datetime import datetime

from config import APP_BASE_URL, email_configured
from db import q
from email_service import send_email

log = logging.getLogger(__name__)

_AWARD_TYPES = ("Award", "Contract Award")


def _recipients() -> list[dict]:
    return q(
        "SELECT username, email FROM users "
        "WHERE email IS NOT NULL AND TRIM(email) <> '' AND is_active = TRUE"
    )


def _job_facts(job_id: int) -> dict:
    rows = q(
        "SELECT id, job_type, started_at, finished_at, error FROM fetch_jobs WHERE id = %s",
        [job_id],
    )
    return rows[0] if rows else {}


def _new_notice_breakdown(since: datetime | None) -> dict:
    """Counts of notices ingested since the job started, split open vs awarded."""
    if since is None:
        return {}
    row = q(
        """
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE notice_type IN %s OR status = 'Awarded') AS awarded,
            COUNT(*) FILTER (WHERE notice_type = 'IFB') AS ifb,
            COUNT(*) FILTER (WHERE notice_type = 'REOI') AS reoi,
            COUNT(DISTINCT country) AS countries
        FROM procurement_notices
        WHERE fetched_at >= %s
        """,
        [_AWARD_TYPES, since],
    )[0]
    row["open"] = int(row["total"]) - int(row["awarded"])
    return row


def _per_country_new(since: datetime | None, limit: int = 12) -> list[dict]:
    if since is None:
        return []
    return q(
        """
        SELECT country, COUNT(*) AS count
        FROM procurement_notices
        WHERE fetched_at >= %s AND country IS NOT NULL AND TRIM(country) <> ''
        GROUP BY country
        ORDER BY count DESC, country
        LIMIT %s
        """,
        [since, limit],
    )


def _failed_countries(result: dict) -> list[str]:
    failed = result.get("failed_countries")
    if failed:
        return list(failed)
    stderr = result.get("stderr") or ""
    marker = "failed countries: "
    if marker in stderr:
        return [c.strip() for c in stderr.split(marker, 1)[1].split(",") if c.strip()]
    return []


def build_summary(job_id: int, job_type: str, payload: dict, result: dict) -> tuple[str, str, str] | None:
    """Return (subject, text, html) for a finished fetch job, or None."""
    facts = _job_facts(job_id)
    started = facts.get("started_at")
    finished = facts.get("finished_at") or datetime.now(started.tzinfo) if started else None
    duration_min = ""
    if started and finished:
        duration_min = f"{max(1, round((finished - started).total_seconds() / 60))} min"

    counts = result.get("run_counts") or {}
    notices = int(counts.get("notices_added", 0) or 0)
    alerts = int(counts.get("alerts_added", 0) or 0)
    bidders = int(counts.get("bidders_added", 0) or 0)
    borrowers = int(counts.get("borrowers_added", 0) or 0)

    breakdown = _new_notice_breakdown(started)
    awarded = int(breakdown.get("awarded", 0) or 0)
    open_count = int(breakdown.get("open", 0) or 0)
    countries_new = _per_country_new(started)
    failed = _failed_countries(result)
    success = bool(result.get("success", not failed))

    scope = payload.get("name") or ("All countries" if job_type == "full_fetch" else "Fetch")
    since = payload.get("since") or ""
    status_word = "completed" if success else "completed with errors"

    headline = (
        f"{notices} new notice{'s' if notices != 1 else ''} "
        f"({open_count} open, {awarded} awarded)"
    )
    subject = f"WB Tracker fetch {status_word}: {headline}"

    lines = [
        f"Hello,",
        "",
        f"The {scope} fetch {status_word}"
        + (f" in {duration_min}" if duration_min else "")
        + (f", searching back to {since}." if since else "."),
        "",
        f"New notices:        {notices} ({open_count} open, {awarded} awarded)",
        f"Award alerts added: {alerts}",
        f"Bidders added:      {bidders}",
        f"Borrowers added:    {borrowers}",
    ]
    if breakdown:
        lines.append(
            f"New by type:        IFB {breakdown.get('ifb', 0)}, REOI {breakdown.get('reoi', 0)}"
        )
    if countries_new:
        lines.append("")
        lines.append("New notices by country:")
        lines.extend(f"  {row['country']}: {row['count']}" for row in countries_new)
    if failed:
        lines.append("")
        lines.append("FAILED countries: " + ", ".join(failed))
    if result.get("stderr"):
        lines.append("")
        lines.append(f"Warning: {result['stderr']}")
    lines += [
        "",
        f"Open the dashboard: {APP_BASE_URL}",
    ]
    text = "\n".join(lines)

    def cell(label: str, value) -> str:
        return (
            '<td style="padding:10px 12px;border:1px solid #e4e8ef;">'
            f'<div style="font-size:10px;color:#7b879f;text-transform:uppercase;'
            f'letter-spacing:0.06em;">{label}</div>'
            f'<div style="font-size:20px;font-weight:700;margin-top:4px;">{value}</div></td>'
        )

    metrics = "".join(
        [
            cell("New notices", notices),
            cell("Open", open_count),
            cell("Awarded", awarded),
            cell("Alerts", alerts),
            cell("Bidders", bidders),
            cell("Borrowers", borrowers),
        ]
    )
    country_rows = "".join(
        f"<tr><td style='padding:6px 10px;border-bottom:1px solid #eef1f6;'>{row['country']}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #eef1f6;text-align:right;"
        f"font-weight:600;'>{row['count']}</td></tr>"
        for row in countries_new
    )
    country_block = (
        '<p style="margin:18px 0 6px;font-size:12px;color:#7b879f;text-transform:uppercase;'
        'letter-spacing:0.06em;">New notices by country</p>'
        f'<table style="border-collapse:collapse;width:100%;font-size:13px;">{country_rows}</table>'
        if country_rows
        else ""
    )
    failed_block = (
        f'<p style="margin:16px 0 0;padding:10px 12px;border:1px solid #f0b9b9;'
        f'background:#fdf3f3;border-radius:8px;color:#b33737;font-size:13px;">'
        f"<strong>Failed countries:</strong> {', '.join(failed)}</p>"
        if failed
        else ""
    )
    warning_block = (
        f'<p style="margin:12px 0 0;color:#a06516;font-size:13px;">Warning: {result.get("stderr")}</p>'
        if result.get("stderr")
        else ""
    )
    since_note = f" Searching back to {since}." if since else ""
    html = (
        '<div style="font-family:Arial,Helvetica,sans-serif;max-width:560px;margin:0 auto;">'
        '<img src="cid:logo" alt="WB Tracker" width="56" height="56" '
        'style="display:block;margin-bottom:16px;border-radius:12px;">'
        f"<p>Hello,</p>"
        f"<p>The <strong>{scope}</strong> fetch <strong>{status_word}</strong>"
        + (f" in {duration_min}." if duration_min else ".")
        + f"{since_note}</p>"
        f'<table style="border-collapse:collapse;width:100%;margin-top:8px;">'
        f'<tr>{metrics}</tr></table>'
        f"{country_block}{failed_block}{warning_block}"
        f'<p style="margin-top:18px;"><a href="{APP_BASE_URL}">Open the dashboard</a></p>'
        "</div>"
    )
    return subject, text, html


def notify_fetch_summary(job_id: int, job_type: str, payload: dict, result: dict) -> int:
    """Send the post-fetch summary to every active user with an email address.

    Returns the number of emails sent. Never raises.
    """
    try:
        if not email_configured():
            log.info("Fetch summary skipped for job #%s: email not configured", job_id)
            return 0
        built = build_summary(job_id, job_type, payload, result)
        if built is None:
            return 0
        subject, text, html = built
        sent = 0
        for user in _recipients():
            if send_email(user["email"], subject, text, html):
                sent += 1
        log.info("Fetch summary for job #%s sent to %s recipient(s)", job_id, sent)
        return sent
    except Exception:
        log.exception("Failed to send fetch summary for job #%s", job_id)
        return 0
