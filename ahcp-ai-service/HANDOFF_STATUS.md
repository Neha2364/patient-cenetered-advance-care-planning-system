# AHCP AI Service — Handoff Status & Checklist

This document tracks the verified implementation status, architectural decisions, and remaining integration items for the backend team.

---

## 1. Verified Implementation Checklist

| Category | Component / Feature | Status | Notes |
|---|---|---|---|
| **Project Structure** | Root directory layout | Verified | `app.py`, `requirements.txt`, `.env.example`, `.gitignore`, `knowledge/`, and `tests/` reside at root. |
| **Dependencies** | Python 3.11–3.13 compatibility | Verified | Compatible with Python 3.11, 3.12, and 3.13. All wheels (including `faiss-cpu` and `torch`) successfully install. |
| **Configuration** | Dynamic `.env` loading | Verified | Loaded via `python-dotenv`. Re-checks `.env` on runtime if variables were absent at boot. |
| **Authentication** | `X-API-Key` protection | Verified | Enforced on `/session`, `/chat`, `/patient-record`, and `/doctor-dashboard`. Correctly returns `401 Unauthorized` for missing or invalid keys. |
| **Endpoint 1** | `GET /health` | Verified | Public route returning `200 OK` with service name and version `1.0.0`. |
| **Endpoint 2** | `POST /session` | Verified | Supports English (`en`) and Kannada (`kn`), returns session ID, starts at Q1 with localized question text. |
| **Endpoint 3** | `POST /chat` (Questionnaire) | Verified | Manages state machine across all 20 questions, validates predefined choices, normalizes inputs, saves canonical answers. |
| **Endpoint 3** | `POST /chat` (Unsure Flow) | Verified | On treatment questions (Q10–Q18), "Unsure" / "ಖಚಿತವಿಲ್ಲ" triggers educational explanation without committing a preference. |
| **Endpoint 3** | `POST /chat` (Post-Q RAG) | Verified | Completed questionnaire sessions transition into general informational RAG chat. |
| **Endpoint 4** | `POST /patient-record` | Verified | Returns canonical structured record (patient info, medical background, treatment preferences, personal values). |
| **Endpoint 5** | `POST /doctor-dashboard` | Verified | Aggregates treatment preference counts (`yes`, `no`, `unsure`), unanswered preferences, and unresolved preferences. |
| **Bilingual Support** | English & Kannada localization | Verified | Full Q1–Q20 text and answer normalization (`"ಹೌದು"` → `"Yes"`, `"ಇಲ್ಲ"` → `"No"`, `"ಖಚಿತವಿಲ್ಲ"` → `"Unsure"`). |
| **Knowledge Base** | PDF extraction & chunking | Verified | Audited all 20 PDFs in `knowledge/`. 15 digital PDFs successfully extract ~130,000+ characters into 240 chunks. |
| **Vector Search** | MiniLM + FAISS indexing | Verified | Uses `sentence-transformers/all-MiniLM-L6-v2` with normalized inner-product FAISS index. Tested and verified locally. |
| **Automated Tests** | Test suite (`pytest`) | Verified | 12 of 12 tests passed covering all endpoints, auth, localization, RAG, and retrieval. |
| **Package** | `AHCP_AI_Service_Final.zip` | Verified | Integrity verified (`testzip()`). Excludes `.venv`, caches, secrets, and temp files. |

---

## 2. Outstanding Blockers & Backend Teammate Action Items

### A. Live OpenRouter Generation
- **Current State**: Blocked / Unverified with live LLM API.
- **Reason**: No real `OPENROUTER_API_KEY` was configured in the environment. Offline tests and running endpoints use mocked/controlled responses.
- **Action for Backend Team**:
  1. Add a valid OpenRouter API key to `.env` (`OPENROUTER_API_KEY=sk-or-v1-...`).
  2. Verify that free-tier quota is active on OpenRouter for model `openrouter/free` (or specify an alternative model in `OPENROUTER_MODEL`).

### B. Session Storage Scalability
- **Current State**: In-memory dictionary (`conversation_store = {}`).
- **Limitation**: Process restarts lose active sessions. Multi-worker uvicorn configurations (`--workers N`) will experience state fragmentation without a sticky session load balancer.
- **Action for Backend Team**:
  1. For production deployment, integrate persistent session storage (e.g., Redis or database) or maintain a single worker process until shared storage is implemented.

### C. Backend Proxy Architecture
- **Current State**: AI service requires `X-API-Key`.
- **Action for Backend Team**:
  1. The main application backend must act as an API gateway proxying patient requests from the web/mobile frontend to the AI service.
  2. `AHCP_AI_SERVICE_API_KEY` must remain strictly server-side and **must never be sent to the frontend browser**.

### D. Scanned PDF Documents (Optional OCR)
- **Current State**: 5 of the 20 PDFs are scanned raster images without embedded text layers:
  1. `Advance Medical Directive (Living Will) Guide.pdf`
  2. `Artificial Nutrition and Feeding Tubes.pdf`
  3. `Choosing a Healthcare Representative.pdf`
  4. `Understanding the Legal Aspects of End-of-Life Care and Living Wills in India.pdf`
  5. `Withdrawal of Life Support.pdf`
- **Action for Backend Team**:
  - The ingestion engine gracefully skips image-only PDFs with a warning log without failing. If text from these 5 guides is needed in RAG retrieval, run OCR (e.g. Adobe Acrobat OCR or Tesseract) and replace the PDFs in `knowledge/`.
