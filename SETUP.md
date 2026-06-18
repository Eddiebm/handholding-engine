# Setup Guide

## Development Setup

### 1. Prerequisites
- Docker Desktop installed and running
- OpenAI API key (or compatible API endpoint)

### 2. Configure Environment
```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-your-actual-key-here
```

### 3. Start Services
```bash
docker-compose up
```

This will:
- Start PostgreSQL on port 5432
- Start FastAPI backend on port 8000
- Start Next.js frontend on port 3000

Wait for all services to be healthy (Docker will show green checkmarks).

### 4. Verify Services

**Frontend:** http://localhost:3000
- Should show dashboard

**Backend API:** http://localhost:8000
- Should return `{"status": "ok"}`

**API Documentation:** http://localhost:8000/docs
- Interactive Swagger UI for all endpoints

### 5. First Run

1. Open http://localhost:3000
2. Click "Create Niche"
3. Fill in:
   - Niche: "Personal Finance"
   - Audience: "Young professionals"
   - Monetization: "Ad revenue + affiliate"
   - Notes: "Practical tips"
4. Click "Add Competitors" and paste 5 YouTube titles
5. Click "Generate Ideas"
6. Score and select your best idea
7. Generate script
8. Generate asset pack

### Troubleshooting

#### Port 3000 already in use
```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9

# Or use a different port
docker-compose up -e "PORT=3001"
```

#### Database connection error
```bash
# Check if postgres is running
docker ps | grep postgres

# View logs
docker-compose logs postgres

# Reset database
docker-compose down -v
docker-compose up
```

#### API key not working
- Check your .env file is in the root directory
- Make sure OPENAI_API_KEY starts with `sk-`
- Verify your key is active at https://platform.openai.com/account/api-keys

#### "Cannot connect to API"
- Verify backend is running: http://localhost:8000
- Check NEXT_PUBLIC_API_URL is correct in docker-compose.yml
- View logs: `docker-compose logs api`

#### Node modules not installed
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up
```

## Production Setup (Hetzner)

### 1. SSH into Server
```bash
ssh root@your-server-ip
```

### 2. Install Docker
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
```

### 3. Clone Repository
```bash
git clone <your-repo-url>
cd handholding-engine
```

### 4. Setup Environment
```bash
cp .env.example .env
nano .env
# Add OPENAI_API_KEY
```

### 5. Start Services
```bash
docker-compose up -d
```

### 6. Setup Nginx (Optional)

Create `/etc/nginx/sites-available/handholding`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
    }
}
```

Enable and restart:
```bash
ln -s /etc/nginx/sites-available/handholding /etc/nginx/sites-enabled/
systemctl restart nginx
```

### 7. Setup HTTPS (Let's Encrypt)
```bash
apt-get install certbot python3-certbot-nginx
certbot --nginx -d your-domain.com
```

### 8. Auto-restart on Reboot
```bash
crontab -e
# Add: @reboot cd /path/to/handholding-engine && docker-compose up -d
```

## Database Management

### Access Database
```bash
docker-compose exec postgres psql -U handholding -d handholding
```

### Load Seed Data
```bash
docker-compose exec postgres psql -U handholding -d handholding < seed.sql
```

### Backup Database
```bash
docker-compose exec postgres pg_dump -U handholding handholding > backup.sql
```

### Restore Database
```bash
docker-compose exec postgres psql -U handholding -d handholding < backup.sql
```

## Development Tips

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f web
```

### Access Backend Shell
```bash
docker-compose exec api bash
```

### Access Frontend Shell
```bash
docker-compose exec web bash
```

### Rebuild Services
```bash
docker-compose build --no-cache
```

### Scale Services
```bash
docker-compose up --scale api=3
```

## Configuration

### Change Model
Edit `apps/api/main.py`:
```python
"model": "gpt-4-turbo",  # Change this
```

### Change API Endpoint
Edit `.env`:
```
OPENAI_API_BASE=https://your-api.example.com/v1
```

### Change Database
Edit `.env`:
```
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

### Change Ports
Edit `docker-compose.yml` and change port mappings.

## Performance Tuning

### Database
- Add indexes to frequently queried columns
- Run `VACUUM` periodically
- Monitor with `pg_stat_statements`

### API
- Add response caching
- Implement rate limiting
- Use connection pooling

### Frontend
- Enable Next.js image optimization
- Add service worker for offline support
- Implement code splitting

## Security Notes

- **Never commit .env files**
- Use strong passwords for database
- Keep Docker images updated
- Use HTTPS in production
- Implement authentication for multi-user
- Validate all user inputs
- Use environment variables for secrets
- Implement CORS properly

## Monitoring

### Health Checks
```bash
curl http://localhost:8000/health
```

### Performance
- Use `docker stats` to monitor resources
- Check database slow queries
- Monitor API response times

### Logs
- Aggregate logs with ELK or similar
- Set up alerts for errors
- Monitor disk space
