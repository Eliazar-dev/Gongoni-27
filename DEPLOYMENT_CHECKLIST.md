# Production Deployment Checklist

This checklist guides you through deploying the Gongoni 27 tracker to production.

---

## Pre-Deployment Preparation

### 1. Choose Your Hosting Platform

| Platform | Difficulty | Cost | Database | Best For |
|----------|-----------|------|----------|----------|
| **Render** | Easy | Free-$ | Postgres (free) | Quick deployment, automatic HTTPS |
| **Railway** | Easy | Free-$ | Postgres (free) | Easy deployment, good free tier |
| **DigitalOcean VPS** | Medium | $5-6/mo | SQLite or Postgres | Full control, predictable cost |
| **AWS EC2** | Hard | Variable | SQLite or Postgres | Enterprise, complex needs |

**Recommendation:** Render (easiest) or DigitalOcean VPS (most cost-effective for long-term).

---

## 2. Prepare Your Domain

### Option A: Use a subdomain (e.g., gongoni.yourdomain.com)
- Create an A record pointing to your server IP
- Or create a CNAME record (for some platforms)

### Option B: Use a platform subdomain (e.g., gongoni27.onrender.com)
- No DNS configuration needed
- Platform provides the domain
- Less professional appearance

### Option C: Register a new domain
- Register via Namecheap, GoDaddy, etc.
- Point to your hosting platform

---

## Step-by-Step Deployment

### Phase 1: Configure Environment Variables

#### 1.1 Generate Secure Keys
```bash
# Generate Django secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate webhook secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Save both values - you'll need them.

#### 1.2 Set Up Email
Follow [EMAIL_SETUP_GUIDE.md](EMAIL_SETUP_GUIDE.md):
- [ ] Created email account (Gmail recommended)
- [ ] Enabled 2-factor authentication
- [ ] Generated App Password
- [ ] Tested email sending (optional)

#### 1.3 Set Up SMS
Follow [SMS_SETUP_GUIDE.md](SMS_SETUP_GUIDE.md):
- [ ] Created Africa's Talking account
- [ ] Added SMS credit (KES 100-500 recommended)
- [ ] Obtained API credentials (username, API key)
- [ ] Tested SMS in sandbox mode (optional)

#### 1.4 Create Production .env File
Copy `.env.production` to `.env` and fill in:

```bash
cd backend
cp .env.production .env
```

Edit `.env` with your values:
- [ ] `DJANGO_SECRET_KEY` = (generated above)
- [ ] `DJANGO_DEBUG` = `0`
- [ ] `DJANGO_ALLOWED_HOSTS` = your domain
- [ ] `DJANGO_CSRF_TRUSTED_ORIGINS` = https://your-domain
- [ ] `DATABASE_URL` = (Postgres URL or leave empty for SQLite)
- [ ] `WEBHOOK_SECRET` = (generated above)
- [ ] `EMAIL_BACKEND_MODE` = `smtp`
- [ ] `EMAIL_HOST_USER` = your email
- [ ] `EMAIL_HOST_PASSWORD` = your app password
- [ ] `DEFAULT_FROM_EMAIL` = Gongoni 27 <your-email>
- [ ] `SMS_BACKEND` = `africastalking`
- [ ] `AT_USERNAME` = your Africa's Talking username
- [ ] `AT_API_KEY` = your Africa's Talking API key

**Never commit .env to git!**

---

### Phase 2: Prepare Code for Deployment

#### 2.1 Collect Static Files
```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
python manage.py collectstatic --noinput
```

#### 2.2 Remove Demo Data (if present)
```bash
python manage.py seed_demo --clear
```

#### 2.3 Verify .gitignore
Ensure `.gitignore` includes:
```
.env
venv/
db.sqlite3
staticfiles/
__pycache__/
*.pyc
```

#### 2.4 Commit Changes
```bash
git add .
git commit -m "Prepare for production deployment"
```

---

### Phase 3: Deploy to Platform

#### Option A: Deploy to Render (Recommended)

1. **Create Postgres Database**
   - Go to https://dashboard.render.com
   - Click "New" → "PostgreSQL"
   - Name: `gongoni27-db`
   - Region: Frankfurt or Singapore (closest to Kenya)
   - Plan: Free
   - Click "Create"

2. **Create Web Service**
   - Click "New" → "Web Service"
   - Connect your GitHub repository
   - Select the `gongoni27` repository
   - Build and deploy settings:
     ```
     Build Command: cd backend && pip install -r requirements.txt && python manage.py collectstatic --noinput
     Start Command: cd backend && gunicorn gongoni.wsgi:application --bind 0.0.0.0:$PORT
     ```
   - Environment variables: Add all from your `.env` file
   - Link to the Postgres database (Render sets `DATABASE_URL` automatically)
   - Click "Create Web Service"

3. **Configure Domain**
   - Click on your web service
   - Go to "Domains"
   - Add your custom domain (if using one)
   - Update DNS as instructed by Render
   - Wait for SSL certificate (automatic)

4. **Verify Deployment**
   - Open the provided URL
   - Test registration
   - Test admin login

#### Option B: Deploy to Railway

1. **Create Project**
   - Go to https://railway.app
   - Click "New Project"
   - Deploy from GitHub
   - Select your repository

2. **Add Postgres**
   - Click "New" → "Provision PostgreSQL"
   - Railway will create the database

3. **Configure Environment Variables**
   - Click on your project
   - Go to "Variables" tab
   - Add all variables from your `.env` file
   - Railway sets `DATABASE_URL` automatically

4. **Configure Build Settings**
   - Add `PORT=8000` to variables
   - Railway auto-detects Python and builds accordingly

5. **Configure Domain**
   - Click "Settings" → "Networking"
   - Add your custom domain
   - Update DNS as instructed

6. **Verify Deployment**
   - Open the provided URL
   - Test all functionality

#### Option C: Deploy to DigitalOcean VPS

1. **Create VPS**
   - Go to https://digitalocean.com
   - Create a Droplet
   - Choose: Ubuntu 22.04 LTS, 1GB RAM, $6/mo
   - Choose a region (closest to Kenya: Bangalore, Frankfurt)
   - Add SSH key for authentication
   - Create Droplet

2. **Connect to VPS**
   ```bash
   ssh root@your-droplet-ip
   ```

3. **Install Dependencies**
   ```bash
   apt update
   apt install python3 python3-pip python3-venv git nginx -y
   ```

4. **Clone Repository**
   ```bash
   cd /var/www
   git clone your-repo-url gongoni27
   cd gongoni27/backend
   ```

5. **Set Up Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

6. **Configure Environment**
   ```bash
   cp .env.example .env
   nano .env
   # Paste your production configuration
   ```

7. **Run Migrations**
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py createsuperuser
   ```

