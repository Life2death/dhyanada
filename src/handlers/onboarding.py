"""Onboarding state machine.

States: new → awaiting_consent → awaiting_first_name → awaiting_last_name
        → awaiting_district → awaiting_taluka → awaiting_village
        → awaiting_crops → awaiting_language → active

Side paths (from any state):
  STOP   → opted_out
  DELETE → erasure_requested
"""
import json
import logging
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from typing import Optional

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update

from src.config import settings
from src.models.farmer import Farmer
from src.models.consent import ConsentEvent

logger = logging.getLogger(__name__)

VALID_STATES = [
    "new",
    "awaiting_consent",
    "awaiting_first_name",
    "awaiting_last_name",
    "awaiting_district",
    "awaiting_taluka",
    "awaiting_village",
    "awaiting_crops",
    "awaiting_language",
    "active",
    "opted_out",
    "erasure_requested",
    "erased",
]

VALID_DISTRICTS = {"latur", "nanded", "jalna", "akola", "yavatmal"}
VALID_CROPS = {"soyabean", "tur", "cotton"}
VALID_LANGUAGES = {"mr", "en"}
CONSENT_VERSION = "1.0"

# Talukas in Ahilyanagar district (canonical → display)
_AHILYANAGAR_TALUKAS: dict[str, str] = {
    "ahmednagar": "Ahmednagar", "ahilyanagar": "Ahmednagar", "nagar": "Ahmednagar",
    "akola": "Akola",
    "jamkhed": "Jamkhed",
    "karjat": "Karjat",
    "kopargaon": "Kopargaon",
    "nevasa": "Nevasa", "newasa": "Nevasa",
    "parner": "Parner",
    "pathardi": "Pathardi",
    "rahata": "Rahata",
    "rahuri": "Rahuri",
    "sangamner": "Sangamner",
    "shevgaon": "Shevgaon",
    "shrigonda": "Shrigonda",
    "shrirampur": "Shrirampur",
}

# Districts that have a seeded village DB (taluka validation + village lookup)
_DISTRICTS_WITH_VILLAGE = {"ahilyanagar"}

# Redis TTL: 24 hours
SESSION_TTL = 86_400

_engine = None
_async_session_factory = None


async def _get_db_session() -> AsyncSession:
    global _engine, _async_session_factory
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False)
        _async_session_factory = sessionmaker(
            _engine, class_=AsyncSession, expire_on_commit=False
        )
    return _async_session_factory()


@dataclass
class OnboardingSession:
    phone: str
    state: str = "new"
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    district: Optional[str] = None
    taluka: Optional[str] = None
    village_id: Optional[int] = None
    village_name: Optional[str] = None
    crops: list[str] = field(default_factory=list)
    preferred_language: str = "mr"
    consent_given: bool = False

    @property
    def display_name(self) -> str:
        parts = [p for p in [self.first_name, self.last_name] if p]
        return " ".join(parts) if parts else "मित्र"


# ---------------------------------------------------------------------------
# Session persistence (Redis)
# ---------------------------------------------------------------------------

def _redis() -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, decode_responses=True)


async def load_session(phone: str) -> OnboardingSession:
    """Load session from Redis, or return a fresh one."""
    async with _redis() as r:
        raw = await r.get(f"session:{phone}")
    if raw:
        data = json.loads(raw)
        # Filter to known fields for backward compat with old session format
        known = {f.name for f in fields(OnboardingSession)}
        data = {k: v for k, v in data.items() if k in known}
        return OnboardingSession(**data)
    return OnboardingSession(phone=phone)


async def save_session(session: OnboardingSession) -> None:
    async with _redis() as r:
        await r.setex(f"session:{session.phone}", SESSION_TTL, json.dumps(asdict(session)))


async def delete_session(phone: str) -> None:
    async with _redis() as r:
        await r.delete(f"session:{phone}")


# ---------------------------------------------------------------------------
# State machine entry point
# ---------------------------------------------------------------------------

