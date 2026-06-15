#!/usr/bin/env node

/**
 * Test script to verify ADK agent communication
 * This tests the actual REST API endpoints directly
 */

async function testAgentQuery() {
  const projectId = process.env.GOOGLE_CLOUD_PROJECT || 'agentspace-prod-w89w';
  const location = process.env.GOOGLE_CLOUD_LOCATION || 'us-central1';
  // Let's test the Demo Agent instead since the ADK agent is a session manager
  const agentId = '5846085732698947584'; // Demo Agent (non-ADK)

  // Get access token (you'll need to set this from gcloud auth print-access-token)
  const accessToken = process.env.ACCESS_TOKEN;

  if (!accessToken) {
    console.error('Please set ACCESS_TOKEN environment variable');
    console.error('Run: export ACCESS_TOKEN=$(gcloud auth print-access-token)');
    process.exit(1);
  }

  const agentResourceName = `projects/${projectId}/locations/${location}/reasoningEngines/${agentId}`;
  const queryUrl = `https://${location}-aiplatform.googleapis.com/v1beta1/${agentResourceName}:query`;

  const headers = {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json',
  };

  // Test different input formats
  const formats = [
    {
      name: 'args array',
      body: { input: { args: ['hi'] } }
    },
    {
      name: 'kwargs',
      body: { input: { kwargs: { input: 'hi' } } }
    },
    {
      name: 'both args and kwargs',
      body: { input: { args: [], kwargs: { input: 'hi' } } }
    },
    {
      name: '__call__',
      body: { input: { "__call__": { "input": "hi" } } }
    },
    {
      name: 'nested input',
      body: { input: { input: 'hi' } }
    },
    {
      name: 'direct query',
      body: { input: { query: 'hi' } }
    }
  ];

  console.log(`Testing agent ${agentId} at ${queryUrl}\n`);

  for (const format of formats) {
    console.log(`Testing format: ${format.name}`);
    console.log('Request body:', JSON.stringify(format.body, null, 2));

    try {
      const response = await fetch(queryUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify(format.body),
      });

      if (response.ok) {
        const data = await response.json();
        console.log('✅ SUCCESS!');
        console.log('Response:', JSON.stringify(data, null, 2));
        console.log('\n=== FOUND WORKING FORMAT ===');
        console.log(`Format: ${format.name}`);
        console.log('Body:', JSON.stringify(format.body, null, 2));
        break;
      } else {
        const error = await response.text();
        console.log('❌ Failed:', error.substring(0, 150));
      }
    } catch (error) {
      console.log('❌ Error:', error.message);
    }
    console.log('---\n');
  }
}

testAgentQuery().catch(console.error);