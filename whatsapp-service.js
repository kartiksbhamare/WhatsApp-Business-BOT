const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode');
const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000; // WhatsApp service port
const BACKEND_PORT = process.env.BACKEND_PORT || 8080; // FastAPI backend port

// Store the client instance and QR code
let client = null;
let isInitializing = false;
let initializationAttempts = 0;
const MAX_INITIALIZATION_ATTEMPTS = 5;
let isReady = false;
let currentQRCode = null; // Store current QR code data
let qrCodeGenerated = false;

app.use(cors());
app.use(express.json());

// Initialize WhatsApp Web Client
async function initializeWhatsAppClient() {
    if (isInitializing) {
        console.log('🔄 WhatsApp Client is already initializing...');
        return;
    }

    isInitializing = true;
    initializationAttempts++;

    console.log(`🚀 Starting WhatsApp Web Client... (Attempt ${initializationAttempts})`);

    try {
        // Create WhatsApp client with Railway-optimized settings
        client = new Client({
            authStrategy: new LocalAuth({
                clientId: "booking-bot",
                dataPath: "/app/.wwebjs_auth"
            }),
            puppeteer: {
                headless: true,
                executablePath: '/usr/bin/google-chrome-stable',
                args: [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-extensions',
                    '--disable-default-apps',
                    '--disable-sync',
                    '--disable-translate',
                    '--disable-background-networking',
                    '--disable-background-timer-throttling',
                    '--disable-renderer-backgrounding',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-client-side-phishing-detection',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection',
                    '--memory-pressure-off',
                    '--max_old_space_size=2048',
                    '--disable-accelerated-2d-canvas',
                    '--disable-canvas-aa',
                    '--disable-2d-canvas-clip-aa',
                    '--disable-gl-drawing-for-tests',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-gpu-sandbox',
                    '--disable-software-rasterizer',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-field-trial-config',
                    '--disable-features=AudioServiceOutOfProcess',
                    '--disable-features=IPCFlooding',
                    '--disable-features=LazyFrameLoading',
                    '--disable-features=ScriptStreaming',
                    '--disable-features=V8VmFuture',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-features=VizHitTestSurfaceLayer',
                    '--disable-features=VizSurfaceActivation',
                    '--force-color-profile=srgb',
                    '--metrics-recording-only',
                    '--no-crash-upload',
                    '--no-default-browser-check',
                    '--no-pings',
                    '--password-store=basic',
                    '--use-mock-keychain',
                    '--disable-component-update',
                    '--disable-domain-reliability',
                    '--disable-features=AutofillServerCommunication',
                    '--disable-features=CertificateTransparencyComponentUpdater',
                    '--disable-features=OptimizationHints',
                    '--disable-features=Translate',
                    '--disable-features=InterestFeedContentSuggestions',
                    '--disable-features=MediaRouter',
                    '--disable-default-apps',
                    '--mute-audio',
                    '--no-default-browser-check',
                    '--autoplay-policy=user-gesture-required',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-notifications',
                    '--disable-renderer-backgrounding',
                    '--disable-permissions-api',
                    '--disable-popup-blocking'
                ],
                timeout: 0, // No timeout
                protocolTimeout: 0, // No protocol timeout
                handleSIGINT: false,
                handleSIGTERM: false,
                handleSIGHUP: false,
                ignoreHTTPSErrors: true,
                defaultViewport: {
                    width: 1366,
                    height: 768
                }
            },
            webVersionCache: {
                type: 'remote',
                remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.2412.54.html',
            }
        });

        // QR Code handling with PNG generation and log display
        client.on('qr', async (qr) => {
            console.log('\n🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥');
            console.log('📱 WHATSAPP QR CODE GENERATED!');
            console.log('🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥🔥\n');
            
            try {
                // Generate QR code as PNG file with high quality
                const qrPath = './whatsapp_qr_code.png';
                await qrcode.toFile(qrPath, qr, {
                    width: 400,
                    margin: 4,
                    color: {
                        dark: '#000000',
                        light: '#FFFFFF'
                    },
                    errorCorrectionLevel: 'M'
                });
                
                console.log('✅ QR Code PNG saved as: whatsapp_qr_code.png');
                
                // Try multiple terminal rendering methods
                let qrDisplayed = false;
                
                // Method 1: Try terminal renderer (most reliable)
                try {
                    const qrTerminal = await qrcode.toString(qr, {
                        type: 'terminal',
                        width: 35,
                        small: true
                    });
                    
                    console.log('\n📋 QR CODE FOR WHATSAPP (scan from your phone):');
                    console.log('='.repeat(60));
                    console.log(qrTerminal);
                    console.log('='.repeat(60));
                    qrDisplayed = true;
                    
                } catch (terminalError) {
                    console.log('⚠️ Terminal QR display failed, trying alternative...');
                    
                    // Method 2: Try smaller terminal version
                    try {
                        const qrSmall = await qrcode.toString(qr, {
                            type: 'terminal',
                            width: 25
                        });
                        
                        console.log('\n📋 QR CODE (SMALLER VERSION):');
                        console.log('-'.repeat(40));
                        console.log(qrSmall);
                        console.log('-'.repeat(40));
                        qrDisplayed = true;
                        
                    } catch (smallError) {
                        console.log('⚠️ Small terminal QR also failed, showing web instructions only...');
                    }
                }
                
                // Always show web instructions (most reliable method)
                console.log('\n🌐 BEST OPTION - SCAN FROM WEB BROWSER:');
                console.log('🔗 Visit this URL in your browser:');
                console.log(`🌐 https://whatsapp-business-bot-production.up.railway.app/qr`);
                console.log('📱 Then scan the QR code from your browser with WhatsApp');
                
                console.log('\n🎯 STEP-BY-STEP INSTRUCTIONS:');
                console.log('1. 🌐 Open the URL above in ANY web browser');
                console.log('2. 📱 Open WhatsApp on your mobile phone');
                console.log('3. ⚙️  Go to Settings > Linked Devices');
                console.log('4. 📸 Tap "Link a Device"');
                console.log('5. 🎯 Scan the QR code from your browser screen');
                console.log('6. ⏳ Wait for connection...\n');
                
                if (!qrDisplayed) {
                    console.log('⚠️ QR code display in logs failed - use web browser method above');
                }
                
                // Store QR code data for web endpoint
                currentQRCode = qr;
                qrCodeGenerated = true;
                
                console.log('⚠️ QR Code expires in 45 seconds - act fast!');
                console.log('🔄 If expired, the system will generate a new one automatically');
                
            } catch (error) {
                console.error('❌ Error generating QR code:', error);
                
                // Store QR code data anyway for web endpoint
                currentQRCode = qr;
                qrCodeGenerated = true;
                
                console.log('\n🌐 QR CODE AVAILABLE VIA WEB ONLY:');
                console.log('🔗 https://whatsapp-business-bot-production.up.railway.app/qr');
                console.log('📱 Open this URL and scan the QR code with WhatsApp');
            }
        });

        // Authentication successful
        client.on('authenticated', () => {
            console.log('✅ WhatsApp Web authenticated successfully!');
            currentQRCode = null; // Clear QR code after authentication
        });

        // Authentication failure
        client.on('auth_failure', (msg) => {
            console.error('❌ WhatsApp Web authentication failed:', msg);
            currentQRCode = null; // Clear QR code on failure
            isInitializing = false;
            
            if (initializationAttempts < MAX_INITIALIZATION_ATTEMPTS) {
                console.log(`🔄 Retrying WhatsApp Web initialization in 20 seconds... (${initializationAttempts}/${MAX_INITIALIZATION_ATTEMPTS})`);
                setTimeout(initializeWhatsAppClient, 20000);
            }
        });

        // Client ready
        client.on('ready', () => {
            console.log('✅ WhatsApp Web Client initialized successfully!');
            console.log('🎉 WhatsApp Web Client is ready to receive messages!');
            console.log(`🌍 Running on Railway cloud at port ${PORT}`);
            currentQRCode = null; // Clear QR code when ready
            isReady = true;
            isInitializing = false;
            initializationAttempts = 0;
        });

        // Message received
        client.on('message', async (message) => {
            console.log('📨 Received message:', message.body);
            console.log('📱 From phone:', message.from);
            console.log('📋 Message details:', {
                from: message.from,
                to: message.to,
                body: message.body,
                type: message.type,
                timestamp: message.timestamp,
                id: message.id._serialized,
                isGroupMsg: message.from.includes('@g.us')
            });
            
            // Forward message to FastAPI backend
            try {
                await forwardMessageToBackend(message);
            } catch (error) {
                console.error('❌ Error forwarding message to backend:', error);
            }
        });

        // Disconnection handling
        client.on('disconnected', (reason) => {
            console.log('⚠️ WhatsApp Web Client was disconnected:', reason);
            isReady = false;
            client = null;
            currentQRCode = null; // Clear QR code on disconnect
            
            if (initializationAttempts < MAX_INITIALIZATION_ATTEMPTS) {
                console.log('🔄 Attempting to reconnect in 15 seconds...');
                setTimeout(initializeWhatsAppClient, 15000);
            }
        });

        // Error handling
        client.on('error', (error) => {
            console.error('❌ WhatsApp Web Client error:', error);
            // Don't retry immediately on error, wait for disconnection event
        });

        // Initialize the client with retry logic
        console.log('🔧 Initializing WhatsApp Web Client...');
        console.log('⏳ This may take 30-60 seconds in cloud environment...');
        
        // Add a longer delay before initialization in cloud
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        await client.initialize();

    } catch (error) {
        console.error('❌ Error initializing WhatsApp Web Client:', error.message);
        console.error('🔍 Full error:', error);
        isInitializing = false;
        
        if (initializationAttempts < MAX_INITIALIZATION_ATTEMPTS) {
            console.log(`🔄 Retrying WhatsApp Web Client initialization in 20 seconds... (${initializationAttempts}/${MAX_INITIALIZATION_ATTEMPTS})`);
            setTimeout(initializeWhatsAppClient, 20000);
        } else {
            console.log('❌ Max initialization attempts reached. Please restart the service.');
        }
    }
}

