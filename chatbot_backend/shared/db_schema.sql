-- Database schema for conversation storage
CREATE TABLE IF NOT EXISTS public.conversations (
    id SERIAL PRIMARY KEY,
    workflow_id VARCHAR(255) NOT NULL,
    speaker VARCHAR(50) NOT NULL CHECK (speaker IN ('user', 'response')),
    message TEXT NOT NULL,
    message_order INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public.conversation_summaries (
    id SERIAL PRIMARY KEY,
    workflow_id VARCHAR(255) UNIQUE NOT NULL,
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_conversations_workflow_id ON public.conversations(workflow_id);
CREATE INDEX IF NOT EXISTS idx_conversations_order ON public.conversations(workflow_id, message_order);