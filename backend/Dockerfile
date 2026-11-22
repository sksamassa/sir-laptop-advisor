FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY migrations ./migrations
COPY src ./src

EXPOSE 8000
# Render (and most PaaS hosts) inject PORT; honour it, falling back to 8000 locally.
CMD ["sh", "-c", "exec uvicorn laptop_dss.main:app --host 0.0.0.0 --port \"${PORT:-8000}\" --app-dir /app/src"]
