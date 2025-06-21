const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3000; // Use Railway's PORT environment variable

// Store the client instance
let client = null;
let isInitializing = false;
let initializationAttempts = 0;
const MAX_INITIALIZATION_ATTEMPTS = 5;
let isReady = false;

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

        // QR Code generation
        client.on('qr', (qr) => {
            console.log('📱 QR Code received, scan with your WhatsApp app:');
            console.log('🔗 QR Code for WhatsApp Web authentication:');
            qrcode.generate(qr, { small: true });
            console.log('📝 Copy this QR code and scan it with your phone.');
            console.log('⚠️ IMPORTANT: This QR code will expire in 45 seconds!');
        });

        // Authentication successful
        client.on('authenticated', () => {
            console.log('✅ WhatsApp Web authenticated successfully!');
        });

        // Authentication failure
        client.on('auth_failure', (msg) => {
            console.error('❌ WhatsApp Web authentication failed:', msg);
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
        const backendUrl = process.env.BACKEND_URL || `http://localhost:${PORT}`;
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
    
    // Initialize WhatsApp Web Client after server starts
    console.log('⏰ Waiting 5 seconds before initializing WhatsApp Client...');
    setTimeout(() => {
        initializeWhatsAppClient();
    }, 5000);
}); 