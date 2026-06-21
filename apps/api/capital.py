"""
Capital layer — autonomous YouTube media company CEO agent, lifecycle management,
affiliate programs, revenue tracking, digital product opportunities, daily scheduling.

Imported by main.py:
    from capital import capital_router, register_capital_scheduler
    app.include_router(capital_router)
    register_capital_scheduler(app)
"""

import os
import json
import sys
import asyncio
from datetime import datetime, timedelta, timezone, date, time
from typing import Optional, List, Dict, Any

import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date, Text,
    JSON as SAJSON, UniqueConstraint, create_engine,
)
from sqlalchemy.orm import declarative_base, Session, sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text

# ── Engine (own NullPool — same DATABASE_URL as the rest of the app) ──────────
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/handholding")
_engine = create_engine(DATABASE_URL, poolclass=NullPool)
_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
Base = declarative_base()

# ── Env vars ──────────────────────────────────────────────────────────────────
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1")


# ── Raw-SQL helper (never call db.execute("string") directly) ─────────────────
def _x(db: Session, sql: str, *args, **kwargs):
    return db.execute(text(sql), *args, **kwargs)


# ── DB Models ─────────────────────────────────────────────────────────────────

class ChannelLifecycle(Base):
    """
    Status machine per niche:
      discovery → incubating → active → scaling → watch → paused → terminated
    """
    __tablename__ = "channel_lifecycle"
    id                          = Column(Integer, primary_key=True)
    niche_id                    = Column(Integer, unique=True, nullable=False)
    niche_name                  = Column(String, nullable=False)
    status                      = Column(String, default="discovery")
    videos_tested               = Column(Integer, default=0)
    videos_graduated            = Column(Integer, default=0)
    incubation_start            = Column(DateTime, nullable=True)
    graduation_date             = Column(DateTime, nullable=True)
    termination_date            = Column(DateTime, nullable=True)
    graduation_threshold_views  = Column(Integer, default=500)
    graduation_threshold_ctr    = Column(Float, default=3.0)
    graduation_videos_required  = Column(Integer, default=3)
    kill_days                   = Column(Integer, default=14)
    kill_views_threshold        = Column(Integer, default=100)
    notes                       = Column(Text, nullable=True)
    created_at                  = Column(DateTime, default=datetime.utcnow)
    updated_at                  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DailyAllocation(Base):
    """Tracks how compute budget is allocated per niche per day."""
    __tablename__ = "daily_allocations"
    id                  = Column(Integer, primary_key=True)
    allocation_date     = Column(Date, nullable=False)
    niche_id            = Column(Integer, nullable=False)
    niche_name          = Column(String, nullable=False)
    videos_allocated    = Column(Integer, default=0)
    videos_completed    = Column(Integer, default=0)
    scheduled_times     = Column(SAJSON, nullable=True)   # list of ISO datetime strings
    total_compute_budget= Column(Integer, default=0)      # total videos for that day
    created_at          = Column(DateTime, default=datetime.utcnow)


class AffiliateProgram(Base):
    __tablename__ = "affiliate_programs"
    id                  = Column(Integer, primary_key=True)
    niche_name          = Column(String, nullable=False)
    product_name        = Column(String, nullable=False)
    affiliate_url       = Column(String, nullable=False)
    commission_type     = Column(String, nullable=False)   # flat | percent
    commission_value    = Column(Float, default=0.0)
    priority            = Column(Integer, default=1)
    active              = Column(Boolean, default=True)
    description         = Column(Text, nullable=True)
    cta_text            = Column(String, nullable=True)
    clicks_estimated    = Column(Integer, default=0)
    revenue_estimated   = Column(Float, default=0.0)
    created_at          = Column(DateTime, default=datetime.utcnow)


class RevenueStream(Base):
    __tablename__ = "revenue_streams"
    id              = Column(Integer, primary_key=True)
    video_memory_id = Column(Integer, nullable=True)
    niche_id        = Column(Integer, nullable=False)
    # stream_type: adsense | affiliate | sponsorship | digital_product | lead_gen
    stream_type     = Column(String, nullable=False)
    amount_usd      = Column(Float, default=0.0)
    notes           = Column(Text, nullable=True)
    recorded_at     = Column(DateTime, default=datetime.utcnow)


class DigitalProductOpportunity(Base):
    __tablename__ = "digital_product_opportunities"
    id                  = Column(Integer, primary_key=True)
    niche_id            = Column(Integer, unique=True, nullable=False)
    niche_name          = Column(String, nullable=False)
    # status: flagged | in_development | launched | cancelled
    status              = Column(String, default="flagged")
    trigger_views       = Column(Integer, nullable=True)
    trigger_winner_rate = Column(Float, nullable=True)
    product_idea        = Column(Text, nullable=True)
    estimated_price     = Column(Float, default=27.0)
    flagged_at          = Column(DateTime, nullable=True)
    launched_at         = Column(DateTime, nullable=True)


class CEODecision(Base):
    __tablename__ = "ceo_decisions"
    id              = Column(Integer, primary_key=True)
    decision_date   = Column(Date, default=date.today)
    # decision_type: allocate | terminate | incubate | scale | pause | affiliate_focus | flag_product
    decision_type   = Column(String, nullable=False)
    niche_id        = Column(Integer, nullable=True)
    niche_name      = Column(String, nullable=True)
    payload         = Column(SAJSON, nullable=True)    # full action payload
    executed        = Column(Boolean, default=False)
    executed_at     = Column(DateTime, nullable=True)
    rationale       = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)


# Create capital tables (best-effort)
try:
    Base.metadata.create_all(bind=_engine)
except Exception as _e:
    print(f"[capital] create_all skipped: {_e}", flush=True)


