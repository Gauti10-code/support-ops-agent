import os
import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite import SqliteSaver
from schemas import ChatRequest, ChatResponse, ApprovalRequest, HealthResponse
from agent import run_agent, resume_agent
from database import test_connection

load_dotenv()

app = FastAPI(
    title="Support Ops Agent API",
    description="AI-powered support agent with order lookup, refund eligibility, RAG policy search, and human-approved refund execution",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CHECKPOINTS_DB = "checkpoints.db"

# ---------- Endpoints ----------

@app.get("/health", response_model=HealthResponse)
def health_check():
    db_status = "connected" if test_connection() else "disconnected"
    return HealthResponse(status="ok", version="1.0.0", database=db_status)

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    try:
        with SqliteSaver.from_conn_string(CHECKPOINTS_DB) as checkpointer:
            result = run_agent(request.message, session_id, checkpointer)
        return ChatResponse(
            response=result["reply"],
            session_id=session_id,
            tools_used=result["tools_used"],
            pending_approval=result["pending_approval"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/approve/{session_id}", response_model=ChatResponse)
def approve(session_id: str, request: ApprovalRequest):
    try:
        with SqliteSaver.from_conn_string(CHECKPOINTS_DB) as checkpointer:
            result = resume_agent(request.approved, session_id, checkpointer)
        return ChatResponse(
            response=result["reply"],
            session_id=session_id,
            tools_used=result["tools_used"],
            pending_approval=False
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history/{session_id}")
def get_history(session_id: str):
    try:
        with SqliteSaver.from_conn_string(CHECKPOINTS_DB) as checkpointer:
            from agent import build_graph
            graph = build_graph(checkpointer)
            config = {"configurable": {"thread_id": session_id}}
            state = graph.get_state(config)
            if not state or not state.values:
                raise HTTPException(status_code=404, detail="Session not found")
            messages = [
                {"role": msg.type, "content": msg.content}
                for msg in state.values["messages"]
                if hasattr(msg, "content") and msg.content
            ]
            return {"session_id": session_id, "messages": messages}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/history/{session_id}")
def clear_history(session_id: str):
    return {"message": f"Session {session_id} cleared", "session_id": session_id}