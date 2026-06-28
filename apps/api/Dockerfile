# Aether Clinician API
FROM python:3.12-slim

WORKDIR /app

# System deps: Tesseract (OCR fallback, eng+hin) and build essentials.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# App code + migrations + seed data.
COPY apps/api ./apps/api
COPY data ./data

WORKDIR /app/apps/api
ENV PYTHONPATH=/app/apps/api
EXPOSE 8000

# Apply migrations, seed reference data, then serve.
CMD ["sh", "-c", "python -m alembic -c ../../data/migrations/alembic.ini upgrade head && python -m app.db.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
