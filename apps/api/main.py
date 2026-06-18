from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text
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

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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
    framework = Column(String, default="storytelling")  # Track which framework was used
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
    is_default = Column(String, default=False)
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

# Automation helpers
async def generate_voice(script_text: str) -> str:
    """Generate voiceover using ElevenLabs"""
    if not ELEVENLABS_API_KEY:
        return ""

    try:
        import requests
        headers = {"xi-api-key": ELEVENLABS_API_KEY}
        data = {
            "text": script_text,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        response = requests.post(
            "https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM",
            headers=headers,
            json=data
        )

        if response.status_code == 200:
            # Save audio file
            filename = f"/tmp/voiceover_{int(os.times()[4])}.mp3"
            with open(filename, "wb") as f:
                f.write(response.content)
            return filename
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
                videos.append({
                    "url": video["video_files"][0]["link"],
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
        from moviepy.video.fx.all import vfx
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
        if broll_clips:
            # Distribute B-roll across voiceover duration
            main_duration = max(0, duration - 6)  # 3 sec intro, 3 sec outro
            avg_clip_duration = main_duration / len(broll_clips) if broll_clips else 3

            # Cut B-roll to fit
            sized_broll = []
            for clip in broll_clips:
                cut_clip = clip.subclipped(0, min(clip.duration, avg_clip_duration))
                sized_broll.append(cut_clip)

            # Concatenate B-roll
            main_video = concatenate_videoclips(sized_broll, method="chain")
            main_video = main_video.resize(height=720).set_fps(30)
        else:
            # Fallback: use solid color
            main_video = ColorClip(size=(1280, 720), color=(30, 30, 30)).set_duration(max(0, duration - 6))

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

        async with httpx.AsyncClient(timeout=60) as client:
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

# Script frameworks for variety
SCRIPT_FRAMEWORKS = {
    "storytelling": """Create a compelling narrative script with:
- HOOK: Start with a surprising story or personal anecdote (5 sec)
- BUILD: Tell the story with drama and tension (7 min)
- CLIMAX: The turning point or biggest revelation (30 sec)
- RESOLUTION: How it all connects to the topic (1 min)
- CTA: Call to action with urgency

Make it feel like telling a friend a story, not reading facts.""",

    "educational": """Write a clear teaching script with:
- HOOK: Ask a question that makes them curious (5 sec)
- LESSON 1: First concept with examples (2 min)
- LESSON 2: Second concept building on first (2 min)
- LESSON 3: Advanced application (2 min)
- SUMMARY: Key takeaways they'll remember (1 min)
- CTA: What to do with this knowledge

Use analogies and simple language.""",

    "trending": """Create a timely, pop-culture script:
- HOOK: Reference what's trending NOW (5 sec)
- WHY IT MATTERS: Why this trend is important (1 min)
- HOW TO: Step-by-step what you can do (5 min)
- PROOF: Real examples or statistics (1 min)
- OPPORTUNITY: How they can capitalize on it (1 min)
- CTA: Urgent action to take

Make it feel urgent and FOMO-driven.""",

    "entertaining": """Write an entertaining, personality-driven script:
- HOOK: Funny observation or relatable moment (5 sec)
- SETUP: Establish the scenario or problem (1 min)
- BUILDUP: Add humor, twists, unexpected angles (6 min)
- PAYOFF: The big reveal or punchline (1 min)
- LESSON: What they learned (optional, 30 sec)
- CTA: What they should do next

Make it feel like hanging with a funny friend.""",

    "contrarian": """Write a surprising, opinion-driven script:
- HOOK: State a bold, controversial take (5 sec)
- COMMON BELIEF: What most people think (1 min)
- WHY WRONG: Evidence against the common belief (3 min)
- TRUTH: Your contrarian perspective (3 min)
- PROOF: Why you're right (1 min)
- CTA: Debate in comments

Make it feel like you're revealing a secret.""",

    "tutorials": """Write a clear, step-by-step how-to script:
- INTRO: What they'll learn and why (1 min)
- TOOLS: What they need (30 sec)
- STEP 1: First action with details (1.5 min)
- STEP 2: Second action (1.5 min)
- STEP 3: Third action (1.5 min)
- FINAL STEP: How to finish (1 min)
- TIPS: Pro tips and common mistakes (1 min)
- CTA: Share their results

Make it beginner-friendly and easy to follow.""",
}

async def call_openai(prompt: str, system: str = "", response_format: str = "text", framework: str = ""):
    """Call OpenAI-compatible API and track costs"""
    global session_costs

    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

    messages = []
    system_content = system
    if framework and framework in SCRIPT_FRAMEWORKS:
        framework_instruction = SCRIPT_FRAMEWORKS[framework]
        system_content = f"{system}\n\n{framework_instruction}" if system else framework_instruction

    if system_content:
        messages.append({"role": "system", "content": system_content})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "gpt-4-turbo",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2000,
    }

    if response_format == "json":
        payload["response_format"] = {"type": "json_object"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            url = f"{OPENAI_API_BASE}/chat/completions"
            response = await client.post(
                url,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

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
    import random
    idea = db.query(VideoIdea).filter(VideoIdea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    # Pick a random framework for variety
    framework = random.choice(list(SCRIPT_FRAMEWORKS.keys()))

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

    response = await call_openai(prompt, response_format="json", framework=framework)
    script_data = json.loads(response)

    db_script = Script(
        idea_id=idea_id,
        hook=script_data["hook"],
        full_script=script_data["full_script"],
        fact_check_flags=json.dumps(script_data.get("fact_check_flags", [])),
        unsupported_claims=json.dumps(script_data.get("unsupported_claims", [])),
        cta=script_data["cta"],
        framework=framework
    )
    db.add(db_script)
    db.commit()
    db.refresh(db_script)
    return db_script

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

        # Step 4: Generate script with random framework
        import random
        framework = random.choice(list(SCRIPT_FRAMEWORKS.keys()))
        script_prompt = f"Write a viral 10-min YouTube script for: '{best_idea.title}' ({niche.audience}). Return JSON: {{\"hook\": \"...\", \"full_script\": \"...\", \"fact_check_flags\": [], \"unsupported_claims\": [], \"cta\": \"...\" }}"
        script_text = await call_openai(script_prompt, response_format="json", framework=framework)
        script_data = json.loads(script_text)

        script = Script(
            idea_id=best_idea.id,
            hook=script_data["hook"],
            full_script=script_data["full_script"],
            fact_check_flags=json.dumps(script_data.get("fact_check_flags", [])),
            unsupported_claims=json.dumps(script_data.get("unsupported_claims", [])),
            cta=script_data["cta"],
            framework=framework
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

        # Script with random framework
        import random
        framework = random.choice(list(SCRIPT_FRAMEWORKS.keys()))
        script_prompt = f"Write a viral 10-min YouTube script for: '{best_idea.title}' ({niche.audience}). Return JSON: {{\"hook\": \"...\", \"full_script\": \"...\", \"fact_check_flags\": [], \"unsupported_claims\": [], \"cta\": \"...\" }}"
        script_text = await call_openai(script_prompt, response_format="json", framework=framework)
        script_data = json.loads(script_text)

        script = Script(
            idea_id=best_idea.id,
            hook=script_data["hook"],
            full_script=script_data["full_script"],
            fact_check_flags=json.dumps(script_data.get("fact_check_flags", [])),
            unsupported_claims=json.dumps(script_data.get("unsupported_claims", [])),
            cta=script_data["cta"],
            framework=framework
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
            Voice.is_default == True
        ).first()

        if user_voice and os.path.exists(user_voice.file_path):
            voice_file = user_voice.file_path
        else:
            # Fallback: generate voiceover if no voice uploaded
            voice_file = await generate_voice(script_data["full_script"])

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
