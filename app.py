import streamlit as st
from PIL import Image
import pytesseract
import re
import uuid
from fpdf import FPDF

# Set path to Tesseract executable
pytesseract.pytesseract.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"

st.set_page_config(page_title="Aadhaar Verifier", layout="centered")
st.title("🪪 Aadhaar Document Verifier")

uploaded_files = st.file_uploader(
    "Upload Aadhaar Card Images",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

# Extract details from image using OCR
def extract_details(image):
    import difflib

    text = pytesseract.image_to_string(image)
    words = text.split()
    clean_text = " ".join(words)

    # Aadhaar Number Detection (4-4-4 pattern)
    aadhar = None
    for i in range(len(words) - 2):
        w1, w2, w3 = words[i], words[i + 1], words[i + 2]
        if all(w.isdigit() and len(w) == 4 for w in [w1, w2, w3]):
            combined = w1 + w2 + w3
            if re.match(r'^[2-9][0-9]{11}$', combined):
                aadhar = combined
                break

    is_aadhar = aadhar is not None

    # Name Detection
    name = "Unknown"
    for i in range(len(words)):
        if words[i].lower() == "name" and i + 2 < len(words):
            if words[i + 1] == ":":
                name_parts = []
                for j in range(i + 2, min(i + 5, len(words))):
                    if words[j].isalpha():
                        name_parts.append(words[j])
                if name_parts:
                    name = " ".join(name_parts)
                    break

    # DOB Detection - handle multiple formats and OCR errors
        # DOB Detection (robust fallback)
        # DOB Detection – advanced cleanup
    dob = "Not Found"

    # Get all 10-char text blocks to search for DOB
    possible_dobs = [w for w in words if len(w) >= 8 and len(w) <= 12]

    for raw in possible_dobs:
        # Step 1: Clean OCR mistakes
        cleaned = raw.replace('O', '0').replace('o', '0')
        cleaned = cleaned.replace('I', '1').replace('l', '1')
        cleaned = re.sub(r'[^0-9]', '/', cleaned)  # replace any non-digit with /

        # Step 2: Check for proper date format
        if re.match(r'\d{2}/\d{2}/\d{4}', cleaned):
            try:
                day, month, year = map(int, cleaned.split("/"))
                if 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100:
                    dob = f"{day:02d}/{month:02d}/{year}"
                    break
            except:
                continue



    # Gender Detection - fuzzy match
    gender = "Not Found"
    gender_options = ["male", "female", "others"]
    for word in words:
        cleaned = re.sub(r'[^a-zA-Z]', '', word).lower()
        best_match = difflib.get_close_matches(cleaned, gender_options, n=1, cutoff=0.7)
        if best_match:
            gender = best_match[0].capitalize()
            break

    return is_aadhar, aadhar, name, dob, gender, text



# Save results to PDF
def save_to_pdf(results):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    for i, res in enumerate(results):
        pdf.cell(200, 10, txt=f"Document {i + 1}", ln=1)
        pdf.cell(200, 10, txt=f"Aadhaar Card: {'Yes' if res['verified'] else 'No'}", ln=1)
        pdf.cell(200, 10, txt=f"Aadhaar No: {res['aadhar']}", ln=1)
        pdf.cell(200, 10, txt=f"Name: {res['name']}", ln=1)
        pdf.cell(200, 10, txt=f"DOB: {res['dob']}", ln=1)
        pdf.cell(200, 10, txt=f"Gender: {res['gender']}", ln=1)
        pdf.ln(10)

    file_path = f"aadhaar_report_{uuid.uuid4().hex[:6]}.pdf"
    pdf.output(file_path)
    return file_path

# Main logic for each uploaded file
if uploaded_files:
    st.success(f"{len(uploaded_files)} image(s) uploaded.")
    results = []

    for file in uploaded_files:
        img = Image.open(file)
        is_aadhar, aadhar, name, dob, gender, raw = extract_details(img)

        st.image(img, caption="Uploaded Image", use_column_width=True)

        if is_aadhar:
            st.success("🟢 Aadhaar Card Verified")
        else:
            st.error("🔴 This is not a valid Aadhaar card")

        st.markdown(f"**Aadhaar Number:** {aadhar if aadhar else 'Not Detected'}")
        st.markdown(f"**Name:** {name}")
        st.markdown(f"**DOB:** {dob}")
        st.markdown(f"**Gender:** {gender}")

        results.append({
            "verified": is_aadhar,
            "aadhar": aadhar if aadhar else "Not Detected",
            "name": name,
            "dob": dob,
            "gender": gender
        })

    if st.button("📄 Generate PDF Report"):
        pdf_path = save_to_pdf(results)
        with open(pdf_path, "rb") as f:
            st.download_button("⬇️ Download Aadhaar Report", f, file_name="aadhaar_report.pdf")
