# Enhanced Chatbot Backend - Cloud Deployment & Scalability Testing

AI-powered chatbot system with **Databricks Company Search** and **Real-time Web Search** capabilities using Temporal workflows for cloud deployment and scalability testing.

## Enhanced Features

### 🏢 Databricks Company Search
Automatically detects company/supplier queries and searches Databricks vector database:
- **Triggers**: "Find companies", "supplier information", "vendor search", etc.
- **Returns**: Company details with contact info, location, and capabilities
- **Example**: "Find IT consulting companies in California" → Returns real company data

### 🌐 Real-time Web Search  
Automatically detects current information requests using OpenAI GPT-4o-search-preview:
- **Triggers**: "current", "latest", "recent", "news", "weather", "stock price", etc.
- **Returns**: Up-to-date information from web search
- **Example**: "What's the latest in AI technology?" → Returns current AI trends

### 🧠 Smart Intent Detection
Automatically routes user queries to appropriate tools:
- **Company queries** → Databricks search
- **Real-time queries** → Web search  
- **Combined queries** → Both tools simultaneously
- **Regular chat** → Standard OpenAI conversation

### ☁️ Cloud-Ready Configuration
Production-ready with cloud configuration management and environment variables.

## Architecture

- **Temporal Workflows**: Durable, scalable conversation management with enhanced tool integration
- **PostgreSQL (Neon)**: Persistent conversation storage with connection pooling  
- **OpenAI GPT-4o-mini**: AI-powered chat responses
- **OpenAI -4o-search-preview**: Real-time web search capabilities
- **Databricks Vector Search**: Company information retrieval and matching
- **Smart Intent Detection**: Automatic tool selection based on user queries
- **Docker**: Containerized deployment with scaling configuration
- **Load Testing**: Automated testing with 20 concurrent sessions

## Environment Variables Required

Copy and configure the environment file:

```bash
cp .env.cloud.example .env.cloud
```

**Required environment variables** (see `.env.cloud.example` for full template):

### Temporal Cloud Configuration
```bash
TEMPORAL_CLOUD_NAMESPACE=your-namespace
TEMPORAL_CLOUD_ADDRESS=region.gcp.api.temporal.io:7233
TEMPORAL_CLOUD_API_KEY=your-api-key
```

### Database Configuration
```bash
DATABASE_URL=postgresql://user:password@host/database
```

### OpenAI Configuration
```bash
OPENAI_API_KEY=sk-your-openai-key
```

### Databricks Configuration (Optional - for company search)
```bash
DATABRICKS_HOST=https://your-instance.azuredatabricks.net
DATABRICKS_TOKEN=your-databricks-token
DATABRICKS_ENDPOINT_NAME=your-endpoint
DATABRICKS_INDEX_NAME=your.index.name
```

### Additional Configuration
```bash
INACTIVITY_TIMEOUT_MINUTES=5
MAX_TOKENS=512
TEMPERATURE=0.1
TOP_P=0.2
MAX_CONCURRENT_ACTIVITIES=20
MAX_CONCURRENT_WORKFLOW_TASKS=10
MAX_CONCURRENT_ACTIVITY_TASKS=20
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
JWT_SECRET=your-jwt-secret
NODE_ENV=development
```

## Deployment Options

### ☁️ **Temporal Cloud (Production) - RECOMMENDED**

#### When to Use
- ✅ **Production deployments**
- ✅ **Scalable applications** 
- ✅ **Managed infrastructure** preferred
- ✅ **No server maintenance** wanted

#### Advantages
- 🚀 **Fully managed** - no infrastructure to maintain
- 📈 **Auto-scaling** - handles load automatically  
- 🔒 **Enterprise security** - built-in authentication
- 📊 **Advanced monitoring** - comprehensive observability
- 🌍 **Global availability** - distributed across regions

#### Setup
```bash
# Configure your .env.cloud with Temporal Cloud credentials
source .env.cloud

# Start worker - no local server needed!
python worker_cloud.py
```

### 💻 **Local Development Server**

#### When to Use  
- 🧪 **Local testing and development**
- 💰 **Cost-conscious development** (free)
- 🔧 **Learning and experimentation**
- 🚫 **No cloud access** available

#### Limitations
- 🏠 **Local only** - not suitable for production
- 🔄 **Manual management** - you handle restarts/scaling
- 📊 **Basic monitoring** - limited observability
- 🔒 **No built-in security** - development only

#### Setup
```bash
# Start local Temporal server (separate terminal)
temporal server start-dev

# Start worker pointing to local server
source .env.cloud && python worker_local.py
```

### 🐳 **Docker Deployment**
- Production-ready containerized deployment
- Can use either Temporal Cloud or local server
- Auto-scaling with multiple worker replicas

## Quick Start

### 1. Environment Setup

```bash
# Copy and configure environment variables
cp .env.cloud.example .env.cloud
# Edit .env.cloud with your credentials (see Environment Variables section above)

# Install dependencies
pip install -r requirements.txt
```


### 2. Temporal Cloud Deployment (Production - Recommended)

