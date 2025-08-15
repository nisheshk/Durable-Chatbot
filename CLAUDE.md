# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Python Backend (Enhanced Chatbot with Cloud Deployment)

**Environment Setup:**
```bash
# Load environment variables for cloud deployment
source chatbot_backend/.env.cloud

# Required environment variables (.env.cloud):
# Temporal Cloud Configuration
TEMPORAL_CLOUD_NAMESPACE=
TEMPORAL_CLOUD_ADDRESS=
TEMPORAL_CLOUD_API_KEY=

# Database Configuration (Neon PostgreSQL)
DATABASE_URL=

# OpenAI Configuration
OPENAI_API_KEY=

# Chatbot Configuration
INACTIVITY_TIMEOUT_MINUTES=5
MAX_TOKENS=512
TEMPERATURE=0.1
TOP_P=0.2

# Worker Scaling Configuration
MAX_CONCURRENT_ACTIVITIES=20
MAX_CONCURRENT_WORKFLOW_TASKS=10
MAX_CONCURRENT_ACTIVITY_TASKS=20

# Database Connection Pool Settings
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30

# Databricks Configuration 
DATABRICKS_HOST=
DATABRICKS_TOKEN=
DATABRICKS_ENDPOINT_NAME=
DATABRICKS_INDEX_NAME=

JWT_SECRET=
NODE_ENV=development

cd chatbot_backend && pip install -r requirements.txt
```

**Production Deployment (Temporal Cloud - Recommended):**
```bash
cd chatbot_backend
source .env.cloud

# Start cloud worker (no local server needed)
python worker_cloud.py

# Send test messages (in another terminal)
source .env.cloud && python client_cloud.py "test-session" "Find IT companies in California" 1
source .env.cloud && python client_cloud.py "test-session" "What's the latest news in AI?" 1
```

**Local Development (Optional):**
```bash
cd chatbot_backend

# Start local Temporal server (separate terminal)
temporal server start-dev

# Start local worker
source .env.cloud && python worker_local.py

# Send messages for testing
source .env.cloud && python send_message.py 'session-1' 'Hello world' '123'
```

**Docker Deployment:**
```bash
cd chatbot_backend

# Build and run with scaling
docker-compose up --build --scale chatbot-worker=3

# Background deployment
docker-compose up -d --build

# Scale workers
docker-compose up -d --scale chatbot-worker=5
```

**Load Testing:**
```bash
cd chatbot_backend
source .env.cloud && python load_test.py
```

### Web UI (Next.js with Authentication)

```bash
cd web-ui
npm install
npm run dev      # Development server
npm run build    # Production build
npm run start    # Production server
npm run lint     # Lint TypeScript/React code
```

## Architecture Overview

### Enhanced Temporal Workflow System
- **Enhanced workflows** (`chatbot_backend/workflows/chat_workflow.py`) orchestrate AI interactions with smart tool routing
- **Enhanced Activities** (`chatbot_backend/activities/openai_activities.py`) handle OpenAI, Databricks, and web search operations
- **Agent Tool Selection** (`chatbot_backend/activities/agent_tool_selection.py`) provides intelligent query routing
- **Cloud-ready workflows** support both Temporal Cloud and local development

### Database Integration
- **PostgreSQL** (Neon) stores conversation history, summaries, and user authentication
- **Enhanced Schema** (`chatbot_backend/shared/db_schema.sql`) includes conversations, summaries, and user tables
- **Connection Pooling** with configurable pool sizes for production scalability
- **User Management** (`web-ui/src/lib/db-schema-users.sql`) for web UI authentication

### Enhanced Features
- **Smart Tool Routing**: Automatically detects and routes queries to appropriate tools
- **Databricks Company Search**: Vector search for supplier and company information
- **Real-time Web Search**: Current information retrieval using OpenAI's search-enabled models
- **Context Management**: Configurable token limits with automatic summarization
- **Multi-session Support**: Independent conversation histories with user association

### Modern Web Frontend
- **Next.js 15** with TypeScript, Tailwind CSS, and modern React patterns
- **Secure Authentication** with JWT tokens, bcrypt hashing, and session management
- **Real-time Chat Interface** with enhanced user experience
- **Conversation History** with user-specific access and search capabilities

## Enhanced AI Features

### 🏢 Smart Company Search (Databricks Integration)
Automatically detects company/supplier queries and searches vector database:

**Auto-triggers on queries like:**
- "Find companies that provide IT services"
- "I need supplier information for construction"
- "Search for vendors in Texas"
- "Company details for [company name]"

**Returns:** Company name, contact info, location, capabilities, and more

### 🌐 Real-time Web Search (OpenAI Integration)
Detects current information requests and performs live web search:

**Auto-triggers on queries like:**
- "What's the current weather in New York?"
- "Latest news about AI"
- "Stock price of Tesla today"
- "What's happening right now in the market?"

**Returns:** Up-to-date information from web sources

### 🧠 Intelligent Tool Routing
Smart query analysis automatically selects the best tools:
- **Company queries** → Databricks search
- **Current events** → Web search  
- **Combined queries** → Both tools simultaneously
- **General chat** → Standard conversation

## Technical Implementation

### Cloud-Ready Architecture
- **Temporal Cloud** integration for production scalability
- **Docker deployment** with auto-scaling worker replicas
- **Connection pooling** for database efficiency
- **Load testing** framework for performance validation

### Session & Memory Management
- **Configurable timeouts** (default: 5 minutes inactivity)
- **Smart context management** with automatic summarization
- **User-associated sessions** with persistent history
- **Token optimization** to prevent context window overflow

### Enhanced Database Operations
- **Real-time persistence** of all conversations
- **User authentication** and session association
- **Scalable connection pooling** (20 base + 30 overflow connections)
- **Multi-table schema** for users, conversations, and summaries

### AI Model Integration
- **Primary Model**: GPT-3.5-turbo for conversations
- **Search Model**: GPT-4o-search-preview for web queries
- **Databricks SDK**: Vector search integration
- **Configurable parameters**: Temperature (0.1), Top-p (0.2), Max tokens (512)

### Modern Web API
- `/api/auth/*` - User authentication (register, login, logout, profile)
- `/api/chat/*` - Enhanced chat operations with tool integration
- **JWT authentication** with secure session management
- **TypeScript APIs** with full type safety

## Current Project Structure

```
chatbot/
├── chatbot_backend/           # Enhanced Python backend
│   ├── activities/            # AI activities (OpenAI, Databricks, Web)
│   ├── workflows/             # Enhanced Temporal workflows
│   ├── shared/               # Database models and utilities
│   ├── worker_cloud.py       # Production worker (Temporal Cloud)
│   ├── worker_local.py       # Development worker
│   ├── client_cloud.py       # Workflow execution client
│   ├── load_test.py          # Performance testing
│   └── docker-compose.yml    # Scalable deployment
├── web-ui/                   # Next.js frontend with auth
│   ├── src/app/api/          # API routes (auth, chat)
│   ├── src/components/       # React components
│   ├── src/lib/              # Database and auth utilities
│   └── package.json          # Dependencies and scripts
├── CLAUDE.md                 # This file (development guide)
└── README.md                 # Project overview
```

# Important Development Notes
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.