#!/usr/bin/env python3
"""
One-time script to populate villages table with complete Ahilyanagar data.

Usage:
    python -m src.scripts.populate_ahilyanagar_villages

Strategy:
    All Overpass queries are STRICTLY scoped inside the Ahilyanagar/Ahmadnagar
    district boundary (admin_level=6). This prevents name collisions with other
    Maharashtra districts that share taluka names (e.g. Akola district in Vidarbha).

    Query flow per taluka:
      Q1 — taluka area scoped inside Ahilyanagar district boundary
      Q2 — villages tagged is_in:district=Ahmadnagar inside district boundary
      Q3 — all villages in district boundary, filtered by is_in:taluk tag
      Fallback — taluka centroid only (single point)

Expected runtime: ~5-8 minutes for all 14 talukas.
"""
import asyncio
import json
import logging
import os
import time
import urllib.parse
import urllib.request

from sqlalchemy import select, func, text as sql_text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.config import settings
from src.models import Village

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# (canonical DB name, OSM search name)
AHILYANAGAR_TALUKAS = [
    ("Ahmednagar",  "Ahmadnagar"),
    ("Akola",       "Akola"),
    ("Jamkhed",     "Jamkhed"),
    ("Karjat",      "Karjat"),
    ("Kopargaon",   "Kopargaon"),
    ("Nevasa",      "Nevasa"),
    ("Parner",      "Parner"),
    ("Pathardi",    "Pathardi"),
    ("Rahata",      "Rahata"),
    ("Rahuri",      "Rahuri"),
    ("Sangamner",   "Sangamner"),
    ("Shevgaon",    "Shevgaon"),
    ("Shrigonda",   "Shrigonda"),
    ("Shrirampur",  "Shrirampur"),
]

TALUKA_CENTROIDS = {
    "Ahmednagar":  (19.0948, 74.7480),
    "Akola":       (18.9667, 74.9833),
    "Jamkhed":     (18.7167, 75.3167),
    "Karjat":      (18.9167, 75.1167),
    "Kopargaon":   (19.8833, 74.4833),
    "Nevasa":      (19.5500, 74.9833),
    "Parner":      (19.0000, 74.4333),
    "Pathardi":    (19.1833, 75.1833),
    "Rahata":      (19.7167, 74.4833),
    "Rahuri":      (19.3833, 74.6500),
    "Sangamner":   (19.5667, 74.2167),
    "Shevgaon":    (19.3500, 75.1667),
    "Shrigonda":   (18.6167, 74.7000),
    "Shrirampur":  (19.6167, 74.6500),
}


def get_database_url() -> str:
    public_url = os.environ.get("DATABASE_PUBLIC_URL") or os.environ.get("POSTGRES_URL")
    if public_url:
        url = public_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        logger.info("Using DATABASE_PUBLIC_URL")
        return url
    logger.info("Using DATABASE_URL from settings")
    return settings.database_url


# ── Overpass helpers ──────────────────────────────────────────────────────────

def _overpass_post(ql: str) -> dict:
    data = urllib.parse.urlencode({"data": ql}).encode()
    req = urllib.request.Request(OVERPASS_URL, data=data, method="POST")
    req.add_header("User-Agent", "Dhyanada-VillageBot/1.0 (https://github.com/Life2death/dhyanada)")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def _parse_result(result: dict) -> list[tuple[str, float, float]]:
    villages = []
    seen = set()
    for el in result.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name:en") or tags.get("name")
        if not name or name in seen:
            continue
        if el["type"] == "node":
            lat, lon = el["lat"], el["lon"]
        elif el["type"] == "way":
            center = el.get("center", {})
            lat = center.get("lat")
            lon = center.get("lon")
            if lat is None:
                continue
        else:
            continue
        seen.add(name)
        villages.append((name, float(lat), float(lon)))
    return villages


def fetch_villages_for_taluka(canonical: str, osm_name: str) -> list[tuple[str, float, float]]:
    """
    All queries strictly scoped inside Ahilyanagar district boundary.
    Returns [(village_name, lat, lon), ...]
    """

    # Q1: taluka area nested inside Ahilyanagar district
    ql1 = f"""
[out:json][timeout:90];
area["name"~"Ahmadnagar|Ahilyanagar"]["admin_level"="6"]->.district;
area["name"="{osm_name}"](area.district)->.taluka;
(
  node["place"~"^(village|hamlet|town)$"](area.taluka);
  way["place"~"^(village|hamlet|town)$"](area.taluka);
);
out center;
"""
    try:
        r = _overpass_post(ql1)
        v = _parse_result(r)
        if v:
            logger.info(f"  Q1 → {len(v)} villages")
            return v
        logger.info(f"  Q1 → 0 villages, trying Q2...")
    except Exception as e:
        logger.warning(f"  Q1 failed: {e}, trying Q2...")

    time.sleep(3)

    # Q2: is_in:taluk tag inside district boundary
    ql2 = f"""
[out:json][timeout:90];
area["name"~"Ahmadnagar|Ahilyanagar"]["admin_level"="6"]->.district;
(
  node["place"~"^(village|hamlet|town)$"]["is_in:taluk"="{osm_name}"](area.district);
  way["place"~"^(village|hamlet|town)$"]["is_in:taluk"="{osm_name}"](area.district);
);
out center;
"""
    try:
        r = _overpass_post(ql2)
        v = _parse_result(r)
        if v:
            logger.info(f"  Q2 → {len(v)} villages")
            return v
        logger.info(f"  Q2 → 0 villages, trying Q3...")
    except Exception as e:
        logger.warning(f"  Q2 failed: {e}, trying Q3...")

    time.sleep(3)

    # Q3: search by taluka name in addr:subdistrict tag, still within district
    ql3 = f"""
[out:json][timeout:90];
area["name"~"Ahmadnagar|Ahilyanagar"]["admin_level"="6"]->.district;
(
  node["place"~"^(village|hamlet|town)$"]["addr:subdistrict"="{osm_name}"](area.district);
  way["place"~"^(village|hamlet|town)$"]["addr:subdistrict"="{osm_name}"](area.district);
);
out center;
"""
    try:
        r = _overpass_post(ql3)
        v = _parse_result(r)
        if v:
            logger.info(f"  Q3 → {len(v)} villages")
            return v
        logger.info(f"  Q3 → 0 villages, using centroid fallback")
    except Exception as e:
        logger.warning(f"  Q3 failed: {e}, using centroid fallback")

    # Fallback: just the taluka centroid (single point)
    lat, lon = TALUKA_CENTROIDS[canonical]
    logger.warning(f"  Fallback → centroid ({lat}, {lon})")
    return [(canonical, lat, lon)]


