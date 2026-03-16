# GenFlex Creative Storyteller - Docker Configuration
# Use the same Python version as the local development environment
FROM python:3.13.9-slim-bookworm

# Set working directory
WORKDIR /app

# Environment hardening / Docker best practices
ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/app/.venv/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
      curl \
      gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files for caching
COPY pyproject.toml uv.lock ./

# Upgrade pip and install python dependencies
RUN python -m pip install --upgrade pip && \
    pip install uv && \
    uv sync --frozen --no-install-project && \
    # Remove build dependencies to shrink image and reduce attack surface
    apt-get purge -y gcc && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# Copy application code
COPY app/ ./app/
COPY static/ ./static/
COPY run_agent.py ./

# Create logs directory
RUN mkdir -p /app/logs

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start the application
CMD ["uvicorn", "app.fast_api_app:app", "--host", "0.0.0.0", "--port", "8080"]