# 🚀 Deployment Plan — Zomato AI Restaurant Recommender

> **Backend → Railway** (FastAPI + SQLite + Groq AI)
> **Frontend → Vercel** (Static HTML/CSS/JS)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Pre-Deployment Checklist](#2-pre-deployment-checklist)
3. [Backend Deployment — Railway](#3-backend-deployment--railway)
4. [Frontend Deployment — Vercel](#4-frontend-deployment--vercel)
5. [Post-Deployment Verification](#5-post-deployment-verification)
6. [Files to Create / Modify](#6-files-to-create--modify)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Architecture Overview

```
┌──────────────────────┐         HTTPS          ┌──────────────────────┐
│                      │ ──────────────────────▶ │                      │
│   Frontend (Vercel)  │                         │  Backend (Railway)   │
│                      │ ◀────────────────────── │                      │
│   index.html         │        JSON / SSE       │  FastAPI + Uvicorn   │
│   styles.css         │                         │  SQLite (zomato.db)  │
│   app.js             │                         │  Groq LLM API        │
│   api.js             │                         │                      │
└──────────────────────┘                         └──────────────────────┘
       Vercel CDN                                    Railway Container
```

---

## 2. Pre-Deployment Checklist

- [x] Project pushed to GitHub repository
- [ ] `.gitignore` created (see [Section 6](#6-files-to-create--modify))
- [ ] Backend `Procfile` created
- [ ] Backend `railway.json` created
- [ ] `requirements.txt` updated with pinned versions
- [ ] `api.js` updated to use environment-based API URL
- [ ] `main.py` CORS origins updated to include Vercel domain
- [ ] `main.py` host/port configured for Railway
- [ ] `vercel.json` created for frontend
- [ ] `GROQ_API_KEY` added to Railway environment variables
- [ ] `zomato.db` is committed to the repo (or data ingestion runs on deploy)

---

## 3. Backend Deployment — Railway

### 3.1 Create Required Files

#### `backend/Procfile`

```
web: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

> **Why?** Railway assigns a dynamic `$PORT`. Uvicorn must bind to `0.0.0.0` (not `127.0.0.1`) so Railway's proxy can reach it.

#### `backend/railway.json`

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn backend.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

#### Update `backend/requirements.txt`

```txt
fastapi
uvicorn[standard]
pandas
datasets
groq
sse-starlette
python-dotenv
```

> **Note:** Added `[standard]` to uvicorn for production-grade performance (includes `uvloop` and `httptools`).

### 3.2 Update `backend/main.py`

#### a) Update CORS origins to include your Vercel domain:

```python
import os

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:5501",
    "http://127.0.0.1:5501",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "null",
]

# Add production Vercel URL from environment variable
VERCEL_URL = os.environ.get("VERCEL_URL", "")
if VERCEL_URL:
    ALLOWED_ORIGINS.append(VERCEL_URL)

# Also allow any *.vercel.app preview deployments
FRONTEND_URL = os.environ.get("FRONTEND_URL", "")
if FRONTEND_URL:
    ALLOWED_ORIGINS.append(FRONTEND_URL)
```

#### b) Update the entrypoint to use `$PORT`:

```python
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False)
```

### 3.3 Update `backend/db.py`

The current `DB_PATH` uses relative path resolution. This should work in Railway since the repo is cloned as-is, but ensure `zomato.db` is committed to the repository:

```python
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'zomato.db')
```

> ⚠️ **Important:** The `zomato.db` file is **~582 MB**. Make sure your GitHub repo and Railway plan can handle this. If the file is too large for GitHub (>100 MB), you'll need to use [Git LFS](https://git-lfs.github.com/) or run `ingest_data.py` as a build step on Railway.

### 3.4 Railway Setup Steps

1. **Go to** [railway.app](https://railway.app) → Sign in with GitHub.

2. **Create New Project** → Select **"Deploy from GitHub repo"** → Pick your `Zomato Recommendation` repository.

3. **Set Root Directory** → In the service settings, set the **root directory** to `/backend` (since `Procfile` and `requirements.txt` live there).

   > ⚠️ However, because `db.py` references `zomato.db` one level up (`os.path.dirname(os.path.dirname(__file__))`), and `main.py` imports from `backend.db`, you may need to set the root directory to `/` (the project root) instead. In that case, Railway will auto-detect the Python project from `backend/requirements.txt`, and you should move the `Procfile` to the project root.

   **Recommended approach — Root Directory = `/` (project root):**
   - Move `Procfile` to the project root (`Zomato Recommendation/Procfile`)
   - Railway nixpacks will detect `backend/requirements.txt` or you can place a root-level `requirements.txt`

4. **Set Environment Variables** in Railway dashboard:

   | Variable        | Value                                            |
   |-----------------|--------------------------------------------------|
   | `GROQ_API_KEY`  | `your-groq-api-key`                              |
   | `FRONTEND_URL`  | `https://your-project.vercel.app` (set after Vercel deploy) |
   | `VERCEL_URL`    | `https://your-project.vercel.app` (same as above) |

   > 🔒 **Never commit your API key to the repo.** Use Railway's environment variables panel.

5. **Deploy** — Railway will auto-build and deploy. Watch the build logs for errors.

6. **Note your Railway URL** — It will look like: `https://your-service-name.up.railway.app`

### 3.5 Database Strategy (Important)

Since `zomato.db` is ~582 MB, you have **two options**:

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| **A** | Commit `zomato.db` to repo (use Git LFS for files >100MB) | Simple, works immediately | Large repo, slow clones |
| **B** | Run `ingest_data.py` as a build/deploy step on Railway | Clean repo, fresh data each deploy | Slower deploys, needs HuggingFace access |

**For Option A (Git LFS):**
```bash
git lfs install
git lfs track "*.db"
git add .gitattributes
git add zomato.db
git commit -m "Add database with LFS"
git push
```

**For Option B (Build step):**
Update `Procfile` or `railway.json` start command:
```
web: python -m backend.ingest_data && uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

---

## 4. Frontend Deployment — Vercel

### 4.1 Update `frontend/api.js`

Replace the hardcoded localhost URL with a dynamic one:

```javascript
/**
 * API Base URL — uses the Railway backend in production,
 * falls back to localhost for local development.
 */
const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8000'
  : 'https://your-service-name.up.railway.app';  // ← Replace with your Railway URL
```

> **Tip:** You can also use Vercel's environment variables at build time if you switch to a framework. For a static site, the above runtime check works perfectly.

### 4.2 Create `frontend/vercel.json`

```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" }
      ]
    }
  ]
}
```

### 4.3 Vercel Setup Steps

1. **Go to** [vercel.com](https://vercel.com) → Sign in with GitHub.

2. **Import Project** → Select your `Zomato Recommendation` repository.

3. **Configure Project:**

   | Setting             | Value         |
   |---------------------|---------------|
   | **Framework Preset** | `Other`       |
   | **Root Directory**   | `frontend`    |
   | **Build Command**    | *(leave empty — no build step needed for static files)* |
   | **Output Directory** | `.`           |

4. **Deploy** — Vercel will deploy your static frontend instantly.

5. **Note your Vercel URL** — It will look like: `https://your-project.vercel.app`

