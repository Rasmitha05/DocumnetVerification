import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance , ImageChops
import re

# ---------------------------
# Aadhaar Number Validation (Verhoeff Algorithm)
# ---------------------------

verhoeff_table_d = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

verhoeff_table_p = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

def verhoeff_validate(num: str) -> bool:
    """Check Aadhaar number with Verhoeff algorithm."""
    c = 0
    for i, item in enumerate(reversed(num)):
        c = verhoeff_table_d[c][verhoeff_table_p[i % 8][int(item)]]
    return c == 0


# ---------------------------
# OCR Preprocessing
# ---------------------------
def preprocess_for_ocr(pil_img: Image.Image) -> Image.Image:
    gray = pil_img.convert("L")
    enhancer = ImageEnhance.Contrast(gray)
    gray = enhancer.enhance(2.0)
    bw = gray.point(lambda x: 0 if x < 140 else 255, '1')
    return bw


# ---------------------------
# Aadhaar Number Extraction
# ---------------------------
def extract_aadhaar_number(pil_img: Image.Image) -> str | None:
    """Extract Aadhaar number from image using multiple passes."""
    def clean_candidate(text: str) -> str | None:
        text = text.replace('O', '0').replace('o', '0')
        text = re.sub(r"[^0-9]", "", text)
        return text if len(text) == 12 else None

    candidates = []

    # Pass 1: Preprocessed image
    pre_img = preprocess_for_ocr(pil_img)
    txt = pytesseract.image_to_string(pre_img, config="--psm 6")
    matches = re.findall(r"\b\d{4}\s?\d{4}\s?\d{4}\b", txt)
    for m in matches:
        cleaned = clean_candidate(m)
        if cleaned:
            candidates.append(cleaned)

    # Pass 2: Raw image
    raw_txt = pytesseract.image_to_string(pil_img, config="--psm 6")
    matches = re.findall(r"\b\d{4}\s?\d{4}\s?\d{4}\b", raw_txt)
    for m in matches:
        cleaned = clean_candidate(m)
        if cleaned:
            candidates.append(cleaned)

    # Return the first valid candidate
    for c in candidates:
        if verhoeff_validate(c):
            return c
    return candidates[0] if candidates else None


# ---------------------------
# Error Level Analysis (ELA)
# ---------------------------
def compute_ela_score(image_path: str) -> float:
    """Perform Error Level Analysis to detect tampering."""
    original = Image.open(image_path).convert("RGB")
    resaved_path = "resaved_temp.jpg"
    original.save(resaved_path, "JPEG", quality=90)

    resaved = Image.open(resaved_path)
    diff = ImageChops.difference(original, resaved)

    extrema = diff.getextrema()
    max_diff = max([ex[1] for ex in extrema])
    if max_diff == 0:
        max_diff = 1

    scale = 255.0 / max_diff
    diff = ImageEnhance.Brightness(diff).enhance(scale)
    arr = np.array(diff)
    ela_score = np.mean(arr)
    return ela_score


# ---------------------------
# Aadhaar Assessment
# ---------------------------
def assess_aadhaar(image_path: str, extracted_num: str = None, ela_threshold: float = 30.0):
    ela_score = 0.0
    reasons = []

    try:
        ela_score = compute_ela_score(image_path)
        if ela_score > ela_threshold:
            reasons.append(f"High ELA score ({ela_score:.2f}), possible tampering.")
        else:
            reasons.append(f"ELA score ({ela_score:.2f}) is within acceptable range.")
    except Exception as e:
        reasons.append(f"ELA check failed: {e}")
        ela_score = 0.0

    # Aadhaar number validity
    if not extracted_num or not re.match(r'^[2-9][0-9]{11}$', extracted_num):
        reasons.append("Aadhaar number format missing or incorrect.")

    verdict = "real"
    if ela_score > ela_threshold:
        verdict = "fake"
    elif "incorrect" in reasons[-1].lower():
        verdict = "suspicious"

    return {
        "verdict": verdict,
        "reasons": reasons,
        "details": {
            "ela_score": ela_score,
            "threshold": ela_threshold,
            "aadhaar_number": extracted_num if extracted_num else "Not Found"
        }
    }
