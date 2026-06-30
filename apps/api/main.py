import PIL.Image
if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
import re
import asyncio
import uuid
from fastapi import FastAPI, HTTPException, Depends, Form, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime
import os
from dotenv import load_dotenv
import httpx
import json
import sys

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/handholding")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
YOUTUBE_CREDENTIALS = os.getenv("YOUTUBE_CREDENTIALS", "")

# OpenAI pricing per 1K tokens (as of 2024)
PRICING = {
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4-turbo-2024-04-09": {"input": 0.01, "output": 0.03},
}

# Global cost tracker for the session
session_costs = {"total": 0.0, "calls": []}

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
Base = declarative_base()

# Database Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)
    name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Niche(Base):
    __tablename__ = "niches"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    audience = Column(String)
    monetization_angle = Column(String)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class CompetitorInput(Base):
    __tablename__ = "competitor_inputs"
    id = Column(Integer, primary_key=True)
    niche_id = Column(Integer, ForeignKey("niches.id"))
    title_or_url = Column(String)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class VideoIdea(Base):
    __tablename__ = "video_ideas"
    id = Column(Integer, primary_key=True)
    niche_id = Column(Integer, ForeignKey("niches.id"))
    title = Column(String)
    reason = Column(Text)
    demand_score = Column(Float, default=0)
    clickability_score = Column(Float, default=0)
    monetization_score = Column(Float, default=0)
    production_ease_score = Column(Float, default=0)
    trust_risk_score = Column(Float, default=0)
    repeatability_score = Column(Float, default=0)
    total_score = Column(Float, default=0)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

class Script(Base):
    __tablename__ = "scripts"
    id = Column(Integer, primary_key=True)
    idea_id = Column(Integer, ForeignKey("video_ideas.id"))
    hook = Column(Text)
    full_script = Column(Text)
    fact_check_flags = Column(Text)
    unsupported_claims = Column(Text)
    cta = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class AssetPack(Base):
    __tablename__ = "asset_packs"
    id = Column(Integer, primary_key=True)
    script_id = Column(Integer, ForeignKey("scripts.id"))
    thumbnail_prompt = Column(Text)
    alternate_titles = Column(Text)
    broll_list = Column(Text)
    voiceover_instructions = Column(Text)
    editor_brief = Column(Text)
    youtube_description = Column(Text)
    pinned_comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    related_type = Column(String)
    related_id = Column(Integer)
    task_text = Column(String)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

class Voice(Base):
    __tablename__ = "voices"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    file_path = Column(String)
    duration = Column(Integer, default=0)  # seconds
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ContentBatch(Base):
    __tablename__ = "content_batches"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    count = Column(Integer, default=10)
    schedule_start = Column(String)
    schedule_frequency = Column(String, default="daily")
    status = Column(String, default="queued")
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# Pydantic Schemas
class NicheCreate(BaseModel):
    name: str
    audience: str
    monetization_angle: str
    notes: str

class NicheResponse(BaseModel):
    id: int
    name: str
    audience: str
    monetization_angle: str
    notes: str

class CompetitorCreate(BaseModel):
    niche_id: int
    title_or_url: str
    notes: str

class CompetitorResponse(BaseModel):
    id: int
    niche_id: int
    title_or_url: str
    notes: str

class VideoIdeaResponse(BaseModel):
    id: int
    niche_id: int
    title: str
    reason: str
    demand_score: float
    clickability_score: float
    monetization_score: float
    production_ease_score: float
    trust_risk_score: float
    repeatability_score: float
    total_score: float
    status: str

class ScriptResponse(BaseModel):
    id: int
    idea_id: int
    hook: str
    full_script: str
    fact_check_flags: str
    unsupported_claims: str
    cta: str

class AssetPackResponse(BaseModel):
    id: int
    script_id: int
    thumbnail_prompt: str
    alternate_titles: str
    broll_list: str
    voiceover_instructions: str
    editor_brief: str
    youtube_description: str
    pinned_comment: str

class NextActionResponse(BaseModel):
    task_text: str
    related_type: str
    related_id: int

# FastAPI App
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

VOICE_ID_FILE = "/opt/handholding-engine/elevenlabs_voice_id.txt"

def get_stored_voice_id() -> str:
    try:
        if os.path.exists(VOICE_ID_FILE):
            return open(VOICE_ID_FILE).read().strip()
    except Exception:
        pass
    return ""

async def clone_voice_on_elevenlabs(clip_paths: list) -> str:
    """Send recorded clips to ElevenLabs instant voice clone and return voice_id."""
    import requests
    fobjs = [open(p, "rb") for p in clip_paths]
    try:
        files = [("files", (os.path.basename(p), f, "audio/webm")) for p, f in zip(clip_paths, fobjs)]
        resp = requests.post(
            "https://api.elevenlabs.io/v1/voices/add",
            headers={"xi-api-key": ELEVENLABS_API_KEY},
            data={"name": "My Cloned Voice"},
            files=files,
        )
        if resp.status_code == 200:
            return resp.json().get("voice_id", "")
        sys.stderr.write(f"ElevenLabs clone error {resp.status_code}: {resp.text}\n")
    except Exception as e:
        sys.stderr.write(f"ElevenLabs clone exception: {e}\n")
    finally:
        for f in fobjs:
            f.close()
    return ""