8. **Configure Systemd Service**
   ```bash
   nano /etc/systemd/system/gongoni.service
   ```
   Add:
   ```ini
   [Unit]
   Description=Gongoni 27 Django Service
   After=network.target

   [Service]
   User=www-data
   Group=www-data
   WorkingDirectory=/var/www/gongoni27/backend
   Environment="PATH=/var/www/gongoni27/backend/venv/bin"
   ExecStart=/var/www/gongoni27/backend/venv/bin/gunicorn gongoni.wsgi:application --bind 127.0.0.1:8000

   [Install]
   WantedBy=multi-user.target
   ```

   ```bash
   systemctl start gongoni
   systemctl enable gongoni
   ```

9. **Configure Nginx**
   ```bash
   nano /etc/nginx/sites-available/gongoni
   ```
   Add:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }

       location /static/ {
           alias /var/www/gongoni27/backend/staticfiles/;
       }
   }
   ```

   ```bash
   ln -s /etc/nginx/sites-available/gongoni /etc/nginx/sites-enabled/
   nginx -t
   systemctl restart nginx
   ```

10. **Set Up SSL with Certbot**
    ```bash
    apt install certbot python3-certbot-nginx -y
    certbot --nginx -d your-domain.com
    ```

11. **Set Up Database Backup**
    ```bash
    # Add to crontab
    crontab -e
    # Add: 0 2 * * * cp /var/www/gongoni27/backend/db.sqlite3 /backups/db.sqlite3.$(date +\%Y\%m\%d)
    ```

12. **Verify Deployment**
    - Open your domain in browser
    - Test all functionality

---

### Phase 4: Post-Deployment Testing

#### 4.1 Basic Functionality
- [ ] Homepage loads correctly
- [ ] Registration form works
- [ ] Thank-you page displays
- [ ] Admin login works (with superuser credentials)
- [ ] Dashboard loads
- [ ] Members page loads
- [ ] Payments page loads

#### 4.2 Email Testing
- [ ] Register a test member with your email
- [ ] Welcome email arrives
- [ ] Email content is correct (mission details, payment info)
- [ ] Check spam folder if not in inbox

#### 4.3 SMS Testing
- [ ] Register a test member with your phone
- [ ] Make a small test payment (KES 30)
- [ ] SMS arrives on your phone
- [ ] SMS content is correct
- [ ] Check Africa's Talking dashboard for delivery status

#### 4.4 Payment Flow Testing
- [ ] Simulate M-Pesa payment: `python manage.py simulate_mpesa ...`
- [ ] Payment appears in admin panel
- [ ] Payment matched to correct member
- [ ] Email and SMS sent
- [ ] Member total updated correctly

#### 4.5 Security Testing
- [ ] DEBUG=0 (debug page not shown on errors)
- [ ] 404 page shows generic error
- [ ] Admin panel requires authentication
- [ ] API endpoints require authentication
- [ ] Static files load correctly

---

### Phase 5: Configure Phone Forwarder

Follow the main README, Part D:

#### 5.1 Install Forwarder App
- [ ] Download "SMS to URL Forwarder" APK
- [ ] Install on treasurer's Android phone
- [ ] Grant SMS permission
- [ ] Disable battery optimization

#### 5.2 Configure Forwarding Rule
- [ ] Sender: `MPESA`
- [ ] Webhook URL: `https://your-domain/api/webhook/sms/?key=YOUR_WEBHOOK_SECRET`
- [ ] Method: POST
- [ ] Body (JSON): `{"from":"%from%","text":"%text%","sentStamp":"%sentStamp%","receivedStamp":"%receivedStamp%"}`

