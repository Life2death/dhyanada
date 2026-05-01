"""Village confirmation handler — asks farmers to confirm their location.

Flow (first 3 days of onboarding):
  Farmer onboards → gets daily brief
  → Part 1 includes: "Your village is X. Want info for this village?"
  → If "हो" (yes) 3 times (any day): village_locked = True, no more prompts
  → If "नाही" (no): ask for new village, update farmer record
  → After day 3: auto-lock regardless of responses
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.farmer import Farmer

logger = logging.getLogger(__name__)


def get_village_display_name(farmer: Farmer) -> str:
    """Format farmer's village as 'village_name, taluka'."""
    parts = []
    if farmer.village_id and hasattr(farmer, 'village') and farmer.village:
        parts.append(farmer.village.village_name)
    elif farmer.village_id:
        # Fallback if relationship not loaded
        parts.append(f"Village ID {farmer.village_id}")

    if farmer.taluka:
        if parts:
            parts[0] = parts[0] + ", " + farmer.taluka
        else:
            parts.append(farmer.taluka)

    return " ".join(parts) if parts else "आपले गाव"


async def ask_village_confirmation(farmer: Farmer) -> str:
    """Generate village confirmation prompt in Marathi + English."""
    village_str = get_village_display_name(farmer)
    days_remaining = max(0, 3 - farmer.village_confirmation_count)

    confirmations_msg = ""
    if days_remaining > 0:
        confirmations_msg = f"\n({days_remaining} अधिक 'हो' आवश्यक लॉक करण्यासाठी)"

    return (
        f"📍 *आपल्या रेकॉर्डमध्ये गाव*: {village_str}\n"
        f"आपल्याला या गावासाठी दैनंदिन माहिती हवी का?{confirmations_msg}\n"
        f"'हो' किंवा 'नाही' पाठवा.\n\n"
        f"Our records: {village_str}\n"
        f"Want daily info for this village?\n"
        f"Send 'YES' or 'NO'."
    )


async def handle_village_confirmation(
    farmer: Farmer,
    text: str,
    db: AsyncSession,
) -> tuple[bool, str]:
    """
    Handle farmer's response to village confirmation prompt.

    Returns: (should_lock, response_message)
    """
    msg = text.strip().lower()
    affirmative = {"हो", "होय", "yes", "y", "ha", "haa", "हा", "yeah"}
    negative = {"नाही", "no", "n", "nahi"}

    if msg in affirmative:
        # Increment confirmation count
        farmer.village_confirmation_count = min(3, farmer.village_confirmation_count + 1)
        days_remaining = 3 - farmer.village_confirmation_count

        if farmer.village_confirmation_count >= 3:
            # Lock village after 3 confirmations
            farmer.village_locked = True
            farmer.village_confirmed_at = datetime.now()
            await db.commit()
            village_str = get_village_display_name(farmer)
            return (
                True,
                f"✅ आपल्या गावाची नोंदणी हिरवी झाली: *{village_str}*\n"
                f"आता दर रोज या गावासाठी माहिती मिळेल.\n\n"
                f"Confirmed! You'll get daily updates for {village_str}."
            )
        else:
            # Not locked yet, encourage more confirmations
            await db.commit()
            return (
                False,
                f"धन्यवाद! {days_remaining} अधिक 'हो' पाठवून कायम करा.\n"
                f"Thanks! Send {days_remaining} more 'YES' to lock in."
            )

    elif msg in negative:
        # Farmer wants to change village
        return (
            False,
            (
                "ठीक आहे. तुमचे नवे गाव, तालुका आणि जिल्हा सांगा.\n"
                "उदा: *वडेगाव, पारनेर, अहिल्यानगर*\n\n"
                "OK. Send your new *village, taluka, district*.\n"
                "E.g: *Vadegaon, Parner, Ahmednagar*"
            )
        )

    else:
        # Invalid response
        return (
            False,
            "'हो' किंवा 'नाही' पाठवा. / Please send 'YES' or 'NO'."
        )


async def reset_village_confirmations(db: AsyncSession, district: str) -> int:
    """
    Reset village confirmations for a specific district.
    Used for re-onboarding village preferences.

    Args:
        db: Database session
        district: District slug (e.g., 'ahmednagar')

    Returns: Count of farmers updated
    """
    result = await db.execute(
        select(Farmer).where(
            Farmer.district == district,
            Farmer.deleted_at == None,
            Farmer.subscription_status == "active",
        )
    )
    farmers = result.scalars().all()

    for farmer in farmers:
        farmer.village_confirmation_count = 0
        farmer.village_locked = False
        farmer.village_confirmed_at = None

    await db.commit()
    logger.info(f"Reset village confirmations for {len(farmers)} farmers in {district}")
    return len(farmers)
