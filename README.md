# 🚀 Smart WhatsApp Booking Bot - Multi-Salon Edition

[![Production Ready](https://img.shields.io/badge/Production-Ready-brightgreen.svg)](https://github.com/kartiksbhamare/WhatsApp-Business-BOT)
[![Multi-Salon](https://img.shields.io/badge/Multi--Salon-Supported-blue.svg)](https://github.com/kartiksbhamare/WhatsApp-Business-BOT)
[![Railway](https://img.shields.io/badge/Deploy-Railway-purple.svg)](https://railway.app)

## 🏢 Multi-Salon Architecture

This system now supports **true multi-salon separation** with:

- **3 Separate WhatsApp Numbers** (one per salon)
- **Individual QR Codes** for each salon
- **Automatic Salon Detection** - customers just send "hi"
- **Complete Service Isolation** - no cross-salon confusion

### 🎯 Salon Configuration

| Salon | Port | WhatsApp Number | Services |
|-------|------|----------------|----------|
| 🏪 Downtown Beauty | 3005 | Individual Number | Hair Cut, Facial, Wash |
| 💇 Uptown Hair Studio | 3006 | Individual Number | Hair Styling, Treatments |
| ✨ Luxury Spa & Salon | 3007 | Individual Number | Spa, Massage, Premium Services |

## 🚀 Quick Start

### Local Testing
```bash
npm run unified
```

### Railway Deployment
1. Push to GitHub
2. Connect to Railway
3. Auto-deployment handles all 3 salons

## 📱 QR Code URLs (Production)
- Salon A: `https://your-app.railway.app:3005/qr`
- Salon B: `https://your-app.railway.app:3006/qr`
- Salon C: `https://your-app.railway.app:3007/qr`

---

*Powered by Option A: Unified Multi-Salon Service Architecture*

## 🚀 Features

- **Free WhatsApp Integration** using Venom Bot (no more Twilio costs!)
- Interactive WhatsApp booking conversations
- Service selection and barber assignment
- Real-time slot availability
- Firebase database integration
- Google Calendar sync (optional)
- RESTful API endpoints
- Easy deployment

## 🛠️ Technologies

- **Backend**: Python FastAPI
- **WhatsApp**: Venom Bot (Node.js)
- **Database**: Firebase Firestore
- **Calendar**: Google Calendar API (optional)

## 📋 Prerequisites

- Python 3.8+
- Node.js 16+
- Firebase account
- WhatsApp account for the bot

## ⚙️ Installation & Setup

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd Smart-WhatsApp-Booking-Bot
```

### 2. Install Dependencies

#### Install Node.js Dependencies (for Venom Bot)
```bash
npm install
```

#### Install Python Dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the root directory:

```bash
# Venom Bot Settings
VENOM_SERVICE_URL=http://localhost:3000

# Firebase Settings
FIREBASE_PROJECT_ID=your-firebase-project-id

# Optional: Google Calendar Integration
GOOGLE_CALENDAR_CREDENTIALS_PATH=client_secret.json
GOOGLE_CALENDAR_ID=your-calendar-id@gmail.com

# App Settings
DEBUG=false
LOG_LEVEL=INFO
```

### 4. Firebase Setup

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or use existing one
3. Go to Project Settings → Service Accounts
4. Generate a new private key and save it as `firebase-key.json` in the root directory
5. Enable Firestore Database in your Firebase project

### 5. Start the Services

#### Option 1: Use the Start Script (Recommended)
```bash
chmod +x start-services.sh
./start-services.sh
```

#### Option 2: Manual Start
Terminal 1 - Start Venom Bot service:
```bash
node venom-service.js
```

Terminal 2 - Start FastAPI application:
```bash
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. WhatsApp Setup

1. When you start the Venom service for the first time, it will generate a QR code
2. Open WhatsApp on your phone
3. Go to Settings → Linked Devices → Link a Device
4. Scan the QR code displayed in the terminal or check `venom.log` file
5. Your WhatsApp is now connected to the bot!

## 📱 How to Use

1. Send a WhatsApp message to your connected phone number with "hi" or "hello"
2. The bot will show available services
3. Select a service by typing the number
4. Choose your preferred barber
5. Select an available time slot
6. Get booking confirmation!

## 🌐 API Endpoints

- `GET /` - Health check
- `GET /api/services` - Get all services
- `GET /api/barbers` - Get all barbers
- `GET /api/slots/{barber_name}` - Get available slots
- `POST /api/initialize` - Initialize database
- `POST /webhook/venom` - Webhook for Venom Bot (internal use)

Visit `http://localhost:8000/docs` for interactive API documentation.

## 🔧 Configuration

### Venom Bot Configuration
- **Session Management**: Venom Bot automatically manages WhatsApp Web sessions
- **QR Code**: Generated automatically on first run
- **Multi-device**: Works with WhatsApp multi-device feature

### Database Configuration
- All salon data is stored in Firebase Firestore
- Sessions are managed in-memory for real-time conversations
- Bookings are persisted to the database

## 🚀 Deployment

### Railway Deployment
1. Connect your GitHub repository to Railway
2. Set environment variables in Railway dashboard
3. Deploy both Node.js service and Python app

### Render Deployment
1. Create two services: one for Node.js (Venom Bot) and one for Python (FastAPI)
2. Configure environment variables
3. Update `VENOM_SERVICE_URL` to point to your deployed Venom service

## 🆚 Why Venom Bot over Twilio?

| Feature | Venom Bot | Twilio |
|---------|-----------|---------|
| **Cost** | ✅ FREE | ❌ Paid (per message) |
| **Setup** | ✅ Easy QR scan | ❌ Complex verification |
| **Limitations** | ✅ No message limits | ❌ Daily limits on trial |
| **Features** | ✅ Full WhatsApp features | ❌ Limited sandbox |

## 🐛 Troubleshooting

### Venom Bot Issues
- **QR Code not showing**: Check `venom.log` file
- **Connection lost**: Restart the Venom service
- **Session expired**: Delete `tokens` folder and restart

### General Issues
- **Port conflicts**: Change ports in configuration
- **Firebase errors**: Check your credentials and project ID
- **Python errors**: Ensure virtual environment is activated

## 📄 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📞 Support

If you encounter any issues or need help setting up the bot, please create an issue in the repository. 