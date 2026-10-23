# SMS Setup Guide for Production

This guide walks you through setting up SMS notifications using Africa's Talking, the recommended SMS provider for Kenya.

## Why Africa's Talking?

- Low cost SMS rates in Kenya (~KES 1-2 per SMS)
- Reliable delivery to Kenyan networks
- Easy API integration
- Sandbox mode for testing without spending
- Developer-friendly dashboard

---

## Step 1: Create an Africa's Talking Account

1. Go to https://africastalking.com
2. Click "Sign Up" in the top right
3. Fill in your details:
   - Full name
   - Email address
   - Phone number (will receive verification code)
   - Country: Kenya
4. Click "Create Account"
5. Check your email for the verification link
6. Enter the SMS verification code sent to your phone

---

## Step 2: Add SMS Credit

1. After signing in, you'll be on the dashboard
2. Click "Billing" or "Buy SMS" in the menu
3. Choose your payment method (M-Pesa, Card, etc.)
4. Buy a small amount for testing (e.g., KES 100 = ~50-100 SMS)
5. **Check the current price per SMS** in your account
   - Rates vary by network (Safaricom, Airtel, Telkom)
   - Typical range: KES 0.80 - KES 2.00 per SMS

---

## Step 3: Get Your API Credentials

1. Go to the dashboard
2. Click "Settings" or "API Credentials"
3. You'll see:
   - **Username**: Your account username (e.g., "sandbox" or your chosen username)
   - **API Key**: A long alphanumeric string (keep this secret!)

**Copy both values** - you'll need them for the `.env` file.

---

## Step 4: Configure .env File

In your production `.env` file, set:

```env
SMS_BACKEND=africastalking
AT_USERNAME=your-username
AT_API_KEY=your-api-key-here
AT_SENDER_ID=
SEND_WELCOME_SMS=0
```

### For Testing (No Cost)
```env
SMS_BACKEND=africastalking
AT_USERNAME=sandbox
AT_API_KEY=your-sandbox-api-key
AT_SENDER_ID=
SEND_WELCOME_SMS=0
```

**Note:** Sandbox mode lets you test without spending credit, but messages are not delivered to real phones.

---

## Step 5: Optional - Set Up a Sender ID

A Sender ID is the name that appears as the sender (e.g., "GONGONI" instead of a phone number).

### Requirements:
- Must be 4-11 characters
- Must be alphabetic (no numbers or special characters)
- Must not contain "SMS" or premium rate keywords
- Takes 1-3 business days to approve (free)

### To Apply:
1. Go to Africa's Talking dashboard
2. Click "SMS" → "Sender IDs"
3. Click "Apply for Sender ID"
4. Fill in:
   - Sender ID name (e.g., "GONGONI")
   - Sample message content
   - Your organization details
5. Submit and wait for approval

### Once Approved:
```env
AT_SENDER_ID=GONGONI
```

**Note:** You can launch without a Sender ID and add it later. The default is a numeric sender ID.

---

## Step 6: Estimate SMS Costs

### Scenario: 100 Members
- Registration welcome SMS: 100 SMS (if enabled)
- Payment receipts (average 2 payments per member): 200 SMS
- Total: ~300 SMS
- Estimated cost: KES 240 - KES 600 (at KES 0.80 - KES 2.00 per SMS)

### Scenario: 200 Members
- Registration welcome SMS: 200 SMS (if enabled)
- Payment receipts (average 2 payments per member): 400 SMS
- Total: ~600 SMS
- Estimated cost: KES 480 - KES 1,200

**Recommendation:** Start with KES 500-1,000 credit, then top up as needed.

---

## Step 7: Test SMS Sending

### Option A: Sandbox Testing (Free)
1. Set `AT_USERNAME=sandbox` in `.env`
2. Make a test payment via the admin panel
3. Check the terminal - you'll see the SMS content printed
4. No actual SMS is sent, no credit is spent

### Option B: Real Testing (Small Cost)
1. Set your real username and API key in `.env`
2. Register a test member with your own phone number
3. Make a small test payment (KES 30)
4. Verify the SMS arrives on your phone
5. Check the "Message log" in the admin panel

---

## Step 8: Configure Welcome SMS

By default, only a welcome **email** is sent at registration. SMS is sent only for payment receipts.

To also send a welcome SMS (costs extra credit):

```env
SEND_WELCOME_SMS=1
```

**Recommendation:** Keep `SEND_WELCOME_SMS=0` unless you have specific reason to enable it. The welcome email is sufficient.

---

## Troubleshooting

### SMS not sending
- Verify `SMS_BACKEND=africastalking` in `.env`
- Check you have SMS credit in your Africa's Talking account
- Verify your API key is correct (copy-paste without extra spaces)
- Check server logs for error messages

### "Invalid username or API key"
- Double-check the username (case-sensitive)
- Regenerate the API key in the dashboard if needed
- Ensure you're not using sandbox credentials in production

### Messages not delivered
- Check the phone number format (must be in international format: 254...)
- Verify the recipient's network is active
- Check Africa's Talking delivery logs in the dashboard
- Some networks may block promotional SMS

### Delivery delays
- Network congestion can cause delays (usually 1-5 minutes)
- During peak hours, delays up to 30 minutes are possible
- Check Africa's Talking status page for outages

### Sandbox messages not arriving
- This is expected - sandbox messages are never delivered to real phones
- Switch to production credentials to test real delivery

---

## Alternative SMS Providers

If Africa's Talking doesn't work for you, consider:

### 1. Twilio
- Global coverage, reliable
- Higher cost for Kenya (~KES 15-20 per SMS)
- Sign up: https://www.twilio.com
- Requires different integration (not directly supported)

### 2. Infobip
- Good coverage in Africa
- Competitive pricing
- Sign up: https://www.infobip.com
- Requires different integration (not directly supported)

### 3. SMSProvider
- Kenyan provider
- Good local rates
- Sign up: https://www.smsprovider.co.ke
- Requires different integration (not directly supported)

**Note:** The project is configured for Africa's Talking. Using another provider would require code changes.

---

## Security Best Practices

1. **Never commit .env file** - It contains your API key
2. **Keep API key secret** - Anyone with it can send SMS from your account
3. **Monitor credit usage** - Check Africa's Talking dashboard regularly
4. **Set up alerts** - Get notified when credit is low
5. **Regenerate keys periodically** - If you suspect a compromise
6. **Use environment variables** - Never hardcode credentials in code

---

## Monitoring SMS Delivery

After launch, monitor SMS delivery:

1. **Africa's Talking Dashboard**
   - Check delivery logs
   - View failed messages
   - Monitor credit balance

2. **Admin Panel**
   - Go to "Members" → click a member → "Messages sent"
   - Shows all email and SMS attempts
   - Failed messages can be resent

3. **Set Up Alerts**
   - Configure low credit alerts in Africa's Talking
   - Recommended alert threshold: 20% of remaining credit

---

## Recommended Setup

For this project, use this configuration:

```env
SMS_BACKEND=africastalking
AT_USERNAME=your-production-username
AT_API_KEY=your-production-api-key
AT_SENDER_ID=        # Leave empty initially, add after approval
SEND_WELCOME_SMS=0   # Keep disabled to save credit
```

This balances cost and functionality. Add a Sender ID later if desired.
