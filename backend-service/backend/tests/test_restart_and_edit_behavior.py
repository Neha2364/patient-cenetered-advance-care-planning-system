import os
import unittest
from datetime import datetime
from backend.app import create_app
from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.acp_preference import ACPPreference
from backend.models.dhr import DHR
from backend.config import Config
from backend.models.ai_session import AISession
from backend.services.ai_service import AIService, AIServiceException

class TestConfig(Config):
    TESTING = True
    ENV = 'testing'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    AHCP_AI_SERVICE_API_KEY = 'test-secret-key-123'
    JWT_SECRET_KEY = 'test-jwt-secret'

class TestRestartAndEditBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(TestConfig)

    def setUp(self):
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create test patient
        self.user = User(
            email="testpatient@example.com",
            role="patient",
            full_name="Rajesh Sharma"
        )
        self.user.set_password("SecurePass123!")
        db.session.add(self.user)
        db.session.commit()

        self.patient = Patient(
            user_id=self.user.id,
            gender="Male",
            age=58,
            preferred_language="English"
        )
        db.session.add(self.patient)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_missing_fields_validation_and_alert_banner(self):
        """Problem 1: Validate missing required fields and alert banners in English and Kannada."""
        # Patient currently lacks phone, address, and DHR
        missing_en = AIService._get_missing_required_fields(self.patient.patient_id, "en")
        self.assertTrue(len(missing_en) >= 3)
        self.assertIn("Designated Healthcare Representative", missing_en)
        self.assertIn("Patient Contact Phone Number", missing_en)
        self.assertIn("Patient Residential Address", missing_en)

        summary_en = AIService._generate_review_summary(self.patient.patient_id, "en")
        self.assertIn("Incomplete Information Required for Confirmation", summary_en)
        self.assertIn("Designated Healthcare Representative", summary_en)

        # In Kannada
        missing_kn = AIService._get_missing_required_fields(self.patient.patient_id, "kn")
        self.assertTrue(len(missing_kn) >= 3)
        summary_kn = AIService._generate_review_summary(self.patient.patient_id, "kn")
        self.assertIn("ದೃಢೀಕರಣಕ್ಕೆ ಅಗತ್ಯವಾದ ಅಪೂರ್ಣ ಮಾಹಿತಿ", summary_kn)

        # Attempting confirmation without required fields must raise 400
        session = AISession(
            session_id="test-incomplete-sess",
            patient_id=self.patient.patient_id,
            language="en",
            current_question=36
        )
        db.session.add(session)
        db.session.commit()

        with self.assertRaises(AIServiceException) as ctx:
            AIService.confirm_review(self.patient.patient_id, session_id=session.session_id)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("missing", ctx.exception.message.lower())

    def test_confirmation_and_completed_session_preservation(self):
        """Problem 1 & 3: Populating required fields confirms successfully and preserves state."""
        self.patient.phone = "+919876543210"
        self.patient.address = "45 Residency Road, Bengaluru"
        dhr = DHR(
            patient_id=self.patient.patient_id,
            full_name="Ananya Sharma",
            relationship="Daughter",
            mobile_primary="+919876543299",
            email_primary="ananya@example.com",
            preference_order=1
        )
        db.session.add(dhr)
        db.session.commit()

        # Review summary should now show verified banner
        summary_en = AIService._generate_review_summary(self.patient.patient_id, "en")
        self.assertIn("All required information is complete and verified", summary_en)
        self.assertNotIn("Incomplete Information", summary_en)

        session = AISession(
            session_id="test-complete-sess",
            patient_id=self.patient.patient_id,
            language="en",
            current_question=36
        )
        db.session.add(session)
        db.session.commit()

        # Confirm review
        res = AIService.confirm_review(self.patient.patient_id, session_id=session.session_id)
        self.assertEqual(res["status"], "completed")
        self.assertTrue(res["is_completed"])
        self.assertEqual(res["question_number"], 36)
        self.assertIsNotNone(res["next_question"])
        self.assertEqual(res["next_question"]["question_number"], 36)

        # Active session data should return completed session without resetting to Q1
        active_data = AIService.get_active_session_data(self.patient.patient_id)
        self.assertIsNotNone(active_data)
        self.assertTrue(active_data["is_completed"])
        self.assertEqual(active_data["current_question"], 36)
        self.assertIn("Complete Advance Care Plan", active_data["question"])

    def test_edit_flow_without_restarting_from_q1(self):
        """Problem 2: Editing a specific section jumps to that item, updates it, and returns to Q44."""
        # Setup preferences with chemotherapy = WANT
        pref = ACPPreference(
            patient_id=self.patient.patient_id,
            chemotherapy_preference="WANT",
            ventilator_preference="DO NOT WANT",
            cpr_preference="WANT"
        )
        db.session.add(pref)
        db.session.commit()

        # Session must be at Q44 (Review & Confirm) — NOT Q36 (alt DHR address in new schema)
        session = AISession(
            session_id="test-edit-sess",
            patient_id=self.patient.patient_id,
            language="en",
            current_question=44
        )
        db.session.add(session)
        db.session.commit()

        # 1. User sends "Edit Chemotherapy" → jumps to Q1014 (1000+14=chemotherapy in new schema)
        jump_res = AIService.process_chat(
            session_id=session.session_id,
            message="Edit Chemotherapy",
            patient_id=self.patient.patient_id,
            performed_by_id=self.user.id
        )
        self.assertEqual(jump_res["question_number"], 1014)
        self.assertIn("Current saved value", jump_res["message"])
        self.assertIn("Yes (WANT)", jump_res["message"])
        self.assertIn("Keep Current Value", jump_res["next_question"]["options"])

        # 2. User answers "I do not want this treatment"
        ans_res = AIService.process_chat(
            session_id=session.session_id,
            message="I do not want this treatment",
            patient_id=self.patient.patient_id,
            performed_by_id=self.user.id
        )
        # Should return directly to Review (Q44)
        self.assertEqual(ans_res["status"], "saved")
        self.assertEqual(ans_res["next_question"]["question_number"], 44)
        self.assertIn("Complete Advance Care Plan (ACP) Summary", ans_res["next_question"]["question"])

        # Check DB updated
        pref = ACPPreference.query.filter_by(patient_id=self.patient.patient_id).first()
        self.assertEqual(pref.chemotherapy_preference, "DO NOT WANT")
        # Other preferences remain untouched!
        self.assertEqual(pref.ventilator_preference, "DO NOT WANT")
        self.assertEqual(pref.cpr_preference, "WANT")

    def test_sanitize_educational_response(self):
        """Problem 4: Educational responses are sanitized of URLs, internal file paths, and chunk tags."""
        raw_text = (
            "CPR (Cardiopulmonary Resuscitation) restores breathing. "
            "For more details see http://localhost:8000/docs or /data/knowledge/acp_guidelines.pdf. "
            "Document: vidhi_living_will.pdf, Chunk ID: 102. Reference [Vidhi Guide]."
        )
        sanitized = AIService._sanitize_educational_response(raw_text)
        self.assertNotIn("http://", sanitized)
        self.assertNotIn("/data/knowledge/", sanitized)
        self.assertNotIn("Chunk ID:", sanitized)
        self.assertNotIn("[Vidhi Guide]", sanitized)
        self.assertIn("CPR (Cardiopulmonary Resuscitation) restores breathing", sanitized)

if __name__ == "__main__":
    unittest.main()
