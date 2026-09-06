FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

# torch's default Linux wheel drags in several hundred MB of separate
# nvidia-* CUDA packages we never use (everything here runs CPU-only, by
# design — SPEC.md section 1). Installing the CPU-only build first means
# the later `pip install .` finds torch already satisfied and skips them.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir .

# Bake the dataset and vector index into the image at build time, so the
# container can start serving immediately once running — no first-request
# cold ingest, and no risk of a health check failing during a multi-minute
# lazy pipeline. This is what makes the image self-contained: a fresh
# `docker build` (or a Hugging Face Space build) needs no external state.
# Real numbers from this pipeline: README.md, "Ingestion measurements" and
# "Indexed corpus scope" — expect this step alone to take ~10-15 minutes.
RUN python -m decp ingest && python -m decp index

# 7860 matches Hugging Face Spaces' Docker SDK convention.
EXPOSE 7860
CMD ["python", "-m", "decp", "serve", "--host", "0.0.0.0", "--port", "7860"]
