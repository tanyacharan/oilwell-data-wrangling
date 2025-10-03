import os
import re
import pytesseract
import mysql.connector
from pdf2image import convert_from_path
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# --- CONFIG ---
PDF_FOLDER = r"C:\Users\tanya\DSCI560_Lab6"
USE_SQLITE = False  # set True if you prefer SQLite for testing

# --- DATABASE SETUP ---
if USE_SQLITE:
    import sqlite3
    conn = sqlite3.connect("wells.db")
else:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",       # change if needed
        password="20020209",  # change if needed
        database="dsci560"
    )

cursor = conn.cursor()

# Create tables if they don’t exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS wells (
    api_number VARCHAR(20) PRIMARY KEY,
    well_name VARCHAR(255),
    township_range VARCHAR(50),
    operator VARCHAR(255),
    latitude FLOAT,
    longitude FLOAT,
    address TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS stimulation_data (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    api_number VARCHAR(20),
    chemical VARCHAR(255),
    volume FLOAT,
    FOREIGN KEY (api_number) REFERENCES wells(api_number)
)
""" if not USE_SQLITE else """
CREATE TABLE IF NOT EXISTS stimulation_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_number TEXT,
    chemical TEXT,
    volume REAL
)
""")

# --- PDF PARSING FUNCTION ---
def parse_pdf(pdf_path):
    filename = os.path.basename(pdf_path)
    # --- OCR step ---
    images = convert_from_path(pdf_path, first_page=1, last_page=1)
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img)

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    api, well_name, township_range, operator, address = None, None, None, None, None

    # --- Detect form type ---
    form_type = "Unknown"
    if "FORM 4" in text.upper() or "SUNDRY NOTICES AND REPORTS ON WELLS" in text.upper():
        form_type = "Form 4"
    elif "FORM 8" in text.upper() or "AUTHORIZATION TO PURCHASE AND TRANSPORT OIL" in text.upper():
        form_type = "Form 8"

    # --- Form 8 extraction ---
    if form_type == "Form 8":
        # API
        api_match = re.search(r"Well\s*File\s*No\.?.*?(\d{4,10})", text, re.IGNORECASE | re.DOTALL)
        if api_match:
            api = api_match.group(1)

        # Well Name
        for i, line in enumerate(lines):
            if "Well Name and Number" in line:
                if i + 1 < len(lines):
                    well_line = lines[i+1]
                    well_name = re.sub(r"SWSW.*", "", well_line).strip()
                break

        # Township/Range
        m = re.search(r"(\d{2,3}N)\s*[| ]+\s*(\d{2,3}\s*W)", text)
        if m:
            township_range = f"{m.group(1)} {m.group(2)}".replace("|","").strip()

        # Operator
        for i, line in enumerate(lines):
            if "Name of First Purchaser" in line:
                if i + 1 < len(lines):
                    candidate = lines[i+1].strip()
                    operator = re.split(
                        r"\s+\d{1,3}\b|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec",
                        candidate
                    )[0].strip(", ")
                break

        # Address
        for i, line in enumerate(lines):
            if "Address" in line and "City" in line:
                if i + 1 < len(lines):
                    address = lines[i+1].strip()
                break
            if re.match(r"\d{3,5}\s+\w+", line):
                address = line.strip()
                break

    # --- Form 4 extraction ---
    elif form_type == "Form 4":
        # API fallback: from filename
        api_match = re.search(r"W(\d{4,10})", filename)
        if api_match:
            api = api_match.group(1)
        else:
            possible_ids = re.findall(r"\b\d{5}\b", text)
            if possible_ids:
                print("API not found, but detected 5-digit numbers:", possible_ids)

        # Skip headers/procedural lines
        skip_patterns = [
            r"600 EAST BOULEVARD", r"BISMARCK", r"SFN", r"INDUSTRIAL COMMISSION",
            r"PLEASE READ INSTRUCTIONS", r"SUBMIT THE ORIGINAL",
            r"C1", r"CO", r"NOTICE", r"REPORT", r"EXEMPTION",
            r"NOVEMBER|DECEMBER|JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER",
            r"\(1", r"for a"
        ]
        content_lines = [l for l in lines if not any(re.search(p, l, re.IGNORECASE) for p in skip_patterns)]

        # Step 1: Well name = line with letters + numbers + dash pattern (typical well name)
        for line in content_lines:
            if re.search(r"[A-Za-z]", line) and re.search(r"\d", line):
                if re.search(r"\d{1,4}-\d{1,4}[A-Z]?", line):
                    well_name = line.strip(" :")
                    break

        # Step 2: fallback - first line with letters + numbers, few symbols
        if not well_name:
            for line in content_lines:
                if re.search(r"[A-Za-z]", line) and re.search(r"\d", line):
                    if len(re.findall(r"[^\w\s\-&,\.]", line)) < 5:
                        well_name = line.strip(" :")
                        break

        # Step 3: fallback - first line after "Report of Work Done" passing filters
        if not well_name:
            for i, line in enumerate(lines):
                if "Report of Work Done" in line:
                    if i + 1 < len(lines):
                        candidate = lines[i+1].strip(" :")
                        if re.search(r"[A-Za-z]", candidate) and re.search(r"\d", candidate):
                            well_name = candidate
                    break

        # Township/Range: optional
        m = re.search(r"(\d{2,3}[NS])\s*[| ]+\s*(\d{2,3}\s*[EW])", text)
        if m:
            township_range = f"{m.group(1)} {m.group(2)}".replace("|","").strip()

        # Operator: known company keywords
        for line in content_lines:
            if re.search(r"(Operator|Oasis|Mercuria|Chesapeake|Continental|LLC|Inc\.)", line, re.IGNORECASE):
                operator = line.strip()
                operator = re.split(r"\s+\d{1,3}\b|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec", operator)[0].strip(", ")
                break

        # Address: lines starting with a number
        for line in content_lines:
            if re.match(r"\d{3,5}\s+\w+", line):
                address = line.strip()
                break

    else:
        print("Unknown form type, using generic extraction.")

    return {
        "api_number": api,
        "well_name": well_name,
        "township_range": township_range,
        "operator": operator,
        "address": address,
        "raw_text": text,
        "form_type": form_type
    }









# --- MAIN LOOP ---
# for file in os.listdir(PDF_FOLDER):
#     if file.endswith(".pdf"):
#         path = os.path.join(PDF_FOLDER, file)
#         print(f"Processing {file}...")
#         data = parse_pdf(path)

#         if not data["api_number"]:
#             print(f"Could not find API number in {file}")
#             continue

#         # Insert into wells table
#         cursor.execute("""
#             INSERT IGNORE INTO wells (api_number, well_name, latitude, longitude, address)
#             VALUES (%s, %s, %s, %s, %s)
#         """, (data["api_number"], data["well_name"], data["latitude"], data["longitude"], data["address"]))

