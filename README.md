# ENCODE EpiDoc - Epigraphic Database Viewer

A powerful Streamlit application designed to visualize, analyze, and search ancient Greek inscriptions encoded in TEI XML format. Transform scholarly TEI-encoded EpiDoc XML documents from the Telamon project into interactive, searchable visualizations with statistical insights.

## Overview

**ENCODE EpiDoc** is a tool for humanities scholars and researchers working with ancient epigraphy. It enables seamless conversion and visualization of complex TEI XML inscription data into an intuitive, user-friendly interface. The application provides three main workflows:

- **Data Visualization**: Display detailed information about monuments, their physical characteristics, textual content, and associated images
- **Search & Query**: Search across multiple documents by monument type, material, category, or custom keywords
- **Analytics**: Generate statistical visualizations and data summaries across inscription collections

## Features

✨ **Key Capabilities:**

- **TEI XML Parsing**: Robust parsing of TEI-encoded EpiDoc XML documents with validation and error handling
- **Leiden+ Formatting**: Displays Greek text with professional Leiden+ notation for epigraphic conventions (gaps, unclear letters, restorations, etc.)
- **Multi-language Content**: Extracts and displays English translations, apparatus notes, commentary, and bibliographic references
- **Image Management**: Upload and display facsimile images matched to inscriptions by document ID or XML references
- **Advanced Search**: Query across monument types, materials, dating, categories, or custom search terms across all document sections
- **Interactive Analytics**: Generate charts showing distributions of monument types, materials, and timelines
- **XML Export**: Download original TEI XML documents directly from the interface

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup

1. **Clone or download the repository:**
   ```bash
   git clone https://github.com/Bestroi150/encode-frontend-transformation.git
   cd encode-frontend-transformation
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Application

```bash
streamlit run streamlit_app.py
```

The application will open in your default web browser at `http://localhost:8501`

### Basic Workflow

1. **Upload TEI XML Files**: Use the file uploader to select one or more TEI-encoded XML files from the Telamon project or your own sources

2. **Upload Images (Optional)**: Add facsimile images (JPG, PNG) that correspond to your inscriptions. Images are matched to documents by filename containing the monument ID

3. **Explore Data**:
   - **Data Visualization Tab**: Browse detailed information about each monument including physical dimensions, material, provenance, and textual content
   - **Search & Query Tab**: Find inscriptions by type, material, category, or search across all text sections
   - **Analytics Tab**: View statistical distributions and interactive visualizations

### Data Sources

Download sample TEI XML files from the **[Telamon Project](https://telamon.uni-sofia.bg/)** - an online database of Greek inscriptions. For best results, download at least 5 XML files to experience the search and analytics features.

## Project Information

**Developed for:**
- **Course**: Front-End Data Processing and Visualization  
- **Date**: May 23, 2025
- **Institution**: University of Parma, Italy
- **Event**: Erasmus+ BIP Intensive ENCODE week (May 18–24, 2025)

**Author:**
Kristiyan Simeonov, Sofia University "St. Kliment Ohridski"

## Technical Details

### Dependencies

- **streamlit** (≥1.24.0): Web application framework
- **pandas** (≥2.0.3): Data manipulation and analysis
- **plotly** (5.15.0): Interactive visualizations
- **pillow** (≥9.5.0): Image processing
- **lxml** (≥4.9.3): XML parsing
- **python-dateutil** (2.8.2): Date handling

### Architecture

The application works with TEI XML documents following the EpiDoc guidelines:

- **TEI Header**: Extracts metadata (editors, dating, provenance, dimensions, materials)
- **Text Body**: Processes Greek edition text, apparatus criticus, translations, commentary, and bibliography
- **Facsimiles**: Manages image references both from XML and user uploads
- **Leiden+ Formatter**: Converts complex EpiDoc XML markup into readable scholarly notation

## File Structure

```
encode-frontend-transformation/
├── streamlit_app.py          # Main application
├── requirements.txt          # Python dependencies
├── README.md                 # This file
└── LICENSE                   # License information
```

## Features in Detail

### Greek Text Processing

The application includes a sophisticated Leiden+ formatter that handles:
- Line breaks and gaps in text
- Unclear letters and restorations
- Abbreviations and expansions
- Deletions and additions
- Corrections and regularizations
- Decorative marks and special characters

### Search Functionality

Query documents across multiple dimensions:
- **Monument Types**: Filter by inscription type (altar, stele, etc.)
- **Materials**: Search by stone or material type
- **Categories**: Find by inscription category
- **Custom Search**: Full-text search across Greek text, translations, commentary, and bibliography

### Analytics Dashboard

Visualize patterns in your inscription collection:
- Distribution of monument types (bar chart)
- Material composition (pie chart)
- Chronological timeline with filtering
- Exportable data tables

## Notes

- Only English-language content is extracted from translation, apparatus, and commentary sections
- Image filenames should contain the monument ID for automatic matching
- TEI XML files must be valid and conform to EpiDoc standards for optimal parsing
- The application gracefully handles missing or incomplete data fields

## License

This project is open source. See the LICENSE file for details.

## Support & Contributions

For issues, suggestions, or contributions, please refer to the project repository on GitHub.

---

**Ready to explore ancient inscriptions?** Start by uploading TEI XML files and images, then navigate between visualization, search, and analytics modes to discover insights in your inscription collection.
