"""
Intelligence layer — trend scraping, hook/thumbnail analytics, CEO agent, portfolio manager.
Imported by main.py:
    from intelligence import intelligence_router, register_intelligence_scheduler
    app.include_router(intelligence_router)
    register_intelligence_scheduler(app)
"""

import os
import json
import asyncio
import subprocess
from datetime import datetime, timedelta, timezone, date
from typing import Optional, List, Dict, Any

import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, Date, JSON as SAJSON,
    create_engine, UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, Session, sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text

# ── Engine (own pool, NullPool for edge/serverless friendliness) ──────────────
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/handholding")
_engine = create_engine(DATABASE_URL, poolclass=NullPool)
_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
Base = declarative_base()

# ── Env vars ──────────────────────────────────────────────────────────────────
YOUTUBE_API_KEY  = os.getenv("YOUTUBE_API_KEY", "")
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE  = os.getenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1")


# ── Raw-SQL helper (SQLAlchemy 2.x) ──────────────────────────────────────────
def _x(db: Session, sql: str, *args, **kwargs):
    return db.execute(text(sql), *args, **kwargs)


# ── DB Models ─────────────────────────────────────────────────────────────────

class TrendVideo(Base):
    __tablename__ = "trend_videos"
    id                = Column(Integer, primary_key=True)
    niche_id          = Column(Integer, nullable=False)
    niche_name        = Column(String, nullable=False)
    title             = Column(String, nullable=False)
    channel           = Column(String, nullable=True)
    video_id          = Column(String, nullable=True)          # YouTube video ID
    views             = Column(Integer, default=0)
    likes             = Column(Integer, default=0)
    published_at      = Column(DateTime, nullable=True)
    trend_score       = Column(Float, default=0.0)
    hook_style        = Column(String, nullable=True)
    thumbnail_style   = Column(String, nullable=True)
    duration_seconds  = Column(Integer, default=0)
    created_at        = Column(DateTime, default=datetime.utcnow)


class HookPerformance(Base):
    __tablename__ = "hook_performance"
    id                = Column(Integer, primary_key=True)
    hook_type         = Column(String, nullable=False)
    niche_id          = Column(Integer, nullable=False)
    video_count       = Column(Integer, default=0)
    avg_retention_pct = Column(Float, default=0.0)
    avg_ctr           = Column(Float, default=0.0)
    avg_views         = Column(Integer, default=0)
    updated_at        = Column(DateTime, default=datetime.utcnow)
    __table_args__    = (UniqueConstraint("hook_type", "niche_id", name="uq_hook_niche"),)


class ThumbnailPerformance(Base):
    __tablename__ = "thumbnail_performance"
    id             = Column(Integer, primary_key=True)
    style          = Column(String, nullable=False)
    niche_id       = Column(Integer, nullable=False)
    video_count    = Column(Integer, default=0)
    avg_ctr        = Column(Float, default=0.0)
    avg_impressions= Column(Integer, default=0)
    updated_at     = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("style", "niche_id", name="uq_thumb_niche"),)


class VideoJobCost(Base):
    __tablename__      = "video_job_costs"
    id                 = Column(Integer, primary_key=True)
    job_id             = Column(String, nullable=False)
    user_id            = Column(Integer, nullable=True)
    niche_id           = Column(Integer, nullable=True)
    openai_cost_usd    = Column(Float, default=0.0)
    rendering_seconds  = Column(Float, default=0.0)
    total_cost_usd     = Column(Float, default=0.0)
    created_at         = Column(DateTime, default=datetime.utcnow)


class CEOReport(Base):
    __tablename__ = "ceo_reports"
    id            = Column(Integer, primary_key=True)
    report_date   = Column(Date, default=date.today)
    content       = Column(Text, nullable=True)
    decisions     = Column(SAJSON, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)


