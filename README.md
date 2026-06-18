# Handholding Content Engine

A web application that helps users create successful faceless YouTube channels by automating most of the work and providing one clear action at a time.

## Features

- **Dashboard**: Single "What do I do next?" button that guides you step-by-step
- **Niche Setup**: Define your YouTube niche, audience, and monetization angle
- **Competitor Analysis**: Paste YouTube URLs to analyze competitor patterns
- **AI Idea Generation**: Generate 10 unique video ideas based on competitors
- **Idea Scoring**: Score each idea across 6 dimensions (demand, clickability, monetization, ease, trust, repeatability)
- **Script Generation**: AI-generated 10-minute scripts with hooks and pattern interrupts
- **Asset Pack**: Complete set of assets including thumbnail prompt, titles, B-roll list, voiceover brief, editor brief, YouTube description

## Tech Stack

- **Frontend**: Next.js 14 + TypeScript + TailwindCSS
- **Backend**: FastAPI + SQLAlchemy + PostgreSQL
- **AI**: OpenAI-compatible API (configurable)
- **Deployment**: Docker Compose (ready for Hetzner VPS)

## Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key (or compatible API endpoint)

### Local Development

1. **Clone and setup:**
```bash
cd handholding-engine
cp .env.example .env
```

2. **Edit .env with your OpenAI key:**
```bash
OPENAI_API_KEY=sk-your-key-here
```

3. **Start services:**
```bash
docker-compose up
```

4. **Access the app:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### First Run

1. Create a niche (e.g., "Personal Finance for Gen Z")
2. Add 5+ competitor YouTube videos
3. Generate ideas (AI will analyze patterns)
4. Score and select your best idea
5. Generate a script
6. Generate asset pack
7. Record voiceover and upload to Fiverr for editing

## Database Schema

### Users
- `id`: Primary key
- `email`: User email
- `name`: User name
- `created_at`: Timestamp

### Niches
- `id`: Primary key
- `user_id`: Foreign key to users
- `name`: Niche name (e.g., "Personal Finance")
- `audience`: Target audience description
- `monetization_angle`: How you'll monetize
- `notes`: Additional notes

### Competitor Inputs
- `id`: Primary key
- `niche_id`: Foreign key to niches
- `title_or_url`: YouTube video title or URL
- `notes`: Why this video works
- `created_at`: Timestamp

### Video Ideas
- `id`: Primary key
- `niche_id`: Foreign key to niches
- `title`: Idea title
- `reason`: Why this idea works
- `demand_score`: 0-10
- `clickability_score`: 0-10
- `monetization_score`: 0-10
- `production_ease_score`: 0-10
- `trust_risk_score`: 0-10
- `repeatability_score`: 0-10
- `total_score`: Average of all scores
- `status`: "pending", "selected", etc.

### Scripts
- `id`: Primary key
- `idea_id`: Foreign key to video_ideas
- `hook`: Opening hook (first 10 seconds)
- `full_script`: Complete script
- `fact_check_flags`: Claims needing fact-checking
- `unsupported_claims`: Unsupported claims
- `cta`: Call to action

### Asset Packs
- `id`: Primary key
- `script_id`: Foreign key to scripts
- `thumbnail_prompt`: Prompt for thumbnail designer
- `alternate_titles`: 3 alternate video titles
- `broll_list`: List of B-roll scenes
- `voiceover_instructions`: How to record voiceover
- `editor_brief`: Brief for Fiverr editor
- `youtube_description`: Full YouTube description
- `pinned_comment`: Comment to pin

### Tasks
- `id`: Primary key
- `user_id`: Foreign key to users
- `related_type`: "niche", "competitor", "idea", "script", "asset_pack"
- `related_id`: ID of related item
- `task_text`: Human-readable task
- `status`: "pending", "completed"

## API Routes

### Niches
- `POST /niches`: Create niche
- `GET /niches`: List niches

### Competitors
- `POST /competitors`: Add competitor video
- `GET /competitors/{niche_id}`: List competitors for niche

### Ideas
- `POST /ideas/generate`: Generate 10 ideas
- `GET /ideas/{niche_id}`: List ideas for niche
- `POST /ideas/{idea_id}/score`: Score an idea
- `POST /ideas/{idea_id}/select`: Select an idea

### Scripts
- `POST /scripts/generate`: Generate script for idea
- `GET /scripts/{idea_id}`: Get script

### Asset Packs
- `POST /asset-packs/generate`: Generate complete asset pack
- `GET /asset-packs/{script_id}`: Get asset pack

### Coach
- `GET /coach/next-action`: Get next action to take

## Environment Variables

```
DATABASE_URL=postgresql://user:password@host:5432/db
OPENAI_API_KEY=sk-...
OPENAI_API_BASE=https://api.openai.com/v1  (optional)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Architecture

### Frontend (Next.js)
- Dashboard with progress tracking
- 6 main pages for each step of the workflow
- Simple, mobile-friendly UI
- Minimal cognitive load

### Backend (FastAPI)
- RESTful API with JSON responses
- SQLAlchemy ORM for database
- Async/await for better performance
- Integration with OpenAI API

### Database (PostgreSQL)
- Normalized schema
- Foreign key constraints
- Timestamps on all tables

## Deployment

### Hetzner VPS Deployment

1. **SSH into server:**
```bash
ssh root@your-server-ip
```

2. **Clone repository:**
```bash
git clone <repo> && cd handholding-engine
```

3. **Setup environment:**
```bash
cp .env.example .env
nano .env  # Add your OpenAI key
```

4. **Start with Docker Compose:**
```bash
docker-compose up -d
```

5. **Setup domain (optional):**
Use Nginx reverse proxy pointing to localhost:3000

## Known Limitations

- Single default user for MVP (no authentication)
- No persistent session management
- AI responses limited to 2000 tokens
- No video upload integration
- No real-time progress updates

## Future Enhancements

- Multi-user support with authentication
- Video upload and storage integration
- Real-time progress notifications
- A/B testing different scripts
- Analytics integration
- Integration with YouTube API for competitor analysis
- Automated video upload
- AI voice generation for voiceover
- Team collaboration features

## Assumptions Made

1. Users have an OpenAI API key
2. PostgreSQL is available (Docker)
3. Users understand basic YouTube concepts
4. AI responses are helpful without human review (in production, add review step)
5. Single user per deployment for MVP

## Support

For issues or questions, check the API docs at http://localhost:8000/docs

## License

MIT
