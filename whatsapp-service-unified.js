const { Client, LocalAuth } = require('whatsapp-web.js');
const express = require('express');
const qrcode = require('qrcode');
const fs = require('fs');
const axios = require('axios');
const path = require('path');

// Multi-salon configuration
const SALONS = {
    salon_a: {
        id: 'salon_a',
        name: 'Downtown Beauty Salon',
        port: 3005,
        clientId: 'salon-a-client'
    },
    salon_b: {
        id: 'salon_b', 
        name: 'Uptown Hair Studio',
        port: 3006,
        clientId: 'salon-b-client'
    },
    salon_c: {
        id: 'salon_c',
        name: 'Luxury Spa & Salon',
        port: 3007,
        clientId: 'salon-c-client'
    }
};

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';

// Global storage for salon data
const salonData = {};

// Initialize salon data
Object.keys(SALONS).forEach(salonId => {
    const salon = SALONS[salonId];
    salonData[salonId] = {
        ...salon,
        app: express(),
        client: null,
        qrCodeData: null,
        isReady: false,
        clientInfo: null,
        connectionStatus: {
            salon_id: salonId,
            salon_name: salon.name,
            is_connected: false,
            phone_number: null,
            connected_at: null,
            last_seen: null,
            connection_count: 0,
            qr_generated_count: 0
        }
    };
});

// Connection status management functions
function getConnectionStatusFile(salonId) {
    return `connection_status_${salonId}.json`;
}

function loadConnectionStatus(salonId) {
    const salon = salonData[salonId];
    const statusFile = getConnectionStatusFile(salonId);
    
    try {
        if (fs.existsSync(statusFile)) {
            const data = fs.readFileSync(statusFile, 'utf8');
            const loaded = JSON.parse(data);
            salon.connectionStatus = { ...salon.connectionStatus, ...loaded };
            console.log(`📋 [${salon.name}] Loaded connection status: ${salon.connectionStatus.is_connected ? '✅ Connected' : '❌ Not Connected'}`);
            if (salon.connectionStatus.phone_number) {
                console.log(`📱 [${salon.name}] Phone: ${salon.connectionStatus.phone_number}`);
            }
        } else {
            console.log(`📋 [${salon.name}] No previous connection status found`);
        }
    } catch (error) {
        console.error(`❌ [${salon.name}] Error loading connection status:`, error.message);
    }
}

function saveConnectionStatus(salonId) {
    const salon = salonData[salonId];
    const statusFile = getConnectionStatusFile(salonId);
    
    try {
        fs.writeFileSync(statusFile, JSON.stringify(salon.connectionStatus, null, 2));
        console.log(`💾 [${salon.name}] Connection status saved`);
    } catch (error) {
        console.error(`❌ [${salon.name}] Error saving connection status:`, error.message);
    }
}

function updateConnectionStatus(salonId, isConnected, phoneNumber = null) {
    const salon = salonData[salonId];
    const now = new Date().toISOString();
    
    salon.connectionStatus.is_connected = isConnected;
    salon.connectionStatus.last_seen = now;
    
    if (isConnected) {
        salon.connectionStatus.phone_number = phoneNumber;
        salon.connectionStatus.connected_at = now;
        salon.connectionStatus.connection_count += 1;
        console.log(`✅ [${salon.name}] WhatsApp connected! Phone: ${phoneNumber}`);
    } else {
        console.log(`❌ [${salon.name}] WhatsApp disconnected`);
    }
    
    saveConnectionStatus(salonId);
}