// Forward message to FastAPI backend
async function forwardMessageToBackend(message) {
    try {
        const messageData = {
            from: message.from,
            to: message.to,
            body: message.body,
            type: message.type,
            timestamp: message.timestamp,
            id: message.id._serialized,
            isGroupMsg: message.from.includes('@g.us'),
            author: message.author || message.from
        };

        // Use localhost for internal communication in Railway
        const backendUrl = process.env.BACKEND_URL || `http://127.0.0.1:${BACKEND_PORT}`;
        const webhookUrl = `${backendUrl}/webhook/whatsapp`;
        
        console.log('📤 Forwarding message to backend...');
        console.log(`🔗 Backend URL: ${webhookUrl}`);
        console.log(`📋 Message data:`, JSON.stringify(messageData, null, 2));

        // Use node-fetch or built-in fetch (Node 18+)
        const fetch = globalThis.fetch || require('node-fetch');
        
        const response = await fetch(webhookUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(messageData),
        });

        console.log(`📊 Backend response status: ${response.status}`);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`❌ Backend response error: ${response.status} - ${errorText}`);
            throw new Error(`HTTP error! status: ${response.status}, body: ${errorText}`);
        }

        const result = await response.json();
        console.log('✅ Message forwarded to backend successfully:', result);
        
        // If backend returns a response message, send it
        if (result.reply) {
            console.log(`📤 Sending reply to ${message.from}: ${result.reply}`);
            await sendMessage(message.from, result.reply);
        } else {
            console.log('ℹ️ No reply from backend');
        }
    } catch (error) {
        console.error('❌ Error forwarding message to backend:', error);
        console.error('🔍 Error details:', {
            message: error.message,
            stack: error.stack,
            name: error.name
        });
    }
}

