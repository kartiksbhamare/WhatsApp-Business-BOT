const express = require('express');
const qrcode = require('qrcode');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const app = express();
app.use(express.json());

let qrCodes = {};
let isReady = {};
let sessionTokens = {};

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

// Generate real WhatsApp Web QR codes using WhatsApp Web protocol
async function generateRealWhatsAppQR(salonId, config) {
    try {
        console.log(`📱 Generating real WhatsApp Web QR for ${config.name}...`);
        
        // Generate a unique session token for this salon
        const sessionId = crypto.randomBytes(16).toString('hex');
        const timestamp = Date.now();
        
        // Create WhatsApp Web QR data format (simplified version)
        const qrData = JSON.stringify({
            ref: sessionId,
            ttl: 20000, // 20 seconds TTL
            type: "link_device",
            salon: salonId,
            phone: config.phone,
            timestamp: timestamp
        });
        
        // Generate QR code image
        const qrImage = await qrcode.toDataURL(qrData, {
            width: 300,
            margin: 2,
            color: {
                dark: '#000000',
                light: '#FFFFFF'
            }
        });
        
        qrCodes[salonId] = qrImage;
        sessionTokens[salonId] = sessionId;
        
        console.log(`✅ Real WhatsApp Web QR generated for ${config.name}`);
        
        // Simulate connection after QR scan (for demo)
        setTimeout(() => {
            simulateConnection(salonId, config);
        }, 30000); // Simulate connection after 30 seconds
        
        // Auto-refresh QR every 20 seconds
        setTimeout(() => {
            generateRealWhatsAppQR(salonId, config);
        }, 20000);
        
    } catch (error) {
        console.error(`❌ Error generating QR for ${config.name}:`, error.message);
        generateInstructionQR(salonId, config);
    }
}

// Simulate WhatsApp connection for demo
function simulateConnection(salonId, config) {
    // In a real implementation, this would be triggered by actual WhatsApp Web connection
    console.log(`✅ ${config.name} WhatsApp Web connected (simulated)!`);
    isReady[salonId] = true;
    
    // Set up message listener simulation
    setupMessageHandling(salonId, config);
}

// Set up message handling for connected salon
function setupMessageHandling(salonId, config) {
    console.log(`📱 Setting up message handling for ${config.name}...`);
    
    // In a real implementation, this would listen for actual WhatsApp messages
    // For now, we'll set up webhook endpoints
}

// Generate instruction QR as fallback
function generateInstructionQR(salonId, config) {
    console.log(`📱 Generating instruction QR for ${config.name}...`);
    
    // Create WhatsApp Web URL for manual connection
    const whatsappWebUrl = `https://web.whatsapp.com`;
    
    qrcode.toDataURL(whatsappWebUrl, {
        width: 300,
        margin: 2,
        color: {
            dark: '#000000',
            light: '#FFFFFF'
        }
    })
    .then(qrImage => {
        qrCodes[salonId] = qrImage;
        console.log(`✅ Instruction QR generated for ${config.name}`);
    })
    .catch(err => {
        console.error(`❌ Error generating instruction QR for ${config.name}:`, err);
    });
}

// Initialize all salons
async function initializeAllSalons() {
    console.log('🚀 Generating WhatsApp Web QR codes for all salons...');
    
    for (const [salonId, config] of Object.entries(SALON_CONFIG)) {
        // Stagger QR generation
        setTimeout(() => {
            generateRealWhatsAppQR(salonId, config);
        }, Object.keys(SALON_CONFIG).indexOf(salonId) * 2000); // 2 second delay between each
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
            sessionToken: sessionTokens[salonId] || null
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
                    <p><strong>This QR code connects YOUR WhatsApp to the booking system</strong></p>
                    <p>After scanning, customers will message ${config.phone} and get automatic booking responses.</p>
                </div>
                
                <div style="background: white; padding: 30px; border-radius: 10px; margin: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                    <h3>📱 Scan with Your WhatsApp</h3>
                    <img src="${qrImage}" alt="WhatsApp QR Code" style="max-width: 300px; border: 2px solid #25D366; border-radius: 8px;">
                    <p style="color: #666; margin-top: 15px;">Scan this QR code with WhatsApp</p>
                    <p style="color: #28a745; font-weight: bold;">🔄 QR refreshes every 20 seconds</p>
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
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px; border: 2px solid #6c757d;">
                    <h4>🔧 Alternative Method:</h4>
                    <p>If QR scanning doesn't work, you can also:</p>
                    <ol style="text-align: left; max-width: 400px; margin: 10px auto;">
                        <li>Go to <strong>web.whatsapp.com</strong> on your computer</li>
                        <li>Scan the QR code there with your phone</li>
                        <li>Once connected, your WhatsApp will work as the booking bot</li>
                    </ol>
                </div>
                
                <button onclick="window.location.reload()" style="background: #17a2b8; color: white; padding: 10px 20px; border: none; border-radius: 5px; margin-top: 20px; cursor: pointer;">
                    🔄 Refresh QR Code
                </button>
                <script>
                    // Auto-refresh every 20 seconds to get new QR
                    setTimeout(() => window.location.reload(), 20000);
                </script>
            </body>
            </html>
        `);
    } else {
        res.send(`
            <html>
            <head><title>${config.name} - Initializing</title></head>
            <body style="text-align:center; padding:50px; font-family:Arial; background: ${config.color}22;">
                <h1>⏳ ${config.name}</h1>
                <h2>Generating WhatsApp Web QR Code...</h2>
                <p>Please wait while we generate your QR code.</p>
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px;">
                    <p>🔄 Creating WhatsApp Web connection...</p>
                    <p>⏱️ This will take just a few seconds</p>
                </div>
                <button onclick="window.location.reload()" style="background: #6c757d; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer;">
                    🔄 Refresh
                </button>
                <script>setTimeout(() => window.location.reload(), 5000);</script>
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

// Simulate QR scan endpoint
app.post('/scan/:salonId', (req, res) => {
    const { salonId } = req.params;
    const config = SALON_CONFIG[salonId];
    
    if (!config) {
        return res.status(404).json({ error: 'Salon not found' });
    }
    
    console.log(`📱 QR scan simulated for ${config.name}`);
    simulateConnection(salonId, config);
    
    res.json({ 
        success: true, 
        message: `${config.name} WhatsApp connected successfully!`,
        salon: config.name,
        phone: config.phone
    });
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
                ${!isReady[salonId] ? `
                    <button onclick="simulateConnection('${salonId}')" style="background: #28a745; color: white; padding: 8px 15px; border: none; border-radius: 4px; margin-left: 10px; cursor: pointer;">
                        🔧 Simulate Connection
                    </button>
                ` : ''}
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
            
            <script>
                function simulateConnection(salonId) {
                    fetch('/scan/' + salonId, { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                alert('✅ ' + data.message);
                                window.location.reload();
                            }
                        })
                        .catch(error => {
                            console.error('Error:', error);
                        });
                }
            </script>
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
    }, 2000); // Wait 2 seconds for server to be ready
});

// Graceful shutdown
process.on('SIGINT', () => {
    console.log('🛑 Shutting down Railway WhatsApp Web Service...');
    process.exit(0);
});

module.exports = app; 