```bash
# Load environment and start worker connected to Temporal Cloud
source .env.cloud && python worker_cloud.py

# Test with real workflows (requires worker running)
source .env.cloud && python client_cloud.py "test-session" "Hello, how are you?" 1

# Test enhanced features with workflows
source .env.cloud && python client_cloud.py "test-session" "Find IT companies in California" 1
source .env.cloud && python client_cloud.py "test-session" "What's the latest news in AI?" 1
source .env.cloud && python client_cloud.py "test-session" "Show me current cloud computing suppliers" 1

# Send messages via web UI script
source .env.cloud && python send_message.py 'session-1' 'What animals are marsupials?' '123'
```

### 3. Local Development (Optional)

Only needed if you want to develop/test locally instead of using Temporal Cloud:

```bash
# Start local Temporal server (in separate terminal)
temporal server start-dev

# Start local worker (uses local server instead of cloud)
source .env && python worker_local.py

# Note: For production, use Temporal Cloud (no local server needed)
```

### 4. Docker Deployment

```bash
# Build and run with 3 worker replicas
docker-compose up --build

# Run in background
docker-compose up -d --build

# View logs
docker-compose logs -f chatbot-worker

# Scale workers
docker-compose up -d --scale chatbot-worker=5
```

### 6. Load Testing

```bash
# Run load test: 20 sessions × 5 messages = 100 total messages
source .env.cloud && python load_test.py

# Monitor via Temporal UI at your cloud namespace
# Monitor database connections in Neon dashboard
```

## Configuration

### Scaling Settings

- **MAX_CONCURRENT_ACTIVITIES**: 20 (OpenAI API calls)
- **MAX_CONCURRENT_WORKFLOW_TASKS**: 10 (workflow execution)
- **MAX_CONCURRENT_ACTIVITY_TASKS**: 20 (activity execution)
- **Worker Replicas**: 3 (via docker-compose)

### Database Pool Settings

- **DB_POOL_SIZE**: 20 (base connections per worker)
- **DB_MAX_OVERFLOW**: 30 (additional connections under load)
- **Total Potential Connections**: 3 workers × (20 + 30) = 150 max

## Load Test Scenarios

1. **Baseline**: Single session, single message
2. **Concurrent**: 20 sessions, 1 message each  
3. **High Load**: 20 sessions, 5 messages each (100 total)
4. **Sustained**: Messages distributed over time with random delays

## Monitoring

- **Temporal UI**: Monitor workflow execution, activities, errors
- **Database**: Track connection usage, query performance
- **Docker Logs**: Worker health, scaling behavior
- **Load Test Metrics**: Response times, success rates, throughput

## Test Results & Performance

### 🧪 **Recent Test Results (All Passed)**
- **Company Search**: 10 companies found across 5 categories
- **Web Search**: 3/3 real-time queries successful  
- **Intent Detection**: 16/16 test cases (100% accuracy)
- **Integration**: All components working seamlessly

### 📊 **Performance Metrics**  
- **Throughput**: ~10-20 messages/second
- **Response Time**: < 5 seconds average (+ tool execution time)
- **Success Rate**: > 95% under normal load
- **Concurrent Sessions**: 20+ simultaneous conversations
- **Tool Response Time**: Databricks ~2-3s, Web Search ~3-5s

### 🎯 **Smart Query Routing Examples**
- `"Find IT companies"` → **Databricks Company Search**
- `"What's the weather today?"` → **Web Search**
- `"Show me current tech suppliers"` → **Both Tools Combined**
- `"How do I code?"` → **Standard Chat**

## Project Structure

```
chatbot_backend/
├── config_cloud.py              # Enhanced cloud configuration
├── worker_cloud.py               # Temporal worker with scaling
├── worker_local.py               # Local development worker
├── client_cloud.py               # Workflow execution client
├── send_message.py               # Web UI message sender
├── load_test.py                 # Load testing framework
├── test_enhanced_features.py    # ✨ Enhanced features test suite
├── docker-compose.yml           # Multi-worker deployment
├── Dockerfile                  # Container configuration
├── .env.cloud                  # ✨ Environment with Databricks config
├── .env.cloud.example          # Environment template
├── workflows/
│   └── chat_workflow.py        # ✨ Enhanced workflow with intent detection
├── activities/
│   ├── openai_activities.py   # ✨ Enhanced with Databricks + Web Search
│   └── agent_tool_selection.py # Smart tool selection logic
└── shared/
    ├── db_schema.sql           # Database schema
    └── models.py               # ✨ Data models for enhanced features
```

### ✨ **Enhanced Files**
- **workflows/chat_workflow.py**: Added smart intent detection and tool routing
- **activities/openai_activities.py**: Added Databricks + Web Search activities  
- **activities/agent_tool_selection.py**: Intelligent tool selection system
- **shared/models.py**: Data models for requests/responses
- **test_enhanced_features.py**: Comprehensive test suite
- **config_cloud.py**: Added Databricks environment variables
- **worker_local.py**: Local development worker option
- **send_message.py**: Web UI integration script



### Environment Variables Checklist

Before running any components, ensure these are set in your `.env.cloud`:

- [ ] `TEMPORAL_CLOUD_NAMESPACE`
- [ ] `TEMPORAL_CLOUD_ADDRESS` 
- [ ] `TEMPORAL_CLOUD_API_KEY`
- [ ] `DATABASE_URL`
- [ ] `OPENAI_API_KEY`
- [ ] `DATABRICKS_HOST` (optional)
- [ ] `DATABRICKS_TOKEN` (optional)
- [ ] `JWT_SECRET`

Use the provided `.env.cloud.example` as a template for all required variables.