#         # Example: look for stimulation data (very rough regex, refine later)
#         stim_matches = re.findall(r"(Proppant|Chemical)\s*[:\-]?\s*([A-Za-z0-9]+)\s+Vol\s*[:\-]?\s*([\d\.]+)", data["raw_text"])
#         for match in stim_matches:
#             chem, vol = match[1], match[2]
#             cursor.execute("""
#                 INSERT INTO stimulation_data (api_number, chemical, volume)
#                 VALUES (%s, %s, %s)
#             """, (data["api_number"], chem, float(vol)))

#         conn.commit()
# Test only one file
test_file = "W90329.pdf"   # change if you want a different file
path = os.path.join(PDF_FOLDER, test_file)
print(f"Processing {test_file}...")
data = parse_pdf(path)
print("Extracted fields:")
print("API:", data["api_number"])
print("Well Name:", data["well_name"])
print("Township/Range:", data.get("township_range"))
print("Operator:", data["operator"])
print("Address:", data["address"])

print("Extraction complete!")
# Show first 500 characters of raw OCR text for debugging
print("\n--- OCR Preview (first 500 chars) ---")
print(data["raw_text"][:500])
print("\n--- End Preview ---")
# Save full OCR text for inspection
with open("W90329_ocr.txt", "w", encoding="utf-8") as f:
    f.write(data["raw_text"])
print("Full OCR text saved to W90329_ocr.txt")