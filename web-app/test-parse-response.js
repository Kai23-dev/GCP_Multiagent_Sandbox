#!/usr/bin/env node

// The response string from the API
const responseStr = `{"content": {"parts": [{"thought_signature": "CrMCAR_MhbbyUZ6qYMIiJFdyP0VrqVN6tTCbWVOkGjVgLLBJ0dEx9KTcGsHJv5E4lft3UsEhnWCzmUm7EzNe55KOM_y5kKCf8Kn8f45WItLJj9eMevTyiCBF4VM2mPFXzqBt9u5BRL9sHFwbfr4oQlXK1uaw4bMV3oa8kMtfeoSQRvBfpvOekANj3PbsXjTp0WhmgRf6tZSBlhNB-qVmRfpVbWfFIW39kfvf52k0tPxOO4qeVaVeIkJ3ACp4Wv56Q-9uH9SjdeiBu6XTW7AXp7JhAmj-H4QIsyXpBr00da_mwcAG1ozUn8lZhtjk_EYSk-aF1bGM_5ujLmfqjy6fqgY7Crt2Q3-t1hJ0oR1_XzXYJGMPolQwCIN0j25boLcVAlPdYGvm-IzKkWCz9mHOUd6qyuYkeg==", "function_call": {"id": "adk-c06515c6-77c7-45f9-8923-f12b77be887d", "args": {"request": "2+2"}, "name": "CodeAgent"}}], "role": "model"}, "finish_reason": "STOP", "usage_metadata": {"candidates_token_count": 6, "candidates_tokens_details": [{"modality": "TEXT", "token_count": 6}], "prompt_token_count": 304, "prompt_tokens_details": [{"modality": "TEXT", "token_count": 304}], "thoughts_token_count": 64, "total_token_count": 374, "traffic_type": "ON_DEMAND"}, "invocation_id": "e-4f5e7673-19fc-446f-9259-1c741724a043", "author": "demo_agent", "actions": {"state_delta": {}, "artifact_delta": {}, "requested_auth_configs": {}}, "long_running_tool_ids": [], "id": "daa897dc-cf8e-42a9-8567-eda0b1022632", "timestamp": 1760042692.627958}
{"content": {"parts": [{"function_response": {"id": "adk-c06515c6-77c7-45f9-8923-f12b77be887d", "name": "CodeAgent", "response": {"result": "2 + 2 = 4\\n"}}}], "role": "user"}, "invocation_id": "e-4f5e7673-19fc-446f-9259-1c741724a043", "author": "demo_agent", "actions": {"state_delta": {}, "artifact_delta": {}, "requested_auth_configs": {}}, "id": "59a65d49-b84b-4c57-b3de-87f831c762ba", "timestamp": 1760042694.449758}
{"content": {"parts": [{"text": "The answer is 4.\\n"}], "role": "model"}, "finish_reason": "STOP", "usage_metadata": {"candidates_token_count": 7, "candidates_tokens_details": [{"modality": "TEXT", "token_count": 7}], "prompt_token_count": 321, "prompt_tokens_details": [{"modality": "TEXT", "token_count": 382}], "total_token_count": 328, "traffic_type": "ON_DEMAND"}, "invocation_id": "e-4f5e7673-19fc-446f-9259-1c741724a043", "author": "demo_agent", "actions": {"state_delta": {}, "artifact_delta": {}, "requested_auth_configs": {}}, "id": "1716b735-bfbe-4382-834b-a6bf838a1258", "timestamp": 1760042694.585415}`;

// Parse the newline-delimited JSON
const lines = responseStr.split('\n');
console.log(`Found ${lines.length} JSON objects in response\n`);

lines.forEach((line, i) => {
  if (line.trim()) {
    try {
      const obj = JSON.parse(line);
      console.log(`Object ${i + 1}:`);

      if (obj.content?.parts?.[0]?.function_call) {
        console.log(`  - Function call: ${obj.content.parts[0].function_call.name}`);
        console.log(`  - Args: ${JSON.stringify(obj.content.parts[0].function_call.args)}`);
      } else if (obj.content?.parts?.[0]?.function_response) {
        console.log(`  - Function response: ${obj.content.parts[0].function_response.name}`);
        console.log(`  - Result: ${JSON.stringify(obj.content.parts[0].function_response.response)}`);
      } else if (obj.content?.parts?.[0]?.text) {
        console.log(`  - Text response: "${obj.content.parts[0].text}"`);
      }
      console.log('');
    } catch (e) {
      console.error(`Failed to parse line ${i + 1}:`, e.message);
    }
  }
});

console.log('\nFinal answer should be: "The answer is 4."');