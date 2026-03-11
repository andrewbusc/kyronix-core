# Railway Deployment Guide for Kyronix Core

## Prerequisites
- GitHub account with this repo pushed
- Railway account (sign up at https://railway.app)

## Step-by-Step Deployment

### 1. Create Railway Project
1. Go to https://railway.app/new
2. Click "Deploy from GitHub repo"
3. Select your Kyronix Core repository
4. Railway will create a new project

### 2. Add PostgreSQL Database
1. In your Railway project, click "+ New"
2. Select "Database" → "Add PostgreSQL"
3. Railway will provision a Postgres database
4. Note: The `DATABASE_URL` variable is automatically created

### 3. Deploy Backend Service
1. Click "+ New" → "GitHub Repo" → Select your repo
2. Configure the service:
   - **Root Directory**: `/backend`
   - **Build Command**: (auto-detected from Dockerfile)
   - **Start Command**: (uses railway.json config)
3. Add environment variables (Settings → Variables):
   ```
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   SECRET_KEY=<generate-random-secret>
   ACCESS_TOKEN_EXPIRE_MINUTES=480
   PASSWORD_RESET_EXPIRE_MINUTES=60
   DEFAULT_ADMIN_EMAIL=admin@kyronix.ai
   DEFAULT_ADMIN_PASSWORD=<secure-password>
   ALLOW_ORIGINS=https://<your-frontend-url>.railway.app
   TIME_ZONE=America/Los_Angeles
   COMPANY_ADDRESS=28 Geary St Suite 650 San Francisco, CA 94108
   PAYROLL_CONTACT_EMAIL=hr@kyronix.ai
   VERIFICATION_SIGNER_NAME=Sandra Morrow
   VERIFICATION_SIGNER_CREDENTIALS=PHR, SHRM-CP
   VERIFICATION_SIGNER_TITLE=HR Manager
   VERIFICATION_SIGNER_EMAIL=hr@kyronix.ai
   VERIFICATION_EMAIL_SIGNATURE_NAME=Sandra Morrow
   VERIFICATION_EMAIL_SIGNATURE_TITLE=HR Coordinator/ Administration
   VERIFICATION_EMPLOYER_DISPLAY_NAME=Kyronix LLC
   VERIFICATION_PHONE=855-912-9883
   VERIFICATION_FAX=855-912-9392
   VERIFICATION_FOOTER_ADDRESS=28 Geary St. Suite 650 * San Francisco, CA 94108
   VERIFICATION_BODY_FONT_PATH=app/assets/fonts/CenturyGothic.ttf
   VERIFICATION_SIGNATURE_FONT_PATH=app/assets/fonts/VladimirScript-Regular.ttf
   SMTP_HOST=mail.privateemail.com
   SMTP_PORT=587
   SMTP_USERNAME=hr@kyronix.ai
   SMTP_PASSWORD=<your-smtp-password>
   SMTP_USE_TLS=true
   SMTP_USE_SSL=false
   SMTP_FROM_EMAIL=hr@kyronix.ai
   SMTP_FROM_NAME=Kyronix LLC HR
   S3_BUCKET=kyronix-core-paystubs
   S3_REGION=us-west-1
   S3_ACCESS_KEY_ID=<your-aws-key>
   S3_SECRET_ACCESS_KEY=<your-aws-secret>
   ```
4. Click "Deploy"
5. Once deployed, copy the public URL (e.g., `https://backend-production-xxxx.up.railway.app`)

### 4. Deploy Frontend Service
1. Click "+ New" → "GitHub Repo" → Select your repo again
2. Configure the service:
   - **Root Directory**: `/frontend`
   - **Build Command**: (auto-detected)
   - **Start Command**: (uses railway.json config)
3. Add environment variable:
   ```
   VITE_API_URL=https://<your-backend-url>.railway.app
   ```
4. Click "Deploy"
5. Copy the frontend public URL

### 5. Update Backend CORS
1. Go back to backend service settings
2. Update `ALLOW_ORIGINS` variable to include your frontend URL:
   ```
   ALLOW_ORIGINS=https://<your-frontend-url>.railway.app
   ```
3. Redeploy backend

### 6. Setup Custom Domain (core.kyronix.ai)
1. In Railway, go to your frontend service
2. Click "Settings" → "Domains"
3. Click "Custom Domain"
4. Enter: `core.kyronix.ai`
5. Railway will provide DNS records (CNAME)
6. Add the CNAME record to your DNS provider:
   - Type: `CNAME`
   - Name: `core` (or `@` for root domain)
   - Value: `<provided-by-railway>.railway.app`
7. Repeat for backend with subdomain `api.core.kyronix.ai`
8. Update environment variables with new domains

## Production Checklist
- [ ] Change `DEFAULT_ADMIN_PASSWORD` to a secure password
- [ ] Generate secure `SECRET_KEY` (use: `openssl rand -hex 32`)
- [ ] Configure SMTP credentials for email
- [ ] Setup AWS S3 for paystub storage
- [ ] Update all email addresses from examples
- [ ] Enable Railway's automatic deployments on git push
- [ ] Setup monitoring/alerts in Railway dashboard
- [ ] Test admin login at https://core.kyronix.ai

## Costs
- Railway free tier: $5 credit/month
- Estimated usage: ~$10-20/month for hobby use
- Upgrade to Developer plan ($20/month) for production

## Troubleshooting
- Check logs: Railway dashboard → Service → "Logs" tab
- Database connection: Ensure `DATABASE_URL` references `${{Postgres.DATABASE_URL}}`
- CORS errors: Verify `ALLOW_ORIGINS` includes frontend URL
- Build failures: Check Dockerfile and requirements.txt
