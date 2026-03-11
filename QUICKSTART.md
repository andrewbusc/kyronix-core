# Quick Start: Deploy to Railway

## 1. Push to GitHub
```bash
git add .
git commit -m "Add Railway deployment config"
git push origin main
```

## 2. Railway Setup (5 minutes)
1. Go to https://railway.app → Sign in with GitHub
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your Kyronix Core repo

## 3. Add Services (in this order)
### a) PostgreSQL Database
- Click "+ New" → "Database" → "PostgreSQL"
- Done! (DATABASE_URL auto-created)

### b) Backend Service
- Click "+ New" → "GitHub Repo" → Select repo
- Settings → Set Root Directory: `backend`
- Settings → Variables → Add all from DEPLOYMENT.md
- Important: Set `DATABASE_URL=${{Postgres.DATABASE_URL}}`
- Deploy!

### c) Frontend Service  
- Click "+ New" → "GitHub Repo" → Select repo
- Settings → Set Root Directory: `frontend`
- Settings → Variables → Add: `VITE_API_URL=<backend-url>`
- Deploy!

## 4. Connect Services
- Copy backend URL → Update frontend `VITE_API_URL`
- Copy frontend URL → Update backend `ALLOW_ORIGINS`
- Redeploy both

## 5. Custom Domain
- Frontend Settings → Domains → Add `core.kyronix.ai`
- Backend Settings → Domains → Add `api.core.kyronix.ai`
- Update DNS with provided CNAME records

## Done! 🚀
Visit https://core.kyronix.ai

---

**Need help?** Check DEPLOYMENT.md for detailed instructions.
