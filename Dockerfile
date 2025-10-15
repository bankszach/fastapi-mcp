
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run will set $PORT
ENV PORT=8080
# Optional: set an API key to require inbound requests to send x-api-key header
# ENV API_KEY=change-me

CMD exec uvicorn app:app --host 0.0.0.0 --port ${PORT} --proxy-headers
