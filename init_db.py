#!/usr/bin/env python3
"""
Initialize SQLite database with required tables.
Run this once: python init_db.py
"""

import os
from sqlalchemy import create_engine

def init_db():
    """Create all tables in SQLite database"""
    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./dhanyada.db")
    # Convert async URL to sync URL for initialization
    db_url_sync = db_url.replace("+aiosqlite", "").replace("sqlite+", "sqlite:///")

    print(f"Initializing database: {db_url_sync}")

    try:
        # Import all models - this registers them with Base
        # Just importing is enough; SQLAlchemy tracks them automatically
        import src.models.farmer
        import src.models.conversation
        import src.models.price
        import src.models.schemes
        import src.models.weather
        import src.models.consent
        import src.models.broadcast

        # Create engine
        engine = create_engine(db_url_sync, echo=False)

        # Import base to get all registered models
        from src.models.base import Base

        # Create all tables
        Base.metadata.create_all(engine)

        print("✅ Database initialized successfully!")
        print(f"   Database location: {db_url_sync}")
        print(f"   Tables created: farmers, crop_of_interest, conversations, mandi_prices, price_alerts, msp_alerts, government_schemes, weather_observations, consent_events, broadcasts")

        engine.dispose()

    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    init_db()
