const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const express = require('express');
const qrcode = require('qrcode');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(express.json());

let clients = {};
let qrCodes = {};
let isReady = {};

// Salon configuration
const SALON_CONFIG = {
    salon_a: {
        name: "Downtown Beauty Salon",
        phone: "+1234567890",
        port: 3005,
        sessionPath: './sessions/salon_a'
    },
    salon_b: {
        name: "Uptown Hair Studio", 
        phone: "+0987654321",
        port: 3006,
        sessionPath: './sessions/salon_b'
    },
    salon_c: {
        name: "Luxury Spa & Salon",
        phone: "+1122334455", 
        port: 3007,
        sessionPath: './sessions/salon_c'
    }
};

// Create sessions directory
if (!fs.existsSync('./sessions')) {
    fs.mkdirSync('./sessions', { recursive: true });
}

// Initialize WhatsApp clients for each salon with retry logic
async function initializeClients() {
    console.log('🚀 Initializing WhatsApp clients for all salons...');
    
    for (const [salonId, config] of Object.entries(SALON_CONFIG)) {
        await initializeClientWithRetry(salonId, config, 3);
    }
}

async function initializeClientWithRetry(salonId, config, maxRetries = 3) {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            console.log(`📱 Setting up ${config.name} (${salonId}) - Attempt ${attempt}/${maxRetries}...`);
            
            // Create session directory for this salon
            if (!fs.existsSync(config.sessionPath)) {
                fs.mkdirSync(config.sessionPath, { recursive: true });
            }
            
            // Initialize client with Railway-optimized settings
            const client = new Client({
                authStrategy: new LocalAuth({
                    clientId: salonId,
                    dataPath: config.sessionPath
                }),
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
                        '--disable-gpu',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding',
                        '--disable-field-trial-config',
                        '--disable-ipc-flooding-protection',
                        '--memory-pressure-off',
                        '--max_old_space_size=4096'
                    ],
                    executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || '/usr/bin/google-chrome-stable'
                },
                webVersionCache: {
                    type: 'remote',
                    remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.2412.54.html',
                }
            });

            // QR Code event
            client.on('qr', async (qr) => {
                console.log(`📱 QR Code generated for ${config.name}`);
                qrCodes[salonId] = qr;
                
                // Generate QR code image
                try {
                    const qrImage = await qrcode.toDataURL(qr);
                    qrCodes[`${salonId}_image`] = qrImage;
                    console.log(`✅ QR image generated for ${config.name}`);
                } catch (err) {
                    console.error(`❌ Error generating QR image for ${config.name}:`, err);
                }
            });

            // Ready event
            client.on('ready', () => {
                console.log(`✅ ${config.name} WhatsApp client is ready!`);
                isReady[salonId] = true;
            });

            // Message event
            client.on('message', async (message) => {
                try {
                    console.log(`📨 Message received for ${config.name}: ${message.body}`);
                    
                    // Forward to FastAPI backend
                    const webhookData = {
                        body: message.body,
                        from: message.from,
                        to: message.to,
                        contactName: message._data.notifyName || 'Unknown',
                        isGroupMsg: message.isGroupMsg
                    };
                    
                    // Send to salon-specific webhook
                    const backendPort = process.env.BACKEND_PORT || process.env.PORT || 8080;
                    const response = await fetch(`http://localhost:${backendPort}/webhook/whatsapp/${salonId}`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(webhookData)
                    });
                    
                    if (response.ok) {
                        const result = await response.json();
                        if (result.reply) {
                            await message.reply(result.reply);
                            console.log(`📤 Reply sent for ${config.name}: ${result.reply}`);
                        }
                    } else {
                        console.error(`❌ Webhook failed for ${config.name}:`, response.status);
                    }
                } catch (error) {
                    console.error(`❌ Error processing message for ${config.name}:`, error);
                }
            });

            // Authentication failure
            client.on('auth_failure', (msg) => {
                console.error(`❌ Authentication failed for ${config.name}:`, msg);
                isReady[salonId] = false;
            });

            // Disconnected event
            client.on('disconnected', (reason) => {
                console.log(`⚠️ ${config.name} disconnected:`, reason);
                isReady[salonId] = false;
            });

            // Store client
            clients[salonId] = client;
            
            // Initialize client with timeout
            await Promise.race([
                client.initialize(),
                new Promise((_, reject) => 
                    setTimeout(() => reject(new Error('Initialization timeout')), 60000)
                )
            ]);
            
            console.log(`✅ ${config.name} initialized successfully!`);
            break; // Success, exit retry loop
            
        } catch (error) {
            console.error(`❌ Error initializing ${config.name} (attempt ${attempt}/${maxRetries}):`, error.message);
            
            // Clean up failed client
            if (clients[salonId]) {
                try {
                    await clients[salonId].destroy();
                } catch (destroyError) {
                    console.error(`Error destroying failed client:`, destroyError.message);
                }
                delete clients[salonId];
            }
            
            if (attempt === maxRetries) {
                console.error(`❌ Failed to initialize ${config.name} after ${maxRetries} attempts. Continuing with other salons...`);
                // Generate a fallback QR for demo purposes
                generateFallbackQR(salonId, config);
            } else {
                console.log(`⏳ Retrying ${config.name} in 5 seconds...`);
                await new Promise(resolve => setTimeout(resolve, 5000));
            }
        }
    }
}

