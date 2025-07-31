from utils.matcher import similarity
from utils.timer import time_it
import os
from tamper_check import assess_aadhaar, extract_aadhaar_number
from tamper_check_pan import assess_pan
import streamlit as st
from PIL import Image
import pytesseract
import re
import uuid
from fpdf import FPDF
import difflib

# Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"

# ----------------- Page Header -----------------
st.set_page_config(page_title="Document Verifier", layout="centered")

col1, col2 = st.columns([1, 5])
with col1:
    st.image("assets/logo.png", width=80)
with col2:
    st.markdown("## 📑 Document Verification Portal")

tab1, tab2 = st.tabs(["\U0001FAAA Aadhaar Card", "\U0001F4B3 PAN Card"])

# ----------------- Aadhaar Functions -----------------

def extract_aadhaar_details(image):
    text = pytesseract.image_to_string(image)
    words = text.split()
    clean_text = " ".join(words)

    aadhar = None
    for i in range(len(words) - 2):
        w1, w2, w3 = words[i], words[i + 1], words[i + 2]
        if all(w.isdigit() and len(w) == 4 for w in [w1, w2, w3]):
            candidate = w1 + w2 + w3
            if re.match(r'^[2-9][0-9]{11}$', candidate):
                aadhar = candidate
                break
    is_aadhar = aadhar is not None

    name = "Unknown"
    for i in range(len(words)):
        if words[i].lower() == "name" and i + 2 < len(words) and words[i + 1] == ":":
            name_parts = [w for w in words[i + 2:i + 5] if w.isalpha()]
            if name_parts:
                name = " ".join(name_parts)
                break

    dob = "Not Found"
    possible_dobs = [w for w in words if len(w) >= 8 and len(w) <= 12]
    for raw in possible_dobs:
        cleaned = raw.replace('O', '0').replace('o', '0').replace('I', '1').replace('l', '1')
        cleaned = re.sub(r'[^0-9]', '/', cleaned)
        if re.match(r'\d{2}/\d{2}/\d{4}', cleaned):
            try:
                d, m, y = map(int, cleaned.split('/'))
                if 1 <= d <= 31 and 1 <= m <= 12 and 1900 <= y <= 2100:
                    dob = f"{d:02d}/{m:02d}/{y}"
                    break
            except:
                continue

    gender = "Not Found"
    for w in words:
        cleaned = re.sub(r'[^a-zA-Z]', '', w.lower())
        match = difflib.get_close_matches(cleaned, ["male", "female", "others"], n=1, cutoff=0.7)
        if match:
            gender = match[0].capitalize()
            break

    return is_aadhar, aadhar, name, dob, gender

def generate_aadhaar_pdf(data_list):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.set_title("Aadhaar Card Verification Report")

    for i, data in enumerate(data_list):
        pdf.cell(200, 10, txt=f"Document {i + 1}", ln=1)
        pdf.cell(200, 10, txt=f"Verified: {'Yes' if data['verified'] else 'No'}", ln=1)
        pdf.cell(200, 10, txt=f"Aadhaar No: {data['aadhar']}", ln=1)
        pdf.cell(200, 10, txt=f"Name: {data['name']}", ln=1)
        pdf.cell(200, 10, txt=f"DOB: {data['dob']}", ln=1)
        pdf.cell(200, 10, txt=f"Gender: {data['gender']}", ln=1)
        pdf.cell(200, 10, txt=f"Tamper Verdict: {data['tamper_verdict']} (ELA: {data['tamper_ela_score']:.2f})", ln=1)
        pdf.ln(10)

    file_path = f"aadhaar_report_{uuid.uuid4().hex[:6]}.pdf"
    pdf.output(file_path)
    return file_path

# ----------------- PAN Functions -----------------

def extract_pan_details(image):
    text = pytesseract.image_to_string(image)
    words = text.split()
    text_clean = text.replace("\n", " ")

    pan_number = "Not Found"
    for word in words:
        pan_candidate = word.upper().strip()
        if re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', pan_candidate):
            pan_number = pan_candidate
            break

    name = "Unknown"
    for i, w in enumerate(words):
        if pan_number in w:
            for j in range(i + 1, len(words)):
                if words[j].isalpha() and words[j].isupper() and len(words[j]) > 3:
                    name = words[j]
                    break
            break

    dob = "Not Found"
    match = re.search(r'\d{2}/\d{2}/\d{4}', text_clean)
    if match:
        dob = match.group()

    return pan_number, name, dob

