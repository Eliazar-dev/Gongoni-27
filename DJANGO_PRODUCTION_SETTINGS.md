# Django Production Settings Guide

This guide explains the critical Django settings that must be configured for production deployment.

---

## Critical Settings Overview

| Setting | Purpose | Production Value |
|---------|---------|------------------|
| `DJANGO_DEBUG` | Controls error display and development features | `0` (must be 0) |
| `DJANGO_SECRET_KEY` | Cryptographic signing key | Long random string |
| `DJANGO_ALLOWED_HOSTS` | Allowed domain names for the site | Your domain(s) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Trusted origins for CSRF protection | Your HTTPS URL(s) |

---

## 1. DJANGO_DEBUG (MUST be 0 in production)

### What it does:
- **When DEBUG=1**: Shows detailed error pages with stack traces, database queries, and configuration details
- **When DEBUG=0**: Shows generic error page, hides sensitive information

### Why it must be 0 in production:
- **Security**: Debug pages expose:
  - File paths on the server
  - Database structure
  - Environment variables (including secrets)
  - Code snippets
- **Performance**: Debug mode adds overhead (debug toolbar, SQL logging)
- **Static files**: In DEBUG=0, static files are served by WhiteNoise (production), not Django (development)

### How to set:
```env
DJANGO_DEBUG=0
```

### Verification:
After deployment, try accessing a non-existent page. You should see a generic 404 page, not a Django debug page.

---

## 2. DJANGO_SECRET_KEY

### What it does:
- Used to sign:
  - Session cookies
  - CSRF tokens
  - Password reset tokens
  - Cryptographic signatures

### Security requirements:
- Must be **unique** per deployment
- Must be **long and random** (minimum 50 characters)
- Must be **kept secret** (never commit to git)
- If compromised, all sessions and tokens become invalid

### How to generate:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Example output: `bqxkowe0P4n0SqCTKFLvnFLlBReU1JmPJD34V2vSnsE`

### How to set:
```env
DJANGO_SECRET_KEY=bqxkowe0P4n0SqCTKFLvnFLlBReU1JmPJD34V2vSnsE
```

### Rotation:
If you need to change the secret key:
1. Generate a new key
2. Update `.env`
3. Restart the server
4. All users will be logged out (sessions invalidated) - this is expected

---

## 3. DJANGO_ALLOWED_HOSTS

### What it does:
- Whitelist of domain names that can serve the site
- Prevents HTTP Host header attacks

### What happens if misconfigured:
- **Missing your domain**: Users get "Bad Request (400)" error
- **Left as localhost**: Only accessible from the server itself, not from outside

### How to set:
```env
# Single domain
DJANGO_ALLOWED_HOSTS=gongoni.example.org

# Multiple domains (comma separated)
DJANGO_ALLOWED_HOSTS=gongoni.example.org,www.gongoni.example.org

# With IP address (not recommended, use domain)
DJANGO_ALLOWED_HOSTS=192.168.1.100
```

### Best practices:
- Use domain names, not IP addresses
- Include both with and without `www.` if both are used
- Remove `localhost` and `127.0.0.1` in production
- Keep the list minimal (only domains you actually use)

### Testing:
```bash
curl -H "Host: gongoni.example.org" http://your-server-ip/
# Should return 200 OK

curl -H "Host: evil.com" http://your-server-ip/
# Should return 400 Bad Request
```

---

## 4. DJANGO_CSRF_TRUSTED_ORIGINS

### What it does:
- Whitelist of origins allowed for CSRF protection
- Required when using HTTPS (which you should in production)

### Why it's needed:
- Django checks the `Origin` or `Referer` header on POST requests
- If the origin doesn't match, the request is rejected (CSRF protection)
- HTTPS changes the origin from `http://` to `https://`

### How to set:
```env
# Single domain
DJANGO_CSRF_TRUSTED_ORIGINS=https://gongoni.example.org

# Multiple domains (comma separated)
DJANGO_CSRF_TRUSTED_ORIGINS=https://gongoni.example.org,https://www.gongoni.example.org
```

### Important notes:
- Must include the protocol (`https://`)
- Must exactly match what users see in their browser
- If you use both HTTP and HTTPS (not recommended), include both:
  ```env
  DJANGO_CSRF_TRUSTED_ORIGINS=http://gongoni.example.org,https://gongoni.example.org
  ```

### Common errors:
| Error | Cause | Fix |
|-------|-------|-----|
| CSRF token missing | Origin not in trusted list | Add domain to `DJANGO_CSRF_TRUSTED_ORIGINS` |
| Form submission fails | Using HTTP but only HTTPS in list | Add HTTP origin or force HTTPS |