# ── DB dependency ─────────────────────────────────────────────────────────────
def get_db():
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Affiliate seed data ───────────────────────────────────────────────────────
AFFILIATE_DATA = [
    # Finance
    ("personal_finance", "Chase Sapphire Preferred",
     "https://creditcards.chase.com/rewards-credit-cards/sapphire/preferred",
     "flat", 200.0, 1, "Get $200 bonus with Chase Sapphire"),
    ("personal_finance", "Robinhood",
     "https://join.robinhood.com",
     "flat", 20.0, 2, "Get free stock with Robinhood"),
    ("personal_finance", "Coinbase",
     "https://coinbase.com/join",
     "flat", 10.0, 3, "Get $10 in Bitcoin with Coinbase"),
    ("personal_finance", "Empower",
     "https://empower.me",
     "flat", 100.0, 1, "Track your net worth free"),
    # AI Tools
    ("ai_tools", "Notion AI",
     "https://notion.so/product/ai",
     "percent", 20.0, 1, "Try Notion AI free"),
    ("ai_tools", "Jasper AI",
     "https://jasper.ai",
     "percent", 30.0, 2, "Write 10x faster with Jasper"),
    ("ai_tools", "Copy.ai",
     "https://copy.ai",
     "percent", 45.0, 3, "Generate content in seconds"),
    # Health
    ("health", "AG1 Athletic Greens",
     "https://drinkag1.com",
     "flat", 30.0, 1, "Get a free AG1 starter kit"),
    ("health", "Thorne Supplements",
     "https://thorne.com",
     "percent", 10.0, 2, "Science-backed supplements"),
    ("health", "Eight Sleep",
     "https://eightsleep.com",
     "flat", 150.0, 1, "Sleep smarter with Eight Sleep"),
    # Business
    ("business", "Shopify",
     "https://shopify.com",
     "flat", 58.0, 1, "Start your store free"),
    ("business", "Bluehost",
     "https://bluehost.com",
     "flat", 65.0, 2, "Launch your website today"),
    ("business", "Skillshare",
     "https://skillshare.com",
     "percent", 40.0, 3, "Learn any skill for free"),
    # Real Estate
    ("real_estate", "Fundrise",
     "https://fundrise.com",
     "flat", 50.0, 1, "Invest in real estate from $10"),
    ("real_estate", "Arrived Homes",
     "https://arrived.com",
     "flat", 50.0, 2, "Own rental property shares"),
]


def _seed_affiliates(db: Session) -> None:
    """Populate affiliate_programs if empty."""
    count_row = _x(db, "SELECT COUNT(*) as c FROM affiliate_programs").fetchone()
    if count_row and int(count_row.c) > 0:
        return
    for row in AFFILIATE_DATA:
        niche_name, product_name, affiliate_url, commission_type, commission_value, priority, cta_text = row
        _x(
            db,
            """INSERT INTO affiliate_programs
               (niche_name, product_name, affiliate_url, commission_type,
                commission_value, priority, active, cta_text, created_at)
               VALUES (:nn, :pn, :au, :ct, :cv, :pr, true, :cta, :ca)""",
            {
                "nn": niche_name, "pn": product_name, "au": affiliate_url,
                "ct": commission_type, "cv": commission_value, "pr": priority,
                "cta": cta_text, "ca": datetime.utcnow(),
            },
        )
    db.commit()


# ── Helper: log a CEO decision ────────────────────────────────────────────────
def _log_decision(
    db: Session,
    decision_type: str,
    niche_id: Optional[int],
    niche_name: Optional[str],
    payload: dict,
    rationale: str,
) -> None:
    _x(
        db,
        """INSERT INTO ceo_decisions
           (decision_date, decision_type, niche_id, niche_name, payload,
            executed, executed_at, rationale, created_at)
           VALUES (:dd, :dt, :ni, :nn, :pl, true, :ea, :ra, :ca)""",
        {
            "dd": date.today(),
            "dt": decision_type,
            "ni": niche_id,
            "nn": niche_name,
            "pl": json.dumps(payload),
            "ea": datetime.utcnow(),
            "ra": rationale,
            "ca": datetime.utcnow(),
        },
    )


# ── 1. CEO Agent Executor ─────────────────────────────────────────────────────

