const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const express = require('express');
const qrcode = require('qrcode');
const fs = require('fs');
const axios = require('axios');
const path = require('path');

// Salon B Configuration
const PORT = process.env.SALON_B_PORT || 3006;
const SALON_ID = 'salon_b';
const SALON_NAME = 'Uptown Hair Studio';
const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
const WEBHOOK_PATH = `/webhook/whatsapp/${SALON_ID}`;

// Connection status file path
const CONNECTION_STATUS_FILE = `connection_status_${SALON_ID}.json`;

const app = express();
app.use(express.json());

console.log(`🏢 Starting WhatsApp Service for ${SALON_NAME}`);
console.log(`🔗 Salon ID: ${SALON_ID}`);
console.log(`📱 Port: ${PORT}`);
console.log(`🔙 Backend URL: ${BACKEND_URL}`);
console.log(`📡 Webhook: ${WEBHOOK_PATH}`);

// Connection status management
let connectionStatus = {
    salon_id: SALON_ID,
    salon_name: SALON_NAME,
    is_connected: false,
    phone_number: null,
    connected_at: null,
    last_seen: null,
    connection_count: 0,
    qr_generated_count: 0
};

// Load/Save/Update connection status functions (same as Salon A)
function loadConnectionStatus() {
    try {
        if (fs.existsSync(CONNECTION_STATUS_FILE)) {
            const data = fs.readFileSync(CONNECTION_STATUS_FILE, 'utf8');
            const loaded = JSON.parse(data);
            connectionStatus = { ...connectionStatus, ...loaded };
            console.log(`📋 Loaded connection status: ${connectionStatus.is_connected ? '✅ Connected' : '❌ Not Connected'}`);
            if (connectionStatus.phone_number) {
                console.log(`📱 Phone: ${connectionStatus.phone_number}`);
                console.log(`🕒 Last connected: ${connectionStatus.connected_at}`);
            }
        } else {
            console.log(`📋 No previous connection status found for ${SALON_NAME}`);
        }
    } catch (error) {
        console.error('❌ Error loading connection status:', error.message);
    }
}

function saveConnectionStatus() {
    try {
        fs.writeFileSync(CONNECTION_STATUS_FILE, JSON.stringify(connectionStatus, null, 2));
        console.log(`💾 Connection status saved for ${SALON_NAME}`);
    } catch (error) {
        console.error('❌ Error saving connection status:', error.message);
    }
}

function updateConnectionStatus(isConnected, phoneNumber = null) {
    const now = new Date().toISOString();
    connectionStatus.is_connected = isConnected;
    connectionStatus.last_seen = now;
    
    if (isConnected) {
        connectionStatus.phone_number = phoneNumber;
        connectionStatus.connected_at = now;
        connectionStatus.connection_count += 1;
        console.log(`✅ ${SALON_NAME} WhatsApp connected! Phone: ${phoneNumber}`);
    } else {
        console.log(`❌ ${SALON_NAME} WhatsApp disconnected`);
    }
    
    saveConnectionStatus();
}

// Load connection status on startup
loadConnectionStatus();

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
    connectionStatus.qr_generated_count += 1;
    saveConnectionStatus();
    
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
    
    // Update connection status with phone number from client info
    const phoneNumber = clientInfo?.wid?.user || 'Unknown';
    updateConnectionStatus(true, phoneNumber);
});

