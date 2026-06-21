"""
Autonomy layer — YouTube publish, analytics, scoring, decisions, feedback, scheduler.
Imported by main.py:  app.include_router(autonomy_router); register_scheduler(app)
"""
import os, json, sys, asyncio, hashlib, re
from datetime import datetime, timedelta, timezone
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, JSON as SAJSON,
    create_engine, ForeignKey
)
from sqlalchemy.orm import declarative_base, Session, sessionmaker
from pydantic import BaseModel

# ── Shared Base (same engine as main.py) ─────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/handholding")
_engine = create_engine(DATABASE_URL)
_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
Base = declarative_base()

def get_db():
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── Env ───────────────────────────────────────────────────────────────────────
YOUTUBE_CLIENT_ID     = os.getenv("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "")
YOUTUBE_REDIRECT_URI  = os.getenv("YOUTUBE_REDIRECT_URI", "http://localhost:5000/youtube/auth/callback")
OPENAI_API_KEY        = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE       = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

# ── New DB Models ─────────────────────────────────────────────────────────────

class VideoMemory(Base):
    """Central autonomy record for every generated video."""
    __tablename__ = "video_memory"
    id                  = Column(Integer, primary_key=True)
    user_id             = Column(Integer, nullable=False, default=1)
    video_generation_id = Column(Integer, nullable=True)   # FK to video_generations.id
    niche_id            = Column(Integer, nullable=True)
    niche_name          = Column(String, nullable=True)
    title               = Column(String, nullable=False)
    framework           = Column(String, nullable=True)
    hook                = Column(Text, nullable=True)
    script_preview      = Column(Text, nullable=True)       # first 500 chars
    local_video_path    = Column(String, nullable=True)
    local_thumbnail_path= Column(String, nullable=True)
    # YouTube
    youtube_video_id    = Column(String, nullable=True)
    youtube_url         = Column(String, nullable=True)
    youtube_channel_id  = Column(String, nullable=True)
    uploaded_at         = Column(DateTime, nullable=True)
    went_live_at        = Column(DateTime, nullable=True)
    scheduled_for       = Column(DateTime, nullable=True)
    # Status lifecycle
    status              = Column(String, default="generated")
    # generated → safety_review → upload_queue → uploading → uploaded → live → archived
    # Safety
    safety_passed       = Column(Boolean, nullable=True)
    safety_flags        = Column(SAJSON, nullable=True)     # list of flag strings
    safety_checked_at   = Column(DateTime, nullable=True)
    # Scoring
    score_label         = Column(String, nullable=True)
    # winner | packaging_problem | retention_problem | loser | needs_more_data
    score_data          = Column(SAJSON, nullable=True)     # raw metric snapshot used for scoring
    scored_at           = Column(DateTime, nullable=True)
    # Decision
    decision            = Column(String, nullable=True)
    # make_more_like_this | change_title_style | change_thumbnail_style |
    # improve_hook | adjust_length | pause_niche | double_down | wait
    decision_reason     = Column(Text, nullable=True)
    decided_at          = Column(DateTime, nullable=True)
    # Metadata
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AnalyticsSnapshot(Base):
    """Time-series analytics snapshots per video at 24h, 72h, 7d, 30d."""
    __tablename__ = "analytics_snapshots"
    id               = Column(Integer, primary_key=True)
    video_memory_id  = Column(Integer, nullable=False)      # FK video_memory.id
    youtube_video_id = Column(String, nullable=False)
    snapshot_type    = Column(String, nullable=False)       # 24h | 72h | 7d | 30d
    collected_at     = Column(DateTime, default=datetime.utcnow)
    views            = Column(Integer, default=0)
    impressions      = Column(Integer, default=0)
    ctr              = Column(Float, default=0.0)           # click-through rate %
    avg_view_duration_sec  = Column(Float, default=0.0)
    avg_view_percentage    = Column(Float, default=0.0)     # retention %
    watch_time_hours       = Column(Float, default=0.0)
    likes            = Column(Integer, default=0)
    comments         = Column(Integer, default=0)
    shares           = Column(Integer, default=0)
    subscribers_gained = Column(Integer, default=0)
    revenue_usd      = Column(Float, default=0.0)
    raw              = Column(SAJSON, nullable=True)         # full API response


class ContentDecision(Base):
    """Logged decisions from the decision engine."""
    __tablename__ = "content_decisions"
    id              = Column(Integer, primary_key=True)
    user_id         = Column(Integer, default=1)
    video_memory_id = Column(Integer, nullable=True)
    niche_id        = Column(Integer, nullable=True)
    decision_type   = Column(String, nullable=False)
    reason          = Column(Text, nullable=True)
    metadata        = Column(SAJSON, nullable=True)
    applied         = Column(Boolean, default=False)
    applied_at      = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)


class AutopilotConfig(Base):
    """Per-user autopilot settings."""
    __tablename__ = "autopilot_config"
    id                    = Column(Integer, primary_key=True)
    user_id               = Column(Integer, unique=True, default=1)
    mode                  = Column(String, default="assisted")  # assisted | full
    uploads_per_day       = Column(Integer, default=1)
    generate_per_day      = Column(Integer, default=3)
    analytics_schedule    = Column(String, default="6:00")       # UTC HH:MM
    generation_schedule   = Column(String, default="7:00")       # UTC HH:MM
    safety_gate_enabled   = Column(Boolean, default=True)
    min_safety_score      = Column(Integer, default=70)          # 0-100
    active                = Column(Boolean, default=False)
    last_run_at           = Column(DateTime, nullable=True)
    created_at            = Column(DateTime, default=datetime.utcnow)
    updated_at            = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Create autonomy tables
Base.metadata.create_all(bind=_engine)

# ── YouTube OAuth ─────────────────────────────────────────────────────────────