async def run_ceo_executor(db: Session) -> dict:
    """
    Pull 7-day context, call Claude Opus 4.5 via OpenRouter, parse JSON
    decisions, execute each action, log CEODecision + CEOReport records.
    """
    if not OPENAI_API_KEY:
        return {"error": "OPENAI_API_KEY not set"}

    since = datetime.utcnow() - timedelta(days=7)
    since_str = since.isoformat()

    # ── Gather context ────────────────────────────────────────────────────────

    # Niche portfolios with aggregated metrics
    portfolios = _x(
        db,
        """SELECT np.niche_id, np.niche_name, np.status, np.videos_per_day,
                  np.priority_score, np.total_revenue_usd, np.total_cost_usd,
                  np.profit_margin_pct,
                  COUNT(DISTINCT vm.id) as total_videos,
                  COALESCE(SUM(CASE WHEN vm.score_label='winner' THEN 1 ELSE 0 END), 0) as winners
           FROM niche_portfolio np
           LEFT JOIN video_memory vm ON vm.niche_id = np.niche_id
             AND vm.created_at >= :since
           GROUP BY np.niche_id, np.niche_name, np.status, np.videos_per_day,
                    np.priority_score, np.total_revenue_usd, np.total_cost_usd,
                    np.profit_margin_pct""",
        {"since": since_str},
    ).fetchall()

    # Channel lifecycle
    lifecycles = _x(
        db,
        "SELECT niche_id, niche_name, status, incubation_start, graduation_date FROM channel_lifecycle",
    ).fetchall()
    lifecycle_map = {r.niche_id: r for r in lifecycles}

    # Today's videos generated vs allocated
    today = date.today()
    today_gen = _x(
        db,
        "SELECT COUNT(*) as c FROM video_memory WHERE DATE(created_at) = :td",
        {"td": today},
    ).fetchone()
    today_alloc = _x(
        db,
        "SELECT COALESCE(SUM(videos_allocated), 0) as c FROM daily_allocations WHERE allocation_date = :td",
        {"td": today},
    ).fetchone()

    # Top 5 winners (last 7 days)
    top_winners = _x(
        db,
        """SELECT vm.id, vm.title, vm.niche_name,
                  COALESCE(snap.views, 0) as views, COALESCE(snap.ctr, 0) as ctr
           FROM video_memory vm
           LEFT JOIN analytics_snapshots snap ON snap.video_memory_id = vm.id
             AND snap.snapshot_type = '7d'
           WHERE vm.score_label = 'winner' AND vm.created_at >= :since
           ORDER BY COALESCE(snap.views, 0) DESC LIMIT 5""",
        {"since": since_str},
    ).fetchall()

    # Bottom 5 losers
    bottom_losers = _x(
        db,
        """SELECT vm.id, vm.title, vm.niche_name,
                  COALESCE(snap.views, 0) as views
           FROM video_memory vm
           LEFT JOIN analytics_snapshots snap ON snap.video_memory_id = vm.id
             AND snap.snapshot_type = '7d'
           WHERE vm.score_label = 'loser' AND vm.created_at >= :since
           ORDER BY COALESCE(snap.views, 0) ASC LIMIT 5""",
        {"since": since_str},
    ).fetchall()

    # Niches with 14+ days no winner
    stale_niches = _x(
        db,
        """SELECT np.niche_id, np.niche_name
           FROM niche_portfolio np
           WHERE np.status IN ('active','scaling')
             AND NOT EXISTS (
               SELECT 1 FROM video_memory vm
               WHERE vm.niche_id = np.niche_id
                 AND vm.score_label = 'winner'
                 AND vm.created_at >= :cutoff
             )""",
        {"cutoff": (datetime.utcnow() - timedelta(days=14)).isoformat()},
    ).fetchall()

    # Total compute budget
    budget_row = _x(
        db,
        "SELECT COALESCE(SUM(videos_per_day), 0) as total FROM niche_portfolio WHERE status IN ('active','scaling','incubating')",
    ).fetchone()
    total_budget = int(budget_row.total or 0)

    # ── Build context string ──────────────────────────────────────────────────
    portfolio_lines = []
    for p in portfolios:
        total_vids = int(p.total_videos or 0)
        winners = int(p.winners or 0)
        winner_rate = (winners / total_vids * 100) if total_vids > 0 else 0.0
        lc_status = lifecycle_map.get(p.niche_id)
        lc_str = lc_status.status if lc_status else "unknown"
        portfolio_lines.append(
            f"  niche_id={p.niche_id} name={p.niche_name} status={p.status} lc={lc_str} "
            f"vpd={p.videos_per_day} winner_rate={winner_rate:.1f}% "
            f"revenue=${p.total_revenue_usd:.2f} cost=${p.total_cost_usd:.2f} "
            f"margin={p.profit_margin_pct:.1f}% priority={p.priority_score:.1f}"
        )

    context = f"""=== PORTFOLIO REPORT (last 7 days) ===
Today: {today}
Videos generated today: {int(today_gen.c or 0)} / allocated: {int(today_alloc.c or 0)}
Total compute budget (videos/day): {total_budget}

NICHES:
{chr(10).join(portfolio_lines) if portfolio_lines else "  (none)"}

TOP 5 WINNERS:
{chr(10).join(f"  [{r.niche_name}] {r.title} — views={r.views} ctr={r.ctr:.1f}%" for r in top_winners) or "  (none)"}

BOTTOM 5 LOSERS:
{chr(10).join(f"  [{r.niche_name}] {r.title} — views={r.views}" for r in bottom_losers) or "  (none)"}

NICHES WITH 14+ DAYS NO WINNER:
{chr(10).join(f"  niche_id={r.niche_id} {r.niche_name}" for r in stale_niches) or "  (none)"}
"""

    system_prompt = (
        "You are the CEO of an autonomous YouTube media company. "
        "Your goal is to maximize long-term profit. "
        "You control compute budget allocation, niche lifecycle decisions, and content strategy. "
        "Make operational decisions, not just reports."
    )

    user_prompt = (
        context
        + '\nRespond with ONLY valid JSON in this exact format: '
        '{"allocations": {"<niche_id>": <videos_per_day>}, '
        '"terminate": [<niche_id>], '
        '"incubate": [{"name": "...", "query": "...", "audience": "...", "monetization_angle": "..."}], '
        '"pause": [<niche_id>], '
        '"scale": [<niche_id>], '
        '"flag_digital_product": [<niche_id>], '
        '"rationale": "...", '
        '"weekly_focus": "...", '
        '"risk_flags": ["..."]}'
    )

    # ── Call OpenRouter / Claude Opus 4.5 ─────────────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{OPENAI_API_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": "anthropic/claude-opus-4-5",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2000,
                },
            )
            resp.raise_for_status()
            raw_content = resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[capital] CEO API error: {e}", flush=True)
        return {"error": f"CEO API call failed: {e}"}

    # Strip markdown fences if present
    content = raw_content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        lines = lines[1:] if lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    try:
        decisions = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"[capital] CEO JSON parse error: {e}\nraw: {raw_content}", flush=True)
        return {"error": f"CEO response not valid JSON: {e}"}

    rationale    = decisions.get("rationale", "")
    weekly_focus = decisions.get("weekly_focus", "")
    actions_taken: List[str] = []

    # ── Execute: allocations ──────────────────────────────────────────────────
    for niche_id_str, vpd in (decisions.get("allocations") or {}).items():
        try:
            nid = int(niche_id_str)
            _x(db, "UPDATE niche_portfolio SET videos_per_day=:v WHERE niche_id=:nid",
               {"v": int(vpd), "nid": nid})
            _log_decision(db, "allocate", nid, None,
                          {"videos_per_day": int(vpd)}, rationale)
            actions_taken.append(f"allocate niche_id={nid} vpd={vpd}")
        except Exception as e:
            print(f"[capital] allocate error niche_id={niche_id_str}: {e}", flush=True)

    # ── Execute: terminate ────────────────────────────────────────────────────
    for nid in (decisions.get("terminate") or []):
        try:
            nid = int(nid)
            _x(db, "UPDATE niche_portfolio SET status='terminated' WHERE niche_id=:nid", {"nid": nid})
            _x(db,
               "UPDATE channel_lifecycle SET status='terminated', termination_date=:td WHERE niche_id=:nid",
               {"td": datetime.utcnow(), "nid": nid})
            _log_decision(db, "terminate", nid, None, {}, rationale)
            actions_taken.append(f"terminate niche_id={nid}")
        except Exception as e:
            print(f"[capital] terminate error niche_id={nid}: {e}", flush=True)

    # ── Execute: incubate ─────────────────────────────────────────────────────
    for inc in (decisions.get("incubate") or []):
        try:
            name = inc.get("name", "").strip()
            audience = inc.get("audience", "")
            monetization_angle = inc.get("monetization_angle", "")
            if not name:
                continue

            # Insert niche if not exists
            existing_niche = _x(
                db, "SELECT id FROM niches WHERE name=:n LIMIT 1", {"n": name}
            ).fetchone()
            if not existing_niche:
                _x(
                    db,
                    "INSERT INTO niches (user_id, name, audience, monetization_angle, created_at) "
                    "VALUES (1, :n, :a, :m, :ca)",
                    {"n": name, "a": audience, "m": monetization_angle, "ca": datetime.utcnow()},
                )
                db.flush()

            niche_row = _x(db, "SELECT id FROM niches WHERE name=:n LIMIT 1", {"n": name}).fetchone()
            niche_id = niche_row.id if niche_row else None

            # Insert niche_portfolio if not exists
            existing_np = _x(
                db, "SELECT id FROM niche_portfolio WHERE niche_name=:n LIMIT 1", {"n": name}
            ).fetchone()
            if not existing_np and niche_id:
                _x(
                    db,
                    "INSERT INTO niche_portfolio "
                    "(niche_id, niche_name, status, videos_per_day, created_at, updated_at) "
                    "VALUES (:ni, :n, 'incubating', 1, :ca, :ca)",
                    {"ni": niche_id, "n": name, "ca": datetime.utcnow()},
                )

            # Insert channel_lifecycle if not exists
            if niche_id:
                existing_lc = _x(
                    db, "SELECT id FROM channel_lifecycle WHERE niche_id=:ni LIMIT 1", {"ni": niche_id}
                ).fetchone()
                if not existing_lc:
                    _x(
                        db,
                        "INSERT INTO channel_lifecycle "
                        "(niche_id, niche_name, status, incubation_start, created_at, updated_at) "
                        "VALUES (:ni, :n, 'incubating', :is, :ca, :ca)",
                        {"ni": niche_id, "n": name, "is": datetime.utcnow(), "ca": datetime.utcnow()},
                    )

            _log_decision(db, "incubate", niche_id, name, inc, rationale)
            actions_taken.append(f"incubate niche={name}")
        except Exception as e:
            print(f"[capital] incubate error {inc}: {e}", flush=True)

    # ── Execute: pause ────────────────────────────────────────────────────────
    for nid in (decisions.get("pause") or []):
        try:
            nid = int(nid)
            _x(db, "UPDATE niche_portfolio SET status='paused' WHERE niche_id=:nid", {"nid": nid})
            _x(db, "UPDATE channel_lifecycle SET status='paused' WHERE niche_id=:nid", {"nid": nid})
            _log_decision(db, "pause", nid, None, {}, rationale)
            actions_taken.append(f"pause niche_id={nid}")
        except Exception as e:
            print(f"[capital] pause error niche_id={nid}: {e}", flush=True)

    # ── Execute: scale ────────────────────────────────────────────────────────
    for nid in (decisions.get("scale") or []):
        try:
            nid = int(nid)
            _x(
                db,
                "UPDATE niche_portfolio SET status='scaling', "
                "videos_per_day=LEAST(videos_per_day+1, 5) WHERE niche_id=:nid",
                {"nid": nid},
            )
            _x(db, "UPDATE channel_lifecycle SET status='scaling' WHERE niche_id=:nid", {"nid": nid})
            _log_decision(db, "scale", nid, None, {}, rationale)
            actions_taken.append(f"scale niche_id={nid}")
        except Exception as e:
            print(f"[capital] scale error niche_id={nid}: {e}", flush=True)

    # ── Execute: flag_digital_product ─────────────────────────────────────────
    for nid in (decisions.get("flag_digital_product") or []):
        try:
            nid = int(nid)
            niche_row = _x(
                db, "SELECT niche_name FROM niche_portfolio WHERE niche_id=:nid LIMIT 1", {"nid": nid}
            ).fetchone()
            niche_name_str = niche_row.niche_name if niche_row else str(nid)

            existing = _x(
                db, "SELECT id FROM digital_product_opportunities WHERE niche_id=:nid LIMIT 1", {"nid": nid}
            ).fetchone()
            if not existing:
                _x(
                    db,
                    "INSERT INTO digital_product_opportunities "
                    "(niche_id, niche_name, status, flagged_at) VALUES (:ni, :nn, 'flagged', :fa)",
                    {"ni": nid, "nn": niche_name_str, "fa": datetime.utcnow()},
                )
            _log_decision(db, "flag_product", nid, niche_name_str, {}, rationale)
            actions_taken.append(f"flag_digital_product niche_id={nid}")
        except Exception as e:
            print(f"[capital] flag_product error niche_id={nid}: {e}", flush=True)

    # ── Store rationale in ceo_reports ────────────────────────────────────────
    try:
        _x(
            db,
            "INSERT INTO ceo_reports (report_date, content, decisions, created_at) "
            "VALUES (:rd, :co, :de, :ca)",
            {
                "rd": date.today(),
                "co": rationale,
                "de": json.dumps(decisions),
                "ca": datetime.utcnow(),
            },
        )
    except Exception as e:
        print(f"[capital] ceo_reports insert error: {e}", flush=True)

    db.commit()

    return {
        "actions_taken": actions_taken,
        "rationale": rationale,
        "weekly_focus": weekly_focus,
        "risk_flags": decisions.get("risk_flags", []),
    }


