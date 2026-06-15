#!/usr/bin/env node

/**
 * Memory Bank Test Script
 * Tests the complete memory save and search flow
 */

const agentId = '4992860311498260480'; // Demo Agent
const baseUrl = 'http://localhost:3000';

// ANSI colors for output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

async function testMemorySave() {
  log('\n🧪 Testing Memory Save...', 'cyan');
  
  try {
    // First, we need to create a session by chatting
    log('1️⃣ Sending a test message to create a session...', 'blue');
    
    const chatResponse = await fetch(`${baseUrl}/api/agent-engine`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: 'Hello, this is a test message for memory bank testing. Remember that my favorite color is blue and I love coding.',
        agentId: agentId,
      })
    });
    
    if (!chatResponse.ok) {
      throw new Error(`Chat failed: ${chatResponse.status}`);
    }
    
    const chatData = await chatResponse.json();
    const sessionId = chatData.sessionId;
    
    log(`✅ Session created: ${sessionId}`, 'green');
    log(`📝 Agent response: ${chatData.response?.substring(0, 100)}...`, 'blue');
    
    // Now save to memory
    log('\n2️⃣ Saving session to memory...', 'blue');
    
    const saveResponse = await fetch(`${baseUrl}/api/agent-memory`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        agentId: agentId,
        sessionId: sessionId,
        action: 'save'
      })
    });
    
    if (!saveResponse.ok) {
      const errorText = await saveResponse.text();
      throw new Error(`Memory save failed: ${saveResponse.status} - ${errorText}`);
    }
    
    const saveData = await saveResponse.json();
    log(`✅ Memory saved successfully!`, 'green');
    log(`📦 Memory ID: ${saveData.memoryId}`, 'blue');
    
    return sessionId;
    
  } catch (error) {
    log(`❌ Memory save test failed: ${error.message}`, 'red');
    throw error;
  }
}

async function testMemorySearch() {
  log('\n🔍 Testing Memory Search...', 'cyan');
  
  try {
    log('1️⃣ Searching for memories with query: "test"', 'blue');
    
    const searchResponse = await fetch(`${baseUrl}/api/agent-memory`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        agentId: agentId,
        action: 'search',
        query: 'test'
      })
    });
    
    if (!searchResponse.ok) {
      const errorText = await searchResponse.text();
      throw new Error(`Memory search failed: ${searchResponse.status} - ${errorText}`);
    }
    
    const searchData = await searchResponse.json();
    
    if (searchData.success && searchData.memories) {
      log(`✅ Search completed successfully!`, 'green');
      log(`📊 Found ${searchData.memories.length} memories`, 'blue');
      
      if (searchData.memories.length > 0) {
        log('\n📝 Memory details:', 'yellow');
        searchData.memories.forEach((memory, index) => {
          log(`\nMemory ${index + 1}:`, 'cyan');
          console.log(JSON.stringify(memory, null, 2));
        });
      } else {
        log('⚠️  No memories found. This might be expected if:', 'yellow');
        log('   - The memory was just saved (may take a moment to index)', 'yellow');
        log('   - The search query doesn\'t match saved content', 'yellow');
        log('   - No memories have been saved yet', 'yellow');
      }
      
      return searchData.memories;
    } else {
      log(`❌ Unexpected response format:`, 'red');
      console.log(searchData);
    }
    
  } catch (error) {
    log(`❌ Memory search test failed: ${error.message}`, 'red');
    throw error;
  }
}

async function runTests() {
  log('╔═══════════════════════════════════════╗', 'cyan');
  log('║   Memory Bank Integration Test       ║', 'cyan');
  log('╚═══════════════════════════════════════╝', 'cyan');
  
  try {
    // Test save
    const sessionId = await testMemorySave();
    
    // Wait a moment for memory to be indexed
    log('\n⏳ Waiting 2 seconds for memory indexing...', 'yellow');
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Test search
    await testMemorySearch();
    
    // Try broader search
    log('\n🔍 Testing broader search with query: "favorite"', 'blue');
    const searchResponse2 = await fetch(`${baseUrl}/api/agent-memory`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        agentId: agentId,
        action: 'search',
        query: 'favorite'
      })
    });
    
    const searchData2 = await searchResponse2.json();
    log(`📊 Found ${searchData2.memories?.length || 0} memories for "favorite"`, 'blue');
    
    log('\n✅ All tests completed!', 'green');
    log('\n💡 Tips:', 'yellow');
    log('   - Check browser console for detailed logs', 'yellow');
    log('   - Use Memory Browser UI to search interactively', 'yellow');
    log('   - Try different search queries', 'yellow');
    
  } catch (error) {
    log('\n❌ Test suite failed', 'red');
    process.exit(1);
  }
}

// Run tests
runTests();