class NichePortfolio(Base):
    __tablename__       = "niche_portfolio"
    id                  = Column(Integer, primary_key=True)
    niche_id            = Column(Integer, unique=True, nullable=False)
    niche_name          = Column(String, nullable=False)
    status              = Column(String, default="active")   # active|scaling|paused|terminated
    videos_per_day      = Column(Integer, default=1)
    priority_score      = Column(Float, default=0.0)
    total_revenue_usd   = Column(Float, default=0.0)
    total_cost_usd      = Column(Float, default=0.0)
    profit_margin_pct   = Column(Float, default=0.0)
    last_evaluated_at   = Column(DateTime, nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Create tables (best-effort; schema may already exist)
try:
    Base.metadata.create_all(bind=_engine)
except Exception as _e:
    print(f"[intelligence] create_all skipped: {_e}", flush=True)


# ── DB dependency ─────────────────────────────────────────────────────────────
def get_db():
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Hook / thumbnail classifiers ──────────────────────────────────────────────

def _classify_hook(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ("secret", "truth", "nobody")):
        return "curiosity"
    if any(k in t for k in ("mistake", "warning", "avoid")):
        return "fear"
    if any(k in t for k in ("shocking", "insane", "unbelievable")):
        return "shock"
    if any(k in t for k in ("how i", "my story", "i tried")):
        return "story"
    if any(k in t for k in ("why", "what if", "how to")):
        return "question"
    if any(k in t for k in ("%", "million", "billion", "#1")):
        return "data_point"
    return "question"


def _classify_thumbnail(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ("breaking", "alert")):
        return "news_style"
    if any(k in t for k in ("rich", "wealth", "expensive")):
        return "luxury"
    words = title.strip().split()
    if len(words) < 5:
        return "minimal"
    if len(words) > 10:
        return "text_heavy"
    return "face"


def _iso_duration_to_seconds(iso: str) -> int:
    """Convert ISO 8601 duration (PT4M13S) to total seconds."""
    import re
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    h, mn, s = (int(x or 0) for x in m.groups())
    return h * 3600 + mn * 60 + s


# ── 1. Trend Intelligence ─────────────────────────────────────────────────────

async def scrape_niche_trends(
    niche_id: int, niche_name: str, query: str, db: Session
) -> List[Dict[str, Any]]:
    if not YOUTUBE_API_KEY:
        return []

    published_after = (
        datetime.now(timezone.utc) - timedelta(days=30)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    async with httpx.AsyncClient(timeout=20) as client:
        search_resp = await client.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "key": YOUTUBE_API_KEY,
                "q": query,
                "type": "video",
                "order": "viewCount",
                "publishedAfter": published_after,
                "maxResults": 15,
                "part": "snippet",
                "relevanceLanguage": "en",
            },
        )
        search_resp.raise_for_status()
        search_data = search_resp.json()

    items = search_data.get("items", [])
    if not items:
        return []

    video_ids = [i["id"]["videoId"] for i in items if "videoId" in i.get("id", {})]

    async with httpx.AsyncClient(timeout=20) as client:
        stats_resp = await client.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "key": YOUTUBE_API_KEY,
                "id": ",".join(video_ids),
                "part": "statistics,contentDetails",
            },
        )
        stats_resp.raise_for_status()
        stats_data = stats_resp.json()

    stats_map: Dict[str, dict] = {}
    for item in stats_data.get("items", []):
        vid = item["id"]
        s = item.get("statistics", {})
        cd = item.get("contentDetails", {})
        stats_map[vid] = {
            "views": int(s.get("viewCount", 0)),
            "likes": int(s.get("likeCount", 0)),
            "duration": _iso_duration_to_seconds(cd.get("duration", "")),
        }

    results = []
    for item in items:
        vid_id = item.get("id", {}).get("videoId")
        if not vid_id:
            continue
        snippet = item.get("snippet", {})
        title   = snippet.get("title", "")
        channel = snippet.get("channelTitle", "")
        pub_raw = snippet.get("publishedAt", "")
        try:
            pub_at = datetime.fromisoformat(pub_raw.replace("Z", "+00:00"))
        except Exception:
            pub_at = None

        st = stats_map.get(vid_id, {})
        views = st.get("views", 0)
        likes = st.get("likes", 0)
        dur   = st.get("duration", 0)

        trend_score = min(100.0, views / 10000 * 20 + likes / 1000 * 5)
        hook_style  = _classify_hook(title)
        thumb_style = _classify_thumbnail(title)

        # Upsert by video_id
        existing = _x(
            db,
            "SELECT id FROM trend_videos WHERE video_id = :vid",
            {"vid": vid_id},
        ).fetchone()

        if existing:
            _x(
                db,
                """UPDATE trend_videos SET views=:v, likes=:l, trend_score=:ts,
                   hook_style=:hs, thumbnail_style=:tm, duration_seconds=:dur
                   WHERE video_id=:vid""",
                {
                    "v": views, "l": likes, "ts": trend_score,
                    "hs": hook_style, "tm": thumb_style,
                    "dur": dur, "vid": vid_id,
                },
            )
        else:
            _x(
                db,
                """INSERT INTO trend_videos
                   (niche_id,niche_name,title,channel,video_id,views,likes,
                    published_at,trend_score,hook_style,thumbnail_style,duration_seconds,created_at)
                   VALUES (:ni,:nn,:ti,:ch,:vid,:v,:l,:pa,:ts,:hs,:tm,:dur,:ca)""",
                {
                    "ni": niche_id, "nn": niche_name, "ti": title,
                    "ch": channel, "vid": vid_id, "v": views, "l": likes,
                    "pa": pub_at, "ts": trend_score, "hs": hook_style,
                    "tm": thumb_style, "dur": dur, "ca": datetime.utcnow(),
                },
            )

        db.commit()
        results.append({
            "video_id": vid_id, "title": title, "channel": channel,
            "views": views, "likes": likes, "trend_score": trend_score,
            "hook_style": hook_style, "thumbnail_style": thumb_style,
            "duration_seconds": dur, "published_at": pub_raw,
        })

    return results


