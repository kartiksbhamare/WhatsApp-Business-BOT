const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');
const cors = require('cors');

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

        // QR Code generation - Store the QR code for web display
        client.on('qr', (qr) => {
            console.log('📱 QR Code received, scan with your WhatsApp app:');
            console.log('🔗 QR Code for WhatsApp Web authentication:');
            
            // Store QR code data for web endpoint
            currentQRCode = qr;
            
            // Display in terminal (may be distorted in Railway logs)
            qrcode.generate(qr, { small: true });
            
            console.log('📝 QR Code is ready!');
            
            // Show the actual Railway URL
            const railwayUrl = process.env.RAILWAY_PUBLIC_DOMAIN || process.env.RAILWAY_STATIC_URL || 'your-app.railway.app';
            const protocol = railwayUrl.includes('localhost') ? 'http' : 'https';
            const fullUrl = railwayUrl.startsWith('http') ? railwayUrl : `${protocol}://${railwayUrl}`;
            
            console.log('🌐 ========================================');
            console.log('🌐 SCAN QR CODE AT THIS URL:');
            console.log(`🌐 ${fullUrl}/qr`);
            console.log('🌐 ========================================');
            console.log('⚠️ IMPORTANT: This QR code will expire in 45 seconds!');
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
        const backendUrl = process.env.BACKEND_URL || `http://localhost:${BACKEND_PORT}`;
        const response = await fetch(`${backendUrl}/webhook/whatsapp`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(messageData),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        console.log('✅ Message forwarded to backend:', result);
        
        // If backend returns a response message, send it
        if (result.reply) {
            await sendMessage(message.from, result.reply);
        }
    } catch (error) {
        console.error('❌ Error forwarding message to backend:', error);
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

// QR Code endpoint for web display
app.get('/qr', (req, res) => {
    if (!currentQRCode) {
        return res.status(404).send(`
            <html>
                <head><title>WhatsApp QR Code</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h1>🔍 No QR Code Available</h1>
                    <p>The WhatsApp Web Client is either:</p>
                    <ul style="text-align: left; display: inline-block;">
                        <li>Already authenticated ✅</li>
                        <li>Not yet initialized ⏳</li>
                        <li>QR Code has expired ⏰</li>
                    </ul>
                    <p><a href="/status">Check Service Status</a></p>
                    <p><em>Refresh this page if you're waiting for the QR code to appear.</em></p>
                </body>
            </html>
        `);
    }

    // Generate QR code as image and display in HTML
    const QRCode = require('qrcode');
    
    QRCode.toDataURL(currentQRCode, { width: 300, margin: 2 }, (err, url) => {
        if (err) {
            return res.status(500).send('Error generating QR code');
        }
        
        res.send(`
            <html>
                <head>
                    <title>WhatsApp QR Code - Scan to Login</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <style>
                        body { 
                            font-family: Arial, sans-serif; 
                            text-align: center; 
                            padding: 20px; 
                            background: #f5f5f5; 
                        }
                        .container { 
                            background: white; 
                            padding: 30px; 
                            border-radius: 10px; 
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
                            display: inline-block; 
                        }
                        .qr-code { 
                            border: 2px solid #25D366; 
                            border-radius: 10px; 
                            padding: 20px; 
                            background: white; 
                        }
                        .instructions { 
                            margin-top: 20px; 
                            color: #666; 
                        }
                        .warning { 
                            color: #ff6b6b; 
                            font-weight: bold; 
                            margin-top: 15px; 
                        }
                    </style>
                    <script>
                        // Auto-refresh every 30 seconds to check for new QR code
                        setTimeout(() => location.reload(), 30000);
                    </script>
                </head>
                <body>
                    <div class="container">
                        <h1>📱 WhatsApp Web Login</h1>
                        <div class="qr-code">
                            <img src="${url}" alt="WhatsApp QR Code" style="max-width: 100%; height: auto;">
                        </div>
                        <div class="instructions">
                            <h3>📋 How to scan:</h3>
                            <ol style="text-align: left; display: inline-block;">
                                <li>Open WhatsApp on your phone</li>
                                <li>Go to Settings → Linked Devices</li>
                                <li>Tap "Link a Device"</li>
                                <li>Scan this QR code</li>
                            </ol>
                        </div>
                        <div class="warning">
                            ⚠️ QR Code expires in 45 seconds!<br>
                            Page will auto-refresh every 30 seconds.
                        </div>
                        <p><a href="/status">Check Service Status</a></p>
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
    
    // Show the public Railway URL for QR code access
    const railwayUrl = process.env.RAILWAY_PUBLIC_DOMAIN || process.env.RAILWAY_STATIC_URL || 'your-app.railway.app';
    const protocol = railwayUrl.includes('localhost') ? 'http' : 'https';
    const fullUrl = railwayUrl.startsWith('http') ? railwayUrl : `${protocol}://${railwayUrl}`;
    
    console.log('🌐 ========================================');
    console.log('🌐 PUBLIC RAILWAY URL:');
    console.log(`🌐 ${fullUrl}`);
    console.log(`🌐 QR CODE PAGE: ${fullUrl}/qr`);
    console.log('🌐 ========================================');
    
    // Initialize WhatsApp Web Client after server starts
    console.log('⏰ Waiting 5 seconds before initializing WhatsApp Client...');
    setTimeout(() => {
        initializeWhatsAppClient();
    }, 5000);
}); 