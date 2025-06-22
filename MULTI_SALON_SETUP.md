# 🏢 Multi-Salon WhatsApp Booking Bot

## 🌟 Overview

This implementation supports **multiple salons** with a single backend and multiple WhatsApp services. Each salon has its own WhatsApp number, services, barbers, and booking system while sharing the same infrastructure.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                Single Backend (Port 8000)           │
├─────────────────────────────────────────────────────┤
│ /webhook/whatsapp/salon_a ← WhatsApp Service A      │
│ /webhook/whatsapp/salon_b ← WhatsApp Service B      │ 
│ /webhook/whatsapp/salon_c ← WhatsApp Service C      │
└─────────────────────────────────────────────────────┘

┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Salon A          │ │ Salon B          │ │ Salon C          │
│ Downtown Beauty  │ │ Uptown Hair      │ │ Luxury Spa       │
│ Port 3001        │ │ Port 3002        │ │ Port 3003        │
│ Phone: +1234...  │ │ Phone: +0987...  │ │ Phone: +1122...  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

## 🚀 Quick Start

### 1. **Start All Services**
```bash
./start-multi-salon-services.sh
```

### 2. **Check Status**
```bash
./check-multi-salon-status.sh
```

### 3. **Connect WhatsApp Numbers**
- **Salon A**: http://localhost:3001/qr
- **Salon B**: http://localhost:3002/qr  
- **Salon C**: http://localhost:3003/qr

### 4. **Stop All Services**
```bash
./stop-multi-salon-services.sh
```

## 📱 Salon Configuration

| Salon | Name | Port | Phone | WhatsApp QR |
|-------|------|------|-------|-------------|
| **Salon A** | Downtown Beauty Salon | 3001 | +1234567890 | http://localhost:3001/qr |
| **Salon B** | Uptown Hair Studio | 3002 | +0987654321 | http://localhost:3002/qr |
| **Salon C** | Luxury Spa & Salon | 3003 | +1122334455 | http://localhost:3003/qr |

## 🛠️ Services & Data

### **Default Services (Per Salon)**
1. Hair Cut ($25, 30 mins)
2. Hair Color ($75, 90 mins)
3. Manicure ($30, 45 mins)
4. Pedicure ($40, 45 mins)
5. Hair Wash & Blow Dry ($20, 30 mins)
6. Facial Treatment ($50, 60 mins)
7. Beard Trim ($15, 20 mins)
8. Eyebrow Threading ($12, 15 mins)

### **Default Staff**

**Salon A (Downtown Beauty):**
- Maya: Hair Color, Facial Treatments
- Raj: Men's Grooming, Nail Care

**Salon B (Uptown Hair):**
- Aisha: Hair Styling, Beauty Treatments
- Ravi: Men's Haircuts, Beard Styling

**Salon C (Luxury Spa):**
- Priya: Spa Treatments, Nail Art
- Dev: Hair Design, Color Specialist

## 📋 API Endpoints

### **Multi-Salon Endpoints**
```
GET  /api/salons                     # Get all salons
GET  /api/services/{salon_id}        # Get services for specific salon
GET  /api/barbers/{salon_id}         # Get barbers for specific salon
GET  /api/barbers/{salon_id}/service/{service_id}  # Get barbers for service
GET  /api/slots/{salon_id}/{barber_name}           # Get available slots
```

### **Webhook Endpoints**
```
POST /webhook/whatsapp/{salon_id}    # Salon-specific webhooks
POST /webhook/whatsapp               # Legacy webhook (routes to salon_a)
```

### **Example API Calls**
```bash
# Get all salons
curl http://localhost:8000/api/salons

# Get Salon A services  
curl http://localhost:8000/api/services/salon_a

# Get Salon B barbers
curl http://localhost:8000/api/barbers/salon_b

# Check Salon A health
curl http://localhost:3001/health
```

## 🔧 Configuration

### **Environment Variables**
```bash
# Backend
BACKEND_URL=http://127.0.0.1:8000

# Salon Ports
SALON_A_PORT=3001
SALON_B_PORT=3002  
SALON_C_PORT=3003

# Salon Phone Numbers
SALON_A_PHONE=+1234567890
SALON_B_PHONE=+0987654321
SALON_C_PHONE=+1122334455
```

### **Phone to Salon Mapping**
The system automatically routes messages based on the receiving WhatsApp number:
- `+1234567890` → `salon_a` (Downtown Beauty)
- `+0987654321` → `salon_b` (Uptown Hair)
- `+1122334455` → `salon_c` (Luxury Spa)

## 💬 Customer Experience

