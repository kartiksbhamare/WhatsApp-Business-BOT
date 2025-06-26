# 🎯 Smart WhatsApp Booking Bot - Single Salon Edition

A complete WhatsApp-based appointment booking system for a single salon using FastAPI, Firebase, and WhatsApp Web.js.

## 🌟 Features

- **📱 WhatsApp Integration**: Real WhatsApp Web.js integration for authentic messaging
- **🔥 Firebase Database**: Cloud-based data storage with real-time sync
- **🎯 Single Salon Focus**: Streamlined for one salon operation
- **📅 Smart Scheduling**: Automatic availability checking and booking
- **🚀 Easy Deployment**: Ready for Railway, Docker, or local development
- **🔧 Environment Configurable**: No hardcoded URLs - works anywhere

## 🚀 Quick Start

### 1. **Environment Setup**
```bash
# Interactive setup (recommended)
./setup_env.sh

# Or copy template manually
cp env.template .env
# Edit .env with your settings
```

### 2. **Start the Bot**
```bash
# Complete setup and start
./start_bot.sh

# Or run simple version
./run_simple.sh
```

### 3. **Connect WhatsApp**
1. Open `http://localhost:3000/qr` in your browser
2. Scan the QR code with WhatsApp
3. Send "hi" to test the bot

## 📋 System Architecture

```
Customer WhatsApp → WhatsApp Web.js → FastAPI Backend → Firebase Database
                                   ↓
                              Booking Confirmation
```

## 🛠️ Installation

### Prerequisites
- **Node.js 18+**
- **Python 3.9+**
- **Google Chrome** (for WhatsApp Web.js)
- **Firebase Project** with Firestore

### Local Development
```bash
# 1. Clone repository
git clone https://github.com/kartiksbhamare/WhatsApp-Business-BOT.git
cd WhatsApp-Business-BOT

# 2. Install dependencies
npm install
pip install -r requirements.txt

# 3. Setup environment
./setup_env.sh

# 4. Add Firebase credentials
# Place your firebase-key.json in the root directory

# 5. Start the bot
./start_bot.sh
```

## 🌍 Deployment Options

### 🚂 Railway (Recommended)
```bash
# 1. Connect GitHub repo to Railway
# 2. Set environment variables:
BACKEND_URL=https://your-app.railway.app
WHATSAPP_SERVICE_URL=https://your-app.railway.app
RAILWAY_ENVIRONMENT=true
FIREBASE_CREDENTIALS_BASE64=<your_base64_credentials>

# 3. Deploy!
```

### 🐳 Docker
```bash
# Using Docker Compose
docker-compose up

# Or build manually
docker build -t whatsapp-bot .
docker run -p 3000:3000 -p 8000:8000 whatsapp-bot
```

## 📱 How It Works

### Customer Experience
1. **Scan QR Code** → Opens WhatsApp chat
2. **Send "hi"** → Bot shows available services
3. **Select Service** → Choose from salon services
4. **Choose Barber** → Pick preferred stylist
5. **Select Date** → Today or tomorrow
6. **Pick Time** → Available time slots
7. **Confirmation** → Booking confirmed!

### Example Conversation
```
Customer: hi
Bot: 👋 Welcome to Beauty Salon! ✨

Here are our services:
1. Hair Cut ($35, ⏱️30 mins)
2. Hair Color ($85, ⏱️120 mins)
3. Manicure ($25, ⏱️45 mins)

📝 Please enter the number of the service you'd like to book.

Customer: 1
Bot: ✅ You've selected Hair Cut!

👨‍💼 Please choose your preferred stylist:
1. ✂️ Maya Rodriguez
2. ✂️ Alex Chen

Customer: 1
Bot: 🎉 Great! You've selected ✂️ Maya Rodriguez.

📅 Please choose your preferred date:
1. 📅 Today (Wednesday, June 26)
2. 🌅 Tomorrow (Thursday, June 27)

Customer: 2
Bot: ✅ Perfect! Available times for 🌅 Thursday, June 27:
1. ⏰ 09:00 AM
2. ⏰ 10:30 AM
3. ⏰ 02:00 PM

Customer: 2
Bot: 🎉✨ Booking Confirmed! ✨🎉

📋 Your Appointment Details:
💄 Service: Hair Cut
✂️ Barber: Maya Rodriguez
📅 Date: Thursday, June 27, 2025
⏰ Time: 10:30 AM

🤗 We look forward to seeing you at Beauty Salon! Thank you for choosing us! 💖
```

## 🔧 Configuration

### Environment Variables
```env
# Service URLs
BACKEND_URL=http://localhost:8000
WHATSAPP_SERVICE_URL=http://localhost:3000
SALON_NAME=Beauty Salon

# Firebase
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_CREDENTIALS_PATH=firebase-key.json
# For Railway:
FIREBASE_CREDENTIALS_BASE64=your_base64_credentials

# Deployment
RAILWAY_ENVIRONMENT=true  # Auto-detected
DOCKER_ENV=true          # Auto-detected
```

### Firebase Setup
1. Create a Firebase project
2. Enable Firestore Database
3. Create a service account key
4. Download `firebase-key.json`
5. Place in project root

## 📊 API Endpoints

- **`GET /`** - Service status and info
- **`GET /health`** - Health check with Firebase status
- **`GET /qr`** - WhatsApp QR code page
- **`POST /webhook/whatsapp`** - WhatsApp message webhook
- **`GET /firebase-status`** - Firebase connection details
- **`GET /bookings`** - All bookings (debug)

Visit `http://localhost:8000/docs` for interactive API documentation.

## 🔍 Troubleshooting

### Common Issues

**QR Code Not Showing**
- Check if Chrome is installed
- Verify WhatsApp service is running
- Check browser console for errors

**Messages Not Working**
- Ensure Firebase is connected
- Check webhook configuration
- Verify WhatsApp Web session is active

**Firebase Connection Failed**
- Verify `firebase-key.json` exists
- Check Firebase project ID
- Ensure Firestore is enabled

### Debug Commands
```bash
# Check service health
curl http://localhost:8000/health

# Test Firebase connection
curl http://localhost:8000/firebase-status

# View logs
tail -f app.log
```

## 🔄 Migration from Multi-Salon

If upgrading from the old multi-salon version:

1. **Backup your data**
2. **Run the new single salon version**
3. **Update environment variables**
4. **Test the booking flow**

The system automatically migrates to single salon mode.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

- **GitHub Issues**: Report bugs and request features
- **Documentation**: Check the guides in `/docs`
- **Discord**: Join our community (link in repo)

---

**🎉 Built with ❤️ for salon owners who want to modernize their booking system!** 