# Support Ops Agent

An AI-powered support operations agent built with LangGraph, FastAPI, and PostgreSQL. The agent handles customer support queries by combining real-time database lookups, RAG over policy documents, and a human-in-the-loop approval gate for sensitive actions like issuing refunds.

## What it does

The agent handles four types of queries autonomously:

- **Order lookup** — queries a PostgreSQL database and returns structured order details (customer, status, items, amount)
- **Refund eligibility check** — applies business rules against live order status to determine if a refund can be processed
- **Policy search** — uses RAG (Retrieval-Augmented Generation) to answer questions from a company policy PDF without hallucinating
- **Issue refund** — executes a refund, but only after a human explicitly approves the action via a separate API call

## Architecture

```
POST /chat
    ↓
FastAPI (main.py)
    ↓
LangGraph agent (agent.py)
    ↓
route_after_llm() decides:
    ├── safe tools  → get_order_details, check_refund_eligibility, search_policy_docs
    └── sensitive   → issue_refund (PAUSED — waits for POST /approve)
    ↓
PostgreSQL (orders table) + Chroma (policy PDF embeddings)
    ↓
LangSmith tracing on every call
```

The human approval mechanism is built using LangGraph's `interrupt_before` — the graph pauses before executing `issue_refund`, saves its state to SQLite via a checkpointer, and only resumes when `POST /approve/{session_id}` is called with `{"approved": true}`.

## Tech stack

| Layer | Technology |
|---|---|
| Agent framework | LangGraph 1.x |
| LLM | GPT-4o-mini via LangChain OpenAI |
| API | FastAPI + Uvicorn |
| Database | PostgreSQL + SQLAlchemy |
| Vector store | Chroma (local) |
| Embeddings | OpenAI text-embedding-3-small |
| PDF loader | PyPDFLoader (LangChain) |
| Persistence | SQLite checkpointer (LangGraph) |
| Observability | LangSmith |
| Data validation | Pydantic v2 |

## Project structure

```
support-ops-agent/
├── main.py              # FastAPI app — all endpoints
├── agent.py             # LangGraph graph, routing, run_agent(), resume_agent()
├── database.py          # PostgreSQL connection and order queries
├── schemas.py           # Pydantic models for domain objects and API contracts
├── policy_doc.pdf       # Policy document used for RAG
├── rag/
│   ├── ingest.py        # One-time script: load PDF, chunk, embed, save to Chroma
│   └── retriever.py     # Load Chroma, expose search_docs()
├── tools/
│   ├── order_tools.py   # get_order_details, check_refund_eligibility
│   ├── refund_tool.py   # issue_refund (sensitive — requires human approval)
│   └── rag_tool.py      # search_policy_docs (wraps retriever as a LangChain tool)
├── test_agent.py        # End-to-end agent tests
├── test_db.py           # Database connection tests
└── test_tools.py        # Individual tool tests
```

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL running locally
- OpenAI API key
- LangSmith API key (optional but recommended)

### Install dependencies

```bash
pip install fastapi uvicorn psycopg2-binary sqlalchemy langchain langchain-openai \
  langchain-chroma langchain-community langchain-text-splitters chromadb pypdf \
  langgraph langsmith python-dotenv pydantic
```

### Environment variables

Create a `.env` file in the project root:

```
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/capstone_db
LANGCHAIN_API_KEY=ls__...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=support-ops-agent
```

### Database setup

```sql
CREATE DATABASE capstone_db;

\c capstone_db

CREATE TABLE orders (
    order_id VARCHAR(20) PRIMARY KEY,
    customer_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('Pending','Processing','Shipped','Delivered','Cancelled')),
    total_amount NUMERIC(10,2) NOT NULL,
    delivery_date DATE,
    items TEXT[] NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO orders VALUES
('ORD-001','Ravi Sharma','Delivered',2340.00,NULL,ARRAY['Gowardhan Ghee 1L','Go Cheese 200g'],NOW()),
('ORD-002','Priya Mehta','Pending',1200.00,'2026-07-10',ARRAY['Gowardhan Butter 500g'],NOW()),
('ORD-003','Amit Patel','Cancelled',890.00,NULL,ARRAY['Go Paneer 200g'],NOW()),
('ORD-004','Sneha Iyer','Shipped',3100.00,'2026-07-08',ARRAY['Gowardhan Ghee 1L','Pride Cheddar'],NOW()),
('ORD-005','Rohan Gupta','Processing',1750.00,'2026-07-12',ARRAY['Go Cheese Spread 180g'],NOW());
```

### Embed the policy document (run once)

```bash
python rag/ingest.py
```

This chunks the PDF into 474 pieces, embeds them using `text-embedding-3-small`, and saves the vector store to `chroma_db/` on disk. Only needs to run once — subsequent runs detect the existing database and skip.

### Start the API

```bash
uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000/docs` for the interactive Swagger UI.

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Server and database status |
| `POST` | `/chat` | Send a message to the agent |
| `POST` | `/approve/{session_id}` | Approve or deny a pending sensitive action |
| `GET` | `/history/{session_id}` | Retrieve conversation history for a session |
| `DELETE` | `/history/{session_id}` | Clear a session |

## Example usage

### Order lookup

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is in order ORD-001?"}'
```

Response:
```json
{
  "response": "Order ORD-001 belongs to Ravi Sharma. Status: Delivered. Items: Gowardhan Ghee 1L, Go Cheese 200g. Total: ₹2340.00.",
  "session_id": "abc-123",
  "tools_used": ["get_order_details"],
  "pending_approval": false
}
```

### Refund flow with human approval

```bash
# Step 1 — request a refund
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Issue a refund for ORD-003"}'

# Response includes pending_approval: true and a session_id

# Step 2 — approve it
curl -X POST http://localhost:8000/approve/YOUR-SESSION-ID \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

### Policy question (RAG)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Who manages the scheme and what are their qualifications?"}'
```

The agent searches the policy PDF and answers from the retrieved content — it does not hallucinate from training data.

## Key design decisions

**Safe vs sensitive tool separation** — tools are split into two groups. Safe tools (`get_order_details`, `check_refund_eligibility`, `search_policy_docs`) run immediately with no human check since they are read-only operations. The sensitive tool (`issue_refund`) requires explicit human approval because it moves money. This is implemented via two separate `ToolNode` instances and `interrupt_before=["sensitive_tools"]` in the compiled graph.

**RAG grounded answers** — the system prompt instructs the agent to always call `search_policy_docs` for policy questions rather than answering from parametric knowledge. This prevents the LLM from confidently stating outdated or fabricated policy details.

**Session persistence** — conversation state is saved to SQLite via LangGraph's `SqliteSaver` checkpointer. A paused approval session survives server restarts and can be resumed from a different process using the same `session_id`.

**Pydantic schemas throughout** — all tool responses are typed Pydantic models serialized to JSON. This ensures the LLM receives consistently structured data rather than freeform strings, improving reasoning quality and making downstream parsing reliable.

## Running tests

```bash
# Test database connection and queries
python test_db.py

# Test all four tools individually
python test_tools.py

# End-to-end agent tests including approval flow
python test_agent.py
```
