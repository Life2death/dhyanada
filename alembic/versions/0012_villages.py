"""Create villages table with Ahilyanagar district seed data.

Revision ID: 0012
Revises: 0011
Create Date: 2026-04-27
"""
from alembic import op
import sqlalchemy as sa

revision = '0012'
down_revision = '0011'
branch_labels = None
depends_on = None

# Seed data: (village_name, taluka_name, district_name, district_slug, lat, lon)
_AHILYANAGAR_VILLAGES = [
    # --- Ahmednagar Taluka ---
    ("Ahmednagar", "Ahmednagar", "Ahilyanagar", "ahilyanagar", 19.0948, 74.7480),
    ("Savedi", "Ahmednagar", "Ahilyanagar", "ahilyanagar", 19.0830, 74.7510),
    ("Bhingar", "Ahmednagar", "Ahilyanagar", "ahilyanagar", 19.1033, 74.7817),
    ("Visapur", "Ahmednagar", "Ahilyanagar", "ahilyanagar", 19.0700, 74.7500),
    ("Mahadeopuri", "Ahmednagar", "Ahilyanagar", "ahilyanagar", 19.0900, 74.7350),
    ("Pimplas", "Ahmednagar", "Ahilyanagar", "ahilyanagar", 19.1200, 74.8000),
    ("Nalegaon", "Ahmednagar", "Ahilyanagar", "ahilyanagar", 19.0600, 74.7200),

    # --- Akola Taluka (Ahmednagar district) ---
    ("Akola", "Akola", "Ahilyanagar", "ahilyanagar", 18.9667, 74.9833),
    ("Bhairi", "Akola", "Ahilyanagar", "ahilyanagar", 18.9833, 74.9500),
    ("Rajur", "Akola", "Ahilyanagar", "ahilyanagar", 19.0000, 74.9833),
    ("Ghargaon", "Akola", "Ahilyanagar", "ahilyanagar", 18.9333, 74.9167),
    ("Bhandardara", "Akola", "Ahilyanagar", "ahilyanagar", 19.5250, 73.7583),
    ("Kotul", "Akola", "Ahilyanagar", "ahilyanagar", 18.9500, 74.9500),

    # --- Jamkhed Taluka ---
    ("Jamkhed", "Jamkhed", "Ahilyanagar", "ahilyanagar", 18.7167, 75.3167),
    ("Miri", "Jamkhed", "Ahilyanagar", "ahilyanagar", 18.6833, 75.2833),
    ("Kondi", "Jamkhed", "Ahilyanagar", "ahilyanagar", 18.7500, 75.3000),
    ("Kanhur", "Jamkhed", "Ahilyanagar", "ahilyanagar", 18.7000, 75.2667),
    ("Takali Dhokeshwar", "Jamkhed", "Ahilyanagar", "ahilyanagar", 18.6667, 75.3167),
    ("Nandur", "Jamkhed", "Ahilyanagar", "ahilyanagar", 18.7333, 75.2500),

    # --- Karjat Taluka (Ahmednagar district) ---
    ("Karjat", "Karjat", "Ahilyanagar", "ahilyanagar", 18.9167, 75.1167),
    ("Tak", "Karjat", "Ahilyanagar", "ahilyanagar", 18.9500, 75.0833),
    ("Shingnapur", "Karjat", "Ahilyanagar", "ahilyanagar", 18.9000, 75.1500),
    ("Bori", "Karjat", "Ahilyanagar", "ahilyanagar", 18.9667, 75.1500),
    ("Kedgaon", "Karjat", "Ahilyanagar", "ahilyanagar", 18.8833, 75.0667),

    # --- Kopargaon Taluka ---
    ("Kopargaon", "Kopargaon", "Ahilyanagar", "ahilyanagar", 19.8833, 74.4833),
    ("Savargaon", "Kopargaon", "Ahilyanagar", "ahilyanagar", 19.8500, 74.4500),
    ("Chandori", "Kopargaon", "Ahilyanagar", "ahilyanagar", 19.8167, 74.4667),
    ("Deodaithan", "Kopargaon", "Ahilyanagar", "ahilyanagar", 19.8833, 74.5167),
    ("Ghoti Budruk", "Kopargaon", "Ahilyanagar", "ahilyanagar", 19.7167, 74.4333),
    ("Pimpri Kopargaon", "Kopargaon", "Ahilyanagar", "ahilyanagar", 19.8667, 74.5000),

    # --- Nevasa Taluka ---
    ("Nevasa", "Nevasa", "Ahilyanagar", "ahilyanagar", 19.5333, 74.9667),
    ("Puntamba", "Nevasa", "Ahilyanagar", "ahilyanagar", 19.4833, 74.8333),
    ("Chitali", "Nevasa", "Ahilyanagar", "ahilyanagar", 19.5000, 74.9500),
    ("Ghogargaon", "Nevasa", "Ahilyanagar", "ahilyanagar", 19.5667, 74.9833),
    ("Kurundvad", "Nevasa", "Ahilyanagar", "ahilyanagar", 19.5167, 75.0167),
    ("Takali Haji", "Nevasa", "Ahilyanagar", "ahilyanagar", 19.5500, 74.9333),

    # --- Parner Taluka ---
    ("Parner", "Parner", "Ahilyanagar", "ahilyanagar", 19.0000, 74.4333),
    ("Malwadi", "Parner", "Ahilyanagar", "ahilyanagar", 19.0167, 74.4000),
    ("Belatgaon", "Parner", "Ahilyanagar", "ahilyanagar", 18.9833, 74.4500),
    ("Pimpri Sandas", "Parner", "Ahilyanagar", "ahilyanagar", 19.0500, 74.4667),
    ("Wadgaon Darya", "Parner", "Ahilyanagar", "ahilyanagar", 19.0333, 74.3833),
    ("Sonai", "Parner", "Ahilyanagar", "ahilyanagar", 19.0667, 74.4500),

    # --- Pathardi Taluka ---
    ("Pathardi", "Pathardi", "Ahilyanagar", "ahilyanagar", 19.1833, 75.1833),
    ("Deulgaon Raja", "Pathardi", "Ahilyanagar", "ahilyanagar", 19.1500, 75.1500),
    ("Ghulewadi", "Pathardi", "Ahilyanagar", "ahilyanagar", 19.2167, 75.2000),
    ("Khed Pathardi", "Pathardi", "Ahilyanagar", "ahilyanagar", 19.1667, 75.2333),
    ("Kuran", "Pathardi", "Ahilyanagar", "ahilyanagar", 19.2000, 75.1667),

    # --- Rahata Taluka ---
    ("Rahata", "Rahata", "Ahilyanagar", "ahilyanagar", 19.7167, 74.4833),
    ("Shirdi", "Rahata", "Ahilyanagar", "ahilyanagar", 19.7650, 74.4764),
    ("Saikheda", "Rahata", "Ahilyanagar", "ahilyanagar", 19.7333, 74.5000),
    ("Eklahare", "Rahata", "Ahilyanagar", "ahilyanagar", 19.6667, 74.5167),
    ("Babhaleshwar", "Rahata", "Ahilyanagar", "ahilyanagar", 19.7167, 74.4333),
    ("Gonde", "Rahata", "Ahilyanagar", "ahilyanagar", 19.7500, 74.4500),

    # --- Rahuri Taluka ---
    ("Rahuri", "Rahuri", "Ahilyanagar", "ahilyanagar", 19.3833, 74.6500),
    ("Dahigaon", "Rahuri", "Ahilyanagar", "ahilyanagar", 19.4167, 74.6000),
    ("Manewadi", "Rahuri", "Ahilyanagar", "ahilyanagar", 19.3500, 74.6667),
    ("Gondegaon", "Rahuri", "Ahilyanagar", "ahilyanagar", 19.4333, 74.6833),
    ("Wakadi", "Rahuri", "Ahilyanagar", "ahilyanagar", 19.3667, 74.6333),
    ("Tisgaon", "Rahuri", "Ahilyanagar", "ahilyanagar", 19.4000, 74.7000),

    # --- Sangamner Taluka ---
    ("Sangamner", "Sangamner", "Ahilyanagar", "ahilyanagar", 19.5667, 74.2000),
    ("Nimgaon Jali", "Sangamner", "Ahilyanagar", "ahilyanagar", 19.5833, 74.1833),
    ("Dehane", "Sangamner", "Ahilyanagar", "ahilyanagar", 19.6167, 74.2500),
    ("Shelar", "Sangamner", "Ahilyanagar", "ahilyanagar", 19.5333, 74.2333),
    ("Munjwadi", "Sangamner", "Ahilyanagar", "ahilyanagar", 19.5833, 74.2667),
    ("Ashti", "Sangamner", "Ahilyanagar", "ahilyanagar", 19.5333, 73.9167),
    ("Ankush Nagar", "Sangamner", "Ahilyanagar", "ahilyanagar", 19.5500, 74.1667),

    # --- Shevgaon Taluka ---
    ("Shevgaon", "Shevgaon", "Ahilyanagar", "ahilyanagar", 19.3167, 75.1833),
    ("Devapur", "Shevgaon", "Ahilyanagar", "ahilyanagar", 19.3500, 75.2167),
    ("Bodhegaon", "Shevgaon", "Ahilyanagar", "ahilyanagar", 19.3000, 75.2000),
    ("Pimpri Shevgaon", "Shevgaon", "Ahilyanagar", "ahilyanagar", 19.2833, 75.1500),
    ("Khandgaon", "Shevgaon", "Ahilyanagar", "ahilyanagar", 19.3333, 75.1500),

    # --- Shrigonda Taluka ---
    ("Shrigonda", "Shrigonda", "Ahilyanagar", "ahilyanagar", 18.6167, 74.7000),
    ("Bhandgaon", "Shrigonda", "Ahilyanagar", "ahilyanagar", 18.5833, 74.7500),
    ("Bhelke", "Shrigonda", "Ahilyanagar", "ahilyanagar", 18.6333, 74.6833),
    ("Khandala Shrigonda", "Shrigonda", "Ahilyanagar", "ahilyanagar", 18.5667, 74.6833),
    ("Shindodi", "Shrigonda", "Ahilyanagar", "ahilyanagar", 18.6500, 74.6667),
    ("Mhalungi", "Shrigonda", "Ahilyanagar", "ahilyanagar", 18.5333, 74.7167),

    # --- Shrirampur Taluka ---
    ("Shrirampur", "Shrirampur", "Ahilyanagar", "ahilyanagar", 19.6167, 74.6500),
    ("Belapur", "Shrirampur", "Ahilyanagar", "ahilyanagar", 19.5833, 74.7000),
    ("Nimgaon Doulatabad", "Shrirampur", "Ahilyanagar", "ahilyanagar", 19.6333, 74.7167),
    ("Ghulewadi Shrirampur", "Shrirampur", "Ahilyanagar", "ahilyanagar", 19.6500, 74.6167),
    ("Loni Kalbhor", "Shrirampur", "Ahilyanagar", "ahilyanagar", 19.6000, 74.6333),
    ("Babhulgaon", "Shrirampur", "Ahilyanagar", "ahilyanagar", 19.6667, 74.6667),
]


