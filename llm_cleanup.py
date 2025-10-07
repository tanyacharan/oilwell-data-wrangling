import os
import json
import mysql.connector
from google import genai
from google.genai import types
from mysql.connector import Error

# --- CONFIG ---
PDF_FOLDER = r"C:\Users\tanya\DSCI560_Lab6"
API_KEY = "AIzaSyC04Om2NPvtFTbAUaM2v1KWTxgYWn7wWQU"
MODEL_NAME = "gemini-2.5-flash"
MAX_PROMPT_CHARS = 1500

# --- MySQL setup ---
try:
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="20020209",
        database="dsci560"
    )
    cursor = conn.cursor()
    print("Connected to MySQL database.")
except Error as e:
    print(f"Error connecting to MySQL: {e}")
    exit(1)

# --- Gemini setup ---
try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    exit(1)

# --- JSON schema for extraction ---
json_schema = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "api_number": types.Schema(type=types.Type.STRING),
        "well_name": types.Schema(type=types.Type.STRING),
        "township_range": types.Schema(type=types.Type.STRING),
        "operator": types.Schema(type=types.Type.STRING),
        "address": types.Schema(type=types.Type.STRING),
        "stimulation_data": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "chemical": types.Schema(type=types.Type.STRING),
                    "volume": types.Schema(type=types.Type.NUMBER),
                },
                required=["chemical", "volume"],
            ),
        ),
    },
    required=["api_number", "well_name", "township_range", "operator", "address", "stimulation_data"]
)

# --- Field max lengths for MySQL ---
MAX_LENGTHS = {
    "api_number": 20,
    "well_name": 65535,
    "township_range": 500,
    "operator": 255,
    "address": 65535
}

def truncate_field(field_name, value):
    if value is None:
        return None
    max_len = MAX_LENGTHS.get(field_name)
    if max_len is not None and isinstance(value, str):
        return value[:max_len]
    return value

# --- Step 1: Collect OCR files ---
ocr_files = [f for f in os.listdir(PDF_FOLDER) if f.endswith("_ocr.txt")]
print(f"Found {len(ocr_files)} OCR files.")

# --- Step 2: Process each OCR ---
for ocr_file in ocr_files:
    api_number = ocr_file.replace("W", "").replace("_ocr.txt", "")
    ocr_path = os.path.join(PDF_FOLDER, ocr_file)

    try:
        with open(ocr_path, "r", encoding="utf-8") as f:
            ocr_text = f.read()
    except Exception as e:
        print(f"Failed to read {ocr_file}: {e}")
        continue

    if not ocr_text.strip():
        print(f"OCR file {ocr_file} is empty. Skipping.")
        continue

    # --- Enhanced prompt to help missing fields ---
    prompt_text = f"""
From the following OCR text, extract structured well data in JSON.
Required fields: api_number, well_name, township_range, operator, address, stimulation_data (list of dicts).
- api_number must equal {api_number}.
- Ensure township_range is concise but complete; truncate long strings if necessary.
- Clean operator field (remove 'Operator:' prefix if present).
- Exclude regulator addresses like '600 EAST BOULEVARD'.
- Stimulation data must have valid chemicals and numeric volumes only.
OCR:
{ocr_text[:MAX_PROMPT_CHARS]}
"""

    # --- Step 3: Generate JSON via model ---
    try:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=json_schema,
            temperature=0,
        )
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt_text],
            config=config
        )

        text_out = response.text.strip()
        if not text_out:
            raise ValueError("Empty response from model")

        data = json.loads(text_out)

    except ValueError as e:
        print(f"LLM failed for API {api_number}: {e}")
        continue
    except json.JSONDecodeError:
        print(f"Invalid JSON returned for API {api_number}. Skipping. Output: {text_out[:100]}")
        continue
    except Exception as e:
        print(f"Unexpected error for API {api_number}: {e}")
        continue

    # --- Step 4: Sanity checks ---
    if "Operator:" in data.get("operator", ""):
        data["operator"] = data["operator"].replace("Operator:", "").strip()
    if data.get("address", "").startswith("600 EAST BOULEVARD"):
        data["address"] = "N/A"

    stim_clean = []
    for stim in data.get("stimulation_data", []):
        chem = stim.get("chemical", "").strip()
        try:
            volume = float(stim.get("volume", 0))
        except (TypeError, ValueError):
            volume = 0
        if len(chem) <= 2 or volume == 0:
            continue
        stim["volume"] = volume
        stim_clean.append(stim)
    data["stimulation_data"] = stim_clean

    # --- Step 5: Insert/update into MySQL safely ---
    try:
        required_fields = ["well_name", "township_range", "operator", "address"]
        if not all(data.get(field) for field in required_fields):
            print(f"Missing essential data for API {api_number}. Skipping.")
            continue

        safe_data = {k: truncate_field(k, v) for k, v in data.items()}

        # Use ON DUPLICATE KEY UPDATE to handle existing rows
        cursor.execute("""
            INSERT INTO wells_cleaned 
            (api_number, well_name, township_range, operator, address, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                well_name = VALUES(well_name),
                township_range = VALUES(township_range),
                operator = VALUES(operator),
                address = VALUES(address),
                latitude = VALUES(latitude),
                longitude = VALUES(longitude)
        """, (
            api_number,
            safe_data.get("well_name", "N/A"),
            safe_data.get("township_range", "N/A"),
            safe_data.get("operator", "N/A"),
            safe_data.get("address", "N/A"),
            safe_data.get("latitude", 0.0),
            safe_data.get("longitude", 0.0)
        ))

        for stim in data.get("stimulation_data", []):
            cursor.execute("""
                INSERT INTO stimulation_data_cleaned (api_number, chemical, volume)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    chemical = VALUES(chemical),
                    volume = VALUES(volume)
            """, (
                api_number,
                stim.get("chemical", "N/A"),
                stim.get("volume", 0.0)
            ))

        conn.commit()
        print(f"Inserted/updated cleaned data for API {api_number}.")
    except Error as e:
        print(f"MySQL insert failed for API {api_number}: {e}")
        conn.rollback()
        continue

print("All OCRs processed and cleaned into wells_cleaned.")
cursor.close()
conn.close()
