import os
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

app = FastAPI()

# Set up the templates directory relative to this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.get("/")
async def read_root(request: Request):
    # FIXED: Explicitly define the request and name parameters
    return templates.TemplateResponse(request=request, name="chat_page.html")