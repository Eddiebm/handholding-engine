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

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/handholding")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

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

async def call_openai(prompt: str, system: str = "", response_format: str = "text"):
    """Call OpenAI-compatible API"""
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "gpt-4-turbo",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2000,
    }

    if response_format == "json":
        payload["response_format"] = {"type": "json_object"}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{OPENAI_API_BASE}/chat/completions",
            json=payload,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

# Routes
@app.get("/health")
def health():
    return {"status": "ok"}

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
        "message": "Complete workflow generated with AI!"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