---

## Example Production Configuration

For a site at `https://gongoni.example.org`:

```env
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=your-long-random-secret-key-here
DJANGO_ALLOWED_HOSTS=gongoni.example.org,www.gongoni.example.org
DJANGO_CSRF_TRUSTED_ORIGINS=https://gongoni.example.org,https://www.gongoni.example.org
```

---

## Additional Production Settings

The following are handled automatically by the code in `settings.py`:

### SSL Proxy Header
```python
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```
This tells Django to trust the `X-Forwarded-Proto` header set by your reverse proxy (nginx, Apache, etc.).

### Static Files
```python
STORAGES = {
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
```
WhiteNoise serves static files efficiently and with compression.

### Logging
```python
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
```
Logs to console at INFO level. Can be enhanced for production.

---

## Security Headers (Optional Enhancements)

For additional security, consider adding these to `settings.py`:

```python
# HTTPS only (redirect HTTP to HTTPS)
SECURE_SSL_REDIRECT = True

# HSTS (force HTTPS for 1 year)
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Secure cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Cookie settings
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
```

**Note:** These require SSL/HTTPS to be properly configured. Add only after basic deployment is working.

---

## Testing Your Configuration

### 1. Check DEBUG is off
Visit a non-existent page:
```
https://your-domain/non-existent-page
```
Should see generic 404, not Django debug page.

### 2. Check ALLOWED_HOSTS
```bash
curl -I https://your-domain/
# Should return 200 OK

curl -H "Host: evil.com" https://your-domain/
# Should return 400 Bad Request
```

### 3. Check CSRF protection
1. Open the admin panel in your browser
2. Try to submit a form
3. Should work normally (no CSRF errors)

### 4. Check static files
Visit:
```
https://your-domain/static/sda-logos.png
```
Should load the image.

---

## Common Mistakes

### ❌ Wrong
```env
DJANGO_DEBUG=1  # Never in production!
DJANGO_ALLOWED_HOSTS=*  # Dangerous wildcard
DJANGO_CSRF_TRUSTED_ORIGINS=  # Empty causes CSRF errors
```

### ✅ Right
```env
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=gongoni.example.org
DJANGO_CSRF_TRUSTED_ORIGINS=https://gongoni.example.org
```

---

## Deployment Checklist

Before going live:

- [ ] `DJANGO_DEBUG=0`
- [ ] `DJANGO_SECRET_KEY` is a long random string (not the default)
- [ ] `DJANGO_ALLOWED_HOSTS` contains your actual domain
- [ ] `DJANGO_CSRF_TRUSTED_ORIGINS` contains your HTTPS URL
- [ ] Test registration works
- [ ] Test admin login works
- [ ] Test static files load
- [ ] Test 404 page shows generic error (not debug page)
- [ ] Verify no debug information in error pages

---

## Environment-Specific Configurations

### Development (local)
```env
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=
```

### Staging (testing environment)
```env
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=staging.gongoni.example.org
DJANGO_CSRF_TRUSTED_ORIGINS=https://staging.gongoni.example.org
```

### Production (live)
```env
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=gongoni.example.org,www.gongoni.example.org
DJANGO_CSRF_TRUSTED_ORIGINS=https://gongoni.example.org,https://www.gongoni.example.org
```

---

## Troubleshooting

### "DisallowedHost" error
- Check `DJANGO_ALLOWED_HOSTS` includes your domain
- Restart the server after changing `.env`

### CSRF verification failed
- Check `DJANGO_CSRF_TRUSTED_ORIGINS` includes your HTTPS URL
- Ensure you're accessing via HTTPS, not HTTP
- Clear browser cookies and try again

### Static files 404
- Run `python manage.py collectstatic --noinput`
- Check `STATIC_ROOT` directory exists and has files
- Verify WhiteNoise is in MIDDLEWARE (it is by default)

### Session errors after deployment
- `DJANGO_SECRET_KEY` changed (users logged out - expected)
- If sessions keep failing, check `DJANGO_SECRET_KEY` is stable

---

## Summary

The four critical settings are:

1. **DJANGO_DEBUG=0** - Security and performance
2. **DJANGO_SECRET_KEY** - Random and secret
3. **DJANGO_ALLOWED_HOSTS** - Your domain(s)
4. **DJANGO_CSRF_TRUSTED_ORIGINS** - Your HTTPS URL(s)

These are all configured in the `.env.production` template. Copy it to `.env` and fill in your values before deployment.