// Generate fallback QR for Railway demo when real WhatsApp fails
function generateFallbackQR(salonId, config) {
    console.log(`📱 Generating fallback QR for ${config.name}...`);
    
    // Create a WhatsApp Web URL that opens chat with the salon
    const whatsappUrl = `https://wa.me/${config.phone.replace('+', '')}?text=hi%20I%20want%20to%20book%20at%20${encodeURIComponent(config.name)}`;
    
    qrcode.toDataURL(whatsappUrl)
        .then(qrImage => {
            qrCodes[salonId] = whatsappUrl;
            qrCodes[`${salonId}_image`] = qrImage;
            console.log(`✅ Fallback QR generated for ${config.name}`);
        })
        .catch(err => {
            console.error(`❌ Error generating fallback QR for ${config.name}:`, err);
        });
}

// API Routes

// Health check
app.get('/health', (req, res) => {
    const status = {
        service: 'Real WhatsApp Web Service',
        status: 'running',
        salons: {}
    };
    
    for (const salonId of Object.keys(SALON_CONFIG)) {
        status.salons[salonId] = {
            ready: isReady[salonId] || false,
            hasQR: !!qrCodes[salonId]
        };
    }
    
    res.json(status);
});

// Get QR code for specific salon
app.get('/qr/:salonId', (req, res) => {
    const { salonId } = req.params;
    const config = SALON_CONFIG[salonId];
    
    if (!config) {
        return res.status(404).json({ error: 'Salon not found' });
    }
    
    const qrData = qrCodes[salonId];
    const qrImage = qrCodes[`${salonId}_image`];
    const isRealWhatsApp = clients[salonId] && isReady[salonId];
    const isFallbackQR = qrData && qrData.startsWith('https://wa.me/');
    
    if (isRealWhatsApp) {
        res.send(`
            <html>
            <head><title>${config.name} - Connected</title></head>
            <body style="text-align:center; padding:50px; font-family:Arial;">
                <h1>✅ ${config.name}</h1>
                <h2>WhatsApp Web Connected Successfully!</h2>
                <p>Phone: ${config.phone}</p>
                <p>🎉 Real WhatsApp Web.js integration is active!</p>
                <p>You can now send messages to this salon's WhatsApp.</p>
                <button onclick="window.location.reload()">🔄 Refresh</button>
            </body>
            </html>
        `);
    } else if (isFallbackQR && qrImage) {
        res.send(`
            <html>
            <head><title>${config.name} - Scan QR Code</title></head>
            <body style="text-align:center; padding:50px; font-family:Arial;">
                <h1>📱 ${config.name}</h1>
                <h2>Scan QR Code to Chat on WhatsApp</h2>
                <p>Phone: ${config.phone}</p>
                <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px; border: 2px solid #ffc107;">
                    <h3>🔗 Direct WhatsApp Link</h3>
                    <p>This QR opens a direct WhatsApp chat with ${config.name}</p>
                    <p>Scan to start chatting immediately!</p>
                </div>
                <div style="margin: 20px;">
                    <img src="${qrImage}" alt="WhatsApp QR Code" style="max-width: 300px; border: 2px solid #25D366; border-radius: 8px;">
                </div>
                <div style="background: #d4edda; padding: 15px; border-radius: 8px; margin: 20px; border: 2px solid #28a745;">
                    <h4>📱 How to Use:</h4>
                    <p>1. Open WhatsApp on your phone</p>
                    <p>2. Scan this QR code</p>
                    <p>3. Send "hi" to start booking</p>
                    <p>4. Our booking system will respond instantly!</p>
                </div>
                <button onclick="window.location.reload()">🔄 Refresh QR</button>
                <script>setTimeout(() => window.location.reload(), 30000);</script>
            </body>
            </html>
        `);
    } else if (qrImage && !isFallbackQR) {
        res.send(`
            <html>
            <head><title>${config.name} - Scan QR Code</title></head>
            <body style="text-align:center; padding:50px; font-family:Arial;">
                <h1>📱 ${config.name}</h1>
                <h2>Scan QR Code with WhatsApp</h2>
                <p>Phone: ${config.phone}</p>
                <div style="background: #d1ecf1; padding: 15px; border-radius: 8px; margin: 20px; border: 2px solid #17a2b8;">
                    <h3>🔗 Real WhatsApp Web Integration</h3>
                    <p>This connects your phone directly to our booking system</p>
                </div>
                <div style="margin: 20px;">
                    <img src="${qrImage}" alt="WhatsApp QR Code" style="max-width: 300px;">
                </div>
                <p>1. Open WhatsApp on your phone</p>
                <p>2. Go to Settings → Linked Devices</p>
                <p>3. Tap "Link a Device"</p>
                <p>4. Scan this QR code</p>
                <button onclick="window.location.reload()">🔄 Refresh QR</button>
                <script>setTimeout(() => window.location.reload(), 30000);</script>
            </body>
            </html>
        `);
    } else {
        res.send(`
            <html>
            <head><title>${config.name} - Loading</title></head>
            <body style="text-align:center; padding:50px; font-family:Arial;">
                <h1>⏳ ${config.name}</h1>
                <h2>Initializing WhatsApp Service...</h2>
                <p>Please wait while we set up your WhatsApp connection.</p>
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px;">
                    <p>🔄 Setting up WhatsApp Web.js...</p>
                    <p>⏱️ This may take up to 60 seconds</p>
                </div>
                <button onclick="window.location.reload()">🔄 Refresh</button>
                <script>setTimeout(() => window.location.reload(), 10000);</script>
            </body>
            </html>
        `);
    }
});

