#!/usr/bin/env python3
"""
One-time script to populate villages table with complete Ahilyanagar data.

Usage:
    python -m src.scripts.populate_ahilyanagar_villages

Strategy:
    1. ONE Overpass query fetches ALL villages inside the Ahilyanagar district
       bounding box (no per-taluka area matching — avoids OSM taluka boundary
       bleeding across districts).
    2. Each village is assigned to its nearest taluka using centroid distance.
    3. Clean slate: existing rows deleted before re-insert.

Ahilyanagar bounding box (degrees):
    South: 18.55  North: 20.10
    West:  73.90  East:  75.65
"""
import asyncio
import json
import logging
import math
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

# Ahilyanagar district bounding box (tight — excludes adjacent districts)
BBOX = (18.55, 73.90, 20.10, 75.65)   # south, west, north, east

# Taluka centroids (lat, lon) — used for nearest-taluka assignment
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


def nearest_taluka(lat: float, lon: float) -> str:
    """Return the taluka name whose centroid is closest to (lat, lon)."""
    def dist(c):
        return math.hypot(lat - c[0], lon - c[1])
    return min(TALUKA_CENTROIDS, key=lambda t: dist(TALUKA_CENTROIDS[t]))


def fetch_all_villages() -> list[tuple[str, float, float]]:
    """
    Single Overpass bounding-box query → all villages in Ahilyanagar district.
    Returns [(name, lat, lon), ...]
    """
    south, west, north, east = BBOX
    bbox_str = f"{south},{west},{north},{east}"

    ql = f"""
[out:json][timeout:120];
(
  node["place"~"^(village|hamlet|town)$"]({bbox_str});
  way["place"~"^(village|hamlet|town)$"]({bbox_str});
);
out center;
"""
    logger.info(f"Querying Overpass for bbox {bbox_str}...")
    data = urllib.parse.urlencode({"data": ql}).encode()
    req = urllib.request.Request(OVERPASS_URL, data=data, method="POST")
    req.add_header("User-Agent", "Dhyanada-VillageBot/1.0 (https://github.com/Life2death/dhyanada)")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req, timeout=150) as resp:
        result = json.loads(resp.read().decode())

    villages = []
    seen = set()
    for el in result.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name:en") or tags.get("name")
        if not name:
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

        key = (name.strip(), round(lat, 4), round(lon, 4))
        if key in seen:
            continue
        seen.add(key)
        villages.append((name.strip(), float(lat), float(lon)))

    logger.info(f"Overpass returned {len(villages)} unique villages in bounding box")
    return villages


async def populate_database(villages: list[tuple[str, float, float]]) -> dict:
    engine = create_async_engine(get_database_url())
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    stats = {"inserted": 0, "failed": 0}

    try:
        async with async_session() as session:
            # Clean slate
            result = await session.execute(
                sql_text("DELETE FROM villages WHERE district_slug = 'ahilyanagar'")
            )
            await session.commit()
            logger.info(f"🗑️  Deleted {result.rowcount} existing rows")

            # Insert all villages, assigning each to its nearest taluka
            taluka_counts: dict[str, int] = {t: 0 for t in TALUKA_CENTROIDS}

            for i, (vname, lat, lon) in enumerate(villages, 1):
                taluka = nearest_taluka(lat, lon)
                try:
                    await session.execute(
                        sql_text("""
                            INSERT INTO villages
                                (village_name, taluka_name, district_name, district_slug, latitude, longitude)
                            VALUES (:vn, :tn, :dn, :ds, :lat, :lon)
                            ON CONFLICT (village_name, taluka_name, district_slug)
                            DO UPDATE SET latitude = EXCLUDED.latitude, longitude = EXCLUDED.longitude
                        """),
                        {"vn": vname, "tn": taluka,
                         "dn": "Ahilyanagar", "ds": "ahilyanagar",
                         "lat": lat, "lon": lon},
                    )
                    stats["inserted"] += 1
                    taluka_counts[taluka] += 1
                except Exception as e:
                    logger.error(f"  Insert failed for {vname}: {e}")
                    stats["failed"] += 1

                if i % 100 == 0:
                    logger.info(f"  Progress: {i}/{len(villages)}")

            await session.commit()

            logger.info("\n  Villages assigned per taluka:")
            for taluka, count in sorted(taluka_counts.items()):
                logger.info(f"    {taluka:20s}: {count:4d}")

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
    logger.info("🌾 Ahilyanagar Villages — Bounding Box + Nearest Taluka")
    logger.info("=" * 70)
    logger.info(f"Bounding box: {BBOX}")
    logger.info(f"Talukas: {len(TALUKA_CENTROIDS)}\n")

    # Step 1: Fetch all villages in one shot
    villages = await asyncio.to_thread(fetch_all_villages)

    # Step 2: Populate with nearest-taluka assignment
    stats = await populate_database(villages)

    logger.info(f"\n📈 Population Stats:")
    logger.info(f"   Total fetched : {len(villages)}")
    logger.info(f"   Rows inserted : {stats['inserted']}")
    logger.info(f"   Rows failed   : {stats['failed']}")

    logger.info("\n⏳ Waiting 10 seconds before verification...")
    await asyncio.sleep(10)

    logger.info("\n🔍 Verification (live DB):")
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