// Disconnected event
client.on('disconnected', (reason) => {
    console.log(`❌ ${SALON_NAME} WhatsApp Client disconnected:`, reason);
    isReady = false;
    clientInfo = null;
    updateConnectionStatus(false);
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

// API Routes - enhanced with connection status
app.get('/health', (req, res) => {
    res.json({
        status: isReady ? 'ready' : 'not_ready',
        salon: SALON_NAME,
        salon_id: SALON_ID,
        port: PORT,
        timestamp: new Date().toISOString(),
        connection_status: connectionStatus
    });
});

app.get('/connection-status', (req, res) => {
    res.json({
        ...connectionStatus,
        current_status: isReady ? 'connected' : 'disconnected',
        qr_needed: !isReady && !connectionStatus.is_connected
    });
});

app.post('/reset-connection', (req, res) => {
    try {
        // Reset connection status
        connectionStatus.is_connected = false;
        connectionStatus.phone_number = null;
        connectionStatus.connected_at = null;
        connectionStatus.qr_generated_count = 0;
        saveConnectionStatus();
        
        // Remove session files to force re-authentication
        const sessionPath = `.wwebjs_auth/session-salon-b-client`;
        if (fs.existsSync(sessionPath)) {
            fs.rmSync(sessionPath, { recursive: true });
            console.log(`🗑️ Removed session files for ${SALON_NAME}`);
        }
        
        res.json({
            success: true,
            message: `Connection reset for ${SALON_NAME}. Restart the service to generate new QR code.`
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

app.get('/qr', (req, res) => {
    // Check if already connected from previous sessions
    if (connectionStatus.is_connected && isReady) {
        const connectedSince = new Date(connectionStatus.connected_at);
        const timeSinceConnection = Date.now() - connectedSince.getTime();
        const hoursSinceConnection = Math.floor(timeSinceConnection / (1000 * 60 * 60));
        
        res.send(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>${SALON_NAME} - Already Connected</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #e6f3ff; }
                    .container { background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 500px; }
                    .success { color: #1E90FF; }
                    .salon-info { background: #e6f3ff; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                    .connection-info { background: #f0f8ff; padding: 15px; border-radius: 5px; margin: 20px 0; text-align: left; }
                    .reset-btn { background: #ff6b6b; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin-top: 10px; }
                    .reset-btn:hover { background: #ff5252; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="salon-info">
                        <h2>🏢 ${SALON_NAME}</h2>
                        <p>📍 Salon ID: ${SALON_ID}</p>
                    </div>
                    <h1 class="success">✅ WhatsApp Already Connected!</h1>
                    <p>This salon's WhatsApp is already connected and ready to receive messages.</p>
                    
                    <div class="connection-info">
                        <strong>📋 Connection Details:</strong><br>
                        📱 Phone: ${connectionStatus.phone_number}<br>
                        🕒 Connected: ${connectedSince.toLocaleString()}<br>
                        ⏰ Online for: ${hoursSinceConnection} hours<br>
                        🔢 Total connections: ${connectionStatus.connection_count}
                    </div>
                    
                    <p>✨ <strong>Your bot is ready!</strong> Customers can now send messages to your WhatsApp number.</p>
                    
                    <div style="margin-top: 30px; padding: 15px; background: #fff3cd; border-radius: 5px;">
                        <strong>🔄 Need to reconnect?</strong><br>
                        <p>Only use this if you're having connection issues:</p>
                        <button class="reset-btn" onclick="resetConnection()">🔄 Reset Connection</button>
                    </div>
                </div>
                
                <script>
                    async function resetConnection() {
                        if (confirm('Are you sure you want to reset the connection? This will require scanning the QR code again.')) {
                            try {
                                const response = await fetch('/reset-connection', { method: 'POST' });
                                const result = await response.json();
                                alert(result.message);
                                if (result.success) {
                                    window.location.reload();
                                }
                            } catch (error) {
                                alert('Error resetting connection: ' + error.message);
                            }
                        }
                    }
                </script>
            </body>
            </html>
        `);
    } else if (qrCodeData) {
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
                        .qr-count { color: #888; font-size: 0.9em; margin-top: 10px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="salon-info">
                            <h2>🏢 ${SALON_NAME}</h2>
                            <p>📍 Salon ID: ${SALON_ID}</p>
                            <div class="qr-count">QR Code #${connectionStatus.qr_generated_count}</div>
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
        res.send(`
            <h1>⏳ ${SALON_NAME} Initializing...</h1>
            <p>Previous connections: ${connectionStatus.connection_count}</p>
            <button onclick="window.location.reload()">🔄 Refresh</button>
        `);
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