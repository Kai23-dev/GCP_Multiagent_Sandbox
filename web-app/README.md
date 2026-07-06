# AgentSpace Web App

A Next.js web application that provides a unified interface for interacting with Google Cloud AI services including Agent Engine, Discovery Engine, and base Vertex AI.

## Features

- **Agent Engine Integration**: Chat with your deployed Google ADK agents
- **Discovery Engine Support**: Search through your indexed data stores
- **Vertex AI Direct Access**: Use base Gemini models directly
- **Unified Chat Interface**: Switch between backends seamlessly
- **Real-time Responses**: Stream responses from all AI services
- **Session Management**: Maintain conversation context
- **Modern UI**: Clean, responsive interface built with Tailwind CSS

## Prerequisites

- Node.js 18+ and npm
- Google Cloud Project with the following APIs enabled:
  - Vertex AI API
  - Discovery Engine API (if using Discovery Engine)
  - Agent Engine API
- Service account with appropriate permissions
- Deployed Agent Engine agents (optional but recommended)

## Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment Variables

Copy the example environment file and configure it:

```bash
cp ../.env.example .env.local
```

Edit `.env.local` with your Google Cloud configuration:

```env
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
DEFAULT_AGENT_ID=your-agent-engine-id
```

### 3. Set up Google Cloud Authentication

Either:
- Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to your service account key file
- Or use `gcloud auth application-default login` for development

### 4. Run the Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to see the application.

## Usage

### Agent Engine

1. Click the settings icon in the top right
2. Select "Agent Engine" as the backend
3. Enter your Agent ID (from your deployed agent)
4. Start chatting with your agent

Your deployed agent ID is: `3931281834880532480`

### Discovery Engine

1. Select "Discovery Engine" as the backend
2. Enter your Data Store ID
3. Search through your indexed documents

### Vertex AI

1. Select "Vertex AI" as the backend
2. Choose your preferred Gemini model
3. Adjust temperature and other parameters
4. Chat directly with the base model

## API Routes

The application includes three main API routes:

- `/api/agent-engine` - Interface with Agent Engine
- `/api/discovery-engine` - Search Discovery Engine data stores
- `/api/vertex-ai` - Direct Vertex AI model access

## Project Structure

```
src/
├── app/
│   ├── api/
│   │   ├── agent-engine/route.ts
│   │   ├── discovery-engine/route.ts
│   │   └── vertex-ai/route.ts
│   ├── globals.css
│   ├── layout.tsx
│   └── page.tsx
└── components/
    └── ChatInterface.tsx
```

## Configuration

### Agent Engine

- Requires a deployed Agent Engine (reasoning engine)
- Uses the Agent ID to route requests
- Supports session management for conversation continuity

### Discovery Engine

- Requires a configured data store
- Supports search filters and query expansion
- Returns structured search results with snippets

### Vertex AI

- Direct access to Gemini models
- Configurable temperature, top-p, top-k parameters
- Built-in safety settings

## Deployment

### Vercel (Recommended)

1. Push your code to GitHub
2. Connect your repository to Vercel
3. Add environment variables in Vercel dashboard
4. Deploy

### Google Cloud Run

1. Build the application:
   ```bash
   npm run build
   ```

2. Create a Dockerfile:
   ```dockerfile
   FROM node:18-alpine
   WORKDIR /app
   COPY package*.json ./
   RUN npm ci --only=production
   COPY . .
   RUN npm run build
   EXPOSE 3000
   CMD ["npm", "start"]
   ```

3. Deploy to Cloud Run:
   ```bash
   gcloud run deploy agentspace-web --source .
   ```

## Troubleshooting

### Authentication Issues

- Ensure your service account has the necessary permissions:
  - `aiplatform.endpoints.predict`
  - `discoveryengine.conversations.converse`
  - `aiplatform.reasoningEngines.query`

### Agent Engine Errors

- Verify your Agent ID is correct
- Check that the agent is deployed and running
- Ensure the agent is in the same project and location

### Discovery Engine Issues

- Confirm your data store ID is correct
- Verify the data store is in the same project
- Check that documents are properly indexed

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License - see LICENSE file for details
