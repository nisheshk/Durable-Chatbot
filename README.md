# AI-Powered Chatbot with Enhanced Search & Cloud Deployment

Scalable chatbot system with **Databricks Company Search**, **Real-time Web Search**, and **Temporal Cloud** integration for production deployment.

## ✨ Key Features

- 🏢 **Smart Company Search**: Automatic Databricks vector database integration
- 🌐 **Real-time Web Search**: Current information retrieval with OpenAI search
- 🧠 **Intelligent Tool Routing**: Auto-detects query intent and selects appropriate tools
- ☁️ **Cloud-Ready**: Production deployment with Temporal Cloud
- 🚀 **Scalable**: Docker deployment with auto-scaling workers
- 🔐 **Secure Web UI**: Next.js frontend with JWT authentication
- 📊 **Load Tested**: Performance validated for concurrent usage

## Prerequisites

- Python 3.10+
- Temporal Cloud account (recommended) or Temporal CLI (for local development)
- PostgreSQL database (Neon recommended)
- OpenAI API key
- Databricks workspace (optional, for company search)
- Node.js 18+ (for web UI)

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Clone and navigate to project
cd chatbot_backend

# Install Python dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.cloud.example .env.cloud
# Edit .env.cloud with your credentials (see Configuration section)
```

### 2. Production Deployment (Recommended)
```bash
# Start Temporal Cloud worker
source .env.cloud && python worker_cloud.py

# Test enhanced features (in another terminal)
source .env.cloud && python client_cloud.py "test-session" "Find IT companies in California" 1
source .env.cloud && python client_cloud.py "test-session" "What's the latest news in AI?" 1
```

### 3. Web UI Setup
```bash
cd web-ui
npm install
npm run dev  # Visit http://localhost:3000
```

## 📋 Configuration

### Required Environment Variables

Configure these in `chatbot_backend/.env.cloud`:

```bash
# Temporal Cloud Configuration
TEMPORAL_CLOUD_NAMESPACE=
TEMPORAL_CLOUD_ADDRESS=
TEMPORAL_CLOUD_API_KEY=

# Database Configuration (Neon PostgreSQL)
DATABASE_URL=

# OpenAI Configuration
OPENAI_API_KEY=

# Databricks Configuration (Optional)
DATABRICKS_HOST=
DATABRICKS_TOKEN=
DATABRICKS_ENDPOINT_NAME=
DATABRICKS_INDEX_NAME=

# Additional Settings
JWT_SECRET=
INACTIVITY_TIMEOUT_MINUTES=5
MAX_TOKENS=512
```

## 🤖 Enhanced AI Features

### Smart Tool Selection
The chatbot automatically analyzes your queries and uses the most appropriate tools:

**Company/Supplier Search (Databricks)**
- "Find companies that provide IT services"
- "Search for construction suppliers in Texas"
- "Show me contact details for [company name]"

**Real-time Information (Web Search)**
- "What's the current weather in New York?"
- "Latest news about artificial intelligence"
- "Stock price of Tesla today"

**Combined Queries**
- "Find current suppliers for the latest AI technology"
- "What tech companies are trending in the news?"

**Standard Chat**
- "How do I write a Python function?"
- "Explain machine learning concepts"

### Performance & Scalability
- **Concurrent Sessions**: 20+ simultaneous conversations
- **Response Time**: < 5 seconds average (+ tool execution time)
- **Success Rate**: > 95% under normal load
- **Auto-scaling**: Docker deployment with multiple worker replicas

## 🛠️ Deployment Options

### ☁️ Temporal Cloud (Production)
**Recommended for production use**
```bash
cd chatbot_backend
source .env.cloud && python worker_cloud.py
```

### 🐳 Docker Deployment
**Scalable containerized deployment**
```bash
cd chatbot_backend
docker-compose up --build --scale chatbot-worker=3
```

### 💻 Local Development
**For testing and development**
```bash
# Start local Temporal server
temporal server start-dev

# Start local worker
cd chatbot_backend
source .env.cloud && python worker_local.py
```

### 🧪 Load Testing
```bash
cd chatbot_backend
source .env.cloud && python load_test.py
```

## 🏗️ Project Architecture

```
chatbot/
├── chatbot_backend/                 # Enhanced Python backend
│   ├── activities/
│   │   ├── openai_activities.py     # AI + Databricks + Web Search
│   │   └── agent_tool_selection.py  # Smart tool routing
│   ├── workflows/
│   │   └── chat_workflow.py         # Enhanced workflow logic
│   ├── shared/
│   │   ├── models.py               # Data models
│   │   └── db_schema.sql           # Database schema
│   ├── worker_cloud.py             # Production worker (Temporal Cloud)
│   ├── worker_local.py             # Development worker
│   ├── client_cloud.py             # Workflow execution client
│   ├── load_test.py                # Performance testing
│   ├── test_enhanced_features.py   # Feature test suite
│   └── docker-compose.yml          # Scalable deployment
├── web-ui/                         # Next.js frontend
│   ├── src/app/api/               # API routes (auth, chat)
│   ├── src/components/            # React components
│   ├── src/lib/                   # Auth & database utilities
│   └── package.json               # Dependencies
├── CLAUDE.md                       # Development guide
└── README.md                       # This file
```

## 🔧 Technology Stack

**Backend**
- **Temporal**: Workflow orchestration (Cloud + Local)
- **OpenAI**: GPT-3.5-turbo (chat) + GPT-4o-search-preview (web search)
- **Databricks**: Vector search for company information
- **PostgreSQL**: Conversation persistence (Neon recommended)
- **Python**: FastAPI-style async architecture

**Frontend**
- **Next.js 15**: Modern React framework with App Router
- **TypeScript**: Full type safety
- **Tailwind CSS**: Utility-first styling
- **JWT**: Secure authentication

**DevOps**
- **Docker**: Containerized deployment
- **Docker Compose**: Multi-worker scaling
- **Load Testing**: Performance validation framework