#### 5.3 Test Real Payment
- [ ] Make KES 30 test payment to Paybill 7108831
- [ ] Payment appears in admin panel
- [ ] Email and SMS sent to member
- [ ] No errors in message log

---

### Phase 6: Launch Preparation

#### 6.1 Remove Demo Data
```bash
python manage.py seed_demo --clear
```

#### 6.2 Create Treasurer Account
```bash
python manage.py createsuperuser
```
Save the username and password securely.

#### 6.3 Final Configuration Check
- [ ] `DJANGO_DEBUG=0`
- [ ] All secret keys are random and secure
- [ ] Email and SMS configured and tested
- [ ] Database backup configured
- [ ] Forwarder app configured
- [ ] Domain accessible via HTTPS

#### 6.4 Share Registration Link
- [ ] Update poster with registration URL
- [ ] Share link in WhatsApp groups
- [ ] Test link from different devices

---

## Ongoing Maintenance

### Daily (During Mission)
- [ ] Check dashboard for payments needing attention
- [ ] Check message log for unreadable messages
- [ ] Verify SMS credit in Africa's Talking
- [ ] Monitor database backups

### Weekly
- [ ] Review payment trends
- [ ] Check for any failed email/SMS attempts
- [ ] Verify server disk space
- [ ] Review any error logs

### After Mission
- [ ] Export member data to Excel
- [ ] Create backup of final database
- [ ] Disable registration (if desired)
- [ ] Archive Africa's Talking logs
- [ ] Document lessons learned

---

## Troubleshooting Quick Reference

| Issue | Solution |
|-------|----------|
| Emails not sending | Check EMAIL_BACKEND_MODE=smtp, verify app password |
| SMS not sending | Check SMS credit, verify API credentials |
| Payments not recording | Check webhook URL, verify WEBHOOK_SECRET |
| Static files 404 | Run `collectstatic --noinput` |
| Database errors | Check DATABASE_URL, run migrations |
| CSRF errors | Check CSRF_TRUSTED_ORIGINS |
| 502 errors | Check gunicorn is running, check nginx config |

---

## Emergency Contacts

- **Developer**: [Add contact]
- **Africa's Talking Support**: support@africastalking.com
- **Hosting Support**: [Platform-specific]

---

## Documentation Reference

- [Email Setup Guide](EMAIL_SETUP_GUIDE.md)
- [SMS Setup Guide](SMS_SETUP_GUIDE.md)
- [Django Production Settings](DJANGO_PRODUCTION_SETTINGS.md)
- [Database Setup Guide](DATABASE_SETUP_GUIDE.md)
- [Static Files Guide](STATIC_FILES_GUIDE.md)
- [Main README](README.md)

---

## Success Criteria

Deployment is successful when:
- ✅ Website loads with HTTPS
- ✅ Registration works and sends welcome email
- ✅ Admin panel accessible
- ✅ Test payment recorded correctly
- ✅ Email and SMS sent for payment
- ✅ Phone forwarder receives and forwards messages
- ✅ No errors in logs
- ✅ Database backup configured

---

## Notes

```
Deployment date: _______________
Deployed by: _______________
Domain: _______________
Hosting platform: _______________
Email provider: _______________
SMS provider: Africa's Talking
Database: SQLite / Postgres
Backup schedule: _______________
```
