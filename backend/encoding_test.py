import pdfplumber
import PyPDF2
from pdfminer.high_level import extract_text as pdfminer_extract_text
import re

pdf_path = r"C:\Users\karen\Downloads\90327_HC ZSÍROLDÓ COMBI GRILL 1L 6DB#_2.pdf"

def score(s):
    return sum(1 for c in s if ord(c) > 127)

def try_repairs(s):
    variants = {}
    variants['original'] = s
    try:
        v1 = s.encode('latin-1', errors='ignore').decode('utf-8', errors='ignore')
        variants['latin1->utf8'] = v1
    except Exception as e:
        variants['latin1->utf8'] = f"<err:{e}>"
    try:
        v2 = s.encode('utf-8', errors='ignore').decode('latin-1', errors='ignore')
        variants['utf8->latin1'] = v2
    except Exception as e:
        variants['utf8->latin1'] = f"<err:{e}>"
    return variants

print("=== PDF path ===")
print(pdf_path)
print()

# 1) pdfplumber
print("=== pdfplumber.extract_text() ===")
try:
    with pdfplumber.open(pdf_path) as pdf:
        t = pdf.pages[0].extract_text() or ""
    print("RAW repr (first 300 chars):")
    print(repr(t[:300]))
    print("score (high-ascii count):", score(t[:300]))
    for name, val in try_repairs(t[:300]).items():
        print(f"-- variant {name} repr:")
        print(repr(val))
        print("  score:", score(val))
except Exception as e:
    print("pdfplumber error:", e)

print()
# 2) PyPDF2
print("=== PyPDF2 PdfReader.extract_text() ===")
try:
    reader = PyPDF2.PdfReader(pdf_path)
    p0 = reader.pages[0]
    t2 = p0.extract_text() or ""
    print("RAW repr (first 300 chars):")
    print(repr(t2[:300]))
    print("score:", score(t2[:300]))
    for name, val in try_repairs(t2[:300]).items():
        print(f"-- variant {name} repr:")
        print(repr(val))
        print("  score:", score(val))
except Exception as e:
    print("PyPDF2 error:", e)

print()
# 3) pdfminer.six (fallback)
print("=== pdfminer.high_level.extract_text() ===")
try:
    t3 = pdfminer_extract_text(pdf_path, page_numbers=[0]) or ""
    print("RAW repr (first 300 chars):")
    print(repr(t3[:300]))
    print("score:", score(t3[:300]))
    for name, val in try_repairs(t3[:300]).items():
        print(f"-- variant {name} repr:")
        print(repr(val))
        print("  score:", score(val))
except Exception as e:
    print("pdfminer error:", e)

print()
print("=== done ===")