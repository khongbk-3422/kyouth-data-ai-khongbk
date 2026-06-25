# Use your specific Python version
FROM python:3.14.5-bookworm 

# Install uv directly from astral-sh
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory inside the container
WORKDIR /app

# Copy the lockfile and pyproject.toml first for caching
COPY pyproject.toml uv.lock ./

# Install the dependencies using uv
RUN uv sync --frozen --no-dev

# Copy the rest of the source code
COPY src ./src

# Set the entrypoint and command to run the server
ENTRYPOINT ["uv", "run", "uvicorn"]
CMD ["--app-dir", "src", "--host", "0.0.0.0", "app:app"]