# Healthcare Compliance Assistant

## Overview
This project is an AI-powered document validation tool designed for healthcare and life sciences organizations. It helps ensure compliance with FDA 21 CFR Part 11 and other relevant standards by analyzing SOPs and related documents for completeness, accuracy, and regulatory alignment.

## High-Level Design
- **Backend (Flask):** Handles file uploads, document parsing, sectionizing, validation, and result generation in the form of compliance score. 

- **Frontend (HTML/JS):** Provides a modern UI for uploading documents, viewing validation results

- **Validation Engine:** Uses configurable rules to check for required sections, metadata, revision history, references, and content quality.


## Installation Steps
1. **Clone the repository:**
   ```sh
   git clone <https://github.com/omwani-jade/Healthcare.git>
   cd Healthcare
   ```
2. **Install Python dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
3. **Install additional packages:**
   ```sh
   pip install fpdf requests
   ```
4. **Set up Azure OpenAI credentials (for AI remediation):**
   - Set environment variables:
     - `AZURE_OPENAI_API_KEY`
     - `AZURE_OPENAI_ENDPOINT`
     - `AZURE_OPENAI_DEPLOYMENT`
     - `AZURE_OPENAI_API_VERSION` (optional)
5. **Run the application:**
   ```sh
   python src/app.py
   ```
6. **Access the frontend:**
   - Open your browser and go to `http://localhost:8000`

## Third-Party Libraries, Tools, and Frameworks
- **Flask**: Web framework for backend API and server.
- **requests**: HTTP client for calling Azure OpenAI endpoints.
- **PyYAML**: For reading and parsing YAML config files.
- **python-docx**: For parsing DOCX documents.
- **pypdf**: For parsing PDF documents.
- **regex**: Advanced regular expression support.
- **rich**: For enhanced logging and terminal output.
- **click**: For command-line interface utilities.
- **openai**: For interacting with OpenAI and Azure OpenAI APIs.

## Tools & Services
- **Azure OpenAI**: Used for generating dynamic remediation suggestions.
- **HTML/CSS/JavaScript**: For frontend UI and interactivity.

## Folder Structure
- `src/` - Main application code
- `kb_uploads/` - Knowledge base and uploaded documents
- `config/` - Validation rules and configuration
- `requirements.txt` - Python dependencies

## Usage
- Upload your SOP or compliance document via the frontend.
- Validate the document and review findings.


## License
This project is for demonstration and internal use only. 
