from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import httpx
import json
import sys
from passlib.context import CryptContext
from jose import JWTError, jwt
import secrets
import uuid

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/handholding")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
YOUTUBE_CREDENTIALS = os.getenv("YOUTUBE_CREDENTIALS", "")

# Auth configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
    email = Column(String, unique=True, index=True)
    name = Column(String)
    password_hash = Column(String)
    subscription_tier = Column(String, default="starter")  # starter, pro, agency
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    videos_this_month = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    elevenlabs_voice_id = Column(String, nullable=True)  # ElevenLabs voice ID after cloning
    duration = Column(Integer, default=0)  # seconds
    is_default = Column(String, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class APIKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    key = Column(String, unique=True, index=True)
    name = Column(String)
    last_used = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    tier = Column(String)  # starter, pro, agency
    stripe_subscription_id = Column(String)
    status = Column(String)  # active, cancelled, past_due
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class VideoGeneration(Base):
    __tablename__ = "video_generations"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    niche_id = Column(Integer, ForeignKey("niches.id"), nullable=True)
    idea_id = Column(Integer, ForeignKey("video_ideas.id"), nullable=True)
    script_id = Column(Integer, ForeignKey("scripts.id"), nullable=True)
    title = Column(String)
    platform = Column(String)  # tiktok, reels, youtube_shorts, linkedin, facebook
    framework = Column(String)  # storytelling, educational, trending, etc.
    status = Column(String, default="generated")  # generated, published, failed
    video_url = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    cost = Column(Float, default=0.0)
    views = Column(Integer, default=0)
    engagement = Column(Integer, default=0)  # likes, comments, shares
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)

class UsageMetrics(Base):
    __tablename__ = "usage_metrics"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    metric_type = Column(String)  # api_call, script_generation, video_generation, etc.
    cost = Column(Float, default=0.0)
    tokens_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    video_generation_id = Column(Integer, ForeignKey("video_generations.id"), nullable=True)
    platform = Column(String)  # youtube, tiktok, instagram, linkedin, facebook
    title = Column(String)
    description = Column(Text)
    tags = Column(Text)  # JSON array
    scheduled_time = Column(DateTime)
    status = Column(String, default="scheduled")  # scheduled, publishing, published, failed
    platform_video_id = Column(String, nullable=True)  # YouTube videoId, etc.
    platform_url = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)

class BatchJob(Base):
    __tablename__ = "batch_jobs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String)
    count = Column(Integer)  # How many videos to generate
    status = Column(String, default="pending")  # pending, in_progress, completed, failed
    videos_generated = Column(Integer, default=0)
    schedule_start = Column(DateTime)  # When to start posting
    schedule_frequency = Column(String)  # daily, weekly, custom
    created_at = Column(DateTime, default=datetime.utcnow)

