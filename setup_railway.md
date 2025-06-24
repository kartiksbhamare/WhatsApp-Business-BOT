# Railway Deployment Setup

## 🚀 Deploy to Railway

### 1. Environment Variables
Set these in your Railway project dashboard:

```bash
# Firebase Configuration (REQUIRED)
FIREBASE_PROJECT_ID=appointment-booking-4c50f
FIREBASE_CREDENTIALS_BASE64=<your-base64-string-from-generate_base64_credentials.sh>

# Chrome Configuration (Railway specific)
PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome-stable
CHROME_BIN=/usr/bin/google-chrome-stable
RAILWAY_ENVIRONMENT=true

# Application Configuration
PORT=8000
SALON_NAME=Beauty Salon
DEBUG=false
LOG_LEVEL=INFO
BACKEND_URL=http://localhost:8000
WHATSAPP_SERVICE_URL=http://localhost:3000
```

### 2. Firebase Service Account Key

**Step 1: Generate Base64 Credentials**
```bash
# Run this in your project directory
./generate_base64_credentials.sh
```

**Step 2: Copy the Base64 String**
The script will output something like:
```
FIREBASE_CREDENTIALS_BASE64=ewogICAgInR5cGUiOiAic2VydmljZV9hY2NvdW50IiwK...
```

**Step 3: Set in Railway**
1. Go to your Railway project dashboard
2. Navigate to **Variables** tab
3. Add new variable:
   - **Name**: `FIREBASE_CREDENTIALS_BASE64`
   - **Value**: (paste the long base64 string)

### 3. Deploy Commands

```bash
# Connect to Railway (if not already connected)
railway login

# Link to your project (if not already linked)
railway link

# Deploy
railway up
```

### 4. Health Check
Your app will be available at:
- **Main app**: `https://your-app.railway.app`
- **Health check**: `https://your-app.railway.app/health`
- **WhatsApp QR**: `https://your-app.railway.app/qr`

### 5. Troubleshooting

**Chrome/Puppeteer Issues:**
- ✅ Chrome path detection is now automatic
- ✅ Enhanced Puppeteer arguments for Railway containers
- ✅ Single-process mode for memory efficiency
- Check logs for: `🐳 Using Docker Chrome path: /usr/bin/google-chrome-stable`

**Firebase Issues:**
- ✅ Base64 credentials automatically decoded in containers
- ✅ Fallback to application default credentials
- Check logs for: `🎉 Firebase Admin SDK connected successfully!`
- If failed, verify `FIREBASE_CREDENTIALS_BASE64` is set correctly

**Common Errors & Solutions:**

1. **"Protocol error (Target.setAutoAttach): Target closed"**
   - ✅ Fixed with enhanced Puppeteer arguments
   - Railway containers now use single-process mode

2. **"Your default credentials were not found"**
   - ✅ Set `FIREBASE_CREDENTIALS_BASE64` environment variable
   - ✅ Use the base64 string from `generate_base64_credentials.sh`

3. **"spawn /Applications/Google Chrome ENOENT"**
   - ✅ Fixed with automatic Chrome path detection
   - Railway now correctly uses `/usr/bin/google-chrome-stable`

### 6. Environment Variables Summary

**Required:**
- `FIREBASE_CREDENTIALS_BASE64` (from generate script)
- `FIREBASE_PROJECT_ID=appointment-booking-4c50f`

**Recommended:**
- `PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome-stable`
- `RAILWAY_ENVIRONMENT=true`
- `SALON_NAME=Beauty Salon`

**Optional:**
- `DEBUG=false`
- `LOG_LEVEL=INFO`

### 7. Deployment Checklist

- [ ] Run `./generate_base64_credentials.sh`
- [ ] Copy base64 credentials to Railway
- [ ] Set all required environment variables
- [ ] Deploy with `railway up`
- [ ] Check health endpoint
- [ ] Test WhatsApp QR code generation
- [ ] Verify Firebase connection in logs

🎊 Your Railway deployment should now work perfectly! 