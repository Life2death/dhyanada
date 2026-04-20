"""Admin routes for advisory-rule CRUD + advisory QA (Phase 4 Step 3).

Mounted at /admin/advisory/* in src/main.py. Reuses the admin JWT middleware
pattern from src/admin/routes.py.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import jwt

from src.advisory.models import AdvisoryGenerationResult, AdvisoryData, RuleData
from src.advisory.repository import AdvisoryRepository
from src.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/advisory", tags=["admin-advisory"])

_engine = None
_factory = None


async def get_db() -> AsyncSession:
    global _engine, _factory
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False)
        _factory = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    async with _factory() as session:
        yield session


async def require_admin(request: Request) -> dict:
    """Reuse admin JWT validation (same format as src/admin/routes.py)."""
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization")
    token = auth.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        if payload.get("type") != "admin":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------------------------------------------------------------------------
# Rule CRUD (JSON)
# ---------------------------------------------------------------------------


def _rule_to_data(rule) -> RuleData:
    return RuleData(
        id=rule.id,
        rule_key=rule.rule_key,
        advisory_type=rule.advisory_type,
        crop=rule.crop,
        eligible_districts=rule.eligible_districts,
        min_temp_c=float(rule.min_temp_c) if rule.min_temp_c is not None else None,
        max_temp_c=float(rule.max_temp_c) if rule.max_temp_c is not None else None,
        min_humidity_pct=float(rule.min_humidity_pct) if rule.min_humidity_pct is not None else None,
        max_humidity_pct=float(rule.max_humidity_pct) if rule.max_humidity_pct is not None else None,
        min_rainfall_mm=float(rule.min_rainfall_mm) if rule.min_rainfall_mm is not None else None,
        max_rainfall_mm=float(rule.max_rainfall_mm) if rule.max_rainfall_mm is not None else None,
        consecutive_days=rule.consecutive_days,
        risk_level=rule.risk_level,
        title_en=rule.title_en,
        message_en=rule.message_en,
        message_mr=rule.message_mr,
        action_hint=rule.action_hint,
        source_citation=rule.source_citation,
        active=rule.active,
    )


@router.get("/api/rules", response_model=list[RuleData])
async def list_rules(
    advisory_type: Optional[str] = None,
    crop: Optional[str] = None,
    only_active: bool = False,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    repo = AdvisoryRepository(db)
    rules = await repo.list_rules(advisory_type=advisory_type, crop=crop, only_active=only_active)
    return [_rule_to_data(r) for r in rules]


@router.get("/api/rules/{rule_id}", response_model=RuleData)
async def get_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    repo = AdvisoryRepository(db)
    rule = await repo.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return _rule_to_data(rule)


@router.post("/api/rules", response_model=RuleData)
async def create_rule(
    data: RuleData,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    repo = AdvisoryRepository(db)
    existing = await repo.get_rule_by_key(data.rule_key)
    if existing:
        raise HTTPException(status_code=409, detail=f"rule_key '{data.rule_key}' already exists")
    rule = await repo.create_rule(data)
    return _rule_to_data(rule)


@router.put("/api/rules/{rule_id}", response_model=RuleData)
async def update_rule(
    rule_id: int,
    data: RuleData,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    repo = AdvisoryRepository(db)
    rule = await repo.update_rule(rule_id, data)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return _rule_to_data(rule)


@router.delete("/api/rules/{rule_id}")
async def delete_rule(
    rule_id: int,
    hard: bool = False,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    repo = AdvisoryRepository(db)
    if hard:
        ok = await repo.hard_delete_rule(rule_id)
    else:
        ok = await repo.soft_delete_rule(rule_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"success": True, "mode": "hard" if hard else "soft"}


# ---------------------------------------------------------------------------
# Recent advisories QA
# ---------------------------------------------------------------------------


@router.get("/api/recent")
async def list_recent_advisories(
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    repo = AdvisoryRepository(db)
    advs = await repo.list_recent_across_farmers(limit=limit)
    return [
        {
            "id": a.id,
            "farmer_id": a.farmer_id,
            "rule_id": a.rule_id,
            "crop": a.crop,
            "advisory_date": a.advisory_date.isoformat(),
            "risk_level": a.risk_level,
            "title": a.title,
            "message": a.message,
            "action_hint": a.action_hint,
            "delivered_via": a.delivered_via,
            "dismissed_at": a.dismissed_at.isoformat() if a.dismissed_at else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in advs
    ]


@router.post("/api/run-now")
async def run_engine_now(
    farmer_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
):
    """Trigger the advisory engine immediately (admin-only, for testing).

    If farmer_id is given, runs for just that farmer; else for all.
    """
    from src.advisory.engine import generate_for_all_farmers, generate_for_farmer

    if farmer_id is not None:
        created = await generate_for_farmer(db, farmer_id)
        return {"farmer_id": farmer_id, "created": len(created)}
    counts = await generate_for_all_farmers(db)
    return {"farmers": len(counts), "total_created": sum(counts.values()), "by_farmer": counts}


# ---------------------------------------------------------------------------
# Minimal HTML rule editor
# ---------------------------------------------------------------------------


RULES_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>Advisory Rules - Kisan AI Admin</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
  body { padding: 20px; font-family: system-ui; }
  .risk-high { color: #dc3545; font-weight: 600; }
  .risk-medium { color: #fd7e14; font-weight: 600; }
  .risk-low { color: #28a745; font-weight: 600; }
  table { font-size: 0.9rem; }
  .inactive { opacity: 0.5; }
</style>
</head>
<body>
<div class="container-fluid">
<h2>Advisory Rules</h2>
<p class="text-muted">Edit weather-threshold rules used by the advisory engine. Changes take effect on the next nightly run.</p>

<div class="mb-3">
  <button class="btn btn-primary btn-sm" onclick="runEngineNow()">Run engine now</button>
  <a href="/admin/advisory/recent" class="btn btn-outline-secondary btn-sm">View recent advisories</a>
</div>

<div id="rules"></div>

<script>
const token = localStorage.getItem('adminToken');
if (!token) { window.location.href = '/admin/login'; }

async function loadRules() {
  const resp = await fetch('/admin/advisory/api/rules', { headers: { 'Authorization': 'Bearer ' + token } });
  if (!resp.ok) { alert('Failed to load rules: ' + resp.status); return; }
  const rules = await resp.json();
  const byType = {};
  rules.forEach(r => { (byType[r.advisory_type] = byType[r.advisory_type] || []).push(r); });

  let html = '';
  for (const type of Object.keys(byType).sort()) {
    html += `<h4 class="mt-4">${type.toUpperCase()} (${byType[type].length})</h4>`;
    html += `<table class="table table-sm table-striped"><thead><tr>
      <th>Key</th><th>Crop</th><th>Thresholds</th><th>Risk</th><th>Title</th><th>Active</th><th></th>
    </tr></thead><tbody>`;
    for (const r of byType[type]) {
      const thresh = [
        r.min_temp_c !== null ? `T≥${r.min_temp_c}` : null,
        r.max_temp_c !== null ? `T≤${r.max_temp_c}` : null,
        r.min_humidity_pct !== null ? `RH≥${r.min_humidity_pct}` : null,
        r.max_humidity_pct !== null ? `RH≤${r.max_humidity_pct}` : null,
        r.min_rainfall_mm !== null ? `Rain≥${r.min_rainfall_mm}` : null,
        r.max_rainfall_mm !== null ? `Rain≤${r.max_rainfall_mm}` : null,
        r.consecutive_days > 1 ? `${r.consecutive_days}d streak` : null,
      ].filter(Boolean).join(', ');
      html += `<tr class="${r.active ? '' : 'inactive'}">
        <td><code>${r.rule_key}</code></td>
        <td>${r.crop || '<em>any</em>'}</td>
        <td>${thresh}</td>
        <td class="risk-${r.risk_level}">${r.risk_level}</td>
        <td>${r.title_en}</td>
        <td>${r.active ? '✓' : '✗'}</td>
        <td>
          <button class="btn btn-sm btn-outline-warning" onclick="toggleRule(${r.id}, ${!r.active})">${r.active ? 'Disable' : 'Enable'}</button>
        </td>
      </tr>`;
    }
    html += '</tbody></table>';
  }
  document.getElementById('rules').innerHTML = html;
}

async function toggleRule(id, activate) {
  const resp = await fetch('/admin/advisory/api/rules/' + id, {
    headers: { 'Authorization': 'Bearer ' + token },
  });
  const rule = await resp.json();
  rule.active = activate;
  const put = await fetch('/admin/advisory/api/rules/' + id, {
    method: 'PUT',
    headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
    body: JSON.stringify(rule),
  });
  if (put.ok) loadRules(); else alert('Failed');
}

async function runEngineNow() {
  const resp = await fetch('/admin/advisory/api/run-now', {
    method: 'POST', headers: { 'Authorization': 'Bearer ' + token },
  });
  const data = await resp.json();
  alert('Engine run: ' + JSON.stringify(data));
}

loadRules();
</script>
</div>
</body>
</html>
"""


