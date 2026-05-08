# 🔒 GitHub Push Checklist — RoadSoS

## ✅ Files SAFE to Push

### Root Level
- [x] `README.md`
- [x] `GITHUB_PUSH_CHECKLIST.md`
- [x] `docker-compose.yml`
- [x] `.gitignore`

### Backend
- [x] `backend/app/` — All Python source code
- [x] `backend/requirements.txt`
- [x] `backend/Dockerfile`
- [x] `backend/.env.example` ← EXAMPLE only, NOT `.env`

### Frontend
- [x] `frontend/src/` — All TypeScript/React source code
- [x] `frontend/package.json`
- [x] `frontend/package-lock.json`
- [x] `frontend/vite.config.ts`
- [x] `frontend/tsconfig.json`
- [x] `frontend/tailwind.config.js`
- [x] `frontend/postcss.config.js`
- [x] `frontend/index.html`
- [x] `frontend/Dockerfile`
- [x] `frontend/public/` — Static assets

### Docker & Scripts
- [x] `docker/init-db.sql`
- [x] `scripts/seed.py`
- [x] `scripts/demo_scenario.py`

### Datasets & Docs
- [x] `datasets/README.md`

---

## ❌ Files to NEVER Push

### Secrets & Credentials
- [ ] `backend/.env` — Contains database passwords and secret keys
- [ ] `*.pem`, `*.key`, `*.cert` — SSL certificates
- [ ] `secrets.json`, `credentials.json` — Any credential files
- [ ] `api_keys.txt` — API keys

### Kiro IDE Metadata (CRITICAL)
- [ ] `.kiro/` — Entire directory
- [ ] `.kiro/specs/` — Spec documents with internal metadata
- [ ] `.kiro/settings/` — IDE settings
- [ ] Any file matching `.kiro/**`

### Build Artifacts
- [ ] `frontend/dist/` — Built frontend
- [ ] `frontend/node_modules/` — Dependencies
- [ ] `backend/__pycache__/` — Python cache
- [ ] `backend/venv/` — Virtual environment
- [ ] `backend/.venv/` — Virtual environment

### Database & Docker Volumes
- [ ] `postgres_data/` — Database files
- [ ] `docker/volumes/` — Docker volume data
- [ ] `*.dump`, `*.sql.gz` — Database dumps

### ML Models (Large Files)
- [ ] `*.pkl`, `*.joblib` — Trained model files
- [ ] `*.h5`, `*.hdf5` — Model weights
- [ ] `models/trained/` — Trained model directory

### Logs & Temp Files
- [ ] `*.log` — Log files
- [ ] `logs/` — Log directory
- [ ] `tmp/`, `temp/` — Temporary files

---

## 🔐 Security Warnings

### 1. Secret Key
The `SECRET_KEY` in `.env.example` is a placeholder:
```
SECRET_KEY=roadsos-dev-secret-key-change-in-production-2024
```
**NEVER use this in production.** Generate a secure key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 2. Database Password
Default password `roadsos_secret` is for local development only.
Change before any deployment:
```bash
# In docker-compose.yml and .env
POSTGRES_PASSWORD=<strong-random-password>
```

### 3. CORS Origins
Default allows `localhost` only. For production, restrict to your domain:
```bash
ALLOWED_ORIGINS=["https://your-domain.com"]
```

### 4. Debug Mode
Ensure `DEBUG=false` in production to prevent stack trace exposure.

### 5. API Authentication
The prototype has no authentication. Add JWT/OAuth before any public deployment.

---

## 🌍 Environment Variables Reminder

Before pushing, verify these are NOT hardcoded anywhere in source:
- [ ] Database passwords
- [ ] Secret keys
- [ ] API keys (if any added)
- [ ] Internal IP addresses
- [ ] Personal information

All sensitive config should use environment variables from `.env` (which is gitignored).

---

## 🧹 Pre-Push Cleanup Checklist

Run these before pushing:

```bash
# 1. Remove Python cache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null

# 2. Remove node_modules (should be gitignored)
# Already in .gitignore

# 3. Verify .env is not tracked
git status | grep ".env"
# Should show nothing

# 4. Verify .kiro is not tracked
git status | grep ".kiro"
# Should show nothing

# 5. Check for secrets in staged files
git diff --cached | grep -i "password\|secret\|key\|token"
# Review any matches carefully

# 6. Verify .gitignore is working
git check-ignore -v .kiro/
git check-ignore -v backend/.env

# 7. Run a final check
git status
git diff --cached --stat
```

---

## 📋 Push Procedure

```bash
# 1. Create a new branch (never push directly to main)
git checkout -b feature/initial-prototype

# 2. Stage only safe files
git add README.md GITHUB_PUSH_CHECKLIST.md docker-compose.yml .gitignore
git add backend/app/ backend/requirements.txt backend/Dockerfile backend/.env.example
git add frontend/src/ frontend/package.json frontend/vite.config.ts
git add frontend/tsconfig.json frontend/tailwind.config.js frontend/postcss.config.js
git add frontend/index.html frontend/Dockerfile frontend/public/
git add docker/ scripts/ datasets/

# 3. Verify staged files
git status

# 4. Commit
git commit -m "feat: RoadSoS initial prototype - AI emergency response platform"

# 5. Push to new branch
git push -u origin feature/initial-prototype

# 6. Create PR with description
# Title: "RoadSoS: AI-Assisted Emergency Response Platform (Hackathon Prototype)"
```

---

## 🏷️ Recommended PR Description Template

```markdown
## RoadSoS — AI-Assisted Emergency Response Platform

### Summary
Full-stack prototype of an AI-powered road accident detection and emergency 
coordination system optimized for Indian road conditions.

### What's Included
- Accident Detection Engine (sensor fusion, ML scoring)
- Emergency Coordination Engine (auto-dispatch, hospital routing)
- Hospital Intelligence Engine (7-factor suitability scoring)
- Risk Prediction Engine (ML heatmaps, blackspot detection)
- Command Center Dashboard (real-time map, WebSocket)
- Citizen Interface (SOS trigger, ambulance tracking)
- Admin Analytics Dashboard (trends, efficiency metrics)

### Tech Stack
FastAPI + React + TypeScript + PostgreSQL/PostGIS + Docker

### Testing
- DEMO_MODE=true generates realistic simulated data
- Run `python scripts/demo_scenario.py` for scenario testing
- API docs at http://localhost:8000/api/docs

### Not Included (Security)
- .env files (use .env.example as template)
- Database dumps
- Trained ML models
```

---

*Last updated: See git log*
