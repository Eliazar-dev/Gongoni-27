# Email Setup Guide for Production

This guide walks you through setting up email for the Gongoni 27 tracker using Gmail (free and reliable).

## Option 1: Gmail (Recommended - Free)

### Step 1: Enable 2-Factor Authentication
1. Go to https://myaccount.google.com/security
2. Sign in to your Google account
3. Find "2-Step Verification" and turn it on if not already enabled
4. Follow the prompts to set up 2FA (can use SMS or authenticator app)

### Step 2: Create an App Password
1. Go to https://myaccount.google.com/apppasswords
2. You may need to sign in again
3. Click "Select app" → choose "Mail"
4. Click "Select device" → choose "Other (Custom name)"
5. Enter a name like "Gongoni 27 Tracker"
6. Click "Generate"
7. **Copy the 16-character password** (it will look like: `abcd efgh ijkl mnop`)
8. Save this password securely - you won't see it again

### Step 3: Configure .env
In your production `.env` file, set:

```env
EMAIL_BACKEND_MODE=smtp
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=1
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=abcd-efgh-ijkl-mnop  # Your 16-char app password (with or without spaces)
DEFAULT_FROM_EMAIL=Gongoni 27 <your-email@gmail.com>
```

**Important:** The app password is NOT your regular Gmail password. Regular passwords will not work with SMTP.

### Step 4: Test Email Sending
After deployment, register a test member and verify the welcome email arrives.

---

## Option 2: Outlook/Hotmail (Free)

### Step 1: Enable 2-Factor Authentication
1. Go to https://account.live.com/proofs/Applications
2. Sign in to your Microsoft account
3. Enable 2-factor authentication if not already enabled

### Step 2: Create an App Password
1. Go to https://account.live.com/proofs/Applications
2. Click "Create a new app password"
3. Name it "Gongoni 27 Tracker"
4. Copy the generated password

### Step 3: Configure .env
```env
EMAIL_BACKEND_MODE=smtp
EMAIL_HOST=smtp.office365.com
EMAIL_PORT=587
EMAIL_USE_TLS=1
EMAIL_HOST_USER=your-email@outlook.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=Gongoni 27 <your-email@outlook.com>
```

---

## Option 3: SendGrid (Free tier available)

### Step 1: Create SendGrid Account
1. Go to https://sendgrid.com and sign up
2. Verify your email address
3. Complete the sender verification (required for free tier)

### Step 2: Get API Key
1. Go to Settings → API Keys
2. Click "Create API Key"
3. Name it "Gongoni 27 Tracker"
4. Set permissions to "Mail Send"
5. Copy the API key

### Step 3: Configure .env
```env
EMAIL_BACKEND_MODE=smtp
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=1
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=SG.your-api-key-here
DEFAULT_FROM_EMAIL=Gongoni 27 <your-verified-email@domain.com>
```

**Note:** The free tier allows 100 emails/day forever, which should be sufficient for this project.

---

## Option 4: Mailgun (Free trial)

### Step 1: Create Mailgun Account
1. Go to https://www.mailgun.com and sign up
2. Verify your email address
3. Add your domain (or use the sandbox domain for testing)

### Step 2: Get SMTP Credentials
1. Go to the Domains section
2. Click on your domain
3. Find the SMTP credentials

### Step 3: Configure .env
```env
EMAIL_BACKEND_MODE=smtp
EMAIL_HOST=smtp.mailgun.org
EMAIL_PORT=587
EMAIL_USE_TLS=1
EMAIL_HOST_USER=postmaster@your-domain.mailgun.org
EMAIL_HOST_PASSWORD=your-smtp-password
DEFAULT_FROM_EMAIL=Gongoni 27 <noreply@your-domain.com>
```

**Note:** The free trial provides 5,000 emails/month for the first month, then pay-as-you-go.

---

## Troubleshooting

### Emails not sending
- Verify the password is correct (for Gmail, use App Password, not regular password)
- Check that 2FA is enabled on the account
- Ensure `EMAIL_BACKEND_MODE=smtp` in `.env`
- Check server logs for error messages

### Gmail: "Less secure apps" error
- This error is outdated. Use App Passwords instead (method above)
- App Passwords work even with 2FA enabled

### Rate limiting
- Gmail: ~100-200 emails/day for free accounts
- SendGrid: 100 emails/day on free tier
- If you expect more, consider a paid plan or use a transactional email service

### Testing before production
- Set `EMAIL_BACKEND_MODE=console` in `.env`
- Emails will print in the terminal instead of being sent
- Verify the content looks correct, then switch to `smtp`

---

## Security Best Practices

1. **Never commit .env file** - It contains your email password
2. **Use strong, unique passwords** - Don't reuse passwords
3. **Enable 2FA** - Required for Gmail App Passwords
4. **Monitor email delivery** - Check bounce rates and spam reports
5. **Set up SPF/DKIM** - For custom domains, improve deliverability
6. **Regular password rotation** - Change app passwords periodically

---

## Recommended Choice

For this project, **Gmail with App Password** is recommended because:
- Free and reliable
- Easy to set up
- Sufficient for the expected volume
- No domain verification required
- Good deliverability rates
