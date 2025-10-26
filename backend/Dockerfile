# Use a slim Python base
FROM python:3.11-slim

# system deps for OCR and PDF processing
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

# copy project files
COPY backend/requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app

# expose port
ENV PORT=8000
EXPOSE 8000

# Start uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]