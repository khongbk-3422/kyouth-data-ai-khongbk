from typing import List, Optional
from fastapi import FastAPI, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Import your cleanly separated utility functions!
from .utils.ollama_utils import get_downloaded_models
from .utils.gemini_utils import get_gemini_models
from .utils.chat_utils import generate_chat_response

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = "http://host.docker.internal:11434/api/generate"


class ChatRequest(BaseModel):
    prompt: str
    model_choice: str


@app.get("/models")
async def list_models():
    local_models = get_downloaded_models()
    gemini_models = get_gemini_models()

    return {"gemini_models": gemini_models, "ollama_models": local_models}


@app.post("/chat")
async def chat(
    prompt: str = Form(...),
    model_choice: str = Form(...),
    files: Optional[List[UploadFile]] = File(
        None
    ),  # Optional, because they might just type a message!
):

    # Hand off all the heavy lifting to your new chat_utils file
    bot_reply = await generate_chat_response(prompt, model_choice, files)

    return {"response": bot_reply}
