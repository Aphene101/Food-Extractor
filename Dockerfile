# Dockerfile - Python + Tesseract + Poppler for OCR (production-ready)
FROM python:3.11-slim

# install system deps for OCR and PDFs
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-hun \
    tesseract-ocr-eng \
    ghostscript \
    qpdf \
    poppler-utils \
    build-essential \
    libpoppler-cpp-dev \
    && rm -rf /var/lib/apt/lists/*

# set workdir
WORKDIR /app

# copy only requirements first for better caching
COPY backend/requirements.txt /app/requirements.txt

# python packaging
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r /app/requirements.txt

# copy backend code
COPY backend /app

# healthcheck endpoint (optional, container-level)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s CMD curl -f http://localhost:8000/healthz || exit 1

# expose port (Render will override via $PORT in runtime)
ENV PORT=8000
EXPOSE 8000

# start command — use runtime PORT env variable
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]