def _yt_client_config():
    return {
        "web": {
            "client_id": YOUTUBE_CLIENT_ID,
            "client_secret": YOUTUBE_CLIENT_SECRET,
            "redirect_uris": [YOUTUBE_REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

YOUTUBE_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

def _build_flow(state=None):
    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_config(
        _yt_client_config(),
        scopes=YOUTUBE_SCOPES,
        state=state,
    )
    flow.redirect_uri = YOUTUBE_REDIRECT_URI
    return flow


def _load_creds(db: Session, user_id: int):
    """Load stored OAuth credentials for a user."""
    from google.oauth2.credentials import Credentials
    # Use platform_credentials table (already in main schema)
    row = db.execute(
        "SELECT access_token, refresh_token, expires_at, channel_id "
        "FROM platform_credentials WHERE user_id=:uid AND platform='youtube' LIMIT 1",
        {"uid": user_id}
    ).fetchone()
    if not row:
        return None, None
    creds = Credentials(
        token=row[0],
        refresh_token=row[1],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YOUTUBE_CLIENT_ID,
        client_secret=YOUTUBE_CLIENT_SECRET,
        scopes=YOUTUBE_SCOPES,
    )
    return creds, row[3]  # creds, channel_id


def _save_creds(db: Session, user_id: int, creds, channel_id: str = None):
    """Upsert YouTube credentials into platform_credentials."""
    expires = creds.expiry if creds.expiry else datetime.utcnow() + timedelta(hours=1)
    existing = db.execute(
        "SELECT id FROM platform_credentials WHERE user_id=:uid AND platform='youtube'",
        {"uid": user_id}
    ).fetchone()
    if existing:
        db.execute(
            "UPDATE platform_credentials SET access_token=:at, refresh_token=:rt, "
            "expires_at=:ex, channel_id=COALESCE(:cid, channel_id), updated_at=NOW() "
            "WHERE user_id=:uid AND platform='youtube'",
            {"at": creds.token, "rt": creds.refresh_token, "ex": expires,
             "cid": channel_id, "uid": user_id}
        )
    else:
        db.execute(
            "INSERT INTO platform_credentials (user_id, platform, access_token, refresh_token, expires_at, channel_id, created_at, updated_at) "
            "VALUES (:uid, 'youtube', :at, :rt, :ex, :cid, NOW(), NOW())",
            {"uid": user_id, "at": creds.token, "rt": creds.refresh_token,
             "ex": expires, "cid": channel_id}
        )
    db.commit()


async def get_youtube_client(user_id: int, db: Session):
    """Return authenticated YouTube API client, refreshing token if needed."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request as GAuthRequest
    from googleapiclient.discovery import build

    creds, channel_id = _load_creds(db, user_id)
    if not creds:
        raise HTTPException(status_code=401, detail="YouTube not connected. Visit /youtube/auth/url to connect.")

    if creds.expired and creds.refresh_token:
        creds.refresh(GAuthRequest())
        _save_creds(db, user_id, creds, channel_id)

    return build("youtube", "v3", credentials=creds), channel_id


async def get_youtube_analytics_client(user_id: int, db: Session):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request as GAuthRequest
    from googleapiclient.discovery import build

    creds, _ = _load_creds(db, user_id)
    if not creds:
        raise HTTPException(status_code=401, detail="YouTube not connected.")
    if creds.expired and creds.refresh_token:
        creds.refresh(GAuthRequest())
        _save_creds(db, user_id, creds)
    return build("youtubeAnalytics", "v2", credentials=creds)


# ── YouTube Publisher ─────────────────────────────────────────────────────────

async def upload_video_to_youtube(
    user_id: int,
    video_path: str,
    title: str,
    description: str,
    tags: list,
    thumbnail_path: str = None,
    scheduled_publish_at: datetime = None,
    db: Session = None,
) -> str:
    """Upload MP4 to YouTube. Returns youtube_video_id."""
    from googleapiclient.http import MediaFileUpload

    youtube, _ = await get_youtube_client(user_id, db)

    privacy = "private" if scheduled_publish_at else "public"
    status_body = {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}
    if scheduled_publish_at:
        status_body["publishAt"] = scheduled_publish_at.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "tags": (tags if isinstance(tags, list) else [])[:500],
            "categoryId": "22",
            "defaultLanguage": "en",
        },
        "status": status_body,
    }

    media = MediaFileUpload(video_path, mimetype="video/mp4", chunksize=10 * 1024 * 1024, resumable=True)

    loop = asyncio.get_event_loop()

    def _do_upload():
        req = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)
        response = None
        while response is None:
            _, response = req.next_chunk()
        return response

    response = await loop.run_in_executor(None, _do_upload)
    yt_video_id = response["id"]
    print(f"[YT] Uploaded: {yt_video_id}", flush=True)

    if thumbnail_path and Path(thumbnail_path).exists():
        try:
            from googleapiclient.http import MediaFileUpload as MFU
            def _set_thumb():
                youtube.thumbnails().set(
                    videoId=yt_video_id,
                    media_body=MFU(thumbnail_path, mimetype="image/jpeg")
                ).execute()
            await loop.run_in_executor(None, _set_thumb)
        except Exception as e:
            print(f"[YT] Thumbnail failed: {e}", flush=True)

    return yt_video_id


# ── Analytics Collector ───────────────────────────────────────────────────────

async def collect_video_analytics(
    memory_id: int,
    youtube_video_id: str,
    snapshot_type: str,
    user_id: int,
    db: Session,
) -> dict:
    """Collect analytics for one video. snapshot_type: 24h | 72h | 7d | 30d"""
    days = {"24h": 1, "72h": 3, "7d": 7, "30d": 30}.get(snapshot_type, 7)
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)

    youtube, _ = await get_youtube_client(user_id, db)
    yt_analytics = await get_youtube_analytics_client(user_id, db)

    # Video stats from Data API
    vid_resp = youtube.videos().list(part="statistics,contentDetails", id=youtube_video_id).execute()
    stats = vid_resp["items"][0]["statistics"] if vid_resp.get("items") else {}

    # Detailed metrics from Analytics API
    metrics = "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage," \
              "subscribersGained,likes,comments,shares,impressions,impressionClickThroughRate"
    try:
        ar = yt_analytics.reports().query(
            ids="channel==MINE",
            startDate=str(start_date),
            endDate=str(end_date),
            metrics=metrics,
            dimensions="video",
            filters=f"video=={youtube_video_id}",
        ).execute()
        cols = [c["name"] for c in ar.get("columnHeaders", [])]
        row_data = ar.get("rows", [[]])[0] if ar.get("rows") else []
        row = dict(zip(cols, row_data)) if row_data else {}
    except Exception as e:
        print(f"[ANALYTICS] Analytics API error: {e}", flush=True)
        row = {}

    snap = {
        "views": int(stats.get("viewCount", 0)),
        "likes": int(stats.get("likeCount", 0)),
        "comments": int(stats.get("commentCount", 0)),
        "impressions": int(row.get("impressions", 0)),
        "ctr": float(row.get("impressionClickThroughRate", 0)),
        "avg_view_duration_sec": float(row.get("averageViewDuration", 0)),
        "avg_view_percentage": float(row.get("averageViewPercentage", 0)),
        "watch_time_hours": float(row.get("estimatedMinutesWatched", 0)) / 60,
        "subscribers_gained": int(row.get("subscribersGained", 0)),
        "shares": int(row.get("shares", 0)),
        "revenue_usd": 0.0,
    }

    # Save snapshot
    existing = db.execute(
        "SELECT id FROM analytics_snapshots WHERE video_memory_id=:mid AND snapshot_type=:st",
        {"mid": memory_id, "st": snapshot_type}
    ).fetchone()
    if existing:
        db.execute(
            "UPDATE analytics_snapshots SET views=:v, impressions=:i, ctr=:c, "
            "avg_view_duration_sec=:ad, avg_view_percentage=:ap, watch_time_hours=:wh, "
            "likes=:l, comments=:co, shares=:s, subscribers_gained=:sg, "
            "collected_at=NOW(), raw=:raw WHERE id=:id",
            {**snap, "raw": json.dumps(snap), "id": existing[0]}
        )
    else:
        db.execute(
            "INSERT INTO analytics_snapshots "
            "(video_memory_id, youtube_video_id, snapshot_type, collected_at, views, impressions, ctr, "
            "avg_view_duration_sec, avg_view_percentage, watch_time_hours, likes, comments, shares, "
            "subscribers_gained, revenue_usd, raw) "
            "VALUES (:mid, :yvid, :st, NOW(), :v, :i, :c, :ad, :ap, :wh, :l, :co, :s, :sg, 0, :raw)",
            {**snap, "mid": memory_id, "yvid": youtube_video_id,
             "st": snapshot_type, "raw": json.dumps(snap)}
        )
    db.commit()
    return snap


# ── Scoring Engine ────────────────────────────────────────────────────────────

def score_video(snapshots: dict) -> dict:
    """
    Classify a video given analytics snapshots.
    snapshots: {"24h": {...}, "72h": {...}, "7d": {...}, "30d": {...}}
    Returns: {"label": str, "confidence": float, "reasons": [str]}
    """
    best = snapshots.get("7d") or snapshots.get("72h") or snapshots.get("24h") or {}
    views = best.get("views", 0)
    ctr   = best.get("ctr", 0)            # %
    ret   = best.get("avg_view_percentage", 0)  # %
    snap_count = sum(1 for v in snapshots.values() if v)

    if views < 100 or snap_count < 1:
        return {"label": "needs_more_data", "confidence": 1.0,
                "reasons": [f"Only {views} views — wait for more data"]}

    reasons = []
    if views >= 5000 and ctr >= 6 and ret >= 50:
        label = "winner"
        reasons = [f"{views} views, {ctr:.1f}% CTR, {ret:.0f}% retention — breakout"]
    elif views >= 1000 and ctr >= 4 and ret >= 45:
        label = "winner"
        reasons = [f"{views} views, {ctr:.1f}% CTR, {ret:.0f}% retention — solid performer"]
    elif ctr < 3 and ret >= 45:
        label = "packaging_problem"
        reasons = [f"Low CTR ({ctr:.1f}%) but good retention ({ret:.0f}%) — title or thumbnail not working"]
    elif ctr >= 4 and ret < 30:
        label = "retention_problem"
        reasons = [f"Good CTR ({ctr:.1f}%) but low retention ({ret:.0f}%) — hook or content not delivering"]
    elif views < 200 and ctr < 2 and ret < 25:
        label = "loser"
        reasons = [f"{views} views, {ctr:.1f}% CTR, {ret:.0f}% retention — not resonating"]
    else:
        label = "needs_more_data"
        reasons = [f"{views} views — mixed signals, need more time"]

    confidence = min(1.0, views / 1000) if snap_count >= 2 else 0.6
    return {"label": label, "confidence": round(confidence, 2), "reasons": reasons}


# ── Decision Engine ───────────────────────────────────────────────────────────

DECISION_MAP = {
    "winner": [
        ("double_down", "This topic cluster is performing — generate 3 more in same niche"),
        ("make_more_like_this", "Replicate hook style, framework, and thumbnail approach"),
    ],
    "packaging_problem": [
        ("change_title_style", "Test power-word or curiosity-gap title on next video"),
        ("change_thumbnail_style", "Test face/emotion or high-contrast thumbnail variant"),
    ],
    "retention_problem": [
        ("improve_hook", "Rewrite opening 30 seconds — current hook isn't holding attention"),
        ("shorten_video", "Try 5-7 min instead of 10 — audience dropping after hook"),
    ],
    "loser": [
        ("pause_niche", "This topic cluster has 3+ losers — pause and reassess angle"),
    ],
    "needs_more_data": [
        ("wait", "Collect 7-day data before deciding"),
    ],
}


def decide_next_action(score_label: str, niche_history: list) -> list:
    """
    Return ordered list of decisions.
    niche_history: list of score_labels for recent videos in same niche.
    """
    decisions = list(DECISION_MAP.get(score_label, [("wait", "No clear signal yet")]))

    loser_streak = sum(1 for l in niche_history[-5:] if l == "loser")
    if loser_streak >= 3:
        decisions = [("pause_niche", f"{loser_streak} consecutive losers — niche needs fresh angle")]

    winner_streak = sum(1 for l in niche_history[-5:] if l == "winner")
    if winner_streak >= 2:
        decisions = [("double_down", f"{winner_streak} winners in a row — double output in this niche")] + decisions

    return decisions


# ── Safety Gate ───────────────────────────────────────────────────────────────

SAFETY_BLOCKED_PATTERNS = [
    (r'\bcure\b|\bcures\b|\btreat\s+cancer\b', "health_claim", "Unverified medical claim"),
    (r'\bguaranteed\s+returns?\b|\bguaranteed\s+profit\b', "financial_claim", "Guaranteed financial returns"),
    (r'\bget\s+rich\s+quick\b', "financial_claim", "Get-rich-quick scheme language"),
    (r'\bstop\s+taking\s+your\s+medication\b|\bdon.t\s+take\s+medicine\b', "medical_advice", "Dangerous medical advice"),
    (r'\b(kill|shoot|bomb|attack)\s+(yourself|people|school|government)\b', "violence", "Violent content"),
    (r'\bchild\s+abuse\b|\bminor\s+porn\b|\bpedo\b', "csam", "CSAM — immediate block"),
]


async def safety_check(title: str, script: str, description: str) -> dict:
    """
    Run safety gate before upload.
    Returns: {"passed": bool, "score": int (0-100), "flags": [...], "block": bool}
    """
    flags = []
    block = False
    full_text = f"{title}\n{description}\n{script[:3000]}"

    for pattern, category, reason in SAFETY_BLOCKED_PATTERNS:
        if re.search(pattern, full_text, re.IGNORECASE):
            flags.append({"category": category, "reason": reason, "severity": "high"})
            if category in ("csam", "violence"):
                block = True

    # AI-assisted check for nuanced issues
    if OPENAI_API_KEY and not block:
        try:
            import httpx
            prompt = (
                f"Review this YouTube video for policy violations. Title: {title[:200]}\n"
                f"Script excerpt: {script[:800]}\n\n"
                "Check for: copyright-risky music/brand references, misleading health/finance claims, "
                "restricted topics, duplicate/low-effort content.\n"
                "Return JSON: {\"issues\": [{\"type\": str, \"severity\": \"low|medium|high\", \"description\": str}], \"overall_risk\": \"low|medium|high\"}"
            )
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{OPENAI_API_BASE}/chat/completions",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "response_format": {"type": "json_object"},
                        "max_tokens": 500,
                    }
                )
                if resp.status_code == 200:
                    ai_result = json.loads(resp.json()["choices"][0]["message"]["content"])
                    for issue in ai_result.get("issues", []):
                        if issue.get("severity") in ("medium", "high"):
                            flags.append({
                                "category": issue.get("type", "ai_detected"),
                                "reason": issue.get("description", ""),
                                "severity": issue.get("severity", "medium"),
                            })
        except Exception as e:
            print(f"[SAFETY] AI check error: {e}", flush=True)

    high_flags = [f for f in flags if f["severity"] == "high"]
    score = max(0, 100 - len(flags) * 15 - len(high_flags) * 25)
    passed = score >= 60 and not block

    return {"passed": passed, "score": score, "flags": flags, "block": block}


# ── Feedback Loop ─────────────────────────────────────────────────────────────

def get_feedback_context(niche_id: int, db: Session) -> str:
    """
    Build a feedback context string to inject into script generation prompts.
    Shows winners to emulate and losers to avoid.
    """
    winners = db.execute(
        "SELECT title, framework, decision_reason FROM video_memory "
        "WHERE niche_id=:nid AND score_label='winner' ORDER BY created_at DESC LIMIT 3",
        {"nid": niche_id}
    ).fetchall()

    losers = db.execute(
        "SELECT title, framework, decision_reason FROM video_memory "
        "WHERE niche_id=:nid AND score_label IN ('loser','retention_problem') "
        "ORDER BY created_at DESC LIMIT 3",
        {"nid": niche_id}
    ).fetchall()

    if not winners and not losers:
        return ""

    lines = ["## Performance Feedback from Previous Videos\n"]
    if winners:
        lines.append("### What worked (emulate these patterns):")
        for w in winners:
            lines.append(f"- \"{w[0]}\" [{w[1]} framework] — {w[2] or 'high performer'}")
    if losers:
        lines.append("\n### What didn't work (avoid these patterns):")
        for l in losers:
            lines.append(f"- \"{l[0]}\" [{l[1]} framework] — {l[2] or 'poor performance'}")
    lines.append("\nUse these insights to make the new script more likely to succeed.\n")
    return "\n".join(lines)


# ── Scheduler ─────────────────────────────────────────────────────────────────

from apscheduler.schedulers.asyncio import AsyncIOScheduler
scheduler = AsyncIOScheduler(timezone="UTC")


async def _run_analytics_collection():
    """Collect analytics for all live videos at appropriate intervals."""
    db = _SessionLocal()
    try:
        now = datetime.utcnow()
        live_videos = db.execute(
            "SELECT id, youtube_video_id, user_id, went_live_at FROM video_memory "
            "WHERE status='live' AND youtube_video_id IS NOT NULL"
        ).fetchall()

        for vid in live_videos:
            mem_id, yt_id, user_id, went_live = vid
            if not went_live:
                continue
            age_hours = (now - went_live).total_seconds() / 3600

            to_collect = []
            existing = db.execute(
                "SELECT snapshot_type FROM analytics_snapshots WHERE video_memory_id=:mid",
                {"mid": mem_id}
            ).fetchall()
            existing_types = {r[0] for r in existing}

            if age_hours >= 24 and "24h" not in existing_types:
                to_collect.append("24h")
            if age_hours >= 72 and "72h" not in existing_types:
                to_collect.append("72h")
            if age_hours >= 168 and "7d" not in existing_types:
                to_collect.append("7d")
            if age_hours >= 720 and "30d" not in existing_types:
                to_collect.append("30d")

            for snap_type in to_collect:
                try:
                    snap = await collect_video_analytics(mem_id, yt_id, snap_type, user_id, db)
                    print(f"[SCHEDULER] Collected {snap_type} for {yt_id}: {snap['views']} views", flush=True)
                    # Score after collecting
                    all_snaps = {}
                    for st in ["24h", "72h", "7d", "30d"]:
                        row = db.execute(
                            "SELECT views,ctr,avg_view_percentage FROM analytics_snapshots "
                            "WHERE video_memory_id=:mid AND snapshot_type=:st ORDER BY collected_at DESC LIMIT 1",
                            {"mid": mem_id, "st": st}
                        ).fetchone()
                        if row:
                            all_snaps[st] = {"views": row[0], "ctr": row[1], "avg_view_percentage": row[2]}
                    score = score_video(all_snaps)
                    db.execute(
                        "UPDATE video_memory SET score_label=:sl, score_data=:sd, scored_at=NOW() WHERE id=:id",
                        {"sl": score["label"], "sd": json.dumps(score), "id": mem_id}
                    )
                    # Log decision
                    history = db.execute(
                        "SELECT score_label FROM video_memory WHERE niche_id=("
                        "SELECT niche_id FROM video_memory WHERE id=:id) "
                        "AND scored_at IS NOT NULL ORDER BY scored_at DESC LIMIT 5",
                        {"id": mem_id}
                    ).fetchall()
                    niche_labels = [r[0] for r in history if r[0]]
                    decisions = decide_next_action(score["label"], niche_labels)
                    for d_type, d_reason in decisions[:1]:
                        existing_d = db.execute(
                            "SELECT id FROM content_decisions WHERE video_memory_id=:mid AND decision_type=:dt",
                            {"mid": mem_id, "dt": d_type}
                        ).fetchone()
                        if not existing_d:
                            db.execute(
                                "INSERT INTO content_decisions (user_id, video_memory_id, niche_id, decision_type, reason, created_at) "
                                "VALUES (:uid, :mid, (SELECT niche_id FROM video_memory WHERE id=:mid2), :dt, :r, NOW())",
                                {"uid": user_id, "mid": mem_id, "mid2": mem_id, "dt": d_type, "r": d_reason}
                            )
                    db.execute(
                        "UPDATE video_memory SET decision=:d, decision_reason=:dr, decided_at=NOW() WHERE id=:id",
                        {"d": decisions[0][0] if decisions else "wait",
                         "dr": decisions[0][1] if decisions else "", "id": mem_id}
                    )
                    db.commit()
                except Exception as e:
                    print(f"[SCHEDULER] Analytics error for {yt_id}: {e}", flush=True)
    finally:
        db.close()


async def _run_daily_generation():
    """Full autopilot: generate + safety check + upload batch."""
    db = _SessionLocal()
    try:
        config = db.execute(
            "SELECT mode, uploads_per_day, generate_per_day, safety_gate_enabled FROM autopilot_config WHERE user_id=1"
        ).fetchone()
        if not config or config[0] != "full":
            return

        mode, uploads_per_day, generate_per_day, safety_enabled = config
        print(f"[AUTOPILOT] Full autopilot running — generate={generate_per_day}, upload={uploads_per_day}", flush=True)

        # Queue pending videos for upload
        pending = db.execute(
            "SELECT id, local_video_path, local_thumbnail_path, title, niche_id FROM video_memory "
            "WHERE status='upload_queue' AND safety_passed=true ORDER BY created_at ASC LIMIT :n",
            {"n": uploads_per_day}
        ).fetchall()

        for vid in pending:
            mem_id, vid_path, thumb_path, title, niche_id = vid
            if not vid_path or not Path(vid_path).exists():
                continue
            try:
                # Get description from content_decisions or script
                desc_row = db.execute(
                    "SELECT youtube_description FROM asset_packs ap "
                    "JOIN scripts s ON ap.script_id=s.id "
                    "JOIN video_ideas vi ON s.idea_id=vi.id "
                    "JOIN video_memory vm ON vm.niche_id=vi.niche_id "
                    "WHERE vm.id=:mid LIMIT 1",
                    {"mid": mem_id}
                ).fetchone()
                description = desc_row[0] if desc_row else f"Watch this video about {title}"
                yt_id = await upload_video_to_youtube(
                    user_id=1, video_path=vid_path, title=title,
                    description=description, tags=[],
                    thumbnail_path=thumb_path, db=db
                )
                db.execute(
                    "UPDATE video_memory SET youtube_video_id=:yid, youtube_url=:url, "
                    "status='uploaded', uploaded_at=NOW(), went_live_at=NOW() WHERE id=:id",
                    {"yid": yt_id, "url": f"https://youtube.com/watch?v={yt_id}", "id": mem_id}
                )
                db.commit()
                print(f"[AUTOPILOT] Uploaded {title} → {yt_id}", flush=True)
            except Exception as e:
                print(f"[AUTOPILOT] Upload failed for memory {mem_id}: {e}", flush=True)

        db.execute(
            "UPDATE autopilot_config SET last_run_at=NOW() WHERE user_id=1"
        )
        db.commit()
    finally:
        db.close()


def register_scheduler(app):
    """Hook APScheduler into FastAPI startup/shutdown."""
    @app.on_event("startup")
    async def _start():
        if not scheduler.running:
            scheduler.add_job(_run_analytics_collection, "cron", hour=6, minute=0, id="analytics_daily")
            scheduler.add_job(_run_daily_generation, "cron", hour=7, minute=0, id="generation_daily")
            scheduler.start()
            print("[SCHEDULER] Started — analytics@06:00 UTC, generation@07:00 UTC", flush=True)

    @app.on_event("shutdown")
    async def _stop():
        if scheduler.running:
            scheduler.shutdown(wait=False)


# ── FastAPI Router ────────────────────────────────────────────────────────────

autonomy_router = APIRouter(tags=["autonomy"])

# ── YouTube Auth ──────────────────────────────────────────────────────────────

@autonomy_router.get("/youtube/auth/url")
def youtube_auth_url():
    """Get YouTube OAuth URL. Redirect the user's browser here."""
    if not YOUTUBE_CLIENT_ID or not YOUTUBE_CLIENT_SECRET:
        raise HTTPException(status_code=400, detail="YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET not set")
    flow = _build_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    return {"auth_url": auth_url}


@autonomy_router.get("/youtube/auth/callback")
async def youtube_auth_callback(code: str, state: str = None, db: Session = Depends(get_db)):
    """Google redirects here after user grants permission."""
    flow = _build_flow(state=state)
    flow.fetch_token(code=code)
    creds = flow.credentials

    from googleapiclient.discovery import build
    yt = build("youtube", "v3", credentials=creds)
    channel_resp = yt.channels().list(part="snippet", mine=True).execute()
    channel_id = channel_resp["items"][0]["id"] if channel_resp.get("items") else None

    _save_creds(db, user_id=1, creds=creds, channel_id=channel_id)
    return {"status": "connected", "channel_id": channel_id}


@autonomy_router.get("/youtube/auth/status")
def youtube_auth_status(db: Session = Depends(get_db)):
    row = db.execute(
        "SELECT channel_id, expires_at FROM platform_credentials WHERE user_id=1 AND platform='youtube'",
    ).fetchone()
    if not row:
        return {"connected": False}
    return {"connected": True, "channel_id": row[0], "expires_at": str(row[1])}


# ── Publisher ─────────────────────────────────────────────────────────────────

class UploadRequest(BaseModel):
    video_memory_id: int
    scheduled_for: Optional[str] = None   # ISO datetime string


@autonomy_router.post("/youtube/upload")
async def trigger_upload(req: UploadRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Upload a video in the queue to YouTube (async)."""
    mem = db.execute(
        "SELECT id, local_video_path, local_thumbnail_path, title, status FROM video_memory WHERE id=:id",
        {"id": req.video_memory_id}
    ).fetchone()
    if not mem:
        raise HTTPException(status_code=404, detail="VideoMemory not found")

    mem_id, vid_path, thumb_path, title, status = mem
    if not vid_path or not Path(vid_path).exists():
        raise HTTPException(status_code=400, detail=f"Video file not found: {vid_path}")

    scheduled_at = None
    if req.scheduled_for:
        scheduled_at = datetime.fromisoformat(req.scheduled_for.replace("Z", "+00:00"))

    db.execute("UPDATE video_memory SET status='uploading' WHERE id=:id", {"id": mem_id})
    db.commit()

    async def _upload():
        _db = _SessionLocal()
        try:
            desc_row = _db.execute(
                "SELECT ap.youtube_description FROM asset_packs ap "
                "JOIN scripts s ON ap.script_id=s.id "
                "JOIN video_ideas vi ON s.idea_id=vi.id "
                "WHERE vi.niche_id=(SELECT niche_id FROM video_memory WHERE id=:mid) LIMIT 1",
                {"mid": mem_id}
            ).fetchone()
            description = desc_row[0] if desc_row else f"Watch: {title}"

            yt_id = await upload_video_to_youtube(
                user_id=1, video_path=vid_path, title=title,
                description=description, tags=[],
                thumbnail_path=thumb_path, scheduled_publish_at=scheduled_at, db=_db
            )
            _db.execute(
                "UPDATE video_memory SET youtube_video_id=:yid, youtube_url=:url, "
                "status=:st, uploaded_at=NOW(), went_live_at=:wl, scheduled_for=:sf WHERE id=:id",
                {"yid": yt_id,
                 "url": f"https://youtube.com/watch?v={yt_id}",
                 "st": "uploaded" if not scheduled_at else "scheduled",
                 "wl": scheduled_at or datetime.utcnow(),
                 "sf": scheduled_at,
                 "id": mem_id}
            )
            _db.commit()
        except Exception as e:
            _db.execute(
                "UPDATE video_memory SET status='upload_failed' WHERE id=:id", {"id": mem_id}
            )
            _db.commit()
            print(f"[UPLOAD] Failed: {e}", flush=True)
        finally:
            _db.close()

    background_tasks.add_task(_upload)
    return {"status": "uploading", "video_memory_id": mem_id}


@autonomy_router.get("/youtube/queue")
def get_upload_queue(db: Session = Depends(get_db)):
    """All videos pending upload approval."""
    rows = db.execute(
        "SELECT id, title, niche_name, status, safety_passed, safety_flags, "
        "score_label, decision, local_video_path, created_at "
        "FROM video_memory WHERE status IN ('safety_review','upload_queue','uploading','upload_failed') "
        "ORDER BY created_at DESC LIMIT 50"
    ).fetchall()
    return [
        {
            "id": r[0], "title": r[1], "niche": r[2], "status": r[3],
            "safety_passed": r[4], "safety_flags": r[5], "score_label": r[6],
            "decision": r[7], "has_video": bool(r[8] and Path(r[8]).exists()),
            "created_at": str(r[9]),
        }
        for r in rows
    ]


@autonomy_router.post("/youtube/queue/{memory_id}/approve")
def approve_upload(memory_id: int, db: Session = Depends(get_db)):
    db.execute(
        "UPDATE video_memory SET status='upload_queue' WHERE id=:id", {"id": memory_id}
    )
    db.commit()
    return {"status": "approved", "id": memory_id}


@autonomy_router.post("/youtube/queue/{memory_id}/reject")
def reject_upload(memory_id: int, db: Session = Depends(get_db)):
    db.execute(
        "UPDATE video_memory SET status='rejected' WHERE id=:id", {"id": memory_id}
    )
    db.commit()
    return {"status": "rejected", "id": memory_id}


# ── Safety ────────────────────────────────────────────────────────────────────

class SafetyCheckRequest(BaseModel):
    title: str
    script: str = ""
    description: str = ""
    video_memory_id: Optional[int] = None


@autonomy_router.post("/safety/check")
async def run_safety_check(req: SafetyCheckRequest, db: Session = Depends(get_db)):
    result = await safety_check(req.title, req.script, req.description)
    if req.video_memory_id:
        db.execute(
            "UPDATE video_memory SET safety_passed=:p, safety_flags=:f, safety_checked_at=NOW(), "
            "status=:st WHERE id=:id",
            {"p": result["passed"], "f": json.dumps(result["flags"]),
             "st": "upload_queue" if result["passed"] else "safety_review",
             "id": req.video_memory_id}
        )
        db.commit()
    return result


# ── Analytics ─────────────────────────────────────────────────────────────────

@autonomy_router.post("/analytics/collect/{memory_id}")
async def trigger_analytics(memory_id: int, snapshot_type: str = "7d", db: Session = Depends(get_db)):
    row = db.execute(
        "SELECT youtube_video_id, user_id FROM video_memory WHERE id=:id", {"id": memory_id}
    ).fetchone()
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail="No YouTube video ID for this memory")
    result = await collect_video_analytics(memory_id, row[0], snapshot_type, row[1] or 1, db)
    return {"snapshot_type": snapshot_type, **result}


@autonomy_router.get("/analytics/video/{memory_id}")
def get_video_analytics(memory_id: int, db: Session = Depends(get_db)):
    snaps = db.execute(
        "SELECT snapshot_type, views, impressions, ctr, avg_view_duration_sec, "
        "avg_view_percentage, watch_time_hours, likes, comments, subscribers_gained, collected_at "
        "FROM analytics_snapshots WHERE video_memory_id=:mid ORDER BY collected_at",
        {"mid": memory_id}
    ).fetchall()
    return {
        "memory_id": memory_id,
        "snapshots": [
            {"type": r[0], "views": r[1], "impressions": r[2], "ctr": r[3],
             "avg_view_duration_sec": r[4], "avg_view_percentage": r[5],
             "watch_time_hours": r[6], "likes": r[7], "comments": r[8],
             "subscribers_gained": r[9], "collected_at": str(r[10])}
            for r in snaps
        ]
    }


# ── Scoring ───────────────────────────────────────────────────────────────────

@autonomy_router.post("/scoring/run")
def run_scoring(db: Session = Depends(get_db)):
    """Score all uploaded videos that have analytics."""
    memories = db.execute(
        "SELECT id FROM video_memory WHERE status IN ('uploaded','live') AND youtube_video_id IS NOT NULL"
    ).fetchall()
    scored = []
    for (mem_id,) in memories:
        snaps_raw = db.execute(
            "SELECT snapshot_type, views, ctr, avg_view_percentage FROM analytics_snapshots "
            "WHERE video_memory_id=:mid", {"mid": mem_id}
        ).fetchall()
        snaps = {r[0]: {"views": r[1], "ctr": r[2], "avg_view_percentage": r[3]} for r in snaps_raw}
        if not snaps:
            continue
        score = score_video(snaps)
        db.execute(
            "UPDATE video_memory SET score_label=:sl, score_data=:sd, scored_at=NOW() WHERE id=:id",
            {"sl": score["label"], "sd": json.dumps(score), "id": mem_id}
        )
        scored.append({"id": mem_id, **score})
    db.commit()
    return {"scored": len(scored), "results": scored}


@autonomy_router.get("/scoring/leaderboard")
def get_leaderboard(db: Session = Depends(get_db)):
    rows = db.execute(
        "SELECT vm.id, vm.title, vm.niche_name, vm.score_label, vm.decision, "
        "vm.youtube_url, vm.went_live_at, "
        "snap.views, snap.ctr, snap.avg_view_percentage "
        "FROM video_memory vm "
        "LEFT JOIN analytics_snapshots snap ON snap.video_memory_id=vm.id "
        "  AND snap.snapshot_type=(SELECT snapshot_type FROM analytics_snapshots "
        "    WHERE video_memory_id=vm.id ORDER BY collected_at DESC LIMIT 1) "
        "WHERE vm.score_label IS NOT NULL "
        "ORDER BY snap.views DESC NULLS LAST LIMIT 50"
    ).fetchall()
    return [
        {"id": r[0], "title": r[1], "niche": r[2], "label": r[3], "decision": r[4],
         "url": r[5], "went_live": str(r[6]) if r[6] else None,
         "views": r[7], "ctr": r[8], "retention": r[9]}
        for r in rows
    ]


# ── Autopilot Config ──────────────────────────────────────────────────────────

class AutopilotConfigUpdate(BaseModel):
    mode: Optional[str] = None              # assisted | full
    uploads_per_day: Optional[int] = None
    generate_per_day: Optional[int] = None
    safety_gate_enabled: Optional[bool] = None
    active: Optional[bool] = None


@autonomy_router.get("/autopilot/config")
def get_autopilot_config(db: Session = Depends(get_db)):
    row = db.execute(
        "SELECT mode, uploads_per_day, generate_per_day, safety_gate_enabled, "
        "active, last_run_at FROM autopilot_config WHERE user_id=1"
    ).fetchone()
    if not row:
        db.execute(
            "INSERT INTO autopilot_config (user_id, mode, uploads_per_day, generate_per_day, "
            "safety_gate_enabled, active, created_at, updated_at) "
            "VALUES (1,'assisted',1,3,true,false,NOW(),NOW())"
        )
        db.commit()
        return {"mode": "assisted", "uploads_per_day": 1, "generate_per_day": 3,
                "safety_gate_enabled": True, "active": False, "last_run_at": None}
    return {"mode": row[0], "uploads_per_day": row[1], "generate_per_day": row[2],
            "safety_gate_enabled": row[3], "active": row[4], "last_run_at": str(row[5]) if row[5] else None}


@autonomy_router.put("/autopilot/config")
def update_autopilot_config(req: AutopilotConfigUpdate, db: Session = Depends(get_db)):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    set_clause = ", ".join(f"{k}=:{k}" for k in updates)
    updates["updated_at"] = datetime.utcnow()
    db.execute(
        f"INSERT INTO autopilot_config (user_id, mode, uploads_per_day, generate_per_day, "
        f"safety_gate_enabled, active, created_at, updated_at) "
        f"VALUES (1,'assisted',1,3,true,false,NOW(),NOW()) "
        f"ON CONFLICT (user_id) DO UPDATE SET {set_clause}, updated_at=:updated_at",
        updates
    )
    db.commit()
    return {"status": "updated", **updates}


@autonomy_router.post("/autopilot/run")
async def manual_autopilot_run(background_tasks: BackgroundTasks):
    """Manually trigger one full autonomy cycle."""
    background_tasks.add_task(_run_analytics_collection)
    background_tasks.add_task(_run_daily_generation)
    return {"status": "triggered", "jobs": ["analytics_collection", "daily_generation"]}


@autonomy_router.get("/autopilot/status")
def get_autopilot_status(db: Session = Depends(get_db)):
    config = db.execute(
        "SELECT mode, active, last_run_at FROM autopilot_config WHERE user_id=1"
    ).fetchone()
    total_vids = db.execute("SELECT COUNT(*) FROM video_memory WHERE user_id=1").fetchone()[0]
    live_vids  = db.execute("SELECT COUNT(*) FROM video_memory WHERE user_id=1 AND status='live'").fetchone()[0]
    uploaded   = db.execute("SELECT COUNT(*) FROM video_memory WHERE user_id=1 AND status IN ('uploaded','live')").fetchone()[0]
    pending    = db.execute("SELECT COUNT(*) FROM video_memory WHERE user_id=1 AND status='upload_queue'").fetchone()[0]
    winners    = db.execute("SELECT COUNT(*) FROM video_memory WHERE user_id=1 AND score_label='winner'").fetchone()[0]
    return {
        "mode": config[0] if config else "assisted",
        "active": config[1] if config else False,
        "last_run_at": str(config[2]) if config and config[2] else None,
        "scheduler_running": scheduler.running,
        "stats": {
            "total_generated": total_vids,
            "uploaded": uploaded,
            "live": live_vids,
            "pending_upload": pending,
            "winners": winners,
        }
    }


# ── Decisions ─────────────────────────────────────────────────────────────────

@autonomy_router.get("/decisions/pending")
def get_pending_decisions(db: Session = Depends(get_db)):
    rows = db.execute(
        "SELECT cd.id, cd.decision_type, cd.reason, cd.created_at, "
        "vm.title, vm.niche_name, vm.score_label "
        "FROM content_decisions cd "
        "LEFT JOIN video_memory vm ON vm.id=cd.video_memory_id "
        "WHERE cd.applied=false ORDER BY cd.created_at DESC LIMIT 30"
    ).fetchall()
    return [
        {"id": r[0], "decision": r[1], "reason": r[2], "created_at": str(r[3]),
         "video_title": r[4], "niche": r[5], "score_label": r[6]}
        for r in rows
    ]


@autonomy_router.post("/decisions/{decision_id}/apply")
def apply_decision(decision_id: int, db: Session = Depends(get_db)):
    db.execute(
        "UPDATE content_decisions SET applied=true, applied_at=NOW() WHERE id=:id",
        {"id": decision_id}
    )
    db.commit()
    return {"status": "applied"}


# ── Reporting ─────────────────────────────────────────────────────────────────

@autonomy_router.get("/reporting/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    total    = db.execute("SELECT COUNT(*) FROM video_memory WHERE user_id=1").fetchone()[0]
    uploaded = db.execute("SELECT COUNT(*) FROM video_memory WHERE user_id=1 AND youtube_video_id IS NOT NULL").fetchone()[0]
    winners  = db.execute("SELECT COUNT(*) FROM video_memory WHERE user_id=1 AND score_label='winner'").fetchone()[0]
    losers   = db.execute("SELECT COUNT(*) FROM video_memory WHERE user_id=1 AND score_label='loser'").fetchone()[0]

    top5 = db.execute(
        "SELECT vm.title, vm.niche_name, vm.score_label, vm.youtube_url, snap.views, snap.ctr "
        "FROM video_memory vm "
        "LEFT JOIN analytics_snapshots snap ON snap.video_memory_id=vm.id "
        "WHERE vm.score_label='winner' ORDER BY snap.views DESC NULLS LAST LIMIT 5"
    ).fetchall()

    worst5 = db.execute(
        "SELECT vm.title, vm.niche_name, vm.score_label, vm.youtube_url, snap.views, snap.ctr "
        "FROM video_memory vm "
        "LEFT JOIN analytics_snapshots snap ON snap.video_memory_id=vm.id "
        "WHERE vm.score_label='loser' ORDER BY snap.views ASC NULLS LAST LIMIT 5"
    ).fetchall()

    niches = db.execute(
        "SELECT niche_name, COUNT(*) as total, "
        "SUM(CASE WHEN score_label='winner' THEN 1 ELSE 0 END) as wins "
        "FROM video_memory WHERE user_id=1 AND niche_name IS NOT NULL "
        "GROUP BY niche_name ORDER BY wins DESC LIMIT 10"
    ).fetchall()

    decisions = db.execute(
        "SELECT decision_type, COUNT(*) FROM content_decisions WHERE applied=false "
        "GROUP BY decision_type ORDER BY COUNT(*) DESC"
    ).fetchall()

    total_views = db.execute(
        "SELECT COALESCE(SUM(views),0) FROM analytics_snapshots snap "
        "JOIN video_memory vm ON vm.id=snap.video_memory_id WHERE vm.user_id=1"
    ).fetchone()[0]

    avg_ctr = db.execute(
        "SELECT COALESCE(AVG(ctr),0) FROM analytics_snapshots snap "
        "JOIN video_memory vm ON vm.id=snap.video_memory_id WHERE vm.user_id=1"
    ).fetchone()[0]

    return {
        "summary": {
            "videos_generated": total,
            "videos_uploaded": uploaded,
            "winners": winners,
            "losers": losers,
            "total_views": int(total_views),
            "avg_ctr_pct": round(float(avg_ctr), 2),
        },
        "top_performers": [
            {"title": r[0], "niche": r[1], "label": r[2], "url": r[3],
             "views": r[4], "ctr": r[5]}
            for r in top5
        ],
        "worst_performers": [
            {"title": r[0], "niche": r[1], "label": r[2], "url": r[3],
             "views": r[4], "ctr": r[5]}
            for r in worst5
        ],
        "winning_niches": [
            {"niche": r[0], "total_videos": r[1], "winners": r[2]}
            for r in niches
        ],
        "pending_actions": [
            {"action": r[0], "count": r[1]}
            for r in decisions
        ],
    }
