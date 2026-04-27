#!/usr/bin/env python3
"""
Fetch all Ahilyanagar district villages from OpenStreetMap Overpass API
and write alembic/versions/0015_villages_full.py with accurate GPS coordinates.

Run once (takes ~5 min):
    python scripts/fetch_ahilyanagar_villages.py

No extra dependencies — uses Python stdlib only.
"""

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import date

DISTRICT_DISPLAY = "Ahilyanagar"
DISTRICT_SLUG = "ahilyanagar"

# OSM still indexes this district under the old name "Ahmednagar"
OSM_DISTRICT_NAME = "Ahmednagar"

# canonical taluka name → OSM search name (same in most cases)
TALUKAS: dict[str, str] = {
    "Ahmednagar": "Ahmednagar",
    "Akola": "Akola",
    "Jamkhed": "Jamkhed",
    "Karjat": "Karjat",
    "Kopargaon": "Kopargaon",
    "Nevasa": "Nevasa",
    "Parner": "Parner",
    "Pathardi": "Pathardi",
    "Rahata": "Rahata",
    "Rahuri": "Rahuri",
    "Sangamner": "Sangamner",
    "Shevgaon": "Shevgaon",
    "Shrigonda": "Shrigonda",
    "Shrirampur": "Shrirampur",
}

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# Nominatim requires a valid User-Agent and email
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "KisanAI-VillageSeeder/1.0 (vikram.panmand@gmail.com)"

# Approximate taluka centroids — used as coordinate fallback for villages
# that Overpass doesn't have coordinates for.
TALUKA_CENTROIDS: dict[str, tuple[float, float]] = {
    "Ahmednagar": (19.0948, 74.7480),
    "Akola":      (18.9667, 74.9833),
    "Jamkhed":    (18.7167, 75.3167),
    "Karjat":     (18.9167, 75.1167),
    "Kopargaon":  (19.8833, 74.4833),
    "Nevasa":     (19.5333, 74.9667),
    "Parner":     (19.0000, 74.4333),
    "Pathardi":   (19.1833, 75.1833),
    "Rahata":     (19.7167, 74.4833),
    "Rahuri":     (19.3833, 74.6500),
    "Sangamner":  (19.5667, 74.2000),
    "Shevgaon":   (19.3167, 75.1833),
    "Shrigonda":  (18.6167, 74.7000),
    "Shrirampur": (19.6167, 74.6500),
}


def _http_post(url: str, payload: str) -> dict:
    data = urllib.parse.urlencode({"data": payload}).encode()
    req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def _http_get(url: str, params: dict) -> list:
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{url}?{qs}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def fetch_via_overpass(taluka: str) -> list[tuple[str, float, float]]:
    """
    Query Overpass for all village/hamlet/town nodes within the taluka boundary.
    Falls back to a district-scoped query if the taluka area isn't found.
    """
    ql = f"""
[out:json][timeout:90];
(
  area["name"="{taluka}"]["admin_level"~"7|8"]["is_in:state_code"="MH"]->.t;
  area["name"="{taluka}"]["admin_level"~"7|8"]["is_in"~"Maharashtra"]->.t;
);
(
  node["place"~"^(village|hamlet|town)$"](area.t);
  way["place"~"^(village|hamlet|town)$"](area.t);
);
out center;
"""
    result = _http_post(OVERPASS_URL, ql)
    return _parse_overpass(result)


def fetch_via_overpass_district_scope(taluka: str) -> list[tuple[str, float, float]]:
    """
    Scoped query: find the taluka area inside Ahmednagar district,
    then fetch villages. More precise but slower.
    """
    ql = f"""
[out:json][timeout:120];
area["name"="{OSM_DISTRICT_NAME}"]["admin_level"="6"]->.d;
area["name"="{taluka}"](area.d)->.t;
(
  node["place"~"^(village|hamlet|town)$"](area.t);
  way["place"~"^(village|hamlet|town)$"](area.t);
);
out center;
"""
    result = _http_post(OVERPASS_URL, ql)
    return _parse_overpass(result)


def _parse_overpass(result: dict) -> list[tuple[str, float, float]]:
    seen: set[str] = set()
    villages: list[tuple[str, float, float]] = []
    for elem in result.get("elements", []):
        tags = elem.get("tags", {})
        # Prefer English name, fall back to primary (Marathi Devanagari)
        name = (
            tags.get("name:en")
            or tags.get("name")
            or tags.get("name:mr")
        )
        if not name:
            continue
        name = name.strip()
        if name in seen:
            continue
        # Nodes have lat/lon directly; ways have a center object
        if elem["type"] == "node":
            lat, lon = elem.get("lat"), elem.get("lon")
        else:
            c = elem.get("center", {})
            lat, lon = c.get("lat"), c.get("lon")
        if lat and lon:
            seen.add(name)
            villages.append((name, float(lat), float(lon)))
    return villages


