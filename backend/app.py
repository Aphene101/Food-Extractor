import os
import tempfile
import subprocess
import shutil
import re
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber

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
    """If PDF has little or no text, use OCRmyPDF or pytesseract fallback."""
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(input_pdf_path)
        text = "".join(page.extract_text() or "" for page in reader.pages[:3])
        if len(text.strip()) > 50:
            shutil.copyfile(input_pdf_path, output_pdf_path)
            return output_pdf_path, "no_ocr_needed"
    except Exception:
        pass

    # If ocrmypdf exists, prefer it
    if shutil.which("ocrmypdf"):
        try:
            subprocess.run(["ocrmypdf", "--deskew", input_pdf_path, output_pdf_path],
                           check=True, capture_output=True)
            return output_pdf_path, "ocr_applied"
        except subprocess.CalledProcessError as e:
            return input_pdf_path, f"ocr_failed:{e}"
    else:
        # fallback to pytesseract
        try:
            import pytesseract
            from pdf2image import convert_from_path
            from PIL import Image
            pages = convert_from_path(input_pdf_path)
            all_text = []
            for p in pages:
                txt = pytesseract.image_to_string(p, lang="eng+hun")
                all_text.append(txt)
            txt_combined = "\n".join(all_text)
            tmp_txt = output_pdf_path + ".txt"
            with open(tmp_txt, "w", encoding="utf-8") as f:
                f.write(txt_combined)
            return tmp_txt, "ocr_pytesseract_applied"
        except Exception as e:
            return input_pdf_path, f"ocr_not_available:{e}"

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
def extract_allergens(text: str):
    result = {}
    if not text:
        for k in ALLERGEN_KEYWORDS:
            result[k] = "Unknown"
        return result
    for allergen, keywords in ALLERGEN_KEYWORDS.items():
        found = any(re.search(r"\b" + re.escape(k) + r"\b", text, re.IGNORECASE) for k in keywords)
        result[allergen] = "Present" if found else "Absent"
    return result

NUTRITION_REGEX = {
    "Energy": r"(?:energy|energia)[^\d]{0,8}([\d.,]+)\s*(k?cal|kj)?",
    "Fat": r"(?:fat|zs[ií]r)[^\d]{0,8}([\d.,]+)\s*(g|mg)?",
    "Carbohydrate": r"(?:carbohydrate|sz[eé]nhidr[aá]t)[^\d]{0,8}([\d.,]+)\s*(g|mg)?",
    "Sugar": r"(?:sugar|cukor)[^\d]{0,8}([\d.,]+)\s*(g|mg)?",
    "Protein": r"(?:protein|feh[eé]rje)[^\d]{0,8}([\d.,]+)\s*(g|mg)?",
    "Sodium": r"(?:sodium|n[aá]trium|salt|s[oó])[^\d]{0,8}([\d.,]+)\s*(g|mg)?"
}

def extract_nutrition(text):
    result = {}
    for k, pattern in NUTRITION_REGEX.items():
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            num = m.group(1).replace(",", ".")
            try:
                val = float(num)
                unit = m.group(2) or "unknown"
                result[k] = {"value": val, "unit": unit, "per": "100g"}
            except:
                result[k] = None
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