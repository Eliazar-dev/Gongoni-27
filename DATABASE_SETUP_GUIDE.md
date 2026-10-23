# Database Setup Guide for Production

This guide helps you choose and configure the right database for your deployment.

---

## Database Options

| Option | Best For | Pros | Cons |
|--------|----------|------|------|
| **SQLite** | VPS with persistent storage | Simple, no setup, zero cost | Not scalable, file-based |
| **Postgres** | Cloud platforms (Render, Railway, etc.) | Scalable, reliable, persistent | Requires setup, may cost |

---

## Option 1: SQLite (Simple, Zero Cost)

### When to use SQLite:
- You have a VPS where files persist after restart
- You expect fewer than 1,000 members
- You want the simplest possible setup
- You're comfortable with file-based backups

### When NOT to use SQLite:
- Using a platform that deletes files on restart (Render free tier, Railway, etc.)
- Expecting high traffic (concurrent writes)
- Need advanced database features

### Configuration

In `.env`, leave `DATABASE_URL` empty:

```env
DATABASE_URL=
```

This is the default. Django will use `backend/db.sqlite3`.

### Backup Strategy

SQLite is a single file. Back it up regularly:

#### Manual Backup:
```bash
# Stop the server first
cd backend
cp db.sqlite3 db.sqlite3.backup.$(date +%Y%m%d)
```

#### Automated Backup (cron job):
```bash
# Add to crontab (crontab -e)
# Backup every day at 2 AM
0 2 * * * cd /path/to/gongoni27/backend && cp db.sqlite3 backups/db.sqlite3.$(date +\%Y\%m\%d)
```

#### Keep Multiple Backups:
```bash
# Keep last 7 days, last 4 weeks, last 12 months
# Backup script example
#!/bin/bash
BACKUP_DIR="/path/to/backups"
DB_FILE="/path/to/gongoni27/backend/db.sqlite3"
DATE=$(date +%Y%m%d)

# Daily backup
cp "$DB_FILE" "$BACKUP_DIR/db.sqlite3.daily.$DATE"

# Weekly backup (Sunday)
if [ $(date +%u) -eq 7 ]; then
    cp "$DB_FILE" "$BACKUP_DIR/db.sqlite3.weekly.$DATE"
fi

# Monthly backup (1st of month)
if [ $(date +%d) -eq 01 ]; then
    cp "$DB_FILE" "$BACKUP_DIR/db.sqlite3.monthly.$DATE"
fi

# Clean old backups (keep 7 daily, 4 weekly, 12 monthly)
find "$BACKUP_DIR" -name "db.sqlite3.daily.*" -mtime +7 -delete
find "$BACKUP_DIR" -name "db.sqlite3.weekly.*" -mtime +28 -delete
find "$BACKUP_DIR" -name "db.sqlite3.monthly.*" -mtime +365 -delete
```

### Permissions

Ensure the database file and directory are writable by the web server:

```bash
cd backend
chmod 644 db.sqlite3
chmod 755 .  # Directory permissions
```

### Migration

No migration needed. The database is already in use.

---

## Option 2: PostgreSQL (Recommended for Cloud Platforms)

### When to use Postgres:
- Using Render, Railway, Heroku, or similar platforms
- Platform deletes files on restart
- Expecting growth beyond 1,000 members
- Need better performance with concurrent writes
- Want automated backups

### Configuration

In `.env`, set `DATABASE_URL`:

```env
DATABASE_URL=postgres://username:password@host:port/database_name
```

### Step-by-Step Setup

#### A. On Render (Recommended)

1. **Create a Postgres database:**
   - Go to https://dashboard.render.com
   - Click "New" → "PostgreSQL"
   - Name it: `gongoni27-db`
   - Choose a region (closest to Kenya: Frankfurt, Singapore)
   - Select a plan (Free tier is sufficient for this project)
   - Click "Create Database"

2. **Get the connection string:**
   - Click on your new database
   - Scroll to "Connections"
   - Copy the "Internal Database URL" (for same-region apps)
   - Or copy "External Database URL" (for different regions)

3. **Add to .env:**
   ```env
   DATABASE_URL=postgres://gongoni27:randompassword@dpg-xxx.oregon-postgres.render.com:5432/gongoni27
   ```

4. **Connect your Django app:**
   - Create a new "Web Service" for Django
   - Link it to the Postgres database
   - Render automatically sets the `DATABASE_URL` environment variable

#### B. On Railway

1. **Create a Postgres database:**
   - Go to https://railway.app
   - Click "New Project" → "Provision PostgreSQL"
   - Railway will create the database

2. **Get the connection string:**
   - Click on the PostgreSQL service
   - Go to "Variables" tab
   - Copy the `DATABASE_URL` value

3. **Add to .env:**
   ```env
   DATABASE_URL=postgres://postgres:password@containers.railway.app:5432/railway
   ```

#### C. On a VPS (Self-Hosted Postgres)

1. **Install Postgres:**
   ```bash
   # Ubuntu/Debian
   sudo apt update
   sudo apt install postgresql postgresql-contrib

   # CentOS/RHEL
   sudo yum install postgresql-server postgresql-contrib
   sudo postgresql-setup initdb
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   ```

2. **Create database and user:**
   ```bash
   sudo -u postgres psql
   ```
   In the psql prompt:
   ```sql
   CREATE DATABASE gongoni27;
   CREATE USER gongoni_user WITH PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE gongoni27 TO gongoni_user;
   \q
   ```