# ── Database helpers ──────────────────────────────────────────────────────────

async def cleanup_existing(session: AsyncSession) -> int:
    """Delete ALL existing Ahilyanagar villages so we start fresh."""
    result = await session.execute(
        sql_text("DELETE FROM villages WHERE district_slug = 'ahilyanagar'")
    )
    await session.commit()
    deleted = result.rowcount
    logger.info(f"🗑️  Deleted {deleted} existing Ahilyanagar village rows")
    return deleted


async def populate_database() -> dict:
    engine = create_async_engine(get_database_url())
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    stats = {"inserted": 0, "failed": 0, "talukas_done": 0}

    try:
        async with async_session() as session:
            # Always start clean to avoid stale/wrong data
            await cleanup_existing(session)

            for canonical, osm_name in AHILYANAGAR_TALUKAS:
                logger.info(f"\n📍 {canonical} (OSM: {osm_name})")
                try:
                    villages = await asyncio.to_thread(fetch_villages_for_taluka, canonical, osm_name)
                except Exception as e:
                    logger.error(f"  Fetch failed entirely: {e} — using centroid")
                    lat, lon = TALUKA_CENTROIDS[canonical]
                    villages = [(canonical, lat, lon)]

                logger.info(f"  Inserting {len(villages)} rows...")
                for vname, lat, lon in villages:
                    try:
                        await session.execute(
                            sql_text("""
                                INSERT INTO villages
                                    (village_name, taluka_name, district_name, district_slug, latitude, longitude)
                                VALUES (:vn, :tn, :dn, :ds, :lat, :lon)
                                ON CONFLICT (village_name, taluka_name, district_slug)
                                DO UPDATE SET latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude
                            """),
                            {"vn": vname, "tn": canonical,
                             "dn": "Ahilyanagar", "ds": "ahilyanagar",
                             "lat": lat, "lon": lon},
                        )
                        stats["inserted"] += 1
                    except Exception as e:
                        logger.error(f"  Insert failed for {vname}: {e}")
                        stats["failed"] += 1

                await session.commit()
                stats["talukas_done"] += 1
                logger.info(f"  ✅ {canonical} committed ({len(villages)} rows)")

                # Polite delay between Overpass requests
                time.sleep(3)

    finally:
        await engine.dispose()

    return stats


async def verify_population() -> dict:
    engine = create_async_engine(get_database_url())
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with async_session() as session:
            total_r = await session.execute(
                select(func.count(Village.id)).where(Village.district_slug == "ahilyanagar")
            )
            total = total_r.scalar()

            taluka_r = await session.execute(
                select(Village.taluka_name, func.count(Village.id))
                .where(Village.district_slug == "ahilyanagar")
                .group_by(Village.taluka_name)
                .order_by(Village.taluka_name)
            )
            by_taluka = dict(taluka_r.all())
        return {"total": total, "by_taluka": by_taluka}
    finally:
        await engine.dispose()


async def main():
    logger.info("=" * 70)
    logger.info("🌾 Ahilyanagar Villages — Strict District-Scoped Population")
    logger.info("=" * 70)
    logger.info("All queries scoped inside Ahilyanagar district boundary (admin_level=6)")
    logger.info(f"Talukas: {len(AHILYANAGAR_TALUKAS)}\n")

    stats = await populate_database()

    logger.info("\n📈 Population Stats:")
    logger.info(f"   Talukas done : {stats['talukas_done']}/14")
    logger.info(f"   Rows inserted: {stats['inserted']}")
    logger.info(f"   Rows failed  : {stats['failed']}")

    logger.info("\n⏳ Waiting 10 seconds before verification...")
    await asyncio.sleep(10)

    logger.info("\n🔍 Verification (live DB count):")
    v = await verify_population()
    logger.info(f"   Total villages in DB: {v['total']}")
    logger.info("\n   By Taluka:")
    for taluka, count in sorted(v["by_taluka"].items()):
        logger.info(f"      {taluka:20s}: {count:4d} villages")

    logger.info("\n" + "=" * 70)
    logger.info("✅ Done!")
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