# Automation helpers
async def generate_voice(script_text: str, voice_path: str = "") -> str:
    """Generate voiceover. Uses ElevenLabs if key valid, else OpenAI TTS."""
    # Try ElevenLabs first (better quality)
    if ELEVENLABS_API_KEY:
        try:
            import requests as _elreq
            _el_voice = "21m00Tcm4TlvDq8ikWAM"  # Rachel (default)
            # Check channels.json for channel-specific voice_id
            try:
                import json as _cej
                _chs = _cej.loads(open("/opt/handholding-engine/data/channels.json").read())
                _ach = next((c for c in _chs if c.get("active")), None)
                if _ach and _ach.get("elevenlabs_voice_id"):
                    _el_voice = _ach["elevenlabs_voice_id"]
            except Exception:
                pass
            def _el_chunks(text, max_len=4000):
                chunks = []
                while len(text) > max_len:
                    cut = text.rfind(". ", 0, max_len)
                    cut = (cut + 2) if cut != -1 else max_len
                    chunks.append(text[:cut].strip())
                    text = text[cut:].strip()
                if text: chunks.append(text)
                return chunks
            _chunks = _el_chunks(script_text)
            _chunk_files = []
            for _i, _chunk in enumerate(_chunks):
                _resp = _elreq.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{_el_voice}",
                    headers={"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"},
                    json={"text": _chunk, "model_id": "eleven_turbo_v2", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
                    timeout=60
                )
                if _resp.status_code == 200:
                    _cf = f"/tmp/el_chunk_{int(os.times()[4])}_{_i}.mp3"
                    open(_cf, "wb").write(_resp.content)
                    _chunk_files.append(_cf)
                else:
                    raise Exception(f"ElevenLabs {_resp.status_code}: {_resp.text[:200]}")
            if not _chunk_files:
                raise Exception("No ElevenLabs chunks generated")
            if len(_chunk_files) == 1:
                return _chunk_files[0]
            _concat = f"/tmp/el_concat_{int(os.times()[4])}.txt"
            open(_concat, "w").write("\n".join(f"file '{f}'" for f in _chunk_files))
            _out = f"/tmp/voiceover_{int(os.times()[4])}.mp3"
            import subprocess as _sp
            _sp.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", _concat, "-c", "copy", _out], capture_output=True)
            for _cf in _chunk_files:
                try: os.remove(_cf)
                except: pass
            if os.path.exists(_out):
                return _out
        except Exception as _el_err:
            sys.stderr.write(f"ElevenLabs TTS failed ({_el_err}), falling back to OpenAI\n")

    if not OPENAI_API_KEY:
        return ""

    try:
        import requests as _req, tempfile as _tmp

        # Split script into 4000-char chunks at sentence boundaries
        def _split_chunks(text, max_len=4000):
            chunks = []
            while len(text) > max_len:
                # Find last sentence end before max_len
                cut = text.rfind('. ', 0, max_len)
                if cut == -1:
                    cut = max_len
                else:
                    cut += 2  # include the period and space
                chunks.append(text[:cut].strip())
                text = text[cut:].strip()
            if text:
                chunks.append(text)
            return chunks

        chunks = _split_chunks(script_text)
        chunk_files = []

        for i, chunk in enumerate(chunks):
            resp = _req.post(
                "https://api.openai.com/v1/audio/speech",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={"model": "tts-1", "voice": "onyx", "input": chunk},
                timeout=60,
            )
            if resp.status_code == 200:
                chunk_file = f"/tmp/tts_chunk_{int(os.times()[4])}_{i}.mp3"
                with open(chunk_file, "wb") as f:
                    f.write(resp.content)
                chunk_files.append(chunk_file)
            else:
                sys.stderr.write(f"TTS chunk {i} error {resp.status_code}: {resp.text[:200]}\n")

        if not chunk_files:
            return ""

        if len(chunk_files) == 1:
            return chunk_files[0]

        # Concatenate MP3 chunks using ffmpeg
        concat_list = f"/tmp/tts_concat_{int(os.times()[4])}.txt"
        with open(concat_list, "w") as f:
            for cf in chunk_files:
                f.write(f"file '{cf}'\n")
        output = f"/tmp/voiceover_{int(os.times()[4])}.mp3"
        import subprocess as _sp
        _sp.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", output],
            capture_output=True
        )
        # Cleanup chunk files
        for cf in chunk_files:
            try: os.remove(cf)
            except: pass
        return output if os.path.exists(output) else chunk_files[0]

    except Exception as e:
        sys.stderr.write(f"Voice generation error: {str(e)}\n")

    return ""

async def fetch_broll(query: str, count: int = 5) -> list:
    """Fetch stock videos from Pexels"""
    if not PEXELS_API_KEY:
        return []

    try:
        import requests
        headers = {"Authorization": PEXELS_API_KEY}
        params = {"query": query, "per_page": count}

        response = requests.get(
            "https://api.pexels.com/videos/search",
            headers=headers,
            params=params
        )

        if response.status_code == 200:
            data = response.json()
            videos = []
            for video in data.get("videos", []):
                files = sorted(video.get("video_files", []), key=lambda f: f.get("width", 9999))
                best = next((f for f in files if 640 <= f.get("width", 0) <= 1280), files[0] if files else None)
                if best:
                    videos.append({
                        "url": best["link"],
                        "title": video["user"]["name"],
                        "duration": video.get("duration", 0)
                    })
            return videos
    except Exception as e:
        sys.stderr.write(f"B-roll fetch error: {str(e)}\n")

    return []

async def assemble_video(voiceover_file: str, broll_videos: list, thumbnail_file: str, title: str, cta_text: str) -> str:
    """Assemble final video from voiceover, B-roll, and thumbnail"""
    try:
        from moviepy.editor import (
            AudioFileClip,
            ImageClip,
            VideoFileClip,
            CompositeVideoClip,
            concatenate_videoclips,
            CompositeAudioClip,
            ColorClip,
        )

        import random

        # Get voiceover duration
        audio = AudioFileClip(voiceover_file)
        duration = audio.duration

        # Create intro (thumbnail with title)
        if thumbnail_file and os.path.exists(thumbnail_file):
            intro = ImageClip(thumbnail_file).set_duration(3)
            intro = intro.resize(height=720).set_fps(30)
        else:
            # Fallback: solid color intro
            intro = ColorClip(size=(1280, 720), color=(50, 50, 50)).set_duration(3)

        # Prepare B-roll clips
        broll_clips = []
        for url in broll_videos[:5]:  # Use up to 5 B-roll videos
            try:
                if url.startswith("http"):
                    # Download video if it's a URL
                    import requests
                    response = requests.get(url, timeout=10)
                    temp_file = f"/tmp/broll_{len(broll_clips)}.mp4"
                    with open(temp_file, "wb") as f:
                        f.write(response.content)
                    clip = VideoFileClip(temp_file)
                else:
                    clip = VideoFileClip(url)

                # Resize to 1280x720
                clip = clip.resize(height=720)
                broll_clips.append(clip)
            except Exception as e:
                sys.stderr.write(f"Failed to load B-roll: {str(e)}\n")
                continue

        # Assemble video: intro + B-roll + outro
        main_duration = max(0, duration - 6)  # 3 sec intro, 3 sec outro
        if broll_clips:
            # Loop b-roll clips to fill full main_duration — avoids frozen frame
            looped = []
            total = 0.0
            prev_total = -1.0
            while total < main_duration:
                if total == prev_total:
                    break  # guard: zero-duration clips would cause infinite loop
                prev_total = total
                for clip in broll_clips:
                    need = main_duration - total
                    if need <= 0:
                        break
                    clip_dur = clip.duration or 0.0
                    if clip_dur <= 0:
                        continue
                    cut = clip.subclip(0, min(clip_dur, need))
                    if cut.duration <= 0:
                        continue
                    looped.append(cut)
                    total += cut.duration
            if not looped:
                looped = [ColorClip(size=(1280, 720), color=(30, 30, 30)).set_duration(main_duration)]
            main_video = concatenate_videoclips(looped, method="chain")
            main_video = main_video.resize(height=720).set_fps(30)
        else:
            main_video = ColorClip(size=(1280, 720), color=(30, 30, 30)).set_duration(main_duration)

        # Create outro (title card with CTA)
        outro = ColorClip(size=(1280, 720), color=(20, 20, 20)).set_duration(3)

        # Combine all clips
        final_video = concatenate_videoclips([intro, main_video, outro])
        final_video = final_video.set_fps(30)

        # Add audio
        final_video = final_video.set_audio(audio)

        # Add fade effects
        final_video = final_video.fadein(0.5).fadeout(0.5)

        # Export video
        output_file = f"/tmp/final_video_{int(os.times()[4])}.mp4"
        final_video.write_videofile(output_file, verbose=False, logger=None, fps=30, codec="libx264")

        # Cleanup
        audio.close()
        if isinstance(final_video, CompositeVideoClip):
            final_video.close()

        return output_file

    except Exception as e:
        sys.stderr.write(f"Video assembly error: {str(e)}\n")
        sys.stderr.flush()
        return ""

