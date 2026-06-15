const fetch = require('node-fetch');

async function testEndpoints() {
  const baseUrl = 'http://localhost:3000';
  const testData = {
    message: 'hello, what is 2+2?',
    agentId: '5846085732698947584'
  };

  const endpoints = [
    '/api/agent-engine',
    '/api/agent-engine-v2',
    '/api/agent-engine-python',
    '/api/agent-engine-stream'
  ];

  console.log('Testing Agent Engine endpoints...\n');

  for (const endpoint of endpoints) {
    console.log(`Testing ${endpoint}...`);

    try {
      const response = await fetch(`${baseUrl}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(testData),
      });

      const data = await response.json();

      if (data.success || data.response) {
        console.log(`✅ ${endpoint} - SUCCESS`);
        console.log(`   Response: ${data.response?.substring(0, 100)}...`);
      } else {
        console.log(`❌ ${endpoint} - FAILED`);
        console.log(`   Error: ${data.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.log(`❌ ${endpoint} - ERROR`);
      console.log(`   ${error.message}`);
    }

    console.log('');
  }
}

// Check if server is running
fetch('http://localhost:3000/api/agents')
  .then(() => {
    console.log('Server is running, starting tests...\n');
    testEndpoints();
  })
  .catch(() => {
    console.log('❌ Server is not running. Please start it with: npm run dev');
  });