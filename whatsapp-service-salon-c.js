const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const express = require('express');
const qrcode = require('qrcode');

// Salon C Configuration
const PORT = process.env.SALON_C_PORT || 3007;
const SALON_ID = 'salon_c';
const SALON_NAME = 'Luxury Spa & Salon';
const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
const WEBHOOK_PATH = `/webhook/whatsapp/${SALON_ID}`;

const app = express();
app.use(express.json());

// Initialize WhatsApp client
const client = new Client({
    authStrategy: new LocalAuth({ clientId: `salon-c-client` }),
    puppeteer: { headless: true, args: ['--no-sandbox', '--disable-setuid-sandbox'] }
});

let qrCodeData = null;
let isReady = false;

client.on('qr', (qr) => {
    console.log(`📱 Salon C QR Code generated`);
    qrCodeData = qr;
});

client.on('ready', () => {
    console.log(`✅ ${SALON_NAME} WhatsApp Client is ready!`);
    isReady = true;
    qrCodeData = null;
});

client.on('message', async (message) => {
    if (message.isStatus || message.from.includes('@g.us')) return;

    try {
        const contact = await message.getContact();
        const contactName = contact.name || contact.pushname || 'Unknown';
        
        const messageData = {
            body: message.body,
            from: message.from,
            to: message.to,
            timestamp: message.timestamp,
            contactName: contactName,
            isGroupMsg: false,
            id: message.id._serialized,
            author: message.from
        };

        const axios = require('axios');
        const response = await axios.post(`${BACKEND_URL}${WEBHOOK_PATH}`, messageData, {
            headers: { 'Content-Type': 'application/json' },
            timeout: 10000
        });

        if (response.data && response.data.reply && response.data.reply.trim()) {
            await client.sendMessage(message.from, response.data.reply);
            console.log(`✅ [${SALON_NAME}] Reply sent successfully`);
        }

    } catch (error) {
        console.error(`❌ Error processing message for ${SALON_NAME}:`, error.message);
        try {
            await client.sendMessage(message.from, "😔 We're experiencing technical difficulties. Please try again later.");
        } catch (sendError) {
            console.error('Error sending error message:', sendError);
        }
    }
});

app.get('/health', (req, res) => {
    res.json({
        status: isReady ? 'ready' : 'not_ready',
        salon: SALON_NAME,
        salon_id: SALON_ID,
        port: PORT,
        timestamp: new Date().toISOString()
    });
});

app.get('/qr', (req, res) => {
    if (qrCodeData) {
        qrcode.toDataURL(qrCodeData, (err, url) => {
            if (err) {
                res.status(500).send('Error generating QR code');
                return;
            }
            
            const html = `
                <!DOCTYPE html>
                <html>
                <head>
                    <title>${SALON_NAME} - WhatsApp QR Code</title>
                    <style>
                        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f8f4ff; }
                        .container { background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                        h1 { color: #9370DB; }
                        .salon-info { background: #f0e6ff; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="salon-info">
                            <h2>🏢 ${SALON_NAME}</h2>
                            <p>📍 Salon ID: ${SALON_ID}</p>
                        </div>
                        <h1>📱 WhatsApp QR Code</h1>
                        <img src="${url}" alt="WhatsApp QR Code" style="max-width: 300px;">
                        <p>⚠️ QR code expires in 45 seconds.</p>
                        <button onclick="window.location.reload()">🔄 Refresh</button>
                    </div>
                </body>
                </html>
            `;
            res.send(html);
        });
    } else if (isReady) {
        res.send(`<h1>✅ ${SALON_NAME} WhatsApp Connected!</h1>`);
    } else {
        res.send(`<h1>⏳ ${SALON_NAME} Initializing...</h1>`);
    }
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`🌍 ${SALON_NAME} WhatsApp Service running on port ${PORT}`);
    console.log(`📱 QR Code: http://localhost:${PORT}/qr`);
});

console.log(`🚀 Starting WhatsApp client for ${SALON_NAME}...`);
client.initialize(); 