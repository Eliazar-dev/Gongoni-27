# Railway Deployment Instructions

## Quick Steps (5 minutes):

1. Go to https://railway.app
2. Sign up with GitHub (Eliazar-dev)
3. Click "New Project" → "Deploy from GitHub repo"
4. Select "Gongoni-27" repository
5. Railway will auto-detect Python
6. Click "Deploy"

## After Deployment:

### Add Postgres Database:
1. In your Railway project, click "New" → "Database" → "Add PostgreSQL"
2. Wait for it to create

### Add Environment Variables:
1. Click on your web service
2. Go to "Variables" tab
3. Add these variables (from .env.vercel):

```
DATABASE_URL=postgresql://neondb_owner:npg_Olb2hqWptB0x@ep-hidden-wave-b5ra3m9g-pooler.c-7.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require
DJANGO_SECRET_KEY=jUdLh4RhFKQ5wsmjWowmhaCQBKOjqX4tTQTwUbgvQPo
DJANGO_DEBUG=0
WEBHOOK_SECRET=wL87EFQMTxFw_6EH0qDgvleyu7Lwpjb85f2aIMax5zY
DJANGO_ALLOWED_HOSTS=*.onrender.com,*.railway.app
DJANGO_CSRF_TRUSTED_ORIGINS=https://*.onrender.com,https://*.railway.app
EMAIL_BACKEND_MODE=console
SMS_BACKEND=console
```

4. Or better - use Railway's Postgres instead of Neon:
   - Link the Railway Postgres database
   - Railway will set DATABASE_URL automatically
   - Update DJANGO_ALLOWED_HOSTS and DJANGO_CSRF_TRUSTED_ORIGINS to use *.railway.app

### Run Migrations:
Railway doesn't run migrations automatically. You'll need to run them via Railway's console or use a build script.

### Build Script (Optional):
Add this to railway.toml if needed.
