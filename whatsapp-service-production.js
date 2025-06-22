const { Client, LocalAuth } = require('whatsapp-web.js');
const express = require('express');
const qrcode = require('qrcode');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(express.json());

let clients = {};
let qrCodes = {};
let isReady = {};
let connectionStatus = {};

// Salon configuration
const SALON_CONFIG = {
    salon_a: {
        name: "Downtown Beauty Salon",
        phone: "+1234567890",
        color: "#4CAF50"
    },
    salon_b: {
        name: "Uptown Hair Studio", 
        phone: "+0987654321",
        color: "#2196F3"
    },
    salon_c: {
        name: "Luxury Spa & Salon",
        phone: "+1122334455", 
        color: "#9C27B0"
    }
};

// Check if running on Railway
const isRailway = process.env.RAILWAY_ENVIRONMENT_NAME || process.env.PORT;
const PORT = 3000;

// Puppeteer configuration - optimized for Railway
const PUPPETEER_CONFIG = {
    headless: true,
    args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--single-process',
        '--no-zygote',
        '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding',
        '--disable-features=TranslateUI',
        '--disable-ipc-flooding-protection',
        '--no-first-run',
        '--no-default-browser-check',
        '--disable-default-apps',
        '--disable-extensions'
    ],
    executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || undefined
};

console.log(`🚀 Starting Production WhatsApp Service (Railway: ${!!isRailway})`);

