import { NextRequest, NextResponse } from 'next/server';
import { verifyToken, getUserById } from '@/lib/auth';
import { spawn } from 'child_process';
import path from 'path';

export async function POST(request: NextRequest) {
  try {
    // Verify authentication
    const token = request.cookies.get('token')?.value;
    if (!token) {
      return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });
    }

    const decoded = verifyToken(token);
    if (!decoded) {
      return NextResponse.json({ error: 'Invalid token' }, { status: 401 });
    }

    const user = await getUserById(decoded.userId);
    if (!user) {
      return NextResponse.json({ error: 'User not found' }, { status: 404 });
    }

    const { message, sessionId } = await request.json();

    if (!message || !sessionId) {
      return NextResponse.json(
        { error: 'Message and sessionId are required' },
        { status: 400 }
      );
    }

    // Create a unique workflow ID that includes the user ID
    const workflowId = `${sessionId}-user-${user.id}`;

    // Call the Python chatbot script
    const response = await callPythonChatbot(workflowId, message);

    return NextResponse.json({ response }, { status: 200 });
  } catch (error) {
    console.error('Chat API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

async function callPythonChatbot(workflowId: string, message: string): Promise<string> {
  return new Promise((resolve, reject) => {
    // Path to the Python script - adjust as needed
    const scriptPath = path.join(process.cwd(), '..', 'bedrock', 'session', 'send_message.py');
    
    const python = spawn('python', [scriptPath, workflowId, message], {
      cwd: path.join(process.cwd(), '..'),
      env: {
        ...process.env,
        PYTHONPATH: path.join(process.cwd(), '..'),
        OPENAI_API_KEY: process.env.OPENAI_API_KEY,
        DATABASE_URL: process.env.DATABASE_URL || "postgresql://neondb_owner:npg_hP6rHznOS1iQ@ep-small-pond-a8lxs577-pooler.eastus2.azure.neon.tech/neondb?sslmode=require"
      }
    });

    let stdout = '';
    let stderr = '';

    python.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    python.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    python.on('close', (code) => {
      if (code === 0) {
        // For now, return a simple response since the actual response comes from the workflow
        resolve('Message sent to chatbot. Please check the workflow for the response or wait for timeout.');
      } else {
        console.error('Python script error:', stderr);
        reject(new Error(`Python script failed with code ${code}: ${stderr}`));
      }
    });

    python.on('error', (error) => {
      console.error('Failed to start Python script:', error);
      reject(error);
    });
  });
}