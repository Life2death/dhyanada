"""Onboarding state machine — simplified 3-question flow with AI parsing.

Flow after consent:
  1. awaiting_name     — "What is your full name?"
  2. awaiting_location — "Type village, taluka, district" (AI parses)
  3. awaiting_crops    — "Which crops do you grow?" (AI parses)
  → active

Side paths (from any state):
  STOP   → opted_out
  DELETE → erasure_requested

Legacy states from the old multi-step flow are migrated forward automatically
so farmers stuck mid-registration are not left in a broken state.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from typing import Optional

import redis.asyncio as aioredis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.config import settings
from src.models.consent import ConsentEvent
from src.models.farmer import Farmer

logger = logging.getLogger(__name__)

CONSENT_VERSION = "1.0"
SESSION_TTL = 86_400  # 24 h

# Old multi-step states → nearest new state
_LEGACY_STATE_MAP: dict[str, str] = {
    "awaiting_first_name": "awaiting_name",
    "awaiting_last_name":  "awaiting_name",
    "awaiting_district":   "awaiting_location",
    "awaiting_taluka":     "awaiting_location",
    "awaiting_village":    "awaiting_location",
    "awaiting_language":   "awaiting_crops",
}

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


# ---------------------------------------------------------------------------
# Session dataclass
# ---------------------------------------------------------------------------

@dataclass
class OnboardingSession:
    phone: str
    state: str = "new"
    name: Optional[str] = None          # full name — one field instead of first/last
    district: Optional[str] = None
    taluka: Optional[str] = None
    village_id: Optional[int] = None
    village_name: Optional[str] = None
    crops: list[str] = field(default_factory=list)
    preferred_language: str = "mr"
    consent_given: bool = False
    # kept for backward-compat when reading old Redis sessions
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    @property
    def display_name(self) -> str:
        src = self.name or (
            f"{self.first_name or ''} {self.last_name or ''}".strip()
        )
        return src.split()[0] if src else "मित्र"


# ---------------------------------------------------------------------------
# Redis session persistence
# ---------------------------------------------------------------------------

def _redis() -> aioredis.Redis:
    return aioredis.from_url(settings.redis_url, decode_responses=True)


async def load_session(phone: str) -> OnboardingSession:
    async with _redis() as r:
        raw = await r.get(f"session:{phone}")
    if raw:
        data = json.loads(raw)
        known = {f.name for f in fields(OnboardingSession)}
        return OnboardingSession(**{k: v for k, v in data.items() if k in known})
    return OnboardingSession(phone=phone)


async def save_session(session: OnboardingSession) -> None:
    async with _redis() as r:
        await r.setex(
            f"session:{session.phone}", SESSION_TTL, json.dumps(asdict(session))
        )


async def delete_session(phone: str) -> None:
    async with _redis() as r:
        await r.delete(f"session:{phone}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def handle(phone: str, text: str) -> str:
    """Process one inbound message.

    Returns the reply string, or "" when the farmer is active and intent
    routing should take over.
    """
    msg = text.strip()

    if _matches_stop(msg):
        return await _transition_stop(phone)
    if _matches_delete(msg):
        return await _transition_delete(phone)

    session = await load_session(phone)

    # Migrate old multi-step sessions forward so they don't loop
    if session.state in _LEGACY_STATE_MAP:
        session.state = _LEGACY_STATE_MAP[session.state]
        await save_session(session)

    if session.state == "erasure_requested" and _matches_delete_confirm(msg):
        return await _transition_delete_confirm(phone)

    if session.state in ("opted_out", "erasure_requested", "erased"):
        return _msg_already_opted_out(session.preferred_language)

    if session.state == "new":
        # Guard: if this farmer is already registered in the DB, skip onboarding.
        # Happens when the 24-h Redis session expires between messages.
        if await _is_farmer_active(phone):
            return ""
        return await _enter_awaiting_consent(phone, session)

    if session.state == "awaiting_consent":
        return await _handle_consent(phone, session, msg)

    if session.state == "awaiting_name":
        return await _handle_name(phone, session, msg)

    if session.state == "awaiting_location":
        return await _handle_location(phone, session, msg)

    if session.state == "awaiting_crops":
        return await _handle_crops(phone, session, msg)

    if session.state == "active":
        return ""

    logger.warning("Unhandled onboarding state=%s phone=%s", session.state, phone)
    return ""


# ---------------------------------------------------------------------------
# State handlers
# ---------------------------------------------------------------------------

async def _is_farmer_active(phone: str) -> bool:
    """Return True if this phone is already a fully-registered active farmer in the DB."""
    try:
        db = await _get_db_session()
        async with db:
            result = await db.execute(
                select(Farmer).where(
                    Farmer.phone == phone,
                    Farmer.onboarding_state == "active",
                    Farmer.deleted_at == None,
                )
            )
            return result.scalar_one_or_none() is not None
    except Exception as exc:
        logger.error("_is_farmer_active error: %s", exc)
        return False


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
    affirmative = {"हो", "होय", "yes", "y", "ha", "haa", "हा"}
    negative = {"नाही", "no", "n", "nahi"}

    if msg.lower() in affirmative:
        session.consent_given = True
        session.state = "awaiting_name"
        await save_session(session)
        return (
            "धन्यवाद! 😊\n"
            "आपले *पूर्ण नाव* सांगा.\n\n"
            "Thank you! Please tell us your *full name*."
        )

    if msg.lower() in negative:
        session.state = "opted_out"
        await save_session(session)
        return (
            "ठीक आहे. कधीही 'Hi' पाठवून पुन्हा नोंदणी करा.\n"
            "OK. Send 'Hi' anytime to register."
        )

    return '"हो" किंवा "नाही" पाठवा. / Please send "YES" or "NO".'


async def _handle_name(phone: str, session: OnboardingSession, msg: str) -> str:
    name = msg.strip()
    if len(name) < 2:
        return (
            "कृपया आपले नाव पाठवा (किमान 2 अक्षरे).\n"
            "Please send your name (at least 2 letters)."
        )
    session.name = name[:100]
    session.state = "awaiting_location"
    await save_session(session)
    return (
        f"नमस्कार, *{name.split()[0]}*! 🙏\n\n"
        "आता तुमचे *गाव, तालुका आणि जिल्हा* एकत्र एका संदेशात पाठवा.\n"
        "उदाहरण: *वडेगाव, पारनेर, अहिल्यानगर*\n\n"
        "Now send your *village, taluka, and district* in one message.\n"
        "E.g: *Vadegaon, Parner, Ahilyanagar*"
    )


async def _handle_location(phone: str, session: OnboardingSession, msg: str) -> str:
    from src.onboarding.ai_parser import parse_location
    from src.ingestion.normalizer import normalize_district

    loc = await parse_location(msg)
    village = loc.get("village")

    if not village:
        return (
            "गाव सापडले नाही. कृपया असे पाठवा:\n"
            "*गाव, तालुका, जिल्हा* — उदा: *वडेगाव, पारनेर, अहिल्यानगर*\n\n"
            "Village not found. Please send:\n"
            "*village, taluka, district* — e.g: *Vadegaon, Parner, Ahilyanagar*"
        )

    session.village_name = village[:100]
    session.taluka = (loc.get("taluka") or "")[:100] or None
    raw_district = loc.get("district") or ""
    session.district = normalize_district(raw_district) or (raw_district[:50] or None)

    session.state = "awaiting_crops"
    await save_session(session)

    parts = [village]
    if session.taluka:
        parts.append(session.taluka)
    if session.district:
        parts.append(session.district)
    loc_display = ", ".join(parts)

    return (
        f"✅ स्थान नोंदवले: *{loc_display}*\n\n"
        "आता तुम्ही कोणती *पिके* घेतात ते सांगा.\n"
        "उदा: *कांदा, सोयाबीन, तूर, गहू, डाळिंब*\n\n"
        f"Location saved: *{loc_display}*\n"
        "Which *crops* do you grow?\n"
        "E.g: *onion, soyabean, tur, wheat, pomegranate*"
    )


async def _handle_crops(phone: str, session: OnboardingSession, msg: str) -> str:
    from src.onboarding.ai_parser import parse_crops

    crops = await parse_crops(msg)
    if not crops:
        return (
            "पीक ओळखता आले नाही. कृपया पुन्हा प्रयत्न करा.\n"
            "उदा: *कांदा, सोयाबीन, तूर*\n\n"
            "Could not identify crops. Try:\n"
            "*onion, soyabean, tur, wheat, cotton, pomegranate*"
        )

    session.crops = list(dict.fromkeys(crops))
    session.state = "active"
    await _persist_to_db(session)
    await delete_session(phone)

    name = session.display_name
    crops_mr = ", ".join(session.crops)
    loc = session.village_name or "-"
    return (
        f"🎉 नोंदणी पूर्ण झाली, *{name}*!\n"
        f"📍 गाव: {loc}\n"
        f"🌾 पिके: {crops_mr}\n\n"
        "दर रोज सकाळी ७ वाजता शेतकरी माहिती पत्र मिळेल.\n"
        "'भाव' पाठवून मंडी भाव, 'हवामान' पाठवून हवामान विचारा.\n\n"
        f"Registration complete, {name}! 🌾\n"
        "You'll get the daily farmer brief every morning at 7 AM."
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
    except Exception as exc:
        logger.error("delete_confirm error phone=%s: %s", phone, exc)

    await delete_session(phone)
    return (
        "आपला डेटा 30 दिवसांत हटवला जाईल. धन्यवाद.\n"
        "Your data will be deleted within 30 days. Thank you."
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

            # Split full name → first / last for the DB schema
            name_parts = (session.name or "").strip().split(None, 1)
            first_name = name_parts[0] if name_parts else None
            last_name = name_parts[1] if len(name_parts) > 1 else None

            if not farmer:
                farmer = Farmer(
                    phone=session.phone,
                    first_name=first_name,
                    last_name=last_name,
                    name=session.name,
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
                farmer.first_name = first_name
                farmer.last_name = last_name
                farmer.name = session.name
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

            from sqlalchemy import delete as sql_delete
            from src.models.farmer import CropOfInterest
            await db.execute(
                sql_delete(CropOfInterest).where(CropOfInterest.farmer_id == farmer.id)
            )
            for crop in session.crops:
                db.add(CropOfInterest(farmer_id=farmer.id, crop=crop))

            await db.commit()
            logger.info(
                "Persisted farmer phone=%s name=%s district=%s taluka=%s village=%s crops=%s",
                session.phone, session.name, session.district,
                session.taluka, session.village_name, session.crops,
            )
    except Exception as exc:
        logger.error("_persist_to_db error: %s", exc)


async def _log_consent_event_with_farmer_id(
    farmer_id: int, event_type: str, db: AsyncSession = None
) -> None:
    own_session = db is None
    if own_session:
        db = await _get_db_session()
    try:
        db.add(ConsentEvent(
            farmer_id=farmer_id,
            event_type=event_type,
            consent_version=CONSENT_VERSION,
            created_at=datetime.now(),
        ))
        if own_session:
            await db.commit()
    except Exception as exc:
        logger.error("consent_event farmer_id=%d type=%s: %s", farmer_id, event_type, exc)
    finally:
        if own_session:
            await db.close()


async def _log_consent_event(phone: str, event_type: str) -> None:
    try:
        db = await _get_db_session()
        async with db:
            result = await db.execute(select(Farmer).where(Farmer.phone == phone))
            farmer = result.scalar_one_or_none()
            if farmer:
                await _log_consent_event_with_farmer_id(farmer.id, event_type, db)
    except Exception as exc:
        logger.error("consent_event phone=%s type=%s: %s", phone, event_type, exc)


# ---------------------------------------------------------------------------
# Matchers
# ---------------------------------------------------------------------------

def _matches_stop(msg: str) -> bool:
    return msg.strip().lower() in {"stop", "थांबा", "बंद", "opt out", "optout"}


def _matches_delete(msg: str) -> bool:
    return bool(re.match(r"^(delete|माझा डेटा हटवा|erase)", msg.strip(), re.IGNORECASE))


def _matches_delete_confirm(msg: str) -> bool:
    return bool(re.match(r"^delete\s+confirm|^डेटा हटवा आहे$", msg.strip(), re.IGNORECASE))


def _msg_already_opted_out(lang: str) -> str:
    if lang == "mr":
        return "तुम्ही आधीच सेवेतून बाहेर पडलेले आहात. 'Hi' पाठवून पुन्हा नोंदणी करा."
    return "You have already opted out. Send 'Hi' to re-register."
