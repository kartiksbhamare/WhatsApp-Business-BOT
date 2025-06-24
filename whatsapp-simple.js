const { Client, LocalAuth } = require('whatsapp-web.js');
const express = require('express');
const qrcode = require('qrcode');
const axios = require('axios');
const fs = require('fs');

const PORT = process.env.PORT || 3000;
const SALON_NAME = process.env.SALON_NAME || 'Beauty Salon';

console.log(`🏢 Starting ${SALON_NAME} WhatsApp Bot`);
console.log(`📋 Port: ${PORT}`);
console.log(`📋 Salon: ${SALON_NAME}`);

// Express app
const app = express();
app.use(express.json());

// Global storage
let whatsappClient = null;
let qrCodeData = null;
let isReady = false;

console.log(`🔧 Initializing WhatsApp client...`);

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
    
    console.log(`🔍 Searching for Chrome executable...`);
    for (const path of chromePaths) {
        console.log(`  Checking: ${path}`);
        if (fs.existsSync(path)) {
            console.log(`✅ Found Chrome at: ${path}`);
            return path;
        } else {
            console.log(`  ❌ Not found`);
        }
    }
    
    console.log(`⚠️ Chrome not found in standard locations, using system default`);
    return undefined; // Let Puppeteer use its default
}

// Get Puppeteer arguments based on environment
function getPuppeteerArgs() {
    const baseArgs = ['--no-sandbox', '--disable-setuid-sandbox'];
    
    // Check if running in Railway/container environment first
    const isContainer = process.env.RAILWAY_ENVIRONMENT || process.env.DOCKER_ENV || 
                       process.env.PUPPETEER_EXECUTABLE_PATH || 
                       fs.existsSync('/usr/bin/google-chrome-stable');
    
    if (isContainer) {
        // Container-specific arguments for Railway/Docker (don't add baseArgs again)
        return [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--no-first-run',
            '--no-zygote',
            '--single-process',
            '--disable-extensions',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-ipc-flooding-protection',
            '--disable-features=TranslateUI',
            '--disable-features=BlinkGenPropertyTrees',
            '--disable-hang-monitor',
            '--disable-prompt-on-repost',
            '--disable-sync',
            '--disable-translate',
            '--memory-pressure-off',
            '--max_old_space_size=4096',
            '--use-gl=swiftshader',
            '--disable-software-rasterizer',
            '--disable-background-networking',
            '--hide-scrollbars',
            '--metrics-recording-only',
            '--mute-audio',
            '--no-default-browser-check',
            '--safebrowsing-disable-auto-update',
            '--ignore-certificate-errors',
            '--ignore-ssl-errors',
            '--ignore-certificate-errors-spki-list',
            '--disable-web-security',
            '--allow-running-insecure-content',
            '--disable-features=VizDisplayCompositor',
            '--disable-features=VizHitTestSurfaceLayer',
            '--disable-blink-features=AutomationControlled',
            '--disable-client-side-phishing-detection',
            '--disable-component-extensions-with-background-pages',
            '--disable-default-apps',
            '--disable-dev-shm-usage',
            '--disable-extensions-file-access-check',
            '--disable-features=TranslateUI',
            '--disable-ipc-flooding-protection',
            '--enable-features=NetworkService,NetworkServiceInProcess',
            '--force-color-profile=srgb',
            '--metrics-recording-only',
            '--no-default-browser-check',
            '--no-first-run',
            '--password-store=basic',
            '--use-mock-keychain',
            '--disable-background-mode',
            '--disable-add-to-shelf',
            '--disable-background-downloads',
            '--disable-background-sync'
        ];
    }
    
    // Add Docker-specific arguments if in container (fallback)
    if (process.env.PUPPETEER_ARGS) {
        const dockerArgs = process.env.PUPPETEER_ARGS.split(' ').filter(arg => arg.trim());
        return [...baseArgs, ...dockerArgs];
    }
    
    // Add additional arguments for stability (local development)
    return [
        ...baseArgs,
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--no-first-run',
        '--disable-extensions'
    ];
}