6. **Go back to Railway** → Add `FRONTEND_URL` = `https://your-project.vercel.app` so CORS allows your frontend.

### 4.4 Custom Domain (Optional)

If you have a custom domain:
1. Go to Vercel → Project Settings → Domains
2. Add your domain (e.g., `zomato-ai.yourdomain.com`)
3. Update Railway's `FRONTEND_URL` env var with the custom domain

---

## 5. Post-Deployment Verification

### Checklist

| # | Test | URL | Expected |
|---|------|-----|----------|
| 1 | Backend health check | `https://<railway-url>/health` | `{"success": true, "data": {"status": "healthy", ...}}` |
| 2 | Locations endpoint | `https://<railway-url>/api/meta/locations` | JSON array of locations |
| 3 | Cuisines endpoint | `https://<railway-url>/api/meta/cuisines` | JSON array of cuisines |
| 4 | Frontend loads | `https://<vercel-url>` | UI renders with dropdowns populated |
| 5 | Recommendation flow | Submit form on frontend | AI recommendations appear |
| 6 | CORS works | Check browser console for CORS errors | No CORS errors |

### Quick Verification Commands

```bash
# Test backend health
curl https://your-service-name.up.railway.app/health

# Test locations
curl https://your-service-name.up.railway.app/api/meta/locations

# Test recommendation
curl -X POST https://your-service-name.up.railway.app/api/restaurants/recommend \
  -H "Content-Type: application/json" \
  -d '{"location": "Banashankari", "cuisine": "North Indian", "budget": "medium", "min_rating": 3.5}'
```