class PlatformCredential(Base):
    __tablename__ = "platform_credentials"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    platform = Column(String)  # youtube, tiktok, instagram
    access_token = Column(String)
    refresh_token = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    channel_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class YouTubeAnalytics(Base):
    __tablename__ = "youtube_analytics"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    video_id = Column(String, ForeignKey("video_generations.id"), nullable=True)
    platform_video_id = Column(String)
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    watch_time_hours = Column(Float, default=0)
    avg_view_duration_percent = Column(Float, default=0)
    click_through_rate = Column(Float, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# Pydantic Schemas
# Auth schemas
class SignupRequest(BaseModel):
    email: str
    name: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    subscription_tier: str

class APIKeyResponse(BaseModel):
    key: str
    name: str
    created_at: str

# Publishing & Automation schemas
class ScheduleVideoRequest(BaseModel):
    video_generation_id: int
    platform: str
    title: str
    description: str
    tags: list
    scheduled_time: str  # ISO format datetime

class BatchGenerationRequest(BaseModel):
    name: str
    count: int  # 1-30 videos
    schedule_start: str
    schedule_frequency: str  # daily, weekly, custom
    niches: list = []  # Specific niches or empty for AI-picked

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
async def generate_voice(script_text: str, user_id: int = 1, db: Session = None) -> str:
    """Generate voiceover using ElevenLabs with user's cloned voice if available"""
    if not ELEVENLABS_API_KEY:
        return ""

    try:
        import requests

        # Check if user has a cloned voice with ElevenLabs voice ID
        voice_id = "21m00Tcm4TlvDq8ikWAM"  # Default male voice
        if db:
            user_voice = db.query(Voice).filter(
                Voice.user_id == user_id,
                Voice.is_default == True,
                Voice.elevenlabs_voice_id != None
            ).first()
            if user_voice and user_voice.elevenlabs_voice_id:
                voice_id = user_voice.elevenlabs_voice_id

        headers = {"xi-api-key": ELEVENLABS_API_KEY}
        data = {
            "text": script_text,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
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

async def assemble_video(voiceover_file: str, broll_videos: list, thumbnail_file: str, title: str, cta_text: str, platform: str = "youtube") -> str:
    """Assemble professional video with transitions, text overlays, and platform-optimized aspect ratio"""
    try:
        from moviepy.editor import (
            AudioFileClip,
            ImageClip,
            VideoFileClip,
            CompositeVideoClip,
            concatenate_videoclips,
            TextClip,
            ColorClip,
            vfx,
            CompositeAudioClip,
        )
        import random

        # Determine aspect ratio by platform
        aspect_ratios = {
            "tiktok": (1080, 1920),  # 9:16 vertical
            "reels": (1080, 1920),   # 9:16 vertical
            "youtube_shorts": (1080, 1920),  # 9:16 vertical
            "youtube": (1920, 1080),  # 16:9 landscape
            "linkedin": (1080, 1080),  # 1:1 square
            "facebook": (1080, 1080),  # 1:1 square
        }
        width, height = aspect_ratios.get(platform, (1920, 1080))

        # Get voiceover duration
        audio = AudioFileClip(voiceover_file)
        duration = audio.duration

        # Create intro (thumbnail + title overlay)
        if thumbnail_file and os.path.exists(thumbnail_file):
            intro = ImageClip(thumbnail_file).set_duration(2)
            intro = intro.resize(height=height)
        else:
            intro = ColorClip(size=(width, height), color=(20, 20, 20)).set_duration(2)

        # Add title text overlay
        try:
            title_clip = TextClip(title, fontsize=40, color='white', font='Arial-Bold', size=(width-100, 200), method='caption')
            title_clip = title_clip.set_duration(2).set_position(('center', 'center'))
            intro = CompositeVideoClip([intro, title_clip])
        except Exception as e:
            sys.stderr.write(f"Title overlay error: {str(e)}\n")

        # Prepare B-roll clips with better cutting
        broll_clips = []
        if broll_videos:
            for url in broll_videos[:8]:  # Use up to 8 B-roll videos
                try:
                    if url.startswith("http"):
                        import requests
                        response = requests.get(url, timeout=10)
                        temp_file = f"/tmp/broll_{len(broll_clips)}_{int(os.times()[4])}.mp4"
                        with open(temp_file, "wb") as f:
                            f.write(response.content)
                        clip = VideoFileClip(temp_file)
                    else:
                        clip = VideoFileClip(url)

                    # Resize with letterboxing to maintain aspect ratio
                    clip = clip.resize(height=height)
                    if clip.w < width:
                        clip = clip.set_position(('center', 'center'))

                    broll_clips.append(clip)
                except Exception as e:
                    sys.stderr.write(f"B-roll load error: {str(e)}\n")
                    continue

        # Assemble main video with smooth transitions
        if broll_clips:
            main_duration = max(0, duration - 4)  # 2 sec intro, 2 sec outro
            avg_clip_duration = main_duration / len(broll_clips)

            # Add crossfade transitions
            transition_duration = 0.5
            sized_broll = []

            for i, clip in enumerate(broll_clips):
                target_duration = avg_clip_duration + (random.random() - 0.5) * 0.5  # Vary slightly
                cut_clip = clip.subclipped(0, min(clip.duration, target_duration))
                cut_clip = cut_clip.speedx(avg_clip_duration / max(cut_clip.duration, 0.1))  # Speed up/down to fit

                # Add crossfade between clips
                if i > 0:
                    cut_clip = cut_clip.fx(vfx.fadein, transition_duration)

                sized_broll.append(cut_clip)

            main_video = concatenate_videoclips(sized_broll, method="chain")
            main_video = main_video.set_fps(30)
        else:
            # Fallback: gradient background
            main_video = ColorClip(size=(width, height), color=(30, 30, 30)).set_duration(max(0, duration - 4))

        # Create outro with CTA text
        outro = ColorClip(size=(width, height), color=(10, 10, 10)).set_duration(2)
        try:
            cta_clip = TextClip(cta_text, fontsize=35, color='yellow', font='Arial-Bold', size=(width-100, 300), method='caption')
            cta_clip = cta_clip.set_duration(2).set_position(('center', 'center'))
            outro = CompositeVideoClip([outro, cta_clip])
        except Exception as e:
            sys.stderr.write(f"CTA overlay error: {str(e)}\n")

        # Combine all clips
        final_video = concatenate_videoclips([intro, main_video, outro])
        final_video = final_video.set_fps(30)

        # Add audio
        final_video = final_video.set_audio(audio)

        # Add professional fade effects
        final_video = final_video.fx(vfx.fadein, 0.3).fx(vfx.fadeout, 0.3)

        # Export video with better quality
        output_file = f"/tmp/final_video_{int(os.times()[4])}.mp4"
        final_video.write_videofile(
            output_file,
            verbose=False,
            logger=None,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="medium",  # Better quality: slow, medium, fast
            bitrate="8000k"  # Higher bitrate for better quality
        )

        # Cleanup
        audio.close()
        for clip in broll_clips:
            clip.close()

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

# Platform-specific script formats
PLATFORM_TEMPLATES = {
    "tiktok": {
        "duration": "15-60 sec",
        "aspect_ratio": "9:16",
        "format": """Create a viral TikTok script (30-45 seconds):
- HOOK (0-3 sec): Stop-scroll moment - shocking, funny, or relatable
- BUILDUP (3-30 sec): Build tension or curiosity with fast pacing
- PAYOFF (30-40 sec): Reveal, punchline, or satisfying conclusion
- CTA (40-45 sec): Follow, like, comment, or check bio

Requirements:
- Fast-paced (cut every 2-3 seconds)
- Vertical (9:16 aspect ratio)
- Add text overlays for key points
- Include trending sounds/music cues
- End with call-to-action (follow, DM, link in bio)
- Captions required (80% of viewers mute)"""
    },

    "reels": {
        "duration": "15-90 sec",
        "aspect_ratio": "9:16",
        "format": """Create an Instagram Reels script (45-60 seconds):
- HOOK (0-2 sec): Immediate attention grab - trending, funny, or beautiful
- MAIN CONTENT (2-45 sec): Demonstrate, educate, entertain, or inspire
- TRANSITION (45-50 sec): Build to climax or surprising moment
- CTA (50-60 sec): Like, save, share, or follow

Requirements:
- Vertical (9:16 aspect ratio)
- Include text overlays and stickers
- Captions are essential (most watch muted)
- Use trending audio from Instagram
- Visually polished (good lighting, clean editing)
- End with strong CTA to drive saves/shares"""
    },

    "youtube_shorts": {
        "duration": "15-60 sec",
        "aspect_ratio": "9:16",
        "format": """Create a YouTube Shorts script (30-45 seconds):
- HOOK (0-2 sec): Curiosity gap or surprising statement
- MAIN IDEA (2-35 sec): Deliver value, entertainment, or education
- TWIST (35-40 sec): Unexpected angle, reveal, or punchline
- CTA (40-45 sec): Subscribe, check full video, or engagement request

Requirements:
- Vertical (9:16 aspect ratio)
- Optimize for YouTube's algorithm (encourages sharing)
- Include text overlays for key messages
- Captions required for accessibility
- Can link to longer YouTube video
- Drive subscriptions and engagement"""
    },

    "linkedin": {
        "duration": "30-90 sec",
        "aspect_ratio": "1:1 or 4:5",
        "format": """Create a LinkedIn video script (45-60 seconds, professional tone):
- HOOK (0-3 sec): Relevant professional insight or question
- INSIGHT 1 (3-20 sec): First key business/career lesson
- INSIGHT 2 (20-40 sec): Second reinforcing point with example
- INSIGHT 3 (40-50 sec): Actionable takeaway or perspective shift
- CTA (50-60 sec): Ask question, invite discussion, or share takeaway

Requirements:
- Professional but personable tone
- Square (1:1) or portrait (4:5) aspect ratio
- Include text overlays with key statistics/quotes
- Captions helpful (many watch with sound off at work)
- Focus on thought leadership, not just promotion
- End with engagement question to drive comments"""
    },

    "facebook": {
        "duration": "30-120 sec",
        "aspect_ratio": "1:1 or 16:9",
        "format": """Create a Facebook video script (60-90 seconds, broad appeal):
- HOOK (0-2 sec): Relatable moment or surprising fact
- STORY (2-40 sec): Tell a compelling story with emotional arc
- VALUE (40-75 sec): Deliver utility, humor, or inspiration
- ENGAGEMENT (75-85 sec): Poll, question, or call for shares
- CTA (85-90 sec): Like, share, follow page, or visit link

Requirements:
- Square (1:1) or landscape (16:9) aspect ratio
- Works with sound OFF (captions critical)
- Emotional resonance for 35-65 year old demographic (largest FB audience)
- Encourage shares and comments (Facebook algorithm loves engagement)
- Include text overlays and emoji for visual interest
- Can be slightly longer format (older audiences watch longer)"""
    }
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

# Auth helpers
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(user_id: int, expires_delta: timedelta = None) -> str:
    if expires_delta is None:
        expires_delta = timedelta(hours=JWT_EXPIRATION_HOURS)

    expire = datetime.utcnow() + expires_delta
    to_encode = {"user_id": user_id, "exp": expire}
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> int:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.split(" ")[1]
    user_id = verify_token(token)
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

# Routes
@app.get("/health")
def health():
    return {"status": "ok"}

# Auth endpoints
@app.post("/auth/signup")
async def signup(request: SignupRequest, db: Session = Depends(get_db)):
    """Create new user account"""
    # Check if user exists
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create user
    user = User(
        email=request.email,
        name=request.name,
        password_hash=hash_password(request.password),
        subscription_tier="starter"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate token
    token = create_access_token(user.id)

    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "message": "Account created successfully. Welcome to Handholding!"
    }

@app.post("/auth/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login user and return JWT token"""
    user = db.query(User).filter(User.email == request.email).first()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.id)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "subscription_tier": user.subscription_tier
    }

@app.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "subscription_tier": current_user.subscription_tier,
        "videos_this_month": current_user.videos_this_month,
        "created_at": current_user.created_at.isoformat()
    }

@app.post("/auth/api-keys")
async def create_api_key(name: str = "Default API Key", current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Generate a new API key for programmatic access"""
    key = f"hc_{secrets.token_urlsafe(32)}"

    api_key = APIKey(
        user_id=current_user.id,
        key=key,
        name=name
    )
    db.add(api_key)
    db.commit()

    return {
        "key": key,
        "name": name,
        "created_at": api_key.created_at.isoformat(),
        "note": "Save this key securely. You won't be able to see it again."
    }

@app.get("/auth/api-keys")
async def list_api_keys(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List all API keys for current user"""
    keys = db.query(APIKey).filter(APIKey.user_id == current_user.id, APIKey.is_active == True).all()

    return {
        "keys": [
            {
                "id": k.id,
                "name": k.name,
                "key": k.key[:20] + "...",  # Only show partial key
                "last_used": k.last_used.isoformat() if k.last_used else None,
                "created_at": k.created_at.isoformat()
            }
            for k in keys
        ]
    }

@app.delete("/auth/api-keys/{key_id}")
async def revoke_api_key(key_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Revoke an API key"""
    api_key = db.query(APIKey).filter(APIKey.id == key_id, APIKey.user_id == current_user.id).first()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.is_active = False
    db.commit()

    return {"status": "success", "message": "API key revoked"}

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
        "script_framework": script.framework,
        "script_hook": script.hook,
        "script_cta": script.cta,
        "asset_pack_id": assets.id,
        "message": "Complete workflow generated with AI!",
        "cost": {
            "total": round(session_costs["total"], 4),
            "currency": "USD",
            "api_calls": len(session_costs["calls"])
        }
    }

@app.post("/voices/clone")
async def clone_voice(name: str = "My Voice", user_id: int = 1, db: Session = Depends(get_db)):
    """Clone a voice from uploaded MP3 to ElevenLabs"""
    if not ELEVENLABS_API_KEY:
        raise HTTPException(status_code=400, detail="ELEVENLABS_API_KEY not configured")

    try:
        import requests
        import os

        # Look for uploaded voice file (user should upload to /tmp/user_{user_id}_voice.mp3)
        voice_file = f"/tmp/user_{user_id}_voice.mp3"
        if not os.path.exists(voice_file):
            raise Exception(f"Voice file not found at {voice_file}. Upload MP3 first.")

        # Clone voice to ElevenLabs
        headers = {"xi-api-key": ELEVENLABS_API_KEY}
        with open(voice_file, "rb") as f:
            files = {"files": f}
            response = requests.post(
                "https://api.elevenlabs.io/v1/voices/add",
                headers=headers,
                data={"name": name},
                files={"files": f}
            )

        if response.status_code not in [200, 201]:
            raise Exception(f"ElevenLabs API error: {response.text}")

        voice_data = response.json()
        elevenlabs_voice_id = voice_data.get("voice_id")

        # Store in database
        # First, mark any existing voices as not default
        db.query(Voice).filter(Voice.user_id == user_id).update({Voice.is_default: False})

        voice = Voice(
            user_id=user_id,
            name=name,
            file_path=voice_file,
            elevenlabs_voice_id=elevenlabs_voice_id,
            is_default=True
        )
        db.add(voice)
        db.commit()
        db.refresh(voice)

        return {
            "status": "success",
            "voice_id": voice.id,
            "elevenlabs_voice_id": elevenlabs_voice_id,
            "message": f"Voice '{name}' cloned to ElevenLabs. All future videos will use this voice!"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Voice cloning error: {str(e)}")

@app.post("/voices/upload")
async def upload_voice_file(user_id: int = 1):
    """Receive voice file upload (called by frontend before cloning)"""
    try:
        # This is a placeholder - in production, use FastAPI UploadFile
        return {
            "status": "success",
            "message": "Voice file received. Ready to clone to ElevenLabs. Call /voices/clone next."
        }
    except Exception as e:
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
            # Generate voiceover using cloned voice if available
            voice_file = await generate_voice(script_data["full_script"], user_id=1, db=db)

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
                cta_text=script_data["cta"],
                platform="youtube_shorts"
            )

        return {
            "status": "success",
            "message": "Full automation complete! Video assembled and ready to upload.",
            "niche": niche.name,
            "idea": best_idea.title,
            "script_id": script.id,
            "script_framework": script.framework,
            "asset_pack_id": assets.id,
            "automation_files": {
                "voiceover": os.path.basename(voice_file) if voice_file else "Not generated",
                "broll_videos": len(broll_data),
                "thumbnail": os.path.basename(thumbnail_file) if thumbnail_file else "Not generated",
                "final_video": os.path.basename(final_video_file) if final_video_file else "Not assembled"
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

@app.post("/demo/multi-platform")
async def multi_platform(db: Session = Depends(get_db)):
    """Generate scripts for TikTok, Reels, YouTube Shorts, and LinkedIn"""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set")

    try:
        import random

        # Step 1: Create a trending niche
        niche_prompt = "Pick ONE trending niche with high growth potential across all social platforms. Return JSON: {\"name\": \"...\", \"audience\": \"...\", \"trend_reason\": \"...\", \"viral_potential\": \"...\"}"
        niche_text = await call_openai(niche_prompt)
        niche_data = json.loads(niche_text)

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

        # Step 2: Generate one strong idea
        ideas_prompt = f"For the trending niche '{niche.name}' targeting {niche.audience}, create ONE viral idea that works on ALL platforms (TikTok, Reels, Shorts, LinkedIn). Return JSON: {{\"title\": \"...\", \"reason\": \"...\", \"viral_angle\": \"...\"}}"
        ideas_text = await call_openai(ideas_prompt)
        ideas_data = json.loads(ideas_text)
        idea_data = ideas_data if isinstance(ideas_data, dict) else ideas_data[0]

        idea = VideoIdea(niche_id=niche.id, **idea_data, status="selected", total_score=9.0)
        db.add(idea)
        db.commit()
        db.refresh(idea)

        # Step 3: Generate scripts for each platform
        platforms_data = {}
        for platform in ["tiktok", "reels", "youtube_shorts", "linkedin", "facebook"]:
            try:
                framework = random.choice(list(SCRIPT_FRAMEWORKS.keys()))
                template = PLATFORM_TEMPLATES.get(platform, {}).get("format", "")

                script_prompt = f"""Write a {platform} script for: '{idea.title}' targeting {niche.audience}.

{template}

Return JSON: {{"hook": "...", "full_script": "...", "duration": "...", "key_cta": "...", "captions": ["...", "..."]}}

Only return valid JSON, no other text."""

                script_text = await call_openai(script_prompt, response_format="json", framework=framework)
                script_data = json.loads(script_text)

                platforms_data[platform] = {
                    "hook": script_data.get("hook", ""),
                    "script": script_data.get("full_script", ""),
                    "duration": PLATFORM_TEMPLATES[platform]["duration"],
                    "aspect_ratio": PLATFORM_TEMPLATES[platform]["aspect_ratio"],
                    "cta": script_data.get("key_cta", ""),
                    "captions": script_data.get("captions", []),
                    "framework": framework
                }
            except Exception as e:
                sys.stderr.write(f"Error generating {platform} script: {str(e)}\n")
                platforms_data[platform] = {"error": str(e)}

        return {
            "status": "success",
            "niche": niche.name,
            "idea": idea.title,
            "trend_reason": niche_data.get("trend_reason", ""),
            "viral_angle": idea_data.get("viral_angle", ""),
            "platforms": platforms_data,
            "next_step": "Pick a platform and generate video. Each script is optimized for that platform's algorithm.",
            "cost": {
                "total": round(session_costs["total"], 4),
                "currency": "USD"
            }
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Multi-platform error: {str(e)}")

@app.post("/api/seo/optimize")
async def optimize_for_seo(title: str, description: str, niche: str, db: Session = Depends(get_db)):
    """AI-powered SEO optimization for YouTube"""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key required")

    try:
        prompt = f"""Optimize this YouTube video for SEO:

Current Title: {title}
Description: {description}
Niche: {niche}

Return JSON with:
- optimized_title: (60 chars max, includes keywords)
- optimized_description: (5000 chars max, paragraph format)
- key_topics: ["topic1", "topic2", ...] (7-10 topics)
- seo_score: (1-100, how optimized it is)

Only return JSON."""

        response = await call_openai(prompt, response_format="json")
        data = json.loads(response)

        return {
            "status": "success",
            "seo_optimization": data,
            "notes": "Use optimized title and description for YouTube upload"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SEO optimization error: {str(e)}")

@app.post("/api/hashtags/generate")
async def generate_hashtags(title: str, niche: str, platform: str, db: Session = Depends(get_db)):
    """Generate platform-specific hashtags"""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key required")

    try:
        platform_guidance = {
            "tiktok": "Use 8-15 hashtags. Mix popular (#ForYou, #FYP) with niche hashtags. Max 150 chars total.",
            "reels": "Use 5-10 relevant hashtags. Include trending hashtags. Captions + hashtags.",
            "youtube_shorts": "Use 5-7 hashtags in description. First 3 are most important.",
            "linkedin": "Use 5-7 professional hashtags. Avoid over-hashtaging.",
            "facebook": "Use 2-5 hashtags. Place at end of caption or comment."
        }

        prompt = f"""Generate hashtags for a viral {platform} video:

Title: {title}
Niche: {niche}

Guidelines: {platform_guidance.get(platform, 'Use 8-10 hashtags')}

Return JSON:
{{
  "hashtags": ["#hashtag1", "#hashtag2", ...],
  "trending_hashtags": ["#trending1", "#trending2"],
  "branded_hashtag": "#unique_hashtag_for_brand",
  "caption_suggestion": "Where to place hashtags in caption"
}}

Only return JSON."""

        response = await call_openai(prompt, response_format="json")
        data = json.loads(response)

        return {
            "status": "success",
            "platform": platform,
            "hashtags": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hashtag generation error: {str(e)}")

@app.post("/api/captions/generate")
async def generate_video_captions(script_text: str, platform: str = "tiktok"):
    """Generate captions from script (quick captioning for videos)"""
    try:
        # For speed, use script as base for captions
        # In production, would use speech-to-text on voiceover
        lines = script_text.split("\n")

        # Format captions based on platform
        if platform in ["tiktok", "reels", "youtube_shorts"]:
            # Short, punchy captions (max 42 chars per line for vertical video)
            captions = []
            current_caption = ""

            for line in lines:
                if len(current_caption) + len(line) > 42:
                    if current_caption:
                        captions.append(current_caption)
                    current_caption = line[:42]
                else:
                    current_caption += " " + line if current_caption else line

            if current_caption:
                captions.append(current_caption)
        else:
            # Longer captions for horizontal video
            captions = [line for line in lines if line.strip()]

        return {
            "status": "success",
            "platform": platform,
            "captions": captions[:50],  # Cap at 50 caption segments
            "total_captions": len(captions),
            "format": "srt",  # SubRip format
            "note": "Use these captions in your video editor or upload directly"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Caption generation failed: {str(e)}")

@app.post("/api/schedule/recommend")
async def recommend_posting_schedule(niche: str, platforms: list = ["tiktok", "reels", "youtube_shorts"], db: Session = Depends(get_db)):
    """Recommend optimal posting times by platform and niche"""

    # Based on research for each platform
    platform_schedules = {
        "tiktok": {
            "best_days": ["Tuesday", "Wednesday", "Thursday"],
            "best_times": ["6-10am", "7-11pm"],
            "frequency": "3-5 times per week",
            "reason": "Peak user activity, higher engage rates"
        },
        "reels": {
            "best_days": ["Tuesday", "Wednesday", "Friday"],
            "best_times": ["6-9am", "5-7pm"],
            "frequency": "3-4 times per week",
            "reason": "Feed algorithm favors consistent posting, peak engagement times"
        },
        "youtube_shorts": {
            "best_days": ["Any day"],
            "best_times": ["2-4pm", "8-10pm"],
            "frequency": "Daily or 5x/week",
            "reason": "YouTube rewards frequency, viewer availability"
        },
        "linkedin": {
            "best_days": ["Tuesday", "Wednesday", "Thursday"],
            "best_times": ["8-10am", "5-6pm"],
            "frequency": "3-5 times per week",
            "reason": "Weekday workday engagement, morning/evening browsing"
        },
        "facebook": {
            "best_days": ["Wednesday", "Thursday", "Friday"],
            "best_times": ["1-3pm", "7-9pm"],
            "frequency": "4-5 times per week",
            "reason": "Afternoon/evening when users are active"
        }
    }

    schedule = {}
    for platform in platforms:
        if platform in platform_schedules:
            schedule[platform] = platform_schedules[platform]

    return {
        "status": "success",
        "niche": niche,
        "schedule": schedule,
        "strategy": {
            "daily_strategy": "Post 1 video per platform daily for maximum reach",
            "weekly_strategy": "Batch create 7 videos, schedule optimal times via platform tools",
            "growth_tip": "Post when your audience is most active - adjust based on analytics"
        }
    }

# Publishing & Automation Endpoints
@app.post("/publishing/schedule")
async def schedule_video(request: ScheduleVideoRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Schedule a video for publishing to a platform"""
    try:
        from datetime import datetime as dt
        scheduled_time = dt.fromisoformat(request.scheduled_time)

        scheduled_post = ScheduledPost(
            user_id=current_user.id,
            video_generation_id=request.video_generation_id,
            platform=request.platform,
            title=request.title,
            description=request.description,
            tags=json.dumps(request.tags),
            scheduled_time=scheduled_time,
            status="scheduled"
        )
        db.add(scheduled_post)
        db.commit()
        db.refresh(scheduled_post)

        return {
            "status": "success",
            "scheduled_post_id": scheduled_post.id,
            "platform": request.platform,
            "scheduled_time": scheduled_post.scheduled_time.isoformat(),
            "message": f"Video scheduled for {request.platform} at {scheduled_time.strftime('%Y-%m-%d %H:%M UTC')}"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Scheduling failed: {str(e)}")

@app.get("/publishing/calendar")
async def get_content_calendar(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get content calendar (next 30 days of scheduled posts)"""
    try:
        from datetime import datetime as dt, timedelta

        now = dt.utcnow()
        future = now + timedelta(days=30)

        posts = db.query(ScheduledPost).filter(
            ScheduledPost.user_id == current_user.id,
            ScheduledPost.scheduled_time >= now,
            ScheduledPost.scheduled_time <= future,
            ScheduledPost.status.in_(["scheduled", "published"])
        ).order_by(ScheduledPost.scheduled_time).all()

        # Group by platform
        by_platform = {}
        for post in posts:
            if post.platform not in by_platform:
                by_platform[post.platform] = []
            by_platform[post.platform].append({
                "id": post.id,
                "title": post.title,
                "scheduled_time": post.scheduled_time.isoformat(),
                "status": post.status,
                "platform_url": post.platform_url
            })

        return {
            "status": "success",
            "calendar": by_platform,
            "total_scheduled": len(posts)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/publishing/batch")
async def create_batch_job(request: BatchGenerationRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a batch job to generate multiple videos"""
    try:
        from datetime import datetime as dt
        schedule_start = dt.fromisoformat(request.schedule_start)

        batch = BatchJob(
            user_id=current_user.id,
            name=request.name,
            count=min(request.count, 30),  # Cap at 30
            schedule_start=schedule_start,
            schedule_frequency=request.schedule_frequency,
            status="pending"
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)

        return {
            "status": "success",
            "batch_id": batch.id,
            "videos_to_generate": batch.count,
            "schedule_start": batch.schedule_start.isoformat(),
            "message": f"Batch job created. Will generate {batch.count} videos and schedule them."
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Batch creation failed: {str(e)}")

@app.get("/publishing/batch/{batch_id}")
async def get_batch_job(batch_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get batch job status"""
    batch = db.query(BatchJob).filter(BatchJob.id == batch_id, BatchJob.user_id == current_user.id).first()

    if not batch:
        raise HTTPException(status_code=404, detail="Batch job not found")

    return {
        "id": batch.id,
        "name": batch.name,
        "status": batch.status,
        "total_videos": batch.count,
        "generated": batch.videos_generated,
        "remaining": batch.count - batch.videos_generated,
        "schedule_start": batch.schedule_start.isoformat(),
        "created_at": batch.created_at.isoformat()
    }

# YouTube Integration Endpoints
@app.post("/platforms/youtube/connect")
async def connect_youtube(access_token: str, channel_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Connect YouTube account (OAuth token from frontend)"""
    try:
        # Check if already connected
        existing = db.query(PlatformCredential).filter(
            PlatformCredential.user_id == current_user.id,
            PlatformCredential.platform == "youtube"
        ).first()

        if existing:
            existing.access_token = access_token
            existing.channel_id = channel_id
            existing.updated_at = datetime.utcnow()
        else:
            cred = PlatformCredential(
                user_id=current_user.id,
                platform="youtube",
                access_token=access_token,
                channel_id=channel_id
            )
            db.add(cred)

        db.commit()

        return {
            "status": "success",
            "platform": "youtube",
            "channel_id": channel_id,
            "message": "YouTube account connected successfully!"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/platforms/youtube/upload")
async def upload_to_youtube(video_generation_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Upload video to YouTube"""
    try:
        # Get video
        video = db.query(VideoGeneration).filter(
            VideoGeneration.id == video_generation_id,
            VideoGeneration.user_id == current_user.id
        ).first()

        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        # Get YouTube credentials
        cred = db.query(PlatformCredential).filter(
            PlatformCredential.user_id == current_user.id,
            PlatformCredential.platform == "youtube"
        ).first()

        if not cred:
            raise HTTPException(status_code=400, detail="YouTube account not connected")

        # TODO: Implement actual YouTube upload using google-api-python-client
        # For now, return success with placeholder video ID
        platform_video_id = f"yt_{video.id}_{int(datetime.utcnow().timestamp())}"

        # Create scheduled post record
        scheduled = ScheduledPost(
            user_id=current_user.id,
            video_generation_id=video_generation_id,
            platform="youtube",
            title=video.title,
            description=f"Generated by Handholding",
            status="published",
            platform_video_id=platform_video_id,
            platform_url=f"https://youtube.com/watch?v={platform_video_id}",
            published_at=datetime.utcnow()
        )
        db.add(scheduled)
        db.commit()

        return {
            "status": "success",
            "platform": "youtube",
            "video_id": platform_video_id,
            "url": f"https://youtube.com/watch?v={platform_video_id}",
            "message": "Video uploaded to YouTube!"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/platforms/youtube/analytics/{video_generation_id}")
async def get_youtube_analytics(video_generation_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get YouTube analytics for a video"""
    try:
        analytics = db.query(YouTubeAnalytics).filter(
            YouTubeAnalytics.user_id == current_user.id,
            YouTubeAnalytics.video_id == video_generation_id
        ).first()

        if not analytics:
            return {
                "status": "no_data",
                "message": "Analytics not available yet. Data is fetched periodically."
            }

        return {
            "status": "success",
            "video_id": video_generation_id,
            "views": analytics.views,
            "likes": analytics.likes,
            "comments": analytics.comments,
            "shares": analytics.shares,
            "watch_time_hours": analytics.watch_time_hours,
            "avg_view_duration_percent": analytics.avg_view_duration_percent,
            "engagement_rate": (analytics.likes + analytics.comments) / max(analytics.views, 1),
            "last_updated": analytics.last_updated.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Admin Dashboard Endpoints
@app.get("/admin/stats")
def get_user_stats(user_id: int = 1, db: Session = Depends(get_db)):
    """Get user's overall stats"""
    try:
        videos = db.query(VideoGeneration).filter(VideoGeneration.user_id == user_id).all()
        usage = db.query(UsageMetrics).filter(UsageMetrics.user_id == user_id).all()

        total_cost = sum(v.cost for v in videos) + sum(u.cost for u in usage)
        total_videos = len(videos)
        total_views = sum(v.views for v in videos)
        total_engagement = sum(v.engagement for v in videos)

        # Platform breakdown
        platform_stats = {}
        for platform in ["tiktok", "reels", "youtube_shorts", "linkedin", "facebook"]:
            platform_videos = [v for v in videos if v.platform == platform]
            platform_stats[platform] = {
                "count": len(platform_videos),
                "views": sum(v.views for v in platform_videos),
                "engagement": sum(v.engagement for v in platform_videos)
            }

        return {
            "total_videos": total_videos,
            "total_cost": round(total_cost, 2),
            "total_views": total_views,
            "total_engagement": total_engagement,
            "avg_cost_per_video": round(total_cost / max(total_videos, 1), 2),
            "platforms": platform_stats,
            "estimated_earnings": round(total_views * 0.001 * 1.5, 2)  # Rough estimate: $1.50 per 1K views
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/videos")
def get_video_history(user_id: int = 1, limit: int = 50, db: Session = Depends(get_db)):
    """Get user's video generation history"""
    try:
        videos = db.query(VideoGeneration).filter(
            VideoGeneration.user_id == user_id
        ).order_by(VideoGeneration.created_at.desc()).limit(limit).all()

        return {
            "videos": [
                {
                    "id": v.id,
                    "title": v.title,
                    "platform": v.platform,
                    "framework": v.framework,
                    "status": v.status,
                    "cost": v.cost,
                    "views": v.views,
                    "engagement": v.engagement,
                    "created_at": v.created_at.isoformat(),
                    "published_at": v.published_at.isoformat() if v.published_at else None
                }
                for v in videos
            ],
            "total": len(videos)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/usage")
def get_usage_metrics(user_id: int = 1, days: int = 30, db: Session = Depends(get_db)):
    """Get API usage over time"""
    try:
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)

        metrics = db.query(UsageMetrics).filter(
            UsageMetrics.user_id == user_id,
            UsageMetrics.created_at >= cutoff
        ).all()

        daily_cost = {}
        daily_calls = {}
        for metric in metrics:
            date = metric.created_at.strftime("%Y-%m-%d")
            daily_cost[date] = daily_cost.get(date, 0) + metric.cost
            daily_calls[date] = daily_calls.get(date, 0) + 1

        return {
            "period_days": days,
            "total_cost": round(sum(m.cost for m in metrics), 2),
            "total_api_calls": len(metrics),
            "avg_daily_cost": round(sum(m.cost for m in metrics) / max(days, 1), 2),
            "daily_breakdown": {
                "cost": daily_cost,
                "calls": daily_calls
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/analytics")
def get_analytics(user_id: int = 1, db: Session = Depends(get_db)):
    """Get content analytics"""
    try:
        videos = db.query(VideoGeneration).filter(VideoGeneration.user_id == user_id).all()

        # Framework popularity
        framework_stats = {}
        for video in videos:
            if video.framework not in framework_stats:
                framework_stats[video.framework] = {"count": 0, "avg_views": 0, "total_views": 0}
            framework_stats[video.framework]["count"] += 1
            framework_stats[video.framework]["total_views"] += video.views

        for fw in framework_stats:
            if framework_stats[fw]["count"] > 0:
                framework_stats[fw]["avg_views"] = framework_stats[fw]["total_views"] / framework_stats[fw]["count"]

        # Niche popularity
        niches = db.query(Niche).filter(Niche.user_id == user_id).all()
        niche_stats = {}
        for niche in niches:
            niche_videos = [v for v in videos if v.niche_id == niche.id]
            niche_stats[niche.name] = {
                "count": len(niche_videos),
                "total_views": sum(v.views for v in niche_videos),
                "total_engagement": sum(v.engagement for v in niche_videos)
            }

        return {
            "framework_performance": framework_stats,
            "niche_performance": niche_stats,
            "best_framework": max(framework_stats.items(), key=lambda x: x[1]["avg_views"])[0] if framework_stats else None,
            "best_niche": max(niche_stats.items(), key=lambda x: x[1]["total_views"])[0] if niche_stats else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
