import os
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define our two models
GEMINI_MODEL = "gemini-3-flash-preview"
OLLAMA_MODEL = "llama3.1"
OLLAMA_URL = "http://ollama:11434/api/generate"

# NEW: We now expect a 'model_choice' from the frontend!
class ChatRequest(BaseModel):
    prompt: str
    model_choice: str 

@app.post("/chat")
async def chat(request: ChatRequest):
    user_message = request.prompt
    choice = request.model_choice
    
    try:
        # --- PATH 1: User chose Gemini ---
        if choice == "gemini":
            client = genai.Client()
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_message,
            )
            bot_reply = f"[Gemini] {response.text}"
            
        # --- PATH 2: User chose Ollama ---
        elif choice == "ollama":
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": user_message,
                "stream": False
            }
            response = requests.post(OLLAMA_URL, json=payload)
            response.raise_for_status() 
            data = response.json()
            bot_reply = f"[Ollama] {data.get('response', 'No response.')}"
            
        else:
            bot_reply = "Error: Unknown model selected."

    except Exception as e:
        bot_reply = f"System Error: {str(e)}"
    
    return {"response": bot_reply}