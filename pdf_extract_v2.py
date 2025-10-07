import os
import re
import pytesseract
import mysql.connector
import fitz
from pdf2image import convert_from_path
from PIL import Image
import io

# --- CONFIG ---
PDF_FOLDER = r"C:\Users\tanya\DSCI560_Lab6"
USE_SQLITE = False  # set True if you prefer SQLite for testing

# Tesseract path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

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

# Create wells table
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

# Create stimulation_data table
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

# --- HELPER: Convert Township/Range to Lat/Lon ---
def township_range_to_latlon(tr_str):
    """
    Convert simple Township/Range strings like "153N 101W" to approximate lat/lon.
    This is a rough estimate assuming "N" = latitude, "S" = negative lat,
    "E" = longitude, "W" = negative lon. Returns (lat, lon).
    """
    lat, lon = 0, 0
    if tr_str:
        lat_match = re.search(r"(\d+)([NS])", tr_str)
        lon_match = re.search(r"(\d+)\s*([EW])", tr_str)
        if lat_match:
            val, dir = int(lat_match.group(1)), lat_match.group(2)
            lat = val if dir == "N" else -val
        if lon_match:
            val, dir = int(lon_match.group(1)), lon_match.group(2)
            lon = val if dir == "E" else -val
    return lat, lon

# --- PARSER FUNCTION (FULL, INTACT) ---
def parse_pdf(pdf_path):
    import os
    import re
    import pytesseract
    from PIL import Image
    import fitz

    print(f"Processing {pdf_path}...")

    # --- OCR Step ---
    doc = fitz.open(pdf_path)
    ocr_text = []

    for page_num in range(len(doc)):
        pix = doc[page_num].get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img = img.convert("L")
        img = img.point(lambda x: 0 if x < 140 else 255)
        text = pytesseract.image_to_string(img, config='--psm 6')
        ocr_text.append(text)

    full_text = "\n".join(ocr_text)
    lines = [l.strip() for l in full_text.splitlines() if l.strip()]

    # --- Detect form type ---
    form_type = "Unknown"
    upper_text = full_text.upper()
    if "FORM 8" in upper_text or "AUTHORIZATION TO PURCHASE AND TRANSPORT OIL" in upper_text:
        form_type = "Form 8"
    elif "FORM 19" in upper_text:
        form_type = "Form 19"
    elif "FORM 4" in upper_text or "SUNDRY NOTICES AND REPORTS ON WELLS" in upper_text:
        form_type = "Form 4"

    # --- Initialize variables ---
    api, well_name, township_range, operator, address = None, None, None, None, None
    stimulation_data = []

    # --- Form 19 extraction ---
    if form_type == "Form 19":
        api_match = re.search(r"UIC No[^\d\w]*([A-Za-z0-9]{5,15})", full_text, re.IGNORECASE)
        well_match = re.search(r"Well Name\s*[:\-]?\s*\|?([^\|]+)", full_text, re.IGNORECASE)
        operator_match = re.search(r"Operator\s*[:\-]?\s*([^\n|]+?)(?:Telephone|$)", full_text, re.IGNORECASE)
        address_match = re.search(r"Address\s*[:\-]?\s*\[?([^\n|]+?)(?:City|$)", full_text, re.IGNORECASE)
        township_match = re.search(r"Field\s*[:\-]?\s*([^\n|]+)", full_text, re.IGNORECASE)

        api = api_match.group(1).strip() if api_match else "N/A"
        well_name = well_match.group(1).strip() if well_match else "N/A"
        operator = operator_match.group(1).strip() if operator_match else "N/A"
        address = address_match.group(1).strip() if address_match else "N/A"
        township_range = township_match.group(1).strip() if township_match else "N/A"

        stim_matches = re.findall(
            r"chemical\s*[:\-]?\s*([A-Za-z\s]+?)\s*(?:Vol|Volume|V[o0]l)?[:\s]*([\d\.]+)?",
            full_text, re.IGNORECASE
        )
        for chem_name, vol in stim_matches:
            try:
                volume = float(vol) if vol else 0
            except:
                volume = 0
            stimulation_data.append({"type": "chemical", "chemical": chem_name.strip(), "volume": volume})

    # --- Form 4 extraction ---
    elif form_type == "Form 4":
        api_match = re.search(r"W(\d{4,10})", os.path.basename(pdf_path))
        api = api_match.group(1) if api_match else None

        skip_patterns = [
            r"600 EAST BOULEVARD", r"BISMARCK", r"SFN", r"INDUSTRIAL COMMISSION",
            r"PLEASE READ INSTRUCTIONS", r"SUBMIT THE ORIGINAL",
            r"C1", r"CO", r"NOTICE", r"REPORT", r"EXEMPTION",
            r"NOVEMBER|DECEMBER|JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER",
            r"\(1", r"for a"
        ]
        content_lines = [l for l in lines if not any(re.search(p, l, re.IGNORECASE) for p in skip_patterns)]

        for line in content_lines:
            if re.search(r"[A-Za-z]", line) and re.search(r"\d", line):
                if re.search(r"\d{1,4}-\d{1,4}[A-Z]?", line):
                    well_name = line.strip(" :")
                    break
        if not well_name:
            for line in content_lines:
                if re.search(r"[A-Za-z]", line) and re.search(r"\d", line):
                    well_name = line.strip(" :")
                    break

        m = re.search(r"(\d{2,3}[NS])\s*[| ]+\s*(\d{2,3}\s*[EW])", full_text)
        if m:
            township_range = f"{m.group(1)} {m.group(2)}".replace("|", "").strip()

        for line in content_lines:
            if re.search(r"(Operator|Oasis|Mercuria|Chesapeake|Continental|LLC|Inc\.)", line, re.IGNORECASE):
                operator = re.split(r"\s+\d{1,3}\b|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec", line.strip())[0].strip(", ")
                break

        for line in content_lines:
            if re.match(r"\d{3,5}\s+\w+", line):
                address = line.strip()
                break

    # --- Form 8 extraction ---
    elif form_type == "Form 8":
        api_match = re.search(r"Well File No\.?.*?(\d{4,10})", full_text, re.IGNORECASE | re.DOTALL)
        api = api_match.group(1) if api_match else None

        for i, line in enumerate(lines):
            if re.search(r"Well Name and Number|Qtr-Qtr|Section", line, re.IGNORECASE):
                if i + 1 < len(lines):
                    well_line = lines[i + 1].strip()
                    m = re.search(r"(\d{2,3}[NS]).*?(\d{2,3}\s*[EW])", well_line)
                    if m:
                        township_range = f"{m.group(1)} {m.group(2)}".replace("|","").strip()
                        well_name = re.sub(r"(\d{2,3}[NS].*?\d{2,3}\s*[EW].*)", "", well_line).strip(" []{}|)")
                    else:
                        well_name = well_line
                break

        operator_candidates = []
        for line in lines:
            if re.search(r"(Operator|LLC|Inc\.|Company|Corporation|Energy|Petroleum)", line, re.IGNORECASE):
                if re.search(r"Operator Telephone Number", line, re.IGNORECASE):
                    continue
                operator_candidates.append(line.strip())

        if operator_candidates:
            operator = operator_candidates[0]
            operator = re.split(r"\s+\d{1,4}\b|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec", operator)[0].strip(", ")

        for line in lines:
            if re.match(r"\d{1,5}\s+\w+", line):
                address = line.strip()
                break

    else:
        print("Unknown form type, using generic extraction.")

    # --- Convert Township/Range to lat/lon ---
    latitude, longitude = township_range_to_latlon(township_range)

    # --- Package results ---
    data = {
        "api_number": api,
        "well_name": well_name,
        "township_range": township_range,
        "operator": operator,
        "latitude": latitude,
        "longitude": longitude,
        "address": address,
        "form_type": form_type,
        "stimulation_data": stimulation_data,
        "raw_text": full_text
    }

    # --- Print results ---
    print("\n--- Extraction complete ---")
    for k, v in data.items():
        if k != "raw_text":
            print(f"{k}: {v}")

    print("\n--- OCR Preview (first 500 chars) ---")
    print(full_text[:500])
    print("\n--- End Preview ---")

    # --- Save full OCR for reference ---
    txt_path = os.path.splitext(pdf_path)[0] + "_ocr.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(full_text)
    print(f"Full OCR text saved to {os.path.basename(txt_path)}")

    return data


