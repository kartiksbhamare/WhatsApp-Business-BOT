# 🔗 Localhost URL Removal & Environment Configuration Guide

This guide explains how all hardcoded localhost URLs have been removed from the Smart WhatsApp Booking Bot project and replaced with configurable environment variables.

## 📋 What Was Changed

### ❌ Before (Hardcoded Localhost)
```javascript
// whatsapp-simple.js
const response = await axios.post('http://localhost:8000/webhook/whatsapp', webhookData);

// app/config.py
WHATSAPP_SERVICE_URL: str = "http://localhost:3000"

// app/main_simple.py
whatsapp_service_url = f"http://localhost:3000/qr"
```

### ✅ After (Environment Variables)
```javascript
// whatsapp-simple.js
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const response = await axios.post(`${BACKEND_URL}/webhook/whatsapp`, webhookData);

// app/config.py
BACKEND_URL: str = "http://localhost:8000"  # Default for local development
WHATSAPP_SERVICE_URL: str = "http://localhost:3000"  # Default for local development

// app/main_simple.py
whatsapp_service_url = f"{settings.WHATSAPP_SERVICE_URL}/qr"
```

## 🔧 Environment Variables

### Core Service URLs
- `BACKEND_URL` - Backend API URL (default: `http://localhost:8000`)
- `WHATSAPP_SERVICE_URL` - WhatsApp service URL (default: `http://localhost:3000`)
- `BACKEND_PORT` - Backend port (default: `8000`)
- `WHATSAPP_PORT` - WhatsApp service port (default: `3000`)

### Service Configuration
- `SALON_NAME` - Your salon name (default: `Beauty Salon`)
- `BACKEND_HOST` - Backend host (default: `0.0.0.0`)
- `WHATSAPP_HOST` - WhatsApp host (default: `0.0.0.0`)

### Environment Detection
- `RAILWAY_ENVIRONMENT` - Automatically detected on Railway
- `DOCKER_ENV` - Set to `true` for Docker containers
- `PORT` - Railway/Heroku port override

## 🚀 Quick Setup

### 1. Interactive Setup
```bash
./setup_env.sh
```

### 2. Manual Setup
Copy the template and customize:
```bash
cp env.template .env
# Edit .env with your preferred editor
```

## 🌍 Deployment Configurations

### 🏠 Local Development
```env
BACKEND_URL=http://localhost:8000
WHATSAPP_SERVICE_URL=http://localhost:3000
BACKEND_PORT=8000
WHATSAPP_PORT=3000
SALON_NAME=Beauty Salon
DEBUG=true
```

### 🚂 Railway Production
```env
BACKEND_URL=https://your-app.railway.app
WHATSAPP_SERVICE_URL=https://your-app.railway.app
RAILWAY_ENVIRONMENT=true
FIREBASE_CREDENTIALS_BASE64=your_base64_credentials
PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome-stable
DEBUG=false
```

### 🐳 Docker Compose
```env
BACKEND_URL=http://backend:8000
WHATSAPP_SERVICE_URL=http://whatsapp:3000
DOCKER_ENV=true
PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome-stable
```

### ⚙️ Custom Deployment
```env
BACKEND_URL=https://api.yourdomain.com
WHATSAPP_SERVICE_URL=https://whatsapp.yourdomain.com
SALON_NAME=Your Salon Name
```

## 📁 Files Modified

### Core Application Files
- `app/config.py` - Added environment variable support with auto-detection
- `whatsapp-simple.js` - Uses `BACKEND_URL` environment variable
- `app/main_simple.py` - Uses settings for WhatsApp service URL
- `app/services/whatsapp.py` - Uses settings for service communication

### Startup Scripts
- `start_bot.sh` - Environment-aware startup with configurable URLs
- `run_simple.sh` - Complete setup script with environment support
- `start_railway.sh` - Railway-optimized startup with environment variables

### Container Configuration
- `Dockerfile` - Environment variable support and dynamic configuration
- `docker-compose.yml` - Service communication via environment variables

### Setup & Utilities
- `setup_env.sh` - Interactive environment configuration script
- `env.template` - Environment variable template with examples

## 🔄 Auto-Detection Features

The application automatically detects your deployment environment:

### Railway Detection
```python
if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("PORT"):
    logger.info("🚂 Railway environment detected")
    # Uses Railway-specific configurations
```

### Docker Detection
```python
elif os.getenv("DOCKER_ENV") or os.path.exists("/.dockerenv"):
    logger.info("🐳 Docker environment detected")
    # Uses Docker service names for internal communication
```

### Local Development
```python
else:
    logger.info("💻 Local development environment detected")
    # Uses localhost defaults
```

## 🛠️ Migration Guide

### From Hardcoded to Environment Variables

1. **Stop existing services:**
   ```bash
   pkill -f "uvicorn"
   pkill -f "node.*whatsapp"
   ```

2. **Set up environment:**
   ```bash
   ./setup_env.sh
   ```

3. **Start with new configuration:**
   ```bash
   ./start_bot.sh
   ```

### Updating Existing Deployments

#### Railway
1. Update environment variables in Railway dashboard
2. Set `BACKEND_URL` and `WHATSAPP_SERVICE_URL` to your Railway app URL
3. Redeploy

#### Docker
1. Update your `docker-compose.yml` or Docker run commands
2. Use service names for internal communication
3. Rebuild and restart containers

## 🔍 Verification

### Check Configuration
```bash
# Local development
curl http://localhost:8000/health

# Production (replace with your domain)
curl https://your-app.railway.app/health
```

### Environment Variables in Use
```bash
# View current configuration
python3 -c "
from app.config import get_settings
settings = get_settings()
print(f'Backend: {settings.BACKEND_URL}')
print(f'WhatsApp: {settings.WHATSAPP_SERVICE_URL}')
print(f'Salon: {settings.SALON_NAME}')
"
```

## 🐛 Troubleshooting

### Common Issues

1. **Service can't communicate:**
   - Check `BACKEND_URL` and `WHATSAPP_SERVICE_URL` are correct
   - Verify ports are not blocked
   - Ensure services are running on expected ports

2. **Environment variables not loaded:**
   - Verify `.env` file exists and is readable
   - Check for syntax errors in `.env`
   - Restart services after changing environment variables

3. **Railway deployment issues:**
   - Ensure `RAILWAY_ENVIRONMENT=true` is set
   - Use HTTPS URLs for Railway public domains
   - Check Railway logs for configuration errors

### Debug Commands
```bash
# Check environment loading
source .env && echo "Backend: $BACKEND_URL, WhatsApp: $WHATSAPP_SERVICE_URL"

# Test service connectivity
curl -f $BACKEND_URL/health
curl -f $WHATSAPP_SERVICE_URL/health

# View application logs
tail -f app.log
```

## 🎯 Benefits

### ✅ Advantages
- **Deployment Flexibility:** Works across local, Railway, Docker, and custom environments
- **No Code Changes:** Switch environments by changing `.env` file only
- **Auto-Detection:** Automatically configures for Railway and Docker
- **Backward Compatibility:** Maintains localhost defaults for existing setups
- **Easy Scaling:** Add new environments without code modifications

### 🔧 Maintenance
- Single source of truth for all URLs
- Environment-specific configurations
- Simplified deployment process
- Easier debugging and troubleshooting

## 📚 Additional Resources

- [Environment Variables Best Practices](env.template)
- [Railway Deployment Guide](setup_railway.md)
- [Docker Configuration](docker-compose.yml)
- [Configuration Reference](app/config.py)

---

**🎉 Your WhatsApp Booking Bot is now completely environment-configurable with zero hardcoded localhost dependencies!** 