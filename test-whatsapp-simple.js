const express = require('express');

console.log('🧪 Testing WhatsApp service startup...');

// Test 1: Check if express works
console.log('✅ Express loaded');

// Test 2: Try to start a simple server on port 3005
const app = express();

app.get('/test', (req, res) => {
    res.json({ status: 'test server working' });
});

console.log('🚀 Attempting to start test server on port 3005...');

const server = app.listen(3005, (err) => {
    if (err) {
        console.error('❌ Failed to start server on port 3005:', err);
        process.exit(1);
    } else {
        console.log('✅ Test server started on port 3005');
        
        // Test 3: Try to load WhatsApp Web.js
        try {
            const { Client, LocalAuth } = require('whatsapp-web.js');
            console.log('✅ WhatsApp Web.js loaded successfully');
            
            // Test 4: Try to create a client (without initializing)
            const client = new Client({
                authStrategy: new LocalAuth({ clientId: 'test-client' }),
                puppeteer: {
                    headless: true,
                    args: [
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--single-process'
                    ],
                    executablePath: process.env.CHROME_BIN || '/usr/bin/google-chrome'
                }
            });
            console.log('✅ WhatsApp client created successfully');
            
            setTimeout(() => {
                console.log('🎯 All tests passed! WhatsApp service should work.');
                server.close();
                process.exit(0);
            }, 2000);
            
        } catch (error) {
            console.error('❌ WhatsApp Web.js error:', error);
            server.close();
            process.exit(1);
        }
    }
});

server.on('error', (err) => {
    console.error('❌ Server error:', err);
    process.exit(1);
}); 