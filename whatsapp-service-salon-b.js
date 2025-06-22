const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const express = require('express');
const qrcode = require('qrcode');
const fs = require('fs');
const axios = require('axios');

// Salon B Configuration
const PORT = process.env.SALON_B_PORT || 3002;
const SALON_ID = 'salon_b';
const SALON_NAME = 'Uptown Hair Studio';
const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
const WEBHOOK_PATH = `/webhook/whatsapp/${SALON_ID}`;

const app = express();
app.use(express.json());

console.log(`🏢 Starting WhatsApp Service for ${SALON_NAME}`);
console.log(`🔗 Salon ID: ${SALON_ID}`);
console.log(`📱 Port: ${PORT}`);
console.log(`🔙 Backend URL: ${BACKEND_URL}`);
console.log(`📡 Webhook: ${WEBHOOK_PATH}`);

// Initialize WhatsApp client with LocalAuth for session persistence
const client = new Client({
    authStrategy: new LocalAuth({ clientId: `salon-b-client` }),
    puppeteer: {
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--single-process',
            '--disable-gpu'
        ],
        defaultViewport: {
            width: 1366,
            height: 768
        }
    }
});

let qrCodeData = null;
let isReady = false;
let clientInfo = null;

// QR Code event
client.on('qr', (qr) => {
    console.log(`📱 Salon B QR Code generated`);
    qrCodeData = qr;
    
    // Generate QR code image
    qrcode.toFile(`salon_b_qr.png`, qr, (err) => {
        if (err) {
            console.error('Error generating QR code image:', err);
        } else {
            console.log('✅ Salon B QR code image saved as salon_b_qr.png');
        }
    });
});

// Ready event
client.on('ready', () => {
    console.log(`✅ ${SALON_NAME} WhatsApp Client is ready!`);
    isReady = true;
    clientInfo = client.info;
    qrCodeData = null; // Clear QR code when ready
});

// Message received event - same logic as Salon A
client.on('message', async (message) => {
    console.log(`📨 [${SALON_NAME}] Received message:`, message.body);
    console.log(`📱 From phone: ${message.from}`);
    
    // Skip if message is from status broadcast or groups
    if (message.isStatus || message.from.includes('@g.us')) {
        console.log('⏭️ Skipping status/group message');
        return;
    }

    try {
        // Get contact info
        const contact = await message.getContact();
        const contactName = contact.name || contact.pushname || message._data.notifyName || 'Unknown';
        
        // Prepare message data for backend
        const messageData = {
            body: message.body,
            from: message.from,
            to: message.to,
            timestamp: message.timestamp,
            contactName: contactName,
            isGroupMsg: message.from.includes('@g.us'),
            id: message.id._serialized,
            author: message.author || message.from
        };

        // Send to backend webhook
        const backendUrl = `${BACKEND_URL}${WEBHOOK_PATH}`;
        const response = await axios.post(backendUrl, messageData, {
            headers: { 'Content-Type': 'application/json' },
            timeout: 10000
        });

        if (response.data && response.data.reply) {
            const replyText = response.data.reply;
            if (replyText && replyText.trim()) {
                const sentMessage = await client.sendMessage(message.from, replyText);
                console.log(`✅ [${SALON_NAME}] Message sent successfully: ${sentMessage.id._serialized}`);
            }
        }

    } catch (error) {
        console.error(`❌ Error processing message for ${SALON_NAME}:`, error.message);
        try {
            await client.sendMessage(message.from, "😔 Sorry, we're experiencing technical difficulties. Please try again later.");
        } catch (sendError) {
            console.error('Error sending error message:', sendError);
        }
    }
});

// API Routes - same as Salon A but with different salon info
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
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <style>
                        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f0f8ff; }
                        .container { background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                        h1 { color: #1E90FF; }
                        .salon-info { background: #e6f3ff; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="salon-info">
                            <h2>🏢 ${SALON_NAME}</h2>
                            <p>📍 Salon ID: ${SALON_ID}</p>
                        </div>
                        <h1>📱 WhatsApp QR Code</h1>
                        <div class="qr-code">
                            <img src="${url}" alt="WhatsApp QR Code" style="max-width: 300px;">
                        </div>
                        <p>⚠️ QR code expires in 45 seconds.</p>
                        <button onclick="window.location.reload()">🔄 Refresh QR Code</button>
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

// Start the server
app.listen(PORT, '0.0.0.0', () => {
    console.log(`🌍 ${SALON_NAME} WhatsApp Service running on port ${PORT}`);
    console.log(`📱 QR Code: http://localhost:${PORT}/qr`);
});

// Initialize WhatsApp client
console.log(`🚀 Starting WhatsApp client for ${SALON_NAME}...`);
client.initialize(); 