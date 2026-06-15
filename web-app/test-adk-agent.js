#!/usr/bin/env node

/**
 * Test script for ADK agent integration
 * Run this to verify the web app can properly communicate with ADK agents
 */

const PROJECT_ID = 'sco-agents-np-9orx';
const AGENT_ID = '1788443623507886080';
const API_URL = process.env.API_URL || 'http://localhost:3000';

async function testADKAgent() {
  console.log('=== Testing ADK Agent Integration ===');
  console.log(`API URL: ${API_URL}`);
  console.log(`Agent ID: ${AGENT_ID}`);
  console.log('');

  try {
    // Test 1: Regular agent-engine endpoint
    console.log('Test 1: Testing /api/agent-engine endpoint...');
    const response1 = await fetch(`${API_URL}/api/agent-engine`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: 'Hello, what can you help me with?',
        agentId: AGENT_ID,
      }),
    });

    if (response1.ok) {
      const data1 = await response1.json();
      console.log('✅ Response received:');
      console.log('  Session ID:', data1.sessionId);
      console.log('  Response:', data1.response?.substring(0, 100) + '...');
      console.log('  Success:', data1.success);
    } else {
      console.log('❌ Request failed:', response1.status, response1.statusText);
      const error = await response1.text();
      console.log('  Error:', error.substring(0, 200));
    }

    console.log('');

    // Test 2: Streaming endpoint
    console.log('Test 2: Testing /api/agent-engine-stream endpoint...');
    const response2 = await fetch(`${API_URL}/api/agent-engine-stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: 'Tell me a short joke',
        agentId: AGENT_ID,
      }),
    });

    if (response2.ok) {
      console.log('✅ Stream response received');
      const reader = response2.body.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data:')) {
            const dataStr = line.substring(5).trim();
            if (dataStr && dataStr !== '[DONE]') {
              try {
                const data = JSON.parse(dataStr);
                if (data.type === 'chunk' && data.content) {
                  fullResponse += data.content;
                  process.stdout.write(data.content);
                } else if (data.type === 'info') {
                  console.log(`\n  [INFO] ${data.message}`);
                } else if (data.type === 'error') {
                  console.log(`\n  [ERROR] ${data.message}`);
                }
              } catch (e) {
                // Skip unparseable lines
              }
            }
          }
        }
      }

      console.log('\n  Full response length:', fullResponse.length);
    } else {
      console.log('❌ Stream request failed:', response2.status, response2.statusText);
    }

    console.log('');

    // Test 3: Test with session persistence
    console.log('Test 3: Testing session persistence...');

    // First message
    const response3a = await fetch(`${API_URL}/api/agent-engine`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: 'My name is TestUser',
        agentId: AGENT_ID,
      }),
    });

    let sessionId = null;
    if (response3a.ok) {
      const data3a = await response3a.json();
      sessionId = data3a.sessionId;
      console.log('✅ First message sent, session:', sessionId);
      console.log('  Response:', data3a.response?.substring(0, 100));
    }

    // Second message with same session
    if (sessionId) {
      const response3b = await fetch(`${API_URL}/api/agent-engine`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: 'What is my name?',
          agentId: AGENT_ID,
          sessionId: sessionId,
        }),
      });

      if (response3b.ok) {
        const data3b = await response3b.json();
        console.log('✅ Second message sent with same session');
        console.log('  Response:', data3b.response?.substring(0, 100));

        if (data3b.response?.toLowerCase().includes('testuser')) {
          console.log('  ✅ Session context maintained!');
        } else {
          console.log('  ⚠️ Session context might not be maintained');
        }
      }
    }

    console.log('');
    console.log('=== Tests Complete ===');

  } catch (error) {
    console.error('Test failed with error:', error);
  }
}

// Run the test
testADKAgent().catch(console.error);