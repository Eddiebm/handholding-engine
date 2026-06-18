# Architecture Overview

## System Design

```
┌─────────────────────────────────────────────────────────────┐
│                     Browser (User)                           │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/WebSocket
                         ↓
┌─────────────────────────────────────────────────────────────┐
│            Next.js Frontend (Port 3000)                      │
│                                                               │
│  Pages:                                                      │
│  - /              Dashboard (progress + next action)        │
│  - /niches        Niche setup form                          │
│  - /competitors   Add YouTube URLs                          │
│  - /ideas         Generate & score ideas                    │
│  - /scripts       Generate 10-min scripts                   │
│  - /asset-pack    Thumbnail, titles, B-roll, etc.          │
│                                                               │
│  Libraries:                                                  │
│  - axios: API calls                                         │
│  - TailwindCSS: Styling                                     │
│  - React hooks: State management                            │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API (JSON)
                         ↓
┌─────────────────────────────────────────────────────────────┐
│          FastAPI Backend (Port 8000)                        │
│                                                               │
│  Endpoints:                                                  │
│  - POST /niches           Create niche                      │
│  - GET /niches            List niches                       │
│  - POST /competitors      Add competitor                    │
│  - GET /competitors/:id   List competitors                  │
│  - POST /ideas/generate   Generate 10 ideas                 │
│  - GET /ideas/:id         List ideas                        │
│  - POST /ideas/:id/score  Score idea (AI)                   │
│  - POST /ideas/:id/select Select idea                       │
│  - POST /scripts/generate Generate script (AI)              │
│  - GET /scripts/:id       Get script                        │
│  - POST /asset-packs/gen  Generate assets (AI)              │
│  - GET /coach/next-action Get next action                   │
│                                                               │
│  Features:                                                   │
│  - SQLAlchemy ORM                                           │
│  - Async request handling                                   │
│  - OpenAI integration                                       │
│  - CORS enabled                                             │
└────────────────────────┬────────────────────────────────────┘
                         │ SQL (psycopg2)
                         ↓
┌─────────────────────────────────────────────────────────────┐
│       PostgreSQL Database (Port 5432)                       │
│                                                               │
│  Tables:                                                     │
│  - users              User accounts                         │
│  - niches             YouTube niches                        │
│  - competitor_inputs  Competitor videos                     │
│  - video_ideas        Generated ideas                       │
│  - scripts            Generated scripts                     │
│  - asset_packs        Generated assets                      │
│  - tasks              User tasks                            │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Niche Creation
User → Form → API → DB → Success

### 2. Competitor Analysis
User (YouTube URLs) → API → OpenAI → "10 ideas" → DB → Display

### 3. Idea Scoring
Selected Idea → OpenAI → Scores (demand, clickability, etc.) → DB → Rank

### 4. Script Generation
Selected Idea → OpenAI → Hook + Full Script + CTA + Fact Checks → DB → Display

### 5. Asset Pack Generation
Script → OpenAI → Thumbnail Prompt + Titles + B-roll + Description → DB → Display

### 6. Coach (Next Action)
State Check → Rule Engine → "What to do next" → Display

## Key Design Decisions

### 1. Single Default User
- MVP simplification
- No authentication complexity
- Easy to upgrade later
- User ID hardcoded as `1` in routes

### 2. AI Integration Layer
- OpenAI-compatible API abstraction
- Configurable via environment variables
- Structured JSON responses
- 2000-token response limit (adjustable)

### 3. Async/Await Architecture
- FastAPI async routes
- Non-blocking I/O
- Better scalability
- httpx for async HTTP

### 4. Frontend State Management
- React hooks (useState, useEffect)
- No Redux/Zustand (MVP simplicity)
- API client in `lib/api.ts`
- Loading states for all async operations

### 5. Database Design
- Normalized schema (3NF)
- Foreign key constraints
- Timestamps on all tables
- No soft deletes

### 6. Docker Compose
- Local development = production-like
- PostgreSQL always available
- Hot reload enabled
- Volume mounts for development

## Component Hierarchy

### Frontend Components (Implicit)
```
Layout
├── Nav (hardcoded in layout)
├── Dashboard (/)
├── Niches (/niches)
│   ├── NicheForm
│   └── NicheList
├── Competitors (/competitors)
│   ├── NicheSelector
│   ├── CompetitorForm
│   └── CompetitorList
├── Ideas (/ideas)
│   ├── IdeaList
│   ├── IdeaScorer
│   └── IdeaSelector
├── Scripts (/scripts)
│   ├── ScriptDisplay
│   └── FactCheckFlags
└── AssetPack (/asset-pack)
    ├── ThumbnailPrompt
    ├── TitleOptions
    ├── BrollList
    ├── VoiceoverBrief
    ├── EditorBrief
    └── YouTubeAssets
