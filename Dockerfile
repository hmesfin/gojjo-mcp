# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Copy documentation and configuration
COPY . .

# Remove unnecessary files to keep image clean
RUN rm -rf .git .env* __pycache__ *.pyc .pytest_cache .coverage \
    && find . -name "*.pyc" -delete \
    && find . -name "__pycache__" -delete

# Create startup script that handles both modes
RUN echo '#!/bin/bash\nset -e\nif [ "$HTTP_MODE" = "true" ]; then\n  echo "Starting OAuth web server (simple)..."\n  exec python src/web_mcp_server_simple.py\nelse\n  echo "Starting MCP protocol server..."\n  exec python src/django_vue_mcp_server.py\nfi' > /app/start.sh && \
    chmod +x /app/start.sh

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose ports for MCP server and health checks
EXPOSE 8000 8080

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command - uses startup script to choose mode
CMD ["/app/start.sh"]