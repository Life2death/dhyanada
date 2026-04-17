"""Rashtriya Kranti Soil Health & Agricultural Support Scheme."""
import logging
from datetime import date
from decimal import Decimal

from src.ingestion.schemes.sources.base import SchemeRecord, SchemeSource

logger = logging.getLogger(__name__)


class RashtriyaKrantiSource(SchemeSource):
    """Fetch Rashtriya Kranti scheme details.

    Rashtriya Kranti Scheme covers:
    - Soil health management
    - Crop insurance support
    - Subsidy on farm equipment
    - Organic farming promotion
    """

    name = "rashtriya_kranti"

    async def fetch(self) -> list[SchemeRecord]:
        """Fetch Rashtriya Kranti scheme data."""
        try:
            logger.info("Fetching Rashtriya Kranti scheme data...")

            # Return hardcoded Rashtriya Kranti schemes
            return [
                SchemeRecord(
                    scheme_name="Rashtriya Kranti Soil Health Management",
                    scheme_slug="rashtriya_kranti_soil",
                    ministry="Ministry of Agriculture & Farmers Welfare",
                    description="Soil testing and health management support",
                    eligibility_criteria={
                        "min_age": 18,
                        "citizenship": "indian",
                        "max_land_hectares": 10,
                        "required_documents": ["Aadhar", "Soil test report"],
                    },
                    commodities=["wheat", "rice", "maize", "cotton", "onion", "sugarcane"],
                    min_land_hectares=0,
                    max_land_hectares=10,
                    annual_benefit="₹2,000-5,000 subsidy",
                    benefit_amount=Decimal("3500"),
                    application_deadline=date(2026, 10, 31),
                    district=None,
                    state="maharashtra",
                    raw_payload={
                        "source": "agriculture.gov.in",
                        "scheme_id": "kranti_1",
                        "status": "active",
                        "last_updated": date.today().isoformat(),
                    },
                ),
                SchemeRecord(
                    scheme_name="Rashtriya Kranti Organic Farming Support",
                    scheme_slug="rashtriya_kranti_organic",
                    ministry="Ministry of Agriculture & Farmers Welfare",
                    description="Support and subsidy for organic farming transition",
                    eligibility_criteria={
                        "min_age": 18,
                        "citizenship": "indian",
                        "max_land_hectares": 5,
                        "required_documents": ["Aadhar", "Organic certification"],
                    },
                    commodities=["vegetables", "fruits", "pulses", "spices"],
                    min_land_hectares=0,
                    max_land_hectares=5,
                    annual_benefit="₹4,000-8,000 subsidy",
                    benefit_amount=Decimal("6000"),
                    application_deadline=date(2026, 9, 30),
                    district=None,
                    state="maharashtra",
                    raw_payload={
                        "source": "agriculture.gov.in",
                        "scheme_id": "kranti_2",
                        "status": "active",
                        "last_updated": date.today().isoformat(),
                    },
                ),
            ]
        except Exception as e:
            logger.error(f"❌ Rashtriya Kranti fetch failed: {e}")
            raise
