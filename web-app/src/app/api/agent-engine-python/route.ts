import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';
import { getUserFromIAPHeaders } from '@/utils/auth';

interface AgentEngineRequest {
  message: string;
  agentId: string;
  sessionId?: string;
  userAccessToken?: string;
  clearSession?: boolean;
}

/**
 * Query Agent Engine using Python SDK subprocess
 * This is a fallback when direct Node.js API calls don't work
 */
export async function POST(request: NextRequest) {
  try {
    const body: AgentEngineRequest = await request.json();
    const { message, agentId, sessionId } = body;

    if (!message || !agentId) {
      return NextResponse.json(
        { error: 'Message and agentId are required' },
        { status: 400 }
      );
    }

    // Get user information
    const userInfo = getUserFromIAPHeaders(request);
    const userId = userInfo.userId || `user-${Date.now()}`;
    const currentSessionId = sessionId || `session-${userId}-${Date.now()}`;

    // Create Python script content
    const pythonScript = `
import sys
import json
from vertexai.preview import reasoning_engines
import vertexai

# Read input
input_data = json.loads(sys.argv[1])

# Initialize Vertex AI
project_id = "${process.env.GOOGLE_CLOUD_PROJECT || 'agentspace-prod-w89w'}"
location = "${process.env.GOOGLE_CLOUD_LOCATION || 'us-central1'}"
vertexai.init(project=project_id, location=location)

agent_id = input_data['agentId']
message = input_data['message']
user_id = input_data['userId']
session_id = input_data['sessionId']

try:
    # Load the agent
    agent_resource = f"projects/{project_id}/locations/{location}/reasoningEngines/{agent_id}"
    agent = reasoning_engines.ReasoningEngine(agent_resource)

    # Try to call the agent directly
    # Most agents should support direct calling
    result = None
    error_msg = None

    # Try direct call first
    try:
        result = agent(message)
    except Exception as e1:
        # Try with query method
        try:
            result = agent.query(input=message)
        except Exception as e2:
            # Try with specific operation
            try:
                # Check if agent has stream_query
                if hasattr(agent, 'operation_schemas'):
                    schemas = agent.operation_schemas()
                    has_stream_query = any(s['name'] == 'stream_query' for s in schemas)

                    if has_stream_query:
                        # This is an ADK agent, but we can't easily stream from subprocess
                        error_msg = f"This is an ADK agent with session management. Available operations: {[s['name'] for s in schemas if 'async' not in s.get('api_mode', '')]}"
                    else:
                        error_msg = f"Agent does not support standard query methods: {str(e2)}"
                else:
                    error_msg = f"Agent query failed: {str(e2)}"
            except Exception as e3:
                error_msg = f"Failed to query agent: {str(e3)}"

    if result is not None:
        response_text = str(result) if result else "No response"
        output = {
            "response": response_text,
            "sessionId": session_id,
            "success": True
        }
    else:
        output = {
            "response": error_msg or "Failed to query agent",
            "sessionId": session_id,
            "success": False,
            "error": error_msg
        }

    print(json.dumps(output))

except Exception as e:
    output = {
        "response": "",
        "sessionId": session_id,
        "success": False,
        "error": str(e)
    }
    print(json.dumps(output))
    sys.exit(1)
`;

    // Write the script to a temporary file
    const tempDir = path.join(process.cwd(), '.tmp');
    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }

    const scriptPath = path.join(tempDir, `query_${Date.now()}.py`);
    fs.writeFileSync(scriptPath, pythonScript);

    // Prepare the input data
    const inputData = JSON.stringify({
      message,
      agentId,
      userId,
      sessionId: currentSessionId
    });

    return new Promise<NextResponse>((resolve) => {
      let output = '';
      let errorOutput = '';

      // Check if we have a Python virtual environment
      const venvPath = path.join(process.cwd(), 'venv', 'bin', 'python');
      const pythonCommand = fs.existsSync(venvPath) ? venvPath : 'python3';

      // Spawn Python process
      const pythonProcess = spawn(pythonCommand, [scriptPath, inputData], {
        env: {
          ...process.env,
          PYTHONUNBUFFERED: '1',
          GOOGLE_CLOUD_PROJECT: process.env.GOOGLE_CLOUD_PROJECT,
          GOOGLE_CLOUD_LOCATION: process.env.GOOGLE_CLOUD_LOCATION || 'us-central1'
        }
      });

      // Collect output
      pythonProcess.stdout.on('data', (data) => {
        output += data.toString();
      });

      // Collect error output
      pythonProcess.stderr.on('data', (data) => {
        errorOutput += data.toString();
        // Don't log warnings
        if (!data.toString().includes('WARNING') && !data.toString().includes('E0000')) {
          console.error('Python stderr:', data.toString());
        }
      });

      // Handle process completion
      pythonProcess.on('close', (code) => {
        // Clean up temp file
        try {
          fs.unlinkSync(scriptPath);
        } catch {
          // Ignore cleanup errors
        }

        if (code !== 0 && !output) {
          console.error('Python process exited with code:', code);
          resolve(NextResponse.json(
            {
              response: '',
              sessionId: currentSessionId,
              success: false,
              error: 'Python process failed',
              details: errorOutput
            },
            { status: 500 }
          ));
          return;
        }

        try {
          // Parse the JSON output from Python
          const result = JSON.parse(output);
          resolve(NextResponse.json(result));
        } catch {
          // If we got some output but it's not JSON, return it as text
          if (output.trim()) {
            resolve(NextResponse.json({
              response: output.trim(),
              sessionId: currentSessionId,
              success: true
            }));
          } else {
            console.error('Failed to parse Python output:', output);
            resolve(NextResponse.json(
              {
                response: '',
                sessionId: currentSessionId,
                success: false,
                error: 'Failed to parse agent response',
                details: output || errorOutput
              },
              { status: 500 }
            ));
          }
        }
      });

      // Handle process errors
      pythonProcess.on('error', (error) => {
        console.error('Failed to spawn Python process:', error);

        // Clean up temp file
        try {
          fs.unlinkSync(scriptPath);
        } catch {
          // Ignore cleanup errors
        }

        resolve(NextResponse.json(
          {
            response: '',
            sessionId: currentSessionId,
            success: false,
            error: 'Failed to start Python process. Make sure Python environment is set up.',
            details: error.message
          },
          { status: 500 }
        ));
      });

      // Set a timeout
      setTimeout(() => {
        pythonProcess.kill();

        // Clean up temp file
        try {
          fs.unlinkSync(scriptPath);
        } catch {
          // Ignore cleanup errors
        }

        resolve(NextResponse.json(
          {
            response: '',
            sessionId: currentSessionId,
            success: false,
            error: 'Query timeout - agent took too long to respond'
          },
          { status: 504 }
        ));
      }, 30000); // 30 second timeout
    });

  } catch (error) {
    console.error('Error in agent-engine-python API:', error);
    return NextResponse.json(
      {
        response: '',
        sessionId: '',
        success: false,
        error: 'Failed to process request',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}