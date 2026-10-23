# Static Files Guide for Production

This guide explains how to handle static files (CSS, JavaScript, images) in production.

---

## Overview

Static files in this project:
- **Frontend assets**: Already built in `frontend/dist/` (React app)
- **Images**: Located in `frontend/dist/` (e.g., `sda-logos.png`)
- **Served by**: WhiteNoise middleware (production-ready static file server)

The frontend is **already built**, so you don't need Node.js or npm for deployment unless you modify the React code.

---

## How Static Files Work

### Development (DEBUG=1)
- Django serves static files automatically
- Files are served from `frontend/dist/`
- Changes to files are reflected immediately

### Production (DEBUG=0)
- WhiteNoise serves static files
- Files are collected to `backend/staticfiles/`
- Files are compressed (gzip, brotli)
- Files are cached efficiently

---

## Collecting Static Files for Production

### Step 1: Ensure Frontend is Built

The frontend should already be built. Verify:

```bash
cd frontend
ls dist/
```

You should see:
- `index.html`
- `assets/` directory with CSS and JS files
- `sda-logos.png` (or other images)

### Step 2: Collect Static Files

In the `backend` directory:

```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
python manage.py collectstatic --noinput
```

This command:
- Copies files from `frontend/dist/` to `backend/staticfiles/`
- Compresses files (gzip, brotli)
- Organizes files efficiently
- The `--noinput` flag skips the confirmation prompt

### Step 3: Verify

Check that files were collected:

```bash
ls staticfiles/
```

You should see:
- `assets/` directory
- `index.html`
- `sda-logos.png`
- Compressed versions (`.gz`, `.br`)

---

## When to Rebuild the Frontend

You only need to rebuild the frontend if you:
- Modify the React code in `frontend/src/`
- Change the styling
- Add new images or assets
- Update dependencies in `frontend/package.json`

### Rebuilding the Frontend

If you need to rebuild:

```bash
cd frontend
npm install
npm run build
```

Then collect static files again:

```bash
cd ../backend
python manage.py collectstatic --noinput
```

---

## Rebuilding on Different Platforms

### On Render (Automatic)

Render automatically runs the build command if you configure it in `render.yaml`:

```yaml
build:
  commands:
    - cd frontend && npm install && npm run build
    - cd ../backend && python manage.py collectstatic --noinput
```

### On Railway (Automatic)

Railway can detect the frontend and build it automatically, or you can add a build script in `package.json`:

```json
{
  "scripts": {
    "build": "cd frontend && npm install && npm run build && cd ../backend && python manage.py collectstatic --noinput"
  }
}
```

### On a VPS (Manual)

Build manually before deployment:

```bash
cd frontend
npm install
npm run build
cd ../backend
python manage.py collectstatic --noinput
```

Then deploy the entire `gongoni27` folder.

---

## WhiteNoise Configuration

WhiteNoise is already configured in `settings.py`:

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # ... other middleware
]

STORAGES = {
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
```

This provides:
- Gzip compression
- Brotli compression (if supported)
- Efficient caching headers
- No need for nginx/Apache for static files

---

## Caching Strategy

WhiteNoise sets optimal caching headers automatically:

- **Static assets (CSS, JS, images)**: Cached for 1 year with hash in filename
- **index.html**: Not cached (serves fresh content)
- **Compressed versions**: Served to browsers that support them

This means:
- Users get fast page loads (assets cached)
- Changes are detected via filename hashes
- No cache-busting needed manually

---

## Troubleshooting

### Static files 404

**Symptom:** Images, CSS, or JS not loading

**Solutions:**
1. Run `python manage.py collectstatic --noinput`
2. Check `STATIC_ROOT` directory exists and has files
3. Verify `DJANGO_DEBUG=0` in production
4. Check file permissions: `chmod -R 755 staticfiles/`

### Changes not reflected

**Symptom:** Modified frontend not showing after rebuild

**Solutions:**
1. Rebuild frontend: `cd frontend && npm run build`
2. Collect static files again: `cd backend && python manage.py collectstatic --noinput`
3. Clear browser cache (Ctrl+Shift+R)
4. Restart the server

### collectstatic command fails

**Symptom:** Error when running collectstatic

**Common causes:**
1. `frontend/dist/` doesn't exist → Build the frontend first
2. Permission denied → Check directory permissions
3. Disk full → Free up space

**Solutions:**
```bash
# Build frontend if missing
cd frontend
npm install
npm run build

# Fix permissions
cd ../backend
chmod -R 755 staticfiles/

# Clear and try again
rm -rf staticfiles/
python manage.py collectstatic --noinput
```

### WhiteNoise not serving files

**Symptom:** Django trying to serve static files (slow)

**Check:**
1. WhiteNoise is in MIDDLEWARE (it is by default)
2. Position is correct (after SecurityMiddleware)
3. No other static file middleware interfering

---

## Advanced: CDN Integration (Optional)

For better performance globally, you can use a CDN:

### Using Cloudflare (Recommended)

1. Point your domain to Cloudflare
2. Cloudflare automatically caches static files
3. No code changes needed

### Using AWS CloudFront

1. Upload `staticfiles/` to S3
2. Create CloudFront distribution
3. Configure Django to use S3 (requires django-storages)

**Note:** For this project, WhiteNoise is sufficient. CDN is optional optimization.

---

## Security Considerations

Static files are publicly accessible. Ensure:

- No sensitive files in `frontend/dist/` or `staticfiles/`
- No `.env` files copied to static files
- No database backups in static files
- No logs or temporary files in static files

The project is structured correctly, so this shouldn't be an issue.

---

## Monitoring Static File Performance

Check that static files are being served efficiently:

```bash
# Check response headers
curl -I https://your-domain/static/assets/index-Bfou3Zkc.css
```

Look for:
- `Content-Encoding: gzip` or `br` (compression working)
- `Cache-Control: max-age=31536000` (long cache for assets)
- `Content-Type: text/css` (correct MIME type)

---

## Best Practices

1. **Always collect static files before deployment**
   ```bash
   python manage.py collectstatic --noinput
   ```

2. **Never commit staticfiles/ to git**
   Add to `.gitignore`:
   ```
   staticfiles/
   ```

3. **Rebuild frontend only when needed**
   - Most deployments won't need frontend rebuilds
   - Only rebuild if you changed React code

4. **Test locally with DEBUG=0**
   ```bash
   DJANGO_DEBUG=0 python manage.py runserver
   ```
   This simulates production static file serving.

5. **Keep frontend/dist/ in git**
   - The built frontend should be committed
   - This ensures quick deployment without Node.js

---

## Quick Reference

### Before every deployment:
```bash
cd backend
python manage.py collectstatic --noinput
```

### If you modified React code:
```bash
cd frontend
npm run build
cd ../backend
python manage.py collectstatic --noinput
```

### Clear static files and rebuild:
```bash
cd backend
rm -rf staticfiles/
python manage.py collectstatic --noinput
```

### Test static files locally:
```bash
cd backend
DJANGO_DEBUG=0 python manage.py runserver
# Open http://127.0.0.1:8000
```

---

## Summary

For this project:
- Frontend is already built in `frontend/dist/`
- Run `python manage.py collectstatic --noinput` before deployment
- WhiteNoise serves files efficiently in production
- No need for nginx/Apache or CDN (optional optimization)
- Only rebuild frontend if you modify React code

That's it! Static files are handled automatically once collected.
