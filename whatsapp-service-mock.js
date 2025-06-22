const express = require('express');
const fs = require('fs');

// Mock WhatsApp service for Railway (no Puppeteer)
const app = express();
const PORT = 3000;  // Fixed port 3000 for mock service, not Railway PORT

console.log('🚀 Starting Mock WhatsApp Service for Railway');

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

// Mock connection status
let connectionStatus = {
    is_connected: true,  // Always connected in mock mode
    phone_number: '+1234567890',
    connected_at: new Date().toISOString(),
    last_seen: new Date().toISOString(),
    connection_count: 1,
    qr_generated_count: 0
};

// Express middleware
app.use(express.json());

// Health check
app.get('/health', (req, res) => {
    const status = {
        status: 'ready',
        service: 'Mock WhatsApp Service (Railway)',
        timestamp: new Date().toISOString(),
        client_info: {
            wid: { user: '1234567890' },
            platform: 'mock'
        },
        connection_status: connectionStatus,
        salons: {}
    };
    
    // Add salon status
    for (const salonId of Object.keys(SALON_CONFIG)) {
        status.salons[salonId] = {
            ready: true,
            hasQR: true,
            hasClient: true
        };
    }
    
    res.json(status);
});

// Service info
app.get('/info', (req, res) => {
    res.json({
        service: 'Mock WhatsApp Service (Railway)',
        status: 'ready',
        qr_available: false,  // No QR needed in mock mode
        backend_url: `http://localhost:${PORT}`,
        connection_status: connectionStatus,
        mode: 'mock'
    });
});

