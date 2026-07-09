"""
v1 API. Same contract as v0 (POST /api/chat -> {reply}) so the widget and the red-team
config can target it unchanged — just a different port (8001). Also returns the pipeline
`trace` (per-node decisions) for the dashboard / observability.

Optional LangSmith tracing: set in backend-v1/.env
  LANGCHAIN_TRACING_V2=true
  LANGCHAIN_API_KEY=ls-...
  LANGCHAIN_PROJECT=verde-bowl-v1
and every node becomes a visible span (Week-4 instrumentation lesson).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pipeline import run_v1
from seed_data import AUTHENTICATED_USER

app = FastAPI(title="Verde Bowl v1 (defended)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class ChatIn(BaseModel):
    message: str
    history: list = []


@app.post("/api/chat")
def chat(inp: ChatIn):
    reply, trace = run_v1(inp.message, inp.history, AUTHENTICATED_USER)
    return {"reply": reply, "trace": trace}


@app.get("/health")
def health():
    return {"ok": True, "build": "v1"}
