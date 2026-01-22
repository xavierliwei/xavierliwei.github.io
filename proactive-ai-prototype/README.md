# Proactive AI Assistant Prototype

A prototype implementation of a proactive AI assistant that combines recommendation systems with conversational AI. Based on the blog post ["What If Your AI Started the Conversation?"](https://xavierliwei.github.io/blog/2026-01-15-proactive-ai-recsys-llm)

**✨ Key Features:**
- 🤖 Proactive AI that initiates conversations based on user interests
- 💬 Smart chat interface with both mock (dev) and Claude API (production) support
- 🎯 Personalized recommendations using multi-factor scoring
- ⏰ Intelligent timing with receptivity detection
- 📊 Transparency panel showing why suggestions are made

## Quick Start

### 1. Start the Backend

```bash
cd backend

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server (uses mock responses by default)
uvicorn app.main:app --reload --port 8000
```

The API will be available at http://localhost:8000

**🚀 Want real AI?** See [CLAUDE_API_SETUP.md](CLAUDE_API_SETUP.md) to configure Claude API (just add an API key to `.env`)

### 2. Start the Frontend

Simply open `frontend/index.html` in your browser, or use a local server:

```bash
cd frontend
python -m http.server 3000
```

Then visit http://localhost:3000

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (Vanilla JS)                    │
│   - Chat interface with proactive suggestions               │
│   - User onboarding flow                                     │
│   - Suggestion cards sidebar                                 │
│   - Settings and transparency panels                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                        │
├─────────────────────────────────────────────────────────────┤
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│   │  Retrieval  │→ │   Ranking   │→ │ Conversation │        │
│   │   Service   │  │   Service   │  │   Service    │        │
│   └─────────────┘  └─────────────┘  └─────────────┘        │
│          │                │                │                │
│          ▼                ▼                ▼                │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│   │    Text     │  │   Trigger   │  │Chat Provider│        │
│   │  Similarity │  │   Decision  │  │ Mock/Claude │        │
│   │   (TF-IDF)  │  │   Service   │  │             │        │
│   └─────────────┘  └─────────────┘  └─────────────┘        │
│                          │                                   │
│                          ▼                                   │
│                  ┌─────────────┐                             │
│                  │  Data Store │ (JSON-based MVP)           │
│                  └─────────────┘                             │
└─────────────────────────────────────────────────────────────┘
```

## Project Structure

```
proactive-ai-prototype/
├── README.md                   # This file
├── CLAUDE_API_SETUP.md        # Claude API setup guide
│
├── frontend/
│   ├── index.html             # Main HTML page with onboarding
│   ├── styles.css             # CSS styles
│   └── app.js                 # Frontend JavaScript
│
└── backend/
    ├── .env.example           # Environment configuration template
    ├── requirements.txt       # Python dependencies
    │
    ├── app/
    │   ├── main.py            # FastAPI app and endpoints
    │   ├── models.py          # Data models
    │   ├── config.py          # Configuration management
    │   ├── chat_provider.py   # Chat provider abstraction
    │   ├── conversation.py    # Conversation orchestrator
    │   ├── recommendation.py  # Recommendation engine
    │   ├── trigger.py         # Trigger decision service
    │   ├── text_similarity.py # TF-IDF text similarity
    │   └── data_store.py      # Data persistence layer
    │
    └── data/
        └── candidates.json    # Sample recommendation data
```

## Key Features

### Recommendation Engine
- **Three-stage pipeline**: Retrieval → Ranking → Selection
- **Multi-factor scoring**: Interest match (40%), activity relevance (30%), engagement (15%), recency (10%), timing (5%)
- **Diversity control**: Prevents repetitive suggestions
- **Feedback loop**: Learns from user interactions

### Conversation Service
- **Pluggable providers**: Easy to switch between mock and Claude API
- **Context-aware**: Maintains conversation history and context
- **Topic expertise**: Specialized responses for technical domains
- **Proactive messaging**: Generates natural conversation openers

### Trigger Decision Service
- **Smart timing**: Respects user preferences and context
- **Receptivity scoring**: Predicts optimal engagement times
- **Snooze support**: User-controlled notification pausing
- **Quality threshold**: Only triggers on high-quality recommendations

### Text Similarity
- **TF-IDF indexing**: Fast semantic search
- **Query expansion**: Domain-specific synonym matching
- **Cosine similarity**: Accurate content matching

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Send message, get AI response |
| `/api/recommendations` | GET | Get personalized recommendations |
| `/api/trigger/check` | POST | Check if proactive message should be sent |
| `/api/search` | POST | Semantic search with query expansion |
| `/api/feedback` | POST | Record user feedback |
| `/api/preferences` | PUT | Update user preferences |
| `/api/snooze` | POST | Snooze notifications |
| `/api/analytics` | GET | Get system analytics |

**Full API documentation**: See inline examples and OpenAPI docs at http://localhost:8000/docs

### Example: Chat with the Assistant

```bash
curl -X POST "http://localhost:8000/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_user",
    "message": "Tell me about distributed systems"
  }'
