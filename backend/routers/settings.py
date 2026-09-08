from datetime import date, timedelta

from auth import require_auth
from db import db, ensure_support_tables, get_app_settings_map, q
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ── Models ────────────────────────────────────────────────────────────────────


class CountryBody(BaseModel):
    name: str


class CountriesBody(BaseModel):
    names: list[str]


class GeneralSettingsBody(BaseModel):
    baseline_date: str | None = None
    country_batch: int | None = None
    request_delay: float | None = None
    auto_sync_hour: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/countries")
def list_countries():
    rows = q("SELECT name, added_at FROM target_countries ORDER BY name")
    return [dict(r) for r in rows]


@router.post("/countries", status_code=201)
def add_country(body: CountryBody, _auth: dict = Depends(require_auth)):
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Country name cannot be empty")
    try:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO target_countries (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING name",
                    (name,),
                )
                result = cur.fetchone()
            conn.commit()
        if not result:
            raise HTTPException(409, f"'{name}' already exists")
        return {"name": name, "added": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e)) from e


@router.post("/countries/bulk", status_code=201)
def add_countries_bulk(body: CountriesBody, _auth: dict = Depends(require_auth)):
    names = [n.strip() for n in body.names if n and n.strip()]
    if not names:
        raise HTTPException(400, "No country names provided")
    added = []
    skipped = []
    try:
        with db() as conn:
            with conn.cursor() as cur:
                for name in names:
                    cur.execute(
                        "INSERT INTO target_countries (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING name",
                        (name,),
                    )
                    if cur.fetchone():
                        added.append(name)
                    else:
                        skipped.append(name)
            conn.commit()
        return {"added": added, "skipped": skipped}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e)) from e


@router.delete("/countries/{name}")
def remove_country(name: str, _: dict = Depends(require_auth)):
    with db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM target_countries WHERE name = %s RETURNING name", (name,))
            deleted = cur.fetchone()
        conn.commit()
    if not deleted:
        raise HTTPException(404, f"'{name}' not found")
    return {"name": name, "deleted": True}


@router.get("/general")
def get_general_settings():
    settings = get_app_settings_map()
    return {
        "baseline_date": settings.get("baseline_date", (date.today() - timedelta(days=730)).isoformat()),
        "country_batch": int(float(settings.get("country_batch", 5))),
        "request_delay": float(settings.get("request_delay", 1.2)),
        "auto_sync_hour": settings.get("auto_sync_hour", "06:00"),
        "updated_at": settings.get("updated_at"),
    }


@router.put("/general")
def update_general_settings(body: GeneralSettingsBody, _: dict = Depends(require_auth)):
    ensure_support_tables()
    updates = {
        "baseline_date": body.baseline_date,
        "country_batch": str(body.country_batch) if body.country_batch is not None else None,
        "request_delay": str(body.request_delay) if body.request_delay is not None else None,
        "auto_sync_hour": body.auto_sync_hour,
    }

    with db() as conn:
        with conn.cursor() as cur:
            for key, value in updates.items():
                if value is None:
                    continue
                cur.execute(
                    """
                    INSERT INTO app_settings (key, value, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
                    """,
                    (key, value),
                )
        conn.commit()

    return get_general_settings()
