#!/usr/bin/env python3
"""
Initialize SQLite database with essential tables for WhatsApp testing.
This skips PostgreSQL-specific types (JSONB) and creates a minimal schema.
"""

import os
import sqlite3

def init_db_simple():
    """Create essential tables in SQLite"""
    db_path = "./kisan_ai.db"

    print(f"Initializing SQLite database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Create farmers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS farmers (
                id TEXT PRIMARY KEY,
                phone TEXT UNIQUE NOT NULL,
                name TEXT,
                age INTEGER,
                district TEXT,
                land_hectares REAL,
                preferred_language TEXT DEFAULT 'mr',
                plan_tier TEXT DEFAULT 'free',
                subscription_status TEXT DEFAULT 'inactive',
                onboarding_state TEXT,
                queries_today INTEGER DEFAULT 0,
                queries_reset_at TIMESTAMP,
                consent_given_at TIMESTAMP,
                consent_version TEXT,
                erasure_requested_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP
            )
        """)

        # Create crop_of_interest table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS crop_of_interest (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farmer_id TEXT NOT NULL,
                crop TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (farmer_id) REFERENCES farmers(id) ON DELETE CASCADE,
                UNIQUE(farmer_id, crop)
            )
        """)

        # Create conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                farmer_id TEXT,
                message_type TEXT,
                raw_text TEXT,
                intent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (farmer_id) REFERENCES farmers(id) ON DELETE CASCADE
            )
        """)

        # Create price_alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_alerts (
                id TEXT PRIMARY KEY,
                farmer_id TEXT NOT NULL,
                commodity TEXT NOT NULL,
                district TEXT,
                condition TEXT DEFAULT '>',
                threshold REAL NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                triggered_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (farmer_id) REFERENCES farmers(id) ON DELETE CASCADE,
                UNIQUE(farmer_id, commodity, district, condition, threshold)
            )
        """)

        # Create msp_alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS msp_alerts (
                id TEXT PRIMARY KEY,
                farmer_id TEXT NOT NULL,
                commodity TEXT NOT NULL,
                alert_threshold REAL NOT NULL,
                triggered_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (farmer_id) REFERENCES farmers(id) ON DELETE CASCADE
            )
        """)

        # Create mandi_prices table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mandi_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                crop TEXT NOT NULL,
                variety TEXT,
                mandi TEXT NOT NULL,
                apmc TEXT,
                district TEXT NOT NULL,
                modal_price REAL,
                min_price REAL,
                max_price REAL,
                msp REAL,
                arrival_quantity_qtl REAL,
                source TEXT DEFAULT 'agmarknet' NOT NULL,
                raw_payload TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_stale BOOLEAN DEFAULT 0,
                UNIQUE(date, apmc, crop, variety, source)
            )
        """)

        # Create weather_observations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE,
                district TEXT,
                temp_high REAL,
                temp_low REAL,
                humidity INTEGER,
                rainfall REAL,
                wind_speed REAL,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create consent_events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS consent_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                farmer_id TEXT,
                event_type TEXT NOT NULL,
                consent_version TEXT,
                message_id TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (farmer_id) REFERENCES farmers(id) ON DELETE CASCADE
            )
        """)

        # Insert sample mandi price data for testing
        from datetime import date
        today = str(date.today())

        sample_prices = [
            (today, 'onion', None, 'Nashik', 'nashik', 'nashik', 4500, 4200, 4800, None, None, 'agmarknet', None, None, 0),
            (today, 'onion', None, 'Pune', 'pune', 'pune', 4700, 4400, 5000, None, None, 'agmarknet', None, None, 0),
            (today, 'wheat', None, 'Nashik', 'nashik', 'nashik', 2500, 2400, 2600, 2550, None, 'agmarknet', None, None, 0),
        ]

        cursor.executemany("""
            INSERT OR IGNORE INTO mandi_prices
            (date, crop, variety, mandi, apmc, district, modal_price, min_price, max_price, msp, arrival_quantity_qtl, source, raw_payload, fetched_at, is_stale)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_prices)

        conn.commit()
        print("✅ Database initialized successfully!")
        print(f"   Location: {db_path}")
        print("   Tables created: farmers, crop_of_interest, conversations, mandi_prices, price_alerts, msp_alerts, weather_observations, consent_events")
        print("   Sample prices added: onion (₹4500), wheat (₹2500)")
        print("\n📌 Ready for WhatsApp testing!")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    init_db_simple()