async def handle(phone: str, text: str) -> str:
    """Process one inbound message through the onboarding state machine.

    Returns the reply to send back (empty string means the farmer is active —
    caller should proceed with normal intent routing).
    """
    msg = text.strip()

    # Global exit commands — checked before any state logic
    if _matches_stop(msg):
        return await _transition_stop(phone)
    if _matches_delete(msg):
        return await _transition_delete(phone)

    session = await load_session(phone)
    state = session.state

    if state == "erasure_requested" and _matches_delete_confirm(msg):
        return await _transition_delete_confirm(phone)

    if state in ("opted_out", "erasure_requested", "erased"):
        return _msg_already_opted_out(session.preferred_language)

    if state == "new":
        return await _enter_awaiting_consent(phone, session)

    if state == "awaiting_consent":
        return await _handle_consent(phone, session, msg)

    if state == "awaiting_first_name":
        return await _handle_first_name(phone, session, msg)

    if state == "awaiting_last_name":
        return await _handle_last_name(phone, session, msg)

    if state == "awaiting_district":
        return await _handle_district(phone, session, msg)

    if state == "awaiting_taluka":
        return await _handle_taluka(phone, session, msg)

    if state == "awaiting_village":
        return await _handle_village(phone, session, msg)

    if state == "awaiting_crops":
        return await _handle_crops(phone, session, msg)

    if state == "awaiting_language":
        return await _handle_language(phone, session, msg)

    if state == "active":
        # Active farmers are handled by the main intent dispatcher.
        return ""

    logger.warning("Unhandled onboarding state %s for %s", state, phone)
    return ""


# ---------------------------------------------------------------------------
# State handlers
# ---------------------------------------------------------------------------

async def _enter_awaiting_consent(phone: str, session: OnboardingSession) -> str:
    session.state = "awaiting_consent"
    await save_session(session)
    return (
        "नमस्कार! महाराष्ट्र किसान AI मध्ये आपले स्वागत आहे. 🌾\n"
        "आम्ही तुमचा फोन नंबर, नाव, जिल्हा, तालुका, गाव आणि पीक माहिती साठवतो — फक्त बाजारभाव कळवण्यासाठी.\n"
        '"हो" पाठवा सहमती देण्यासाठी. "नाही" पाठवा नाकारण्यासाठी.\n'
        "कधीही STOP पाठवून सेवा थांबवा.\n\n"
        "Welcome to Maharashtra Kisan AI! 🌾\n"
        "We store your phone, name, district, taluka, village, and crop info — only to send market prices.\n"
        'Send "YES" to agree or "NO" to decline.'
    )


async def _handle_consent(phone: str, session: OnboardingSession, msg: str) -> str:
    affirmative = {"हो", "yes", "y", "ha", "haa", "हा"}
    negative = {"नाही", "no", "n", "nahi"}

    if msg.lower() in affirmative:
        session.consent_given = True
        session.state = "awaiting_first_name"
        await save_session(session)
        return "धन्यवाद! आपले पहिले नाव (First Name) सांगा.\nThank you! Please share your first name."

    if msg.lower() in negative:
        session.state = "opted_out"
        await save_session(session)
        return (
            "ठीक आहे. तुम्ही सेवा वापरू शकत नाही.\n"
            "OK. You have declined. Send 'Hi' anytime to restart."
        )

    return '"हो" किंवा "नाही" पाठवा. / Please send "YES" or "NO".'


async def _handle_first_name(phone: str, session: OnboardingSession, msg: str) -> str:
    if len(msg) < 2 or len(msg) > 50:
        return "कृपया वैध पहिले नाव पाठवा (2–50 अक्षरे).\nPlease send a valid first name (2–50 characters)."
    session.first_name = msg.strip()
    session.state = "awaiting_last_name"
    await save_session(session)
    return "आपले आडनाव (Last Name) सांगा.\nPlease share your last name."


async def _handle_last_name(phone: str, session: OnboardingSession, msg: str) -> str:
    if len(msg) < 2 or len(msg) > 50:
        return "कृपया वैध आडनाव पाठवा (2–50 अक्षरे).\nPlease send a valid last name (2–50 characters)."
    session.last_name = msg.strip()
    session.state = "awaiting_district"
    await save_session(session)
    return (
        "तुमचा जिल्हा कोणता आहे?\n\n"
        "Which district are you from?\n"
        "पुणे / अहिल्यानगर / नाशिक / लातूर / नांदेड / औरंगाबाद\n"
        "Pune / Ahilyanagar / Nashik / Latur / Nanded / Aurangabad"
    )


