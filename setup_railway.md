# Railway Deployment Setup

## 🚀 Deploy to Railway

### 1. Environment Variables
Set these in your Railway project dashboard:

```bash
# Firebase Configuration
FIREBASE_PROJECT_ID=appointment-booking-4c50f
FIREBASE_CREDENTIALS_PATH=firebase-key.json

# Chrome Configuration (Railway specific)
PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome-stable
PUPPETEER_ARGS=--no-sandbox --disable-setuid-sandbox --disable-dev-shm-usage --disable-gpu --no-first-run --no-zygote --single-process --disable-extensions
CHROME_BIN=/usr/bin/google-chrome-stable

# Application Configuration
PORT=8000
SALON_NAME=Beauty Salon
DEBUG=false
LOG_LEVEL=INFO
```

### 2. Firebase Service Account Key

**Option A: Environment Variable (Recommended for Railway)**
1. Convert your `firebase-key.json` to base64:
   ```bash
   base64 -i firebase-key.json
   ```
2. Set as environment variable in Railway:
   ```
   FIREBASE_CREDENTIALS_BASE64=<your-base64-string>
   ```

**Option B: Upload File**
1. Upload `firebase-key.json` to your Railway project
2. Ensure it's in the root directory

### 3. Deploy Commands

```bash
# Connect to Railway
railway login

# Link to your project
railway link

# Deploy
railway up
```

### 4. Health Check
Your app will be available at:
- Main app: `https://your-app.railway.app`
- Health check: `https://your-app.railway.app/health`
- WhatsApp QR: `https://your-app.railway.app/qr`

### 5. Troubleshooting

**Chrome Issues:**
- Railway containers should automatically find Chrome at `/usr/bin/google-chrome-stable`
- Check logs for Chrome path detection messages

**Firebase Issues:**
- Ensure `FIREBASE_PROJECT_ID` is set correctly
- Verify Firebase credentials are properly configured
- Check that your Firebase project allows server-side access

**Port Issues:**
- Railway automatically handles port mapping
- Your app should listen on the PORT environment variable 