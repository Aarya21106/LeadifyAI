# Leadify AI

Leadify AI is a robust multi-agent AI system designed for autonomous cold email lead management. It acts as an intelligent Sales Development Representative (SDR), automatically identifying leads, managing outreach campaigns, and providing intelligent follow-ups to maximize conversion rates.

## Prerequisites
- Docker & Docker Compose (for containerized local setup)
- Python 3.11+
- Node.js 20+

## Local Setup
1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd LeadifyAI
   ```
2. **Setup environment variables:**
   ```bash
   cp .env.example .env
   ```
   Fill in all necessary API keys inside the `.env` file (Database, Google OAuth, GenAI providers, etc.).

3. **Run using Docker Compose:**
   ```bash
   docker compose up --build
   ```

## Railway Deployment
1. Connect your GitHub repository to Railway.
2. Add a **PostgreSQL** plugin in your Railway project to serve as your Database.
3. Replace the `DATABASE_URL` and configure all other necessary environment variables in the Railway Variables section relying on `.env.example`.
4. Trigger the deployment—Railway will automatically build the React interface and deploy the combined FastAPI application based on the root `Dockerfile` and `railway.toml`.

## Agent Cycle
Leadify utilizes continuous background processes governed by standard intervals (e.g., set by `AGENT_CYCLE_MINUTES`). The agents periodically synthesize pending data, initiate conversational follow-ups, and progress leads along the pipeline automatically without explicit human interaction.

## Screenshot Placeholder
![App Screenshot](https://via.placeholder.com/800x400?text=Leadify+AI+Dashboard)