async def _handle_district(phone: str, session: OnboardingSession, msg: str) -> str:
    from src.ingestion.normalizer import normalize_district

    canonical = normalize_district(msg)
    if not canonical:
        return (
            "जिल्हा ओळखता आला नाही. कृपया पुन्हा प्रयत्न करा.\n"
            "Could not recognise district. Please try:\n"
            "पुणे / अहिल्यानगर / नाशिक / लातूर / Pune / Ahilyanagar / Nashik / Latur"
        )
    session.district = canonical
    session.state = "awaiting_taluka"
    await save_session(session)

    if canonical in _DISTRICTS_WITH_VILLAGE:
        taluka_list = " / ".join(sorted(set(_AHILYANAGAR_TALUKAS.values())))
        return (
            f"तुमचा तालुका कोणता? अहिल्यानगर जिल्ह्यातील तालुके:\n\n"
            f"Which taluka in Ahilyanagar district?\n"
            f"{taluka_list}"
        )

    return (
        "तुमचा तालुका कोणता?\n\n"
        "Which taluka are you from? (Please type your taluka name)"
    )


async def _handle_taluka(phone: str, session: OnboardingSession, msg: str) -> str:
    raw = msg.strip()

    if session.district in _DISTRICTS_WITH_VILLAGE:
        # Validated taluka list for Ahilyanagar
        canonical_taluka = _AHILYANAGAR_TALUKAS.get(raw.lower())
        if not canonical_taluka:
            taluka_list = " / ".join(sorted(set(_AHILYANAGAR_TALUKAS.values())))
            return (
                "तालुका ओळखता आला नाही. कृपया खालीलपैकी एक पाठवा:\n"
                f"Taluka not recognised. Please send one of:\n{taluka_list}"
            )
        session.taluka = canonical_taluka
        session.state = "awaiting_village"
        await save_session(session)

        villages = await _fetch_villages_for_taluka(canonical_taluka, "ahilyanagar")
        if villages:
            village_list = "\n".join(f"• {v['name']}" for v in villages[:15])
            return (
                f"तुमचे गाव कोणते? {canonical_taluka} तालुक्यातील गावे:\n\n"
                f"Which village? Villages in {canonical_taluka} taluka:\n"
                f"{village_list}\n\n"
                "(तुमचे गाव नसल्यास जवळचे गाव पाठवा / Send nearest village if yours isn't listed)"
            )
        return (
            f"तुमचे गाव नाव पाठवा ({canonical_taluka} तालुका).\n"
            f"Please send your village name ({canonical_taluka} taluka)."
        )

    # Free-text taluka for all other districts
    if len(raw) < 2:
        return "कृपया तालुका नाव पाठवा.\nPlease send your taluka name."
    session.taluka = raw[:100]
    session.state = "awaiting_village"
    await save_session(session)
    return "तुमचे गाव नाव पाठवा.\nPlease send your village name."


async def _handle_village(phone: str, session: OnboardingSession, msg: str) -> str:
    raw_name = msg.strip()
    if session.district in _DISTRICTS_WITH_VILLAGE:
        village = await _lookup_village(raw_name, session.taluka, "ahilyanagar")
        if village:
            session.village_id = village["id"]
            session.village_name = village["name"]
        else:
            session.village_name = raw_name[:100]
    else:
        session.village_name = raw_name[:100]

    session.state = "awaiting_crops"
    await save_session(session)
    return (
        "कोणती पिके? (एकापेक्षा जास्त असल्यास comma ने विभाजित करा)\n\n"
        "Which crops are you interested in? (comma-separated)\n"
        "Soyabean / Tur / Cotton / Onion / Wheat / Pomegranate"
    )


async def _handle_crops(phone: str, session: OnboardingSession, msg: str) -> str:
    from src.ingestion.normalizer import normalize_commodity

    parts = [p.strip() for p in msg.replace(",", " ").split() if p.strip()]
    crops = [c for c in (normalize_commodity(p) for p in parts) if c]

    if not crops:
        return (
            "पीक ओळखता आले नाही. कृपया पुन्हा प्रयत्न करा.\n"
            "Could not recognise crop. Try: Soyabean / Tur / Cotton / Onion / Wheat"
        )
    session.crops = list(dict.fromkeys(crops))
    session.state = "awaiting_language"
    await save_session(session)
    return (
        "भाषा निवडा / Choose language:\n"
        "1 → मराठी\n"
        "2 → English"
    )


