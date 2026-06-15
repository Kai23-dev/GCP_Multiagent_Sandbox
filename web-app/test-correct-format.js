const fetch = require('node-fetch');

async function testCorrectFormat() {
  const baseUrl = 'http://localhost:3000';

  console.log('Testing Agent Engine with correct ADK format...\n');

  const endpoint = '/api/agent-engine-correct';
  const testData = {
    message: 'hello, what is 2+2?',
    agentId: '5846085732698947584'
  };

  console.log(`Testing ${endpoint}...`);
  console.log(`Agent ID: ${testData.agentId}`);
  console.log(`Message: ${testData.message}\n`);

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
      console.log(`✅ SUCCESS!`);
      console.log(`Response: ${data.response}`);
      console.log(`Session ID: ${data.sessionId}`);
    } else {
      console.log(`❌ FAILED`);
      console.log(`Error: ${data.error || 'Unknown error'}`);
      if (data.details) {
        console.log(`Details: ${data.details}`);
      }
    }
  } catch (error) {
    console.log(`❌ ERROR`);
    console.log(`   ${error.message}`);
  }
}

// Check if server is running
fetch('http://localhost:3000/api/agents')
  .then(() => {
    console.log('Server is running, starting test...\n');
    testCorrectFormat();
  })
  .catch(() => {
    console.log('❌ Server is not running. Please start it with: npm run dev');
  });