try {
    // Initialize WhatsApp client with dynamic Chrome configuration
    const chromeExecutablePath = getChromeExecutablePath();
    const puppeteerArgs = getPuppeteerArgs();
    
    console.log(`🔧 Chrome executable: ${chromeExecutablePath || 'system default'}`);
    console.log(`🔧 Puppeteer args: ${puppeteerArgs.join(' ')}`);
    
    const puppeteerConfig = {
        headless: true,
        args: puppeteerArgs,
        timeout: 60000,
        protocolTimeout: 60000,
        handleSIGINT: false,
        handleSIGTERM: false,
        handleSIGHUP: false,
        defaultViewport: null,
        devtools: false
    };
    
    if (chromeExecutablePath) {
        puppeteerConfig.executablePath = chromeExecutablePath;
    }
    
    whatsappClient = new Client({
        authStrategy: new LocalAuth({ clientId: 'simple-salon' }),
        puppeteer: puppeteerConfig,
        restartOnAuthFail: true,
        qrMaxRetries: 5,
        takeoverOnConflict: true,
        takeoverTimeoutMs: 60000
    });

    console.log(`✅ WhatsApp client created successfully`);

    // QR Code event
    whatsappClient.on('qr', (qr) => {
        console.log(`📱 [${SALON_NAME}] QR Code generated`);
        qrCodeData = qr;
        
        // Generate QR code image
        qrcode.toFile('qr.png', qr, (err) => {
            if (err) {
                console.error(`❌ [${SALON_NAME}] Error generating QR code image:`, err);
            } else {
                console.log(`✅ [${SALON_NAME}] QR code image saved as qr.png`);
            }
        });
    });

    // Ready event
    whatsappClient.on('ready', () => {
        console.log(`✅ [${SALON_NAME}] WhatsApp Bot is ready!`);
        isReady = true;
        qrCodeData = null;
    });

    // Message received event
    whatsappClient.on('message', async (message) => {
        console.log(`📨 [${SALON_NAME}] Received message from ${message.from}:`);
        console.log(`📝 Message body: "${message.body}"`);
        console.log(`👤 Contact name: ${message._data.notifyName || 'Unknown'}`);
        console.log(`📊 Message type: ${message.type}`);
        console.log(`🔍 Is status: ${message.isStatus}`);
        console.log(`👥 Is group: ${message.from.includes('@g.us')}`);
        
        // Skip if message is from status broadcast or groups
        if (message.isStatus || message.from.includes('@g.us')) {
            console.log(`⏭️ [${SALON_NAME}] Skipping status/group message`);
            return;
        }
        
        try {
            console.log(`🔗 [${SALON_NAME}] Sending to backend webhook...`);
            
            // Send to backend webhook
            const webhookData = {
                body: message.body,
                from: message.from,
                contactName: message._data.notifyName || 'Unknown'
            };
            
            console.log(`📤 [${SALON_NAME}] Webhook data:`, JSON.stringify(webhookData, null, 2));
            
            const response = await axios.post('http://localhost:8000/webhook/whatsapp', webhookData, {
                headers: {
                    'Content-Type': 'application/json'
                },
                timeout: 10000
            });
            
            console.log(`📊 [${SALON_NAME}] Backend response status: ${response.status}`);
            console.log(`📝 [${SALON_NAME}] Backend response:`, JSON.stringify(response.data, null, 2));
            
            if (response.data && response.data.reply) {
                console.log(`📤 [${SALON_NAME}] Sending reply to ${message.from}: ${response.data.reply}`);
                await whatsappClient.sendMessage(message.from, response.data.reply);
                console.log(`✅ [${SALON_NAME}] Reply sent successfully`);
            } else {
                console.log(`ℹ️ [${SALON_NAME}] No reply from backend`);
            }
        } catch (error) {
            console.error(`❌ [${SALON_NAME}] Error processing message:`, error.message);
            if (error.response) {
                console.error(`📊 [${SALON_NAME}] Backend error status: ${error.response.status}`);
                console.error(`📝 [${SALON_NAME}] Backend error data:`, error.response.data);
            }
            
            // Send error message to user
            try {
                await whatsappClient.sendMessage(message.from, "😔 Sorry, we're experiencing technical difficulties. Please try again later or contact us directly.");
                console.log(`📤 [${SALON_NAME}] Error message sent to user`);
            } catch (sendError) {
                console.error(`❌ [${SALON_NAME}] Error sending error message:`, sendError.message);
            }
        }
    });

    // Error handling
    whatsappClient.on('disconnected', (reason) => {
        console.log(`❌ [${SALON_NAME}] WhatsApp Bot disconnected:`, reason);
        isReady = false;
    });

    console.log(`🔧 Setting up event handlers complete`);

} catch (error) {
    console.error(`❌ Error creating WhatsApp client:`, error);
    process.exit(1);
}

