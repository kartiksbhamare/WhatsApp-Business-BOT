# 🚀 Railway Multi-Salon Deployment Guide

## 🎯 Single-Salon Mode for Railway

Due to Railway's resource constraints, this Smart WhatsApp Booking Bot now runs in **Single-Salon Mode** where each Railway deployment handles one salon to ensure stable Chrome/WhatsApp connections.

## 📋 Deployment Options

### Option 1: Single Salon Deployment (Recommended for Testing)

Deploy one salon to test the system:

1. **Fork/Clone the repository**
2. **Connect to Railway**
3. **Set environment variable**: `ACTIVE_SALON=salon_a`
4. **Deploy**

**Result**: One stable salon with reliable QR code generation

### Option 2: Multi-Deployment Setup (Production)

Deploy 3 separate Railway services for all salons:

#### 🏪 Salon A (Downtown Beauty) Deployment:
```bash
# Repository: your-repo
# Environment: ACTIVE_SALON=salon_a
# URL: https://salon-a-bot.railway.app/qr/salon_a
```

#### 💇 Salon B (Uptown Hair Studio) Deployment:
```bash
# Repository: your-repo (same repo, different service)
# Environment: ACTIVE_SALON=salon_b  
# URL: https://salon-b-bot.railway.app/qr/salon_b
```

#### ✨ Salon C (Luxury Spa) Deployment:
```bash
# Repository: your-repo (same repo, different service)
# Environment: ACTIVE_SALON=salon_c
# URL: https://salon-c-bot.railway.app/qr/salon_c
```

## 🔧 How to Deploy Multiple Salons

### Step 1: Create 3 Railway Services

1. Go to Railway dashboard
2. Create **3 separate services** from the same GitHub repo:
   - `salon-a-whatsapp-bot`
   - `salon-b-whatsapp-bot` 
   - `salon-c-whatsapp-bot`

### Step 2: Configure Environment Variables

**For Salon A Service:**
```bash
ACTIVE_SALON=salon_a
NODE_ENV=production
```

**For Salon B Service:**
```bash
ACTIVE_SALON=salon_b
NODE_ENV=production
```

**For Salon C Service:**
```bash
ACTIVE_SALON=salon_c
NODE_ENV=production
```

### Step 3: Deploy and Get URLs

Each service will get its own Railway URL:
- **Salon A**: `https://salon-a-whatsapp-bot-production.up.railway.app/qr/salon_a`
- **Salon B**: `https://salon-b-whatsapp-bot-production.up.railway.app/qr/salon_b`
- **Salon C**: `https://salon-c-whatsapp-bot-production.up.railway.app/qr/salon_c`

## 📱 QR Code URLs

Each deployment will serve QR codes at:
- `/qr/salon_a` (regardless of ACTIVE_SALON, routes to active salon)
- `/health` (health check)
- `/` (main page with salon info)

## 💡 Benefits of Single-Salon Mode

✅ **Stable Chrome processes** - No resource conflicts
✅ **Reliable QR generation** - Each salon gets full container resources  
✅ **Better error isolation** - One salon failure doesn't affect others
✅ **Easier debugging** - Clear logs per salon
✅ **Scalable** - Add more salons by creating more services

## 🔄 Switching Active Salon

To change which salon a deployment serves:

1. Go to Railway service settings
2. Update `ACTIVE_SALON` environment variable
3. Redeploy

Valid values: `salon_a`, `salon_b`, `salon_c`

## 🎯 Quick Start (Single Salon)

1. **Deploy to Railway**
2. **Set**: `ACTIVE_SALON=salon_a`
3. **Visit**: `https://your-app.railway.app/qr/salon_a`
4. **Scan QR code** with WhatsApp
5. **Start receiving bookings!**

## 🆘 Troubleshooting

**Q: QR code not showing?**
A: Check logs for Chrome initialization errors. Single-salon mode should resolve most issues.

**Q: "Could not connect to device"?**
A: This should be fixed in single-salon mode. If still occurring, check Railway resource usage.

**Q: Want to test all 3 salons?**
A: Create 3 separate Railway services with different `ACTIVE_SALON` values.

---

**This single-salon approach ensures stable, reliable WhatsApp connections in Railway's environment!** 🎉 