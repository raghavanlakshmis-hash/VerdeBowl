from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent import run_agent
from seed_data import AUTHENTICATED_USER

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatIn(BaseModel):
    message: str
    history: list = []

@app.post("/api/chat")
def chat(inp: ChatIn):
    reply, _ = run_agent(inp.message, inp.history, AUTHENTICATED_USER)
    return {"reply": reply}