async def _handle_language(phone: str, session: OnboardingSession, msg: str) -> str:
    lang_map = {"1": "mr", "2": "en", "marathi": "mr", "मराठी": "mr", "english": "en", "en": "en"}
    lang = lang_map.get(msg.strip().lower())
    if not lang:
        return "1 (मराठी) किंवा 2 (English) पाठवा."

    session.preferred_language = lang
    session.state = "active"
    await _persist_to_db(session)
    await delete_session(phone)

    display = session.display_name
    if lang == "mr":
        return (
            f"नोंदणी पूर्ण झाली, {display}! 🌾\n"
            f"'भाव' पाठवून आजचा मंडी भाव विचारा, 'हवामान' पाठवून हवामान जाणून घ्या."
        )
    return (
        f"Registration complete, {display}! 🌾\n"
        f"Send 'price' for mandi rates or 'weather' for forecast anytime."
    )


# ---------------------------------------------------------------------------
# Stop / delete
# ---------------------------------------------------------------------------

async def _transition_stop(phone: str) -> str:
    session = await load_session(phone)
    session.state = "opted_out"
    await save_session(session)
    await _log_consent_event(phone, "opt_out")
    return (
        "तुम्हाला सेवेतून वगळण्यात आले आहे.\n"
        "You have been opted out. Send 'Hi' to re-register."
    )


async def _transition_delete(phone: str) -> str:
    session = await load_session(phone)
    session.state = "erasure_requested"
    await save_session(session)
    return (
        "डेटा हटवायचा आहे का? 'DELETE CONFIRM' पाठवा.\n"
        "Want to delete your data? Send 'DELETE CONFIRM' to confirm."
    )


async def _transition_delete_confirm(phone: str) -> str:
    try:
        db = await _get_db_session()
        async with db:
            stmt = select(Farmer).where(Farmer.phone == phone)
            result = await db.execute(stmt)
            farmer = result.scalar_one_or_none()

            if farmer:
                farmer.erasure_requested_at = datetime.now()
                await db.flush()
                await _log_consent_event_with_farmer_id(farmer.id, "erasure_request", db)

                from src.models.broadcast import BroadcastLog
                await db.execute(
                    update(BroadcastLog)
                    .where(BroadcastLog.farmer_id == farmer.id)
                    .values(deleted_at=datetime.now())
                )
                await db.commit()
                logger.info("Erasure request confirmed farmer_id=%d phone=%s", farmer.id, phone)
            else:
                logger.warning("Could not find farmer phone=%s for erasure confirmation", phone)
    except Exception as e:
        logger.error("Error confirming erasure for phone=%s: %s", phone, e)

    await delete_session(phone)
    return (
        "आपला डेटा 30 दिवसांत हटवला जाईल. विनंती करण्याबद्दल धन्यवाद.\n"
        "Your data will be deleted in 30 days. Thank you for letting us know."
    )


# ---------------------------------------------------------------------------
# DB persistence
# ---------------------------------------------------------------------------

async def _persist_to_db(session: OnboardingSession) -> None:
    try:
        db = await _get_db_session()
        async with db:
            stmt = select(Farmer).where(Farmer.phone == session.phone)
            result = await db.execute(stmt)
            farmer = result.scalar_one_or_none()

            full_name = f"{session.first_name or ''} {session.last_name or ''}".strip() or None

            if not farmer:
                farmer = Farmer(
                    phone=session.phone,
                    first_name=session.first_name,
                    last_name=session.last_name,
                    name=full_name,
                    district=session.district,
                    taluka=session.taluka,
                    village_id=session.village_id,
                    preferred_language=session.preferred_language,
                    subscription_status="active",
                    onboarding_state="active",
                    consent_given_at=datetime.now(),
                    consent_version=CONSENT_VERSION,
                )
                db.add(farmer)
                await db.flush()
            else:
                farmer.first_name = session.first_name
                farmer.last_name = session.last_name
                farmer.name = full_name
                farmer.district = session.district
                farmer.taluka = session.taluka
                farmer.village_id = session.village_id
                farmer.preferred_language = session.preferred_language
                farmer.subscription_status = "active"
                farmer.onboarding_state = "active"
                farmer.consent_given_at = datetime.now()
                farmer.consent_version = CONSENT_VERSION
                await db.flush()

            await _log_consent_event_with_farmer_id(farmer.id, "opt_in", db)

            from src.models.farmer import CropOfInterest
            await db.execute(
                select(CropOfInterest).where(CropOfInterest.farmer_id == farmer.id)
            )
            for crop in session.crops:
                coi = CropOfInterest(farmer_id=farmer.id, crop=crop)
                db.add(coi)

            await db.commit()
            logger.info(
                "Persisted farmer phone=%s id=%d name=%s district=%s taluka=%s crops=%s lang=%s",
                session.phone, farmer.id, full_name, session.district,
                session.taluka, session.crops, session.preferred_language,
            )
    except Exception as e:
        logger.error("Error persisting farmer to DB: %s", e)