// Salon-specific QR code pages
app.get('/qr/:salonId', (req, res) => {
    const { salonId } = req.params;
    const config = SALON_CONFIG[salonId];
    
    if (!config) {
        return res.status(404).json({ error: 'Salon not found' });
    }
    
    res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>${config.name} - Mock Connected</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 30px; background: ${config.color}22; }
                .container { background: white; padding: 30px; border-radius: 15px; display: inline-block; box-shadow: 0 4px 8px rgba(0,0,0,0.1); max-width: 600px; }
                .success { color: #25D366; }
                .mock-notice { background: #fff3cd; padding: 20px; border-radius: 10px; margin: 20px 0; border: 2px solid #ffc107; }
                .salon-info { background: ${config.color}22; padding: 20px; border-radius: 10px; margin: 20px 0; border: 2px solid ${config.color}; }
                .qr-demo { background: #f8f9fa; padding: 30px; border-radius: 10px; margin: 20px 0; border: 2px dashed #6c757d; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="success">✅ ${config.name}</h1>
                <h2>Mock WhatsApp Service Ready!</h2>
                
                <div class="salon-info">
                    <h3>🏪 Salon Information</h3>
                    <p><strong>📱 Phone:</strong> ${config.phone}</p>
                    <p><strong>🆔 Salon ID:</strong> ${salonId}</p>
                    <p><strong>🎯 Status:</strong> Mock Mode Active</p>
                </div>
                
                <div class="mock-notice">
                    <h3>🔧 Development Mode</h3>
                    <p>This is a mock WhatsApp service for Railway deployment.</p>
                    <p>The booking system is fully functional for <strong>${config.name}</strong>!</p>
                </div>
                
                <div class="qr-demo">
                    <h3>📱 QR Code Demo</h3>
                    <div style="width: 200px; height: 200px; background: #f0f0f0; border: 2px dashed #999; margin: 20px auto; display: flex; align-items: center; justify-content: center; border-radius: 10px;">
                        <div style="text-align: center; color: #666;">
                            <div style="font-size: 48px;">📱</div>
                            <div>Demo QR</div>
                            <div style="font-size: 12px;">${config.name}</div>
                        </div>
                    </div>
                    <p><strong>In production:</strong> Real WhatsApp Web QR code would appear here</p>
                </div>
                
                <div style="background: #d4edda; padding: 20px; border-radius: 10px; margin: 20px 0; border: 2px solid #28a745;">
                    <h3>🎉 ${config.name} System Ready!</h3>
                    <p>✅ Backend API connected</p>
                    <p>✅ Database operational</p>
                    <p>✅ Booking system active</p>
                    <p>✅ Salon-specific services loaded</p>
                </div>
                
                <div style="background: #d1ecf1; padding: 20px; border-radius: 10px; margin: 20px 0; border: 2px solid #17a2b8;">
                    <h3>📋 How It Works (Production):</h3>
                    <ol style="text-align: left; max-width: 400px; margin: 0 auto;">
                        <li><strong>Salon owner scans</strong> the real QR code</li>
                        <li><strong>Connects WhatsApp</strong> to ${config.phone}</li>
                        <li><strong>Customers message</strong> ${config.phone}</li>
                        <li><strong>Bot responds</strong> with ${config.name} services</li>
                        <li><strong>Complete booking</strong> for this salon only</li>
                    </ol>
                </div>
                
                <button onclick="window.location.reload()" style="background: ${config.color}; color: white; padding: 15px 30px; border: none; border-radius: 8px; cursor: pointer; font-size: 16px; margin-top: 20px;">
                    🔄 Refresh Status
                </button>
            </div>
        </body>
        </html>
    `);
});

// General QR code page - shows all salons
app.get('/qr', (req, res) => {
    let salonsList = '';
    for (const [salonId, config] of Object.entries(SALON_CONFIG)) {
        salonsList += `
            <div style="background: ${config.color}33; margin: 15px; padding: 20px; border-radius: 10px; border: 2px solid ${config.color};">
                <h3>${config.name}</h3>
                <p><strong>Phone:</strong> ${config.phone}</p>
                <p><strong>Status:</strong> ✅ Mock Ready</p>
                <a href="/qr/${salonId}" style="background: ${config.color}; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 10px;">
                    📱 View ${config.name} QR
                </a>
            </div>
        `;
    }
    
    res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Multi-Salon WhatsApp - Mock Service</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; min-height: 100vh; margin: 0; }
                .container { max-width: 800px; margin: 0 auto; background: rgba(255,255,255,0.1); padding: 30px; border-radius: 15px; backdrop-filter: blur(10px); }
                .mock-notice { background: rgba(255,243,205,0.9); color: #856404; padding: 20px; border-radius: 10px; margin: 20px 0; border: 2px solid #ffc107; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 Multi-Salon WhatsApp Service</h1>
                <h2>Mock Mode for Railway Deployment</h2>
                
                <div class="mock-notice">
                    <h3>🔧 Development Mode Active</h3>
                    <p>This is a mock WhatsApp service running on Railway.</p>
                    <p>All salon booking systems are fully operational!</p>
                </div>
                
                ${salonsList}
                
                <div style="background: rgba(40,167,69,0.2); color: #28a745; padding: 20px; border-radius: 10px; margin: 20px 0; border: 2px solid #28a745;">
                    <h3>✅ All Systems Operational</h3>
                    <p>✅ 3 Salons configured and ready</p>
                    <p>✅ Backend API fully functional</p>
                    <p>✅ Database connected and populated</p>
                    <p>✅ Booking system active for all salons</p>
                </div>
                
                <div style="margin-top: 30px; padding: 20px; background: rgba(255,255,255,0.1); border-radius: 10px;">
                    <h3>📋 Production Deployment:</h3>
                    <p>Deploy with real WhatsApp Web.js for actual QR codes and messaging</p>
                </div>
            </div>
        </body>
        </html>
    `);
});

// Salon-specific QR image endpoints
app.get('/qr-image/:salonId', (req, res) => {
    const { salonId } = req.params;
    const config = SALON_CONFIG[salonId];
    
    if (!config) {
        return res.status(404).json({ error: 'Salon not found' });
    }
    
    res.status(404).json({ 
        error: 'QR image not available in mock mode',
        message: `Use real WhatsApp service for ${config.name} QR codes`,
        salon: config.name
    });
});

// Mock send message endpoint
app.post('/send-message', (req, res) => {
    console.log('📤 Mock: Would send message:', req.body);
    res.json({
        success: true,
        message: 'Message sent (mock)',
        id: 'mock_' + Date.now()
    });
});

// Salon-specific webhook endpoints
app.post('/webhook/whatsapp/:salonId', (req, res) => {
    const { salonId } = req.params;
    const config = SALON_CONFIG[salonId];
    
    if (!config) {
        return res.status(404).json({ error: 'Salon not found' });
    }
    
    console.log(`📨 Mock: Received webhook for ${config.name} (${salonId}):`, req.body);
    
    // Mock response based on message content
    let reply = '';
    const message = req.body.body?.toLowerCase() || '';
    
    if (message.includes('hi') || message.includes('hello')) {
        reply = `🏪 Welcome to ${config.name}!\n\n` +
                `📱 Phone: ${config.phone}\n` +
                `🎯 This is a mock response for testing.\n\n` +
                `In production, you would see:\n` +
                `📋 Available services\n` +
                `👨‍💼 Available barbers\n` +
                `📅 Booking options\n\n` +
                `Type "services" to see what we offer!`;
    } else if (message.includes('service')) {
        reply = `💇‍♀️ ${config.name} Services (Mock):\n\n` +
                `✂️ Haircut - $30\n` +
                `🎨 Hair Color - $80\n` +
                `💆‍♀️ Facial - $50\n` +
                `💅 Manicure - $25\n\n` +
                `Type "book" to make an appointment!`;
    } else {
        reply = `Thank you for contacting ${config.name}!\n\n` +
                `📱 Phone: ${config.phone}\n` +
                `🤖 This is a mock response.\n\n` +
                `Type "hi" to see our welcome message!`;
    }
    
    res.json({
        success: true,
        reply: reply,
        salon_id: salonId,
        salon_name: config.name
    });
});

// General webhook endpoint for backward compatibility
app.post('/webhook', (req, res) => {
    console.log('📨 Mock: Received general webhook:', req.body);
    res.json({
        success: true,
        reply: 'Mock response from WhatsApp service (general endpoint)'
    });
});

// Start the server
app.listen(PORT, () => {
    console.log(`🚀 Mock WhatsApp service running on port ${PORT}`);
    console.log(`🔗 QR Code URL: http://localhost:${PORT}/qr`);
    console.log(`📋 Health Check: http://localhost:${PORT}/health`);
    console.log('✅ Service ready - Mock mode active');
    
    // Log salon-specific endpoints
    console.log('\n📱 Salon-specific endpoints:');
    for (const [salonId, config] of Object.entries(SALON_CONFIG)) {
        console.log(`   ${config.name}: http://localhost:${PORT}/qr/${salonId}`);
    }
});

// Graceful shutdown
process.on('SIGINT', () => {
    console.log('\n🛑 Shutting down Mock WhatsApp service...');
    console.log('👋 Service shut down. Goodbye!');
    process.exit(0);
}); 