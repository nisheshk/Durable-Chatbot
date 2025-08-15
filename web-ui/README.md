# Durable Chatbot Web UI

A modern Next.js web interface for the durable chatbot with user authentication and conversation history.

## Features

- 🔐 User authentication (login/register)
- 💬 Real-time chat interface
- 📚 Persistent conversation history
- 🔄 Integration with Temporal workflows
- 🗄️ Neon PostgreSQL database storage
- 🎨 Tailwind CSS styling

## Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.local.example .env.local
   # Edit .env.local with your actual values
   ```

3. **Set up the database:**
   
   Run the user schema SQL in your Neon database:
   ```bash
   psql "your-neon-connection-string" -f src/lib/db-schema-users.sql
   ```

4. **Start the development server:**
   ```bash
   npm run dev
   ```

5. **Make sure your Temporal worker is running:**
   ```bash
   cd ../
   ./session_chat.sh worker
   ```

## Environment Variables

Create a `.env.local` file with:

```env
DATABASE_URL=your-neon-postgresql-connection-string
JWT_SECRET=your-super-secret-jwt-key
OPENAI_API_KEY=your-openai-api-key
NODE_ENV=development
```

## Usage

1. **Register/Login:** Create an account or sign in
2. **Chat:** Start conversations with the AI chatbot
3. **History:** View all your past conversations
4. **Sessions:** Each conversation is automatically saved with a unique session ID

## API Routes

- `POST /api/auth/register` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `GET /api/auth/me` - Get current user
- `POST /api/chat/send` - Send message to chatbot
- `GET /api/chat/history` - Get conversation history

## Architecture

The web UI integrates with the existing Python Temporal chatbot by:

1. Authenticating users and managing sessions
2. Calling the Python chatbot script via child process
3. Storing conversations with user associations in Neon
4. Providing a clean interface to view conversation history

## Build for Production

```bash
npm run build
npm start
```