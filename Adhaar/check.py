from ultralytics import YOLO
import cv2
import numpy as np
import os
import matplotlib.pyplot as plt
import pytesseract
import re

# Set Tesseract OCR executable path
pytesseract.pytesseract.tesseract_cmd = r'C:/Program Files/Tesseract-OCR/tesseract.exe'

def extract_text_and_draw_boxes(image):
    data = pytesseract.image_to_data(image, config='--psm 4', output_type=pytesseract.Output.DICT)
    for i in range(len(data['text'])):
        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
        conf = int(data['conf'][i])
        text = data['text'][i]
        if conf > 60 and w > 5 and h > 5 and w / h > 0.2:
            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
    return image, data

def display_text_with_boxes(image, data):
    for i in range(len(data['text'])):
        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
        conf = int(data['conf'][i])
        text = data['text'][i]
        if conf > 60 and w > 5 and h > 5 and w / h > 0.2:
            cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(image, f"{text}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    plt.figure(figsize=(8, 8))
    plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    plt.title('OCR Result')
    plt.show()

def is_valid_aadhar_combo(parts):
    combined = ''.join(parts)
    return re.match(r'^[2-9]{1}[0-9]{11}$', combined)

# === MAIN SCRIPT ===

# 1. Load image
user_input_path = "aadharimage.png"  # Change this if your image has a different name
print("📷 Loading:", user_input_path)

if not os.path.exists(user_input_path):
    print("❌ File not found:", os.path.abspath(user_input_path))
    exit()

with open(user_input_path, 'rb') as f:
    file_bytes = np.asarray(bytearray(f.read()), dtype=np.uint8)
    user_input_image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

print("✅ Image loaded.")

# 2. OCR and extract text
user_input_image, text_data = extract_text_and_draw_boxes(user_input_image)

print("\n📝 OCR Text Extracted:")
print(text_data['text'])

# 3. Detect Aadhaar number using 4-digit combos
print("\n🔍 Checking Aadhaar Number Candidates:")

aadhar_number = None
name_candidate = None
text_list = text_data['text']

for i in range(len(text_list) - 2):
    p1 = text_list[i].strip()
    p2 = text_list[i+1].strip()
    p3 = text_list[i+2].strip()
    
    if all([p1.isdigit(), p2.isdigit(), p3.isdigit(), len(p1) == 4, len(p2) == 4, len(p3) == 4]):
        combined = p1 + p2 + p3
        print(f"Checking: {p1} {p2} {p3} → {combined}")
        if is_valid_aadhar_combo([p1, p2, p3]):
            aadhar_number = combined
            for j in range(i - 1, -1, -1):
                name_text = text_list[j].strip()
                if name_text and not name_text.replace(" ", "").isdigit():
                    name_candidate = name_text
                    break
            break

# 4. Output Result
if aadhar_number:
    print(f"\n✅ Aadhaar Number Detected: {aadhar_number}")
    print(f"👤 Name (Best Guess): {name_candidate if name_candidate else 'Not Found'}")
    print("🟢 Aadhaar Card Confirmed")
else:
    print("🔴 Aadhaar Number Not Found — Cannot Confirm Aadhaar Card")

# 5. Show image with OCR boxes
display_text_with_boxes(user_input_image, text_data)
