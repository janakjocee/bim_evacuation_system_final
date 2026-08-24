# BIM Evacuation System - production container
FROM python:3.14-slim-bookworm

ARG APP_UID=10001
ARG APP_GID=10001

WORKDIR /app

# System dependencies used by the scientific stack and health check.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libxml2-dev \
    libxslt1-dev \
    libz-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid "${APP_GID}" app \
    && useradd --uid "${APP_UID}" --gid app --create-home --shell /usr/sbin/nologin app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Upgrade pip tooling (important for wheel resolution)
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel

# Install Python dependencies
RUN python -m pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=app:app src/ ./src/
COPY --chown=app:app config/ ./config/
COPY --chown=app:app data/ ./data/
# Keep root multipage sources available for direct execution and backwards
# compatibility. Deployed sidebar pages are self-contained under src/ui/pages.
COPY --chown=app:app pages/ ./pages/
COPY --chown=app:app .streamlit/ ./.streamlit/

# Writable runtime locations are explicit so the application can run with a
# read-only root filesystem under Docker Compose.
RUN mkdir -p outputs logs \
    && chown -R app:app outputs logs

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

USER app

CMD ["streamlit", "run", "src/ui/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
