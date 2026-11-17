import unittest
import json
from unittest.mock import patch
from datetime import date
from backend.config import Config
from backend.app import create_app
from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.ai_session import AISession
from backend.services.ai_service import AIService
from backend.utils.auth_helpers import generate_token

class TestConfig(Config):
    TESTING = True
    ENV = 'testing'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    AHCP_AI_SERVICE_API_KEY = 'test-secret-key-123'
    JWT_SECRET_KEY = 'test-jwt-secret'

class QuestionnaireValidationTestCase(unittest.TestCase):
    """Regression tests verifying Q1 full-name text validation, Q2 date parsing, and absence of choice validation errors."""

    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create patient user
        self.patient_user = User(
            email="kajal_test@example.com",
            full_name="Original Name",
            role="patient"
        )
        self.patient_user.set_password("SecurePass123!")
        db.session.add(self.patient_user)
        db.session.commit()

        self.patient = Patient(
            user_id=self.patient_user.id,
            phone="+919876543210",
            preferred_language="English"
        )
        db.session.add(self.patient)
        db.session.commit()

        self.token = generate_token(self.patient_user.id, self.patient_user.email, self.patient_user.role)
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    @patch("backend.services.ai_service.AIService._request")
    def test_q1_accepts_name_and_persists_to_user_profile(self, mock_ai_req):
        """User enters 'kajal' for Q1. Must validate text and persist to user profile."""
        session = AISession(
            session_id="session-val-1",
            patient_id=self.patient.patient_id,
            language="en",
            current_question=1
        )
        db.session.add(session)
        db.session.commit()

        mock_ai_req.return_value = {
            "status": "saved",
            "message": "Thank you, kajal.",
            "next_question": {
                "question_number": 2,
                "question": "What is your date of birth?",
                "options": None
            }
        }

        res = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "session-val-1", "message": "kajal"}),
            headers=self.headers
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["status"], "saved")

        # Verify question_number was forwarded to FastAPI
        mock_ai_req.assert_called_once()
        call_kwargs = mock_ai_req.call_args[1]
        self.assertEqual(call_kwargs["json"]["question_number"], 1)
        self.assertEqual(call_kwargs["json"]["message"], "kajal")

        # Verify User profile was updated
        updated_user = db.session.get(User, self.patient_user.id)
        self.assertEqual(updated_user.full_name, "kajal")

    @patch("backend.services.ai_service.AIService._request")
    def test_q2_accepts_dd_mm_yyyy_dates_without_choice_validation(self, mock_ai_req):
        """User enters '12/4/2002' and '12/4/2003' for Q2.
        Must parse as valid dates, persist date_of_birth and derived age, and never return choice errors."""
        session = AISession(
            session_id="session-val-2",
            patient_id=self.patient.patient_id,
            language="en",
            current_question=2
        )
        db.session.add(session)
        db.session.commit()

        mock_ai_req.return_value = {
            "status": "saved",
            "message": "Date of birth recorded.",
            "next_question": {
                "question_number": 3,
                "question": "What is your gender?",
                "options": ["Male", "Female", "Other"]
            }
        }

        # 1. Test 12/4/2002
        res = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "session-val-2", "message": "12/4/2002"}),
            headers=self.headers
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["status"], "saved")
        self.assertNotIn("select one of the available options", (data.get("message") or "").lower())

        # Verify FastAPI received question_number: 2
        call_kwargs = mock_ai_req.call_args[1]
        self.assertEqual(call_kwargs["json"]["question_number"], 2)

        # Verify Patient record was updated
        updated_patient = db.session.get(Patient, self.patient.patient_id)
        self.assertEqual(updated_patient.date_of_birth, date(2002, 4, 12))
        self.assertGreater(updated_patient.age, 20)

        # 2. Test 12/4/2003
        session.current_question = 2
        db.session.commit()

        res2 = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "session-val-2", "message": "12/4/2003"}),
            headers=self.headers
        )
        self.assertEqual(res2.status_code, 200)
        data2 = json.loads(res2.data)
        self.assertEqual(data2["status"], "saved")
        self.assertNotIn("select one of the available options", (data2.get("message") or "").lower())

        updated_patient = db.session.get(Patient, self.patient.patient_id)
        self.assertEqual(updated_patient.date_of_birth, date(2003, 4, 12))

    def test_q2_rejects_genuinely_invalid_dates_and_keeps_question_active(self):
        """User enters invalid date (32/4/2002) or future date. Must return invalid with format guidance."""
        session = AISession(
            session_id="session-val-3",
            patient_id=self.patient.patient_id,
            language="en",
            current_question=2
        )
        db.session.add(session)
        db.session.commit()

        # Invalid day 32
        res = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "session-val-3", "message": "32/4/2002"}),
            headers=self.headers
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["status"], "invalid")
        self.assertIn("DD/MM/YYYY", data["message"])
        self.assertEqual(data["question_number"], 2)

        # Pointer must not advance
        fresh_session = AISession.query.filter_by(session_id="session-val-3").first()
        self.assertIsNotNone(fresh_session)
        self.assertEqual(fresh_session.current_question, 2)

    def test_q1_rejects_dates_or_boolean_words(self):
        """User enters date string or 'Yes' for Q1. Must reject and ask for name."""
        session = AISession(
            session_id="session-val-4",
            patient_id=self.patient.patient_id,
            language="en",
            current_question=1
        )
        db.session.add(session)
        db.session.commit()

        res = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "session-val-4", "message": "12/04/2002"}),
            headers=self.headers
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["status"], "invalid")
        self.assertIn("not a date", data["message"].lower())
        self.assertEqual(data["question_number"], 1)

if __name__ == "__main__":
    unittest.main()
