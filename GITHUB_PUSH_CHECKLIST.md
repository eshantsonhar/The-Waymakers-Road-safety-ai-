# RoadSoS — GitHub Push Checklist
## Pre-Publish Security & Cleanup Verification

Use this checklist **before pushing to any public repository** to ensure no secrets, credentials, or garbage files are committed.

---

## ✅ FILES THAT ARE SAFE TO PUSH

```
START_ROADSOS.bat           - One-click launch script
README.md                   - Project documentation
GITHUB_PUSH_CHECKLIST.md    - This file
docker-compose.yml          - Docker configuration
docker/init-db.sql          - Database initialization
.gitignore                  - Git exclusion rules
LICENSE                     - License file
backend/
├── app/                    - Application source code (ALL)
├── requirements.txt        - Python dependencies
├── Dockerfile              - Container build
├── .env.example            - Example environment (NO real secrets)
├── Dockerfile              - Container config
frontend/
├── src/                    - React source code (ALL)
├── index.html              - Entry point
├── package.json            - Node dependencies
├── vite.config.ts          - Build configuration
├── tsconfig.json           - TypeScript config
├── postcss.config.js       - CSS config
├── tailwind.config.js      - Tailwind config
├── Dockerfile              - Container config
hardware_module_code/       - Hardware simulation (ALL)
datasets/                   - Dataset documentation only
scripts/                    - Utility scripts
```

---

## ❌ FILES NOT SAFE TO PUSH — MUST NOT COMMIT

```
.env                        - CONTAINS SECRETS (API keys, DB URLs)
.env.local                  - Local secrets
*.pem, *.key, *.cert        - SSL/TLS private keys
secrets.json                - Secret configurations
api_keys.txt                - API keys in plain text
__pycache__/                - Python bytecode cache
node_modules/               - Node.js dependencies (regenerate via npm install)
.venv/                      - Python virtual environment
venv/                       - Alternative venv name
.env/                       - Alternative env name
dist/                       - Build artifacts
build/                      - Build artifacts
*.db, *.sqlite, *.sqlite3   - Database files (local data)
logs/                       - Application logs
*.log                       - Individual log files
.vscode/                    - IDE settings (may contain secrets)
.idea/                      - JetBrains IDE settings
.DS_Store                   - macOS system files
Thumbs.db                   - Windows thumbnail cache
.kiro/                      - AI editor workspace artifacts
*.tmp, *.temp               - Temporary files
*.bak, *.backup             - Backup files
```

---

## 🔴 SECURITY WARNINGS

### 1. Environment Variables (CRITICAL)

The file `backend/.env` **MUST NOT** be committed. It contains:

```ini
# NEVER commit these values:
DATABASE_URL=postgresql://user:password@host:port/dbname
SECRET_KEY=your-secret-key-here
API_KEY=your-api-key
```

**Solution:** The repo includes `backend/.env.example` which contains placeholder values. Copy it to create your local `.env`:

```bash
copy backend\.env.example backend\.env
```

### 2. API Keys

Check for hardcoded API keys in:
- Source code (search for `api_key`, `apikey`, `secret`, `token`, `password`)
- Configuration files
- Test files
- Comments/documentation

Run this search:
```bash
cd RoadSoS
grep -r --include="*.py" --include="*.ts" --include="*.tsx" --include="*.json" \
  -i "api_key\|apikey\|secret\|token\|password\|auth_token" . | grep -v node_modules | grep -v __pycache__
```

### 3. Database Dumps

```bash
# Remove any database dumps before committing
del /s *.sql.gz *.dump *.db *.sqlite
```

---

## 🧹 PRE-PUSH CLEANUP CHECKLIST

### Step 1: Remove Sensitive Files

```bash
# Remove local environment file
del backend\.env

# Remove Python cache
for /r /d %i in (__pycache__) do rmdir /s /q "%i" 2>nul

# Remove node_modules if accidentally present
rmdir /s /q frontend\node_modules 2>nul
```

### Step 2: Verify Git Status

```bash
git status
```

Expected output should show **only**:
- Source code files
- Documentation
- Configuration templates (.env.example, NOT .env)
- Static assets

**WARNING:** If `backend/.env`, `frontend/node_modules`, or `__pycache__` appear in the list, **DO NOT PUSH**. Run cleanup first.

### Step 3: Review All Changes

```bash
# Review every file about to be committed
git diff --cached --stat

# Check for secrets in staged files
git diff --cached -S "password\|secret\|api_key" -- . 2>nul
```

### Step 4: Test One-Click Run

**Before pushing to a public repo**, verify the system works:

```bash
# 1. Clone to a fresh directory
git clone <your-repo-url> RoadSoS-test
cd RoadSoS-test

# 2. Run the startup script
START_ROADSOS.bat
```

The system should:
- Install all dependencies automatically
- Start backend on port 8000
- Start frontend on port 5173
- Open browser automatically
- Show live demo with auto-generated incidents

Fix any errors before pushing.

---

## ✅ FINAL VERIFICATION CHECKLIST

Before `git push`:

- [ ] `backend/.env` is **NOT** in the staging area
- [ ] No `__pycache__/` directories are staged
- [ ] No `node_modules/` directories are staged
- [ ] No `.db`, `.sqlite`, or `.sqlite3` files are staged
- [ ] No `.pem`, `.key`, `.cert` files are staged
- [ ] No `.kiro/` or AI editor artifact directories are staged
- [ ] No `logs/` or `*.log` files are staged
- [ ] `.gitignore` covers all the above categories
- [ ] All source code files compile successfully
- [ ] `START_ROADSOS.bat` runs to completion
- [ ] System launches in browser without manual steps

```bash
# Final safe push command
git add -A
git status                    # Verify ONLY expected files
git commit -m "RoadSoS v1.0 - AI Emergency Response Platform"
git push origin main
```

---

## 📦 Dependency Verification

### Python (backend/requirements.txt)
```
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
httpx>=0.25.0
websockets>=12.0
pydantic>=2.5.0
python-dotenv>=1.0.0
```

### Node.js (frontend/package.json)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-leaflet": "^4.2.1",
    "leaflet": "^1.9.4",
    "zustand": "^4.4.0",
    "framer-motion": "^10.16.0",
    "lucide-react": "^0.290.0"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "typescript": "^5.2.0"
  }
}
```

---

## 🚨 EMERGENCY — If Secrets Were Committed

**If you accidentally committed a secret to a public repo:**

1. **IMMEDIATELY rotate/revoke the exposed credential** (API key, database password, etc.)
2. Remove the file from git history:
   ```bash
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch path/to/secrets-file" \
     --prune-empty --tag-name-filter cat -- --all
   ```
3. Force push the cleaned history:
   ```bash
   git push origin --force --all
   ```
4. Inform any collaborators to re-clone

---

> **Last updated:** May 2026  
> **Maintainer:** RoadSoS Team  
> **Security contact:** Keep internal