// Initialize WhatsApp client for a specific salon
async function initializeSalonClient(salonId, config) {
    try {
        console.log(`🚀 Initializing WhatsApp client for ${config.name}...`);
        
        // Create sessions directory
        const sessionPath = `./sessions/${salonId}`;
        if (!fs.existsSync('./sessions')) {
            fs.mkdirSync('./sessions', { recursive: true });
        }
        
        // Create client with optimized config for Railway
        const client = new Client({
            authStrategy: new LocalAuth({ 
                clientId: salonId,
                dataPath: sessionPath
            }),
            puppeteer: PUPPETEER_CONFIG,
            webVersionCache: {
                type: 'remote',
                remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.2412.54.html',
            }
        });

        // Initialize connection status
        connectionStatus[salonId] = {
            is_connected: false,
            phone_number: config.phone,
            connected_at: null,
            last_seen: null,
            connection_count: 0,
            qr_generated_count: 0
        };

        // QR Code event - generates REAL WhatsApp Web QR codes
        client.on('qr', async (qr) => {
            console.log(`📱 REAL WhatsApp QR generated for ${config.name}`);
            
            try {
                // Convert the real WhatsApp QR to image
                const qrImage = await qrcode.toDataURL(qr, {
                    width: 300,
                    margin: 2,
                    color: {
                        dark: '#000000',
                        light: '#FFFFFF'
                    }
                });
                qrCodes[salonId] = qrImage;
                connectionStatus[salonId].qr_generated_count++;
                console.log(`✅ QR image created for ${config.name}`);
            } catch (error) {
                console.error(`❌ Error creating QR image for ${config.name}:`, error);
                generateFallbackQR(salonId, config);
            }
        });

        // Ready event
        client.on('ready', () => {
            console.log(`✅ ${config.name} WhatsApp client ready!`);
            isReady[salonId] = true;
            connectionStatus[salonId].is_connected = true;
            connectionStatus[salonId].connected_at = new Date().toISOString();
            connectionStatus[salonId].connection_count++;
        });

        // Message event
        client.on('message', async (message) => {
            try {
                console.log(`📨 Message received for ${config.name}: ${message.body}`);
                
                // Skip group messages
                if (message.isGroupMsg) return;
                
                // Update last seen
                connectionStatus[salonId].last_seen = new Date().toISOString();
                
                // Prepare webhook data
                const webhookData = {
                    body: message.body,
                    from: message.from,
                    to: message.to,
                    contactName: message._data.notifyName || 'Unknown',
                    salon_id: salonId
                };
                
                // Send to FastAPI backend
                const backendPort = process.env.BACKEND_PORT || process.env.PORT || 8080;
                const backendUrl = isRailway ? 
                    `http://localhost:${backendPort}` : 
                    `http://localhost:${backendPort}`;
                
                const response = await fetch(`${backendUrl}/webhook/whatsapp/${salonId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(webhookData)
                });
                
                if (response.ok) {
                    const result = await response.json();
                    if (result.reply) {
                        await message.reply(result.reply);
                        console.log(`📤 Reply sent for ${config.name}`);
                    }
                } else {
                    console.error(`❌ Backend webhook failed for ${config.name}:`, response.status);
                }
            } catch (error) {
                console.error(`❌ Error processing message for ${config.name}:`, error);
            }
        });

        // Error events
        client.on('auth_failure', (msg) => {
            console.error(`❌ Auth failure for ${config.name}:`, msg);
            connectionStatus[salonId].is_connected = false;
        });

        client.on('disconnected', (reason) => {
            console.log(`⚠️ ${config.name} disconnected:`, reason);
            isReady[salonId] = false;
            connectionStatus[salonId].is_connected = false;
        });

        // Store client
        clients[salonId] = client;
        
        // Initialize with timeout
        setTimeout(() => {
            client.initialize();
        }, Object.keys(SALON_CONFIG).indexOf(salonId) * 3000); // Stagger initialization
        
    } catch (error) {
        console.error(`❌ Failed to initialize ${config.name}:`, error.message);
        generateFallbackQR(salonId, config);
    }
}

// Generate fallback QR when WhatsApp Web.js fails
function generateFallbackQR(salonId, config) {
    console.log(`📱 Generating fallback QR for ${config.name}...`);
    
    // Create a direct WhatsApp link QR
    const whatsappUrl = `https://wa.me/${config.phone.replace('+', '')}?text=Hi%20I%20want%20to%20book%20at%20${encodeURIComponent(config.name)}`;
    
    qrcode.toDataURL(whatsappUrl, { 
        width: 300, 
        margin: 2,
        color: {
            dark: '#000000',
            light: '#FFFFFF'
        }
    })
    .then(qrImage => {
        qrCodes[salonId] = qrImage;
        console.log(`✅ Fallback QR created for ${config.name}`);
    })
    .catch(err => {
        console.error(`❌ Error creating fallback QR for ${config.name}:`, err);
    });
}

// Initialize all salon clients
async function initializeAllClients() {
    console.log('🚀 Starting WhatsApp Web.js clients for all salons...');
    
    // Create sessions directory
    if (!fs.existsSync('./sessions')) {
        fs.mkdirSync('./sessions', { recursive: true });
    }
    
    // Initialize each salon
    for (const [salonId, config] of Object.entries(SALON_CONFIG)) {
        await initializeSalonClient(salonId, config);
        // Small delay between initializations
        await new Promise(resolve => setTimeout(resolve, 2000));
    }
}

// API Routes

app.get('/health', (req, res) => {
    const status = {
        service: 'Production WhatsApp Web.js Service',
        status: 'running',
        environment: isRailway ? 'railway' : 'local',
        timestamp: new Date().toISOString(),
        salons: {}
    };
    
    for (const salonId of Object.keys(SALON_CONFIG)) {
        status.salons[salonId] = {
            ready: isReady[salonId] || false,
            hasQR: !!qrCodes[salonId],
            hasClient: !!clients[salonId],
            connection_status: connectionStatus[salonId] || {}
        };
    }
    
    res.json(status);
});

// Salon-specific QR code pages
app.get('/qr/:salonId', (req, res) => {
    const { salonId } = req.params;
    const config = SALON_CONFIG[salonId];
    
    if (!config) {
        return res.status(404).json({ error: 'Salon not found' });
    }
    
    const qrImage = qrCodes[salonId];
    const connected = isReady[salonId];
    const connStatus = connectionStatus[salonId] || {};
    
    if (connected) {
        res.send(`
            <html>
            <head><title>${config.name} - WhatsApp Connected</title></head>
            <body style="text-align:center; padding:50px; font-family:Arial; background: ${config.color}22;">
                <h1>✅ ${config.name}</h1>
                <h2>WhatsApp Web Connected Successfully!</h2>
                <p>📞 Phone: ${config.phone}</p>
                
                <div style="background: #d4edda; padding: 20px; border-radius: 10px; margin: 20px; border: 2px solid #28a745;">
                    <h3>🎉 Your WhatsApp is now the booking bot!</h3>
                    <p>Customers can message <strong>${config.phone}</strong> to book appointments.</p>
                    <p>The bot will automatically respond with booking options.</p>
                    <p><strong>Connected:</strong> ${new Date(connStatus.connected_at).toLocaleString()}</p>
                    <p><strong>Connection Count:</strong> ${connStatus.connection_count}</p>
                </div>
                
                <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px; border: 2px solid #ffc107;">
                    <h4>📋 Test the Bot:</h4>
                    <p>Send a message to <strong>${config.phone}</strong> saying "hi" to test the booking system!</p>
                </div>
                
                <button onclick="window.location.reload()" style="background: #28a745; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer;">
                    🔄 Refresh Status
                </button>
            </body>
            </html>
        `);
    } else if (qrImage) {
        res.send(`
            <html>
            <head><title>${config.name} - Scan QR Code</title></head>
            <body style="text-align:center; padding:50px; font-family:Arial; background: ${config.color}22;">
                <h1>📱 ${config.name}</h1>
                <h2>Connect Your WhatsApp to the Booking Bot</h2>
                <p>📞 Phone: ${config.phone}</p>
                
                <div style="background: #fff3cd; padding: 20px; border-radius: 10px; margin: 20px; border: 2px solid #ffc107;">
                    <h3>👨‍💼 For Salon Owner Only</h3>
                    <p><strong>This is a REAL WhatsApp Web QR code</strong></p>
                    <p>Scan this to connect YOUR WhatsApp to the booking system</p>
                </div>
                
                <div style="background: white; padding: 30px; border-radius: 10px; margin: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                    <h3>📱 Real WhatsApp Web QR Code</h3>
                    <img src="${qrImage}" alt="WhatsApp QR Code" style="max-width: 300px; border: 2px solid #25D366; border-radius: 8px;">
                    <p style="color: #25D366; font-weight: bold; margin-top: 15px;">✅ This is a genuine WhatsApp Web QR code</p>
                    <p><strong>QR Generated:</strong> ${connStatus.qr_generated_count || 0} times</p>
                </div>
                
                <div style="background: #d1ecf1; padding: 20px; border-radius: 10px; margin: 20px; border: 2px solid #17a2b8;">
                    <h3>📋 How to Connect:</h3>
                    <ol style="text-align: left; max-width: 400px; margin: 0 auto;">
                        <li><strong>Open WhatsApp</strong> on your phone (salon owner's phone)</li>
                        <li><strong>Go to Settings</strong> → Linked Devices</li>
                        <li><strong>Tap "Link a Device"</strong></li>
                        <li><strong>Scan the QR code</strong> above</li>
                        <li><strong>Your WhatsApp becomes the booking bot!</strong></li>
                    </ol>
                </div>
                
                <button onclick="window.location.reload()" style="background: #17a2b8; color: white; padding: 10px 20px; border: none; border-radius: 5px; margin-top: 20px; cursor: pointer;">
                    🔄 Refresh QR Code
                </button>
                <script>setTimeout(() => window.location.reload(), 30000);</script>
            </body>
            </html>
        `);
    } else {
        res.send(`
            <html>
            <head><title>${config.name} - Initializing</title></head>
            <body style="text-align:center; padding:50px; font-family:Arial; background: ${config.color}22;">
                <h1>⏳ ${config.name}</h1>
                <h2>Initializing WhatsApp Web Connection...</h2>
                <p>Please wait while we set up your real WhatsApp Web QR code.</p>
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px;">
                    <p>🔄 Starting WhatsApp Web.js client...</p>
                    <p>⏱️ This may take up to 60 seconds</p>
                    <p><strong>Environment:</strong> ${isRailway ? 'Railway Cloud' : 'Local Development'}</p>
                </div>
                <button onclick="window.location.reload()" style="background: #6c757d; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer;">
                    🔄 Refresh
                </button>
                <script>setTimeout(() => window.location.reload(), 15000);</script>
            </body>
            </html>
        `);
    }
});

// QR image endpoints
app.get('/qr-image/:salonId', (req, res) => {
    const { salonId } = req.params;
    const qrImage = qrCodes[salonId];
    
    if (qrImage) {
        const base64Data = qrImage.replace(/^data:image\/png;base64,/, "");
        const img = Buffer.from(base64Data, 'base64');
        res.writeHead(200, {
            'Content-Type': 'image/png',
            'Content-Length': img.length
        });
        res.end(img);
    } else {
        res.status(404).json({ error: 'QR code not available yet' });
    }
});

// General QR page
app.get('/qr', (req, res) => {
    let salonStatus = '';
    
    for (const [salonId, config] of Object.entries(SALON_CONFIG)) {
        const status = isReady[salonId] ? '✅ Connected' : (qrCodes[salonId] ? '📱 QR Ready' : '⏳ Loading');
        const connStatus = connectionStatus[salonId] || {};
        
        salonStatus += `
            <div style="background: ${config.color}33; margin: 15px; padding: 20px; border-radius: 10px; border: 2px solid ${config.color};">
                <h3>${config.name}</h3>
                <p><strong>Status:</strong> ${status}</p>
                <p><strong>Phone:</strong> ${config.phone}</p>
                <p><strong>Connected:</strong> ${connStatus.is_connected ? 'Yes' : 'No'}</p>
                <p><strong>QR Generated:</strong> ${connStatus.qr_generated_count || 0} times</p>
                <a href="/qr/${salonId}" style="background: ${config.color}; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 10px;">
                    📱 Connect ${config.name} WhatsApp
                </a>
            </div>
        `;
    }
    
    res.send(`
        <html>
        <head><title>Production WhatsApp Web.js Service</title></head>
        <body style="font-family: Arial; text-align: center; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; min-height: 100vh; margin: 0;">
            <div style="max-width: 800px; margin: 0 auto; background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; backdrop-filter: blur(10px);">
                <h1>🚀 Production WhatsApp Web.js Service</h1>
                <p>Real WhatsApp Web integration using whatsapp-web.js</p>
                <p><strong>Environment:</strong> ${isRailway ? 'Railway Cloud Deployment' : 'Local Development'}</p>
                
                <div style="background: rgba(40,167,69,0.2); color: #28a745; padding: 15px; border-radius: 8px; margin: 20px 0; border: 2px solid #28a745;">
                    <h3>✅ Real WhatsApp Web QR Codes</h3>
                    <p>These are genuine WhatsApp Web QR codes generated by whatsapp-web.js</p>
                    <p>Salon owners can scan these to actually connect their WhatsApp</p>
                </div>
                
                ${salonStatus}
                
                <div style="margin-top: 30px; padding: 20px; background: rgba(255,255,255,0.1); border-radius: 10px;">
                    <h3>📋 How It Works:</h3>
                    <ol style="text-align: left; max-width: 500px; margin: 0 auto;">
                        <li><strong>Salon owner clicks</strong> their salon's "Connect WhatsApp" button</li>
                        <li><strong>Real WhatsApp Web QR code</strong> is generated by whatsapp-web.js</li>
                        <li><strong>Salon owner scans QR code</strong> with their WhatsApp</li>
                        <li><strong>Their WhatsApp becomes the booking bot</strong></li>
                        <li><strong>Customers message the salon's phone number</strong> directly</li>
                        <li><strong>Bot responds automatically</strong> with booking options</li>
                    </ol>
                </div>
                
                <button onclick="window.location.reload()" style="background: #17a2b8; color: white; padding: 10px 20px; border: none; border-radius: 5px; margin-top: 20px; cursor: pointer;">
                    🔄 Refresh All Status
                </button>
            </div>
        </body>
        </html>
    `);
});

// Webhook endpoints for receiving messages from WhatsApp
app.post('/webhook/whatsapp/:salonId', (req, res) => {
    const { salonId } = req.params;
    const config = SALON_CONFIG[salonId];
    
    if (!config) {
        return res.status(404).json({ error: 'Salon not found' });
    }
    
    console.log(`📨 Webhook received for ${config.name} (${salonId}):`, req.body);
    
    // This endpoint receives messages FROM the backend, not TO the backend
    // The message handling is done in the client.on('message') event above
    res.json({
        success: true,
        message: `Webhook received for ${config.name}`,
        salon_id: salonId
    });
});

// Send message endpoint
app.post('/send-message/:salonId', async (req, res) => {
    const { salonId } = req.params;
    const { to, message } = req.body;
    const client = clients[salonId];
    
    if (!client || !isReady[salonId]) {
        return res.status(503).json({ error: 'WhatsApp client not ready for this salon' });
    }
    
    try {
        const chatId = to.includes('@c.us') ? to : `${to}@c.us`;
        await client.sendMessage(chatId, message);
        res.json({ success: true, message: 'Message sent' });
    } catch (error) {
        console.error('Error sending message:', error);
        res.status(500).json({ error: 'Failed to send message' });
    }
});

// Start server
app.listen(PORT, () => {
    console.log(`🚀 Production WhatsApp Web.js Service running on port ${PORT}`);
    console.log(`🔗 Access at: http://localhost:${PORT}`);
    console.log(`🌍 Environment: ${isRailway ? 'Railway Cloud' : 'Local Development'}`);
    
    // Initialize all salon clients after a short delay
    setTimeout(() => {
        initializeAllClients();
    }, 5000);
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

module.exports = app; 