# ── 2. Dynamic Daily Scheduler ────────────────────────────────────────────────

async def build_daily_schedule(db: Session) -> list:
    """
    Read active niches, space up to 8 jobs starting 07:00 UTC two hours apart,
    prioritise by priority_score DESC when there are more niches than slots.
    """
    today = date.today()

    niches = _x(
        db,
        "SELECT niche_id, niche_name, videos_per_day, priority_score "
        "FROM niche_portfolio "
        "WHERE status IN ('active','scaling','incubating') AND videos_per_day > 0 "
        "ORDER BY priority_score DESC",
    ).fetchall()

    MAX_SLOTS = 8
    START_HOUR = 7   # 07:00 UTC
    SLOT_GAP   = 2   # hours between slots

    # Expand each niche by its videos_per_day allocation, up to MAX_SLOTS
    expanded: List[dict] = []
    for row in niches:
        for _ in range(row.videos_per_day):
            expanded.append({"niche_id": row.niche_id, "niche_name": row.niche_name})
        if len(expanded) >= MAX_SLOTS:
            expanded = expanded[:MAX_SLOTS]
            break

    schedule_entries = []
    today_dt = datetime.combine(today, time(START_HOUR, 0))

    for slot_num, entry in enumerate(expanded):
        slot_time = today_dt + timedelta(hours=slot_num * SLOT_GAP)
        slot_iso  = slot_time.isoformat()

        # Check if allocation already exists for this niche today
        existing = _x(
            db,
            "SELECT id FROM daily_allocations WHERE allocation_date=:td AND niche_id=:ni LIMIT 1",
            {"td": today, "ni": entry["niche_id"]},
        ).fetchone()

        if not existing:
            _x(
                db,
                """INSERT INTO daily_allocations
                   (allocation_date, niche_id, niche_name, videos_allocated,
                    videos_completed, scheduled_times, total_compute_budget, created_at)
                   VALUES (:td, :ni, :nn, 1, 0, :st, :tcb, :ca)""",
                {
                    "td":  today,
                    "ni":  entry["niche_id"],
                    "nn":  entry["niche_name"],
                    "st":  json.dumps([slot_iso]),
                    "tcb": len(expanded),
                    "ca":  datetime.utcnow(),
                },
            )
        else:
            # Append the slot time to existing scheduled_times
            existing_row = _x(
                db,
                "SELECT scheduled_times, videos_allocated FROM daily_allocations WHERE id=:eid",
                {"eid": existing.id},
            ).fetchone()
            existing_times = existing_row.scheduled_times or []
            if isinstance(existing_times, str):
                existing_times = json.loads(existing_times)
            existing_times.append(slot_iso)
            _x(
                db,
                "UPDATE daily_allocations SET scheduled_times=:st, videos_allocated=:va WHERE id=:eid",
                {
                    "st": json.dumps(existing_times),
                    "va": int(existing_row.videos_allocated or 0) + 1,
                    "eid": existing.id,
                },
            )

        schedule_entries.append({
            "niche_id":       entry["niche_id"],
            "niche_name":     entry["niche_name"],
            "scheduled_time": slot_iso,
            "slot_number":    slot_num + 1,
        })

    db.commit()
    return schedule_entries


# ── 3. Incubation Lifecycle Checker ──────────────────────────────────────────

