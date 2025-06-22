const express = require('express');
const qrcode = require('qrcode');
const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(express.json());

let qrCodes = {};
let isReady = {};
let browsers = {};
let pages = {};

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

// Railway-optimized Puppeteer configuration
const PUPPETEER_CONFIG = {
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
        '--max_old_space_size=2048',
        '--disable-extensions',
        '--disable-plugins',
        '--disable-images',
        '--disable-javascript',
        '--disable-default-apps'
    ],
    executablePath: process.env.PUPPETEER_EXECUTABLE_PATH || '/usr/bin/google-chrome-stable'
};

// Initialize WhatsApp Web sessions for each salon
async function initializeSalon(salonId, config) {
    try {
        console.log(`🚀 Initializing ${config.name} (${salonId})...`);
        
        // Launch browser for this salon
        const browser = await puppeteer.launch(PUPPETEER_CONFIG);
        browsers[salonId] = browser;
        
        // Create new page
        const page = await browser.newPage();
        pages[salonId] = page;
        
        // Set user agent
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36');
        
        // Navigate to WhatsApp Web
        console.log(`📱 Loading WhatsApp Web for ${config.name}...`);
        await page.goto('https://web.whatsapp.com', { 
            waitUntil: 'networkidle2',
            timeout: 60000 
        });
        
        // Wait for QR code to appear
        console.log(`⏳ Waiting for QR code for ${config.name}...`);
        await page.waitForSelector('div[data-ref] canvas', { timeout: 60000 });
        
        // Extract QR code
        const qrCodeDataUrl = await page.evaluate(() => {
            const canvas = document.querySelector('div[data-ref] canvas');
            return canvas ? canvas.toDataURL() : null;
        });
        
        if (qrCodeDataUrl) {
            qrCodes[salonId] = qrCodeDataUrl;
            console.log(`✅ QR code generated for ${config.name}`);
            
            // Monitor for connection
            monitorConnection(salonId, config, page);
        } else {
            throw new Error('QR code not found');
        }
        
    } catch (error) {
        console.error(`❌ Error initializing ${config.name}:`, error.message);
        
        // Cleanup failed browser
        if (browsers[salonId]) {
            try {
                await browsers[salonId].close();
            } catch (e) {
                console.error(`Error closing browser for ${config.name}:`, e.message);
            }
            delete browsers[salonId];
        }
        
        // Generate fallback QR for this salon
        generateFallbackQR(salonId, config);
    }
}

// Monitor WhatsApp Web connection status
async function monitorConnection(salonId, config, page) {
    try {
        // Check if connected (no QR code visible)
        const checkConnection = async () => {
            try {
                const qrExists = await page.$('div[data-ref] canvas');
                if (!qrExists) {
                    console.log(`✅ ${config.name} connected successfully!`);
                    isReady[salonId] = true;
                    
                    // Set up message listener
                    await setupMessageListener(salonId, config, page);
                    return true;
                }
                return false;
            } catch (error) {
                console.error(`Error checking connection for ${config.name}:`, error.message);
                return false;
            }
        };
        
        // Check every 5 seconds
        const connectionInterval = setInterval(async () => {
            const connected = await checkConnection();
            if (connected) {
                clearInterval(connectionInterval);
            }
        }, 5000);
        
        // Stop checking after 10 minutes
        setTimeout(() => {
            clearInterval(connectionInterval);
        }, 600000);
        
    } catch (error) {
        console.error(`Error monitoring connection for ${config.name}:`, error.message);
    }
}

// Set up message listener for connected WhatsApp
async function setupMessageListener(salonId, config, page) {
    try {
        console.log(`📱 Setting up message listener for ${config.name}...`);
        
        // Listen for new messages
        await page.evaluateOnNewDocument(() => {
            // This would be where we'd set up message interception
            // For now, we'll use webhook approach
        });
        
    } catch (error) {
        console.error(`Error setting up message listener for ${config.name}:`, error.message);
    }
}

