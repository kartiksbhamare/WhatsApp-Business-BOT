const { Client, LocalAuth } = require('whatsapp-web.js');
const express = require('express');
const qrcode = require('qrcode');
const fs = require('fs');
const axios = require('axios');
const path = require('path');

// Simplified configuration for Railway
const app = express();
const PORT = process.env.PORT || 3000;
const BACKEND_URL = process.env.BACKEND_URL || `http://localhost:${PORT}`;

let client;
let qrCodeData = null;
let isReady = false;
let clientInfo = null;

// Connection status tracking
let connectionStatus = {
    is_connected: false,
    phone_number: null,
    connected_at: null,
    last_seen: null,
    connection_count: 0,
    qr_generated_count: 0
};

// Railway-optimized Puppeteer configuration
const puppeteerConfig = {
    headless: true,
    args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--no-first-run',
        '--no-zygote',
        '--single-process',
        '--disable-gpu',
        '--disable-web-security',
        '--disable-features=VizDisplayCompositor',
        '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding',
        '--disable-extensions',
        '--disable-plugins',
        '--disable-default-apps',
        '--disable-hang-monitor',
        '--disable-prompt-on-repost',
        '--disable-sync',
        '--disable-translate',
        '--disable-ipc-flooding-protection',
        '--memory-pressure-off',
        '--max_old_space_size=2048',
        '--disable-default-apps',
        '--disable-extensions',
        '--disable-plugins',
        '--disable-translate',
        '--disable-sync',
        '--disable-background-networking',
        '--disable-background-timer-throttling',
        '--disable-client-side-phishing-detection',
        '--disable-default-apps',
        '--disable-dev-shm-usage',
        '--disable-extensions',
        '--disable-features=TranslateUI',
        '--disable-hang-monitor',
        '--disable-ipc-flooding-protection',
        '--disable-popup-blocking',
        '--disable-prompt-on-repost',
        '--disable-renderer-backgrounding',
        '--disable-sync',
        '--disable-translate',
        '--metrics-recording-only',
        '--no-first-run',
        '--safebrowsing-disable-auto-update',
        '--enable-automation',
        '--password-store=basic',
        '--use-mock-keychain'
    ],
    executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || '/usr/bin/google-chrome-stable'
};

console.log('🚀 Starting Railway-Optimized WhatsApp Service');

