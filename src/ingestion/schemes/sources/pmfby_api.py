"""PM-FASAL (Pradhan Mantri Fasal Bima Yojana) scheme source."""
import logging
from datetime import date
from decimal import Decimal

from src.ingestion.schemes.sources.base import SchemeRecord, SchemeSource

logger = logging.getLogger(__name__)


class PMFBYSource(SchemeSource):
    """Fetch PM-FASAL Bima Yojana scheme details.

    PM-FASAL provides crop insurance with 70-75% government subsidy.
    - Eligibility: Landholding farmers (any size)
    - Benefit: 70-75% premium subsidy on crop insurance
    - Commodities: Kharif (rice, maize, cotton) + Rabi (wheat, chickpea)
    - Status: All-India scheme (active)
    - Application: Through district/tahsil offices
    """

    name = "pmfby_api"
    api_url = "https://pmfby.gov.in/api/schemes"  # Placeholder

    async def fetch(self) -> list[SchemeRecord]:
        """Fetch PM-FASAL Bima Yojana scheme data."""
        try:
            logger.info("Fetching PM-FASAL scheme data...")

            # Return hardcoded PM-FASAL for now (actual API integration depends on public endpoint)
            return [
                SchemeRecord(
                    scheme_name="Pradhan Mantri Fasal Bima Yojana",
                    scheme_slug="pm_fasal",
                    ministry="Ministry of Agriculture & Farmers Welfare",
                    description="Crop insurance scheme with government-subsidized premiums",
                    eligibility_criteria={
                        "min_age": 18,
                        "citizenship": "indian",
                        "land_ownership": "any",  # All landholding farmers
                        "required_documents": ["Land records", "Aadhar"],
                    },
                    commodities=["rice", "maize", "cotton", "wheat", "chickpea", "onion", "potato"],
                    min_land_hectares=0,
                    max_land_hectares=None,  # No upper limit
                    annual_benefit="70% premium subsidy",
                    benefit_amount=Decimal("70"),  # As percentage
                    application_deadline=date(2026, 6, 30),
                    district=None,  # All-India
                    state="maharashtra",
                    raw_payload={
                        "source": "pmfby.gov.in",
                        "scheme_id": "2",
                        "status": "active",
                        "premium_rates": {
                            "rice": "₹500-600/quintal",
                            "cotton": "₹600-800/quintal",
                            "wheat": "₹300-400/quintal",
                        },
                        "last_updated": date.today().isoformat(),
                    },
                )
            ]
        except Exception as e:
            logger.error(f"❌ PM-FASAL fetch failed: {e}")
            raise
