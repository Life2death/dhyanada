"""Farmer authentication logic for OTP-based login."""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.config import settings
from src.models.farmer import Farmer
from src.models.farmer_session import FarmerSession


async def request_login_otp(
    db: AsyncSession,
    phone: str,
) -> Tuple[bool, str]:
    """
    Request OTP for farmer login.

    Args:
        db: Database session
        phone: Farmer's phone number (international format: +91XXXXXXXXXX)

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Find or create farmer by phone
        stmt = select(Farmer).where(Farmer.phone == phone)
        result = await db.execute(stmt)
        farmer = result.scalar_one_or_none()

        if not farmer:
            # Create new farmer if doesn't exist
            farmer = Farmer(
                phone=phone,
                preferred_language="mr",  # Default to Marathi
                onboarding_state="awaiting_consent",
            )
            db.add(farmer)
            await db.flush()  # Flush to get farmer.id without committing

        # Generate OTP
        otp = FarmerSession.generate_otp()

        # Create session with OTP
        session_token = FarmerSession.generate_session_token()
        otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
        expires_at = datetime.utcnow() + timedelta(hours=24)

        session = FarmerSession(
            farmer_id=farmer.id,
            phone=phone,
            session_token=session_token,
            otp=otp,
            otp_expires_at=otp_expires_at,
            expires_at=expires_at,
        )
        db.add(session)
        await db.commit()

        # TODO: Send OTP via WhatsApp
        # await send_whatsapp_otp(phone, otp)

        return True, otp  # In development, return OTP; in production, don't return it

    except Exception as e:
        await db.rollback()
        return False, f"Error requesting OTP: {str(e)}"


async def verify_login_otp(
    db: AsyncSession,
    phone: str,
    otp: str,
) -> Tuple[bool, Optional[str], str]:
    """
    Verify OTP and create session token.

    Args:
        db: Database session
        phone: Farmer's phone number
        otp: 6-digit OTP entered by farmer

    Returns:
        Tuple of (success: bool, jwt_token: Optional[str], message: str)
    """
    try:
        # Find farmer
        stmt = select(Farmer).where(Farmer.phone == phone)
        result = await db.execute(stmt)
        farmer = result.scalar_one_or_none()

        if not farmer:
            return False, None, "Farmer not found"

        # Find the most recent session for this farmer
        stmt = (
            select(FarmerSession)
            .where(FarmerSession.farmer_id == farmer.id)
            .where(FarmerSession.verified_at.is_(None))  # Not yet verified
            .order_by(FarmerSession.created_at.desc())
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            return False, None, "No active OTP request found. Please request OTP again."

        # Check if OTP is expired
        if datetime.utcnow() > session.otp_expires_at:
            await db.delete(session)
            await db.commit()
            return False, None, "OTP expired. Please request a new OTP."

        # Check if OTP matches
        if session.otp != otp:
            return False, None, "Invalid OTP. Please try again."

        # Mark session as verified
        session.verified_at = datetime.utcnow()
        db.add(session)
        await db.commit()

        # Create JWT token
        payload = {
            "type": "farmer",
            "farmer_id": farmer.id,
            "phone": farmer.phone,
            "session_token": session.session_token,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow(),
        }

        token = jwt.encode(
            payload,
            settings.jwt_secret,
            algorithm="HS256"
        )

        return True, token, "OTP verified successfully"

    except Exception as e:
        await db.rollback()
        return False, None, f"Error verifying OTP: {str(e)}"


async def validate_farmer_session(
    db: AsyncSession,
    token: str,
) -> Tuple[bool, Optional[int], str]:
    """
    Validate farmer session token.

    Args:
        db: Database session
        token: JWT token from client

    Returns:
        Tuple of (is_valid: bool, farmer_id: Optional[int], message: str)
    """
    try:
        # Decode JWT
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"]
        )

        if payload.get("type") != "farmer":
            return False, None, "Invalid token type"

        farmer_id = payload.get("farmer_id")
        session_token = payload.get("session_token")

        if not farmer_id or not session_token:
            return False, None, "Missing farmer_id or session_token in token"

        # Find session in database
        stmt = (
            select(FarmerSession)
            .where(FarmerSession.farmer_id == farmer_id)
            .where(FarmerSession.session_token == session_token)
            .where(FarmerSession.verified_at.isnot(None))
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            return False, None, "Session not found or not verified"

        # Check if session is expired
        if datetime.utcnow() > session.expires_at:
            return False, None, "Session expired"

        # Check if farmer exists and is not deleted
        farmer_stmt = select(Farmer).where(Farmer.id == farmer_id)
        farmer_result = await db.execute(farmer_stmt)
        farmer = farmer_result.scalar_one_or_none()

        if not farmer or farmer.deleted_at is not None:
            return False, None, "Farmer not found or deleted"

        return True, farmer_id, "Session valid"

    except jwt.ExpiredSignatureError:
        return False, None, "Token expired"
    except jwt.InvalidTokenError:
        return False, None, "Invalid token"
    except Exception as e:
        return False, None, f"Error validating session: {str(e)}"


async def cleanup_expired_sessions(db: AsyncSession) -> int:
    """
    Delete expired sessions (older than 24 hours).

    Args:
        db: Database session

    Returns:
        Number of sessions deleted
    """
    try:
        stmt = select(FarmerSession).where(
            FarmerSession.expires_at < datetime.utcnow()
        )
        result = await db.execute(stmt)
        sessions = result.scalars().all()

        for session in sessions:
            await db.delete(session)

        await db.commit()
        return len(sessions)

    except Exception as e:
        await db.rollback()
        print(f"Error cleaning up expired sessions: {str(e)}")
        return 0
