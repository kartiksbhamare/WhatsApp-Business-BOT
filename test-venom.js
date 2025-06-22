// Simple test script for Venom Bot
const venom = require('venom-bot');

async function testVenomBot() {
    try {
        console.log('🧪 Testing Venom Bot initialization...');
        
        const client = await venom.create(
            'test-session',
            (base64Qr, asciiQR, attempts, urlCode) => {
                console.log('📱 QR Code for testing:');
                console.log(asciiQR);
                console.log('Attempts:', attempts);
                console.log('URL:', urlCode);
            },
            undefined,
            {
                logQR: false,
                headless: true,
                devtools: false,
                useChrome: true,
                debug: false,
                logLevel: 'error'
            }
        );

        console.log('✅ Venom Bot initialized successfully!');
        
        // Get device info
        const deviceInfo = await client.getHostDevice();
        console.log('📱 Device Info:', deviceInfo);

        // Test message sending capability (commented out to avoid sending actual messages)
        /*
        const testNumber = '1234567890@c.us'; // Replace with actual test number
        await client.sendText(testNumber, '🧪 Test message from Venom Bot');
        console.log('✅ Test message sent successfully!');
        */

        console.log('✅ Venom Bot test completed successfully!');
        
        // Close the client
        await client.close();
        process.exit(0);
        
    } catch (error) {
        console.error('❌ Error testing Venom Bot:', error);
        process.exit(1);
    }
}

testVenomBot(); 