RECENT_HTML = """
<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Recent Advisories</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{padding:20px;font-family:system-ui;} .risk-high{color:#dc3545;} .risk-medium{color:#fd7e14;} .risk-low{color:#28a745;}</style>
</head><body><div class="container-fluid">
<h2>Recent Advisories (last 200)</h2>
<p><a href="/admin/advisory/rules">← Back to rules</a></p>
<div id="advs">Loading...</div>
<script>
const token = localStorage.getItem('adminToken');
if (!token) window.location.href='/admin/login';
fetch('/admin/advisory/api/recent', { headers: {'Authorization':'Bearer '+token} })
  .then(r=>r.json()).then(rows=>{
    let html='<table class="table table-sm table-striped"><thead><tr><th>Date</th><th>Farmer</th><th>Crop</th><th>Risk</th><th>Title</th><th>WhatsApp</th><th>Dismissed</th></tr></thead><tbody>';
    for (const a of rows){
      html += `<tr><td>${a.advisory_date}</td><td>${a.farmer_id}</td><td>${a.crop||'-'}</td>
        <td class="risk-${a.risk_level}">${a.risk_level}</td>
        <td>${a.title}</td>
        <td>${(a.delivered_via||{}).whatsapp ? '✓' : '—'}</td>
        <td>${a.dismissed_at ? '✓' : '—'}</td></tr>`;
    }
    html += '</tbody></table>';
    document.getElementById('advs').innerHTML = html;
  });
</script>
</div></body></html>
"""


@router.get("/rules", response_class=HTMLResponse)
async def rules_page():
    return RULES_HTML


@router.get("/recent", response_class=HTMLResponse)
async def recent_page():
    return RECENT_HTML