// Initialize WhatsApp client with Railway-specific settings
function initializeWhatsApp() {
    try {
        console.log('🔧 Initializing WhatsApp client for Railway...');
        
        client = new Client({
            authStrategy: new LocalAuth({ clientId: 'railway-client' }),
            puppeteer: puppeteerConfig
        });

        // QR Code event
        client.on('qr', (qr) => {
            console.log('📱 QR Code generated for Railway deployment');
            qrCodeData = qr;
            connectionStatus.qr_generated_count += 1;
            
            // Generate QR code image
            qrcode.toFile('railway_qr.png', qr, (err) => {
                if (err) {
                    console.error('❌ Error generating QR code image:', err);
                } else {
                    console.log('✅ QR code image saved as railway_qr.png');
                }
            });
        });

        // Ready event
        client.on('ready', () => {
            console.log('✅ WhatsApp Client is ready on Railway!');
            isReady = true;
            clientInfo = client.info;
            qrCodeData = null;
            
            const phoneNumber = clientInfo?.wid?.user || 'Unknown';
            connectionStatus.is_connected = true;
            connectionStatus.phone_number = phoneNumber;
            connectionStatus.connected_at = new Date().toISOString();
            connectionStatus.connection_count += 1;
            
            console.log(`📱 Connected with phone: ${phoneNumber}`);
        });

        // Disconnected event
        client.on('disconnected', (reason) => {
            console.log('❌ WhatsApp Client disconnected:', reason);
            isReady = false;
            clientInfo = null;
            connectionStatus.is_connected = false;
            connectionStatus.last_seen = new Date().toISOString();
        });

        // Authentication failure
        client.on('auth_failure', (msg) => {
            console.error('❌ Authentication failure:', msg);
            isReady = false;
            connectionStatus.is_connected = false;
        });

        // Message received event
        client.on('message', async (message) => {
            console.log('📨 Received message:', message.body);
            console.log('📱 From phone:', message.from);
            
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
                
                console.log('📋 Message details:', JSON.stringify(messageData, null, 2));
                
                // Send to backend webhook (default to salon_a for Railway)
                const webhookPath = '/webhook/whatsapp/salon_a';
                const backendUrl = `${BACKEND_URL}${webhookPath}`;
                console.log('🔗 Backend URL:', backendUrl);
                
                const response = await axios.post(backendUrl, messageData, {
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    timeout: 10000
                });
                
                console.log('📊 Backend response status:', response.status);
                
                if (response.data && response.data.reply) {
                    console.log('✅ Message forwarded to backend successfully');
                    
                    // Send reply if provided
                    const replyText = response.data.reply;
                    if (replyText && replyText.trim()) {
                        console.log('📤 Sending reply to', message.from, ':', replyText);
                        
                        const sentMessage = await client.sendMessage(message.from, replyText);
                        console.log('✅ Message sent successfully:', sentMessage.id._serialized);
                    } else {
                        console.log('ℹ️ No reply text provided by backend');
                    }
                } else {
                    console.log('ℹ️ No reply needed from backend');
                }
                
            } catch (error) {
                console.error('❌ Error processing message:', error.message);
                
                // Send error message to user
                try {
                    await client.sendMessage(message.from, "😔 Sorry, we're experiencing technical difficulties. Please try again later or contact us directly.");
                } catch (sendError) {
                    console.error('❌ Error sending error message:', sendError);
                }
            }
        });

        // Initialize the client
        console.log('🔄 Starting WhatsApp client initialization...');
        client.initialize();
        
    } catch (error) {
        console.error('❌ Error initializing WhatsApp client:', error.message);
        
        // Retry after 30 seconds
        setTimeout(() => {
            console.log('🔄 Retrying WhatsApp initialization...');
            initializeWhatsApp();
        }, 30000);
    }
}

// Express middleware
app.use(express.json());

// Health check
app.get('/health', (req, res) => {
    res.json({
        status: isReady ? 'ready' : 'not_ready',
        service: 'Railway WhatsApp Service',
        timestamp: new Date().toISOString(),
        client_info: clientInfo,
        connection_status: connectionStatus
    });
});

// Service info
app.get('/info', (req, res) => {
    res.json({
        service: 'Railway WhatsApp Service',
        status: isReady ? 'ready' : 'initializing',
        qr_available: !!qrCodeData,
        backend_url: BACKEND_URL,
        connection_status: connectionStatus
    });
});

