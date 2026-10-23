# Gongoni 27: mission registration and giving tracker

Seventh-day Adventist Church, Mount Kenya University. Gongoni Mission 27, 25 April to 9 May 2027.

Members register on one page. When they pay the church Paybill, the treasurer's phone forwards the M-Pesa message
to this system. The system records the payment, works out the percentage and balance, and sends the member an
email first and then an SMS with the receipt.

```
Member pays Paybill 7108831 ──> M-Pesa SMS on treasurer's Android phone
        ──> forwarder app ──> POST /api/webhook/sms/ ──> read, match, record
        ──> email (full receipt) ──> SMS (short receipt)
```

Pages: `/` registration, `/thank-you`, and for the treasurer `/admin` (dashboard), `/admin/members`, `/admin/payments`.

## 1. Try it on your computer (10 minutes)

You need Python 3.11 or newer.

```bash
cd backend
python -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # Windows: copy .env.example .env
# open .env and set DJANGO_DEBUG=1 and WEBHOOK_SECRET=anything-long
python manage.py migrate
python manage.py createsuperuser    # this is the treasurer's login
python manage.py seed_demo          # optional: fake members and payments to play with
python manage.py runserver
```

Open http://127.0.0.1:8000. The website is already built (`frontend/dist`), so Node is not needed.
Emails and SMS are printed in the terminal until you configure real sending (section 3).

**Test a payment without a phone:**

```bash
python manage.py simulate_mpesa --name "Belinda Boyani Mayore" --phone 254707548406 --amount 1000
```

**Run the automatic tests (56 tests):** `python manage.py test tracker`

## 2. Put it online

Use any host that runs Python (a small VPS, Render, Railway and similar). On the server:

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env     # fill it in, see below. Keep DJANGO_DEBUG=0
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
gunicorn gongoni.wsgi --bind 0.0.0.0:8000 --workers 2
```

Important settings in `.env`:

| Setting | What to put |
| --- | --- |
| `DJANGO_SECRET_KEY` | a long random string |
| `DJANGO_ALLOWED_HOSTS` | your domain, for example `gongoni.example.org` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://gongoni.example.org` |
| `DATABASE_URL` | for Postgres: `postgres://user:pass@host:5432/db`. Leave empty to use the SQLite file. |
| `WEBHOOK_SECRET` | a long random string, used by the phone app (section 4) |

Notes:
- Use **https**. The forwarder app sends a secret and members enter personal details.
- Some hosts delete files on restart. If yours does, use Postgres (`DATABASE_URL`) so registrations are not lost.
- Back up the database daily.
- If you edit the React code, rebuild with `cd frontend && npm install && npm run build`, then run `collectstatic` again.

## 3. Email and SMS

**Email (free).** Set `EMAIL_BACKEND_MODE=smtp` and fill in `EMAIL_HOST`, `EMAIL_HOST_USER`,
`EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`. For a Gmail account, create an "App password" and use it as the password.

**SMS.** Create an account with [Africa's Talking](https://africastalking.com), buy a little credit, then set
`SMS_BACKEND=africastalking`, `AT_USERNAME`, `AT_API_KEY`. Leave `AT_USERNAME=sandbox` to test without spending credit
(sandbox messages are not delivered to real phones). An approved sender name (`AT_SENDER_ID`) is optional and can take
time to approve. Check the current price per SMS in your account before launch.

Every message attempt, sent or failed, is listed under the member in the admin page.
If an SMS fails (for example no credit), the payment is still recorded. Use **Resend** on the Payments page later.

## 4. The treasurer's phone (Android only)

1. Install **SMS to URL Forwarder** from its [GitHub releases page](https://github.com/bogkonstantin/android_income_sms_gateway_webhook)
   or F-Droid. It is not on Google Play, so Android may show a warning. The project says this is a false alarm.
2. Allow it to read SMS, and turn **battery optimisation off** for the app, or Android may stop it in the background.
3. Add a forwarding rule:
   - Sender: `MPESA`
   - Webhook URL: `https://YOUR-SITE/api/webhook/sms/?key=YOUR_WEBHOOK_SECRET`
   - Request body (JSON): `{"from":"%from%","text":"%text%","sentStamp":"%sentStamp%","receivedStamp":"%receivedStamp%"}`
4. Keep the phone on, with data, until the mission ends.

Test it by sending a real small payment (for example KES 30) with account `Mission Commitment`.

## 5. How matching works

Only messages whose account text contains `mission` count (so tithes and other payments are ignored and never emailed).
The church's Utility balance in the message is thrown away and never stored.

1. **Payer phone** equals a member's phone or M-Pesa number, or a number the treasurer linked before: recorded automatically.
2. **Payer name** equals a member's name (any order, any capitals): recorded automatically.
3. **Close name** (at least two shared names, for example "BELINDA MAYORE"): waits for the treasurer to press **Confirm**.
4. **No match or two possible members**: goes to **Needs attention**. The treasurer contacts the payer, then presses **Assign**.
   The system remembers that payer for next time.

Repeated messages are ignored (each M-Pesa code is stored once). Payments are never deleted, only **Reversed** with a reason.

## 6. Daily use for the treasurer

- **Dashboard**: total raised, who has completed, who has not started, payments needing attention.
- **Members**: search, filter, click a member to edit details and see their payments and messages sent. **Download Excel** for meetings.
- **Payments → Needs attention**: confirm or assign. **Record a payment**: for cash or a missed message.
- **Payments → Message log**: messages the phone sent that the system could not read (tell the developer if you see any).

## What was tested, and what was not

Tested here: the 56 automatic tests; a real run of the finished site in a browser (registration, thank-you page,
sign in, dashboard, members, assign, Excel download); the webhook with your sample message; emails and SMS in
"console" mode (printed, not really sent).

**Not tested with real services:** Africa's Talking, real SMTP email, and the forwarder app on a real phone.
Please test these three on launch day with a KES 30 payment before opening registration to everyone.

## Folders

```
backend/    Django: tracker/ has models, M-Pesa reader, matching, notifications, API, tests
frontend/   React (Vite): src/pages = public pages, src/admin = treasurer pages, dist/ = ready-built site
```

## Production Setup Guides

For detailed production configuration and deployment, see these guides:

- [PRODUCTION_SETUP_SUMMARY.md](PRODUCTION_SETUP_SUMMARY.md) - Quick overview of all production setup
- [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - Complete step-by-step deployment checklist
- [EMAIL_SETUP_GUIDE.md](EMAIL_SETUP_GUIDE.md) - Email configuration (Gmail, Outlook, SendGrid, Mailgun)
- [SMS_SETUP_GUIDE.md](SMS_SETUP_GUIDE.md) - SMS configuration with Africa's Talking
- [DJANGO_PRODUCTION_SETTINGS.md](DJANGO_PRODUCTION_SETTINGS.md) - Django production settings explained
- [DATABASE_SETUP_GUIDE.md](DATABASE_SETUP_GUIDE.md) - Database options (SQLite vs Postgres)
- [STATIC_FILES_GUIDE.md](STATIC_FILES_GUIDE.md) - Static files handling in production
