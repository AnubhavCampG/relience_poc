# Reliance Sales & Inventory AI Copilot POC

An intelligent, AI-powered Copilot that queries Reliance Product, Inventory, and Customer data in natural language and generates draft Sales Quotes on demand.

Built with **LangGraph**, **PostgreSQL**, **FastAPI**, schema-aware prompts, and a SQL validation layer.

---

## Key Features

* **LangGraph Agent**: Multi-step flow — intent routing → SQL / PDF / quote → respond
* **PostgreSQL Database**: Enterprise DDL from `data/ddl/` with CSV seed in `data/seed/`
* **Schema-Aware Prompts**: Live introspection from `information_schema`
* **SQL Validator**: SELECT-only, table allowlist via sqlglot
* **FastAPI REST API**: Chat, quotes, PDF extraction
* **PDF Text Extraction**: Integrated into agent and API
* **CLI**: `python scripts/chatbot.py`

---

## Repository Structure

```
relience_poc/
├── app/                      # Application package
│   ├── main.py               # FastAPI entry
│   ├── config.py             # Settings & paths
│   ├── agent/                # LangGraph graph & nodes
│   ├── api/                  # REST routes & schemas
│   ├── db/                   # SQLAlchemy engine & seed
│   ├── schema/               # DB schema introspection
│   ├── sql/                  # Validator & executor
│   ├── prompts/              # LLM prompt templates
│   ├── services/             # LLM, quotes, PDF
│   └── utils/                # PDF extraction core
├── data/
│   ├── ddl/                  # Table-Script.sql
│   └── seed/                 # Product, Inventory, Customer CSVs
├── scripts/
│   ├── init_db.py            # PostgreSQL bootstrap
│   ├── chatbot.py            # Interactive CLI
│   └── extract_pdf.py        # Standalone PDF CLI
├── legacy/                   # Deprecated SQLite loader
├── runtime/                  # Generated files (gitignored)
│   ├── quotes/
│   └── uploads/
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Start PostgreSQL

```bash
docker compose up -d
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` with Azure OpenAI credentials and `DATABASE_URL`.

### 4. Initialize database

```bash
python scripts/init_db.py
```

### 5. Run API server

```bash
uvicorn app.main:app --reload
```

Docs: http://localhost:8000/docs

### 6. Or use CLI

```bash
python scripts/chatbot.py
```

---

## API Examples

### Health

```bash
curl http://localhost:8000/health
```

### Chat

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Show customers in Texas\"}"
```

### Chat with PDF upload

```bash
curl -X POST http://localhost:8000/api/v1/chat/upload \
  -F "message=Summarize this document" \
  -F "file=@document.pdf"
```

### Extract PDF

```bash
curl -X POST http://localhost:8000/api/v1/pdf/extract \
  -F "file=@document.pdf" -F "summarize=true"
```

### Create quote

```bash
curl -X POST http://localhost:8000/api/v1/quotes \
  -H "Content-Type: application/json" \
  -d "{\"customer_no\": \"100099\", \"items\": [{\"product_id\": \"124593\", \"quantity\": 15, \"price\": 120.50}]}"
```

---

## Agent Flow

```
route_intent → sql_writer → validate_sql → execute_sql → respond
route_intent → quote_builder → respond
route_intent → pdf_extractor → respond
```

---

## CLI Tips

```text
pdf:runtime/uploads/myfile.pdf Summarize key points
pdf:scan.pdf --ocr Extract text from scanned document
```

Standalone PDF extraction:

```bash
python scripts/extract_pdf.py document.pdf --output out.txt
python scripts/extract_pdf.py ./pdfs --batch --output ./out
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| DB connection failed | `docker compose up -d`, check `DATABASE_URL` |
| Missing modules | `pip install -r requirements.txt` |
| Empty schema on `/ready` | Run `python scripts/init_db.py` |
| PDF OCR fails | Install Tesseract + `pip install pytesseract pdf2image pillow` |

---

## License & Collaboration

Git-friendly layout with `.env.example` and Docker Compose for onboarding.
