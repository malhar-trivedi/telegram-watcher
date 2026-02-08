FROM python:3.9-slim

WORKDIR /app

# Install system dependencies if needed (none for now)

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Healthcheck: Application writes to /tmp/heartbeat. If stale (>2m), restart.
HEALTHCHECK --interval=2m --timeout=10s --retries=3 \
    CMD python healthcheck.py || exit 1

# Run the bot
CMD ["python", "-u", "main.py"]
