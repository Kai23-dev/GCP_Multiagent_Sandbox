#!/usr/bin/env node

/**
 * Test ADK agent formats with the updated endpoint
 */

async function testADKAgent() {
  const baseUrl = 'http://localhost:3010';
  const agentId = '5846085732698947584'; // Demo Agent (the working one)

  console.log('Testing ADK Agent with updated endpoint...\n');

  try {
    const response = await fetch(`${baseUrl}/api/agent-engine`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: 'Hello, what is 2+2?',
        agentId: agentId,
      }),
    });

    const data = await response.json();

    console.log('Response status:', response.status);
    console.log('Response data:', JSON.stringify(data, null, 2));

    if (data.debug) {
      console.log('\nDebug info - Attempted formats:');
      data.debug.forEach(attempt => {
        console.log(`  - ${attempt.format}: ${attempt.status || attempt.error}`);
      });
    }

    if (data.agentType) {
      console.log('\nAgent type:', data.agentType);
    }

    if (data.response) {
      console.log('\nAgent response (first 200 chars):');
      console.log(data.response.substring(0, 200) + '...');

      // Try to parse and extract text
      try {
        const parsed = JSON.parse(data.response);
        if (parsed.content?.parts?.[0]?.text) {
          console.log('\nExtracted text:', parsed.content.parts[0].text);
        }
      } catch (e) {
        // Not JSON, just text
        console.log('\nFull response:', data.response);
      }
    }

  } catch (error) {
    console.error('Error:', error);
  }
}

// Run the test
testADKAgent();