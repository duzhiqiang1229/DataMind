FROM python:3.12-slim AS backend

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run: 2 workers in production, disable docs and debug
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
