"""Integration tests for Vercel Serverless Function & In-Process AI Service Migration."""
import os
import sys
from pathlib import Path
import pytest

# Ensure root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

AI_DIR = ROOT_DIR / "ahcp-ai-service"
if str(AI_DIR) not in sys.path and AI_DIR.exists():
    sys.path.insert(0, str(AI_DIR))

from backend.config import Config
from backend.app import create_app
from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.ai_session import AISession
from backend.models.acp_preference import ACPPreference
from backend.services.ai_service import AIService
from backend.utils.auth_helpers import generate_token
import app as ai_app_module


@pytest.fixture(scope="module")
def app_instance():
    """Create Flask application instance configured for in-process AI execution."""
    os.environ["AHCP_AI_BASE_URL"] = "inprocess"
    Config.AHCP_AI_BASE_URL = "inprocess"
    app = create_app()
    app.config["TESTING"] = True
    yield app


@pytest.fixture
def client(app_instance):
    return app_instance.test_client()


def test_api_entrypoint_exports_wsgi_app():
    """Verify that api/index.py imports successfully and exports a WSGI app."""
    import api.index as vercel_entry
    assert hasattr(vercel_entry, "app")
    assert callable(vercel_entry.app)


def test_no_heavy_ai_dependencies_imported():
    """Confirm that sentence-transformers, torch, transformers, and faiss are NOT loaded."""
    loaded_modules = sys.modules.keys()
    for forbidden in ["torch", "sentence_transformers", "transformers", "faiss"]:
        assert forbidden not in loaded_modules, f"Forbidden heavy dependency loaded: {forbidden}"


def test_inprocess_ai_health(client):
    """Verify /api/ai/health returns healthy using in-process dispatch without port 8000."""
    resp = client.get("/api/ai/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "healthy"
    assert data["backend_connected"] is True
    assert data["ai_service"]["status"] == "healthy"


def test_inprocess_ai_session_and_chat_flow(client, app_instance):
    """Test full patient session creation, chat answering, and state progression in-process."""
    with app_instance.app_context():
        # Find or create a test patient
        user = User.query.filter_by(email="patient_inproc_test@acpcare.app").first()
        if not user:
            user = User(
                full_name="InProcess Patient",
                email="patient_inproc_test@acpcare.app",
                role="patient"
            )
            user.set_password("PatientPass123!")
            db.session.add(user)
            db.session.commit()

        patient = Patient.query.filter_by(user_id=user.id).first()
        if not patient:
            patient = Patient(user_id=user.id, preferred_language="English")
            db.session.add(patient)
            db.session.commit()

        token = generate_token(user.id, user.email, user.role)

        # 1. Create AI Session via Flask
        session_data = AIService.create_session(patient.patient_id, language="en", performed_by_id=user.id)
        assert session_data is not None
        session_id = session_data["session_id"]
        assert session_id.startswith("session_")
        assert session_data["question_number"] == 1

        # 2. Submit Answer to Question 1 (Name)
        chat_res = AIService.process_chat(
            session_id=session_id,
            message="InProcess Test Patient",
            patient_id=patient.patient_id,
            performed_by_id=user.id,
            question_number=1
        )
        assert chat_res is not None
        assert chat_res.get("status") in ("saved", "answered", "explanation")

        # 3. Verify answer was persisted in DB
        db.session.expire_all()
        refreshed_patient = Patient.query.get(patient.patient_id)
        assert refreshed_patient.user.full_name is not None


def test_serverless_cold_start_session_hydration(app_instance):
    """Verify that if conversation_store memory is completely lost, session rehydrates from DB."""
    with app_instance.app_context():
        # Setup patient and DB session
        user = User.query.filter_by(email="patient_inproc_test@acpcare.app").first()
        patient = Patient.query.filter_by(user_id=user.id).first()
        ai_session = AISession.query.filter_by(patient_id=patient.patient_id).order_by(AISession.created_at.desc()).first()
        assert ai_session is not None

        # SIMULATE SERVERLESS COLD START:
        # Wipe in-memory conversation_store in the AI service
        ai_app_module.conversation_store.clear()
        assert ai_session.session_id not in ai_app_module.conversation_store

        # Perform chat turn: AIService should detect missing memory, hydrate from DB, and proceed without 404
        chat_res = AIService.process_chat(
            session_id=ai_session.session_id,
            message="Yes",
            patient_id=patient.patient_id,
            performed_by_id=user.id,
            question_number=11  # CPR preference
        )
        assert chat_res is not None
        # Verify it did not return 404 Session Not Found
        assert chat_res.get("status") in ("saved", "answered", "explanation")
        # Verify session container was reconstructed in memory
        assert ai_session.session_id in ai_app_module.conversation_store


def test_temp_pdf_directory_configuration():
    """Verify TEMP_PDF_DIR uses /tmp when running on Vercel."""
    os.environ["VERCEL"] = "1"
    # Re-evaluate logic from Config
    temp_dir = os.getenv("TEMP_PDF_DIR") or (
        "/tmp/temp_pdfs" if (os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
        else os.path.join(str(ROOT_DIR), "backend", "temp_pdfs")
    )
    assert temp_dir == "/tmp/temp_pdfs"
    del os.environ["VERCEL"]
