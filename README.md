# Leadify AI 🚀

**Leadify AI** is an autonomous, multi-agent business-to-business (B2B) lead generation and outreach pipeline. It replaces the manual research and generic sequencing of traditional SDRs with a swarm of specialized AI agents that find, analyze, score, and draft hyper-personalized outreach.

![Leadify Dashboard](leadify/ui/public/vite.svg) *(UI built with a premium Modern Minimalist Dark Theme)*

## 🧠 The Multi-Agent Swarm

Leadify doesn't use a single massive prompt. It breaks down the sales process into an assembly line of specialized agents:

1. **🕵️ Finder Agent**: Semantically searches the web and databases for ideal targets based on your Conversational ICP.
2. **👀 Watch Agent**: Monitors companies for active buying signals (e.g., funding rounds, hiring sprees, executive changes).
3. **🗺️ Scout Agent**: Deep-dives into individual prospects, reading their public profiles, podcasts, and articles to extract hyper-personalization anchors.
4. **🎯 Scorer Agent**: Evaluates the gathered intelligence against your Ideal Customer Profile and assigns a clear 0-100 fit score with explicitly stated reasoning.
5. **✍️ Writer Agent**: Drafts highly personalized outreach emails using the Scout Agent's anchors. No template variables.
6. **⚖️ Reviewer Agent**: Evaluates the Writer's drafts. Perfect emails are queued for sending; mediocre emails are sent back for revision.
7. **📤 Sender Agent**: Dispatches approved emails and updates lead statuses.

## 🎨 The Command Center (Frontend)

Built with **React**, **Vite**, **TanStack Query**, and **Framer Motion**, the Leadify dashboard acts as an executive command center rather than a dense developer tool.

- **Conversational Setup**: Dial in your target profile by chatting with the setup wizard.
- **Human-in-the-Loop Queue**: Review, edit, or approve AI-generated drafts before they go out.
- **Live Agent Monitor**: Watch the swarm work in real-time.
- **Linear/Vercel Aesthetic**: High-contrast typography (Inter), glassmorphism, and deep dark-mode drop shadows.

## ⚙️ Backend Architecture

- **FastAPI**: High-performance asynchronous Python backend.
- **SQLite**: Local database for instant persistence (easily swappable to PostgreSQL).
- **Websockets**: Real-time streaming of agent statuses to the frontend.
- **Background Tasks**: The agent swarm runs continuously in the background loop without blocking the main API thread.

## 🚀 Quickstart (Demo Mode)

To run the offline demo (which populates realistic dummy B2B data and simulates the agent pipeline without hitting external APIs):

### 1. Backend Setup
```bash
# From the root directory, install dependencies
pip install -r requirements.txt

# Reset and populate the demo database with 50 realistic leads
python setup_demo.py

# Start the FastAPI server
uvicorn leadify.api.main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd leadify/ui
npm install

# Start the Vite development server
npm run dev -- --port 5173
```
Open your browser to `http://localhost:5173`.

## 🔒 Environment Variables

For production, you'll need to configure the `.env` file with actual API keys for the LLM providers, search API (e.g. Tavily), and your Google OAuth credentials for the Sender Agent.

```env
GEMINI_API_KEY=your_gemini_key
TAVILY_API_KEY=your_tavily_key
ENCRYPTION_KEY=32_byte_base64_encoded_key
DATABASE_URL=sqlite:///./leadify.db
```
