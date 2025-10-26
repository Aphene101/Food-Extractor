import os
import tempfile
import subprocess
import shutil
import re
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
import shutil, logging
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def check_tools():
    tools = {
      "tesseract": shutil.which("tesseract"),
      "ghostscript": shutil.which("gswin64c") or shutil.which("gs"),
      "qpdf": shutil.which("qpdf"),
      "pdftoppm": shutil.which("pdftoppm"),
    }
    logging.info("OCR tool availability: %s", tools)
    return tools

TOOLS = check_tools()

# --- FastAPI setup ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # simplify dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Allergen keywords ---
ALLERGEN_KEYWORDS = {
    "Gluten": ["gluten", "glutén", "wheat", "búza", "barley", "árpa", "rye", "rozs", "oats", "zab"],
    "Egg": ["egg", "eggs", "tojás", "tojások"],
    "Crustaceans": ["crustacean", "crustaceans", "rák", "rákfélék", "garnéla", "homár"],
    "Fish": ["fish", "hal"],
    "Peanut": ["peanut", "peanuts", "földimogyoró"],
    "Soy": ["soy", "soya", "soybean", "szója"],
    "Milk": ["milk", "lactose", "dairy", "tej", "tejszín", "tejtermék"],
    "Tree nuts": ["almond", "walnut", "cashew", "hazelnut", "pecan", "pistachio",
                  "mandula", "dió", "kesudió", "mogyoró", "pisztácia", "pekándió", "diófélék"],
    "Celery": ["celery", "zeller"],
    "Mustard": ["mustard", "mustár"]
}

# --- Encoding helpers ---
ACCENTED_CHARS_REGEX = re.compile(r"[ÁáÉéÍíÓóÖöŐőÚúÜüŰű]")

def _accent_count(s: str) -> int:
    return len(ACCENTED_CHARS_REGEX.findall(s or ""))

def fix_text_encoding(text: str):
    """Try to correct mojibake from latin1/utf8 mismatch, prefer accented variant."""
    if not text:
        return text, "no_text"
    variants = {"orig": text}
    try:
        variants["latin1→utf8"] = text.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
    except Exception:
        pass
    try:
        variants["utf8→latin1"] = text.encode("utf-8", errors="ignore").decode("latin-1", errors="ignore")
    except Exception:
        pass
    best_key = max(variants.keys(), key=lambda k: _accent_count(variants[k]))
    return variants[best_key], ("repair:" + best_key if best_key != "orig" else "repair:none")

def force_utf8_filename(name: str) -> str:
    """Ensure safe UTF-8 filename on all OS."""
    try:
        return name.encode("utf-8", "ignore").decode("utf-8")
    except Exception:
        return "uploaded.pdf"

