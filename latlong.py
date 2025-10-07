import mysql.connector
import re
import time
from google import genai
from google.genai import types
from mysql.connector import Error

# ------------------------
# DB connection
# ------------------------
try:
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="20020209",
        database="dsci560"
    )
    cursor = db.cursor(dictionary=True, buffered=True) 
    print("Connected to MySQL database.")
except Error as e:
    print(f"Error connecting to MySQL: {e}")
    exit(1)


# ------------------------
# Gemini setup
# ------------------------
API_KEY = "" 
MODEL_NAME = "gemini-2.5-flash"
MAX_RETRIES = 3 # New constant for retry attempts

try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    print(f"Error initializing Gemini client: {e}")
    exit(1)


# ------------------------
# Helper: parse lat/long from text
# ------------------------
def extract_lat_long(text):
    match = re.search(r'(-?\d+\.\d+)[, ]*\s*(-?\d+\.\d+)', text.strip())
    
    if match:
        try:
            lat_val = float(match.group(1))
            long_val = float(match.group(2))
            
            if -90 <= lat_val <= 90 and -180 <= long_val <= 180:
                if lat_val > 0 and long_val > 50 and long_val <= 180: 
                    long_val = -long_val
                
                return lat_val, long_val
                
        except ValueError:
            return None, None
            
    return None, None


# ------------------------
# Get wells needing geocoding
# ------------------------
cursor.execute("""
    SELECT api_number, well_name, address, closest_city
    FROM wells_cleaned
    WHERE latitude IS NULL OR latitude = 0.0
""")
wells = cursor.fetchall()

print(f"Found {len(wells)} wells to geocode...")

# ------------------------
# Loop through wells
# ------------------------
for well in wells:
    well_name = well.get('well_name', 'N/A')
    api_number = well['api_number']
    address = well.get('address')
    city = well.get('closest_city')
    
    # ------------------
    # Compose prompt
    # ------------------
    if address and address.strip().upper() not in ['N/A', 'NOT PROVIDED', 'SEE ATTACHED']:
        prompt_text = f"Provide the latitude and longitude in decimal degrees for this address: {address}. Give only the numbers, separated by a comma (Latitude, Longitude)."
    elif city and city.strip().upper() not in ['N/A', 'NOT PROVIDED']:
        prompt_text = f"Provide the approximate latitude and longitude in decimal degrees for the city: {city}. Give only the numbers, separated by a comma (Latitude, Longitude)."
    else:
        prompt_text = f"Provide an approximate latitude and longitude in decimal degrees for the oil well named '{well_name}' in the United States. Give only the numbers, separated by a comma (Latitude, Longitude)."

    
    # ------------------
    # Retry Logic (NEW)
    # ------------------
    success = False
    for attempt in range(MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[prompt_text],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=100
                )
            )
            
            # Check for a valid response object and text
            if response is None or response.text is None:
                 # Raise a temporary error to trigger the retry loop
                raise ValueError(f"Attempt {attempt + 1}: Empty or None response object returned.")
            
            text = response.text.strip()
            
            if not text:
                raise ValueError(f"Attempt {attempt + 1}: Empty response text after stripping.")

            # If we reached here, the API call succeeded and returned content
            success = True
            break
            
        except Exception as e:
            # If it's the last attempt, log the final error
            if attempt == MAX_RETRIES - 1:
                print(f"Error geocoding {well_name} (API {api_number}): {e}")
                continue # Skip to the next well
            
            # For non-final attempts, wait longer and try again (exponential backoff)
            wait_time = 2 ** attempt
            print(f"API failed for {well_name}. Retrying in {wait_time} seconds (Attempt {attempt + 1})...")
            time.sleep(wait_time)

    # If the API call failed after all retries, continue to the next well
    if not success:
        continue

    # ------------------
    # Coordinate Processing
    # ------------------
    lat, long = extract_lat_long(text)
    
    if lat is None or long is None:
        print(f"Could not parse coordinates for {well_name} (API {api_number}). Raw response: {text[:50]}...")
        continue

    # ------------------
    # Update DB
    # ------------------
    try:
        update_query = "UPDATE wells_cleaned SET latitude=%s, longitude=%s WHERE api_number=%s"
        cursor.execute(update_query, (lat, long, api_number))
        db.commit()
        print(f"Updated {well_name} (API {api_number}): {lat}, {long}")

        # Small pause even on success to keep rate low
        time.sleep(0.5) 
        
    except Exception as e:
        print(f"MySQL Update Error for {well_name} (API {api_number}): {e}")
        db.rollback()


cursor.close()
db.close()
print("Geocoding complete!")
