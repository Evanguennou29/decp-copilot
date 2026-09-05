FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

# Placeholder entry point; switched to serving the FastAPI app in lot 3.
CMD ["python", "-m", "decp"]