def upgrade() -> None:
    op.create_table(
        'villages',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('village_name', sa.String(100), nullable=False),
        sa.Column('taluka_name', sa.String(100), nullable=False),
        sa.Column('district_name', sa.String(100), nullable=False),
        sa.Column('district_slug', sa.String(50), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.UniqueConstraint(
            'village_name', 'taluka_name', 'district_slug',
            name='uq_village_taluka_district',
        ),
    )
    op.create_index('idx_villages_district', 'villages', ['district_slug'])
    op.create_index('idx_villages_taluka', 'villages', ['taluka_name', 'district_slug'])
    op.create_index('idx_villages_name', 'villages', ['village_name'])

    # Seed Ahilyanagar district villages
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "INSERT INTO villages (village_name, taluka_name, district_name, district_slug, latitude, longitude) "
            "VALUES (:vn, :tn, :dn, :ds, :lat, :lon)"
        ),
        [
            {"vn": v, "tn": t, "dn": d, "ds": ds, "lat": lat, "lon": lon}
            for v, t, d, ds, lat, lon in _AHILYANAGAR_VILLAGES
        ],
    )


def downgrade() -> None:
    op.drop_index('idx_villages_name', table_name='villages')
    op.drop_index('idx_villages_taluka', table_name='villages')
    op.drop_index('idx_villages_district', table_name='villages')
    op.drop_table('villages')