# --- MAIN LOOP: ONLY RUN REMAINING FILES ---
# Manually specify the last 3 PDFs
remaining_files = ["W90244.pdf", "W90329.pdf", "W90330.pdf"]  # replace names if different

for idx, file in enumerate(remaining_files, start=1):
    path = os.path.join(PDF_FOLDER, file)
    print(f"\n=== Processing {file} ({idx}/{len(remaining_files)}) ===")

    try:
        data = parse_pdf(path)
    except Exception as e:
        print(f"Error processing {file}: {e}")
        continue

    if not data["api_number"]:
        print(f"Skipping {file} — API number not found.")
        continue

    # --- Insert into wells table ---
    cursor.execute("""
        INSERT INTO wells (api_number, well_name, township_range, operator, latitude, longitude, address)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            well_name = VALUES(well_name),
            township_range = VALUES(township_range),
            operator = VALUES(operator),
            latitude = VALUES(latitude),
            longitude = VALUES(longitude),
            address = VALUES(address)
    """, (
        data["api_number"],
        data["well_name"],
        data.get("township_range", "N/A"),
        data.get("operator", "N/A"),
        data.get("latitude", 0),
        data.get("longitude", 0),
        data.get("address", "N/A")
    ))

    # --- Insert stimulation data ---
    for stim in data.get("stimulation_data", []):
        cursor.execute("""
            INSERT INTO stimulation_data (api_number, chemical, volume)
            VALUES (%s, %s, %s)
        """, (data["api_number"], stim.get("chemical", "N/A"), stim.get("volume", 0)))

    conn.commit()
    print(f"Finished processing {file} ({idx}/{len(remaining_files)})")

print("\nRemaining PDFs processed successfully.")


