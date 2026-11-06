AHCP source knowledge corpus

This folder includes the healthcare and advance-care-planning PDF sources available with the project package. The service extracts text from these PDFs at first RAG retrieval and builds a MiniLM + FAISS index locally. Some PDFs may be image/scanned-only; OCR them before use if they yield no extractable text. Do not add patient-identifiable records here.

The live OpenRouter answer path requires OPENROUTER_API_KEY and may be rate-limited by the provider. API keys must never be stored in this folder or committed to version control.
