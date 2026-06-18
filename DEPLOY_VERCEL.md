# Deploy to Vercel

## Architecture

**Frontend:** Vercel (Next.js)
**Backend:** Render.com or Railway (FastAPI)
**Database:** Neon (PostgreSQL)

## Step 1: Setup Database (Neon)

1. Go to https://neon.tech
2. Sign up (free tier available)
3. Create a new project
4. Get `DATABASE_URL`
5. Save it for later

## Step 2: Deploy Backend (Render)

### Option A: Render.com (Recommended - Free tier)

1. Go to https://render.com
2. Sign up
3. Create new "Web Service"
4. Connect GitHub (or paste repo URL)
5. Build command: `pip install -r requirements.txt`
6. Start command: `uvicorn apps.api.main:app --host 0.0.0.0 --port $PORT`
7. Environment variables:
   ```
   DATABASE_URL=postgresql://... (from Neon)
   OPENAI_API_KEY=sk-...
   ```
8. Deploy
9. Copy the service URL (e.g., `https://your-api.onrender.com`)

### Option B: Railway.app

1. Go to https://railway.app
2. Sign up
3. Create new project
4. Connect GitHub
5. Add environment variables (DATABASE_URL, OPENAI_API_KEY)
6. Deploy
7. Copy the public URL

## Step 3: Deploy Frontend (Vercel)

1. Push code to GitHub:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/handholding-engine.git
   git branch -M main
   git push -u origin main
   ```

2. Go to https://vercel.com
3. Sign in with GitHub
4. Click "New Project"
5. Import the GitHub repo
6. Configure:
   - Framework: Next.js
   - Root Directory: `apps/web`
7. Environment variables:
   ```
   NEXT_PUBLIC_API_URL=https://your-api.onrender.com
   ```
8. Deploy

## Step 4: Test

1. Visit your Vercel URL
2. Create a niche
3. Add competitors
4. Generate ideas (wait 10-20 seconds for AI)
5. Done!

## Full Architecture

```
User Browser
    ↓
Vercel (Next.js Frontend)
    ├→ Render API (FastAPI Backend)
    │   ├→ Neon Database (PostgreSQL)
    │   └→ OpenAI API
```

## Environment Variables Needed

### Neon
```
DATABASE_URL=postgresql://user:password@ep-xyz.neon.tech/dbname?sslmode=require
```

### Render/Railway Backend
```
DATABASE_URL=postgresql://...
OPENAI_API_KEY=sk-...
```

### Vercel Frontend
```
NEXT_PUBLIC_API_URL=https://your-api.onrender.com
```

## Troubleshooting

### "Cannot connect to API"
- Check NEXT_PUBLIC_API_URL is set in Vercel
- Verify Render/Railway service is running
- Check backend logs for errors

### "Database connection failed"
- Verify DATABASE_URL is correct
- Check Neon IP whitelist (allow all in free tier)
- Run migrations if needed

### "OpenAI API error"
- Verify API key is correct
- Check OpenAI account has credits
- Check rate limits

## Cost Estimate

- **Neon**: Free tier (up to 3 projects)
- **Render**: Free tier (sleeps after 15 min inactivity)
- **Railway**: Free tier ($5/month after free credits)
- **Vercel**: Free tier
- **OpenAI**: Pay-as-you-go ($0.01-0.10 per idea generation)

**Total monthly cost: ~$5-20** (depending on usage)

## Production Checklist

- [ ] Database backups enabled
- [ ] Environment variables secure
- [ ] OPENAI_API_KEY rotated
- [ ] Custom domain configured
- [ ] SSL/TLS enabled (automatic on Vercel)
- [ ] Monitoring setup (Sentry, LogRocket)
- [ ] Error alerts configured
- [ ] Database indexed for performance
- [ ] Rate limiting configured
- [ ] Authentication added (future)

## Monitoring

### Vercel
- Vercel Dashboard shows deployments and errors
- Real-time logs available

### Render/Railway
- Service logs show API errors
- Health checks available

### Neon
- Query analytics
- Connection monitoring

## Scale to Production

When ready to scale:
1. Move from Render free tier to paid ($7-50/month)
2. Add caching (Redis on Railway)
3. Add CDN (Vercel Edge Network)
4. Add monitoring (Datadog, New Relic)
5. Add auth (NextAuth.js)
6. Add queue system (Bull Queue on Railway)

## One-Click Deploy (Future)

Deploy button coming soon:
```
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/YOUR_USERNAME/handholding-engine)
```
