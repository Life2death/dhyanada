"""Hardcoded government schemes (fallback when APIs unavailable)."""
import logging
from datetime import date
from decimal import Decimal

from src.ingestion.schemes.sources.base import SchemeRecord, SchemeSource

logger = logging.getLogger(__name__)


class HardcodedSchemesSource(SchemeSource):
    """Hardcoded government schemes as fallback.

    This source is used when all API sources are unavailable.
    Updated annually or when schemes change significantly.
    """

    name = "hardcoded"

    async def fetch(self) -> list[SchemeRecord]:
        """Return hardcoded government schemes for Maharashtra."""
        try:
            logger.info("Using hardcoded government schemes (fallback)...")

            return [
                # PM-KISAN
                SchemeRecord(
                    scheme_name="PM Kisan Samman Nidhi Yojana",
                    scheme_slug="pm_kisan",
                    ministry="Ministry of Agriculture",
                    description="₹6,000/year direct income support to farmers",
                    eligibility_criteria={
                        "min_age": 18,
                        "max_land_hectares": 2,
                        "citizenship": "indian",
                    },
                    commodities=["wheat", "rice", "maize", "cotton", "onion", "potato"],
                    min_land_hectares=0,
                    max_land_hectares=2,
                    annual_benefit="₹6,000/year",
                    benefit_amount=Decimal("6000"),
                    application_deadline=date(2026, 12, 31),
                    district=None,
                    state="maharashtra",
                    raw_payload={"source": "hardcoded", "version": "2026-04"},
                ),

                # PM-FASAL
                SchemeRecord(
                    scheme_name="Pradhan Mantri Fasal Bima Yojana",
                    scheme_slug="pm_fasal",
                    ministry="Ministry of Agriculture",
                    description="Crop insurance with 70% premium subsidy",
                    eligibility_criteria={
                        "min_age": 18,
                        "land_ownership": "any",
                    },
                    commodities=["rice", "wheat", "maize", "cotton", "onion"],
                    min_land_hectares=0,
                    max_land_hectares=None,
                    annual_benefit="70% premium subsidy",
                    benefit_amount=Decimal("70"),
                    application_deadline=date(2026, 6, 30),
                    district=None,
                    state="maharashtra",
                    raw_payload={"source": "hardcoded", "version": "2026-04"},
                ),

                # Soil Health Card
                SchemeRecord(
                    scheme_name="Soil Health Card Scheme",
                    scheme_slug="soil_health_card",
                    ministry="Ministry of Agriculture",
                    description="Free soil testing and recommendations",
                    eligibility_criteria={
                        "min_age": 18,
                        "land_ownership": "any",
                    },
                    commodities=["all"],
                    min_land_hectares=0,
                    max_land_hectares=None,
                    annual_benefit="Free soil testing",
                    benefit_amount=Decimal("0"),  # Free service
                    application_deadline=date(2026, 12, 31),
                    district=None,
                    state="maharashtra",
                    raw_payload={"source": "hardcoded", "version": "2026-04"},
                ),

                # Paramparagat Krishi Vikas Yojana (Organic)
                SchemeRecord(
                    scheme_name="Paramparagat Krishi Vikas Yojana",
                    scheme_slug="pkvy_organic",
                    ministry="Ministry of Agriculture",
                    description="Organic farming promotion with ₹5,000/hectare subsidy",
                    eligibility_criteria={
                        "min_age": 18,
                        "max_land_hectares": 5,
                        "farming_type": "organic",
                    },
                    commodities=["vegetables", "fruits", "pulses", "spices"],
                    min_land_hectares=0,
                    max_land_hectares=5,
                    annual_benefit="₹5,000/hectare",
                    benefit_amount=Decimal("5000"),
                    application_deadline=date(2026, 8, 31),
                    district=None,
                    state="maharashtra",
                    raw_payload={"source": "hardcoded", "version": "2026-04"},
                ),

                # Maharashtra-specific: Crop Insurance Support
                SchemeRecord(
                    scheme_name="Maharashtra Agricultural Contingency Support",
                    scheme_slug="mah_contingency",
                    ministry="Maharashtra Government",
                    description="Emergency support during crop failure (drought, flood, pest)",
                    eligibility_criteria={
                        "min_age": 18,
                        "state": "maharashtra",
                        "affected_by_disaster": True,
                    },
                    commodities=["all"],
                    min_land_hectares=0,
                    max_land_hectares=None,
                    annual_benefit="₹1,000-5,000 per hectare",
                    benefit_amount=Decimal("3000"),
                    application_deadline=date(2026, 12, 31),
                    district=None,
                    state="maharashtra",
                    raw_payload={"source": "hardcoded", "version": "2026-04"},
                ),
            ]

        except Exception as e:
            logger.error(f"❌ Hardcoded schemes fetch failed: {e}")
            raise