// Send message function
async function sendMessage(to, message) {
    if (!client || !isReady) {
        throw new Error('WhatsApp Web Client not initialized or not ready');
    }

    try {
        // Ensure phone number is in correct format
        let phoneNumber = to;
        
        // WhatsApp Web.js uses the format as received, no need to modify
        console.log(`📤 Sending message to: ${phoneNumber}`);
        console.log(`📝 Message content: ${message}`);
        
        const result = await client.sendMessage(phoneNumber, message);
        console.log('✅ Message sent successfully:', result.id._serialized);
        return result;
    } catch (error) {
        console.error('❌ Error sending message:', error);
        throw error;
    }
}

// API Routes
app.get('/health', (req, res) => {
    const status = {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        service: 'WhatsApp Web Service',
        client_ready: isReady,
        initializing: isInitializing,
        environment: process.env.NODE_ENV || 'development',
        platform: 'Railway Cloud'
    };
    
    console.log('🏥 Health check requested:', status);
    res.json(status);
});

app.get('/info', async (req, res) => {
    try {
        if (!client || !isReady) {
            return res.status(503).json({
                error: 'WhatsApp Web Client not ready',
                ready: false
            });
        }

        const info = await client.info;
        const clientInfo = {
            ready: isReady,
            user: {
                id: info.wid._serialized,
                name: info.pushname,
                platform: info.platform
            },
            version: info.phone.wa_version,
            battery: info.battery || null
        };

        console.log('ℹ️ Client info requested:', clientInfo);
        res.json(clientInfo);
    } catch (error) {
        console.error('❌ Error getting client info:', error);
        res.status(500).json({
            error: 'Failed to get client info',
            message: error.message
        });
    }
});

