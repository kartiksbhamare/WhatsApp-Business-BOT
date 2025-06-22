const express = require('express');
const fs = require('fs');

// Mock WhatsApp service for Railway (no Puppeteer)
const app = express();
const PORT = process.env.PORT || 3000;

console.log('🚀 Starting Mock WhatsApp Service for Railway');

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
    res.json({
        status: 'ready',
        service: 'Mock WhatsApp Service (Railway)',
        timestamp: new Date().toISOString(),
        client_info: {
            wid: { user: '1234567890' },
            platform: 'mock'
        },
        connection_status: connectionStatus
    });
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

// QR code page - shows connected status
app.get('/qr', (req, res) => {
    res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Multi-Salon WhatsApp - Mock Connected</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #e8f5e8; }
                .container { background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.1); max-width: 600px; }
                .success { color: #25D366; }
                .connection-info { background: #f0f8ff; padding: 15px; border-radius: 5px; margin: 20px 0; text-align: left; }
                .mock-notice { background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border: 2px solid #ffc107; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="success">✅ Multi-Salon WhatsApp Ready!</h1>
                
                <div class="mock-notice">
                    <h3>🔧 Development Mode</h3>
                    <p>This is a mock WhatsApp service for Railway deployment. The booking system is fully functional, but WhatsApp integration is simulated.</p>
                </div>
                
                <div class="connection-info">
                    <strong>📋 Service Details:</strong><br>
                    📱 Mode: Mock/Development<br>
                    🕒 Started: ${new Date().toLocaleString()}<br>
                    🎯 Status: All salons ready<br>
                    🔢 Backend: Fully operational
                </div>
                
                <div style="background: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>🏢 Multi-Salon System Active</h3>
                    <p><strong>All 3 salons are operational:</strong></p>
                    <ul style="text-align: left; max-width: 400px; margin: 0 auto;">
                        <li>🏪 Downtown Beauty Salon</li>
                        <li>💇 Uptown Hair Studio</li>
                        <li>✨ Luxury Spa & Salon</li>
                    </ul>
                </div>
                
                <div style="background: #f8d7da; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3>📱 To Enable Real WhatsApp:</h3>
                    <p>Deploy the full WhatsApp service locally or use a dedicated WhatsApp server.</p>
                    <p>This mock service ensures your Railway deployment works perfectly!</p>
                </div>
            </div>
        </body>
        </html>
    `);
});

// Mock QR image endpoint
app.get('/qr-image', (req, res) => {
    res.status(404).json({ 
        error: 'QR code not available in mock mode',
        message: 'Use local development for real WhatsApp integration'
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

// Webhook endpoint for testing
app.post('/webhook', (req, res) => {
    console.log('📨 Mock: Received webhook:', req.body);
    res.json({
        success: true,
        reply: 'Mock response from WhatsApp service'
    });
});

// Start the server
app.listen(PORT, () => {
    console.log(`🚀 Mock WhatsApp service running on port ${PORT}`);
    console.log(`🔗 QR Code URL: http://localhost:${PORT}/qr`);
    console.log(`📋 Health Check: http://localhost:${PORT}/health`);
    console.log('✅ Service ready - Mock mode active');
});

// Graceful shutdown
process.on('SIGINT', () => {
    console.log('\n🛑 Shutting down Mock WhatsApp service...');
    console.log('👋 Service shut down. Goodbye!');
    process.exit(0);
}); 