async def check_incubation_status(db: Session) -> dict:
    """
    Advance or terminate niches based on video performance thresholds.
    Also promotes active→scaling and active→watch based on 14-day winner rate.
    """
    now = datetime.utcnow()
    report: Dict[str, list] = {"graduated": [], "terminated": [], "promoted_scaling": [], "moved_watch": [], "terminated_watch": []}

    # ── Incubating niches ──────────────────────────────────────────────────────
    incubating = _x(
        db,
        "SELECT niche_id, niche_name, incubation_start, graduation_videos_required, "
        "graduation_threshold_views, graduation_threshold_ctr, kill_days, kill_views_threshold "
        "FROM channel_lifecycle WHERE status='incubating'",
    ).fetchall()

    for lc in incubating:
        niche_id = lc.niche_id

        # Count total videos in this niche
        total_row = _x(
            db, "SELECT COUNT(*) as c FROM video_memory WHERE niche_id=:ni", {"ni": niche_id}
        ).fetchone()
        total_vids = int(total_row.c or 0)

        # Count graduated videos: 7d snapshot with views >= threshold AND ctr >= threshold
        grad_row = _x(
            db,
            """SELECT COUNT(DISTINCT vm.id) as c
               FROM video_memory vm
               JOIN analytics_snapshots snap ON snap.video_memory_id = vm.id
                 AND snap.snapshot_type = '7d'
               WHERE vm.niche_id = :ni
                 AND snap.views >= :tv
                 AND snap.ctr >= :tc""",
            {
                "ni": niche_id,
                "tv": lc.graduation_threshold_views,
                "tc": lc.graduation_threshold_ctr,
            },
        ).fetchone()
        graduated_count = int(grad_row.c or 0)

        # Days since incubation started
        if lc.incubation_start:
            days_since = (now - lc.incubation_start).days
        else:
            days_since = 0

        if graduated_count >= (lc.graduation_videos_required or 3):
            # Promote to active
            _x(
                db,
                "UPDATE channel_lifecycle SET status='active', graduation_date=:gd, updated_at=:ua "
                "WHERE niche_id=:ni",
                {"gd": now, "ua": now, "ni": niche_id},
            )
            _x(
                db,
                "UPDATE niche_portfolio SET status='active', videos_per_day=2, updated_at=:ua "
                "WHERE niche_id=:ni",
                {"ua": now, "ni": niche_id},
            )
            _log_decision(db, "incubate", niche_id, lc.niche_name,
                          {"graduated_count": graduated_count}, "Incubation graduation threshold met")
            report["graduated"].append({"niche_id": niche_id, "niche_name": lc.niche_name})

        elif days_since >= (lc.kill_days or 14) and graduated_count == 0:
            # Check if any video at least hit the kill_views_threshold
            any_views_row = _x(
                db,
                """SELECT COUNT(DISTINCT vm.id) as c
                   FROM video_memory vm
                   JOIN analytics_snapshots snap ON snap.video_memory_id = vm.id
                   WHERE vm.niche_id = :ni AND snap.views >= :kv""",
                {"ni": niche_id, "kv": lc.kill_views_threshold or 100},
            ).fetchone()
            any_views = int(any_views_row.c or 0)

            if any_views == 0:
                _x(
                    db,
                    "UPDATE channel_lifecycle SET status='terminated', termination_date=:td, updated_at=:ua "
                    "WHERE niche_id=:ni",
                    {"td": now, "ua": now, "ni": niche_id},
                )
                _x(
                    db,
                    "UPDATE niche_portfolio SET status='terminated', videos_per_day=0, updated_at=:ua "
                    "WHERE niche_id=:ni",
                    {"ua": now, "ni": niche_id},
                )
                _log_decision(db, "terminate", niche_id, lc.niche_name,
                              {"days": days_since, "graduated": 0}, "Incubation kill threshold reached")
                report["terminated"].append({"niche_id": niche_id, "niche_name": lc.niche_name})

    # ── Active niches — check for scaling or watch ────────────────────────────
    cutoff_14d = (now - timedelta(days=14)).isoformat()

    active = _x(
        db, "SELECT niche_id, niche_name FROM channel_lifecycle WHERE status='active'",
    ).fetchall()

    for lc in active:
        niche_id = lc.niche_id

        total_row = _x(
            db,
            "SELECT COUNT(*) as c FROM video_memory WHERE niche_id=:ni AND created_at>=:cut",
            {"ni": niche_id, "cut": cutoff_14d},
        ).fetchone()
        total_vids = int(total_row.c or 0)

        if total_vids == 0:
            continue

        winner_row = _x(
            db,
            "SELECT COUNT(*) as c FROM video_memory "
            "WHERE niche_id=:ni AND score_label='winner' AND created_at>=:cut",
            {"ni": niche_id, "cut": cutoff_14d},
        ).fetchone()
        winners = int(winner_row.c or 0)
        winner_rate = winners / total_vids

        if winner_rate >= 0.3 and winners >= 2:
            _x(db, "UPDATE channel_lifecycle SET status='scaling', updated_at=:ua WHERE niche_id=:ni",
               {"ua": now, "ni": niche_id})
            _x(db,
               "UPDATE niche_portfolio SET status='scaling', "
               "videos_per_day=LEAST(videos_per_day+1, 5), updated_at=:ua WHERE niche_id=:ni",
               {"ua": now, "ni": niche_id})
            _log_decision(db, "scale", niche_id, lc.niche_name,
                          {"winner_rate": winner_rate, "winners": winners}, "Auto-scale: 30% winner rate")
            report["promoted_scaling"].append({"niche_id": niche_id, "niche_name": lc.niche_name})

        elif winner_rate < 0.1 and total_vids >= 10:
            _x(db, "UPDATE channel_lifecycle SET status='watch', updated_at=:ua WHERE niche_id=:ni",
               {"ua": now, "ni": niche_id})
            _x(db, "UPDATE niche_portfolio SET status='watch', updated_at=:ua WHERE niche_id=:ni",
               {"ua": now, "ni": niche_id})
            _log_decision(db, "pause", niche_id, lc.niche_name,
                          {"winner_rate": winner_rate, "total": total_vids}, "Moved to watch: <10% winner rate")
            report["moved_watch"].append({"niche_id": niche_id, "niche_name": lc.niche_name})

    # ── Watch niches — terminate if no new winners in 14 days ────────────────
    watching = _x(
        db, "SELECT niche_id, niche_name FROM channel_lifecycle WHERE status='watch'",
    ).fetchall()

    for lc in watching:
        niche_id = lc.niche_id
        new_winner = _x(
            db,
            "SELECT COUNT(*) as c FROM video_memory "
            "WHERE niche_id=:ni AND score_label='winner' AND created_at>=:cut",
            {"ni": niche_id, "cut": cutoff_14d},
        ).fetchone()
        if int(new_winner.c or 0) == 0:
            _x(
                db,
                "UPDATE channel_lifecycle SET status='terminated', termination_date=:td, updated_at=:ua "
                "WHERE niche_id=:ni",
                {"td": now, "ua": now, "ni": niche_id},
            )
            _x(
                db,
                "UPDATE niche_portfolio SET status='terminated', videos_per_day=0, updated_at=:ua "
                "WHERE niche_id=:ni",
                {"ua": now, "ni": niche_id},
            )
            _log_decision(db, "terminate", niche_id, lc.niche_name,
                          {}, "Watch period expired — no new winners in 14 days")
            report["terminated_watch"].append({"niche_id": niche_id, "niche_name": lc.niche_name})

    db.commit()
    return report


