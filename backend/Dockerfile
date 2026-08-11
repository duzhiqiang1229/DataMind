FROM python:3.12-slim AS backend

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

RUN chmod +x /app/docker-entrypoint.sh

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]

# The in-process scheduler must have a single owner. Scale it out only after
# moving scheduling to a dedicated worker or adding a distributed lock.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