async def _log_consent_event_with_farmer_id(
    farmer_id: int, event_type: str, db: AsyncSession = None
) -> None:
    own_session = False
    if db is None:
        db = await _get_db_session()
        own_session = True

    try:
        event = ConsentEvent(
            farmer_id=farmer_id,
            event_type=event_type,
            consent_version=CONSENT_VERSION,
            created_at=datetime.now(),
        )
        db.add(event)
        if own_session:
            await db.commit()
        logger.info("Logged consent event farmer_id=%d type=%s", farmer_id, event_type)
    except Exception as e:
        logger.error("Error logging consent event farmer_id=%d type=%s: %s", farmer_id, event_type, e)
    finally:
        if own_session:
            await db.close()


async def _log_consent_event(phone: str, event_type: str) -> None:
    try:
        db = await _get_db_session()
        async with db:
            stmt = select(Farmer).where(Farmer.phone == phone)
            result = await db.execute(stmt)
            farmer = result.scalar_one_or_none()
            if farmer:
                await _log_consent_event_with_farmer_id(farmer.id, event_type, db)
            else:
                logger.warning("Could not find farmer phone=%s to log event type=%s", phone, event_type)
    except Exception as e:
        logger.error("Error logging consent event phone=%s type=%s: %s", phone, event_type, e)


# ---------------------------------------------------------------------------
# Village DB helpers
# ---------------------------------------------------------------------------

async def _fetch_villages_for_taluka(taluka: str, district_slug: str) -> list[dict]:
    try:
        from sqlalchemy import text as sql_text
        db = await _get_db_session()
        async with db:
            result = await db.execute(
                sql_text(
                    "SELECT id, village_name FROM villages "
                    "WHERE taluka_name = :taluka AND district_slug = :ds "
                    "ORDER BY village_name"
                ),
                {"taluka": taluka, "ds": district_slug},
            )
            return [{"id": row[0], "name": row[1]} for row in result.fetchall()]
    except Exception as exc:
        logger.error("_fetch_villages_for_taluka: %s", exc)
        return []


async def _lookup_village(name: str, taluka: str | None, district_slug: str) -> dict | None:
    try:
        from sqlalchemy import text as sql_text
        db = await _get_db_session()
        async with db:
            params: dict = {"name": name, "ds": district_slug}
            where = "LOWER(village_name) = LOWER(:name) AND district_slug = :ds"
            if taluka:
                where += " AND taluka_name = :taluka"
                params["taluka"] = taluka
            result = await db.execute(
                sql_text(
                    f"SELECT id, village_name, latitude, longitude FROM villages "
                    f"WHERE {where} LIMIT 1"
                ),
                params,
            )
            row = result.fetchone()
            if row:
                return {"id": row[0], "name": row[1], "lat": row[2], "lon": row[3]}
    except Exception as exc:
        logger.error("_lookup_village: %s", exc)
    return None


# ---------------------------------------------------------------------------
# Matchers
# ---------------------------------------------------------------------------

def _matches_stop(msg: str) -> bool:
    return msg.strip().lower() in {"stop", "थांबा", "बंद", "opt out", "optout"}


def _matches_delete(msg: str) -> bool:
    import re
    return bool(re.match(r"^(delete|माझा डेटा हटवा|erase)", msg.strip(), re.IGNORECASE))


def _matches_delete_confirm(msg: str) -> bool:
    import re
    return bool(re.match(r"^delete\s+confirm|^डेटा हटवा आहे$", msg.strip(), re.IGNORECASE))


def _msg_already_opted_out(lang: str) -> str:
    if lang == "mr":
        return "तुम्ही आधीच सेवेतून बाहेर पडलेले आहात. 'Hi' पाठवून पुन्हा नोंदणी करा."
    return "You have already opted out. Send 'Hi' to re-register."
