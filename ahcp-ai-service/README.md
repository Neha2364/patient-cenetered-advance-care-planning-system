# AHCP AI Service

Standalone FastAPI service extracted from the Advance Health Care Planning (`ACP.ipynb`) notebook and engineered for independent execution. The service implements:
- Complete Q1–Q20 advance care planning questionnaire workflow.
- Full English (`en`) and Kannada (`kn`) language support with question text translation and answer normalization.
- Strict Python-controlled state machine ensuring patient answers are stored accurately without hallucination.
- Dedicated "Unsure" educational flow on treatment preference questions that explains concepts without prematurely saving choices.
- In-memory FAISS inner-product vector store powered by `sentence-transformers/all-MiniLM-L6-v2` embeddings over healthcare PDFs.
- OpenRouter LLM generation for grounded educational explanations.
- API key authentication (`X-API-Key`) on all protected endpoints.
- Structured patient records and visualization-ready doctor dashboard summaries.

---

## Quick Setup (Windows PowerShell)

For step-by-step copy-paste commands, refer to [`START_HERE_WINDOWS.txt`](START_HERE_WINDOWS.txt).

```powershell
# 1. Open project root
cd "C:\Users\Poorvikapriya s\Downloads\AHCP_AI_Service_Package (1)"

# 2. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 4. Configure environment (.env is loaded automatically via python-dotenv)
Copy-Item .env.example .env

# Set your private service key and optional OpenRouter key:
$env:AHCP_AI_SERVICE_API_KEY = "your-private-secret-key"
$env:OPENROUTER_API_KEY = "your-openrouter-key"  # Optional, for live generation

# 5. Run tests
python -m pytest -v

# 6. Start service
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

---

## API Endpoints & Authentication

All endpoints except `GET /health` require the HTTP header:
`X-API-Key: <AHCP_AI_SERVICE_API_KEY>`

| Method | Endpoint | Auth Required | Description |
|---|---|---|---|
| `GET` | `/health` | No | Public health check returning service status. |
| `POST` | `/session` | Yes | Starts a new session in English (`en`) or Kannada (`kn`), returns Q1. |
| `POST` | `/chat` | Yes | Submits patient answers, progresses questionnaire, or triggers Unsure/RAG explanations. |
| `POST` | `/patient-record?session_id=...` | Yes | Returns canonical structured patient record. |
| `POST` | `/doctor-dashboard?session_id=...` | Yes | Returns structured record with summary counts and unresolved items. |

---

## Knowledge Base & RAG Architecture

The `knowledge/` directory contains 20 curated advance care planning and healthcare reference PDFs:
- **15 PDFs** contain digital text extractable via `pypdf` (e.g., MedlinePlus CPR, mechanical ventilators, organ donation, palliative care, cancer, diabetes, etc.).
- **5 PDFs** are scanned document guides without embedded text layers (e.g., Living Will guide, feeding tubes, withdrawal of life support). The ingestion pipeline logs clear notices for image-based PDFs without failing.
- On first retrieval, `app.py` chunks extractable text (800 chars, 150 overlap), computes normalized embeddings with MiniLM, and constructs a FAISS `IndexFlatIP` index in memory (240 chunks).
- No prebuilt index file is needed; indexing happens automatically on demand.

---

## Testing

The project includes an automated test suite in `tests/test_api.py`:
- Validates all 5 endpoints, status codes, and 401/404 handling.
- Tests full 20-question completion in both English and Kannada.
- Tests answer normalization (`"ಹೌದು"` → `"Yes"`, `"ಇಲ್ಲ"` → `"No"`, `"ಖಚಿತವಿಲ್ಲ"` → `"Unsure"`).
- Tests that "Unsure" provides explanations without prematurely committing decisions.
- Verifies real FAISS retrieval on local PDFs.
- All LLM generation is mocked during offline tests so zero OpenRouter credits are consumed.

Run tests:
```powershell
python -m pytest -v
```

---

## Security Best Practices

- Real API keys must never be committed to Git. `.env` is ignored via `.gitignore`.
- Keep `AHCP_AI_SERVICE_API_KEY` internal between the backend and AI service. Never expose it to frontend or browser clients.
