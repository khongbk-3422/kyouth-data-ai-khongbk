import sys
import os
import time
import ollama
from google import genai
from dotenv import load_dotenv

load_dotenv()

def prompt_model(model: str, prompt: str) -> str:
    try:
        # Route 1: Local Ollama Models
        if model in ["llama3.1", "phi3", "deepseek-r1:1.5b"]:
            response = ollama.generate(model=model, prompt=prompt)
            return response.get('response', '')
            
        # Route 2: Cloud Gemini Models
        elif "gemini" in model:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                return "[Gemini Error] GOOGLE_API_KEY not found in .env file."
                
            client = genai.Client(api_key=api_key)
            
            # --- NEW: Retry loop for 503 Server Errors ---
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model=model,
                        contents=prompt,
                    )
                    return response.text
                except Exception as e:
                    # If it's the last attempt, raise the error to be caught by the main block
                    if attempt == max_retries - 1:
                        raise e
                    # Otherwise, wait 2 seconds and try again
                    time.sleep(2)
            
        else:
            return f"Error: Model '{model}' is not recognized."
            
    except Exception as e:
        system = "Gemini" if "gemini" in model else "Ollama"
        return f"[{system} Error] {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: uv run prompt_model.py <model_name> <\"your prompt here\">")
        sys.exit(1)
        
    model_name = sys.argv[1]
    prompt_text = sys.argv[2]
    
    response_text = prompt_model(model_name, prompt_text)
    
    print("\n--- RESPONSE ---\n")
    print(response_text)