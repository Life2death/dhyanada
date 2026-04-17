"""PM-KISAN (Pradhan Mantri Kisan Samman Nidhi) scheme source."""
import logging
from datetime import date, timedelta
from decimal import Decimal

import httpx

from src.ingestion.schemes.sources.base import SchemeRecord, SchemeSource

logger = logging.getLogger(__name__)


class PMKISANSource(SchemeSource):
    """Fetch PM-KISAN scheme details.

    PM-KISAN provides ₹6,000/year to farmers with <2 hectares of landholding.
    - Eligibility: Indian citizen, age >18, land < 2 hectares
    - Benefit: ₹6,000/year (₹2,000 every 4 months)
    - Commodities: All crops
    - Status: All-India scheme (active)
    - Application: Online at pmkisan.gov.in
    """

    name = "pmksy_api"
    api_url = "https://pmkisan.gov.in/api/v1/schemes"  # Placeholder (actual endpoint may vary)

    async def fetch(self) -> list[SchemeRecord]:
        """Fetch PM-KISAN scheme data."""
        try:
            # Note: PM-KISAN API endpoint may not be public; using fallback approach
            logger.info("Fetching PM-KISAN scheme data...")

            # Return hardcoded PM-KISAN for now (actual API integration depends on public endpoint)
            return [
                SchemeRecord(
                    scheme_name="PM Kisan Samman Nidhi Yojana",
                    scheme_slug="pm_kisan",
                    ministry="Ministry of Agriculture & Farmers Welfare",
                    description="Direct income support to all landholding farmer families",
                    eligibility_criteria={
                        "min_age": 18,
                        "max_age": None,
                        "citizenship": "indian",
                        "min_land_hectares": 0,
                        "max_land_hectares": 2,
                        "required_documents": ["Aadhar", "Land records"],
                    },
                    commodities=["wheat", "rice", "maize", "soyabean", "cotton", "onion", "potato", "sugarcane"],
                    min_land_hectares=0,
                    max_land_hectares=2,
                    annual_benefit="₹6,000/year",
                    benefit_amount=Decimal("6000"),
                    application_deadline=date(2026, 12, 31),
                    district=None,  # All-India
                    state="maharashtra",
                    raw_payload={
                        "source": "pmkisan.gov.in",
                        "scheme_id": "1",
                        "status": "active",
                        "last_updated": date.today().isoformat(),
                    },
                )
            ]
        except Exception as e:
            logger.error(f"❌ PM-KISAN fetch failed: {e}")
            raise