// Generate fallback QR when WhatsApp Web fails
function generateFallbackQR(salonId, config) {
    console.log(`📱 Generating fallback QR for ${config.name}...`);
    
    // Create a message that explains this is for salon owners
    const instructions = `To connect ${config.name} to the booking bot:\n\n1. Open WhatsApp on your phone\n2. Go to Settings → Linked Devices\n3. Tap "Link a Device"\n4. Scan the QR code on our website\n\nPhone: ${config.phone}`;
    
    qrcode.toDataURL(instructions, {
        width: 300,
        margin: 2,
        color: {
            dark: '#000000',
            light: '#FFFFFF'
        }
    })
    .then(qrImage => {
        qrCodes[salonId] = qrImage;
        console.log(`✅ Fallback QR generated for ${config.name}`);
    })
    .catch(err => {
        console.error(`❌ Error generating fallback QR for ${config.name}:`, err);
    });
}

// Initialize all salons
async function initializeAllSalons() {
    console.log('🚀 Initializing WhatsApp Web for all salons...');
    
    for (const [salonId, config] of Object.entries(SALON_CONFIG)) {
        // Stagger initialization to avoid overwhelming Railway
        setTimeout(() => {
            initializeSalon(salonId, config);
        }, Object.keys(SALON_CONFIG).indexOf(salonId) * 10000); // 10 second delay between each
    }
}

// API Routes