# ── 2. Idea Scoring ───────────────────────────────────────────────────────────

async def score_idea_competitiveness(
    title: str, niche_name: str, db: Session
) -> Dict[str, float]:
    if not YOUTUBE_API_KEY:
        return {
            "search_demand": 55.0,
            "competition": 40.0,
            "trend_score": 60.0,
            "opportunity_score": 58.0,
        }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "key": YOUTUBE_API_KEY,
                "q": title,
                "type": "video",
                "order": "relevance",
                "maxResults": 10,
                "part": "snippet",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    items = data.get("items", [])
    result_count = len(items)

    # Proxy for demand: more results = more demand (capped at 100)
    search_demand = min(100.0, result_count * 10.0)
    # Proxy for competition: channel age / how many results returned (simplified)
    competition   = min(100.0, result_count * 8.0)
    trend_score   = 50.0  # default without extra signals

    if items:
        # Use view signals from first few results to weight trend_score
        vid_ids = [i["id"].get("videoId") for i in items if i.get("id", {}).get("videoId")][:5]
        if vid_ids:
            async with httpx.AsyncClient(timeout=15) as client:
                sr = await client.get(
                    "https://www.googleapis.com/youtube/v3/videos",
                    params={
                        "key": YOUTUBE_API_KEY,
                        "id": ",".join(vid_ids),
                        "part": "statistics",
                    },
                )
                sr.raise_for_status()
                sdata = sr.json()
            total_views = sum(
                int(i.get("statistics", {}).get("viewCount", 0))
                for i in sdata.get("items", [])
            )
            trend_score = min(100.0, total_views / 50000 * 10)

    opportunity_score = (
        search_demand * 0.4 + trend_score * 0.4 + (100 - competition) * 0.2
    )

    return {
        "search_demand": round(search_demand, 1),
        "competition": round(competition, 1),
        "trend_score": round(trend_score, 1),
        "opportunity_score": round(opportunity_score, 1),
    }


# ── 3. Hook Performance Updater ───────────────────────────────────────────────

