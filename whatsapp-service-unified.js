const { Client, LocalAuth } = require('whatsapp-web.js');
const express = require('express');
const qrcode = require('qrcode');
const fs = require('fs');
const axios = require('axios');
const path = require('path');

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
const PORT = process.env.PORT || 3000;

// Single salon configuration
const SALON_NAME = process.env.SALON_NAME || 'Beauty Salon';

// Global storage
let whatsappClient = null;
let qrCodeData = null;
let isReady = false;
let clientInfo = null;

// Express app
const app = express();
app.use(express.json());

// Connection status
let connectionStatus = {
    is_connected: false,
    phone_number: null,
    connected_at: null,
    last_seen: null,
    connection_count: 0,
    qr_generated_count: 0
};

// Connection status file management
function loadConnectionStatus() {
    const statusFile = 'connection_status.json';
    try {
        if (fs.existsSync(statusFile)) {
            const data = fs.readFileSync(statusFile, 'utf8');
            const loaded = JSON.parse(data);
            connectionStatus = { ...connectionStatus, ...loaded };
            console.log(`📋 [${SALON_NAME}] Loaded connection status: ${connectionStatus.is_connected ? '✅ Connected' : '❌ Not Connected'}`);
            if (connectionStatus.phone_number) {
                console.log(`📱 [${SALON_NAME}] Phone: ${connectionStatus.phone_number}`);
            }
        } else {
            console.log(`📋 [${SALON_NAME}] No previous connection status found`);
        }
    } catch (error) {
        console.error(`❌ [${SALON_NAME}] Error loading connection status:`, error.message);
    }
}

function saveConnectionStatus() {
    const statusFile = 'connection_status.json';
    try {
        fs.writeFileSync(statusFile, JSON.stringify(connectionStatus, null, 2));
        console.log(`💾 [${SALON_NAME}] Connection status saved`);
    } catch (error) {
        console.error(`❌ [${SALON_NAME}] Error saving connection status:`, error.message);
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
        console.log(`✅ [${SALON_NAME}] WhatsApp connected! Phone: ${phoneNumber}`);
    } else {
        console.log(`❌ [${SALON_NAME}] WhatsApp disconnected`);
    }
    
    saveConnectionStatus();
}

