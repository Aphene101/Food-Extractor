# FOOD PDF EXTRACTOR — DEVELOPER TEST PROJECT (2025)

**Author:** Karen Saleh Yousry Saleh Morcos
**Submission:** Developer Test 2025

---

## Overview

The Food PDF Extractor is a full-stack web application that automatically extracts allergens and nutritional values from food product PDF documents.

It supports both digital and scanned PDFs using OCR (Optical Character Recognition) technology. The goal is to provide a structured and readable JSON output that lists key allergens and nutritional information for food labeling and compliance checks.

---

## Technology Stack

Frontend: React (Vite) - Web interface for uploading PDFs and viewing results
Backend: FastAPI - OCR and data extraction service
OCR Engine: Tesseract OCR + OCRmyPDF
Deployment: Backend on Render (Docker) / Frontend on Vercel

---

## Live Deployment

Frontend URL: https://food-extractor-chi.vercel.app/
Backend URL: https://food-extractor-1.onrender.com/

---

## Features

• Upload PDF documents (digital or scanned)
• Automatic OCR text extraction
• Detection of allergens and nutritional values
• JSON and table-based output
• Downloadable OCR text for verification
• Supports Hungarian and English text
• Handles both text-based and image-based (scanned) PDFs

---

## Supported File Types

Format: .pdf
Languages: Hungarian, English

---

## Local Installation

### Requirements

- Python 3.10 or higher
- Node.js 18 or higher
- Tesseract OCR (English + Hungarian)
- Poppler-utils (for pdfplumber)

---

## Backend Setup

1. Open terminal and navigate to backend folder:
   `cd backend`

2. Create and activate virtual environment:
   `python -m venv venv`
   `venv\Scripts\activate` (Windows)
   or
   `source venv/bin/activate` (Mac/Linux)

3. Install dependencies:
   `pip install -r requirements.txt`

4. Run the development server:
   `uvicorn app:app --reload`

Backend runs at: **http://127.0.0.1:8000**

---

## Frontend Setup

1. Navigate to frontend folder:
   `cd frontend`

2. Install dependencies:
   `npm install`

3. Start development server:
   `npm run dev`

Frontend runs at: **http://127.0.0.1:5173**

4. Create a `.env` file in the frontend directory and add:
   `VITE_API_URL=http://127.0.0.1:8000`

---

## Deployment Instructions

### Backend (Render via Docker)

- Base image: Python 3.11
- Installs: Tesseract OCR (English + Hungarian) and Poppler-utils
- Start command:
  `uvicorn app:app --host 0.0.0.0 --port $PORT`

Example Render URL:
https://food-extractor-1.onrender.com

### Frontend (Vercel)

- Root Directory: `frontend`
- Framework Preset: `Vite`
- Environment Variable:
  `VITE_API_URL=https://food-extractor-1.onrender.com`

---

## API Details

### POST /upload

Uploads a PDF file and returns structured allergen and nutrition data.

Example Request:
`curl -F "file=@product.pdf" https://food-extractor-1.onrender.com/upload`

```bash
Example Response:
{
"filename": "example.pdf",
"allergens": {"Milk": "Present", "Egg": "Absent"},
"nutrition": {"Energy": {"value": 223, "unit": "kJ"}},
"notes": ["ocr_applied"]
}

```

---

## Testing Locally

Example:
`curl.exe -F "file=@C:\Users\name\Downloads\sample.pdf" http://127.0.0.1:8000/upload`

Expected:
JSON output listing detected allergens and nutrition values.

---

## Project Structure

Dockerfile

backend/
│ app.py → FastAPI backend (OCR, text extraction, API)
│ requirements.txt → Backend dependencies
│ encoding_test.py → Encoding repair and debugging script

frontend/
│ src/App.jsx → React interface for file upload and display
│ index.html → Root HTML entry
│ package.json → Frontend dependencies

---

## Example Output

```bash
{
"filename": "90327_HC ZSÍROLDÓ COMBI GRILL.pdf",
"allergens": {
"Milk": "Absent",
"Egg": "Absent",
"Soy": "Absent"
},
"nutrition": {
"Energy": {"value": 223, "unit": "kJ"}
},
"notes": ["ocr_applied", "tables_found:1"]
}
```

---

## Developer Notes

• OCR fallback logic and encoding repair are implemented in `app.py`
• Encoding repair tests can be run using `encoding_test.py`
• Frontend communicates with backend via simple `POST /upload` endpoint
• Dockerfile includes all OCR dependencies for seamless Render deployment