# ── 4. Affiliate Link Injector ────────────────────────────────────────────────

def get_affiliate_block(niche_name: str, db: Session) -> str:
    """
    Returns a formatted affiliate block to append to a YouTube description.
    Falls back to generic programs when no niche match is found.
    """
    normalized = niche_name.lower().replace(" ", "_").replace("-", "_")

    rows = _x(
        db,
        """SELECT product_name, affiliate_url, cta_text
           FROM affiliate_programs
           WHERE (LOWER(niche_name) = :nn OR LOWER(REPLACE(niche_name,' ','_')) = :nn)
             AND active = true
           ORDER BY priority ASC LIMIT 3""",
        {"nn": normalized},
    ).fetchall()

    if not rows:
        # Generic fallback
        rows = _x(
            db,
            """SELECT product_name, affiliate_url, cta_text
               FROM affiliate_programs
               WHERE product_name IN ('Skillshare','Notion AI')
                 AND active = true
               ORDER BY priority ASC LIMIT 2""",
        ).fetchall()

    if not rows:
        return "\n\n--- RESOURCES MENTIONED ---\n🔗 Start learning for free: https://skillshare.com\n"

    lines = ["\n\n--- RESOURCES MENTIONED ---"]
    for r in rows:
        cta = r.cta_text or r.product_name
        lines.append(f"🔗 {cta}: {r.affiliate_url}")
    lines.append("")
    return "\n".join(lines)


# ── 5. Revenue Stream Recorder ────────────────────────────────────────────────

def record_revenue(
    niche_id: int,
    stream_type: str,
    amount: float,
    video_memory_id: Optional[int],
    db: Session,
) -> dict:
    """Insert revenue stream and update niche_portfolio aggregate."""
    _x(
        db,
        """INSERT INTO revenue_streams
           (video_memory_id, niche_id, stream_type, amount_usd, recorded_at)
           VALUES (:vmid, :ni, :st, :am, :ra)""",
        {
            "vmid": video_memory_id,
            "ni":   niche_id,
            "st":   stream_type,
            "am":   amount,
            "ra":   datetime.utcnow(),
        },
    )

    if stream_type == "adsense":
        _x(
            db,
            "UPDATE niche_portfolio SET total_revenue_usd = total_revenue_usd + :am WHERE niche_id=:ni",
            {"am": amount, "ni": niche_id},
        )

    # Recalculate profit_margin_pct
    row = _x(
        db,
        "SELECT total_revenue_usd, total_cost_usd FROM niche_portfolio WHERE niche_id=:ni",
        {"ni": niche_id},
    ).fetchone()

    if row and float(row.total_revenue_usd or 0) > 0:
        margin = (float(row.total_revenue_usd) - float(row.total_cost_usd or 0)) \
                 / float(row.total_revenue_usd) * 100
        _x(
            db,
            "UPDATE niche_portfolio SET profit_margin_pct=:pm, updated_at=:ua WHERE niche_id=:ni",
            {"pm": margin, "ua": datetime.utcnow(), "ni": niche_id},
        )

    db.commit()
    return {"recorded": True, "niche_id": niche_id, "amount_usd": amount, "stream_type": stream_type}


# ── 6. Digital Product Flagger ────────────────────────────────────────────────

def check_digital_product_opportunities(db: Session) -> list:
    """
    Flag niches that have >= 10,000 total views AND >= 30% winner rate
    but haven't been flagged yet.
    """
    niches = _x(
        db,
        "SELECT niche_id, niche_name, total_revenue_usd FROM niche_portfolio "
        "WHERE status IN ('active','scaling')",
    ).fetchall()

    flagged: List[dict] = []

    for n in niches:
        nid = n.niche_id

        total_views_row = _x(
            db,
            """SELECT COALESCE(SUM(snap.views), 0) as tv
               FROM video_memory vm
               JOIN analytics_snapshots snap ON snap.video_memory_id = vm.id
               WHERE vm.niche_id = :ni""",
            {"ni": nid},
        ).fetchone()
        total_views = int(total_views_row.tv or 0)

        if total_views < 10000:
            continue

        total_row = _x(
            db, "SELECT COUNT(*) as c FROM video_memory WHERE niche_id=:ni", {"ni": nid}
        ).fetchone()
        total_vids = int(total_row.c or 0)

        if total_vids == 0:
            continue

        winner_row = _x(
            db,
            "SELECT COUNT(*) as c FROM video_memory WHERE niche_id=:ni AND score_label='winner'",
            {"ni": nid},
        ).fetchone()
        winner_rate = int(winner_row.c or 0) / total_vids

        if winner_rate < 0.3:
            continue

        # Check already flagged
        existing = _x(
            db,
            "SELECT id FROM digital_product_opportunities WHERE niche_id=:ni LIMIT 1",
            {"ni": nid},
        ).fetchone()
        if existing:
            continue

        # Get monetization angle for product idea
        np_row = _x(
            db,
            "SELECT niche_name FROM niche_portfolio WHERE niche_id=:ni LIMIT 1",
            {"ni": nid},
        ).fetchone()
        niche_name_str = np_row.niche_name if np_row else n.niche_name

        # Simple template for product idea
        product_idea = (
            f"The {niche_name_str.replace('_', ' ').title()} Playbook — "
            f"A step-by-step guide to mastering {niche_name_str.replace('_', ' ')} "
            f"and building income in this niche."
        )

        _x(
            db,
            """INSERT INTO digital_product_opportunities
               (niche_id, niche_name, status, trigger_views, trigger_winner_rate,
                product_idea, estimated_price, flagged_at)
               VALUES (:ni, :nn, 'flagged', :tv, :wr, :pi, 27.0, :fa)""",
            {
                "ni": nid,
                "nn": niche_name_str,
                "tv": total_views,
                "wr": winner_rate,
                "pi": product_idea,
                "fa": datetime.utcnow(),
            },
        )
        flagged.append({"niche_id": nid, "niche_name": niche_name_str, "total_views": total_views})

    db.commit()
    return flagged


# ── FastAPI Router ────────────────────────────────────────────────────────────

