const axios = require('axios');

// Test configuration
const SALON_PORTS = {
    salon_a: 3005,
    salon_b: 3006,
    salon_c: 3007
};

const SALON_NAMES = {
    salon_a: 'Downtown Beauty Salon',
    salon_b: 'Uptown Hair Studio',
    salon_c: 'Luxury Spa & Salon'
};

async function testSalonService(salonId, port) {
    console.log(`\n🧪 Testing ${SALON_NAMES[salonId]} on port ${port}...`);
    
    try {
        // Test health endpoint
        const healthResponse = await axios.get(`http://localhost:${port}/health`, { timeout: 5000 });
        console.log(`✅ Health check: ${healthResponse.data.status}`);
        console.log(`   Salon: ${healthResponse.data.salon}`);
        console.log(`   Connection: ${healthResponse.data.connection_status.is_connected ? 'Connected' : 'Not Connected'}`);
        
        // Test info endpoint
        const infoResponse = await axios.get(`http://localhost:${port}/info`, { timeout: 5000 });
        console.log(`✅ Service info: ${infoResponse.data.status}`);
        console.log(`   QR Available: ${infoResponse.data.qr_available ? 'Yes' : 'No'}`);
        
        // Test connection status
        const statusResponse = await axios.get(`http://localhost:${port}/connection-status`, { timeout: 5000 });
        console.log(`✅ Connection status: ${statusResponse.data.current_status}`);
        console.log(`   Phone: ${statusResponse.data.phone_number || 'Not connected'}`);
        
        return true;
    } catch (error) {
        console.log(`❌ Error testing ${SALON_NAMES[salonId]}: ${error.message}`);
        return false;
    }
}

async function testAllSalons() {
    console.log('🚀 Testing Unified Multi-Salon WhatsApp Service');
    console.log('=' .repeat(60));
    
    let successCount = 0;
    const totalSalons = Object.keys(SALON_PORTS).length;
    
    for (const [salonId, port] of Object.entries(SALON_PORTS)) {
        const success = await testSalonService(salonId, port);
        if (success) successCount++;
        
        // Wait a bit between tests
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    console.log('\n📊 Test Results:');
    console.log('=' .repeat(60));
    console.log(`✅ Successful: ${successCount}/${totalSalons} salons`);
    console.log(`❌ Failed: ${totalSalons - successCount}/${totalSalons} salons`);
    
    if (successCount === totalSalons) {
        console.log('\n🎉 All salons are running successfully!');
        console.log('\n🔗 QR Code URLs:');
        Object.entries(SALON_PORTS).forEach(([salonId, port]) => {
            console.log(`   🏢 ${SALON_NAMES[salonId]}: http://localhost:${port}/qr`);
        });
    } else {
        console.log('\n⚠️ Some salons failed to start. Check the unified service logs.');
    }
    
    return successCount === totalSalons;
}

// Run the test
if (require.main === module) {
    testAllSalons()
        .then(success => {
            process.exit(success ? 0 : 1);
        })
        .catch(error => {
            console.error('❌ Test failed:', error.message);
            process.exit(1);
        });
}

module.exports = { testAllSalons, testSalonService }; 