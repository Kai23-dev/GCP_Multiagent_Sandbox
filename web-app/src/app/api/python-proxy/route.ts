import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import path from 'path';

interface PythonProxyRequest {
  message: string;
  agentId: string;
  userId: string;
  sessionId?: string;
}

/**
 * Proxy to Python for ADK agent communication
 * This endpoint spawns a Python process to handle ADK agent queries
 */
export async function POST(request: NextRequest) {
  try {
    const body: PythonProxyRequest = await request.json();
    const { message, agentId, userId, sessionId } = body;

    if (!message || !agentId || !userId) {
      return NextResponse.json(
        { error: 'Message, agentId, and userId are required' },
        { status: 400 }
      );
    }

    // Path to Python script
    const scriptPath = path.join(process.cwd(), 'scripts', 'query_adk_agent.py');

    // Prepare the input data
    const inputData = JSON.stringify({
      message,
      agentId,
      userId,
      sessionId: sessionId || null
    });

    return new Promise<NextResponse>((resolve) => {
      let output = '';
      let errorOutput = '';

      // Check if we have a Python virtual environment
      const venvPath = path.join(process.cwd(), 'venv', 'bin', 'python');
      const pythonCommand = process.platform === 'win32'
        ? path.join(process.cwd(), 'venv', 'Scripts', 'python.exe')
        : venvPath;

      // Spawn Python process
      const pythonProcess = spawn(pythonCommand, [scriptPath], {
        env: {
          ...process.env,
          PYTHONUNBUFFERED: '1',
          GOOGLE_CLOUD_PROJECT: process.env.GOOGLE_CLOUD_PROJECT,
          GOOGLE_CLOUD_LOCATION: process.env.GOOGLE_CLOUD_LOCATION || 'us-central1'
        }
      });

      // Send input data to Python script
      pythonProcess.stdin.write(inputData);
      pythonProcess.stdin.end();

      // Collect output
      pythonProcess.stdout.on('data', (data) => {
        output += data.toString();
      });

      // Collect error output
      pythonProcess.stderr.on('data', (data) => {
        errorOutput += data.toString();
        console.error('Python stderr:', data.toString());
      });

      // Handle process completion
      pythonProcess.on('close', (code) => {
        if (code !== 0) {
          console.error('Python process exited with code:', code);
          console.error('Error output:', errorOutput);
          resolve(NextResponse.json(
            {
              error: 'Failed to query agent',
              details: errorOutput || 'Python process failed'
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
          console.error('Failed to parse Python output:', output);
          resolve(NextResponse.json(
            {
              error: 'Failed to parse agent response',
              details: output
            },
            { status: 500 }
          ));
        }
      });

      // Handle process errors
      pythonProcess.on('error', (error) => {
        console.error('Failed to spawn Python process:', error);
        resolve(NextResponse.json(
          {
            error: 'Failed to start Python process',
            details: error.message
          },
          { status: 500 }
        ));
      });
    });

  } catch (error) {
    console.error('Error in python-proxy API:', error);
    return NextResponse.json(
      { error: 'Failed to process request', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}