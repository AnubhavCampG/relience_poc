# Reliance Sales & Inventory AI Copilot POC

An intelligent, AI-powered Copilot designed to query and explore the Reliance Product, Inventory, and Customer database in natural language, and generate draft Sales Quotes on demand.

The project features a fully local relational database environment adapted dynamically from SQL schemas, coupled with an interactive command-line assistant powered by Azure OpenAI.

---

## 🚀 Key Features

* **AI-Powered SQL Copilot**: Translates natural language queries into SQL statements, executes them against a local SQLite database, and presents clean, readable answers.
* **Dual-Mode Tool Calling**: Features standard OpenAI function calling alongside custom JSON-parsing fallbacks (tailored specifically for advanced reasoning models).
* **Dynamic Sales Quote Generator**: Automatically compiles and exports professional sales quotes to structured `.json` files.
* **DDL Schema Compiler**: Contains a custom script compiler (`tableDB.py`) that adaptively translates enterprise MS SQL / Snowflake DDL syntax to SQLite standards on-the-fly and populates the database from raw CSVs.
* **Portable & Git-Ready**: Out-of-the-box support for script-relative pathing, standard `.gitignore` rules, and template configurations for immediate team collaboration.

---

## 🛠️ Tech Stack

* **Language**: Python 3.8+
* **Database**: SQLite3
* **LLM Integration**: Azure OpenAI SDK
* **Environment Management**: Python-dotenv

---

## 📂 Repository Structure

```
├── .env.example              # Template for configuring Azure OpenAI credentials
├── .gitignore                # Rules for excluding cache, local DBs, and active credentials
├── README.md                 # Project documentation (this file)
├── Customer-Data.csv         # Source Customer records
├── Inventory.csv             # Source Inventory records
├── Product.csv               # Source Product/Item Master records
├── Table-Script.sql          # Source SQL DDL Schema Definition script
├── reliance_data.db          # Generated SQLite database (Ignored by Git)
├── tableDB.py                # Database compiler & CSV importer script
└── chatbot.py                # Main CLI AI Chatbot application
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