def generate_pan_pdf(data_list):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.set_title("PAN Card Verification Report")

    for i, data in enumerate(data_list):
        pdf.cell(200, 10, txt=f"Document {i + 1}", ln=1)
        pdf.cell(200, 10, txt=f"Verified: {'Yes' if data['pan'] != 'Not Found' else 'No'}", ln=1)
        pdf.cell(200, 10, txt=f"PAN No: {data['pan']}", ln=1)
        pdf.cell(200, 10, txt=f"Name: {data['name']}", ln=1)
        pdf.cell(200, 10, txt=f"DOB: {data['dob']}", ln=1)
        pdf.cell(200, 10, txt=f"Tamper Verdict: {data['tamper_verdict']} (ELA: {data['tamper_ela_score']:.2f})", ln=1)
        pdf.ln(10)

    file_path = f"pan_report_{uuid.uuid4().hex[:6]}.pdf"
    pdf.output(file_path)
    return file_path

# ----------------- Aadhaar Tab -----------------

with tab1:
    uploaded = st.file_uploader("Upload Aadhaar Images", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    aadhaar_data = []

    if uploaded:
        for file in uploaded:
            img = Image.open(file).convert("RGB")
            temp_path = "temp_aadhaar.jpg"
            img.save(temp_path, "JPEG")

            with st.spinner("⏳ Please wait... Your Aadhaar is being processed."):
                is_aadhar, _, name, dob, gender = extract_aadhaar_details(img)
                num = extract_aadhaar_number(img)
                assess = assess_aadhaar(temp_path, extracted_num=num)
                verdict = assess["verdict"]
                ela_score = assess["details"]["ela_score"]
                reasons = assess["reasons"]

            st.image(img, caption="Uploaded Aadhaar", use_column_width=True)

            if verdict == "real":
                st.success(f"✅ Aadhaar looks REAL (ELA Score: {ela_score:.2f})")
            elif verdict == "fake":
                st.error(f"❌ Aadhaar looks FAKE / Tampered (ELA Score: {ela_score:.2f})")
            else:
                st.warning(f"⚠️ Aadhaar is SUSPICIOUS (ELA Score: {ela_score:.2f})")

            with st.expander("Why this verdict?"):
                for r in reasons:
                    st.write(f"- {r}")

            if is_aadhar:
                st.success("🟢 Aadhaar Card Verified")
            else:
                st.error("🔴 Invalid Aadhaar Card")

            st.markdown(f"**Aadhaar Number:** {num}")
            st.markdown(f"**Name:** {name}")
            st.markdown(f"**DOB:** {dob}")
            st.markdown(f"**Gender:** {gender}")
            st.markdown("---")

            aadhaar_data.append({
                "verified": is_aadhar,
                "aadhar": num,
                "name": name,
                "dob": dob,
                "gender": gender,
                "tamper_verdict": verdict,
                "tamper_ela_score": ela_score,
                "tamper_reasons": reasons
            })

        if st.button("📄 Generate Aadhaar PDF Report"):
            pdf_path = generate_aadhaar_pdf(aadhaar_data)
            with open(pdf_path, "rb") as f:
                st.download_button("⬇️ Download Aadhaar Report", f, file_name="aadhaar_report.pdf")

# ----------------- PAN Tab -----------------

with tab2:
    uploaded_pan = st.file_uploader("Upload PAN Card Images", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="pan_upload")
    pan_data = []

    if uploaded_pan:
        for file in uploaded_pan:
            img = Image.open(file).convert("RGB")
            temp_path = "temp_pan.jpg"
            img.save(temp_path, "JPEG")

            with st.spinner("⏳ Please wait... Your PAN is being processed."):
                pan, name, dob = extract_pan_details(img)
                assess = assess_pan(temp_path)
                verdict = assess["verdict"]
                ela_score = assess["details"]["ela_score"]
                reasons = assess["reasons"]

            st.image(img, caption="Uploaded PAN", use_column_width=True)

            if verdict == "real":
                st.success(f"✅ PAN looks REAL (ELA Score: {ela_score:.2f})")
            elif verdict == "fake":
                st.error(f"❌ PAN looks FAKE / Tampered (ELA Score: {ela_score:.2f})")
            else:
                st.warning(f"⚠️ PAN is SUSPICIOUS (ELA Score: {ela_score:.2f})")

            with st.expander("Why this verdict?"):
                for r in reasons:
                    st.write(f"- {r}")

            if pan != "Not Found":
                st.success("🟢 PAN Card Verified")
            else:
                st.error("🔴 Invalid PAN Card")

            st.markdown(f"**PAN Number:** {pan}")
            st.markdown(f"**Name:** {name}")
            st.markdown(f"**DOB:** {dob}")
            st.markdown("---")

            pan_data.append({
                "pan": pan,
                "name": name,
                "dob": dob,
                "tamper_verdict": verdict,
                "tamper_ela_score": ela_score,
                "tamper_reasons": reasons
            })

        if st.button("📄 Generate PAN PDF Report"):
            pdf_path = generate_pan_pdf(pan_data)
            with open(pdf_path, "rb") as f:
                st.download_button("⬇️ Download PAN Report", f, file_name="pan_report.pdf")

# ----------------- Footer -----------------

st.markdown("---")
st.markdown("*Crafted with precision and integrity by a passionate team — Document Verifier © 2025*")
