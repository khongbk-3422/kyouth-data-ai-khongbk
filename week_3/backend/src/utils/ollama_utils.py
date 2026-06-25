import requests

def get_downloaded_models():
    """
    Fetches the list of models currently downloaded in Ollama.
    """
    # Use host.docker.internal if connecting to Windows, 
    # or just "http://ollama:11434" if you went back to the separate container!
    base_url = "http://ollama:11434"
    
    try:
        # The /api/tags endpoint lists all installed models
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        response.raise_for_status()
        
        data = response.json()
        
        # Loop through the JSON and extract just the model names (e.g., 'phi3:latest')
        model_names = [model["name"] for model in data.get("models", [])]
        return model_names
        
    except Exception as e:
        print(f"Error fetching Ollama models: {e}")
        return [] # Return an empty list if Ollama is turned off