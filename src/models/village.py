from sqlalchemy import String, Float, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class Village(Base):
    __tablename__ = "villages"

    id: Mapped[int] = mapped_column(primary_key=True)
    village_name: Mapped[str] = mapped_column(String(100), nullable=False)
    taluka_name: Mapped[str] = mapped_column(String(100), nullable=False)
    district_name: Mapped[str] = mapped_column(String(100), nullable=False)
    district_slug: Mapped[str] = mapped_column(String(50), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "village_name", "taluka_name", "district_slug",
            name="uq_village_taluka_district",
        ),
        Index("idx_villages_district", "district_slug"),
        Index("idx_villages_taluka", "taluka_name", "district_slug"),
        Index("idx_villages_name", "village_name"),
    )
