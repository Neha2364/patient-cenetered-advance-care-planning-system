# Backend Integration Handoff — AHCP AI Service

This document describes how the main application backend connects to and coordinates with the **AHCP AI Service**.

---

## 1. Authentication & Base URL

- **Base URL**: Set via configuration (e.g. `http://127.0.0.1:8000` locally, or an internal service URL in production).
- **Authentication**: All routes except `GET /health` require the HTTP header:
  ```http
  X-API-Key: <AHCP_AI_SERVICE_API_KEY>
  ```
- **Security Rule**: The `AHCP_AI_SERVICE_API_KEY` is a private server-to-server secret. Store it securely in backend secret stores. **Never expose this key to frontend or client-side code.**

---

## 2. API Contract & Endpoints

### 1. `GET /health`
Public liveness and health check.
- **Request**: `GET /health` (no headers)
- **Response** (`200 OK`):
  ```json
  {
    "status": "healthy",
    "service": "AHCP AI Service",
    "version": "1.0.0"
  }
  ```

---

### 2. `POST /session`
Initializes a new questionnaire session for a patient.
- **Headers**: `X-API-Key: <key>`, `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "language": "en"  // "en" for English, "kn" for Kannada
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "session_id": "session_20261015_094500_123456",
    "language": "en",
    "question_number": 1,
    "question": "What is your full name?",
    "options": null
  }
  ```

---

### 3. `POST /chat`
Sends a patient answer or question message to the active session.
- **Headers**: `X-API-Key: <key>`, `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "session_id": "session_20261015_094500_123456",
    "message": "Jane Doe"
  }
  ```
- **Response Status Types**:
  1. **`saved`**: Answer saved into patient record; returns `next_question`.
     ```json
     {
       "status": "saved",
       "message": "Your answer has been saved.",
       "question_number": 1,
       "answer": "Jane Doe",
       "next_question": {
         "question_number": 2,
         "question": "What is your date of birth?",
         "options": null
       },
       "sources": null
     }
     ```
  2. **`explanation`** (Unsure Flow): When a patient selects "Unsure" or "ಖಚಿತವಿಲ್ಲ" on treatment preference questions (Q10–Q18). **The treatment choice is NOT saved**, keeping the current question active for the patient to decide after reading the explanation.
     ```json
     {
       "status": "explanation",
       "message": "Cardiopulmonary resuscitation (CPR) is an emergency procedure...",
       "question_number": 10,
       "answer": null,
       "next_question": null,
       "sources": [
         {"source": "CPR _ Cardiopulmonary Resuscitation _ MedlinePlus.pdf", "category": "knowledge", "score": 0.53}
       ]
     }
     ```
  3. **`invalid`**: The input was empty or did not match any of the allowed choice options. Displays options again.
     ```json
     {
       "status": "invalid",
       "message": "Please select one of the available options.",
       "question_number": 10,
       "answer": null,
       "next_question": {
         "question_number": 10,
         "question": "Would you want CPR if your heart stopped?",
         "options": ["Yes", "No", "Unsure"]
       },
       "sources": null
     }
     ```
  4. **`completed`**: All 20 questions have been answered.
     ```json
     {
       "status": "completed",
       "message": "Thank you. The AHCP questionnaire has been completed.",
       "question_number": 20,
       "answer": "No additional wishes",
       "next_question": null,
       "sources": null
     }
     ```
  5. **`answer`** (Post-Questionnaire RAG Mode): If the questionnaire is already completed, subsequent messages are treated as general informational RAG questions.
     ```json
     {
       "status": "answer",
       "message": "A living will (Advance Medical Directive) is...",
       "question_number": null,
       "answer": "...",
       "next_question": null,
       "sources": [...]
     }
     ```

---

### 4. `POST /patient-record?session_id=<id>`
Fetches the canonical structured record constructed directly from patient answers.
- **Headers**: `X-API-Key: <key>`
- **Response** (`200 OK`):
  ```json
  {
    "patient_information": {
      "full_name": "Jane Doe",
      "date_of_birth": "1985-04-12",
      "gender": "Female",
      "healthcare_decision_maker": "John Doe",
      "decision_maker_relationship": "Spouse"
    },
    "medical_background": {
      "chronic_conditions": "Hypertension",
      "serious_hospitalization": "None",
      "long_term_medications": "Amlodipine",
      "allergies": "Penicillin"
    },
    "treatment_preferences": {
      "cpr": "Yes",
      "ventilator": "No",
      "dialysis": "Unsure",
      "artificial_nutrition": "No",
      "artificial_hydration": "Yes",
      "organ_donation": "Yes",
      "goals_of_care": "Comfort-focused care",
      "preferred_place_of_care": "Home",
      "level_of_medical_intervention": "Limited medical treatment"
    },
    "personal_values": {
      "most_important_goal": "Being with family and comfortable",
      "additional_wishes": "Please contact my spouse for any emergency."
    }
  }
  ```

---

### 5. `POST /doctor-dashboard?session_id=<id>`
Provides dashboard visualization summary metrics alongside patient details.
- **Headers**: `X-API-Key: <key>`
- **Response** (`200 OK`):
  ```json
  {
    "patient_information": { ... },
    "medical_background": { ... },
    "treatment_preferences": { ... },
    "personal_values": { ... },
    "visualization": {
      "preference_summary": {
        "yes": 4,
        "no": 2,
        "unsure": 1
      },
      "unanswered_preferences": [],
      "unresolved_preferences": ["dialysis"]
    }
  }
  ```

---

## 3. Architecture & Integration Boundaries

> [!IMPORTANT]
> **Key Integration Rules:**
> 1. **Backend Proxy Pattern**: The main application backend must proxy all patient requests to the AI service. The frontend (web/mobile) must NEVER talk directly to the AI service.
> 2. **Secret Isolation**: Store `AHCP_AI_SERVICE_API_KEY` exclusively in server-side environment secrets. **Never send or expose this secret to the client-side frontend.**
> 3. **In-Memory Session Storage**: Active sessions are currently kept in Python process memory (`conversation_store = {}`). Restarting the service clears all active sessions. Do not run multi-worker setups (`uvicorn --workers N`) until a shared database or Redis session store is implemented.
> 4. **Live OpenRouter Status**: Offline RAG retrieval and question flows are fully verified with mocked generation. Live OpenRouter LLM generation remains **unverified** until valid live API credentials and quota are supplied in `.env`.

---

## 4. Minimal Backend Integration Example (Python / requests)

```python
import os
import requests

AI_BASE_URL = os.getenv("AHCP_AI_BASE_URL", "http://127.0.0.1:8000")
AI_KEY = os.getenv("AHCP_AI_SERVICE_API_KEY", "your-secret-key")
HEADERS = {"X-API-Key": AI_KEY, "Content-Type": "application/json"}

# 1. Create a session
res = requests.post(f"{AI_BASE_URL}/session", json={"language": "en"}, headers=HEADERS)
session = res.json()
session_id = session["session_id"]
print(f"Started session {session_id}, Q1: {session['question']}")

# 2. Submit an answer
chat_res = requests.post(
    f"{AI_BASE_URL}/chat",
    json={"session_id": session_id, "message": "Jane Doe"},
    headers=HEADERS
)
print("Chat status:", chat_res.json()["status"])

# 3. Retrieve structured patient record
record_res = requests.post(
    f"{AI_BASE_URL}/patient-record",
    params={"session_id": session_id},
    headers=HEADERS
)
print("Patient Record:", record_res.json())
```