# --- OCR handling ---
def run_ocr_if_needed(input_pdf_path, output_pdf_path):
    """
    Try to use ocrmypdf first (captures stderr and returns it in notes if it fails).
    If ocrmypdf is not available or fails, try a pytesseract/pdf2image fallback.
    Returns tuple: (path_to_text_or_pdf, ocr_note)
      - path_to_text_or_pdf: if ocrmypdf produced a searchable PDF, this is that PDF path;
                             if fallback produced a text file, this is the .txt path;
                             otherwise it's the original input_pdf_path.
      - ocr_note: short note string describing what happened (or error text).
    """
    import sys
    # quick check: is ocrmypdf installed?
    if shutil.which("ocrmypdf") is None:
        # No ocrmypdf — skip to pytesseract fallback below
        ocrmypdf_available = False
    else:
        ocrmypdf_available = True

    # Helper: detect if PDF already contains text (small heuristic)
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(input_pdf_path)
        text_preview = ""
        for p in reader.pages[:3]:
            text_preview += p.extract_text() or ""
        if len(text_preview.strip()) >= 80:
            # likely already contains text; just copy and skip OCR
            shutil.copyfile(input_pdf_path, output_pdf_path)
            return output_pdf_path, "no_ocr_needed"
    except Exception:
        # if PyPDF2 can't read, we'll try OCR
        pass

    # Try ocrmypdf if available
    if ocrmypdf_available:
        try:
            # run and capture output
            proc = subprocess.run(
                ["ocrmypdf", "--deskew", input_pdf_path, output_pdf_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True
            )
            # success
            return output_pdf_path, "ocr_applied"
        except subprocess.CalledProcessError as e:
            # capture stderr for debugging and fall back
            stderr = (e.stderr or "").strip()
            note = f"ocr_failed:{stderr[:1000]}"  # first 1000 chars of stderr
            # fall through to fallback attempt below
        except Exception as e:
            note = f"ocr_failed_unexpected:{str(e)}"
    else:
        note = "ocrmypdf_not_installed"

    # Fallback: try pytesseract (requires pytesseract + pdf2image + poppler/Tesseract installed)
    try:
        # import here so missing packages raise ImportError we can catch
        import pytesseract
        from pdf2image import convert_from_path
        from PIL import Image

        # convert PDF pages to images (this may require poppler)
        images = convert_from_path(input_pdf_path)
        ocr_text_parts = []
        for img in images:
            # use Hungarian+English if tesseract has 'hun' installed; else fallback to 'eng'
            try:
                txt = pytesseract.image_to_string(img, lang="hun+eng")
            except Exception:
                txt = pytesseract.image_to_string(img)
            ocr_text_parts.append(txt)
        combined = "\n\n".join(ocr_text_parts)
        # save as UTF-8 text file
        txt_path = output_pdf_path + ".txt"
        with open(txt_path, "w", encoding="utf-8") as fh:
            fh.write(combined)
        return txt_path, (note + " | pytesseract_ok" if note else "pytesseract_ok")
    except ImportError as ie:
        # pytesseract/pdf2image not installed
        fallback_note = (note + " | pytesseract_missing")
        return input_pdf_path, fallback_note
    except Exception as e:
        # fallback failed
        fallback_note = (note + " | pytesseract_failed:" + str(e))
        return input_pdf_path, fallback_note

# --- Text & table extraction ---
def extract_text_and_tables(pdf_path):
    if pdf_path.endswith(".txt"):  # OCR text fallback
        with open(pdf_path, "r", encoding="utf-8") as f:
            return f.read(), [], ["ocr_text_mode"]

    text, tables, notes = [], [], []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            fixed, note = fix_text_encoding(t)
            text.append(fixed)
            if note != "repair:none":
                notes.append(note)
            tbs = page.extract_tables()
            if tbs:
                tables.extend(tbs)
    return "\n\n".join(text), tables, notes

# --- Allergen & Nutrition extraction ---
def extract_allergens(text):
    results = {}

    NEG_WORDS = ["mentes", "nem tartalmaz", "mentesség", "no", "free from"]

    for allergen, keywords in ALLERGEN_KEYWORDS.items():
        found = False
        for kword in keywords:
            if re.search(r"\b" + re.escape(kword) + r"\b", text, re.IGNORECASE):
                found = True

                for mctx in re.finditer(re.escape(kword), text, re.IGNORECASE):
                    start = max(0, mctx.start() - 25)
                    end = min(len(text), mctx.end() + 25)
                    ctx = text[start:end].lower()
                    if any(nw in ctx for nw in NEG_WORDS):
                        found = False
                        break

                if found:
                    break  # exit keyword loop early if allergen confirmed

        results[allergen] = "Present" if found else "Absent"

    return results

NUTRITION_REGEX = {
    "Energy": r"(?:energy|energia)[^\d]{0,8}([\d.,]+)\s*(k?cal|kj)?",
    "Fat": r"(?:fat|zs[ií]r)[^\d]{0,8}([\d.,]+)\s*(g|mg)?",
    "Carbohydrate": r"(?:carbohydrate|sz[eé]nhidr[aá]t)[^\d]{0,8}([\d.,]+)\s*(g|mg)?",
    "Sugar": r"(?:sugar|cukor)[^\d]{0,8}([\d.,]+)\s*(g|mg)?",
    "Protein": r"(?:protein|feh[eé]rje)[^\d]{0,8}([\d.,]+)\s*(g|mg)?",
    "Sodium": r"(?:sodium|n[aá]trium|salt|s[oó])[^\d]{0,8}([\d.,]+)\s*(g|mg)?"
}

def _normalize_unit(u: str):
    if not u:
        return None
    u = u.lower().strip()
    if u in ("g", "gram", "grams"):
        return "g"
    if u in ("mg", "milligram", "milligrams"):
        return "mg"
    if u in ("kcal", "cal"):
        return "kcal"
    if u in ("kj", "kJ", "kj"):
        return "kJ"
    # keep as-is if we don't recognize but remove whitespace
    return u

def extract_nutrition(text):
    """
    Return dict: { Nutrient: { value: float, unit: str|None, per: '100g', source: 'label', confidence: float } | None }
    """
    result = {}
    for k, pattern in NUTRITION_REGEX.items():
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            num = m.group(1).replace(",", ".").strip()
            unit_raw = (m.group(2) or "").strip()
            try:
                val = float(num)
            except Exception:
                # numeric parse failed — leave as None (caller can decide how to display)
                result[k] = None
                continue
            unit = _normalize_unit(unit_raw)
            result[k] = {
                "value": val,
                "unit": unit,
                "per": "100g",
                "source": "label",
                "confidence": 0.9
            }
        else:
            result[k] = None
    return result

# --- FastAPI endpoint ---
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    tmp = tempfile.mkdtemp()
    safe_name = force_utf8_filename(file.filename)
    path_in = os.path.join(tmp, safe_name)
    with open(path_in, "wb") as f:
        f.write(await file.read())

    path_ocr = os.path.join(tmp, "ocr_" + safe_name)
    pdf_used, ocr_note = run_ocr_if_needed(path_in, path_ocr)
    text, tables, notes = extract_text_and_tables(pdf_used)
    allergens = extract_allergens(text)
    nutrition = extract_nutrition(text)

    fixed_text, fix_note = fix_text_encoding(text)
    return {
        "filename": safe_name,
        "allergens": allergens,
        "nutrition": nutrition,
        "raw_text_extract": fixed_text[:4000],
        "notes": [ocr_note, fix_note, *notes, f"tables_found:{len(tables)}"]
    }

if __name__ == "__main__":
    print("Run: uvicorn app:app --reload --port 8000")