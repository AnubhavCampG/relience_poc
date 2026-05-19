# Reliance Sales & Inventory AI Copilot POC

An intelligent, AI-powered Copilot designed to query and explore the Reliance Product, Inventory, and Customer database in natural language, and generate draft Sales Quotes on demand.

The project features a fully local relational database environment adapted dynamically from SQL schemas, coupled with an interactive command-line assistant powered by Azure OpenAI.

---

## 🚀 Key Features

* **AI-Powered SQL Copilot**: Translates natural language queries into SQL statements, executes them against a local SQLite database, and presents clean, readable answers.
* **Dual-Mode Tool Calling**: Features standard OpenAI function calling alongside custom JSON-parsing fallbacks (tailored specifically for advanced reasoning models).
* **Dynamic Sales Quote Generator**: Automatically compiles and exports professional sales quotes to structured `.json` files.
* **DDL Schema Compiler**: Contains a custom script compiler (`tableDB.py`) that adaptively translates enterprise MS SQL / Snowflake DDL syntax to SQLite standards on-the-fly and populates the database.
* **PDF Text Extraction**: Robust PDF text extraction utility with OCR support for scanned documents and batch processing capabilities.
* **Portable & Git-Ready**: Out-of-the-box support for script-relative pathing, standard `.gitignore` rules, and template configurations for immediate team collaboration.

---

## 🛠️ Tech Stack

* **Language**: Python 3.8+
* **Database**: SQLite3
* **LLM Integration**: Azure OpenAI SDK
* **Environment Management**: Python-dotenv
* **PDF Processing**: PyPDF2, pytesseract (optional), pdf2image (optional)

---

## 📂 Repository Structure

```
├── .env.example                  # Template for configuring Azure OpenAI credentials
├── .gitignore                    # Rules for excluding cache, local DBs, and active credentials
├── README.md                     # Project documentation (this file)
├── Customer-Data.csv             # Source Customer records
├── Inventory.csv                 # Source Inventory records
├── Product.csv                   # Source Product/Item Master records
├── Table-Script.sql              # Source SQL DDL Schema Definition script
├── reliance_data.db              # Generated SQLite database (Ignored by Git)
├── tableDB.py                    # Database compiler & CSV importer script
├── chatbot.py                    # Main CLI AI Chatbot application
└── pdf_text_extractor.py         # PDF text extraction utility with OCR support
```

---

## 🗄️ Relational Database Schema

The database consists of the following primary tables, populated from their respective CSV data:

### 1. `PORTAL_CUSTOMER`
Contains detailed customer profiles and shipping configurations.
* **Key Fields**: `CUST_NO` (Primary Identifier), `CUST_NAME`, `CUST_CITY`, `CUST_STATE`, `CUST_ZIP`, `CUST_CURRENCY_CUSTOMER`

### 2. `MDM_DIM_PRODUCT_MASTER_MV`
Stores product data, item specifications, dimensions, and classifications.
* **Key Fields**: `PRODUCT_ID` (Primary Identifier), `ITEM_DESCRIPTION`, `COMMODITY`, `SHAPE`, `SIZE_DESCRIPTION`

### 3. `FCT_INVENTORY_MV`
Maintains operational stock levels, freight unit costs, and warehouse allocations.
* **Key Fields**: `INVENTORY_ID` (Primary Identifier), `PRODUCT_ID` (FK to Product), `CUST_NO` (FK to Customer), `ON_HAND_WEIGHT`, `ON_HAND_AVAILABLE_WEIGHT`, `LOCATION`

---

## ⚡ Quick Start Guide

### 1. Clone & Setup Directory
Navigate to your project root directory and make sure your environment is configured.

### 2. Configure Environment Variables
Copy `.env.example` to a new file named `.env`:
```bash
cp .env.example .env
```
Open `.env` and fill in your actual Azure OpenAI keys and endpoint details:
```env
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
DEPLOYMENT_NAME=gpt-5.2-chat
OPENAI_API_VERSION=2024-12-01-preview
```

### 3. Initialize & Populate the Database
Run the custom schema compiler. This script cleans up existing databases, creates tables according to the schema (adapting data types to SQLite compatibility), and imports all CSV records:
```bash
python tableDB.py
```
**Expected Output:**
```
--- Creating Tables ---
Success: CREATE TABLE IF NOT EXISTS MDM_DIM_PRODUCT_MASTER_MV...
Success: CREATE TABLE IF NOT EXISTS FCT_INVENTORY_MV...
Success: CREATE TABLE PORTAL_CUSTOMER...

--- Importing Data ---
Imported 1000 rows into MDM_DIM_PRODUCT_MASTER_MV
Imported 1000 rows into FCT_INVENTORY_MV
Imported 10 rows into PORTAL_CUSTOMER

--- Final Verification ---
Table MDM_DIM_PRODUCT_MASTER_MV: 1000 rows
Table FCT_INVENTORY_MV: 1000 rows
Table PORTAL_CUSTOMER: 10 rows
```