def fetch_via_nominatim(taluka: str) -> list[tuple[str, float, float]]:
    """
    Last-resort: use Nominatim structured search to find the main taluka
    town and a few known sub-places. This won't enumerate all villages
    but ensures the taluka HQ is present.
    """
    params = {
        "q": f"{taluka}, {OSM_DISTRICT_NAME}, Maharashtra, India",
        "format": "json",
        "limit": 1,
        "addressdetails": 0,
    }
    results = _http_get(NOMINATIM_URL, params)
    if results:
        r = results[0]
        return [(taluka, float(r["lat"]), float(r["lon"]))]
    lat, lon = TALUKA_CENTROIDS[taluka]
    return [(taluka, lat, lon)]


def generate_migration(rows: list[tuple]) -> str:
    """Render the Alembic migration file content."""
    today = date.today().isoformat()
    entries = "\n".join(
        f'    ("{vn.replace(chr(34), chr(39))}", "{tn}", "{DISTRICT_DISPLAY}", '
        f'"{DISTRICT_SLUG}", {lat:.6f}, {lon:.6f}),'
        for vn, tn, lat, lon in rows
    )
    return f'''\
"""Reseed villages table — full Ahilyanagar district data from OSM.

Source: OpenStreetMap Overpass API (fetched {today})
Villages: {len(rows)} across 14 talukas.

Revision ID: 0015
Revises: 0014
Create Date: {today}
"""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None

_VILLAGES = [
{entries}
]


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM villages"))
    conn.execute(
        sa.text(
            "INSERT INTO villages "
            "(village_name, taluka_name, district_name, district_slug, latitude, longitude) "
            "VALUES (:vn, :tn, :dn, :ds, :lat, :lon)"
        ),
        [
            {{"vn": vn, "tn": tn, "dn": dn, "ds": ds, "lat": lat, "lon": lon}}
            for vn, tn, dn, ds, lat, lon in _VILLAGES
        ],
    )


def downgrade() -> None:
    op.get_bind().execute(sa.text("DELETE FROM villages"))
'''


def main() -> None:
    all_rows: list[tuple[str, str, float, float]] = []
    summary: dict[str, int] = {}

    for canonical, osm_name in TALUKAS.items():
        print(f"  {canonical:<20}", end=" ", flush=True)

        villages: list[tuple[str, float, float]] = []

        # Attempt 1: Overpass with state-code filter
        try:
            villages = fetch_via_overpass(osm_name)
            time.sleep(600)  # 10-minute gap between talukas
        except Exception as e:
            print(f"[overpass-1 failed: {e}]", end=" ", flush=True)

        # Attempt 2: district-scoped Overpass
        if not villages:
            try:
                villages = fetch_via_overpass_district_scope(osm_name)
                time.sleep(600)  # 10-minute gap between talukas
            except Exception as e:
                print(f"[overpass-2 failed: {e}]", end=" ", flush=True)

        # Attempt 3: Nominatim (at least gets the taluka HQ)
        if not villages:
            try:
                villages = fetch_via_nominatim(osm_name)
                time.sleep(1)
            except Exception as e:
                print(f"[nominatim failed: {e}]", end=" ", flush=True)
                lat, lon = TALUKA_CENTROIDS[canonical]
                villages = [(canonical, lat, lon)]

        count = len(villages)
        summary[canonical] = count
        print(f"{count} villages")
        for vn, lat, lon in villages:
            all_rows.append((vn, canonical, lat, lon))

    # Deduplicate by (name, taluka)
    seen: set[tuple[str, str]] = set()
    deduped: list[tuple[str, str, float, float]] = []
    for vn, tn, lat, lon in all_rows:
        key = (vn.lower(), tn)
        if key not in seen:
            seen.add(key)
            deduped.append((vn, tn, lat, lon))

    print(f"\n{'─'*45}")
    print(f"Total unique villages : {len(deduped)}")
    print(f"{'─'*45}")
    for t, c in summary.items():
        print(f"  {t:<20} {c}")

    out_path = Path("alembic/versions/0015_villages_full.py")
    out_path.write_text(generate_migration(deduped), encoding="utf-8")
    print(f"\nMigration written → {out_path}")
    print("Next: git add alembic/versions/0015_villages_full.py && git commit -m 'data: full Ahilyanagar village seed from OSM'")


if __name__ == "__main__":
    main()