```

### Database Relations
```
Users (1) ────→ (N) Niches
Niches (1) ────→ (N) Competitor Inputs
Niches (1) ────→ (N) Video Ideas
Video Ideas (1) ────→ (1) Scripts
Scripts (1) ────→ (1) Asset Packs
Users (1) ────→ (N) Tasks
```

## API Request/Response Pattern

All endpoints follow this pattern:

### Request
```json
{
  "field": "value",
  "nested": {
    "field": "value"
  }
}
```

### Response (Success - 200)
```json
{
  "id": 1,
  "field": "value",
  "created_at": "2024-01-15T10:00:00"
}
```

### Response (Error - 4xx/5xx)
```json
{
  "detail": "Human-readable error message"
}
```

## Authentication & Authorization

**MVP Implementation:** None (single hardcoded user)

**Production Upgrade Path:**
1. Add JWT tokens to auth routes
2. Store sessions in database
3. Protect routes with middleware
4. Add role-based access control

## Scalability Considerations

### Immediate Bottlenecks
1. AI API rate limits (OpenAI)
2. Database connection pool
3. Single backend instance

### Solutions
1. Queue system (Celery, RabbitMQ)
2. Connection pooling (pgBouncer)
3. Load balancer + multiple instances
4. Redis caching for ideas/scripts

### Database Optimization
- Add indexes on frequently queried columns
- Implement pagination for list endpoints
- Archive old records
- Connection pooling with pgBouncer

## Security Considerations

### Current (MVP)
- ✅ No hardcoded secrets in code
- ✅ Environment variables for config
- ✅ SQL parameterization (SQLAlchemy)
- ❌ No authentication
- ❌ No rate limiting
- ❌ No input validation beyond Pydantic

### Production Checklist
- Add authentication (JWT)
- Implement rate limiting
- Add CORS origin whitelist
- Validate all inputs
- Sanitize error messages
- Add logging/monitoring
- Use HTTPS only
- Implement CSRF protection
- Add request signing

## Deployment Architecture

### Local Development
```
docker-compose up
localhost:3000 (frontend)
localhost:8000 (API)
localhost:5432 (database)
```

### Production (Hetzner)
```
VM (Hetzner)
├── Docker Compose
│   ├── Frontend (Next.js)
│   ├── API (FastAPI)
│   └── Database (PostgreSQL)
├── Nginx Reverse Proxy
└── SSL/TLS (Let's Encrypt)
```

### Cloud Deployment
```
Could be adapted to:
- AWS (ECS + RDS + CloudFront)
- GCP (Cloud Run + Cloud SQL)
- Azure (Container Instances + Database)
- DigitalOcean (App Platform)
```

## Performance Metrics

### Target Response Times
- GET endpoints: < 100ms
- POST endpoints: < 500ms
- AI generation: < 30s (expected)

### Database Performance
- Indexes on: niche_id, user_id, status, created_at
- Connection pool: 10-20 connections
- Query timeout: 30 seconds

### Frontend Performance
- Bundle size: < 300KB (gzipped)
- Core Web Vitals: Green
- Mobile-friendly: Yes

## Testing Strategy

### Not Implemented in MVP (Future)
- Unit tests (Jest for frontend, pytest for backend)
- Integration tests (API routes)
- E2E tests (Playwright)
- Load tests (k6)

## Monitoring & Observability

### Not Implemented in MVP (Future)
- Application metrics (Prometheus)
- Distributed tracing (Jaeger)
- Error tracking (Sentry)
- Logs aggregation (ELK)
- Uptime monitoring (Pingdom)

## File Structure

```
handholding-engine/
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── main.py             # Main application
│   │   ├── requirements.txt    # Python dependencies
│   │   └── Dockerfile          # Container config
│   └── web/                    # Next.js frontend
│       ├── app/                # App Router pages
│       │   ├── page.tsx        # Dashboard
│       │   ├── layout.tsx      # Root layout
│       │   ├── globals.css     # Global styles
│       │   ├── niches/
│       │   ├── competitors/
│       │   ├── ideas/
│       │   ├── scripts/
│       │   └── asset-pack/
│       ├── lib/
│       │   └── api.ts          # API client
│       ├── package.json        # Dependencies
│       ├── tsconfig.json       # TypeScript config
│       ├── next.config.js      # Next.js config
│       ├── tailwind.config.js  # Tailwind config
│       └── Dockerfile          # Container config
├── docker-compose.yml          # Multi-container setup
├── .env.example                # Environment template
├── .gitignore                  # Git ignore rules
├── README.md                   # User documentation
├── SETUP.md                    # Setup instructions
├── ARCHITECTURE.md             # This file
└── seed.sql                    # Sample data
```

## Dependencies

### Frontend (Next.js)
- next: Framework
- react: UI library
- typescript: Type safety
- tailwindcss: Styling
- axios: HTTP client
- autoprefixer: CSS tool
- postcss: CSS processor

### Backend (FastAPI)
- fastapi: Web framework
- uvicorn: ASGI server
- sqlalchemy: ORM
- psycopg2-binary: PostgreSQL driver
- pydantic: Validation
- python-dotenv: Config
- httpx: HTTP client

### Infrastructure
- PostgreSQL: Database
- Docker: Containerization
- Docker Compose: Orchestration
- Nginx: Reverse proxy (optional)

## Upgrade Path

### Phase 1 (Current)
- Single user
- No auth
- Manual deployment

### Phase 2
- Multi-user with JWT auth
- User-specific data
- Improved error handling
- Better logging

### Phase 3
- Queue system for AI generation
- Real-time progress updates
- Video upload integration
- Analytics dashboard

### Phase 4
- Mobile app
- Team collaboration
- Advanced analytics
- API marketplace