async def generate_thumbnail(prompt: str) -> str:
    """Generate thumbnail using DALL-E"""
    try:
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
        payload = {
            "model": "dall-e-3",
            "prompt": f"YouTube thumbnail (1280x720): {prompt}",
            "n": 1,
            "size": "1024x1024"
        }

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{OPENAI_API_BASE}/images/generations",
                json=payload,
                headers=headers
            )

            if response.status_code == 200:
                data = response.json()
                image_url = data["data"][0]["url"]

                # Download and save image
                import requests
                img_response = requests.get(image_url)
                filename = f"/tmp/thumbnail_{int(os.times()[4])}.png"
                with open(filename, "wb") as f:
                    f.write(img_response.content)
                return filename
    except Exception as e:
        sys.stderr.write(f"Thumbnail generation error: {str(e)}\n")

    return ""

async def call_openai(prompt: str, system: str = "", response_format: str = "text"):
    """Call OpenAI-compatible API and track costs"""
    global session_costs

    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "gpt-4-turbo",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 4000,
    }

    if response_format == "json":
        payload["response_format"] = {"type": "json_object"}

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            url = f"{OPENAI_API_BASE}/chat/completions"
            response = await client.post(
                url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            content = re.sub(r"```(?:json)?", "", content).strip()
            # Strip markdown code blocks
            content = re.sub(r'```(?:json)?\s*', '', content).strip()

            # Calculate cost from token usage
            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            model = data.get("model", "gpt-4-turbo")

            # Get pricing for model
            model_pricing = PRICING.get(model, PRICING.get("gpt-4-turbo"))
            input_cost = (input_tokens / 1000) * model_pricing["input"]
            output_cost = (output_tokens / 1000) * model_pricing["output"]
            total_cost = input_cost + output_cost

            # Track cost
            session_costs["total"] += total_cost
            session_costs["calls"].append({
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": total_cost
            })

            # Strip markdown formatting if present (```json ... ```)
            if content.startswith("```"):
                lines = content.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]  # Remove opening ```
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]  # Remove closing ```
                content = "\n".join(lines).strip()

            return content
    except Exception as e:
        sys.stderr.write(f"OpenAI API error: {str(e)}\n")
        sys.stderr.flush()
        raise

# Routes
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/download/video/{filename}")
async def download_video(filename: str):
    """Download assembled video file"""
    import mimetypes
    from fastapi.responses import FileResponse

    file_path = f"/tmp/{filename}"

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video not found")

    return FileResponse(
        path=file_path,
        media_type="video/mp4",
        filename=filename
    )

@app.post("/niches")
def create_niche(niche: NicheCreate, db: Session = Depends(get_db)):
    db_niche = Niche(**niche.dict(), user_id=1)
    db.add(db_niche)
    db.commit()
    db.refresh(db_niche)
    return db_niche

@app.get("/niches")
def list_niches(db: Session = Depends(get_db)):
    return db.query(Niche).filter(Niche.user_id == 1).all()

@app.post("/competitors")
def create_competitor(competitor: CompetitorCreate, db: Session = Depends(get_db)):
    db_competitor = CompetitorInput(**competitor.dict())
    db.add(db_competitor)
    db.commit()
    db.refresh(db_competitor)
    return db_competitor

@app.get("/competitors/{niche_id}")
def list_competitors(niche_id: int, db: Session = Depends(get_db)):
    return db.query(CompetitorInput).filter(CompetitorInput.niche_id == niche_id).all()

@app.post("/ideas/generate")
async def generate_ideas(niche_id: int, db: Session = Depends(get_db)):
    """Generate 10 ideas based on niche and competitors"""
    niche = db.query(Niche).filter(Niche.id == niche_id).first()
    if not niche:
        raise HTTPException(status_code=404, detail="Niche not found")

    competitors = db.query(CompetitorInput).filter(CompetitorInput.niche_id == niche_id).all()
    competitor_text = "\n".join([f"- {c.title_or_url}" for c in competitors])

    prompt = f"""
Analyze these YouTube competitors for the niche: {niche.name}
Audience: {niche.audience}
Monetization angle: {niche.monetization_angle}

Competitors:
{competitor_text}

Generate exactly 10 unique video ideas that:
1. Follow patterns from the competitors
2. Address emotional triggers and curiosity gaps
3. Fit the monetization angle
4. Are production-feasible

Return JSON with:
[{{"title": "...", "reason": "..."}}]

Only return the JSON array, no other text.
"""

    response = await call_openai(prompt, response_format="json")
    ideas = json.loads(response)

    created_ideas = []
    for idea in ideas:
        db_idea = VideoIdea(
            niche_id=niche_id,
            title=idea["title"],
            reason=idea["reason"],
            status="pending"
        )
        db.add(db_idea)
        created_ideas.append(db_idea)

    db.commit()
    return created_ideas

@app.get("/ideas/{niche_id}")
def list_ideas(niche_id: int, db: Session = Depends(get_db)):
    return db.query(VideoIdea).filter(VideoIdea.niche_id == niche_id).all()