// Express routes
app.get('/health', (req, res) => {
    res.json({
        status: isReady ? 'ready' : 'not_ready',
        salon: SALON_NAME,
        port: PORT,
        timestamp: new Date().toISOString()
    });
});

app.get('/qr', (req, res) => {
    if (isReady) {
        res.send(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>${SALON_NAME} - Connected</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #e8f5e8; }
                    .container { background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>✅ ${SALON_NAME} WhatsApp Connected!</h1>
                    <p>Your bot is ready to receive messages.</p>
                </div>
            </body>
            </html>
        `);
    } else if (qrCodeData) {
        res.send(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>${SALON_NAME} - Scan QR Code</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 20px; background: #f0f8ff; }
                    .container { background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                    .qr-container { margin: 20px 0; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>📱 ${SALON_NAME} - Scan QR Code</h1>
                    <div class="qr-container">
                        <img src="/qr-image" alt="WhatsApp QR Code" style="max-width: 300px; border: 2px solid #25D366; border-radius: 10px;">
                    </div>
                    <p><strong>How to Connect:</strong></p>
                    <ol style="text-align: left; display: inline-block;">
                        <li>Open WhatsApp on your phone</li>
                        <li>Go to Settings → Linked Devices</li>
                        <li>Tap "Link a Device"</li>
                        <li>Scan the QR code above</li>
                    </ol>
                    <p>Once connected, customers can send "hi" to start booking!</p>
                </div>
                
                <script>
                    // Auto-refresh every 30 seconds
                    setTimeout(() => window.location.reload(), 30000);
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
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f0f8ff; }
                    .container { background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
                    .spinner { border: 4px solid #f3f3f3; border-top: 4px solid #007bff; border-radius: 50%; width: 50px; height: 50px; animation: spin 1s linear infinite; margin: 20px auto; }
                    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🔄 ${SALON_NAME} - Initializing...</h1>
                    <div class="spinner"></div>
                    <p>Please wait while we generate your QR code...</p>
                </div>
                
                <script>
                    // Auto-refresh every 5 seconds
                    setTimeout(() => window.location.reload(), 5000);
                </script>
            </body>
            </html>
        `);
    }
});

app.get('/qr-image', (req, res) => {
    const fs = require('fs');
    const path = require('path');
    const qrImagePath = 'qr.png';
    
    if (fs.existsSync(qrImagePath)) {
        res.sendFile(path.resolve(qrImagePath));
    } else {
        res.status(404).json({ error: 'QR code image not found' });
    }
});

// Start server
app.listen(PORT, () => {
    console.log(`🚀 [${SALON_NAME}] WhatsApp Bot running on port ${PORT}`);
    console.log(`🔗 [${SALON_NAME}] QR Code URL: http://localhost:${PORT}/qr`);
    
    // Initialize WhatsApp with enhanced error handling and retries
    let initializationAttempts = 0;
    const maxInitializationAttempts = 5;
    
    const initializeWithRetry = async () => {
        initializationAttempts++;
        console.log(`🔄 [${SALON_NAME}] Initializing WhatsApp client (attempt ${initializationAttempts}/${maxInitializationAttempts})...`);
        
        try {
            // Add a small delay before initialization to let Chrome settle
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            await whatsappClient.initialize();
            console.log(`✅ [${SALON_NAME}] WhatsApp client initialized successfully!`);
        } catch (error) {
            console.error(`❌ [${SALON_NAME}] Initialization failed (attempt ${initializationAttempts}):`, error.message);
            
            if (initializationAttempts < maxInitializationAttempts) {
                const retryDelay = Math.min(10000 * initializationAttempts, 60000); // Exponential backoff, max 60s
                console.log(`🔄 [${SALON_NAME}] Retrying in ${retryDelay/1000} seconds...`);
                
                // Clean up any existing client state
                try {
                    await whatsappClient.destroy();
                } catch (destroyError) {
                    console.log(`🧹 [${SALON_NAME}] Client cleanup completed`);
                }
                
                setTimeout(initializeWithRetry, retryDelay);
            } else {
                console.error(`❌ [${SALON_NAME}] Failed to initialize after ${maxInitializationAttempts} attempts`);
                console.log(`🔄 [${SALON_NAME}] Will continue running server, manual restart may be needed`);
            }
        }
    };
    
    // Start initialization after a brief delay
    setTimeout(initializeWithRetry, 3000);
});

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