def update_hook_performance(
    hook_type: str, niche_id: int,
    retention_pct: float, ctr: float, views: int, db: Session
) -> None:
    row = _x(
        db,
        "SELECT id, video_count, avg_retention_pct, avg_ctr, avg_views "
        "FROM hook_performance WHERE hook_type=:ht AND niche_id=:ni",
        {"ht": hook_type, "ni": niche_id},
    ).fetchone()

    now = datetime.utcnow()
    if row:
        c = row.video_count
        new_ret = (row.avg_retention_pct * c + retention_pct) / (c + 1)
        new_ctr = (row.avg_ctr * c + ctr) / (c + 1)
        new_views = int((row.avg_views * c + views) / (c + 1))
        _x(
            db,
            """UPDATE hook_performance
               SET video_count=:vc, avg_retention_pct=:r, avg_ctr=:ct, avg_views=:v, updated_at=:ua
               WHERE hook_type=:ht AND niche_id=:ni""",
            {
                "vc": c + 1, "r": new_ret, "ct": new_ctr, "v": new_views,
                "ua": now, "ht": hook_type, "ni": niche_id,
            },
        )
    else:
        _x(
            db,
            """INSERT INTO hook_performance
               (hook_type,niche_id,video_count,avg_retention_pct,avg_ctr,avg_views,updated_at)
               VALUES (:ht,:ni,1,:r,:ct,:v,:ua)""",
            {
                "ht": hook_type, "ni": niche_id,
                "r": retention_pct, "ct": ctr, "v": views, "ua": now,
            },
        )
    db.commit()


# ── 4. Thumbnail Performance Updater ─────────────────────────────────────────

def update_thumbnail_performance(
    style: str, niche_id: int, ctr: float, impressions: int, db: Session
) -> None:
    row = _x(
        db,
        "SELECT id, video_count, avg_ctr, avg_impressions "
        "FROM thumbnail_performance WHERE style=:st AND niche_id=:ni",
        {"st": style, "ni": niche_id},
    ).fetchone()

    now = datetime.utcnow()
    if row:
        c = row.video_count
        new_ctr  = (row.avg_ctr * c + ctr) / (c + 1)
        new_impr = int((row.avg_impressions * c + impressions) / (c + 1))
        _x(
            db,
            """UPDATE thumbnail_performance
               SET video_count=:vc, avg_ctr=:ct, avg_impressions=:imp, updated_at=:ua
               WHERE style=:st AND niche_id=:ni""",
            {
                "vc": c + 1, "ct": new_ctr, "imp": new_impr,
                "ua": now, "st": style, "ni": niche_id,
            },
        )
    else:
        _x(
            db,
            """INSERT INTO thumbnail_performance
               (style,niche_id,video_count,avg_ctr,avg_impressions,updated_at)
               VALUES (:st,:ni,1,:ct,:imp,:ua)""",
            {
                "st": style, "ni": niche_id,
                "ct": ctr, "imp": impressions, "ua": now,
            },
        )
    db.commit()


# ── 5. Best Hook for Niche ────────────────────────────────────────────────────

def get_best_hook_type(niche_id: int, db: Session) -> str:
    row = _x(
        db,
        """SELECT hook_type FROM hook_performance
           WHERE niche_id=:ni AND video_count >= 3
           ORDER BY avg_retention_pct DESC LIMIT 1""",
        {"ni": niche_id},
    ).fetchone()
    return row.hook_type if row else "curiosity"


# ── 6. Best Thumbnail Style for Niche ────────────────────────────────────────

def get_best_thumbnail_style(niche_id: int, db: Session) -> str:
    row = _x(
        db,
        """SELECT style FROM thumbnail_performance
           WHERE niche_id=:ni AND video_count >= 3
           ORDER BY avg_ctr DESC LIMIT 1""",
        {"ni": niche_id},
    ).fetchone()
    return row.style if row else "text_heavy"


# ── 7. Financial Controller ───────────────────────────────────────────────────

def record_job_cost(
    job_id: str, user_id: int, niche_id: int,
    openai_cost: float, rendering_seconds: float, db: Session
) -> Dict[str, float]:
    rendering_cost = rendering_seconds * 0.00001   # Hetzner CPU estimate
    total          = openai_cost + rendering_cost

    _x(
        db,
        """INSERT INTO video_job_costs
           (job_id,user_id,niche_id,openai_cost_usd,rendering_seconds,total_cost_usd,created_at)
           VALUES (:jid,:uid,:ni,:oc,:rs,:tc,:ca)""",
        {
            "jid": job_id, "uid": user_id, "ni": niche_id,
            "oc": openai_cost, "rs": rendering_seconds,
            "tc": total, "ca": datetime.utcnow(),
        },
    )

    # Update niche portfolio total cost
    _x(
        db,
        """UPDATE niche_portfolio
           SET total_cost_usd = total_cost_usd + :tc, updated_at=:ua
           WHERE niche_id=:ni""",
        {"tc": total, "ua": datetime.utcnow(), "ni": niche_id},
    )
    db.commit()
    return {"total_cost_usd": total, "rendering_cost_usd": rendering_cost}


