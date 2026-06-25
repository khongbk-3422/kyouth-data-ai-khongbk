import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# NEW: Tell the backend to accept requests from ANY port (like our frontend on 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In a real app, you would put "http://127.0.0.1:8000" here
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_MODEL = "gemini-3-flash-preview"

class ChatRequest(BaseModel):
    prompt: str

@app.post("/chat")
async def chat(request: ChatRequest):
    user_message = request.prompt
    
    try:
        client = genai.Client()
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_message,
        )
        bot_reply = response.text
        
    except Exception as e:
        bot_reply = f"AI Error: {str(e)}"
    
    return {"response": bot_reply}