// Get QR image for specific salon
app.get('/qr-image/:salonId', (req, res) => {
    const { salonId } = req.params;
    const qrImage = qrCodes[`${salonId}_image`];
    
    if (qrImage) {
        const base64Data = qrImage.replace(/^data:image\/png;base64,/, "");
        const img = Buffer.from(base64Data, 'base64');
        res.writeHead(200, {
            'Content-Type': 'image/png',
            'Content-Length': img.length
        });
        res.end(img);
    } else {
        res.status(404).json({ error: 'QR code not available' });
    }
});

// Send message
app.post('/send-message', async (req, res) => {
    try {
        const { phone, message, salonId = 'salon_a' } = req.body;
        
        const client = clients[salonId];
        if (!client || !isReady[salonId]) {
            return res.status(503).json({ error: `${SALON_CONFIG[salonId]?.name || 'Salon'} WhatsApp not ready` });
        }
        
        const chatId = phone.includes('@') ? phone : `${phone}@c.us`;
        await client.sendMessage(chatId, message);
        
        res.json({ 
            success: true, 
            message: 'Message sent successfully',
            salon: SALON_CONFIG[salonId].name
        });
    } catch (error) {
        console.error('Error sending message:', error);
        res.status(500).json({ error: 'Failed to send message' });
    }
});

// Main directory page
app.get('/', (req, res) => {
    let salonStatus = '';
    
    for (const [salonId, config] of Object.entries(SALON_CONFIG)) {
        const status = isReady[salonId] ? '✅ Connected' : (qrCodes[salonId] ? '📱 QR Ready' : '⏳ Loading');
        salonStatus += `
            <div style="background: #f5f5f5; margin: 15px; padding: 20px; border-radius: 10px;">
                <h3>${config.name}</h3>
                <p>Status: ${status}</p>
                <p>Phone: ${config.phone}</p>
                <a href="/qr/${salonId}" style="background: #25D366; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    📱 Open ${config.name}
                </a>
            </div>
        `;
    }
    
    res.send(`
        <html>
        <head><title>Real WhatsApp Web Service</title></head>
        <body style="font-family: Arial; text-align: center; padding: 30px;">
            <h1>🚀 Real WhatsApp Web Service</h1>
            <p>Multi-salon WhatsApp Web.js integration</p>
            ${salonStatus}
            <div style="margin-top: 30px; padding: 20px; background: #e3f2fd; border-radius: 10px;">
                <h3>📋 Instructions:</h3>
                <ol style="text-align: left; max-width: 400px; margin: 0 auto;">
                    <li>Click on a salon above</li>
                    <li>Scan the QR code with WhatsApp</li>
                    <li>Send "hi" to start booking</li>
                </ol>
            </div>
        </body>
        </html>
    `);
});

// Start server
const PORT = 3000; // Fixed port for WhatsApp service
app.listen(PORT, () => {
    console.log(`🚀 Real WhatsApp Web Service running on port ${PORT}`);
    console.log(`🔗 Access at: http://localhost:${PORT}`);
    
    // Initialize clients
    initializeClients().catch(console.error);
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('🛑 Shutting down WhatsApp clients...');
    
    for (const [salonId, client] of Object.entries(clients)) {
        try {
            await client.destroy();
            console.log(`✅ ${SALON_CONFIG[salonId].name} client destroyed`);
        } catch (error) {
            console.error(`❌ Error destroying ${SALON_CONFIG[salonId].name} client:`, error);
        }
    }
    
    process.exit(0);
}); 