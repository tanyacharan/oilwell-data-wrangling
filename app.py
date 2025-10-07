from flask import Flask, render_template, request, jsonify # Import request and jsonify for the API
import mysql.connector

# Rename the app's title displayed in the browser tab
app = Flask(__name__, template_folder="drill_template")

# Database connection info (Same as before)
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "20020209",  # update if needed
    "database": "dsci560"
}

# Helper function to get a database connection
def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

# Function to fetch well data along with associated stimulation data (Unchanged)
def fetch_well_data():
    conn = None
    wells = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. Fetch all primary well data
        cursor.execute("""
            SELECT
                api_number, well_name, operator, latitude, longitude,
                well_type, closest_city, well_status,
                barrels_oil, mcf_gas
            FROM wells_cleaned
            WHERE latitude IS NOT NULL AND latitude != 0.0
        """)
        wells = cursor.fetchall()
        
        if wells:
            api_list = [f"'{well['api_number']}'" for well in wells]
            
            cursor.execute(f"""
                SELECT api_number, chemical, volume
                FROM stimulation_data_cleaned
                WHERE api_number IN ({','.join(api_list)})
                ORDER BY api_number, chemical;
            """)
            stim_data = cursor.fetchall()

            stim_map = {well['api_number']: [] for well in wells}
            
            for stim in stim_data:
                if stim['api_number'] in stim_map:
                    stim_str = f"{stim['chemical']} ({stim['volume']:,.0f})"
                    stim_map[stim['api_number']].append(stim_str)

            for well in wells:
                well['stimulation_data_list'] = stim_map.get(well['api_number'], ["N/A"])
                well['oil_barrels'] = well.pop('barrels_oil', 'N/A')
                well['mcf_gas'] = well.pop('mcf_gas', 'N/A')
                well['status'] = well.pop('well_status', 'N/A')


    except Exception as e:
        wells = []
        print("Database error:", e)
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
    
    return wells


# --- NEW: API ROUTE FOR SEARCH FUNCTIONALITY ---
@app.route("/api/search", methods=["GET"])
def search_wells():
    # Get the user's search query (q=...)
    query = request.args.get('q', '').strip()
    results = []

    if not query:
        return jsonify(results)

    # Use LIKE clauses to search across multiple relevant fields
    search_term = f'%{query}%'
    
    # NOTE: Using a parameterized query helps prevent SQL injection (but requires minor modification to the helper function)
    # Since the structure is simple, we'll use f-strings for quick implementation, but note security risk.
    search_query = f"""
        SELECT
            api_number, well_name, latitude, longitude, closest_city
        FROM wells_cleaned
        WHERE
            well_name LIKE '{search_term}' OR
            api_number LIKE '{search_term}' OR
            closest_city LIKE '{search_term}' OR
            operator LIKE '{search_term}'
        LIMIT 10
    """
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(search_query)
        results = cursor.fetchall()
    except Exception as e:
        print("Search API error:", e)
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            
    return jsonify(results)
# --- END NEW API ROUTE ---


@app.route("/")
def index():
    wells = fetch_well_data()
    return render_template("map.html", wells_json=wells)


if __name__ == "__main__":
    app.run(debug=True)