### **Booking Flow (Same for All Salons)**
1. Customer sends "hi" to any salon's WhatsApp
2. Bot shows **salon-specific** services and prices
3. Customer selects service number
4. Bot shows **salon-specific** available barbers
5. Customer selects barber
6. Bot shows date options (today/tomorrow)
7. Customer selects date
8. Bot shows **salon-specific** available time slots
9. Customer selects time
10. ✅ **Booking confirmed** with salon name included

### **Example Conversation**
```
Customer: hi
Bot: 👋 Welcome to Downtown Beauty Salon! ✨

Here are our services:
1. Hair Cut ($25, 30 mins)
2. Hair Color ($75, 90 mins)
...

Customer: 1
Bot: ✅ You've selected Hair Cut!

👨‍💼 Please choose your preferred stylist:
1. ✂️ Maya
2. ✂️ Raj

Customer: 1
Bot: 🎉 Great! You've selected ✂️ Maya.

📅 Please choose your preferred date:
1. 📅 Today (Monday, January 22)
2. 🌅 Tomorrow (Tuesday, January 23)
...
```

## 🗄️ Database Structure

```
salons/
├── salon_a: { name: "Downtown Beauty", phone: "+1234567890", ... }
├── salon_b: { name: "Uptown Hair", phone: "+0987654321", ... }
└── salon_c: { name: "Luxury Spa", phone: "+1122334455", ... }

services/
├── salon_a_1: { salon_id: "salon_a", name: "Hair Cut", ... }
├── salon_a_2: { salon_id: "salon_a", name: "Hair Color", ... }
├── salon_b_1: { salon_id: "salon_b", name: "Hair Cut", ... }
└── ...

barbers/
├── salon_a_maya: { salon_id: "salon_a", name: "Maya", ... }
├── salon_a_raj: { salon_id: "salon_a", name: "Raj", ... }
├── salon_b_aisha: { salon_id: "salon_b", name: "Aisha", ... }
└── ...

bookings/
├── booking_1: { salon_id: "salon_a", service_id: "salon_a_1", ... }
├── booking_2: { salon_id: "salon_b", service_id: "salon_b_2", ... }
└── ...
```

## 🔍 Monitoring & Troubleshooting

### **Health Checks**
```bash
# Backend health
curl http://localhost:8000/health

# WhatsApp service health
curl http://localhost:3001/health  # Salon A
curl http://localhost:3002/health  # Salon B
curl http://localhost:3003/health  # Salon C
```

### **Log Monitoring**
Each service logs with salon identifiers:
```
📨 [Downtown Beauty Salon] Received message: hi
📱 Processing message for salon: salon_a
✅ [Downtown Beauty Salon] Reply sent successfully
```

### **Common Issues**

1. **Port Already in Use**
   ```bash
   # Check what's using the port
   lsof -ti :3001
   
   # Kill the process
   kill -9 <PID>
   ```

2. **WhatsApp Not Connecting**
   - Check QR code hasn't expired (45 seconds)
   - Ensure phone number is correct in config
   - Verify WhatsApp Web is enabled on phone

3. **Messages Not Routing**
   - Check phone number mapping in config
   - Verify webhook URLs are correct
   - Check backend logs for routing info

## 🚀 Deployment

### **Railway Deployment**
Deploy as separate services:
1. **Backend Service**: FastAPI app (Port $PORT)
2. **Salon A Service**: WhatsApp service A (Port $PORT)  
3. **Salon B Service**: WhatsApp service B (Port $PORT)
4. **Salon C Service**: WhatsApp service C (Port $PORT)

### **Environment Variables for Production**
```bash
# Backend service
BACKEND_URL=https://your-backend.railway.app

# WhatsApp services  
SALON_A_WHATSAPP_URL=https://salon-a.railway.app
SALON_B_WHATSAPP_URL=https://salon-b.railway.app  
SALON_C_WHATSAPP_URL=https://salon-c.railway.app

# Update webhook URLs accordingly
```

## 🎯 Benefits

✅ **Scalable**: Easy to add more salons  
✅ **Isolated**: Each salon has separate data  
✅ **Cost-Effective**: Shared backend infrastructure  
✅ **Flexible**: Different services/staff per salon  
✅ **Maintainable**: Single codebase for all salons  
✅ **Reliable**: Independent WhatsApp connections  

## 📞 Support

For issues or questions:
1. Check logs in each service
2. Run `./check-multi-salon-status.sh` 
3. Verify configuration in `app/config.py`
4. Test API endpoints manually
5. Check WhatsApp service connectivity

---

🎉 **Your Multi-Salon WhatsApp Booking Bot is ready to serve multiple locations!** 