// Initialize WhatsApp clients and Express apps for each salon
function initializeSalon(salonId) {
    const salon = salonData[salonId];
    
    console.log(`🏢 Initializing ${salon.name}`);
    console.log(`🔗 Salon ID: ${salonId}`);
    console.log(`📱 Port: ${salon.port}`);
    
    // Load connection status
    loadConnectionStatus(salonId);
    
    // Initialize WhatsApp client
    salon.client = new Client({
        authStrategy: new LocalAuth({ clientId: salon.clientId }),
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
    
    // QR Code event
    salon.client.on('qr', (qr) => {
        console.log(`📱 [${salon.name}] QR Code generated`);
        salon.qrCodeData = qr;
        salon.connectionStatus.qr_generated_count += 1;
        saveConnectionStatus(salonId);
        
        // Generate QR code image
        qrcode.toFile(`${salonId}_qr.png`, qr, (err) => {
            if (err) {
                console.error(`❌ [${salon.name}] Error generating QR code image:`, err);
            } else {
                console.log(`✅ [${salon.name}] QR code image saved as ${salonId}_qr.png`);
            }
        });
    });
    
    // Ready event
    salon.client.on('ready', () => {
        console.log(`✅ [${salon.name}] WhatsApp Client is ready!`);
        salon.isReady = true;
        salon.clientInfo = salon.client.info;
        salon.qrCodeData = null;
        
        const phoneNumber = salon.clientInfo?.wid?.user || 'Unknown';
        updateConnectionStatus(salonId, true, phoneNumber);
    });
    
    // Disconnected event
    salon.client.on('disconnected', (reason) => {
        console.log(`❌ [${salon.name}] WhatsApp Client disconnected:`, reason);
        salon.isReady = false;
        salon.clientInfo = null;
        updateConnectionStatus(salonId, false);
    });
    
    // Message received event
    salon.client.on('message', async (message) => {
        console.log(`📨 [${salon.name}] Received message:`, message.body);
        console.log(`📱 From phone: ${message.from}`);
        
        // Skip if message is from status broadcast or groups
        if (message.isStatus || message.from.includes('@g.us')) {
            console.log(`⏭️ [${salon.name}] Skipping status/group message`);
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
            
            console.log(`📋 [${salon.name}] Message details:`, JSON.stringify(messageData, null, 2));
            
            // Send to backend webhook
            const webhookPath = `/webhook/whatsapp/${salonId}`;
            const backendUrl = `${BACKEND_URL}${webhookPath}`;
            console.log(`🔗 [${salon.name}] Backend URL: ${backendUrl}`);
            
            const response = await axios.post(backendUrl, messageData, {
                headers: {
                    'Content-Type': 'application/json'
                },
                timeout: 10000
            });
            
            console.log(`📊 [${salon.name}] Backend response status: ${response.status}`);
            
            if (response.data && response.data.reply) {
                console.log(`✅ [${salon.name}] Message forwarded to backend successfully`);
                
                // Send reply if provided
                const replyText = response.data.reply;
                if (replyText && replyText.trim()) {
                    console.log(`📤 [${salon.name}] Sending reply to ${message.from}: ${replyText}`);
                    
                    const sentMessage = await salon.client.sendMessage(message.from, replyText);
                    console.log(`✅ [${salon.name}] Message sent successfully: ${sentMessage.id._serialized}`);
                } else {
                    console.log(`ℹ️ [${salon.name}] No reply text provided by backend`);
                }
            } else {
                console.log(`ℹ️ [${salon.name}] No reply needed from backend`);
            }
            
        } catch (error) {
            console.error(`❌ [${salon.name}] Error processing message:`, error.message);
            
            // Send error message to user
            try {
                await salon.client.sendMessage(message.from, "😔 Sorry, we're experiencing technical difficulties. Please try again later or contact us directly.");
            } catch (sendError) {
                console.error(`❌ [${salon.name}] Error sending error message:`, sendError);
            }
        }
    });
    
    // Setup Express routes for this salon
    setupSalonRoutes(salonId);
    
    // Initialize WhatsApp client
    salon.client.initialize();
}

// Setup Express routes for a salon
function setupSalonRoutes(salonId) {
    const salon = salonData[salonId];
    
    salon.app.use(express.json());
    
    // Health check
    salon.app.get('/health', (req, res) => {
        res.json({
            status: salon.isReady ? 'ready' : 'not_ready',
            salon: salon.name,
            salon_id: salonId,
            port: salon.port,
            timestamp: new Date().toISOString(),
            client_info: salon.clientInfo,
            connection_status: salon.connectionStatus
        });
    });
    
    // Service info
    salon.app.get('/info', (req, res) => {
        res.json({
            service: `${salon.name} WhatsApp Service`,
            salon_id: salonId,
            port: salon.port,
            status: salon.isReady ? 'ready' : 'initializing',
            qr_available: !!salon.qrCodeData,
            backend_url: BACKEND_URL,
            webhook_path: `/webhook/whatsapp/${salonId}`,
            connection_status: salon.connectionStatus
        });
    });
    
    // Connection status
    salon.app.get('/connection-status', (req, res) => {
        res.json({
            ...salon.connectionStatus,
            current_status: salon.isReady ? 'connected' : 'disconnected',
            qr_needed: !salon.isReady && !salon.connectionStatus.is_connected
        });
    });
    
    // Reset connection
    salon.app.post('/reset-connection', (req, res) => {
        try {
            // Reset connection status
            salon.connectionStatus.is_connected = false;
            salon.connectionStatus.phone_number = null;
            salon.connectionStatus.connected_at = null;
            salon.connectionStatus.qr_generated_count = 0;
            saveConnectionStatus(salonId);
            
            // Remove session files to force re-authentication
            const sessionPath = `.wwebjs_auth/session-${salon.clientId}`;
            if (fs.existsSync(sessionPath)) {
                fs.rmSync(sessionPath, { recursive: true });
                console.log(`🗑️ [${salon.name}] Removed session files`);
            }
            
            res.json({
                success: true,
                message: `Connection reset for ${salon.name}. Restart the service to generate new QR code.`
            });
        } catch (error) {
            res.status(500).json({
                success: false,
                error: error.message
            });
        }
    });
    
    // QR code page
    salon.app.get('/qr', (req, res) => {
        // Check if already connected
        if (salon.connectionStatus.is_connected && salon.isReady) {
            const connectedSince = new Date(salon.connectionStatus.connected_at);
            const timeSinceConnection = Date.now() - connectedSince.getTime();
            const hoursSinceConnection = Math.floor(timeSinceConnection / (1000 * 60 * 60));
            
            res.send(`
                <!DOCTYPE html>
                <html>
                <head>
                    <title>${salon.name} - Already Connected</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <style>
                        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #e8f5e8; }
                        .container { background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 500px; }
                        .success { color: #25D366; }
                        .salon-info { background: #e8f5e8; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                        .connection-info { background: #f0f8ff; padding: 15px; border-radius: 5px; margin: 20px 0; text-align: left; }
                        .reset-btn { background: #ff6b6b; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin-top: 10px; }
                        .reset-btn:hover { background: #ff5252; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="salon-info">
                            <h2>🏢 ${salon.name}</h2>
                            <p>📍 Salon ID: ${salonId}</p>
                        </div>
                        <h1 class="success">✅ WhatsApp Already Connected!</h1>
                        <p>This salon's WhatsApp is already connected and ready to receive messages.</p>
                        
                        <div class="connection-info">
                            <strong>📋 Connection Details:</strong><br>
                            📱 Phone: ${salon.connectionStatus.phone_number}<br>
                            🕒 Connected: ${connectedSince.toLocaleString()}<br>
                            ⏰ Online for: ${hoursSinceConnection} hours<br>
                            🔢 Total connections: ${salon.connectionStatus.connection_count}
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
            return;
        }
        
        // Show QR code if not connected
        if (salon.qrCodeData) {
            res.send(`
                <!DOCTYPE html>
                <html>
                <head>
                    <title>${salon.name} - WhatsApp QR Code</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <style>
                        body { font-family: Arial, sans-serif; text-align: center; padding: 20px; background: #f0f8ff; }
                        .container { background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 500px; }
                        .salon-info { background: #e8f5e8; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                        .qr-container { margin: 20px 0; }
                        .instructions { background: #fff3cd; padding: 15px; border-radius: 5px; margin-top: 20px; text-align: left; }
                        .auto-detect { background: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0; }
                        .refresh-btn { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin-top: 10px; }
                        .refresh-btn:hover { background: #0056b3; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="salon-info">
                            <h2>🏢 ${salon.name}</h2>
                            <p>📍 Salon ID: ${salonId}</p>
                            <p>📱 Port: ${salon.port}</p>
                        </div>
                        
                        <h1>📱 WhatsApp QR Code</h1>
                        
                        <div class="auto-detect">
                            <h3>🎯 Automatic Salon Detection Active!</h3>
                            <p>✨ Once you scan this QR code and connect WhatsApp, customers can simply send <strong>"hi"</strong> and will automatically get ${salon.name}'s services and barbers!</p>
                            <p>🔄 No need for special commands - the system will remember this is ${salon.name}'s WhatsApp number.</p>
                        </div>
                        
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
                        
                        <button class="refresh-btn" onclick="window.location.reload()">🔄 Refresh QR Code</button>
                        
                        <p style="margin-top: 20px; color: #666; font-size: 14px;">
                            🔄 This page will auto-refresh every 30 seconds to check connection status
                        </p>
                    </div>
                    
                    <script src="https://cdn.jsdelivr.net/npm/qrcode@1.5.3/build/qrcode.min.js"></script>
                    <script>
                        // Generate QR code
                        const qrData = \`${salon.qrCodeData}\`;
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
                        
                        // Auto-refresh every 30 seconds to check connection status
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
                    <title>${salon.name} - Initializing</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <style>
                        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f0f8ff; }
                        .container { background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                        .salon-info { background: #e8f5e8; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                        .loading { color: #007bff; }
                        .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #007bff; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin: 20px auto; }
                        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="salon-info">
                            <h2>🏢 ${salon.name}</h2>
                            <p>📍 Salon ID: ${salonId}</p>
                        </div>
                        <h1 class="loading">🔄 Initializing WhatsApp...</h1>
                        <div class="spinner"></div>
                        <p>Please wait while we generate your QR code...</p>
                        <p>This page will automatically refresh when ready.</p>
                    </div>
                    
                    <script>
                        // Auto-refresh every 5 seconds until QR code is ready
                        setTimeout(() => {
                            window.location.reload();
                        }, 5000);
                    </script>
                </body>
                </html>
            `);
        }
    });
    
    // QR code image endpoint
    salon.app.get('/qr-image', (req, res) => {
        const qrImagePath = `${salonId}_qr.png`;
        if (fs.existsSync(qrImagePath)) {
            res.sendFile(path.resolve(qrImagePath));
        } else {
            res.status(404).json({ error: 'QR code image not found' });
        }
    });
    
    // Start the Express server for this salon
    salon.app.listen(salon.port, () => {
        console.log(`🚀 [${salon.name}] WhatsApp service running on port ${salon.port}`);
        console.log(`🔗 [${salon.name}] QR Code URL: http://localhost:${salon.port}/qr`);
    });
}

// Initialize all salons
function initializeAllSalons() {
    console.log('🏢 Starting Multi-Salon WhatsApp Service');
    console.log('🔧 Initializing all salons...');
    
    Object.keys(SALONS).forEach(salonId => {
        initializeSalon(salonId);
    });
    
    console.log('✅ All salons initialized!');
    console.log('\n📋 Salon Summary:');
    Object.keys(SALONS).forEach(salonId => {
        const salon = SALONS[salonId];
        console.log(`  🏢 ${salon.name} (${salonId}): http://localhost:${salon.port}/qr`);
    });
}

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('\n🛑 Shutting down all WhatsApp services...');
    
    const shutdownPromises = Object.keys(salonData).map(async (salonId) => {
        const salon = salonData[salonId];
        if (salon.client) {
            try {
                await salon.client.destroy();
                console.log(`✅ [${salon.name}] WhatsApp client shutdown complete`);
            } catch (error) {
                console.error(`❌ [${salon.name}] Error during shutdown:`, error.message);
            }
        }
    });
    
    await Promise.all(shutdownPromises);
    console.log('👋 All services shut down. Goodbye!');
    process.exit(0);
});

// Start the multi-salon service
initializeAllSalons(); 