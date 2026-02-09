# Setup Guide: Enterprise LangGraph Agent

This guide covers the installation, configuration, and execution of the Enterprise LangGraph Agent.

## 1. Prerequisites

Before starting, ensure you have the following installed:
-   **Python 3.10+**: required for modern async and typing features.
-   **Redis**: Required for persistent state management.
    -   *Windows*: Use WSL or Run via Docker: `docker run -d -p 6379:6379 redis`
    -   *Fallback*: The system will fall back to in-memory storage if Redis is unavailable (state will be accepted but lost on restart).
-   **OpenAI API Key**: Required for the Router and LLM nodes.

## 2. Installation

1.  **Navigate to the project directory**:
    ```powershell
    cd enterprise_agent
    ```

2.  **Create and Activate Virtual Environment**:
    ```powershell
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install Dependencies**:
    ```powershell
    pip install -r requirements.txt
    ```

## 3. Project Structure

```bash
enterprise_agent/
├── app/
│   ├── api/            # FastAPI server and endpoints
│   ├── core/           # Configuration and State definitions
│   ├── agent/          # Graph logic and Tools
│   └── services/       # Middleware, Checkpointer, Redis
├── venv/               # Virtual environment
├── requirements.txt
├── README.md
└── verification_script_v2.py
```

## 4. Configuration

The application uses `config.py` which loads environment variables. You can create a `.env` file in the `enterprise_agent` root:

```ini
# .env
OPENAI_API_KEY=sk-your-key-here
REDIS_URL=redis://localhost:6379
```

### Advanced Settings (config.py)
-   `KB_LLM_MODEL`: Model used for Knowledge Base queries (Default: `gpt-3.5-turbo`).
-   `ACTION_LLM_MODEL`: Model used for Routing and Structured Output (Default: `gpt-4-turbo`).
-   `PII_REDACTION_ENABLED`: Toggle PII filtering (Default: `True`).

### Local LLM Configuration (Example: Ollama)
To use a local model (e.g., Llama 3 via Ollama) for the Knowledge Base:

1.  **Run Ollama**: `ollama run llama3`
2.  **Update `.env`**:
    ```ini
    KB_LLM_MODEL=llama3
    KB_LLM_BASE_URL=http://localhost:11434/v1
    KB_LLM_API_KEY=ollama
    ```

**Note**: For `ACTION_LLM_MODEL`, ensure the local model supports **Structured Outputs** (Function Calling) effectively. Otherwise, sticking to GPT-4o/Turbo is recommended for the Router.

## 5. Running the Application

### Start the FastAPI Server
Run the following command to start the agent API:

```powershell
uvicorn enterprise_agent.app.api.server:app --reload
```

-   **API Root**: `http://localhost:8000`
-   **Swagger UI**: `http://localhost:8000/docs`

### Running Verification Tests
To verify the installation and agent logic (using Mocks):

```powershell
python verification_script_v2.py
```

## 6. Usage

### Chat Endpoint
**POST** `/chat`

*New Session (Auto-generate ID)*:
```json
{
  "message": "Update my email",
  "user_id": "user_123",
  "access_token": "optional_bearer_token"
}
```

*Continue Session*:
```json
{
  "message": "Yes, proceed.",
  "thread_id": "returned_uuid_from_previous_call",
  "user_id": "user_123"
}
```

### Approval Endpoint (HITL)
**POST** `/approve`
```json
{
  "thread_id": "session_1",
  "approved": true
}
```