@app.post("/ideas/{idea_id}/score")
async def score_idea(idea_id: int, db: Session = Depends(get_db)):
    """Score an idea across 6 dimensions"""
    idea = db.query(VideoIdea).filter(VideoIdea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    prompt = f"""
Score this video idea on a scale of 1-10 for:
- demand_score: Will people search for this?
- clickability_score: Is the title compelling?
- monetization_score: Monetization potential
- production_ease_score: How easy to produce?
- trust_risk_score: Risk of misinformation (1=high risk, 10=safe)
- repeatability_score: Can this be a series?

Title: {idea.title}
Reason: {idea.reason}

Return JSON: {{"demand": 8, "clickability": 7, "monetization": 6, "production_ease": 8, "trust_risk": 9, "repeatability": 8}}
"""

    response = await call_openai(prompt, response_format="json")
    scores = json.loads(response)

    idea.demand_score = scores.get("demand", 0)
    idea.clickability_score = scores.get("clickability", 0)
    idea.monetization_score = scores.get("monetization", 0)
    idea.production_ease_score = scores.get("production_ease", 0)
    idea.trust_risk_score = scores.get("trust_risk", 0)
    idea.repeatability_score = scores.get("repeatability", 0)
    idea.total_score = sum([
        idea.demand_score,
        idea.clickability_score,
        idea.monetization_score,
        idea.production_ease_score,
        idea.trust_risk_score,
        idea.repeatability_score
    ]) / 6 * 10

    db.commit()
    return idea

@app.post("/ideas/{idea_id}/select")
def select_idea(idea_id: int, db: Session = Depends(get_db)):
    idea = db.query(VideoIdea).filter(VideoIdea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    idea.status = "selected"
    db.commit()
    return idea

@app.post("/scripts/generate")
async def generate_script(idea_id: int, db: Session = Depends(get_db)):
    """Generate a 10-minute script with hook, pattern interrupts, and CTA"""
    idea = db.query(VideoIdea).filter(VideoIdea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    prompt = f"""
Write a compelling 10-minute YouTube script for:
Title: {idea.title}
Reason: {idea.reason}

Requirements:
- Strong opening hook (first 10 seconds)
- Pattern interrupt every 60-90 seconds
- Conversational, natural tone
- Clear call-to-action at end
- Flag any unsupported claims with [FACT CHECK NEEDED]

Return JSON:
{{
  "hook": "...",
  "full_script": "...",
  "fact_check_flags": ["claim 1", "claim 2"],
  "unsupported_claims": ["claim 1"],
  "cta": "..."
}}

Only return JSON, no other text.
"""

    response = await call_openai(prompt, response_format="json")
    script_data = json.loads(response)

    db_script = Script(
        idea_id=idea_id,
        hook=script_data["hook"],
        full_script=script_data["full_script"],
        fact_check_flags=json.dumps(script_data.get("fact_check_flags", [])),
        unsupported_claims=json.dumps(script_data.get("unsupported_claims", [])),
        cta=script_data["cta"]
    )
    db.add(db_script)
    db.commit()
    db.refresh(db_script)
    return db_script


@app.get("/scripts/latest")
def get_latest_script(db: Session = Depends(get_db)):
    script = db.query(Script).order_by(Script.id.desc()).first()
    if not script:
        raise HTTPException(status_code=404, detail="No scripts found")
    idea = db.query(VideoIdea).filter(VideoIdea.id == script.idea_id).first()
    return {
        "id": script.id,
        "idea_id": script.idea_id,
        "idea_title": idea.title if idea else "Unknown",
        "hook": script.hook,
        "full_script": script.full_script,
        "fact_check_flags": script.fact_check_flags,
        "cta": script.cta
    }

@app.get("/scripts/{idea_id}")
def get_script(idea_id: int, db: Session = Depends(get_db)):
    script = db.query(Script).filter(Script.idea_id == idea_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")
    return script

@app.post("/asset-packs/generate")
async def generate_asset_pack(script_id: int, db: Session = Depends(get_db)):
    """Generate thumbnail, titles, B-roll, voiceover brief, editor brief, description, pinned comment"""
    script = db.query(Script).filter(Script.id == script_id).first()
    if not script:
        raise HTTPException(status_code=404, detail="Script not found")

    idea = db.query(VideoIdea).filter(VideoIdea.id == script.idea_id).first()

    prompt = f"""
Generate a complete asset pack for this YouTube video:
Title: {idea.title}
Hook: {script.hook}

Return JSON:
{{
  "thumbnail_prompt": "Detailed visual description for thumbnail designer",
  "alternate_titles": ["Title option 1", "Title option 2", "Title option 3"],
  "broll_list": ["Scene 1", "Scene 2", ...],
  "voiceover_instructions": "How to record voiceover (tone, pace, emotion)",
  "editor_brief": "Instructions for editor on Fiverr",
  "youtube_description": "Full YouTube description with keywords",
  "pinned_comment": "The pinned comment to post"
}}

Only return JSON, no other text.
"""

    response = await call_openai(prompt, response_format="json")
    asset_data = json.loads(response)

    db_pack = AssetPack(
        script_id=script_id,
        thumbnail_prompt=asset_data["thumbnail_prompt"],
        alternate_titles=json.dumps(asset_data["alternate_titles"]),
        broll_list=json.dumps(asset_data["broll_list"]),
        voiceover_instructions=asset_data["voiceover_instructions"],
        editor_brief=asset_data["editor_brief"],
        youtube_description=asset_data["youtube_description"],
        pinned_comment=asset_data["pinned_comment"]
    )
    db.add(db_pack)
    db.commit()
    db.refresh(db_pack)
    return db_pack

@app.get("/asset-packs/{script_id}")
def get_asset_pack(script_id: int, db: Session = Depends(get_db)):
    pack = db.query(AssetPack).filter(AssetPack.script_id == script_id).first()
    if not pack:
        raise HTTPException(status_code=404, detail="Asset pack not found")
    return pack

@app.get("/coach/next-action")
def get_next_action(db: Session = Depends(get_db)):
    """Return exactly one next action based on progress"""
    user_id = 1

    niches = db.query(Niche).filter(Niche.user_id == user_id).count()
    if niches == 0:
        return NextActionResponse(task_text="Create your first niche", related_type="niche", related_id=0)

    niche_id = db.query(Niche).filter(Niche.user_id == user_id).first().id
    competitors = db.query(CompetitorInput).filter(CompetitorInput.niche_id == niche_id).count()
    if competitors < 5:
        return NextActionResponse(
            task_text="Add 5 competitor videos to analyze patterns",
            related_type="competitor",
            related_id=niche_id
        )

    ideas = db.query(VideoIdea).filter(VideoIdea.niche_id == niche_id, VideoIdea.status == "pending").count()
    if ideas == 0:
        return NextActionResponse(
            task_text="Generate video ideas based on competitors",
            related_type="idea",
            related_id=niche_id
        )

    unscored = db.query(VideoIdea).filter(VideoIdea.niche_id == niche_id, VideoIdea.total_score == 0).first()
    if unscored:
        return NextActionResponse(
            task_text=f"Score this idea: {unscored.title}",
            related_type="idea",
            related_id=unscored.id
        )

    selected = db.query(VideoIdea).filter(VideoIdea.status == "selected").first()
    if not selected:
        top_idea = db.query(VideoIdea).filter(VideoIdea.niche_id == niche_id).order_by(VideoIdea.total_score.desc()).first()
        return NextActionResponse(
            task_text=f"Select this top idea: {top_idea.title}",
            related_type="idea",
            related_id=top_idea.id
        )

    script = db.query(Script).filter(Script.idea_id == selected.id).first()
    if not script:
        return NextActionResponse(
            task_text=f"Generate script for: {selected.title}",
            related_type="script",
            related_id=selected.id
        )

    asset_pack = db.query(AssetPack).filter(AssetPack.script_id == script.id).first()
    if not asset_pack:
        return NextActionResponse(
            task_text="Generate asset pack (thumbnail, titles, B-roll)",
            related_type="asset_pack",
            related_id=script.id
        )

    return NextActionResponse(
        task_text="Record your voiceover and upload to Fiverr for editing",
        related_type="publish",
        related_id=0
    )

@app.post("/demo/auto-workflow")
async def auto_workflow(db: Session = Depends(get_db)):
    """AI-powered complete workflow: niche → competitors → ideas → script → assets"""

    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set in environment")

    try:
        # Step 1: Create a trending niche
        niche_prompt = "Pick ONE trending YouTube niche with high monetization potential. Return ONLY JSON: {\"name\": \"...\", \"audience\": \"...\", \"monetization_angle\": \"...\", \"notes\": \"...\"}"
        niche_text = await call_openai(niche_prompt)
        if not niche_text:
            raise Exception("OpenAI returned empty response for niche")
        niche_data = json.loads(niche_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate niche: {str(e)}")

    try:
        # Ensure demo user exists
        demo_user = db.query(User).filter(User.id == 1).first()
        if not demo_user:
            demo_user = User(id=1, email="demo@example.com", name="Demo User")
            db.add(demo_user)
            db.commit()

        niche = Niche(user_id=1, **niche_data)
        db.add(niche)
        db.commit()
        db.refresh(niche)

        # Step 2: Generate realistic competitor videos
        comp_prompt = f"For '{niche.name}', list 5 REAL YouTube competitors. Return JSON array: [{{\"title_or_url\": \"name\", \"notes\": \"why it works\"}}]"
        comp_text = await call_openai(comp_prompt)
        comp_data = json.loads(comp_text)

        for comp in comp_data:
            competitor = CompetitorInput(niche_id=niche.id, **comp)
            db.add(competitor)
        db.commit()

        # Step 3: Generate 5 video ideas
        ideas_prompt = f"For '{niche.name}' ({niche.audience}), create 5 viral video ideas. Return JSON: [{{\"title\": \"...\", \"reason\": \"...\", \"demand_score\": 8, \"clickability_score\": 8, \"monetization_score\": 8, \"production_ease_score\": 8, \"trust_risk_score\": 9, \"repeatability_score\": 8}}]"
        ideas_text = await call_openai(ideas_prompt)
        ideas_data = json.loads(ideas_text)

        best_idea = None
        for idea_data in ideas_data:
            idea_data["total_score"] = (idea_data["demand_score"] + idea_data["clickability_score"] + idea_data["monetization_score"] + idea_data["production_ease_score"] + idea_data["trust_risk_score"] + idea_data["repeatability_score"]) / 6
            idea = VideoIdea(niche_id=niche.id, **idea_data, status="selected")
            db.add(idea)
            db.commit()
            db.refresh(idea)
            if not best_idea or idea.total_score > best_idea.total_score:
                best_idea = idea

        # Step 4: Generate script
        script_prompt = f"Write a viral 10-min YouTube script for: '{best_idea.title}' ({niche.audience}). Return JSON: {{\"hook\": \"...\", \"full_script\": \"...\", \"fact_check_flags\": [], \"unsupported_claims\": [], \"cta\": \"...\" }}"
        script_text = await call_openai(script_prompt, response_format="json")
        script_data = json.loads(script_text)

        script = Script(
            idea_id=best_idea.id,
            hook=script_data["hook"],
            full_script=script_data["full_script"],
            fact_check_flags=json.dumps(script_data.get("fact_check_flags", [])),
            unsupported_claims=json.dumps(script_data.get("unsupported_claims", [])),
            cta=script_data["cta"]
        )
        db.add(script)
        db.commit()
        db.refresh(script)

        # Step 5: Generate asset pack
        assets_prompt = f"Create asset pack for '{best_idea.title}'. Return JSON: {{\"thumbnail_prompt\": \"...\", \"alternate_titles\": [...], \"broll_list\": [...], \"voiceover_instructions\": \"...\", \"editor_brief\": \"...\", \"youtube_description\": \"...\", \"pinned_comment\": \"...\"}}"
        assets_text = await call_openai(assets_prompt, response_format="json")
        assets_data = json.loads(assets_text)

        assets = AssetPack(
            script_id=script.id,
            thumbnail_prompt=assets_data["thumbnail_prompt"],
            alternate_titles=json.dumps(assets_data["alternate_titles"]),
            broll_list=json.dumps(assets_data["broll_list"]),
            voiceover_instructions=assets_data["voiceover_instructions"],
            editor_brief=assets_data["editor_brief"],
            youtube_description=assets_data["youtube_description"],
            pinned_comment=assets_data["pinned_comment"]
        )
        db.add(assets)
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Workflow error: {str(e)}")

    return {
        "status": "success",
        "niche_id": niche.id,
        "niche_name": niche.name,
        "idea_id": best_idea.id,
        "idea_title": best_idea.title,
        "script_id": script.id,
        "asset_pack_id": assets.id,
        "message": "Complete workflow generated with AI!",
        "cost": {
            "total": round(session_costs["total"], 4),
            "currency": "USD",
            "api_calls": len(session_costs["calls"])
        }
    }

@app.post("/voices/upload")
async def upload_voice(user_id: int = 1, db: Session = Depends(get_db)):
    """Upload cloned voice file for video generation"""
    try:
        # For now, accept voice file metadata
        # In production, this would handle file upload
        voice = Voice(
            user_id=user_id,
            name="My Cloned Voice",
            file_path="/tmp/cloned_voice.mp3",
            is_default=True
        )
        db.add(voice)
        db.commit()
        db.refresh(voice)

        return {
            "status": "success",
            "voice_id": voice.id,
            "message": "Voice uploaded successfully. Will be used for all future generations."
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")

@app.get("/voices/list")
async def list_voices(user_id: int = 1, db: Session = Depends(get_db)):
    """List user's cloned voices"""
    voices = db.query(Voice).filter(Voice.user_id == user_id).all()
    return {
        "voices": [{"id": v.id, "name": v.name, "is_default": v.is_default} for v in voices]
    }

async def merge_human_clips(voiceover_file: str) -> str:
    """Prepend recorded intro and append outro to ElevenLabs voiceover"""
    intro_path = "/opt/handholding-engine/human_intro.webm"
    outro_path = "/opt/handholding-engine/human_outro.webm"
    has_intro = os.path.exists(intro_path)
    has_outro = os.path.exists(outro_path)
    if not has_intro and not has_outro:
        return voiceover_file
    try:
        from pydub import AudioSegment
        main_audio = AudioSegment.from_mp3(voiceover_file)
        segments = []
        if has_intro:
            segments.append(AudioSegment.from_file(intro_path))
        segments.append(main_audio)
        if has_outro:
            segments.append(AudioSegment.from_file(outro_path))
        combined = segments[0]
        for seg in segments[1:]:
            combined = combined + seg
        output_file = f"/tmp/merged_voiceover_{int(os.times()[4])}.mp3"
        combined.export(output_file, format="mp3")
        return output_file
    except Exception as e:
        sys.stderr.write(f"merge_human_clips error: {str(e)}\n")
        return voiceover_file


_jobs: dict = {}


def _parse_json(text: str):
    """Extract and parse JSON from GPT response, handling trailing text."""
    import re as _re
    text = text.strip()
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting array
    m = _re.search(r'\[.*\]', text, _re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    # Try extracting object
    m = _re.search(r'\{.*\}', text, _re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    raise ValueError(f"Could not parse JSON from: {text[:200]}")

async def _run_automation(job_id: str):
    db = SessionLocal()
    def step(s: str):
        _jobs[job_id]["step"] = s

    try:
        step("Picking trending niche...")
        if not ELEVENLABS_API_KEY or not PEXELS_API_KEY:
            raise Exception("Missing ELEVENLABS_API_KEY or PEXELS_API_KEY")

        # Read active channel to constrain niche
        import json as _cj
        _ch_data = _cj.loads(open("/opt/handholding-engine/data/channels.json").read())
        _active_ch = next((c for c in _ch_data if c.get("active")), None)
        _ch_name = _active_ch["display_name"] if _active_ch else "Personal Finance"
        _ch_keywords = ", ".join(_active_ch.get("niche_keywords", [])[:6]) if _active_ch else "money, investing, budgeting"
        niche_text = await call_openai(
            f"You are creating content for a YouTube channel called \"{_ch_name}\". "
            f"Pick ONE specific niche topic within this channel's focus ({_ch_keywords}). "
            "Return ONLY JSON: {\"name\": \"...\", \"audience\": \"...\", \"monetization_angle\": \"...\", \"notes\": \"...\"}",
        )
        niche_data = _parse_json(niche_text)

        demo_user = db.query(User).filter(User.id == 1).first()
        if not demo_user:
            demo_user = User(id=1, email="demo@example.com", name="Demo User")
            db.add(demo_user)
            db.commit()

        niche = Niche(user_id=1, **niche_data)
        db.add(niche)
        db.commit()
        db.refresh(niche)

        step("Researching competitors...")
        comp_text = await call_openai(f"For '{niche.name}', list 5 REAL YouTube competitors. Return JSON array: [{{\"title_or_url\": \"name\", \"notes\": \"why it works\"}}]")
        comp_data = _parse_json(comp_text)
        for comp in comp_data:
            db.add(CompetitorInput(niche_id=niche.id, **comp))
        db.commit()

        step("Generating video ideas...")
        ideas_text = await call_openai(f"For '{niche.name}' ({niche.audience}), create 5 viral video ideas. Return JSON: [{{\"title\": \"...\", \"reason\": \"...\", \"demand_score\": 8, \"clickability_score\": 8, \"monetization_score\": 8, \"production_ease_score\": 8, \"trust_risk_score\": 9, \"repeatability_score\": 8}}]")
        ideas_data = _parse_json(ideas_text)
        best_idea = None
        for idea_data in ideas_data:
            idea_data["total_score"] = sum([idea_data["demand_score"], idea_data["clickability_score"], idea_data["monetization_score"], idea_data["production_ease_score"], idea_data["trust_risk_score"], idea_data["repeatability_score"]]) / 6
            idea_data.pop("hook", None)
            idea = VideoIdea(niche_id=niche.id, **idea_data, status="selected")
            db.add(idea)
            db.commit()
            db.refresh(idea)
            if not best_idea or idea.total_score > best_idea.total_score:
                best_idea = idea

        step("Writing script...")
        # Generate script in 3 parts to ensure 10-minute length (GPT won't write 1600 words in one shot)
        _title = best_idea.title
        _audience = niche.audience
        _part1 = await call_openai(
            f"Write the OPENING of a YouTube script for: {_title!r} (audience: {_audience}).\n"
            "Include: strong hook, intro, and first 2 main points.\n"
            "Write 400-500 words of spoken script only. No JSON, no formatting, no labels.\n"
            "Start immediately with the first spoken words.",
            response_format="text"
        )
        _part2 = await call_openai(
            f"Continue this YouTube script for: {_title!r}.\n"
            f"Previous section ended with: ...{_part1[-200:]}\n"
            "Write the MIDDLE section: next 3 main points with examples and transitions.\n"
            "Write 500-600 words of spoken script only. Continue seamlessly.",
            response_format="text"
        )
        _part3 = await call_openai(
            f"Write the CLOSING of this YouTube script for: {_title!r}.\n"
            f"Previous section ended with: ...{_part2[-200:]}\n"
            "Include: final tips, summary, and strong call-to-action.\n"
            "Write 400-500 words of spoken script only. End with a compelling CTA.",
            response_format="text"
        )
        full_script_text = f"{_part1}\n\n{_part2}\n\n{_part3}"
        # Extract hook and CTA
        import re as _re
        hook_sentences = ". ".join(_part1.split(". ")[:3]) + "."
        cta_sentences = ". ".join(_part3.split(". ")[-3:]).strip()
        script_data = {
            "hook": hook_sentences,
            "full_script": full_script_text,
            "fact_check_flags": [],
            "unsupported_claims": [],
            "cta": cta_sentences,
        }
        script = Script(idea_id=best_idea.id, hook=script_data["hook"], full_script=script_data["full_script"], fact_check_flags=json.dumps(script_data.get("fact_check_flags", [])), unsupported_claims=json.dumps(script_data.get("unsupported_claims", [])), cta=script_data["cta"])
        db.add(script)
        db.commit()
        db.refresh(script)

        step("Building asset pack...")
        assets_text = await call_openai(f"Create asset pack for '{best_idea.title}'. Return JSON: {{\"thumbnail_prompt\": \"...\", \"alternate_titles\": [...], \"broll_list\": [...], \"voiceover_instructions\": \"...\", \"editor_brief\": \"...\", \"youtube_description\": \"...\", \"pinned_comment\": \"...\"}}", response_format="json")
        assets_data = _parse_json(assets_text)
        assets = AssetPack(script_id=script.id, thumbnail_prompt=assets_data["thumbnail_prompt"], alternate_titles=json.dumps(assets_data["alternate_titles"]), broll_list=json.dumps(assets_data["broll_list"]), voiceover_instructions=assets_data["voiceover_instructions"], editor_brief=assets_data["editor_brief"], youtube_description=assets_data["youtube_description"], pinned_comment=assets_data["pinned_comment"])
        db.add(assets)
        db.commit()

        step("Generating voiceover...")
        user_voice = db.query(Voice).filter(Voice.user_id == 1, Voice.is_default == 'true').first()
        voice_file = user_voice.file_path if (user_voice and os.path.exists(user_voice.file_path)) else await generate_voice(script_data["full_script"])
        if voice_file:
            voice_file = await merge_human_clips(voice_file)

        step("Fetching B-roll...")
        # Generate specific visual search terms so footage actually matches the content
        _broll_terms_text = await call_openai(
            f"For a YouTube video titled: \"{_idea_title if '_idea_title' in dir() else best_idea.title}\"\n"
            "List 4 specific Pexels video search queries that show realistic, relevant footage.\n"
            "Focus on concrete visuals: people doing things, specific objects, real scenes.\n"
            "NO abstract concepts. Return JSON array of 4 strings only.",
            response_format="json"
        )
        try:
            _broll_queries = _parse_json(_broll_terms_text)
            if not isinstance(_broll_queries, list):
                _broll_queries = [best_idea.title]
        except Exception:
            _broll_queries = [best_idea.title]
        broll_data = []
        for _q in _broll_queries[:4]:
            _clips = await fetch_broll(_q, count=2)
            broll_data.extend(_clips)
        if not broll_data:
            broll_data = await fetch_broll(best_idea.title, count=5)

        step("Generating thumbnail...")
        thumbnail_file = await generate_thumbnail(assets_data["thumbnail_prompt"])

        step("Assembling video...")
        final_video_file = ""
        if voice_file:
            final_video_file = await assemble_video(voiceover_file=voice_file, broll_videos=[v["url"] for v in broll_data] if broll_data else [], thumbnail_file=thumbnail_file or "", title=best_idea.title, cta_text=script_data["cta"])

        # ── Upload to YouTube via channels.json ──
        youtube_url = ""
        if final_video_file and os.path.exists(final_video_file):
            try:
                step("Uploading to YouTube...")
                import json as _json
                channels_path = "/opt/handholding-engine/data/channels.json"
                channels = _json.loads(open(channels_path).read())
                ch = next((c for c in channels if c.get("active")), None)
                if ch:
                    from google.oauth2.credentials import Credentials
                    from google.auth.transport.requests import Request as GReq
                    from googleapiclient.discovery import build
                    from googleapiclient.http import MediaFileUpload
                    creds = Credentials(
                        token=None,
                        refresh_token=ch["refresh_token"],
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=ch["client_id"],
                        client_secret=ch["client_secret"],
                    )
                    creds.refresh(GReq())
                    yt = build("youtube", "v3", credentials=creds)
                    body = {
                        "snippet": {
                            "title": best_idea.title[:100],
                            "description": assets_data.get("youtube_description", f"Watch: {best_idea.title}")[:4900],
                            "tags": ["finance", "money", niche.name],
                            "categoryId": "22",
                        },
                        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False},
                    }
                    media = MediaFileUpload(final_video_file, mimetype="video/mp4", resumable=True)
                    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
                    response = None
                    while response is None:
                        _, response = req.next_chunk()
                    yt_id = response["id"]
                    youtube_url = f"https://youtu.be/{yt_id}"
                    print(f"[YT] Uploaded: {youtube_url}", flush=True)
                    # Send success email
                    try:
                        import httpx as _hx
                        rk = os.getenv("RESEND_KEY","")
                        if rk:
                            _hx.post("https://api.resend.com/emails",
                                headers={"Authorization":f"Bearer {rk}","Content-Type":"application/json"},
                                json={"from":"Handholding Engine <hello@ideabylunch.com>",
                                      "to":["eddie@bannermanmenson.com"],
                                      "subject":f"✅ New video posted: {best_idea.title}",
                                      "html":f"<h2>{best_idea.title}</h2><p><a href='{youtube_url}'>Watch on YouTube →</a></p>"},
                                timeout=10)
                    except Exception:
                        pass
            except Exception as yt_err:
                print(f"[YT] Upload failed: {yt_err}", flush=True)

        result = {
            "status": "success",
            "message": "Full automation complete!",
            "niche": niche.name,
            "idea": best_idea.title,
            "script_id": script.id,
            "asset_pack_id": assets.id,
            "youtube_url": youtube_url,
            "automation_files": {
                "voiceover": voice_file or "Not generated",
                "broll_videos": len(broll_data),
                "thumbnail": thumbnail_file or "Not generated",
                "final_video": final_video_file or "Not assembled",
            },
            "cost": {"total": round(session_costs["total"], 4), "currency": "USD"},
            "next_step": "Uploaded!" if youtube_url else "Video assembled, upload pending.",
            "download_url": final_video_file or "",
        }
        # Persist result to disk so it survives server restarts
        import json as _json2
        os.makedirs("/tmp/hh_jobs", exist_ok=True)
        with open(f"/tmp/hh_jobs/{job_id}.json", "w") as _jf:
            _json2.dump({"status":"done","step":"Complete!","live":_jobs[job_id].get("live",{}),"result":result,"error":None}, _jf)
        _jobs[job_id] = {"status": "done", "step": "Complete!", "result": result}
    except Exception as e:
        try: db.rollback()
        except Exception: pass
        import traceback as _tb2, json as _json3
        full_err = str(e) + " " + _tb2.format_exc()[:3000]
        os.makedirs("/tmp/hh_jobs", exist_ok=True)
        with open(f"/tmp/hh_jobs/{job_id}.json", "w") as _ef:
            _json3.dump({"status":"error","step":"Failed","error":full_err,"result":None}, _ef)
        _jobs[job_id] = {"status": "error", "step": "Failed", "error": str(e)}
        # Send failure alert
        try:
            import httpx as _hxe, traceback as _tb
            rk = os.getenv("RESEND_KEY","")
            if rk:
                _hxe.post("https://api.resend.com/emails",
                    headers={"Authorization":f"Bearer {rk}","Content-Type":"application/json"},
                    json={"from":"Handholding Engine <hello@ideabylunch.com>",
                          "to":["eddie@bannermanmenson.com"],
                          "subject":"ALERT: Handholding Engine daily run FAILED",
                          "html":f"<pre>{str(e)}\n{_tb.format_exc()[:2000]}</pre>"},
                    timeout=10)
        except Exception:
            pass
    finally:
        db.close()


@app.post("/demo/full-automation/start")
async def start_automation():
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "running", "step": "Starting..."}
    asyncio.create_task(_run_automation(job_id))
    return {"job_id": job_id}


@app.get("/demo/full-automation/status/{job_id}")
async def automation_status(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/demo/full-automation")
async def full_automation(db: Session = Depends(get_db)):
    """Complete automation: niche → YouTube upload (requires API keys)"""

    if not ELEVENLABS_API_KEY or not PEXELS_API_KEY:
        raise HTTPException(
            status_code=400,
            detail="Missing ELEVENLABS_API_KEY or PEXELS_API_KEY environment variables"
        )

    try:
        # Step 1: Generate full workflow
        niche_prompt = "Pick ONE trending YouTube niche with high monetization potential. Return ONLY JSON: {\"name\": \"...\", \"audience\": \"...\", \"monetization_angle\": \"...\", \"notes\": \"...\"}"
        niche_text = await call_openai(niche_prompt)
        niche_data = json.loads(niche_text)

        demo_user = db.query(User).filter(User.id == 1).first()
        if not demo_user:
            demo_user = User(id=1, email="demo@example.com", name="Demo User")
            db.add(demo_user)
            db.commit()

        niche = Niche(user_id=1, **niche_data)
        db.add(niche)
        db.commit()
        db.refresh(niche)

        # Competitors
        comp_prompt = f"For '{niche.name}', list 5 REAL YouTube competitors. Return JSON array: [{{\"title_or_url\": \"name\", \"notes\": \"why it works\"}}]"
        comp_text = await call_openai(comp_prompt)
        comp_data = json.loads(comp_text)

        for comp in comp_data:
            competitor = CompetitorInput(niche_id=niche.id, **comp)
            db.add(competitor)
        db.commit()

        # Ideas
        ideas_prompt = f"For '{niche.name}' ({niche.audience}), create 5 viral video ideas. Return JSON: [{{\"title\": \"...\", \"reason\": \"...\", \"demand_score\": 8, \"clickability_score\": 8, \"monetization_score\": 8, \"production_ease_score\": 8, \"trust_risk_score\": 9, \"repeatability_score\": 8}}]"
        ideas_text = await call_openai(ideas_prompt)
        ideas_data = json.loads(ideas_text)

        best_idea = None
        for idea_data in ideas_data:
            idea_data["total_score"] = (idea_data["demand_score"] + idea_data["clickability_score"] + idea_data["monetization_score"] + idea_data["production_ease_score"] + idea_data["trust_risk_score"] + idea_data["repeatability_score"]) / 6
            idea = VideoIdea(niche_id=niche.id, **idea_data, status="selected")
            db.add(idea)
            db.commit()
            db.refresh(idea)
            if not best_idea or idea.total_score > best_idea.total_score:
                best_idea = idea

        # Script
        script_prompt = f"Write a viral 10-min YouTube script for: '{best_idea.title}' ({niche.audience}). Return JSON: {{\"hook\": \"...\", \"full_script\": \"...\", \"fact_check_flags\": [], \"unsupported_claims\": [], \"cta\": \"...\" }}"
        script_data = json.loads(script_text)

        script = Script(
            idea_id=best_idea.id,
            hook=script_data["hook"],
            full_script=script_data["full_script"],
            fact_check_flags=json.dumps(script_data.get("fact_check_flags", [])),
            unsupported_claims=json.dumps(script_data.get("unsupported_claims", [])),
            cta=script_data["cta"]
        )
        db.add(script)
        db.commit()
        db.refresh(script)

        # Assets
        assets_prompt = f"Create asset pack for '{best_idea.title}'. Return JSON: {{\"thumbnail_prompt\": \"...\", \"alternate_titles\": [...], \"broll_list\": [...], \"voiceover_instructions\": \"...\", \"editor_brief\": \"...\", \"youtube_description\": \"...\", \"pinned_comment\": \"...\"}}"
        assets_text = await call_openai(assets_prompt, response_format="json")
        assets_data = json.loads(assets_text)

        assets = AssetPack(
            script_id=script.id,
            thumbnail_prompt=assets_data["thumbnail_prompt"],
            alternate_titles=json.dumps(assets_data["alternate_titles"]),
            broll_list=json.dumps(assets_data["broll_list"]),
            voiceover_instructions=assets_data["voiceover_instructions"],
            editor_brief=assets_data["editor_brief"],
            youtube_description=assets_data["youtube_description"],
            pinned_comment=assets_data["pinned_comment"]
        )
        db.add(assets)
        db.commit()

        # Step 2: Get user's cloned voice or generate one
        user_voice = db.query(Voice).filter(
            Voice.user_id == 1,
            Voice.is_default == 'true'
        ).first()

        if user_voice and os.path.exists(user_voice.file_path):
            voice_file = user_voice.file_path
        else:
            voice_file = await generate_voice(script_data["full_script"])

        if voice_file:
            voice_file = await merge_human_clips(voice_file)

        # Step 3: Fetch B-roll
        broll_data = await fetch_broll(best_idea.title, count=3)

        # Step 4: Generate thumbnail
        thumbnail_file = await generate_thumbnail(assets_data["thumbnail_prompt"])

        # Step 5: Assemble final video
        final_video_file = ""
        if voice_file:
            broll_urls = [v["url"] for v in broll_data] if broll_data else []
            final_video_file = await assemble_video(
                voiceover_file=voice_file,
                broll_videos=broll_urls,
                thumbnail_file=thumbnail_file if thumbnail_file else "",
                title=best_idea.title,
                cta_text=script_data["cta"]
            )

        return {
            "status": "success",
            "message": "Full automation complete! Video assembled and ready to upload.",
            "niche": niche.name,
            "idea": best_idea.title,
            "script_id": script.id,
            "asset_pack_id": assets.id,
            "automation_files": {
                "voiceover": voice_file if voice_file else "Not generated",
                "broll_videos": len(broll_data),
                "thumbnail": thumbnail_file if thumbnail_file else "Not generated",
                "final_video": final_video_file if final_video_file else "Not assembled"
            },
            "cost": {
                "total": round(session_costs["total"], 4),
                "currency": "USD"
            },
            "next_step": "Video ready! Download the final video and upload to YouTube directly.",
            "download_url": f"Download: {final_video_file}" if final_video_file else "Video assembly failed"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Automation error: {str(e)}")

@app.post("/publishing/batch")
async def create_batch(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    demo_user = db.query(User).filter(User.id == 1).first()
    if not demo_user:
        demo_user = User(id=1, email="demo@example.com", name="Demo User")
        db.add(demo_user)
        db.commit()
    batch = ContentBatch(
        user_id=1,
        name=data.get("name", "Content Batch"),
        count=int(data.get("count", 10)),
        schedule_start=str(data.get("schedule_start", "")),
        schedule_frequency=data.get("schedule_frequency", "daily"),
        status="queued",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return {"message": f"Batch '{batch.name}' created with {batch.count} videos scheduled {batch.schedule_frequency}", "batch_id": batch.id}


@app.get("/publishing/batch/{batch_id}")
async def get_batch(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(ContentBatch).filter(ContentBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return {
        "id": batch.id,
        "name": batch.name,
        "count": batch.count,
        "schedule_start": batch.schedule_start,
        "schedule_frequency": batch.schedule_frequency,
        "status": batch.status,
        "created_at": batch.created_at.isoformat() if batch.created_at else None,
    }


@app.get("/publishing/batches")
async def list_batches(db: Session = Depends(get_db)):
    batches = db.query(ContentBatch).filter(ContentBatch.user_id == 1).order_by(ContentBatch.created_at.desc()).all()
    return {"batches": [{"id": b.id, "name": b.name, "count": b.count, "status": b.status, "schedule_frequency": b.schedule_frequency} for b in batches]}


@app.post("/voices/record-clip")
async def save_record_clip(clip_type: str = Form(...), file: UploadFile = File(...)):
    if clip_type not in ("intro", "outro"):
        raise HTTPException(status_code=400, detail="clip_type must be intro or outro")
    save_path = f"/opt/handholding-engine/human_{clip_type}.webm"
    content_bytes = await file.read()
    with open(save_path, "wb") as f:
        f.write(content_bytes)

    # Auto-clone to ElevenLabs (best-effort — never fails the save)
    voice_id = ""
    try:
        if ELEVENLABS_API_KEY:
            clips = [p for p in [
                "/opt/handholding-engine/human_intro.webm",
                "/opt/handholding-engine/human_outro.webm",
            ] if os.path.exists(p)]
            if clips:
                voice_id = await clone_voice_on_elevenlabs(clips)
                if voice_id:
                    with open(VOICE_ID_FILE, "w") as vf:
                        vf.write(voice_id)
    except Exception as e:
        sys.stderr.write(f"Clone step error (non-fatal): {e}\n")

    return {"ok": True, "clip_type": clip_type, "bytes": len(content_bytes), "voice_id": voice_id or None}


@app.get("/voices/clone-status")
async def voice_clone_status():
    voice_id = get_stored_voice_id()
    return {"cloned": bool(voice_id), "voice_id": voice_id or None}


@app.get("/voices/has-clips")
async def has_clips():
    return {
        "intro": os.path.exists("/opt/handholding-engine/human_intro.webm"),
        "outro": os.path.exists("/opt/handholding-engine/human_outro.webm"),
    }


@app.delete("/voices/record-clip/{clip_type}")
async def delete_record_clip(clip_type: str):
    if clip_type not in ("intro", "outro"):
        raise HTTPException(status_code=400, detail="clip_type must be intro or outro")
    path = f"/opt/handholding-engine/human_{clip_type}.webm"
    if os.path.exists(path):
        os.remove(path)
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