// QR code page
app.get('/qr', (req, res) => {
    if (connectionStatus.is_connected && isReady) {
        const connectedSince = new Date(connectionStatus.connected_at);
        const timeSinceConnection = Date.now() - connectedSince.getTime();
        const hoursSinceConnection = Math.floor(timeSinceConnection / (1000 * 60 * 60));
        
        res.send(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Multi-Salon WhatsApp - Connected</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #e8f5e8; }
                    .container { background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 500px; }
                    .success { color: #25D366; }
                    .connection-info { background: #f0f8ff; padding: 15px; border-radius: 5px; margin: 20px 0; text-align: left; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1 class="success">✅ Multi-Salon WhatsApp Connected!</h1>
                    <p>Your WhatsApp booking system is active and ready!</p>
                    
                    <div class="connection-info">
                        <strong>📋 Connection Details:</strong><br>
                        📱 Phone: ${connectionStatus.phone_number}<br>
                        🕒 Connected: ${connectedSince.toLocaleString()}<br>
                        ⏰ Online for: ${hoursSinceConnection} hours<br>
                        🔢 Total connections: ${connectionStatus.connection_count}
                    </div>
                    
                    <p>✨ <strong>All salons are ready!</strong> Customers can now send messages to start booking.</p>
                </div>
            </body>
            </html>
        `);
        return;
    }
    
    if (qrCodeData) {
        res.send(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Multi-Salon WhatsApp QR Code</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 20px; background: #f0f8ff; }
                    .container { background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 500px; }
                    .qr-container { margin: 20px 0; }
                    .instructions { background: #fff3cd; padding: 15px; border-radius: 5px; margin-top: 20px; text-align: left; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>📱 Multi-Salon WhatsApp QR Code</h1>
                    <p>Scan this QR code to connect all salons to WhatsApp</p>
                    
                    <div class="qr-container">
                        <div id="qr-code"></div>
                    </div>
                    
                    <div class="instructions">
                        <h3>📋 How to Connect:</h3>
                        <ol>
                            <li>🔍 Open WhatsApp on your phone</li>
                            <li>⚙️ Go to Settings → Linked Devices</li>
                            <li>➕ Tap "Link a Device"</li>
                            <li>📷 Scan the QR code above</li>
                            <li>✅ Wait for connection confirmation</li>
                        </ol>
                    </div>
                    
                    <p style="margin-top: 20px; color: #666; font-size: 14px;">
                        🔄 This page will auto-refresh every 30 seconds
                    </p>
                </div>
                
                <script src="https://cdn.jsdelivr.net/npm/qrcode@1.5.3/build/qrcode.min.js"></script>
                <script>
                    // Generate QR code
                    const qrData = \`${qrCodeData}\`;
                    QRCode.toCanvas(document.getElementById('qr-code'), qrData, {
                        width: 300,
                        height: 300,
                        margin: 2,
                        color: {
                            dark: '#000000',
                            light: '#FFFFFF'
                        }
                    }, function (error) {
                        if (error) {
                            console.error('Error generating QR code:', error);
                            document.getElementById('qr-code').innerHTML = '<p>Error generating QR code</p>';
                        }
                    });
                    
                    // Auto-refresh every 30 seconds
                    setTimeout(() => {
                        window.location.reload();
                    }, 30000);
                </script>
            </body>
            </html>
        `);
    } else {
        res.send(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Multi-Salon WhatsApp - Initializing</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f0f8ff; }
                    .container { background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                    .loading { color: #007bff; }
                    .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #007bff; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin: 20px auto; }
                    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1 class="loading">🔄 Initializing Multi-Salon WhatsApp...</h1>
                    <div class="spinner"></div>
                    <p>Please wait while we generate your QR code...</p>
                    <p>This page will automatically refresh when ready.</p>
                </div>
                
                <script>
                    // Auto-refresh every 10 seconds until QR code is ready
                    setTimeout(() => {
                        window.location.reload();
                    }, 10000);
                </script>
            </body>
            </html>
        `);
    }
});

// QR code image endpoint
app.get('/qr-image', (req, res) => {
    const qrImagePath = 'railway_qr.png';
    if (fs.existsSync(qrImagePath)) {
        res.sendFile(path.resolve(qrImagePath));
    } else {
        res.status(404).json({ error: 'QR code image not found' });
    }
});

// Start the server
app.listen(PORT, () => {
    console.log(`🚀 Railway WhatsApp service running on port ${PORT}`);
    console.log(`🔗 QR Code URL: http://localhost:${PORT}/qr`);
    
    // Initialize WhatsApp after server starts
    setTimeout(() => {
        initializeWhatsApp();
    }, 2000);
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('\n🛑 Shutting down Railway WhatsApp service...');
    
    if (client) {
        try {
            await client.destroy();
            console.log('✅ WhatsApp client shutdown complete');
        } catch (error) {
            console.error('❌ Error during shutdown:', error.message);
        }
    }
    
    console.log('👋 Service shut down. Goodbye!');
    process.exit(0);
}); 