app.post('/send-message', async (req, res) => {
    try {
        const { phone, message } = req.body;

        if (!phone || !message) {
            return res.status(400).json({
                error: 'Phone number and message are required',
                required_fields: ['phone', 'message']
            });
        }

        if (!client || !isReady) {
            return res.status(503).json({
                error: 'WhatsApp Web Client not ready',
                ready: isReady
            });
        }

        console.log('📤 API send message request:', { phone, message });

        const result = await sendMessage(phone, message);
        
        res.json({
            success: true,
            message: 'Message sent successfully',
            messageId: result.id._serialized,
            timestamp: new Date().toISOString()
        });

    } catch (error) {
        console.error('❌ Error in send-message API:', error);
        res.status(500).json({
            error: 'Failed to send message',
            message: error.message
        });
    }
});

app.get('/status', (req, res) => {
    const status = {
        service: 'WhatsApp Web Service',
        ready: isReady,
        initializing: isInitializing,
        attempts: initializationAttempts,
        timestamp: new Date().toISOString()
    };
    
    res.json(status);
});

// Serve the QR code PNG file directly
app.get('/qr-image', (req, res) => {
    const qrPath = './whatsapp_qr_code.png';
    
    console.log('🖼️ QR image requested, file exists:', fs.existsSync(qrPath));
    
    if (fs.existsSync(qrPath)) {
        res.setHeader('Content-Type', 'image/png');
        res.setHeader('Cache-Control', 'no-cache');
        res.sendFile(path.resolve(qrPath));
    } else {
        res.status(404).json({ 
            error: 'QR code image not available',
            message: 'QR code has not been generated yet or has expired',
            suggestion: 'Visit /qr for the web interface'
        });
    }
});

