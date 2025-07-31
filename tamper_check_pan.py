from PIL import Image, ImageChops
import numpy as np
import os
import cv2
import math
import re

def compute_ela_score(image_path, quality=90):
    """
    Compute Error Level Analysis (ELA) score for tamper detection.
    """
    temp_ela_path = "temp_ela_pan.jpg"
    image = Image.open(image_path).convert("RGB")
    image.save(temp_ela_path, "JPEG", quality=quality)
    resaved = Image.open(temp_ela_path)
    diff = ImageChops.difference(image, resaved)

    extrema = diff.getextrema()
    max_diff = max([ex[1] for ex in extrema])
    if max_diff == 0:
        max_diff = 1

    scale = 255.0 / max_diff
    ela_image = diff.point(lambda p: p * scale)
    ela_array = np.asarray(ela_image)
    mean_ela = np.mean(ela_array)

    os.remove(temp_ela_path)
    return mean_ela, ela_image

def assess_pan(image_path):
    """
    Assess whether PAN card is tampered based on ELA analysis.
    """
    ela_score, _ = compute_ela_score(image_path)
    verdict = "real"
    reasons = []

    # Thresholds based on empirical testing
    if ela_score > 35:
        verdict = "fake"
        reasons.append("High ELA score suggests strong tampering artifacts.")
    elif ela_score > 20:
        verdict = "suspicious"
        reasons.append("Moderate ELA score suggests possible tampering.")

    return {
        "verdict": verdict,
        "reasons": reasons if reasons else ["ELA score is within acceptable limits."],
        "details": {
            "ela_score": ela_score
        }
    }
