# Use your specific Python 3.14.5 image
FROM python:3.14.5-bookworm

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory
WORKDIR /app

# Copy the project definition files
COPY pyproject.toml uv.lock ./

# Install dependencies (syncs the environment exactly to your lockfile)
RUN uv sync --frozen --no-dev --no-install-project

# Copy the rest of your application code
COPY . .

# Final sync to install your own project code
RUN uv sync --frozen --no-dev

# Expose port 8000 inside the container
EXPOSE 8000

# Run the FastAPI server using the 'uv run' command
CMD ["uv", "run", "uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]