### 4. Launch the AI Chatbot Copilot
Start the interactive AI command-line interface:
```bash
python chatbot.py
```

### 💡 Example Prompt Scenarios to Try
* **Search Customers**: *"Show me the details and location of ERA INDUSTRIES LLC."*
* **Inventory Query**: *"What product categories are available in stock right now?"*
* **Product Search**: *"Find products that contain 'ALUMINUM' in their descriptions and have shapes like 'TUBE - ROUND'."*
* **Generate a Quote**: *"Create a draft sales quote for customer 100099 with product 124593, quantity 15, and price 120.50."*

---

## 📄 PDF Text Extraction Utility

### Overview
`pdf_text_extractor.py` is a robust utility for extracting text from PDF files with support for both standard PDFs and scanned documents (via OCR).

### Features
✅ **Accurate Text Extraction** - Properly extracts text from multi-page PDFs  
✅ **OCR Support** - Falls back to Tesseract OCR for image-based PDFs  
✅ **Error Handling** - Validates file paths and handles corrupted PDFs gracefully  
✅ **Batch Processing** - Extract text from multiple PDFs in one operation  
✅ **Flexible Output** - Display text in console or save to files  

### Installation

**Basic Installation** (Standard PDF text extraction):
```bash
pip install PyPDF2
```

**With OCR Support** (For scanned PDFs):
```bash
pip install PyPDF2 pytesseract pdf2image pillow
```

**Note on Tesseract**: If using OCR, ensure Tesseract is installed on your system:
- **Windows**: Download from https://github.com/UB-Mannheim/tesseract/wiki
- **macOS**: `brew install tesseract`
- **Linux**: `sudo apt-get install tesseract-ocr`

### Usage Examples

#### 1. Extract text from a single PDF to console:
```bash
python pdf_text_extractor.py document.pdf
```

#### 2. Extract and save to file:
```bash
python pdf_text_extractor.py document.pdf --output extracted.txt
```

#### 3. Use OCR for scanned PDFs:
```bash
python pdf_text_extractor.py scanned_document.pdf --ocr --output extracted.txt
```

#### 4. Batch process a directory:
```bash
python pdf_text_extractor.py ./documents --batch --output ./output
```

### Python API Usage

#### Simple Text Extraction:
```python
from pdf_text_extractor import extract_text_from_pdf

# Extract and print text
text = extract_text_from_pdf("document.pdf")
print(text)
```

#### With OCR and File Output:
```python
from pdf_text_extractor import extract_text_from_pdf

# Extract with OCR and save to file
text = extract_text_from_pdf(
    "scanned_document.pdf",
    use_ocr=True,
    output_file="extracted.txt"
)
```

#### Batch Processing:
```python
from pdf_text_extractor import batch_extract_pdfs

# Process all PDFs in a directory
results = batch_extract_pdfs(
    pdf_directory="./documents",
    output_directory="./output",
    use_ocr=False
)

# Access results
for filename, extracted_text in results.items():
    print(f"{filename}: {extracted_text[:100]}...")
```

### Command-Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `pdf_file` | - | Path to PDF file or directory |
| `--output` | `-o` | Output file to save extracted text |
| `--ocr` | - | Use OCR for scanned PDFs |
| `--batch` | `-b` | Process all PDFs in a directory |

### Error Handling

The utility includes comprehensive error handling for:
- ✅ Missing or invalid PDF files
- ✅ Corrupted PDF pages
- ✅ Missing dependencies (PyPDF2, pytesseract, etc.)
- ✅ Scanned PDFs without OCR configured

All errors are logged with detailed messages for troubleshooting.

---

## 📚 Logging

Both the AI Copilot and PDF extraction utilities use Python's standard logging module for detailed operation tracking. Logs include timestamps, severity levels, and informative messages for debugging.

---

## 🔐 Security & Privacy

* **No API Keys in Git**: Always use `.env` files; never commit credentials to the repository.
* **Local Database**: All data remains local—no automatic synchronization with external services beyond Azure OpenAI API calls.
* **PDF Processing**: No data retention; extracted text is not stored unless explicitly saved by the user.

---

## 📝 License & Collaboration

This project is designed for team collaboration with Git-friendly structure and clear documentation for onboarding new contributors.

---

## 🆘 Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'openai'"
**Solution**: Install required dependencies
```bash
pip install -r requirements.txt
```

### Issue: PDF extraction returns no text
**Solution**: Try enabling OCR for scanned PDFs
```bash
python pdf_text_extractor.py document.pdf --ocr
```

### Issue: OCR not working
**Solution**: Ensure Tesseract is installed and pytesseract is configured correctly:
```bash
# Install system package
sudo apt-get install tesseract-ocr  # Linux
brew install tesseract              # macOS

# Verify installation
tesseract --version
```

---

## 📞 Support & Feedback

For issues, feature requests, or contributions, please open an issue or submit a pull request to the repository.
