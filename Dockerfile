# ---------- Stage 1: Builder ----------
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .

# Install dependencies into user directory for clean multi-stage copy
RUN pip install --no-cache-dir --user -r requirements.txt gunicorn uvicorn[standard]


# ---------- Stage 2: Final runtime image ----------
FROM python:3.11-slim

WORKDIR /app

# Create non-root user with proper home directory
RUN groupadd -r appuser && useradd -r -m -g appuser appuser

# Copy installed packages from builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY . .

# Ensure non-root user owns everything it needs to access
RUN chown -R appuser:appuser /app /home/appuser

# Switch to non-root user
USER appuser

# Make sure Python can find user-installed packages
ENV PATH=/home/appuser/.local/bin:$PATH

EXPOSE 8000

# Health check hits the FastAPI root endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# Run FastAPI with uvicorn (production server)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]