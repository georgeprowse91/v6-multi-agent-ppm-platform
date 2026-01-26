# Production Web Console Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose web port
EXPOSE 8501

# Run web console

RUN useradd -m -u 10001 appuser && chown -R appuser:appuser /app

USER appuser

CMD ["uvicorn", "src.main:app", "--host=0.0.0.0", "--port=8501"]
