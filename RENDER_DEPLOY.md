# Render Deployment Instructions

## Environment Variables to Set in Render

**IMPORTANT:** Use Supabase Connection **Pooler** (not the direct database URL)

In Supabase:
1. Project Settings → Database
2. Connection string selector: Change from "Session" to **"Transaction"** ← THIS IS IMPORTANT
3. Copy the URL (it should have `pooler.supabase.com`)

Replace `[YOUR-PASSWORD]` below with your actual Supabase password:

```
DATABASE_URL=postgresql+psycopg2://postgres.ierwmfsazkdenrysscaz:Dioga2508*+@aws-1-us-east-1.pooler.supabase.com:5432/postgres

SECRET_KEY=8dkdKCCzaDcvqinCp8bJhYwJnn4AbFY840LDMaeEEZ0

ENVIRONMENT=production

ALGORITHM=HS256

ACCESS_TOKEN_EXPIRE_MINUTES=30

PUBLIC_FRONTEND_URL=https://[YOUR_NETLIFY_URL]

BACKEND_CORS_ORIGINS=["https://[YOUR_NETLIFY_URL]"]
```

## Steps to Deploy

1. Go to https://render.com and login
2. Create a "New +" → "Web Service"
3. Connect your `clinic-backend` GitHub repo
4. Select the repo
5. Fill in:
   - **Name:** clinic-backend
   - **Runtime:** Python 3
6. **Important:** Before deploying, set all environment variables above
   - Replace `[YOUR_NETLIFY_URL]` with your actual Netlify URL
7. Click "Deploy"

## Database Notes

- The DATABASE_URL uses Supabase PostgreSQL
- The connection pool is configured automatically via `pooler.supabase.com`
- If you get connection timeouts, increase `SQLALCHEMY_POOL_SIZE` in settings

## Expected Render URL

After deployment, you'll get a URL like: `https://clinic-backend.onrender.com`
This is what you'll use in the frontend's VITE_API_URL