capital_router = APIRouter(prefix="/capital", tags=["capital"])


# ─ Pydantic request models ────────────────────────────────────────────────────

class AffiliateProgramCreate(BaseModel):
    niche_name: str
    product_name: str
    affiliate_url: str
    commission_type: str   # flat | percent
    commission_value: float
    priority: int = 1
    active: bool = True
    description: Optional[str] = None
    cta_text: Optional[str] = None


class RevenueRecordRequest(BaseModel):
    niche_id: int
    stream_type: str
    amount_usd: float
    video_memory_id: Optional[int] = None
    notes: Optional[str] = None


# ─ CEO routes ─────────────────────────────────────────────────────────────────

@capital_router.post("/ceo/execute")
async def ceo_execute():
    db = _SessionLocal()
    try:
        result = await run_ceo_executor(db)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@capital_router.get("/ceo/decisions")
def ceo_decisions():
    db = _SessionLocal()
    try:
        rows = _x(
            db,
            "SELECT id, decision_date, decision_type, niche_id, niche_name, "
            "payload, executed, executed_at, rationale, created_at "
            "FROM ceo_decisions ORDER BY created_at DESC LIMIT 30",
        ).fetchall()
        return [
            {
                "id":            r.id,
                "decision_date": str(r.decision_date),
                "decision_type": r.decision_type,
                "niche_id":      r.niche_id,
                "niche_name":    r.niche_name,
                "payload":       r.payload,
                "executed":      r.executed,
                "executed_at":   r.executed_at.isoformat() if r.executed_at else None,
                "rationale":     r.rationale,
                "created_at":    r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    finally:
        db.close()


# ─ Schedule routes ────────────────────────────────────────────────────────────

@capital_router.get("/schedule/today")
def schedule_today():
    db = _SessionLocal()
    try:
        today = date.today()
        rows = _x(
            db,
            "SELECT id, niche_id, niche_name, videos_allocated, videos_completed, "
            "scheduled_times, total_compute_budget, created_at "
            "FROM daily_allocations WHERE allocation_date=:td ORDER BY id",
            {"td": today},
        ).fetchall()
        return [
            {
                "id":                  r.id,
                "niche_id":            r.niche_id,
                "niche_name":          r.niche_name,
                "videos_allocated":    r.videos_allocated,
                "videos_completed":    r.videos_completed,
                "scheduled_times":     r.scheduled_times or [],
                "total_compute_budget": r.total_compute_budget,
                "created_at":          r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    finally:
        db.close()


@capital_router.post("/schedule/build")
async def schedule_build():
    db = _SessionLocal()
    try:
        entries = await build_daily_schedule(db)
        return {"schedule": entries, "count": len(entries)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ─ Lifecycle routes ───────────────────────────────────────────────────────────

@capital_router.get("/lifecycle")
def lifecycle_list():
    db = _SessionLocal()
    try:
        rows = _x(
            db,
            "SELECT id, niche_id, niche_name, status, videos_tested, videos_graduated, "
            "incubation_start, graduation_date, termination_date, notes, created_at, updated_at "
            "FROM channel_lifecycle ORDER BY niche_id",
        ).fetchall()
        return [
            {
                "id":                r.id,
                "niche_id":         r.niche_id,
                "niche_name":       r.niche_name,
                "status":           r.status,
                "videos_tested":    r.videos_tested,
                "videos_graduated": r.videos_graduated,
                "incubation_start": r.incubation_start.isoformat() if r.incubation_start else None,
                "graduation_date":  r.graduation_date.isoformat() if r.graduation_date else None,
                "termination_date": r.termination_date.isoformat() if r.termination_date else None,
                "notes":            r.notes,
                "created_at":       r.created_at.isoformat() if r.created_at else None,
                "updated_at":       r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ]
    finally:
        db.close()


@capital_router.post("/lifecycle/check")
async def lifecycle_check():
    db = _SessionLocal()
    try:
        report = await check_incubation_status(db)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ─ Affiliate routes ───────────────────────────────────────────────────────────

@capital_router.get("/affiliates")
def affiliates_list():
    db = _SessionLocal()
    try:
        rows = _x(
            db,
            "SELECT id, niche_name, product_name, affiliate_url, commission_type, "
            "commission_value, priority, active, cta_text, clicks_estimated, "
            "revenue_estimated, created_at FROM affiliate_programs ORDER BY niche_name, priority",
        ).fetchall()
        return [
            {
                "id":                r.id,
                "niche_name":        r.niche_name,
                "product_name":      r.product_name,
                "affiliate_url":     r.affiliate_url,
                "commission_type":   r.commission_type,
                "commission_value":  r.commission_value,
                "priority":          r.priority,
                "active":            r.active,
                "cta_text":          r.cta_text,
                "clicks_estimated":  r.clicks_estimated,
                "revenue_estimated": r.revenue_estimated,
                "created_at":        r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    finally:
        db.close()


@capital_router.post("/affiliates")
def affiliates_add(body: AffiliateProgramCreate):
    db = _SessionLocal()
    try:
        _x(
            db,
            """INSERT INTO affiliate_programs
               (niche_name, product_name, affiliate_url, commission_type, commission_value,
                priority, active, description, cta_text, created_at)
               VALUES (:nn, :pn, :au, :ct, :cv, :pr, :ac, :de, :cta, :ca)""",
            {
                "nn":  body.niche_name,
                "pn":  body.product_name,
                "au":  body.affiliate_url,
                "ct":  body.commission_type,
                "cv":  body.commission_value,
                "pr":  body.priority,
                "ac":  body.active,
                "de":  body.description,
                "cta": body.cta_text,
                "ca":  datetime.utcnow(),
            },
        )
        db.commit()
        return {"status": "created", "product_name": body.product_name}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@capital_router.get("/affiliates/{niche_name}")
def affiliate_block(niche_name: str):
    db = _SessionLocal()
    try:
        block = get_affiliate_block(niche_name, db)
        return {"niche_name": niche_name, "affiliate_block": block}
    finally:
        db.close()


# ─ Revenue routes ─────────────────────────────────────────────────────────────

@capital_router.get("/revenue")
def revenue_summary():
    db = _SessionLocal()
    try:
        rows = _x(
            db,
            """SELECT rs.niche_id, np.niche_name,
                      rs.stream_type,
                      COUNT(*) as events,
                      SUM(rs.amount_usd) as total_usd
               FROM revenue_streams rs
               LEFT JOIN niche_portfolio np ON np.niche_id = rs.niche_id
               GROUP BY rs.niche_id, np.niche_name, rs.stream_type
               ORDER BY total_usd DESC""",
        ).fetchall()
        return [
            {
                "niche_id":   r.niche_id,
                "niche_name": r.niche_name,
                "stream_type": r.stream_type,
                "events":     int(r.events or 0),
                "total_usd":  round(float(r.total_usd or 0), 4),
            }
            for r in rows
        ]
    finally:
        db.close()


@capital_router.post("/revenue")
def revenue_record(body: RevenueRecordRequest):
    db = _SessionLocal()
    try:
        result = record_revenue(
            niche_id=body.niche_id,
            stream_type=body.stream_type,
            amount=body.amount_usd,
            video_memory_id=body.video_memory_id,
            db=db,
        )
        return result
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ─ Digital products routes ────────────────────────────────────────────────────

@capital_router.get("/digital-products")
def digital_products_list():
    db = _SessionLocal()
    try:
        rows = _x(
            db,
            "SELECT id, niche_id, niche_name, status, trigger_views, trigger_winner_rate, "
            "product_idea, estimated_price, flagged_at, launched_at "
            "FROM digital_product_opportunities ORDER BY flagged_at DESC",
        ).fetchall()
        return [
            {
                "id":                  r.id,
                "niche_id":            r.niche_id,
                "niche_name":          r.niche_name,
                "status":              r.status,
                "trigger_views":       r.trigger_views,
                "trigger_winner_rate": r.trigger_winner_rate,
                "product_idea":        r.product_idea,
                "estimated_price":     r.estimated_price,
                "flagged_at":          r.flagged_at.isoformat() if r.flagged_at else None,
                "launched_at":         r.launched_at.isoformat() if r.launched_at else None,
            }
            for r in rows
        ]
    finally:
        db.close()


# ─ Capital summary route ──────────────────────────────────────────────────────

@capital_router.get("/summary")
def capital_summary():
    db = _SessionLocal()
    try:
        # Niches
        niches_rows = _x(
            db,
            "SELECT niche_id, niche_name, status, videos_per_day, priority_score, "
            "total_revenue_usd, total_cost_usd, profit_margin_pct "
            "FROM niche_portfolio ORDER BY priority_score DESC",
        ).fetchall()

        # Lifecycle
        lc_rows = _x(
            db,
            "SELECT niche_id, status FROM channel_lifecycle",
        ).fetchall()
        lc_map = {r.niche_id: r.status for r in lc_rows}

        # Today's allocations
        today = date.today()
        alloc_rows = _x(
            db,
            "SELECT niche_id, videos_allocated, videos_completed "
            "FROM daily_allocations WHERE allocation_date=:td",
            {"td": today},
        ).fetchall()
        alloc_map = {r.niche_id: {"allocated": r.videos_allocated, "completed": r.videos_completed}
                     for r in alloc_rows}

        # Revenue totals
        rev_row = _x(
            db,
            "SELECT COALESCE(SUM(amount_usd), 0) as total FROM revenue_streams",
        ).fetchone()

        # Flagged products
        prod_count = _x(
            db,
            "SELECT COUNT(*) as c FROM digital_product_opportunities WHERE status='flagged'",
        ).fetchone()

        return {
            "niches": [
                {
                    "niche_id":         r.niche_id,
                    "niche_name":       r.niche_name,
                    "portfolio_status": r.status,
                    "lifecycle_status": lc_map.get(r.niche_id, "unknown"),
                    "videos_per_day":   r.videos_per_day,
                    "priority_score":   r.priority_score,
                    "revenue_usd":      round(float(r.total_revenue_usd or 0), 4),
                    "cost_usd":         round(float(r.total_cost_usd or 0), 4),
                    "profit_margin_pct": round(float(r.profit_margin_pct or 0), 1),
                    "today_allocated":  alloc_map.get(r.niche_id, {}).get("allocated", 0),
                    "today_completed":  alloc_map.get(r.niche_id, {}).get("completed", 0),
                }
                for r in niches_rows
            ],
            "total_revenue_usd":        round(float(rev_row.total or 0), 4),
            "flagged_digital_products": int(prod_count.c or 0),
            "report_date":              str(today),
        }
    finally:
        db.close()


# ── Scheduler Registration ────────────────────────────────────────────────────

def register_capital_scheduler(app) -> None:
    """
    Register APScheduler jobs on FastAPI startup.
    Imports APScheduler from autonomy if available, otherwise creates own.
    """
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = AsyncIOScheduler(timezone="UTC")

    @app.on_event("startup")
    async def _startup():
        # Seed affiliate programs once
        _db = _SessionLocal()
        try:
            _seed_affiliates(_db)
        except Exception as e:
            print(f"[capital] affiliate seed error: {e}", flush=True)
        finally:
            _db.close()

        # CEO executor: 05:30 UTC daily
        scheduler.add_job(
            _run_ceo_job,
            CronTrigger(hour=5, minute=30),
            id="capital_ceo_executor",
            replace_existing=True,
        )

        # Incubation check: 06:00 UTC daily
        scheduler.add_job(
            _run_incubation_job,
            CronTrigger(hour=6, minute=0),
            id="capital_incubation_check",
            replace_existing=True,
        )

        # Digital product check: 06:15 UTC daily
        scheduler.add_job(
            _run_digital_product_job,
            CronTrigger(hour=6, minute=15),
            id="capital_digital_products",
            replace_existing=True,
        )

        # Daily schedule build: 06:45 UTC daily
        scheduler.add_job(
            _run_daily_schedule_job,
            CronTrigger(hour=6, minute=45),
            id="capital_daily_schedule",
            replace_existing=True,
        )

        if not scheduler.running:
            scheduler.start()
        print("[capital] scheduler started", flush=True)

    @app.on_event("shutdown")
    def _shutdown():
        if scheduler.running:
            scheduler.shutdown(wait=False)


# ── Async job wrappers (APScheduler calls these directly) ─────────────────────

async def _run_ceo_job():
    db = _SessionLocal()
    try:
        result = await run_ceo_executor(db)
        print(f"[capital] CEO job done: {result.get('actions_taken', [])}", flush=True)
    except Exception as e:
        print(f"[capital] CEO job error: {e}", flush=True)
    finally:
        db.close()


async def _run_incubation_job():
    db = _SessionLocal()
    try:
        report = await check_incubation_status(db)
        print(f"[capital] incubation check done: {report}", flush=True)
    except Exception as e:
        print(f"[capital] incubation job error: {e}", flush=True)
    finally:
        db.close()


def _run_digital_product_job():
    db = _SessionLocal()
    try:
        flagged = check_digital_product_opportunities(db)
        if flagged:
            print(f"[capital] flagged digital products: {flagged}", flush=True)
    except Exception as e:
        print(f"[capital] digital product job error: {e}", flush=True)
    finally:
        db.close()


async def _run_daily_schedule_job():
    db = _SessionLocal()
    try:
        entries = await build_daily_schedule(db)
        print(f"[capital] daily schedule built: {len(entries)} slots", flush=True)
    except Exception as e:
        print(f"[capital] daily schedule job error: {e}", flush=True)
    finally:
        db.close()
