# Patient-Centered Advance Care Planning (ACP) System Backend

This repository houses the production-ready backend for the **Patient-Centered Advance Care Planning System**. The system manages clinical patient details, captures structured life-prolonging treatment directives from AI conversational models, supports Designated Healthcare Representative (DHR) management, maintains audit logs for medical governance, and dynamically compiles Advance Medical Directive (AMD) documents as legally conforming PDFs using ReportLab, storing them in Supabase Storage.

## Tech Stack
* **Framework:** Python Flask
* **Database Layer:** Supabase PostgreSQL (managed via SQLAlchemy ORM)
* **Storage Layer:** Supabase Storage (storing generated directive PDFs)
* **Serialization/Validation:** Marshmallow (with marshmallow-sqlalchemy)
* **Document Rendering:** ReportLab
* **Authentication:** Custom JWT Middleware

---

## Directory Structure
```
backend/
├── app.py                  # App entry point & Factory
├── config.py               # Config parsing & Validation
├── extensions.py           # DB & Marshmallow extension instances
├── requirements.txt        # Python dependency specifications
├── .env.example            # Environment variables template
├── README.md               # Backend API and setup documentation
├── database/
│   └── seed.py             # Database seed tool for testing
├── models/
│   ├── __init__.py         # Aggregated models imports
│   ├── user.py             # User accounts & roles
│   ├── patient.py          # Clinical patient profiles
│   ├── acp_preference.py   # Detailed care preferences & workflow
│   ├── dhr.py              # Designated Healthcare Representatives
│   ├── chat_history.py     # AI Chatbot dialogue sessions
│   ├── generated_amd.py    # Generated PDF metadata
│   └── audit_log.py        # Log trails for medical auditing
├── schemas/
│   ├── __init__.py         # Aggregated Marshmallow schemas
│   ├── user.py             # User schema
│   ├── patient.py          # Patient validations
│   ├── acp_preference.py   # Care preference validations
│   ├── dhr.py              # DHR validations
│   ├── chat_history.py     # Conversation log validations
│   └── amd.py              # Witness & Notary validations
├── controllers/
│   ├── __init__.py
│   ├── patient_controller.py
│   ├── acp_controller.py
│   ├── dhr_controller.py
│   ├── chat_controller.py
│   ├── audit_controller.py
│   ├── amd_controller.py
│   └── dashboard_controller.py
├── routes/
│   ├── __init__.py         # Blueprint configuration
│   └── api.py              # Endpoint binding routes
├── services/
│   ├── __init__.py
│   ├── patient_service.py  # Patient DB actions
│   ├── acp_service.py      # Preference workflow actions
│   ├── dhr_service.py      # DHR management
│   ├── chat_service.py     # AI mapping integration
│   ├── audit_service.py    # Medical compliance logger
│   ├── amd_service.py      # Orchestrates PDF rendering and storage
│   └── storage_service.py  # Supabase Storage client integrations
├── static/
│   └── openapi.json        # Swagger API documentation
├── tests/
│   └── test_api.py         # End-to-end integration tests
└── generated_pdfs/         # Local temporary files buffer
```

---

## Installation & Setup

1. **Clone & Navigate:**
   ```bash
   cd ACP_System/backend
   ```

2. **Configure Environment Variables:**
   Copy `.env.example` to `.env` and fill in your Supabase connection strings, storage buckets, and keys:
   ```bash
   cp .env.example .env
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize & Seed Database:**
   Ensure database tables are provisioned and populated with sample clinical credentials:
   ```bash
   python -m database.seed
   ```

5. **Start Flask Dev Server:**
   ```bash
   python app.py
   ```
   The backend will run on `http://localhost:5000`.

---

## API Documentation (Swagger)
The API documentation is integrated dynamically via Swagger UI. Once the backend server is running, navigate to:
* **Interactive UI:** `http://localhost:5000/api/docs` or `/docs`
* **JSON Specs:** `http://localhost:5000/static/openapi.json`

---

## REST Endpoints Cheat Sheet

### Patient Profiles
* `POST /api/patients` - Register a patient profile
* `GET /api/patients` - List all patient files (Doctors/Admins)
* `GET /api/patients/{id}` - Fetch patient details
* `PUT /api/patients/{id}` - Modify clinical metrics
* `DELETE /api/patients/{id}` - Permanently erase file (Admins)

### Advance Care Planning (ACP)
* `POST /api/acp` - Save patient healthcare preferences
* `GET /api/acp/{patient_id}` - Retrieve preferences dossier
* `PUT /api/acp/{patient_id}` - Modify care preferences

### Designated Healthcare Representatives (DHR)
* `POST /api/dhr` - Appoint a new representative
* `GET /api/dhr/{patient_id}` - Retrieve representatives sorted by preference rank
* `PUT /api/dhr/{id}` - Modify DHR details
* `DELETE /api/dhr/{id}` - Remove a DHR appointment

### Document (AMD) Management
* `POST /api/amd/generate` - Generate signed AMD PDF & upload to Supabase
* `GET /api/amd/download/{patient_id}` - Redirect to the active PDF download URL

### Webhooks (AI Chatbot)
* `POST /api/chat/process` - Receive structured clinical data parsed from conversations

### Dashboards
* **Doctor Workspace:**
  * `GET /api/doctor/patients` - Full patient list with filters (language, status, review)
  * `GET /api/doctor/patient/{id}` - Full patient detail overview
  * `GET /api/doctor/amd/{patient_id}` - Fetch history of generated document versions
  * `PUT /api/doctor/review/{patient_id}` - Approve, verify, or reject patient preferences
* **Admin Workspace:**
  * `GET /api/admin/dashboard` - Global metrics (patients, completion rate, audit log feed)

---

## Running Unit Tests
To run the automated test suite locally:
```bash
python -m unittest tests.test_api
```
This runs integrations testing, checks route protection decorators, maps preferences, and checks ReportLab generation mocks.

To run backend:

* **PowerShell:**
  ```powershell
  .\backend\.venv\Scripts\Activate.ps1
  python -m backend.app
  ```

* **Command Prompt (CMD):**
  ```cmd
  .\backend\.venv\Scripts\activate.bat
  python -m backend.app
  ```

* **Direct execution without activating:**
  ```powershell
  .\backend\.venv\Scripts\python.exe -m backend.app
  ```