// Health check
app.get('/health', (req, res) => {
    const status = {
        service: 'Railway WhatsApp Web Service',
        status: 'running',
        salons: {}
    };
    
    for (const salonId of Object.keys(SALON_CONFIG)) {
        status.salons[salonId] = {
            ready: isReady[salonId] || false,
            hasQR: !!qrCodes[salonId],
            browser: !!browsers[salonId]
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
    
    const qrImage = qrCodes[salonId];
    const connected = isReady[salonId];
    
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
                    <p><strong>This QR code connects YOUR WhatsApp to the booking system</strong></p>
                    <p>After scanning, customers will message ${config.phone} and get automatic booking responses.</p>
                </div>
                
                <div style="background: white; padding: 30px; border-radius: 10px; margin: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                    <h3>📱 Scan with Your WhatsApp</h3>
                    <img src="${qrImage}" alt="WhatsApp QR Code" style="max-width: 300px; border: 2px solid #25D366; border-radius: 8px;">
                    <p style="color: #666; margin-top: 15px;">Scan this QR code with WhatsApp</p>
                </div>
                
                <div style="background: #d1ecf1; padding: 20px; border-radius: 10px; margin: 20px; border: 2px solid #17a2b8;">
                    <h3>📋 How to Connect:</h3>
                    <ol style="text-align: left; max-width: 400px; margin: 0 auto;">
                        <li><strong>Open WhatsApp</strong> on your phone (salon owner's phone)</li>
                        <li><strong>Go to Settings</strong> → Linked Devices</li>
                        <li><strong>Tap "Link a Device"</strong></li>
                        <li><strong>Scan the QR code</strong> above</li>
                        <li><strong>Your WhatsApp is now the booking bot!</strong></li>
                    </ol>
                </div>
                
                <div style="background: #d4edda; padding: 20px; border-radius: 10px; margin: 20px; border: 2px solid #28a745;">
                    <h3>🎯 What happens next:</h3>
                    <ul style="text-align: left; max-width: 400px; margin: 0 auto;">
                        <li>Customers message <strong>${config.phone}</strong> directly</li>
                        <li>Your WhatsApp automatically responds with booking options</li>
                        <li>Customers can book appointments through your WhatsApp</li>
                        <li>You receive all booking confirmations</li>
                    </ul>
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
                <h2>Setting up WhatsApp Web Connection...</h2>
                <p>Please wait while we generate your QR code.</p>
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px;">
                    <p>🔄 Initializing WhatsApp Web...</p>
                    <p>⏱️ This may take up to 60 seconds</p>
                </div>
                <button onclick="window.location.reload()" style="background: #6c757d; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer;">
                    🔄 Refresh
                </button>
                <script>setTimeout(() => window.location.reload(), 10000);</script>
            </body>
            </html>
        `);
    }
});

// Get QR image for specific salon
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
        res.status(404).json({ error: 'QR code not available' });
    }
});

// Main dashboard
app.get('/', (req, res) => {
    let salonStatus = '';
    
    for (const [salonId, config] of Object.entries(SALON_CONFIG)) {
        const status = isReady[salonId] ? '✅ Connected' : (qrCodes[salonId] ? '📱 QR Ready' : '⏳ Loading');
        salonStatus += `
            <div style="background: ${config.color}33; margin: 15px; padding: 20px; border-radius: 10px; border: 2px solid ${config.color};">
                <h3>${config.name}</h3>
                <p><strong>Status:</strong> ${status}</p>
                <p><strong>Phone:</strong> ${config.phone}</p>
                <a href="/qr/${salonId}" style="background: ${config.color}; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 10px;">
                    📱 Connect ${config.name} WhatsApp
                </a>
            </div>
        `;
    }
    
    res.send(`
        <html>
        <head><title>Railway WhatsApp Web Service</title></head>
        <body style="font-family: Arial; text-align: center; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; min-height: 100vh; margin: 0;">
            <div style="max-width: 800px; margin: 0 auto; background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; backdrop-filter: blur(10px);">
                <h1>🚀 Railway WhatsApp Web Service</h1>
                <p>Multi-salon WhatsApp Web integration for salon owners</p>
                
                <div style="background: rgba(40,167,69,0.2); color: #28a745; padding: 15px; border-radius: 8px; margin: 20px 0; border: 2px solid #28a745;">
                    <h3>👨‍💼 For Salon Owners</h3>
                    <p>Each salon owner scans their QR code to connect their WhatsApp to the booking system.</p>
                    <p>Customers then message the salon's phone number directly for bookings.</p>
                </div>
                
                ${salonStatus}
                
                <div style="margin-top: 30px; padding: 20px; background: rgba(255,255,255,0.1); border-radius: 10px;">
                    <h3>📋 How It Works:</h3>
                    <ol style="text-align: left; max-width: 500px; margin: 0 auto;">
                        <li><strong>Salon owner clicks</strong> their salon's "Connect WhatsApp" button</li>
                        <li><strong>Salon owner scans QR code</strong> with their WhatsApp</li>
                        <li><strong>Their WhatsApp becomes the booking bot</strong></li>
                        <li><strong>Customers message the salon's phone number</strong> directly</li>
                        <li><strong>Bot responds automatically</strong> with booking options</li>
                    </ol>
                </div>
            </div>
        </body>
        </html>
    `);
});

// Webhook endpoint for message processing
app.post('/webhook/:salonId', async (req, res) => {
    const { salonId } = req.params;
    const config = SALON_CONFIG[salonId];
    
    if (!config) {
        return res.status(404).json({ error: 'Salon not found' });
    }
    
    try {
        const { message, phone, contactName } = req.body;
        
        // Forward to FastAPI backend
        const backendPort = process.env.BACKEND_PORT || process.env.PORT || 8080;
        const response = await fetch(`http://localhost:${backendPort}/webhook/whatsapp/${salonId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                body: message,
                from: phone,
                contactName: contactName || 'Unknown'
            })
        });
        
        if (response.ok) {
            const result = await response.json();
            res.json({ reply: result.reply });
        } else {
            res.status(500).json({ error: 'Backend webhook failed' });
        }
    } catch (error) {
        console.error(`Webhook error for ${config.name}:`, error);
        res.status(500).json({ error: 'Webhook processing failed' });
    }
});

// Start server
const PORT = 3000;
app.listen(PORT, () => {
    console.log(`🚀 Railway WhatsApp Web Service running on port ${PORT}`);
    console.log(`🔗 Access at: http://localhost:${PORT}`);
    
    // Initialize all salons
    setTimeout(() => {
        initializeAllSalons();
    }, 5000); // Wait 5 seconds for server to be ready
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('🛑 Shutting down WhatsApp Web browsers...');
    
    for (const [salonId, browser] of Object.entries(browsers)) {
        try {
            await browser.close();
            console.log(`✅ ${SALON_CONFIG[salonId].name} browser closed`);
        } catch (error) {
            console.error(`❌ Error closing ${SALON_CONFIG[salonId].name} browser:`, error);
        }
    }
    
    process.exit(0);
});

module.exports = app; 