```

### Example: Get Recommendations

```bash
curl "http://localhost:8000/api/recommendations?user_id=demo_user&limit=5"
```

## Configuration

### Development Mode (Default)
No configuration needed! Just run the server and it uses smart mock responses.

### Production Mode (Claude API)
1. Copy `.env.example` to `.env`
2. Add your Claude API key from [console.anthropic.com](https://console.anthropic.com/)
3. Choose a model (default: Haiku - cheapest and fastest)
4. Restart the server

**Detailed guide**: See [CLAUDE_API_SETUP.md](CLAUDE_API_SETUP.md)

## Design Principles

### Modular & Extensible
Each component has a clear interface and can be easily replaced:

- **Chat Provider**: Switch between mock, Claude, OpenAI, or local models
- **Data Store**: Replace JSON with PostgreSQL, MongoDB, etc.
- **Text Similarity**: Upgrade from TF-IDF to embeddings (sentence-transformers)
- **Ranking**: Add ML models trained on feedback data
- **Trigger Logic**: Enhance with learned engagement patterns

### Transparent & User-Controlled
- **Explanation signals**: Users see why recommendations were made
- **Preference controls**: Frequency, topics, time windows
- **Snooze functionality**: User-controlled pausing
- **Feedback collection**: Continuous improvement

## Roadmap

- [x] **Claude API Integration** - Pluggable chat providers with mock and Claude support
- [ ] **Vector Search** - Semantic embeddings with sentence-transformers
- [ ] **ML-based Ranking** - Learn from user feedback
- [ ] **WebSocket Support** - Real-time bidirectional communication
- [ ] **User Authentication** - Secure multi-user support
- [ ] **Database Storage** - PostgreSQL/MongoDB for persistence
- [ ] **A/B Testing** - Experiment framework for optimization
- [ ] **Analytics Dashboard** - Visualize engagement metrics
- [ ] **Calendar Integration** - Context-aware timing

## Technical Stack

- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Backend**: FastAPI (Python), Pydantic for validation
- **AI**: Anthropic Claude API (with mock fallback)
- **Storage**: JSON (MVP) - easily upgradeable
- **Search**: TF-IDF with cosine similarity

## Contributing

This is a prototype demonstrating the concepts from the blog post. Key areas for improvement:

1. Add vector embeddings for better semantic search
2. Implement ML-based ranking models
3. Add user authentication and multi-tenancy
4. Replace JSON storage with a real database
5. Add WebSocket support for real-time updates

## License

MIT License - Feel free to use this as a starting point for your own projects!

## Related Resources

- **Blog Post**: [What If Your AI Started the Conversation?](https://xavierliwei.github.io/blog/2026-01-15-proactive-ai-recsys-llm)
- **Claude API Setup**: [CLAUDE_API_SETUP.md](CLAUDE_API_SETUP.md)
- **Claude API Docs**: [docs.anthropic.com](https://docs.anthropic.com/)
- **FastAPI Docs**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com/)
