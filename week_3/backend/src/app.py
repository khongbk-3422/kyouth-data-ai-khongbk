import os
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv

from .utils.ollama_utils import get_downloaded_models 
from .utils.gemini_utils import get_gemini_models

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
    
    return {
        "gemini_models": gemini_models,
        "ollama_models": local_models
    }

@app.post("/chat")
async def chat(request: ChatRequest):
    user_message = request.prompt
    choice = request.model_choice 
    
    try:
        if choice.startswith("gemini"):
            client = genai.Client()
            response = client.models.generate_content(
                model=choice, 
                contents=user_message,
            )
            bot_reply = f"[{choice}] {response.text}"
            
        elif choice.startswith("ollama-"):
            
            actual_model = choice.replace("ollama-", "", 1)
            
            payload = {
                "model": actual_model, 
                "prompt": user_message,
                "stream": False
            }
            response = requests.post(OLLAMA_URL, json=payload)
            response.raise_for_status() 
            data = response.json()
            bot_reply = f"[{actual_model}] {data.get('response', 'No response.')}"

        else:
            bot_reply = "Error: Unknown model routing."

    except Exception as e:
        bot_reply = f"System Error: {str(e)}"
    
    return {"response": bot_reply}