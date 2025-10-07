# Oil Well Data Wrangling Project

A comprehensive data extraction and analysis system for oil well documents, featuring OCR processing, AI-powered data cleanup, and interactive web visualization.

## Project Overview

This project processes oil well PDF documents (Forms 4, 8, and 19) to extract key information including:
- API numbers
- Well names and locations
- Operator information
- Township/Range coordinates
- Stimulation data (chemicals and volumes)
- Geographic coordinates (latitude/longitude)

## Features

- **PDF Processing**: OCR extraction from oil well forms using Tesseract
- **AI-Powered Cleanup**: Google Gemini integration for data validation and cleanup
- **Database Storage**: MySQL database with well and stimulation data tables
- **Web Interface**: Flask application with interactive map visualization
- **Search Functionality**: Real-time well search across multiple fields
- **Geographic Conversion**: Township/Range to latitude/longitude conversion

## File Structure

```
├── app.py                 # Flask web application
├── pdf_extract_v2.py      # Main PDF processing script
├── llm_cleanup.py         # AI-powered data cleanup
├── llm_finder.py          # Google Gemini model finder utility
├── latlong.py             # Geographic coordinate utilities
├── well_url.csv           # Well URL references
├── ocr_data_output/       # PDF documents and OCR text files
├── legacy/                # Legacy scripts
├── static/                # Web application assets
```

## Prerequisites

### Software Requirements
- Python 3.7+
- MySQL Server
- Tesseract OCR
- Google Gemini API access

### Hardware Requirements
- Sufficient RAM for PDF processing
- Storage space for OCR text files

## Installation

1. **Clone or download the project**
   ```bash
   git clone <repository-url>
   cd oilwell-data-wrangling-main
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Tesseract OCR**
   - Windows: Download from [GitHub Tesseract releases](https://github.com/tesseract-ocr/tesseract)
   - Update the path in `pdf_extract_v2.py` line 15

4. **Setup MySQL Database**
   ```sql
   CREATE DATABASE dsci560_lab6;
   ```

5. **Configure API Keys**
   - Add your Google Gemini API key to `llm_cleanup.py` and `llm_finder.py`

## Configuration

### Database Settings
Update database credentials in relevant files:
- `app.py` lines 8-13
- `pdf_extract_v2.py` lines 22-27
- `llm_cleanup.py` lines 16-21

### File Paths
Update file paths for your system:
- `PDF_FOLDER` in `pdf_extract_v2.py` line 11
- Tesseract path in `pdf_extract_v2.py` line 15

## Usage

### 1. Process PDF Documents
```bash
python pdf_extract_v2.py
```
- Extracts data from PDFs in the configured folder
- Generates OCR text files
- Populates MySQL database

### 2. Clean Data with AI
```bash
python llm_cleanup.py
```
- Uses Google Gemini to validate and clean extracted data
- Updates database with improved data quality

### 3. Launch Web Application
```bash
python app.py
```
- Access the web interface at `http://localhost:5000`
- View interactive map with well locations
- Search wells by name, API number, city, or operator

## API Endpoints

- `GET /` - Main map interface
- `GET /api/search?q=<query>` - Search wells (returns JSON)

## Database Schema

### Wells Table
- `api_number` (VARCHAR) - Primary key
- `well_name` (VARCHAR)
- `township_range` (VARCHAR)
- `operator` (VARCHAR)
- `latitude` (FLOAT)
- `longitude` (FLOAT)
- `address` (TEXT)

### Stimulation Data Table
- `id` (INTEGER) - Primary key
- `api_number` (VARCHAR) - Foreign key
- `chemical` (VARCHAR)
- `volume` (FLOAT)

## Supported Document Types

- **Form 4**: Sundry Notices and Reports on Wells
- **Form 8**: Authorization to Purchase and Transport Oil
- **Form 19**: Underground Injection Control permits

## Development Notes

- OCR processing includes image preprocessing for better accuracy
- Township/Range coordinates are converted to approximate lat/long
- SQL injection protection should be enhanced in production
- Error handling includes database connection management
## Future Enhancements

- Enhanced SQL injection protection
- Batch processing optimization
- Additional form type support
- Advanced geographic coordinate conversion
- Data validation improvements
- REST API expansion
- More seamless integration across devices (.env support)