---

## 6. Files to Create / Modify

### New Files

| File | Purpose |
|------|---------|
| `.gitignore` | Exclude `.venv`, `__pycache__`, `.env`, etc. |
| `Procfile` (project root) | Railway start command |
| `railway.json` (project root) | Railway build/deploy config |
| `frontend/vercel.json` | Vercel routing and headers config |

### `.gitignore` (project root)

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/

# Virtual environment
.venv/
venv/
env/

# Environment variables (NEVER commit secrets)
.env

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Database (uncomment if using Git LFS or build-step ingestion)
# zomato.db
```

### Modified Files

| File | Change |
|------|--------|
| `backend/main.py` | Add dynamic CORS origins from env vars, update entrypoint port |
| `backend/requirements.txt` | Add `uvicorn[standard]` |
| `frontend/api.js` | Replace hardcoded `localhost:8000` with Railway URL |

---

## 7. Troubleshooting

### Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| **CORS errors in browser** | Vercel domain not in `ALLOWED_ORIGINS` | Add `FRONTEND_URL` env var on Railway with your Vercel URL |
| **502 Bad Gateway on Railway** | App not binding to `$PORT` | Ensure `--port $PORT` in start command |
| **Module not found: `backend.db`** | Wrong root directory on Railway | Set root directory to `/` (project root), not `/backend` |
| **`zomato.db` not found** | DB file not deployed | Use Git LFS or run `ingest_data.py` on deploy |
| **Groq API errors** | Missing or invalid API key | Verify `GROQ_API_KEY` in Railway env vars |
| **Frontend shows "Cannot connect to backend"** | Wrong `API_BASE` in `api.js` | Update with your Railway URL |
| **Build fails on Railway** | Missing dependencies | Check `requirements.txt` has all packages |
| **Git push rejected (file too large)** | `zomato.db` > 100 MB | Use Git LFS: `git lfs track "*.db"` |

### Useful Railway CLI Commands

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link to project
railway link

# View logs
railway logs

# Set environment variable
railway variables set GROQ_API_KEY=your-key-here

# Deploy
railway up
```

---

## Deployment Sequence (Step-by-Step Summary)

```
1. Create .gitignore, Procfile, railway.json, vercel.json
2. Update main.py (CORS + PORT)
3. Update api.js (dynamic API_BASE)
4. Commit and push to GitHub
5. Deploy backend on Railway
   → Set GROQ_API_KEY env var
   → Note the Railway URL
6. Deploy frontend on Vercel
   → Set root directory to "frontend"
   → Note the Vercel URL
7. Go back to Railway → Set FRONTEND_URL = Vercel URL
8. Redeploy Railway (to pick up new CORS origin)
9. Verify all endpoints and the full flow
```

---

> **📝 Note:** After both deployments are live, remember to regenerate your `GROQ_API_KEY` if it was ever exposed in the `.env` file that was pushed to GitHub. Always treat it as compromised if it touched version control.