// Initialize WhatsApp client
function initializeWhatsApp() {
    console.log(`🏢 Initializing ${SALON_NAME} WhatsApp Bot`);
    
    // Load connection status
    loadConnectionStatus();
    
    // Determine Chrome executable path based on environment
    function getChromeExecutablePath() {
        // Check if running in Docker container (prioritize this)
        if (process.env.PUPPETEER_EXECUTABLE_PATH) {
            console.log(`🐳 Using Docker Chrome path: ${process.env.PUPPETEER_EXECUTABLE_PATH}`);
            return process.env.PUPPETEER_EXECUTABLE_PATH;
        }
        
        // Check for common Chrome paths (prioritize Linux for containers)
        const chromePaths = [
            '/usr/bin/google-chrome-stable',  // Linux (Docker/Railway)
            '/usr/bin/google-chrome',         // Linux alternative
            '/usr/bin/chromium-browser',      // Ubuntu/Debian alternative
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',  // macOS
            'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',    // Windows
            'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe' // Windows 32-bit
        ];
        
        console.log(`🔍 [${SALON_NAME}] Searching for Chrome executable...`);
        for (const path of chromePaths) {
            console.log(`  Checking: ${path}`);
            if (fs.existsSync(path)) {
                console.log(`✅ [${SALON_NAME}] Found Chrome at: ${path}`);
                return path;
            } else {
                console.log(`  ❌ Not found`);
            }
        }
        
        console.log(`⚠️ [${SALON_NAME}] Chrome not found in standard locations, using system default`);
        return undefined; // Let Puppeteer use its default
    }

    // Get Puppeteer arguments based on environment
    function getPuppeteerArgs() {
        const baseArgs = ['--no-sandbox', '--disable-setuid-sandbox'];
        
        // Add Docker-specific arguments if in container
        if (process.env.PUPPETEER_ARGS) {
            const dockerArgs = process.env.PUPPETEER_ARGS.split(' ');
            return [...baseArgs, ...dockerArgs];
        }
        
        // Check if running in Railway/container environment
        const isContainer = process.env.RAILWAY_ENVIRONMENT || process.env.DOCKER_ENV || 
                           process.env.PUPPETEER_EXECUTABLE_PATH || 
                           fs.existsSync('/usr/bin/google-chrome-stable');
        
        if (isContainer) {
            // Container-specific arguments for Railway/Docker
            return [
                ...baseArgs,
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-default-apps',
                '--single-process',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-ipc-flooding-protection',
                '--disable-features=TranslateUI',
                '--disable-features=BlinkGenPropertyTrees',
                '--run-all-compositor-stages-before-draw',
                '--disable-threaded-animation',
                '--disable-threaded-scrolling',
                '--disable-checker-imaging',
                '--disable-new-content-rendering-timeout',
                '--disable-image-animation-resync',
                '--disable-partial-raster',
                '--use-gl=swiftshader',
                '--disable-software-rasterizer'
            ];
        }
        
        // Add additional arguments for stability (local development)
        return [
            ...baseArgs,
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
            '--disable-extensions',
            '--disable-plugins',
            '--disable-default-apps'
        ];
    }

    // Get Chrome configuration
    const chromeExecutablePath = getChromeExecutablePath();
    const puppeteerArgs = getPuppeteerArgs();
    
    console.log(`🔧 [${SALON_NAME}] Chrome executable: ${chromeExecutablePath || 'system default'}`);
    console.log(`🔧 [${SALON_NAME}] Puppeteer args: ${puppeteerArgs.join(' ')}`);
    
    const puppeteerConfig = {
        headless: true,
        args: puppeteerArgs
    };
    
    if (chromeExecutablePath) {
        puppeteerConfig.executablePath = chromeExecutablePath;
    }
    
    // Initialize WhatsApp client with dynamic Chrome configuration
    whatsappClient = new Client({
        authStrategy: new LocalAuth({ clientId: 'salon-bot' }),
        puppeteer: puppeteerConfig
    });
    
    // Ready event
    whatsappClient.on('ready', () => {
        console.log(`✅ [${SALON_NAME}] WhatsApp Bot is ready!`);
        isReady = true;
        clientInfo = whatsappClient.info;
        qrCodeData = null;
        
        const phoneNumber = clientInfo?.wid?.user || 'Unknown';
        updateConnectionStatus(true, phoneNumber);
    });
    
    // Disconnected event
    whatsappClient.on('disconnected', (reason) => {
        console.log(`❌ [${SALON_NAME}] WhatsApp Bot disconnected:`, reason);
        isReady = false;
        clientInfo = null;
        updateConnectionStatus(false);
        
        // Auto-retry connection after 30 seconds
        setTimeout(() => {
            console.log(`🔄 [${SALON_NAME}] Attempting to reconnect...`);
            try {
                whatsappClient.initialize();
            } catch (error) {
                console.error(`❌ [${SALON_NAME}] Reconnection failed:`, error.message);
            }
        }, 30000);
    });
    
    // Error event
    whatsappClient.on('auth_failure', (msg) => {
        console.error(`❌ [${SALON_NAME}] Authentication failure:`, msg);
        isReady = false;
        updateConnectionStatus(false);
    });
    
    // QR Code event
    whatsappClient.on('qr', (qr) => {
        console.log(`📱 [${SALON_NAME}] QR Code generated`);
        qrCodeData = qr;
        connectionStatus.qr_generated_count += 1;
        saveConnectionStatus();
        
        // Generate QR code image
        qrcode.toFile('qr.png', qr, (err) => {
            if (err) {
                console.error(`❌ [${SALON_NAME}] Error generating QR code image:`, err);
            } else {
                console.log(`✅ [${SALON_NAME}] QR code image saved as qr.png`);
            }
        });
    });
    
    // Message received event
    whatsappClient.on('message', async (message) => {
        console.log(`📨 [${SALON_NAME}] Received message:`, message.body);
        console.log(`📱 From phone: ${message.from}`);
        
        // Skip if message is from status broadcast or groups
        if (message.isStatus || message.from.includes('@g.us')) {
            console.log(`⏭️ [${SALON_NAME}] Skipping status/group message`);
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
            const backendUrl = `${BACKEND_URL}/webhook/whatsapp`;
            console.log(`🔗 [${SALON_NAME}] Backend URL: ${backendUrl}`);
            
            const response = await axios.post(backendUrl, messageData, {
                headers: {
                    'Content-Type': 'application/json'
                },
                timeout: 10000
            });
            
            console.log(`📊 [${SALON_NAME}] Backend response status: ${response.status}`);
            
            if (response.data && response.data.reply) {
                console.log(`✅ [${SALON_NAME}] Message forwarded to backend successfully`);
                
                // Send reply if provided
                const replyText = response.data.reply;
                if (replyText && replyText.trim()) {
                    console.log(`📤 [${SALON_NAME}] Sending reply to ${message.from}: ${replyText}`);
                    
                    const sentMessage = await whatsappClient.sendMessage(message.from, replyText);
                    console.log(`✅ [${SALON_NAME}] Message sent successfully: ${sentMessage.id._serialized}`);
                } else {
                    console.log(`ℹ️ [${SALON_NAME}] No reply text provided by backend`);
                }
            } else {
                console.log(`ℹ️ [${SALON_NAME}] No reply needed from backend`);
            }
            
        } catch (error) {
            console.error(`❌ [${SALON_NAME}] Error processing message:`, error.message);
            
            // Send error message to user
            try {
                await whatsappClient.sendMessage(message.from, "😔 Sorry, we're experiencing technical difficulties. Please try again later or contact us directly.");
            } catch (sendError) {
                console.error(`❌ [${SALON_NAME}] Error sending error message:`, sendError);
            }
        }
    });
    
    // Initialize WhatsApp client with error handling
    try {
        console.log(`🔄 [${SALON_NAME}] Initializing WhatsApp client...`);
        whatsappClient.initialize().catch((error) => {
            console.error(`❌ [${SALON_NAME}] WhatsApp initialization error:`, error.message);
            isReady = false;
            updateConnectionStatus(false);
            
            // Retry after 10 seconds
            setTimeout(() => {
                console.log(`🔄 [${SALON_NAME}] Retrying initialization...`);
                initializeWhatsApp();
            }, 10000);
        });
    } catch (error) {
        console.error(`❌ [${SALON_NAME}] Error initializing WhatsApp client:`, error.message);
        isReady = false;
        updateConnectionStatus(false);
        
        // Retry after 10 seconds
        setTimeout(() => {
            console.log(`🔄 [${SALON_NAME}] Retrying initialization...`);
            initializeWhatsApp();
        }, 10000);
    }
}

