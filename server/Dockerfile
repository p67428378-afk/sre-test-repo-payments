FROM python:3.12-slim

WORKDIR /app

# Install dependencies (paths are relative to repo root build context)
COPY server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server/ ./server/

# Cloud Run requires the container to listen on port 8080
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "python -m uvicorn server.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