3. **Configure Postgres for remote access (if needed):**
   ```bash
   sudo nano /etc/postgresql/*/main/postgresql.conf
   # Change: listen_addresses = '*'

   sudo nano /etc/postgresql/*/main/pg_hba.conf
   # Add: host    gongoni27    gongoni_user    0.0.0.0/0    md5

   sudo systemctl restart postgresql
   ```

4. **Add to .env:**
   ```env
   DATABASE_URL=postgres://gongoni_user:secure_password@localhost:5432/gongoni27
   ```

### Migration from SQLite to Postgres

If you started with SQLite and want to switch to Postgres:

1. **Export data from SQLite:**
   ```bash
   cd backend
   source venv/bin/activate  # Windows: venv\Scripts\activate
   python manage.py dumpdata > data.json
   ```

2. **Configure Postgres in .env:**
   ```env
   DATABASE_URL=postgres://user:pass@host:5432/dbname
   ```

3. **Run migrations on Postgres:**
   ```bash
   python manage.py migrate
   ```

4. **Import data:**
   ```bash
   python manage.py loaddata data.json
   ```

5. **Verify:**
   ```bash
   python manage.py shell
   >>> from tracker.models import Member
   >>> Member.objects.count()
   ```

6. **Clean up:**
   ```bash
   rm data.json
   # Optionally keep db.sqlite3 as backup
   ```

### Backup Strategy

Postgres has built-in backup tools:

#### Manual Backup:
```bash
pg_dump -U username -h host -d dbname > backup.sql
```

#### Automated Backup (cron):
```bash
# Backup every day at 2 AM
0 2 * * * pg_dump -U gongoni_user -h localhost gongoni27 > /backups/gongoni27_$(date +\%Y\%m\%d).sql
```

#### Using pgAdmin (GUI):
1. Open pgAdmin
2. Right-click database → "Backup"
3. Choose format (Plain or Custom)
4. Save to file

### Restore from Backup

```bash
psql -U username -h host -d dbname < backup.sql
```

---

## Database URL Format Reference

The `DATABASE_URL` format is:

```
postgres://[user[:password]@][host][:port][/dbname][?param1=value1&...]
```

### Examples:

```env
# Local Postgres
DATABASE_URL=postgres://gongoni_user:password@localhost:5432/gongoni27

# Remote Postgres
DATABASE_URL=postgres://gongoni_user:password@db.example.com:5432/gongoni27

# Render (Internal)
DATABASE_URL=postgres://gongoni27:abc123@dpg-xxx.oregon-postgres.render.com:5432/gongoni27

# Railway
DATABASE_URL=postgres://postgres:password@containers.railway.app:5432/railway

# With connection pooling (PgBouncer)
DATABASE_URL=postgres://user:pass@host:6432/dbname?poolmode=transaction
```

---

## Connection Pooling (Optional)

For high-traffic sites, use connection pooling:

### Render:
Render automatically provides connection pooling with the internal URL.

### Railway:
Add `?poolmode=transaction` to your DATABASE_URL:
```env
DATABASE_URL=postgres://user:pass@host:5432/dbname?poolmode=transaction
```

### Self-hosted (PgBouncer):
Install and configure PgBouncer:
```bash
sudo apt install pgbouncer
# Configure /etc/pgbouncer/pgbouncer.ini
# Restart: sudo systemctl restart pgbouncer
```

---

## Performance Tuning (Postgres)

For production with Postgres, consider these settings in `postgresql.conf`:

```ini
# Memory settings (adjust based on server RAM)
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
work_mem = 16MB

# Connection settings
max_connections = 100

# WAL settings
wal_buffers = 16MB
checkpoint_completion_target = 0.9
```

After changing, restart Postgres:
```bash
sudo systemctl restart postgresql
```

---

## Monitoring Database Health

### Check database size:
```sql
SELECT pg_size_pretty(pg_database_size('gongoni27'));
```

### Check table sizes:
```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Check active connections:
```sql
SELECT count(*) FROM pg_stat_activity;
```

### Check slow queries:
Enable logging in `postgresql.conf`:
```ini
log_min_duration_statement = 1000  # Log queries > 1 second
```

---

## Troubleshooting

### SQLite: "database is locked"
- Cause: Multiple concurrent writes
- Solution: Use Postgres for production with concurrency

### Postgres: "connection refused"
- Check Postgres is running: `sudo systemctl status postgresql`
- Check firewall allows port 5432
- Verify host and port in DATABASE_URL

### Postgres: "authentication failed"
- Verify username and password in DATABASE_URL
- Check user has privileges: `\l` in psql

### Postgres: "database does not exist"
- Create the database: `CREATE DATABASE gongoni27;`
- Verify dbname in DATABASE_URL

### Migration fails
- Ensure DATABASE_URL is correct
- Run: `python manage.py migrate --run-syncdb`
- Check for pending migrations: `python manage.py showmigrations`

---

## Recommendation

### For this project:

**If using a VPS (DigitalOcean, Linode, AWS EC2):**
- Use **SQLite** if files persist
- Simple, zero cost, sufficient for the expected load
- Back up the file daily

**If using Render, Railway, or similar:**
- Use **Postgres** (provided by the platform)
- Free tier is sufficient
- Automatic backups available
- Persists across restarts

**If unsure:**
- Start with SQLite on a VPS
- Migrate to Postgres if you outgrow it
- The migration process is straightforward

---

## Final Checklist

Before going live:

- [ ] Database chosen (SQLite or Postgres)
- [ ] DATABASE_URL configured (or left empty for SQLite)
- [ ] Migrations run: `python manage.py migrate`
- [ ] Superuser created: `python manage.py createsuperuser`
- [ ] Backup strategy in place
- [ ] Tested restore from backup
- [ ] Database permissions correct
- [ ] Connection tested from application
