// Use native fetch in Node.js 18+
const fetch = globalThis.fetch || require('node-fetch');

async function testAllEndpoints() {
  const baseUrl = 'http://localhost:3000';

  // Test data
  const agents = [
    { id: '607906784857817088', name: 'ADK Agent' },
    { id: '5846085732698947584', name: 'Demo Agent' }
  ];

  const endpoints = [
    { path: '/api/agent-engine', name: 'Main Endpoint (with class_method)' },
    { path: '/api/agent-engine-stream', name: 'Streaming Endpoint (with class_method)' },
    { path: '/api/agent-engine-correct', name: 'Correct Format Endpoint' },
    { path: '/api/agent-engine-python', name: 'Python Fallback' }
  ];

  console.log('=' .repeat(60));
  console.log('Testing All Agent Engine Endpoints');
  console.log('=' .repeat(60));

  for (const agent of agents) {
    console.log(`\n\nAgent: ${agent.name} (${agent.id})`);
    console.log('-'.repeat(60));

    for (const endpoint of endpoints) {
      console.log(`\nTesting: ${endpoint.name}`);
      console.log(`Endpoint: ${endpoint.path}`);

      try {
        const response = await fetch(`${baseUrl}${endpoint.path}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: 'hello, what is 2+2?',
            agentId: agent.id
          }),
          timeout: 10000 // 10 second timeout
        });

        const data = await response.json();

        if (data.success || data.response) {
          console.log(`✅ SUCCESS`);
          if (data.response) {
            const preview = data.response.substring(0, 100);
            console.log(`   Response: ${preview}${data.response.length > 100 ? '...' : ''}`);
          }
          if (data.sessionId) {
            console.log(`   Session: ${data.sessionId}`);
          }
        } else {
          console.log(`❌ FAILED`);
          console.log(`   Error: ${data.error || 'No response'}`);
          if (data.details) {
            const details = data.details.substring(0, 100);
            console.log(`   Details: ${details}${data.details.length > 100 ? '...' : ''}`);
          }
        }
      } catch (error) {
        console.log(`❌ ERROR`);
        console.log(`   ${error.message}`);
      }
    }
  }

  console.log('\n' + '='.repeat(60));
  console.log('Test Complete');
  console.log('='.repeat(60));
}

// Check if server is running
console.log('Checking if server is running...');
fetch('http://localhost:3000/api/agents')
  .then(() => {
    console.log('✅ Server is running\n');
    testAllEndpoints();
  })
  .catch(() => {
    console.log('❌ Server is not running');
    console.log('Please start the server with: npm run dev');
  });