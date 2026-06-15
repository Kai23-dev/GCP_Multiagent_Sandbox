#!/usr/bin/env node

/**
 * Test script to get agent details and understand their configuration
 */

const { GoogleAuth } = require('google-auth-library');

async function testAgentDetails() {
  const projectId = process.env.GOOGLE_CLOUD_PROJECT || 'agentspace-prod-w89w';
  const location = process.env.GOOGLE_CLOUD_LOCATION || 'us-central1';

  // Test all agents
  const agents = [
    { id: '607906784857817088', name: 'A demo ADK Agent' },
    { id: '5846085732698947584', name: 'Demo Agent' },
    { id: '2701781544422342656', name: 'my-agent' },
    { id: '8178176283490910208', name: 'A demo ADK Agent (2)' }
  ];

  // Use ADC for authentication
  const googleAuth = new GoogleAuth({
    scopes: ['https://www.googleapis.com/auth/cloud-platform']
  });

  const client = await googleAuth.getClient();
  const accessToken = await client.getAccessToken();

  if (!accessToken.token) {
    throw new Error('Failed to get access token from ADC');
  }

  const headers = {
    'Authorization': `Bearer ${accessToken.token}`,
    'Content-Type': 'application/json',
  };

  console.log('Using ADC authentication\n');

  for (const agent of agents) {
    console.log(`\n=== ${agent.name} (${agent.id}) ===`);

    const agentResourceName = `projects/${projectId}/locations/${location}/reasoningEngines/${agent.id}`;
    const agentUrl = `https://${location}-aiplatform.googleapis.com/v1beta1/${agentResourceName}`;

    try {
      // Get agent details
      const response = await fetch(agentUrl, {
        method: 'GET',
        headers
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Framework:', data.spec?.agentFramework || 'unknown');

        // Check for class methods
        const classMethods = data.spec?.packageSpec?.agentClass?.classMethods || [];
        if (classMethods.length > 0) {
          console.log('Class methods:');
          classMethods.forEach(m => console.log(`  - ${m.name}`));
        }

        // Check for operation schemas
        const operationSchemas = data.operationSchemas || [];
        if (operationSchemas.length > 0) {
          console.log('Operation schemas:');
          operationSchemas.forEach(s => console.log(`  - ${s.name}`));
        }

        // Try a simple query
        console.log('\nTrying query endpoint...');
        const queryUrl = `${agentUrl}:query`;

        // When Python SDK calls agent.query(input="hi"), it likely becomes:
        // The "input" parameter is the key, and the value is our message
        const formats = [
          { name: 'direct text', body: { input: "hi" } },
          { name: 'wrapped input', body: { input: { input: "hi" } } },
          { name: 'empty input', body: { input: {} } }
        ];

        for (const format of formats) {
          console.log(`  Trying ${format.name}:`, JSON.stringify(format.body));
          const queryResponse = await fetch(queryUrl, {
            method: 'POST',
            headers,
            body: JSON.stringify(format.body),
          });

          if (queryResponse.ok) {
            console.log('    ✅ SUCCESS!');
            const result = await queryResponse.json();
            console.log('    Response:', JSON.stringify(result, null, 2).substring(0, 200));
            break; // Found working format
          } else {
            const error = await queryResponse.text();
            console.log('    ❌ Failed:', error.substring(0, 100));
          }
        }

      } else {
        console.log('Failed to get agent details:', response.status);
      }
    } catch (error) {
      console.log('Error:', error.message);
    }
  }
}

testAgentDetails().catch(console.error);