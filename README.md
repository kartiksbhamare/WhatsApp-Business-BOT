# WhatsApp Business BOT

A smart WhatsApp booking system for salons built with FastAPI, Firebase, and Twilio.

## Features

- WhatsApp-based interaction
- Service booking system
- Barber selection
- Time slot management
- Firebase database integration
- Twilio WhatsApp messaging

## Tech Stack

- FastAPI
- Firebase (Firestore)
- Twilio
- Python 3.11+

## Setup

1. Clone the repository:
```bash
git clone https://github.com/kartiksbhamare/WhatsApp-Business-BOT.git
cd WhatsApp-Business-BOT
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables in `.env`:
```env
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=your_whatsapp_number
FIREBASE_CREDENTIALS=your_firebase_credentials_json
```

5. Run the server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

## Project Structure

```
app/
├── __init__.py
├── main.py              # FastAPI application
├── config.py           # Configuration management
├── config_check.py    # Configuration validation
└── services/
    └── firestore.py   # Firebase database operations
```

## Usage

1. Send a WhatsApp message to your Twilio number
2. Follow the interactive prompts to:
   - Select a service
   - Choose a barber
   - Pick an available time slot
3. Receive booking confirmation

## Development

- Uses FastAPI for the web server
- Firestore for database operations
- Twilio for WhatsApp communication
- Supports both TwiML and direct message responses

## License

MIT License 