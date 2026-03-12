# Smart Campus Assistant 🎓

An AI chatbot that answers campus questions in Hebrew or English.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenAI API key

### Setup

1. **Copy .env template**
   ```bash
   cp .env.example .env
   ```

2. **Add your OpenAI API key to .env**
   ```bash
   OPENAI_API_KEY=sk-proj-xxxxx...
   ```

3. **Start the project**
   ```bash
   docker compose up --build
   ```

4. **Open in browser**
   - Frontend: http://localhost
   - API Docs: http://localhost:8000/docs

## What It Does

Answers questions about:
- **Exam schedules** and office hours
- **Room locations** and campus navigation
- **Technical support** (passwords, login, Wi-Fi)
- **Grades and appeals**
- **Library services**
- **Student housing and events**

Ask in Hebrew or English — responds in your language.


## How it works

1. User asks a question (Hebrew or English)
2. Backend classifies question into 6 categories using keyword matching
3. Fetches relevant data from SQLite database
4. Sends to OpenAI GPT-4o-mini with system prompt + database context
5. AI returns answer grounded only in database (no hallucination)
6. Frontend displays plain-text response in chat

## API Usage

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "מתי המבחן?", "session_id": "user-123"}'
```

Response:
```json
{
  "answer": "The exam is on March 15, 2026 at 14:00",
  "category": "schedule"
}
```

## Configuration

Edit `.env`:
```bash
OPENAI_API_KEY=sk-proj-xxxxx...
OPENAI_MODEL=gpt-4o-mini
AI_TEMPERATURE=0.2
AI_TIMEOUT_SECONDS=10.0
```

## Documentation
- [API Docs](http://localhost:8000/docs) — Interactive Swagger UI

---

Built with FastAPI + React + GPT-4o-mini
