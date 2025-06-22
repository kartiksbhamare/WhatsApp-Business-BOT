const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const express = require('express');
const qrcode = require('qrcode');
const fs = require('fs');
const axios = require('axios');

// Salon A Configuration
const PORT = process.env.SALON_A_PORT || 3005;
const SALON_ID = 'salon_a';
const SALON_NAME = 'Downtown Beauty Salon';
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
    authStrategy: new LocalAuth({ clientId: `salon-a-client` }),
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
    console.log(`📱 Salon A QR Code generated`);
    qrCodeData = qr;
    
    // Generate QR code image
    qrcode.toFile(`salon_a_qr.png`, qr, (err) => {
        if (err) {
            console.error('Error generating QR code image:', err);
        } else {
            console.log('✅ Salon A QR code image saved as salon_a_qr.png');
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

// Disconnected event
client.on('disconnected', (reason) => {
    console.log(`❌ ${SALON_NAME} WhatsApp Client disconnected:`, reason);
    isReady = false;
    clientInfo = null;
});

// Message received event
client.on('message', async (message) => {
    console.log(`📨 [${SALON_NAME}] Received message:`, message.body);
    console.log(`📱 From phone: ${message.from}`);
    console.log(`👤 Contact name: ${message._data.notifyName || 'Unknown'}`);
    
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

        console.log(`📋 [${SALON_NAME}] Message details:`, JSON.stringify(messageData, null, 2));

        // Send to backend webhook
        const backendUrl = `${BACKEND_URL}${WEBHOOK_PATH}`;
        console.log(`🔗 Backend URL: ${backendUrl}`);
        
        const response = await axios.post(backendUrl, messageData, {
            headers: {
                'Content-Type': 'application/json'
            },
            timeout: 10000
        });

        console.log(`📊 Backend response status: ${response.status}`);
        
        if (response.data && response.data.reply) {
            console.log(`✅ Message forwarded to backend successfully:`, JSON.stringify(response.data, null, 2));
            
            // Send reply if provided
            const replyText = response.data.reply;
            if (replyText && replyText.trim()) {
                console.log(`📤 Sending reply to ${message.from}: ${replyText}`);
                console.log(`📤 Sending message to: ${message.from}`);
                console.log(`📝 Message content: ${replyText}`);
                
                const sentMessage = await client.sendMessage(message.from, replyText);
                console.log(`✅ Message sent successfully: ${sentMessage.id._serialized}`);
            } else {
                console.log('ℹ️ No reply text provided by backend');
            }
        } else {
            console.log('ℹ️ No reply needed from backend');
        }

    } catch (error) {
        console.error(`❌ Error processing message for ${SALON_NAME}:`, error.message);
        
        // Send error message to user
        try {
            await client.sendMessage(message.from, "😔 Sorry, we're experiencing technical difficulties. Please try again later or contact us directly.");
        } catch (sendError) {
            console.error('Error sending error message:', sendError);
        }
    }
});

// API Routes
app.get('/health', (req, res) => {
    res.json({
        status: isReady ? 'ready' : 'not_ready',
        salon: SALON_NAME,
        salon_id: SALON_ID,
        port: PORT,
        timestamp: new Date().toISOString(),
        client_info: clientInfo
    });
});

app.get('/info', (req, res) => {
    res.json({
        service: `${SALON_NAME} WhatsApp Service`,
        salon_id: SALON_ID,
        port: PORT,
        status: isReady ? 'ready' : 'initializing',
        qr_available: !!qrCodeData,
        backend_url: BACKEND_URL,
        webhook_path: WEBHOOK_PATH
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
                        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f5f5f5; }
                        .container { background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                        h1 { color: #25D366; }
                        .qr-code { margin: 20px 0; }
                        .instructions { margin-top: 20px; color: #666; }
                        .salon-info { background: #e8f5e8; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
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
                        <div class="instructions">
                            <p><strong>📋 Instructions:</strong></p>
                            <p>1. Open WhatsApp on your phone</p>
                            <p>2. Go to Settings → Linked Devices</p>
                            <p>3. Tap "Link a Device"</p>
                            <p>4. Scan this QR code</p>
                            <br>
                            <p>⚠️ <strong>Important:</strong> QR code expires in 45 seconds.</p>
                            <button onclick="window.location.reload()">🔄 Refresh QR Code</button>
                        </div>
                    </div>
                    <script>
                        // Auto-refresh every 45 seconds
                        setTimeout(() => {
                            window.location.reload();
                        }, 45000);
                    </script>
                </body>
                </html>
            `;
            res.send(html);
        });
    } else if (isReady) {
        res.send(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>${SALON_NAME} - WhatsApp Connected</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f5f5f5; }
                    .container { background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                    .success { color: #25D366; }
                    .salon-info { background: #e8f5e8; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="salon-info">
                        <h2>🏢 ${SALON_NAME}</h2>
                        <p>📍 Salon ID: ${SALON_ID}</p>
                    </div>
                    <h1 class="success">✅ WhatsApp Connected!</h1>
                    <p>The WhatsApp service is running and connected.</p>
                    <p>You can now receive messages for ${SALON_NAME}.</p>
                </div>
            </body>
            </html>
        `);
    } else {
        res.send(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>${SALON_NAME} - Initializing</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f5f5f5; }
                    .container { background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                    .salon-info { background: #e8f5e8; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="salon-info">
                        <h2>🏢 ${SALON_NAME}</h2>
                        <p>📍 Salon ID: ${SALON_ID}</p>
                    </div>
                    <h1>⏳ Initializing WhatsApp Service...</h1>
                    <p>Please wait while we set up the connection.</p>
                    <button onclick="window.location.reload()">🔄 Refresh</button>
                </div>
                <script>
                    setTimeout(() => window.location.reload(), 5000);
                </script>
            </body>
            </html>
        `);
    }
});

// Send message endpoint
app.post('/send-message', async (req, res) => {
    try {
        const { phone, message } = req.body;
        
        if (!isReady) {
            return res.status(503).json({ error: 'WhatsApp client not ready' });
        }
        
        if (!phone || !message) {
            return res.status(400).json({ error: 'Phone and message are required' });
        }
        
        // Format phone number
        const formattedPhone = phone.includes('@c.us') ? phone : `${phone}@c.us`;
        
        const sentMessage = await client.sendMessage(formattedPhone, message);
        
        res.json({
            success: true,
            messageId: sentMessage.id._serialized,
            salon: SALON_NAME
        });
        
    } catch (error) {
        console.error(`Error sending message for ${SALON_NAME}:`, error);
        res.status(500).json({ error: error.message });
    }
});

// Start the server
app.listen(PORT, '0.0.0.0', () => {
    console.log(`🌍 ${SALON_NAME} WhatsApp Service running on port ${PORT}`);
    console.log(`🔗 Port: ${PORT}`);
    console.log(`📋 Health check: http://localhost:${PORT}/health`);
    console.log(`📤 Send message: POST http://localhost:${PORT}/send-message`);
    console.log(`ℹ️  Get info: http://localhost:${PORT}/info`);
    console.log(`📊 Status: http://localhost:${PORT}/status`);
    console.log(`📱 QR Code: http://localhost:${PORT}/qr`);
});

// Initialize WhatsApp client
console.log(`🚀 Starting WhatsApp client for ${SALON_NAME}...`);
client.initialize(); 