# BIM Evacuation System - Dockerfile
FROM python:3.10-slim

WORKDIR /app

# System dependencies (ifcopenshell + scientific stack may need these)
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    libxml2-dev \
    libxslt1-dev \
    libz-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Upgrade pip tooling (important for wheel resolution)
RUN pip install --upgrade pip setuptools wheel

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install spaCy model (do not put en-core-web-sm in requirements.txt)
RUN python -m spacy download en_core_web_sm

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY data/ ./data/

# Create output directory
RUN mkdir -p outputs

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "src/ui/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
