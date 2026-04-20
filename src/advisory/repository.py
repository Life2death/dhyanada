"""Advisory repository — queries for rules + generated advisories (Phase 4 Step 3)."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.advisory.models import AdvisoryData, RuleData
from src.models.advisory import Advisory
from src.models.advisory_rule import AdvisoryRule


class AdvisoryRepository:
    """Queries for rule management (admin) and farmer advisory lookups (dashboard)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Rules (admin CRUD)
    # ------------------------------------------------------------------

    async def list_rules(
        self,
        advisory_type: Optional[str] = None,
        crop: Optional[str] = None,
        only_active: bool = False,
    ) -> list[AdvisoryRule]:
        stmt = select(AdvisoryRule)
        if advisory_type:
            stmt = stmt.where(AdvisoryRule.advisory_type == advisory_type)
        if crop:
            stmt = stmt.where(AdvisoryRule.crop == crop)
        if only_active:
            stmt = stmt.where(AdvisoryRule.active.is_(True))
        stmt = stmt.order_by(AdvisoryRule.advisory_type, AdvisoryRule.crop, AdvisoryRule.rule_key)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_rule(self, rule_id: int) -> Optional[AdvisoryRule]:
        stmt = select(AdvisoryRule).where(AdvisoryRule.id == rule_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_rule_by_key(self, rule_key: str) -> Optional[AdvisoryRule]:
        stmt = select(AdvisoryRule).where(AdvisoryRule.rule_key == rule_key)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_rule(self, data: RuleData) -> AdvisoryRule:
        """Insert or update a rule keyed by rule_key. Used by seed loader + admin edits."""
        existing = await self.get_rule_by_key(data.rule_key)
        if existing:
            for field, value in data.model_dump(exclude={"id"}).items():
                setattr(existing, field, value)
            rule = existing
        else:
            rule = AdvisoryRule(**data.model_dump(exclude={"id"}))
            self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def create_rule(self, data: RuleData) -> AdvisoryRule:
        rule = AdvisoryRule(**data.model_dump(exclude={"id"}))
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def update_rule(self, rule_id: int, data: RuleData) -> Optional[AdvisoryRule]:
        rule = await self.get_rule(rule_id)
        if not rule:
            return None
        for field, value in data.model_dump(exclude={"id"}, exclude_unset=True).items():
            setattr(rule, field, value)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def soft_delete_rule(self, rule_id: int) -> bool:
        rule = await self.get_rule(rule_id)
        if not rule:
            return False
        rule.active = False
        await self.db.commit()
        return True

    async def hard_delete_rule(self, rule_id: int) -> bool:
        stmt = delete(AdvisoryRule).where(AdvisoryRule.id == rule_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    # ------------------------------------------------------------------
    # Advisories (farmer dashboard + admin QA)
    # ------------------------------------------------------------------

    async def get_recent_advisories(
        self, farmer_id: int, days: int = 7, include_dismissed: bool = False
    ) -> list[Advisory]:
        cutoff = date.today() - timedelta(days=days)
        stmt = (
            select(Advisory)
            .where(
                and_(
                    Advisory.farmer_id == farmer_id,
                    Advisory.advisory_date >= cutoff,
                )
            )
            .order_by(Advisory.advisory_date.desc(), Advisory.risk_level.desc())
        )
        if not include_dismissed:
            stmt = stmt.where(Advisory.dismissed_at.is_(None))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_recent_across_farmers(self, limit: int = 200) -> list[Advisory]:
        """Admin QA: recent generated advisories across all farmers."""
        stmt = select(Advisory).order_by(Advisory.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def dismiss(self, advisory_id: int, farmer_id: int) -> bool:
        stmt = (
            update(Advisory)
            .where(and_(Advisory.id == advisory_id, Advisory.farmer_id == farmer_id))
            .values(dismissed_at=datetime.utcnow())
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def mark_whatsapp_delivered(self, advisory_id: int, message_id: str) -> None:
        adv = (
            await self.db.execute(select(Advisory).where(Advisory.id == advisory_id))
        ).scalar_one_or_none()
        if not adv:
            return
        delivered = dict(adv.delivered_via or {})
        delivered["whatsapp"] = message_id
        adv.delivered_via = delivered
        await self.db.commit()

    # ------------------------------------------------------------------
    # Converters
    # ------------------------------------------------------------------

    @staticmethod
    def to_advisory_data(adv: Advisory, rule: Optional[AdvisoryRule] = None) -> AdvisoryData:
        return AdvisoryData(
            id=adv.id,
            rule_id=adv.rule_id,
            rule_key=rule.rule_key if rule else None,
            advisory_type=rule.advisory_type if rule else None,
            crop=adv.crop,
            advisory_date=adv.advisory_date,
            valid_until=adv.valid_until,
            risk_level=adv.risk_level,
            title=adv.title,
            message=adv.message,
            action_hint=adv.action_hint,
            source_citation=adv.source_citation,
            delivered_via=adv.delivered_via,
            dismissed_at=adv.dismissed_at,
            created_at=adv.created_at,
        )