// Express routes
app.get('/health', (req, res) => {
    res.json({
        status: isReady ? 'ready' : 'not_ready',
        salon: SALON_NAME,
        port: PORT,
        timestamp: new Date().toISOString(),
        client_info: clientInfo,
        connection_status: connectionStatus
    });
});

app.get('/info', (req, res) => {
    res.json({
        service: `${SALON_NAME} WhatsApp Bot`,
        port: PORT,
        status: isReady ? 'ready' : 'initializing',
        qr_available: !!qrCodeData,
        backend_url: BACKEND_URL,
        webhook_path: '/webhook/whatsapp',
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
        const sessionPath = '.wwebjs_auth/session-salon-bot';
        if (fs.existsSync(sessionPath)) {
            fs.rmSync(sessionPath, { recursive: true });
            console.log(`🗑️ [${SALON_NAME}] Removed session files`);
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

// QR code page
app.get('/qr', (req, res) => {
    // Check if already connected
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
                        <h2>🏢 ${SALON_NAME}</h2>
                    </div>
                    <h1 class="success">✅ WhatsApp Already Connected!</h1>
                    <p>Your salon's WhatsApp bot is already connected and ready to receive messages.</p>
                    
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
        return;
    }
    
    // Show QR code if not connected
    if (qrCodeData) {
        res.send(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>${SALON_NAME} - WhatsApp QR Code</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 20px; background: #f0f8ff; }
                    .container { background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 500px; }
                    .salon-info { background: #e8f5e8; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
                    .qr-container { margin: 20px 0; }
                    .instructions { background: #fff3cd; padding: 15px; border-radius: 5px; margin-top: 20px; text-align: left; }
                    .refresh-btn { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; margin-top: 10px; }
                    .refresh-btn:hover { background: #0056b3; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="salon-info">
                        <h2>🏢 ${SALON_NAME}</h2>
                        <p>📱 WhatsApp Booking Bot</p>
                    </div>
                    
                    <h1>📱 Scan QR Code to Connect</h1>
                    
                    <div class="qr-container">
                        <img src="/qr-image" alt="WhatsApp QR Code" style="max-width: 300px; height: auto; border: 2px solid #25D366; border-radius: 10px;" onerror="this.style.display='none'; document.getElementById('qr-error').style.display='block';">
                        <div id="qr-error" style="display: none; color: #dc3545; margin-top: 15px;">
                            <p>🔄 Generating QR code...</p>
                            <p>Please refresh in a few seconds.</p>
                        </div>
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
                        <p><strong>🎉 Once connected, customers can send "hi" to start booking!</strong></p>
                    </div>
                    
                    <button class="refresh-btn" onclick="window.location.reload()">🔄 Refresh QR Code</button>
                    
                    <p style="margin-top: 20px; color: #666; font-size: 14px;">
                        🔄 This page will auto-refresh every 30 seconds to check connection status
                    </p>
                </div>
                
                <script>
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
                <title>${SALON_NAME} - Initializing</title>
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
                        <h2>🏢 ${SALON_NAME}</h2>
                    </div>
                    <h1 class="loading">🔄 Initializing WhatsApp Bot...</h1>
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
app.get('/qr-image', (req, res) => {
    const qrImagePath = 'qr.png';
    if (fs.existsSync(qrImagePath)) {
        res.sendFile(path.resolve(qrImagePath));
    } else {
        res.status(404).json({ error: 'QR code image not found' });
    }
});

// Start the Express server
app.listen(PORT, () => {
    console.log(`🚀 [${SALON_NAME}] WhatsApp Bot running on port ${PORT}`);
    console.log(`🔗 [${SALON_NAME}] QR Code URL: http://localhost:${PORT}/qr`);
});

// Initialize WhatsApp
initializeWhatsApp();

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('\n🛑 Shutting down WhatsApp Bot...');
    
    if (whatsappClient) {
        try {
            await whatsappClient.destroy();
            console.log(`✅ [${SALON_NAME}] WhatsApp client shutdown complete`);
        } catch (error) {
            console.error(`❌ [${SALON_NAME}] Error during shutdown:`, error.message);
        }
    }
    
    console.log('👋 Bot shut down. Goodbye!');
    process.exit(0);
}); 