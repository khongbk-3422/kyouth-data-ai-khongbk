# Use your specific Python 3.14.5 image
FROM python:3.14.5-bookworm

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory
WORKDIR /app

# Copy the dependency files first
COPY pyproject.toml .

# Install dependencies using uv
RUN uv pip install --system fastapi uvicorn pydantic requests google-genai python-dotenv

# Copy the rest of your application code
COPY . .

# Expose port 8000 inside the container
EXPOSE 8000

# Run the FastAPI server using app.py
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]