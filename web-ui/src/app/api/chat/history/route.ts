import { NextRequest, NextResponse } from 'next/server';
import { verifyToken, getUserById } from '@/lib/auth';
import pool from '@/lib/database';

export async function GET(request: NextRequest) {
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

    // Get query parameters
    const { searchParams } = new URL(request.url);
    const workflowId = searchParams.get('workflowId');

    if (workflowId) {
      // Get specific conversation
      const conversation = await getConversation(user.id, workflowId);
      return NextResponse.json({ conversation }, { status: 200 });
    } else {
      // Get all conversations for the user
      const conversations = await getAllConversations(user.id);
      return NextResponse.json({ conversations }, { status: 200 });
    }
  } catch (error) {
    console.error('Chat history API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

async function getConversation(userId: number, workflowId: string) {
  try {
    // Get conversation messages
    const messagesResult = await pool.query(
      `SELECT workflow_id, speaker, message, message_order, created_at 
       FROM public.conversations 
       WHERE user_id = $1 AND workflow_id = $2 
       ORDER BY message_order ASC`,
      [userId, workflowId]
    );

    // Get conversation summary
    const summaryResult = await pool.query(
      `SELECT summary, created_at, updated_at 
       FROM public.conversation_summaries 
       WHERE user_id = $1 AND workflow_id = $2`,
      [userId, workflowId]
    );

    return {
      workflow_id: workflowId,
      messages: messagesResult.rows,
      summary: summaryResult.rows[0] || null,
    };
  } catch (error) {
    console.error('Error getting conversation:', error);
    return null;
  }
}

async function getAllConversations(userId: number) {
  try {
    // Get all unique workflow IDs with their summaries for the user
    const result = await pool.query(
      `SELECT DISTINCT 
         cs.workflow_id, 
         cs.summary, 
         cs.created_at, 
         cs.updated_at,
         (SELECT COUNT(*) FROM public.conversations c WHERE c.workflow_id = cs.workflow_id AND c.user_id = $1) as message_count
       FROM public.conversation_summaries cs
       WHERE cs.user_id = $1
       ORDER BY cs.updated_at DESC`,
      [userId]
    );

    return result.rows;
  } catch (error) {
    console.error('Error getting all conversations:', error);
    return [];
  }
}