const venom = require('venom-bot');
const express = require('express');
const cors = require('cors');

const app = express();
const PORT = 3000;

// Store the client instance
let client = null;
let isInitializing = false;
let initializationAttempts = 0;
const MAX_INITIALIZATION_ATTEMPTS = 5;

app.use(cors());
app.use(express.json());

// Initialize Venom Bot with better configuration
async function initializeVenomBot() {
    if (isInitializing) {
        console.log('🔄 Venom Bot is already initializing...');
        return;
    }

    isInitializing = true;
    initializationAttempts++;

    console.log(`🚀 Starting Venom Bot... (Attempt ${initializationAttempts})`);

    try {
        const venomOptions = {
            session: 'booking-bot',
            headless: true,
            devtools: false,
            useChrome: true,
            debug: false,
            logQR: true,
            browserWS: '',
            executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            browserArgs: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
                '--disable-extensions',
                '--disable-default-apps',
                '--disable-translate',
                '--disable-sync',
                '--disable-background-networking',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows',
                '--disable-ipc-flooding-protection'
            ],
            refreshQR: 15000, // Refresh QR every 15 seconds
            autoClose: 300000, // Close after 5 minutes of no activity
            waitForLogin: true,
            puppeteerOptions: {
                headless: true,
                executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                args: [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage'
                ]
            },
            createPathFileToken: true,
            addBrowserArgs: [],
            folderNameToken: 'tokens',
            mkdirFolderToken: '',
            headless: 'new',
            addProxy: [],
            browserPathExecutable: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            addBrowserArgs: []
        };

        client = await venom.create(venomOptions);
        
        console.log('✅ Venom Bot initialized successfully!');
        isInitializing = false;
        initializationAttempts = 0;

        // Set up message listener
        client.onMessage((message) => {
            console.log('📨 Received message:', message.body);
            console.log('📱 From phone:', message.from);
            console.log('📋 Message details:', {
                from: message.from,
                chatId: message.chatId,
                type: message.type,
                isGroupMsg: message.isGroupMsg
            });
            
            // Forward message to FastAPI backend
            forwardMessageToBackend(message)
                .catch(error => console.error('❌ Error forwarding message:', error));
        });

        // Set up status change listener
        client.onStateChange((state) => {
            console.log('🔄 State changed:', state);
            
            if (state === 'CONFLICT' || state === 'UNLAUNCHED') {
                console.log('⚠️ WhatsApp Web logged out, reinitializing...');
                client = null;
                setTimeout(() => {
                    if (initializationAttempts < MAX_INITIALIZATION_ATTEMPTS) {
                        initializeVenomBot();
                    } else {
                        console.log('❌ Max initialization attempts reached. Please restart the service.');
                    }
                }, 5000);
            }
        });

        console.log('🎉 Venom Bot is ready to receive messages!');
        return client;

    } catch (error) {
        console.error('❌ Error initializing Venom Bot:', error.message);
        isInitializing = false;
        
        if (initializationAttempts < MAX_INITIALIZATION_ATTEMPTS) {
            console.log(`🔄 Retrying Venom Bot initialization in 10 seconds... (${initializationAttempts}/${MAX_INITIALIZATION_ATTEMPTS})`);
            setTimeout(initializeVenomBot, 10000);
        } else {
            console.log('❌ Max initialization attempts reached. Please restart the service.');
        }
    }
}

// Forward message to FastAPI backend
async function forwardMessageToBackend(message) {
    try {
        const response = await fetch('http://localhost:8000/webhook/venom', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                from: message.from,
                body: message.body,
                type: message.type,
                timestamp: message.timestamp,
                id: message.id,
                chatId: message.chatId,
                author: message.author,
                isGroupMsg: message.isGroupMsg
            }),
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
    if (!client) {
        throw new Error('Venom Bot not initialized');
    }

    try {
        // Ensure phone number is in correct format
        let phoneNumber = to;
        
        // If it doesn't contain @c.us, add it
        if (!phoneNumber.includes('@c.us')) {
            // Remove any non-digits and format properly
            const cleanNumber = phoneNumber.replace(/\D/g, '');
            phoneNumber = `${cleanNumber}@c.us`;
        }
        
        console.log(`📤 Sending message to: ${phoneNumber}`);
        console.log(`📝 Message content: ${message}`);
        
        const result = await client.sendText(phoneNumber, message);
        console.log('✅ Message sent successfully:', result);
        return result;
    } catch (error) {
        console.error('❌ Error sending message:', error);
        throw error;
    }
}

// API Routes
app.get('/health', (req, res) => {
    const status = client ? 'ready' : 'not ready';
    res.json({
        status: status,
        timestamp: new Date().toISOString(),
        attempts: initializationAttempts,
        maxAttempts: MAX_INITIALIZATION_ATTEMPTS
    });
});

app.post('/send-message', async (req, res) => {
    try {
        const { to, message } = req.body;
        
        if (!to || !message) {
            return res.status(400).json({
                success: false,
                error: 'Missing required fields: to, message'
            });
        }

        if (!client) {
            return res.status(503).json({
                success: false,
                error: 'Venom Bot not initialized'
            });
        }

        const result = await sendMessage(to, message);
        res.json({
            success: true,
            result: result
        });
    } catch (error) {
        console.error('❌ Error in send-message endpoint:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

app.get('/info', async (req, res) => {
    try {
        if (!client) {
            return res.status(503).json({
                success: false,
                error: 'Venom Bot not initialized'
            });
        }

        const info = await client.getHostDevice();
        res.json({
            success: true,
            info: info
        });
    } catch (error) {
        console.error('❌ Error getting info:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('📱 Shutting down Venom Bot...');
    
    if (client) {
        try {
            await client.close();
        } catch (error) {
            console.error('❌ Error closing Venom Bot:', error);
        }
    }
    
    process.exit(0);
});

process.on('SIGTERM', async () => {
    console.log('📱 Shutting down Venom Bot...');
    
    if (client) {
        try {
            await client.close();
        } catch (error) {
            console.error('❌ Error closing Venom Bot:', error);
        }
    }
    
    process.exit(0);
});

// Start the server
app.listen(PORT, () => {
    console.log(`🌐 Venom service running on port ${PORT}`);
    console.log(`📋 Health check: http://localhost:${PORT}/health`);
    console.log(`📤 Send message: POST http://localhost:${PORT}/send-message`);
    console.log(`ℹ️  Get info: http://localhost:${PORT}/info`);
    
    // Initialize Venom Bot
    initializeVenomBot();
}); 