// Simple QR image page
app.get('/qr-simple', (req, res) => {
    const qrPath = './whatsapp_qr_code.png';
    
    if (!fs.existsSync(qrPath)) {
        res.send(`
            <!DOCTYPE html>
            <html>
            <head><title>QR Code Not Ready</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1>⏳ QR Code Not Ready</h1>
                <p>Please wait for WhatsApp to initialize...</p>
                <button onclick="window.location.reload()">Refresh</button>
            </body>
            </html>
        `);
        return;
    }
    
    res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>WhatsApp QR Code</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { 
                    font-family: Arial; 
                    text-align: center; 
                    padding: 20px; 
                    background: #f5f5f5; 
                }
                .container { 
                    background: white; 
                    padding: 30px; 
                    border-radius: 10px; 
                    display: inline-block; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
                }
                img { 
                    max-width: 100%; 
                    border: 2px solid #25D366; 
                    border-radius: 10px; 
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📱 Scan with WhatsApp</h1>
                <img src="/qr-image" alt="WhatsApp QR Code" />
                <p>⚠️ Expires in 45 seconds</p>
                <button onclick="window.location.reload()">🔄 Refresh</button>
            </div>
        </body>
        </html>
    `);
});

// QR Code web page - Simplified and reliable
app.get('/qr', (req, res) => {
    console.log('🌐 QR page requested - qrCodeGenerated:', qrCodeGenerated, 'currentQRCode exists:', !!currentQRCode);
    
    if (!qrCodeGenerated || !currentQRCode) {
        res.send(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>WhatsApp QR Code - Loading</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { 
                        font-family: Arial, sans-serif; 
                        text-align: center; 
                        padding: 20px;
                        background: #f0f2f5;
                        margin: 0;
                        min-height: 100vh;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    }
                    .container {
                        background: white;
                        border-radius: 15px;
                        padding: 40px;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                        max-width: 500px;
                        width: 90%;
                    }
                    .spinner {
                        border: 4px solid #f3f3f3;
                        border-top: 4px solid #25D366;
                        border-radius: 50%;
                        width: 50px;
                        height: 50px;
                        animation: spin 1s linear infinite;
                        margin: 20px auto;
                    }
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🔄 WhatsApp QR Code Loading...</h1>
                    <div class="spinner"></div>
                    <p>⏳ WhatsApp Web is initializing...</p>
                    <p>🔄 QR Code will appear here once ready</p>
                    <p><small>Auto-refreshing in 5 seconds...</small></p>
                    <script>
                        setTimeout(() => window.location.reload(), 5000);
                    </script>
                </div>
            </body>
            </html>
        `);
        return;
    }

    // Generate QR code as data URL for web display
    qrcode.toDataURL(currentQRCode, { 
        width: 400, 
        margin: 4,
        errorCorrectionLevel: 'M'
    }, (err, url) => {
        if (err) {
            console.error('❌ Error generating QR data URL:', err);
            res.status(500).send(`
                <!DOCTYPE html>
                <html>
                <head><title>QR Code Error</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1>❌ QR Code Generation Error</h1>
                    <p>Please refresh the page or try again.</p>
                    <button onclick="window.location.reload()">Refresh</button>
                </body>
                </html>
            `);
            return;
        }

        console.log('✅ QR code data URL generated successfully');
        
        res.send(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>📱 WhatsApp QR Code - Scan Now!</title>
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { 
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        text-align: center; 
                        padding: 20px;
                        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
                        color: white;
                        min-height: 100vh;
                        margin: 0;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    }
                    .container {
                        background: white;
                        color: #333;
                        border-radius: 20px;
                        padding: 30px;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                        max-width: 450px;
                        width: 90%;
                    }
                    .qr-container {
                        background: #f8f9fa;
                        border-radius: 15px;
                        padding: 20px;
                        margin: 20px 0;
                        border: 2px solid #e9ecef;
                    }
                    .qr-code {
                        width: 100%;
                        max-width: 300px;
                        height: auto;
                        border-radius: 10px;
                    }
                    .instructions {
                        text-align: left;
                        background: #e8f5e8;
                        padding: 20px;
                        border-radius: 10px;
                        margin: 20px 0;
                        border-left: 4px solid #25D366;
                    }
                    .warning {
                        background: #fff3cd;
                        color: #856404;
                        padding: 15px;
                        border-radius: 8px;
                        margin: 15px 0;
                        border-left: 4px solid #ffc107;
                        font-size: 14px;
                    }
                    .title {
                        color: #25D366;
                        margin-bottom: 10px;
                    }
                    .step {
                        margin: 8px 0;
                        font-size: 15px;
                    }
                    .refresh-btn {
                        background: #25D366;
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 25px;
                        cursor: pointer;
                        font-size: 14px;
                        margin-top: 15px;
                    }
                    .refresh-btn:hover {
                        background: #128C7E;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1 class="title">📱 WhatsApp QR Code</h1>
                    
                    <div class="qr-container">
                        <img src="${url}" alt="WhatsApp QR Code" class="qr-code" />
                    </div>
                    
                    <div class="instructions">
                        <h3>🎯 How to Scan:</h3>
                        <div class="step">1. <strong>Open WhatsApp</strong> on your phone</div>
                        <div class="step">2. Go to <strong>Settings → Linked Devices</strong></div>
                        <div class="step">3. Tap <strong>"Link a Device"</strong></div>
                        <div class="step">4. <strong>Scan this QR code</strong></div>
                        <div class="step">5. Wait for connection ✅</div>
                    </div>
                    
                    <div class="warning">
                        ⚠️ <strong>Important:</strong> QR code expires in 45 seconds. 
                        If expired, click refresh below.
                    </div>
                    
                    <button class="refresh-btn" onclick="window.location.reload()">
                        🔄 Refresh QR Code
                    </button>
                    
                    <p><small>🔄 Auto-refresh in 40 seconds...</small></p>
                    
                    <script>
                        setTimeout(() => window.location.reload(), 40000);
                    </script>
                </div>
            </body>
            </html>
        `);
    });
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('🛑 Shutting down WhatsApp Web Service...');
    
    if (client) {
        await client.destroy();
    }
    
    process.exit(0);
});

process.on('SIGTERM', async () => {
    console.log('🛑 Shutting down WhatsApp Web Service...');
    
    if (client) {
        await client.destroy();
    }
    
    process.exit(0);
});

// Start the server
app.listen(PORT, '0.0.0.0', () => {
    console.log(`🌐 WhatsApp Web service running on Railway cloud`);
    console.log(`🔗 Port: ${PORT}`);
    console.log(`📋 Health check: http://localhost:${PORT}/health`);
    console.log(`📤 Send message: POST http://localhost:${PORT}/send-message`);
    console.log(`ℹ️  Get info: http://localhost:${PORT}/info`);
    console.log(`📊 Status: http://localhost:${PORT}/status`);
    console.log(`🌍 Environment: ${process.env.NODE_ENV || 'development'}`);
    
    // Try to detect Railway URL from various environment variables
    const possibleUrls = [
        process.env.RAILWAY_PUBLIC_DOMAIN,
        process.env.RAILWAY_STATIC_URL,
        process.env.PUBLIC_URL,
        process.env.VERCEL_URL,
        process.env.RAILWAY_DOMAIN
    ].filter(Boolean);
    
    console.log('🌐 ========================================');
    console.log('🌐 TO ACCESS QR CODE:');
    
    if (possibleUrls.length > 0) {
        const railwayUrl = possibleUrls[0];
        const protocol = railwayUrl.includes('localhost') ? 'http' : 'https';
        const fullUrl = railwayUrl.startsWith('http') ? railwayUrl : `${protocol}://${railwayUrl}`;
        console.log(`🌐 PUBLIC URL: ${fullUrl}`);
        console.log(`🌐 QR CODE PAGE: ${fullUrl}/qr`);
    } else {
        console.log('🌐 1. Go to Railway Dashboard → Settings → Networking');
        console.log('🌐 2. Click "Generate Domain" button');
        console.log('🌐 3. Copy the generated URL');
        console.log('🌐 4. Add "/qr" to the end of the URL');
        console.log('🌐 5. Visit that URL to scan the QR code');
    }
    
    console.log('🌐 ========================================');
    
    // Initialize WhatsApp Web Client after server starts
    console.log('⏰ Waiting 5 seconds before initializing WhatsApp Client...');
    setTimeout(() => {
        initializeWhatsAppClient();
    }, 5000);
}); 