# ── 8. CEO Agent ──────────────────────────────────────────────────────────────

async def run_ceo_agent(db: Session) -> str:
    since = datetime.utcnow() - timedelta(days=7)

    # Analytics: last 7 days
    analytics_rows = _x(
        db,
        """SELECT snapshot_type, SUM(views) as views, AVG(ctr) as ctr,
                  AVG(avg_view_percentage) as retention, SUM(revenue_usd) as revenue
           FROM analytics_snapshots WHERE collected_at >= :since
           GROUP BY snapshot_type ORDER BY snapshot_type""",
        {"since": since},
    ).fetchall()

    analytics_summary = "\n".join(
        f"  [{r.snapshot_type}] views={r.views} ctr={r.ctr:.2f}% "
        f"retention={r.retention:.1f}% revenue=${r.revenue:.2f}"
        for r in analytics_rows
    ) or "  No analytics data for past 7 days."

    # Niche portfolio
    portfolio_rows = _x(
        db,
        "SELECT niche_name, status, priority_score, profit_margin_pct, videos_per_day "
        "FROM niche_portfolio ORDER BY priority_score DESC",
        {},
    ).fetchall()

    portfolio_summary = "\n".join(
        f"  {r.niche_name}: status={r.status} priority={r.priority_score:.1f} "
        f"margin={r.profit_margin_pct:.1f}% vpd={r.videos_per_day}"
        for r in portfolio_rows
    ) or "  No niches in portfolio."

    # Top performing videos (7 days)
    top_videos = _x(
        db,
        """SELECT vm.title, vm.niche_name, vm.score_label, a.views, a.revenue_usd
           FROM analytics_snapshots a
           JOIN video_memory vm ON vm.id = a.video_memory_id
           WHERE a.collected_at >= :since
           ORDER BY a.views DESC LIMIT 5""",
        {"since": since},
    ).fetchall()

    top_summary = "\n".join(
        f"  [{r.score_label}] {r.title} ({r.niche_name}) — {r.views} views, ${r.revenue_usd:.2f}"
        for r in top_videos
    ) or "  No video data."

    # Worst performers
    worst_videos = _x(
        db,
        """SELECT vm.title, vm.niche_name, vm.score_label, a.views
           FROM analytics_snapshots a
           JOIN video_memory vm ON vm.id = a.video_memory_id
           WHERE a.collected_at >= :since
           ORDER BY a.views ASC LIMIT 5""",
        {"since": since},
    ).fetchall()

    worst_summary = "\n".join(
        f"  [{r.score_label}] {r.title} ({r.niche_name}) — {r.views} views"
        for r in worst_videos
    ) or "  No data."

    # Cost vs revenue
    cost_row = _x(
        db,
        "SELECT SUM(total_cost_usd) as tc FROM video_job_costs WHERE created_at >= :since",
        {"since": since},
    ).fetchone()
    total_cost = float(cost_row.tc or 0)

    rev_row = _x(
        db,
        "SELECT SUM(revenue_usd) as tr FROM analytics_snapshots WHERE collected_at >= :since",
        {"since": since},
    ).fetchone()
    total_rev = float(rev_row.tr or 0)

    context = f"""=== WEEKLY PERFORMANCE DATA ===
Date: {datetime.utcnow().strftime('%Y-%m-%d')}

ANALYTICS (last 7 days):
{analytics_summary}

COST vs REVENUE:
  Total cost:    ${total_cost:.4f}
  Total revenue: ${total_rev:.4f}
  Net:           ${total_rev - total_cost:.4f}

NICHE PORTFOLIO:
{portfolio_summary}

TOP PERFORMERS:
{top_summary}

WORST PERFORMERS:
{worst_summary}
"""

    if not OPENAI_API_KEY:
        content = f"[CEO Report — {datetime.utcnow().date()}]\n\nNO OPENAI_API_KEY configured.\n\nRaw data:\n{context}"
    else:
        payload = {
            "model": "anthropic/claude-opus-4-5",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are the CEO of an autonomous YouTube media company. "
                        "You are data-driven, direct, and strategic. "
                        "You never sugarcoat underperformance and always give specific, actionable decisions."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"{context}\n\n"
                        "Review the above performance data and produce:\n"
                        "1) What worked this week\n"
                        "2) What failed\n"
                        "3) Specific actions for next week\n"
                        "4) Which niches to scale/pause/kill\n\n"
                        "Be specific and data-driven. Format your response clearly with numbered sections."
                    ),
                },
            ],
            "max_tokens": 1500,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{OPENAI_API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["choices"][0]["message"]["content"]

    # Parse decisions (simple extraction — look for keywords)
    decisions: List[str] = []
    for line in content.splitlines():
        lower = line.lower()
        for kw in ("scale", "pause", "kill", "terminate", "double down", "stop"):
            if kw in lower and line.strip():
                decisions.append(line.strip())
                break

    _x(
        db,
        """INSERT INTO ceo_reports (report_date, content, decisions, created_at)
           VALUES (:rd,:ct,:dc,:ca)""",
        {
            "rd": date.today(),
            "ct": content,
            "dc": json.dumps(decisions),
            "ca": datetime.utcnow(),
        },
    )
    db.commit()
    return content


# ── 9. Portfolio Manager ──────────────────────────────────────────────────────

def evaluate_portfolio(db: Session) -> List[Dict[str, Any]]:
    niches = _x(db, "SELECT * FROM niche_portfolio", {}).fetchall()
    summary = []

    for n in niches:
        niche_id = n.niche_id

        rev_row = _x(
            db,
            """SELECT COALESCE(SUM(a.revenue_usd), 0) as total_rev
               FROM analytics_snapshots a
               JOIN video_memory vm ON vm.id = a.video_memory_id
               WHERE vm.niche_id = :ni""",
            {"ni": niche_id},
        ).fetchone()
        total_revenue = float(rev_row.total_rev or 0)

        cost_row = _x(
            db,
            "SELECT COALESCE(SUM(total_cost_usd), 0) as tc FROM video_job_costs WHERE niche_id=:ni",
            {"ni": niche_id},
        ).fetchone()
        total_cost = float(cost_row.tc or 0)

        profit_margin = 0.0
        if total_revenue > 0:
            profit_margin = (total_revenue - total_cost) / total_revenue * 100

        # Winner rate
        winner_row = _x(
            db,
            """SELECT
                 COUNT(*) FILTER (WHERE score_label='winner') as winners,
                 COUNT(*) as total
               FROM video_memory WHERE niche_id=:ni""",
            {"ni": niche_id},
        ).fetchone()
        total_vids  = int(winner_row.total or 0)
        winner_rate = (int(winner_row.winners or 0) / total_vids * 100) if total_vids else 0

        priority_score = (
            winner_rate * 0.5 +
            profit_margin * 0.3 +
            (n.videos_per_day * 5)
        )

        if priority_score > 60:
            new_status = "scaling"
        elif priority_score > 30:
            new_status = "active"
        elif priority_score > 10:
            new_status = "watch"
        else:
            new_status = "paused"

        now = datetime.utcnow()
        _x(
            db,
            """UPDATE niche_portfolio SET
               total_revenue_usd=:tr, total_cost_usd=:tc,
               profit_margin_pct=:pm, priority_score=:ps,
               status=:st, last_evaluated_at=:le, updated_at=:ua
               WHERE niche_id=:ni""",
            {
                "tr": total_revenue, "tc": total_cost,
                "pm": profit_margin, "ps": priority_score,
                "st": new_status, "le": now, "ua": now, "ni": niche_id,
            },
        )

        traffic_light = (
            "green" if new_status == "scaling" else
            "yellow" if new_status in ("active", "watch") else
            "red"
        )

        summary.append({
            "niche_id": niche_id,
            "niche_name": n.niche_name,
            "status": new_status,
            "traffic_light": traffic_light,
            "priority_score": round(priority_score, 2),
            "profit_margin_pct": round(profit_margin, 2),
            "total_revenue_usd": round(total_revenue, 4),
            "total_cost_usd": round(total_cost, 4),
            "videos_per_day": n.videos_per_day,
            "winner_rate_pct": round(winner_rate, 1),
        })

    db.commit()
    return summary


# ── 10. Shorts Generator ──────────────────────────────────────────────────────

async def generate_shorts_clip(video_path: str, output_path: str) -> str:
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-t", "58",
        "-vf", "crop=ih*9/16:ih,scale=1080:1920",
        "-vf", (
            "crop=ih*9/16:ih,scale=1080:1920,"
            "drawtext=text='WATCH FULL VIDEO 👆':fontsize=48:fontcolor=white:"
            "x=(w-text_w)/2:y=h-100:box=1:boxcolor=black@0.5:boxborderw=10"
        ),
        "-c:v", "libx264",
        "-preset", "fast",
        "-c:a", "aac",
        output_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {stderr.decode()[-500:]}")
    return output_path


# ── Scheduler jobs ────────────────────────────────────────────────────────────

def _trend_scraping_job():
    db = _SessionLocal()
    try:
        rows = _x(db, "SELECT niche_id, niche_name FROM niche_portfolio WHERE status != 'terminated'", {}).fetchall()
        for row in rows:
            asyncio.run(scrape_niche_trends(row.niche_id, row.niche_name, row.niche_name, db))
    except Exception as e:
        print(f"[intelligence] trend_scraping_job error: {e}", flush=True)
    finally:
        db.close()


def _ceo_agent_job():
    db = _SessionLocal()
    try:
        asyncio.run(run_ceo_agent(db))
    except Exception as e:
        print(f"[intelligence] ceo_agent_job error: {e}", flush=True)
    finally:
        db.close()


def _portfolio_eval_job():
    db = _SessionLocal()
    try:
        evaluate_portfolio(db)
    except Exception as e:
        print(f"[intelligence] portfolio_eval_job error: {e}", flush=True)
    finally:
        db.close()


def register_intelligence_scheduler(app):
    """
    Hook into APScheduler instance created by autonomy.py (imported first).
    Falls back to its own scheduler if none is found.
    """
    try:
        from autonomy import _scheduler as scheduler
    except ImportError:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        scheduler = AsyncIOScheduler()

    @app.on_event("startup")
    async def _start_intelligence_jobs():
        if not scheduler.running:
            scheduler.start()

        scheduler.add_job(
            _trend_scraping_job,
            trigger="cron",
            hour=5, minute=0,
            id="intelligence_trend_scraping",
            replace_existing=True,
        )
        scheduler.add_job(
            _ceo_agent_job,
            trigger="cron",
            hour=5, minute=30,
            id="intelligence_ceo_agent",
            replace_existing=True,
        )
        scheduler.add_job(
            _portfolio_eval_job,
            trigger="cron",
            hour=5, minute=45,
            id="intelligence_portfolio_eval",
            replace_existing=True,
        )
        print("[intelligence] Scheduler jobs registered.", flush=True)


# ── FastAPI Router ────────────────────────────────────────────────────────────

intelligence_router = APIRouter(prefix="/intelligence", tags=["intelligence"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class ScrapeTrendsRequest(BaseModel):
    niche_id: int
    niche_name: str
    query: str


class ScoreIdeaRequest(BaseModel):
    title: str
    niche_name: str


class UpdatePortfolioRequest(BaseModel):
    status: Optional[str] = None
    videos_per_day: Optional[int] = None


# ── Routes ────────────────────────────────────────────────────────────────────

@intelligence_router.get("/trends/{niche_id}")
def get_trends_for_niche(niche_id: int, db: Session = Depends(get_db)):
    rows = _x(
        db,
        """SELECT id, niche_id, niche_name, title, channel, video_id, views, likes,
                  published_at, trend_score, hook_style, thumbnail_style,
                  duration_seconds, created_at
           FROM trend_videos WHERE niche_id=:ni ORDER BY trend_score DESC LIMIT 50""",
        {"ni": niche_id},
    ).fetchall()
    return [dict(r._mapping) for r in rows]


@intelligence_router.post("/trends/scrape")
async def manual_trend_scrape(body: ScrapeTrendsRequest, db: Session = Depends(get_db)):
    results = await scrape_niche_trends(body.niche_id, body.niche_name, body.query, db)
    return {"scraped": len(results), "videos": results}


@intelligence_router.get("/trends/top")
def get_top_trends(limit: int = 20, db: Session = Depends(get_db)):
    rows = _x(
        db,
        """SELECT id, niche_id, niche_name, title, channel, video_id, views,
                  likes, trend_score, hook_style, thumbnail_style, created_at
           FROM trend_videos ORDER BY trend_score DESC LIMIT :lim""",
        {"lim": limit},
    ).fetchall()
    return [dict(r._mapping) for r in rows]


@intelligence_router.get("/hooks/{niche_id}")
def get_hook_performance(niche_id: int, db: Session = Depends(get_db)):
    rows = _x(
        db,
        """SELECT id, hook_type, niche_id, video_count, avg_retention_pct,
                  avg_ctr, avg_views, updated_at
           FROM hook_performance WHERE niche_id=:ni ORDER BY avg_retention_pct DESC""",
        {"ni": niche_id},
    ).fetchall()
    return [dict(r._mapping) for r in rows]


@intelligence_router.get("/thumbnails/{niche_id}")
def get_thumbnail_performance(niche_id: int, db: Session = Depends(get_db)):
    rows = _x(
        db,
        """SELECT id, style, niche_id, video_count, avg_ctr, avg_impressions, updated_at
           FROM thumbnail_performance WHERE niche_id=:ni ORDER BY avg_ctr DESC""",
        {"ni": niche_id},
    ).fetchall()
    return [dict(r._mapping) for r in rows]


@intelligence_router.get("/ceo/latest")
def get_latest_ceo_report(db: Session = Depends(get_db)):
    row = _x(
        db,
        "SELECT id, report_date, content, decisions, created_at FROM ceo_reports ORDER BY created_at DESC LIMIT 1",
        {},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No CEO reports found")
    return dict(row._mapping)


@intelligence_router.post("/ceo/run")
async def trigger_ceo_agent(db: Session = Depends(get_db)):
    content = await run_ceo_agent(db)
    return {"ok": True, "report_preview": content[:500]}


@intelligence_router.get("/portfolio")
def get_portfolio(db: Session = Depends(get_db)):
    summary = evaluate_portfolio(db)
    return {"niches": summary, "count": len(summary)}


@intelligence_router.put("/portfolio/{niche_id}")
def update_portfolio_niche(
    niche_id: int,
    body: UpdatePortfolioRequest,
    db: Session = Depends(get_db),
):
    row = _x(
        db,
        "SELECT id FROM niche_portfolio WHERE niche_id=:ni",
        {"ni": niche_id},
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Niche not found")

    updates: Dict[str, Any] = {"ua": datetime.utcnow(), "ni": niche_id}
    set_clauses = ["updated_at=:ua"]

    if body.status is not None:
        valid_statuses = {"active", "scaling", "paused", "terminated", "watch"}
        if body.status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"status must be one of {valid_statuses}")
        updates["st"] = body.status
        set_clauses.append("status=:st")

    if body.videos_per_day is not None:
        if body.videos_per_day < 0:
            raise HTTPException(status_code=400, detail="videos_per_day must be >= 0")
        updates["vpd"] = body.videos_per_day
        set_clauses.append("videos_per_day=:vpd")

    _x(
        db,
        f"UPDATE niche_portfolio SET {', '.join(set_clauses)} WHERE niche_id=:ni",
        updates,
    )
    db.commit()
    return {"ok": True, "niche_id": niche_id}


@intelligence_router.get("/costs")
def get_cost_summary(db: Session = Depends(get_db)):
    rows = _x(
        db,
        """SELECT niche_id,
                  COUNT(*) as job_count,
                  SUM(openai_cost_usd) as openai_total,
                  SUM(rendering_seconds) as rendering_total_sec,
                  SUM(total_cost_usd) as grand_total
           FROM video_job_costs
           GROUP BY niche_id
           ORDER BY grand_total DESC""",
        {},
    ).fetchall()
    return [dict(r._mapping) for r in rows]


@intelligence_router.post("/score-idea")
async def score_idea(body: ScoreIdeaRequest, db: Session = Depends(get_db)):
    scores = await score_idea_competitiveness(body.title, body.niche_name, db)
    return scores
