That's a smart final step. A professional project requires a great README.

Here is a complete, punchy README file and GitHub repository description for your SiteScout visualization project.

SiteScout: Geospatial Energy Data Visualization
Repository Description:

SiteScout: Dynamic web application for visualizing oil and gas well data. Features interactive mapping, production analysis clustering, and integrated search capabilities built with Flask and Leaflet.

SiteScout: Geospatial Energy Data Visualization
SiteScout is a full-stack Python (Flask) and JavaScript (Leaflet) web application designed to visualize oil and gas well data extracted from scanned PDF documents. It allows users to explore well locations, view production metrics, analyze stimulation data, and search specific API numbers on an interactive map.

Features
Interactive Mapping: Displays 69 geocoded wells across the US (primarily ND, TX, OK) using Leaflet.js and OpenStreetMap tiles.

Dynamic Clustering: Uses Leaflet.markercluster to group dense well markers. Cluster size is dynamically scaled based on Total Oil Production (bbls), highlighting high-value regions.

Status Indicators: Markers are colored based on well_status (Blue for Active/Producing, Gray for Inactive/SWD).

Animated Search: A modern, animated search control allows users to instantly query the MySQL database by Well Name, API Number, Operator, or Closest City, then pans the map to the result and opens the specific well popup.

Detailed Popups: Each marker displays comprehensive well data, including API number, Operator, Status, production values (Oil/Gas), and detailed Stimulation Data (chemicals and volumes extracted from OCR).

Reset View: Dedicated button to instantly return the map to the continental U.S. view.

Setup and Installation
This project requires Python 3.x and a running MySQL server.

1. Prerequisites
You must have the following installed on your Linux environment:

Python 3.x

MySQL Server (and the ability to connect via the root user and password specified in app.py).

2. Python Environment Setup
Navigate to your project directory and install the required Python libraries:

Bash

# Install Flask and the MySQL connector library
pip install Flask mysql-connector-python
3. Database Configuration and Data Loading
A. Configure Database:

Ensure your MySQL server is running and create the database and tables:

SQL

# Run this in your MySQL console
CREATE DATABASE dsci560;
USE dsci560;

# Create wells_cleaned table
CREATE TABLE wells_cleaned (
    api_number VARCHAR(20) PRIMARY KEY,
    well_name TEXT,
    operator VARCHAR(255),
    address TEXT,
    closest_city VARCHAR(100),
    well_status VARCHAR(50),
    well_type VARCHAR(50),
    barrels_oil VARCHAR(50),
    mcf_gas VARCHAR(50),
    latitude FLOAT,
    longitude FLOAT
);

# Create stimulation_data_cleaned table
CREATE TABLE stimulation_data_cleaned (
    id INT AUTO_INCREMENT PRIMARY KEY,
    api_number VARCHAR(20),
    chemical VARCHAR(255),
    volume FLOAT,
    FOREIGN KEY (api_number) REFERENCES wells_cleaned(api_number)
);
B. Load Data:

You must have previously run the SQL UPDATE and INSERT commands (generated in the preceding steps) to populate the wells_cleaned and stimulation_data_cleaned tables with the 69 wells and their data.

4. File Structure
Ensure your project directory is structured correctly for Flask:

your_project/
├── app.py
├── static/
│   └── sitescout_logo.png   <-- LOGO IMAGE
├── drill_template/
│   └── map.html
└── ... other files
5. Run the Application
Execute the Flask application from your terminal:

Bash

python app.py
The application will launch on your local network. Open your browser and navigate to:

http://127.0.0.1:5000/

GeoJSON and External Dependencies
State Boundaries: The map feature that displays state summaries on hover relies on the external file static/us_states.geojson. This file must be present in the static folder for the boundary feature to load correctly.

Map Libraries: The application uses public CDNs for Leaflet, Leaflet.markercluster, jQuery, and Font Awesome, ensuring minimal local dependencies.
