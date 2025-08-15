import { NextRequest, NextResponse } from 'next/server';
import { verifyToken, getUserById } from '@/lib/auth';
import { spawn } from 'child_process';
import path from 'path';
import pool from '@/lib/database';

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

    // Use sessionId as the workflow ID (no need to encode user_id)
    const workflowId = sessionId;

    // Get initial message count for this workflow
    const initialCount = await getMessageCount(workflowId, user.id);

    // Call the Python chatbot script with user ID
    await callPythonChatbot(workflowId, message, user.id);

    // Wait for the workflow to complete and get the response
    const response = await waitForResponse(workflowId, user.id, initialCount);

    return NextResponse.json({ response }, { status: 200 });
  } catch (error) {
    console.error('Chat API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

async function getMessageCount(workflowId: string, userId: number): Promise<number> {
  try {
    const result = await pool.query(
      'SELECT COUNT(*) FROM public.conversations WHERE workflow_id = $1 AND user_id = $2',
      [workflowId, userId]
    );
    return parseInt(result.rows[0].count) || 0;
  } catch (error) {
    console.error('Error getting message count:', error);
    return 0;
  }
}

async function waitForResponse(workflowId: string, userId: number, initialCount: number): Promise<string> {
  const maxWaitTime = 75000; // 75 seconds (more buffer for workflow timeout)
  const pollInterval = 1000; // 1 second (faster polling)
  const startTime = Date.now();

  console.log(`Waiting for response for workflow ${workflowId}, user ${userId}, initial count: ${initialCount}`);

  while (Date.now() - startTime < maxWaitTime) {
    try {
      // Check for new messages in the database
      const result = await pool.query(
        `SELECT speaker, message, message_order 
         FROM public.conversations 
         WHERE workflow_id = $1 AND user_id = $2 
         ORDER BY message_order ASC`,
        [workflowId, userId]
      );

      const messages = result.rows;
      console.log(`Poll ${Math.floor((Date.now() - startTime) / 1000)}s: Found ${messages.length} messages (initial: ${initialCount})`);
      
      // Look for new response messages
      if (messages.length > initialCount) {
        const newMessages = messages.slice(initialCount);
        const botResponse = newMessages.find(msg => msg.speaker === 'response');
        
        if (botResponse) {
          console.log(`Found bot response: ${botResponse.message.substring(0, 50)}...`);
          return botResponse.message;
        }
      }

      // Wait before polling again
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    } catch (error) {
      console.error('Error polling for response:', error);
    }
  }

  // If we get here, timeout occurred
  return 'Sorry, the AI took too long to respond. Please try again or check your conversation history later.';
}

async function callPythonChatbot(workflowId: string, message: string, userId: number): Promise<void> {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(process.cwd(), '..', 'chatbot_backend', 'send_message.py');
    
    const python = spawn('python', [scriptPath, workflowId, message, userId.toString()], {
      cwd: path.join(process.cwd(), '..'),
      env: {
        ...process.env,
        PYTHONPATH: path.join(process.cwd(), '..'),
        OPENAI_API_KEY: process.env.OPENAI_API_KEY,
        DATABASE_URL: process.env.DATABASE_URL,
        // Temporal Cloud Configuration
        TEMPORAL_CLOUD_NAMESPACE: process.env.TEMPORAL_CLOUD_NAMESPACE || 'local-test.ssstk',
        TEMPORAL_CLOUD_ADDRESS: process.env.TEMPORAL_CLOUD_ADDRESS || 'us-east4.gcp.api.temporal.io:7233',
        TEMPORAL_CLOUD_API_KEY: process.env.TEMPORAL_CLOUD_API_KEY,
        // Databricks Configuration
        DATABRICKS_HOST: process.env.DATABRICKS_HOST,
        DATABRICKS_TOKEN: process.env.DATABRICKS_TOKEN,
        DATABRICKS_ENDPOINT_NAME: process.env.DATABRICKS_ENDPOINT_NAME || 'procurement_calendar',
        DATABRICKS_INDEX_NAME: process.env.DATABRICKS_INDEX_NAME || 'procurement_calendar.silver.companies_vs_index',
        // Chatbot Configuration
        INACTIVITY_TIMEOUT_MINUTES: process.env.INACTIVITY_TIMEOUT_MINUTES || '5',
        MAX_TOKENS: process.env.MAX_TOKENS || '512',
        TEMPERATURE: process.env.TEMPERATURE || '0.1',
        TOP_P: process.env.TOP_P || '0.2'
      }
    });

    let stderr = '';

    python.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    python.on('close', (code) => {
      if (code === 0) {
        resolve();
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