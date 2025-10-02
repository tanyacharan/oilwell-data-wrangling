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
    #images = convert_from_path(pdf_path)
    images = convert_from_path(pdf_path, first_page=1, last_page=1)
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img)

    # Regex examples (tune these based on actual docs)
    api = re.search(r"API\s*#?:?\s*(\d+)", text)
    name = re.search(r"Well\s*Name[:\s]+([A-Za-z0-9\s\-]+)", text)
    lat = re.search(r"Lat(?:itude)?[:\s]+([\d\.\-]+)", text)
    lon = re.search(r"Lon(?:gitude)?[:\s]+([\d\.\-]+)", text)
    addr = re.search(r"Address[:\s]+(.+)", text)

    return {
        "api_number": api.group(1) if api else None,
        "well_name": name.group(1).strip() if name else None,
        "latitude": float(lat.group(1)) if lat else None,
        "longitude": float(lon.group(1)) if lon else None,
        "address": addr.group(1).strip() if addr else None,
        "raw_text": text
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
test_file = "W11745.pdf"   # change if you want a different file
path = os.path.join(PDF_FOLDER, test_file)
print(f"Processing {test_file}...")
data = parse_pdf(path)

print("Extraction complete!")
# Show first 500 characters of raw OCR text for debugging
print("\n--- OCR Preview (first 500 chars) ---")
print(data["raw_text"][:500])
print("\n--- End Preview ---")
# Save full OCR text for inspection
with open("W11745_ocr.txt", "w", encoding="utf-8") as f:
    f.write(data["raw_text"])
print("Full OCR text saved to W11745_ocr.txt")