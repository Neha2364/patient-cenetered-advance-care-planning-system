import sys
import os
import json
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, date

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
_root_dir = os.path.abspath(os.path.join(_backend_dir, ".."))
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

from backend.app import create_app
from backend.config import Config
from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.acp_preference import ACPPreference
from backend.models.dhr import DHR
from backend.models.ai_session import AISession
from backend.services.ai_service import AIService
from backend.utils.auth_helpers import generate_token


class TestConfig(Config):
    TESTING = True
    ENV = 'testing'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    AHCP_AI_SERVICE_API_KEY = 'test-secret-key-123'
    JWT_SECRET_KEY = 'test-jwt-secret'


QUESTIONNAIRE_METADATA = AIService.QUESTIONNAIRE_METADATA
FOLLOW_UP_METADATA = AIService.FOLLOW_UP_METADATA


class ChatbotCleanupTestCase(unittest.TestCase):
    """Exhaustive test suite verifying the 8 criteria for Patient ACP Chatbot question and option cleanup."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app(TestConfig)
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

    def setUp(self):
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Clean existing test users if any
        for email in ["cleanup_pat_en@test.com", "cleanup_pat_kn@test.com", "cleanup_doc@test.com"]:
            u = User.query.filter_by(email=email).first()
            if u:
                db.session.delete(u)
        db.session.commit()

        # Create English test patient (role must be lowercase 'patient')
        self.user_en = User(email="cleanup_pat_en@test.com", role="patient", full_name="Aarav Sharma")
        self.user_en.set_password("SecurePass123!")
        db.session.add(self.user_en)
        db.session.flush()

        self.patient_en = Patient(
            user_id=self.user_en.id,
            preferred_language="English",
            gender="Male",
            date_of_birth=date(1990, 5, 15),
            age=34,
            phone="9876543210"
        )
        db.session.add(self.patient_en)

        # Create Kannada test patient (role must be lowercase 'patient')
        self.user_kn = User(email="cleanup_pat_kn@test.com", role="patient", full_name="ರಾಹುಲ್ ಗೌಡ")
        self.user_kn.set_password("SecurePass123!")
        db.session.add(self.user_kn)
        db.session.flush()

        self.patient_kn = Patient(
            user_id=self.user_kn.id,
            preferred_language="Kannada",
            gender="Male",
            date_of_birth=date(1985, 3, 20),
            age=39,
            phone="9876543211"
        )
        db.session.add(self.patient_kn)

        # Create Doctor user (role must be lowercase 'doctor')
        self.user_doc = User(email="cleanup_doc@test.com", role="doctor", full_name="Dr. Smith")
        self.user_doc.set_password("DoctorPass123!")
        db.session.add(self.user_doc)
        db.session.commit()

        self.token_en = generate_token(self.user_en.id, self.user_en.email, self.user_en.role)
        self.token_kn = generate_token(self.user_kn.id, self.user_kn.email, self.user_kn.role)
        self.token_doc = generate_token(self.user_doc.id, self.user_doc.email, self.user_doc.role)

        self.headers_en = {"Authorization": f"Bearer {self.token_en}", "Content-Type": "application/json"}
        self.headers_kn = {"Authorization": f"Bearer {self.token_kn}", "Content-Type": "application/json"}
        self.headers_doc = {"Authorization": f"Bearer {self.token_doc}", "Content-Type": "application/json"}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # -------------------------------------------------------------------------
    # Criterion 1: Remove Language Preference Question
    # -------------------------------------------------------------------------
    @patch("requests.request")
    def test_1_language_preference_removed_and_dashboard_language_used(self, mock_req):
        """Language preference question is removed from active chatbot prompts; dashboard language is used."""
        # 1. Question 5 absent from metadata
        self.assertNotIn(5, QUESTIONNAIRE_METADATA["en"])
        self.assertNotIn(5, QUESTIONNAIRE_METADATA["kn"])
        self.assertEqual(len(QUESTIONNAIRE_METADATA["en"]), 43)
        self.assertEqual(len(QUESTIONNAIRE_METADATA["kn"]), 43)
        self.assertEqual(set(QUESTIONNAIRE_METADATA["en"].keys()), set(range(1, 45)) - {5})

        # 2. Creating session for Kannada patient auto-selects 'kn' from dashboard profile
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "session_id": "sess_kn_auto",
            "language": "kn",
            "question_number": 1,
            "question": QUESTIONNAIRE_METADATA["kn"][1]["question"],
            "options": None
        }
        mock_req.return_value = mock_resp

        res_kn = self.client.post("/api/ai/session", data=json.dumps({}), headers=self.headers_kn)
        self.assertEqual(res_kn.status_code, 200)
        data_kn = json.loads(res_kn.data)
        self.assertEqual(data_kn.get("language"), "kn")
        # Check first question is in Kannada
        self.assertIn("ಹೆಸರು", data_kn.get("question", ""))

        # 3. In chatbot flow: answering Q4 (phone) advances directly to Q6 (address), completely skipping Q5
        sess = AISession(
            session_id="sess_lang_skip_test",
            patient_id=self.patient_en.patient_id,
            language="en",
            current_question=4
        )
        db.session.add(sess)
        db.session.commit()

        mock_resp_chat = MagicMock()
        mock_resp_chat.ok = True
        mock_resp_chat.status_code = 200
        mock_resp_chat.json.return_value = {
            "status": "saved",
            "message": "Answer recorded.",
            "question_number": 4,
            "answer": "9876543210",
            "next_question": QUESTIONNAIRE_METADATA["en"][6],
            "sources": None
        }
        mock_req.return_value = mock_resp_chat

        res_chat = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_lang_skip_test", "message": "9876543210"}),
            headers=self.headers_en
        )
        self.assertEqual(res_chat.status_code, 200)
        chat_data = json.loads(res_chat.data)
        self.assertEqual(chat_data["status"], "saved")
        # Next question MUST be Q6 (residential address), not Q5
        self.assertEqual(chat_data["next_question"]["question_number"], 6)
        self.assertIn("address", chat_data["next_question"]["question"].lower())

        # 4. Patient preferred_language remains in database
        db.session.refresh(self.patient_en)
        self.assertEqual(self.patient_en.preferred_language, "English")
        db.session.refresh(self.patient_kn)
        self.assertEqual(self.patient_kn.preferred_language, "Kannada")

    # -------------------------------------------------------------------------
    # Criterion 2: Simplify Medical Background Questions (Q7, Q8, Q9, Q10)
    # -------------------------------------------------------------------------
    @patch("requests.request")
    def test_2_simplify_medical_background_questions(self, mock_req):
        """Medical background questions display simplified wording without bracketed explanatory text."""
        en_meta = QUESTIONNAIRE_METADATA["en"]
        kn_meta = QUESTIONNAIRE_METADATA["kn"]

        # Exact wording checks for English
        self.assertEqual(en_meta[7]["question"], "Do you have any chronic medical conditions?")
        self.assertEqual(en_meta[8]["question"], "Have you ever had a serious hospitalization or major illness?")
        self.assertEqual(en_meta[9]["question"], "What long-term medications do you currently take?")
        self.assertEqual(en_meta[10]["question"], "Do you have any known allergies to medications, food, or other substances?")

        # Exact wording checks for Kannada
        self.assertEqual(kn_meta[7]["question"], "ನಿಮಗೆ ಯಾವುದೇ ದೀರ್ಘಕಾಲದ ವೈದ್ಯಕೀಯ ಕಾಯಿಲೆಗಳಿವೆಯೇ?")
        self.assertEqual(kn_meta[8]["question"], "ನೀವು ಎಂದಾದರೂ ಗಂಭೀರ ಕಾಯಿಲೆಯಿಂದ ಆಸ್ಪತ್ರೆಗೆ ದಾಖಲಾಗಿದ್ದೀರಾ ಅಥವಾ ದೊಡ್ಡ ಶಸ್ತ್ರಚಿಕಿತ್ಸೆಗೆ ಒಳಗಾಗಿದ್ದೀರಾ?")
        self.assertEqual(kn_meta[9]["question"], "ನೀವು ಪ್ರಸ್ತುತ ನಿಯಮಿತವಾಗಿ ತೆಗೆದುಕೊಳ್ಳುತ್ತಿರುವ ದೀರ್ಘಕಾಲದ ಔಷಧಿಗಳು ಯಾವುವು?")
        self.assertEqual(kn_meta[10]["question"], "ನಿಮಗೆ ಔಷಧಿಗಳು, ಆಹಾರ ಅಥವಾ ಇತರ ವಸ್ತುಗಳಿಂದ ಯಾವುದೇ ಅಲರ್ಜಿಗಳಿವೆಯೇ?")

        # Verify no bracketed text in Q7..Q10 in either language
        for q in (7, 8, 9, 10):
            self.assertNotIn("(", en_meta[q]["question"])
            self.assertNotIn(")", en_meta[q]["question"])
            self.assertNotIn("(", kn_meta[q]["question"])
            self.assertNotIn(")", kn_meta[q]["question"])

        # Test answering with real conditions, hospitalization, medications, allergies
        sess = AISession(session_id="sess_med_bg_test", patient_id=self.patient_en.patient_id, language="en", current_question=7)
        db.session.add(sess)
        db.session.commit()

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "saved", "message": "Answer recorded."}
        mock_req.return_value = mock_resp

        # Q7 answer
        res = self.client.post("/api/ai/chat", data=json.dumps({"session_id": "sess_med_bg_test", "message": "Hypertension and Asthma"}), headers=self.headers_en)
        self.assertEqual(res.status_code, 200)
        # Q8 answer
        res = self.client.post("/api/ai/chat", data=json.dumps({"session_id": "sess_med_bg_test", "message": "Appendectomy in 2018"}), headers=self.headers_en)
        self.assertEqual(res.status_code, 200)
        # Q9 answer
        res = self.client.post("/api/ai/chat", data=json.dumps({"session_id": "sess_med_bg_test", "message": "Amlodipine 5mg daily"}), headers=self.headers_en)
        self.assertEqual(res.status_code, 200)
        # Q10 answer
        res = self.client.post("/api/ai/chat", data=json.dumps({"session_id": "sess_med_bg_test", "message": "Penicillin and Peanuts"}), headers=self.headers_en)
        self.assertEqual(res.status_code, 200)

        db.session.refresh(self.patient_en)
        self.assertEqual(self.patient_en.chronic_conditions, "Hypertension and Asthma")
        self.assertEqual(self.patient_en.serious_hospitalization, "Appendectomy in 2018")
        self.assertEqual(self.patient_en.long_term_medications, "Amlodipine 5mg daily")
        self.assertEqual(self.patient_en.allergies, "Penicillin and Peanuts")

        # Test entering "None" or "No"
        AIService._persist_canonical_answer(self.patient_en.patient_id, 7, "None", self.user_en.id)
        AIService._persist_canonical_answer(self.patient_en.patient_id, 8, "No", self.user_en.id)
        AIService._persist_canonical_answer(self.patient_en.patient_id, 9, "None", self.user_en.id)
        AIService._persist_canonical_answer(self.patient_en.patient_id, 10, "No", self.user_en.id)
        db.session.commit()
        db.session.refresh(self.patient_en)
        self.assertEqual(self.patient_en.chronic_conditions, "None")
        self.assertEqual(self.patient_en.serious_hospitalization, "No")
        self.assertEqual(self.patient_en.long_term_medications, "None")
        self.assertEqual(self.patient_en.allergies, "No")

    # -------------------------------------------------------------------------
    # Criterion 3: Remove Unsure Options from Donation Questions
    # -------------------------------------------------------------------------
    @patch("requests.request")
    def test_3_remove_unsure_from_donation_questions_only(self, mock_req):
        """Donation questions show only Yes and No, rejecting Unsure; saves correctly."""
        en_meta = QUESTIONNAIRE_METADATA["en"]
        kn_meta = QUESTIONNAIRE_METADATA["kn"]

        # 1. Q37 Organ donation options
        self.assertEqual(en_meta[37]["options"], ["Yes", "No"])
        self.assertEqual(kn_meta[37]["options"], ["ಹೌದು", "ಇಲ್ಲ"])
        self.assertNotIn("Unsure", en_meta[37]["options"])
        self.assertNotIn("ಖಚಿತವಿಲ್ಲ", kn_meta[37]["options"])

        # 2. Q38 Body donation options
        self.assertEqual(en_meta[38]["options"], ["Yes", "No"])
        self.assertEqual(kn_meta[38]["options"], ["ಹೌದು", "ಇಲ್ಲ"])
        self.assertNotIn("Unsure", en_meta[38]["options"])
        self.assertNotIn("ಖಚಿತವಿಲ್ಲ", kn_meta[38]["options"])

        # 3. Follow-up Q30 (Body donation) options
        self.assertEqual(FOLLOW_UP_METADATA["en"][30]["options"], ["Yes", "No"])
        self.assertEqual(FOLLOW_UP_METADATA["kn"][30]["options"], ["ಹೌದು", "ಇಲ್ಲ"])

        # 4. Rejecting "Unsure" on Q37
        sess = AISession(session_id="sess_donation_test", patient_id=self.patient_en.patient_id, language="en", current_question=37)
        db.session.add(sess)
        db.session.commit()

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "saved", "message": "Answer recorded."}
        mock_req.return_value = mock_resp

        res_unsure_37 = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_donation_test", "message": "Unsure"}),
            headers=self.headers_en
        )
        self.assertEqual(res_unsure_37.status_code, 200)
        data_unsure_37 = json.loads(res_unsure_37.data)
        self.assertEqual(data_unsure_37["status"], "invalid")
        self.assertIn("Please choose Yes or No", data_unsure_37["message"])
        # Session pointer should NOT advance
        db.session.refresh(sess)
        self.assertEqual(sess.current_question, 37)

        # 5. Accepting "Yes" on Q37
        res_yes_37 = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_donation_test", "message": "Yes"}),
            headers=self.headers_en
        )
        self.assertEqual(res_yes_37.status_code, 200)
        pref = ACPPreference.query.filter_by(patient_id=self.patient_en.patient_id).first()
        self.assertIsNotNone(pref)
        self.assertEqual(pref.organ_donation, "YES")

        # 6. Rejecting "Unsure" on Q38
        db.session.refresh(sess)
        self.assertEqual(sess.current_question, 38)
        res_unsure_38 = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_donation_test", "message": "Unsure"}),
            headers=self.headers_en
        )
        self.assertEqual(res_unsure_38.status_code, 200)
        data_unsure_38 = json.loads(res_unsure_38.data)
        self.assertEqual(data_unsure_38["status"], "invalid")
        self.assertIn("Please choose Yes or No", data_unsure_38["message"])

        # 7. Accepting "No" on Q38
        res_no_38 = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_donation_test", "message": "No"}),
            headers=self.headers_en
        )
        self.assertEqual(res_no_38.status_code, 200)
        db.session.refresh(pref)
        self.assertEqual(pref.body_donation, "NO")

    # -------------------------------------------------------------------------
    # Criterion 4: Medical Treatment Questions Retain Unsure + Educational Explanation
    # -------------------------------------------------------------------------
    @patch("requests.request")
    def test_4_medical_treatment_questions_retain_unsure(self, mock_req):
        """Unsure is preserved on CPR, ventilator, dialysis, chemo, radio, surgery, IV fluids, tube feeding."""
        treatment_questions = [11, 12, 13, 14, 15, 16, 17, 18]
        en_meta = QUESTIONNAIRE_METADATA["en"]
        kn_meta = QUESTIONNAIRE_METADATA["kn"]

        for q in treatment_questions:
            self.assertIn("Unsure", en_meta[q]["options"], f"Q{q} must have Unsure option in English")
            self.assertIn("ಖಚಿತವಿಲ್ಲ", kn_meta[q]["options"], f"Q{q} must have ಖಚಿತವಿಲ್ಲ option in Kannada")

        # Follow-up treatment questions
        self.assertIn("Unsure", FOLLOW_UP_METADATA["en"][33]["options"])  # Chemo follow-up
        self.assertIn("Unsure", FOLLOW_UP_METADATA["en"][34]["options"])  # Radio follow-up
        self.assertIn("Unsure", FOLLOW_UP_METADATA["en"][35]["options"])  # Surgery follow-up

        # Test answering Unsure on all 8 treatments returns their own correct distinct educational explanation
        treatment_keywords = {
            11: ("cpr", "resuscitation"),
            12: ("mechanical ventilation", "ventilator"),
            13: ("dialysis", "kidney"),
            14: ("chemotherapy", "cancer"),
            15: ("radiotherapy", "radiation"),
            16: ("surgery", "surgical"),
            17: ("hydration", "fluids"),
            18: ("nutrition", "feeding")
        }

        for q_num, keywords in treatment_keywords.items():
            exp_en = AIService._get_treatment_explanation(q_num, "en")
            exp_kn = AIService._get_treatment_explanation(q_num, "kn")
            self.assertIn("Educational Information (Unsure)", exp_en)
            self.assertTrue(any(kw in exp_en.lower() for kw in keywords), f"Q{q_num} English explanation should contain {keywords}")
            self.assertTrue(len(exp_kn) > 30, f"Q{q_num} Kannada explanation should be present")

            # CRITICAL BUG TEST: Q12 (Mechanical Ventilation) MUST NOT mention Kidney Dialysis!
            if q_num == 12:
                self.assertNotIn("dialysis", exp_en.lower())
                self.assertNotIn("kidney", exp_en.lower())
                self.assertNotIn("ಡಯಾಲಿಸಿಸ್", exp_kn)
                self.assertNotIn("ಮೂತ್ರಪಿಂಡ", exp_kn)

        # Test answering Unsure on Q12 (Mechanical Ventilation) via chat API
        sess = AISession(session_id="sess_treatment_unsure", patient_id=self.patient_en.patient_id, language="en", current_question=12)
        db.session.add(sess)
        db.session.commit()

        # Without microservice (fallback to local verified explanation)
        mock_req.side_effect = Exception("Microservice offline")

        res = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_treatment_unsure", "message": "Unsure"}),
            headers=self.headers_en
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["status"], "explanation")
        self.assertIn("mechanical ventilation", data.get("message", "").lower())
        self.assertNotIn("kidney", data.get("message", "").lower())
        self.assertNotIn("dialysis", data.get("message", "").lower())

        # Test that selecting Unsure DOES NOT overwrite a previously saved preference
        pref = ACPPreference.query.filter_by(patient_id=self.patient_en.patient_id).first()
        if not pref:
            pref = ACPPreference(patient_id=self.patient_en.patient_id)
            db.session.add(pref)
        pref.ventilator_preference = "WANT"
        db.session.commit()

        AIService._persist_canonical_answer(self.patient_en.patient_id, 12, "Unsure", self.user_en.id)
        db.session.commit()
        db.session.refresh(pref)
        self.assertEqual(pref.ventilator_preference, "WANT")

        # But if previously not specified, setting WANT or DO NOT WANT works
        AIService._persist_canonical_answer(self.patient_en.patient_id, 11, "Yes", self.user_en.id)
        db.session.commit()
        db.session.refresh(pref)
        self.assertEqual(pref.cpr_preference, "WANT")
        # Then sending Unsure keeps it as WANT
        AIService._persist_canonical_answer(self.patient_en.patient_id, 11, "Unsure", self.user_en.id)
        db.session.commit()
        db.session.refresh(pref)
        self.assertEqual(pref.cpr_preference, "WANT")

    # -------------------------------------------------------------------------
    # Criterion 5: Simplify Optional Questions
    # -------------------------------------------------------------------------
    @patch("requests.request")
    def test_5_simplify_optional_questions(self, mock_req):
        """Optional questions Q39, Q40, Q42, Q43 have bracketed text removed and retain Skip option."""
        en_meta = QUESTIONNAIRE_METADATA["en"]
        kn_meta = QUESTIONNAIRE_METADATA["kn"]

        # Exact text checks for English
        self.assertEqual(en_meta[39]["question"], "Do you have any spiritual, cultural, or last rites / funeral wishes?")
        self.assertEqual(en_meta[40]["question"], "What is your permanent residential address?")
        self.assertEqual(en_meta[42]["question"], "Please enter your Government ID number")
        self.assertEqual(en_meta[43]["question"], "What is your Municipality or Gram Panchayat?")

        # Check options for English
        self.assertIn("Skip", en_meta[39]["options"])
        self.assertIn("No specific wishes", en_meta[39]["options"])
        self.assertIn("Skip", en_meta[40]["options"])
        self.assertIn("Same as current address", en_meta[40]["options"])
        self.assertIn("Skip", en_meta[42]["options"])
        self.assertIn("Skip", en_meta[43]["options"])

        # Check Kannada options
        self.assertIn("Skip", kn_meta[39]["options"])
        self.assertIn("Skip", kn_meta[40]["options"])
        self.assertIn("Skip", kn_meta[42]["options"])
        self.assertIn("Skip", kn_meta[43]["options"])

        # Verify no bracketed explanation text in questions
        for q in (39, 40, 42, 43):
            self.assertNotIn("Optional", en_meta[q]["question"])
            self.assertNotIn("(", en_meta[q]["question"])
            self.assertNotIn(")", en_meta[q]["question"])

        # Test selecting "Skip"
        sess = AISession(session_id="sess_optional_skip", patient_id=self.patient_en.patient_id, language="en", current_question=39)
        db.session.add(sess)
        db.session.commit()

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "saved", "message": "Answer recorded."}
        mock_req.return_value = mock_resp

        # Answering Skip for Q39
        res39 = self.client.post("/api/ai/chat", data=json.dumps({"session_id": "sess_optional_skip", "message": "Skip"}), headers=self.headers_en)
        self.assertEqual(res39.status_code, 200)
        self.assertEqual(json.loads(res39.data)["status"], "saved")

        # Answering "Same as current address" for Q40
        self.patient_en.current_address = "42 MG Road, Bengaluru"
        db.session.commit()
        res40 = self.client.post("/api/ai/chat", data=json.dumps({"session_id": "sess_optional_skip", "message": "Same as current address"}), headers=self.headers_en)
        self.assertEqual(res40.status_code, 200)
        db.session.refresh(self.patient_en)
        self.assertEqual(self.patient_en.permanent_address, "42 MG Road, Bengaluru")

    # -------------------------------------------------------------------------
    # Criterion 6: Correct DB Persistence to Canonical Fields
    # -------------------------------------------------------------------------
    def test_6_canonical_db_persistence_across_all_fields(self):
        """All answers persist into correct Patient and ACPPreference columns."""
        pid = self.patient_en.patient_id
        uid = self.user_en.id

        AIService._persist_canonical_answer(pid, 7, "Hypertension", uid)
        AIService._persist_canonical_answer(pid, 8, "Heart surgery 2020", uid)
        AIService._persist_canonical_answer(pid, 9, "Aspirin, Atorvastatin", uid)
        AIService._persist_canonical_answer(pid, 10, "Sulfa drugs", uid)
        AIService._persist_canonical_answer(pid, 37, "Yes", uid)
        AIService._persist_canonical_answer(pid, 38, "No", uid)
        AIService._persist_canonical_answer(pid, 39, "Traditional Hindu rituals", uid)
        AIService._persist_canonical_answer(pid, 40, "100 Indiranagar, Bengaluru", uid)
        AIService._persist_canonical_answer(pid, 42, "1234-5678-9012", uid)
        AIService._persist_canonical_answer(pid, 43, "BBMP East", uid)
        db.session.commit()

        db.session.refresh(self.patient_en)
        pref = ACPPreference.query.filter_by(patient_id=pid).first()

        self.assertEqual(self.patient_en.chronic_conditions, "Hypertension")
        self.assertEqual(self.patient_en.serious_hospitalization, "Heart surgery 2020")
        self.assertEqual(self.patient_en.long_term_medications, "Aspirin, Atorvastatin")
        self.assertEqual(self.patient_en.allergies, "Sulfa drugs")
        self.assertEqual(pref.organ_donation, "YES")
        self.assertEqual(pref.body_donation, "NO")
        self.assertEqual(pref.last_rites, "Traditional Hindu rituals")
        self.assertEqual(self.patient_en.permanent_address, "100 Indiranagar, Bengaluru")
        self.assertEqual(self.patient_en.government_id_number, "1234-5678-9012")
        self.assertEqual(self.patient_en.municipality_panchayat, "BBMP East")

    # -------------------------------------------------------------------------
    # Criterion 7: Final ACP Summary Reflects Answers Correctly
    # -------------------------------------------------------------------------
    def test_7_final_acp_summary_reflects_answers_correctly(self):
        """Dashboard synthesis and dossier summary reflect all cleaned questions and answers."""
        pid = self.patient_en.patient_id
        uid = self.user_en.id

        AIService._persist_canonical_answer(pid, 7, "Asthma", uid)
        AIService._persist_canonical_answer(pid, 8, "None", uid)
        AIService._persist_canonical_answer(pid, 9, "Inhaler", uid)
        AIService._persist_canonical_answer(pid, 10, "Pollen", uid)
        AIService._persist_canonical_answer(pid, 37, "Yes", uid)
        AIService._persist_canonical_answer(pid, 38, "Yes", uid)
        AIService._persist_canonical_answer(pid, 39, "No specific wishes", uid)
        db.session.commit()

        summary = AIService._synthesize_dashboard_from_db(pid)
        self.assertEqual(summary["medical_background"]["chronic_conditions"], "Asthma")
        self.assertEqual(summary["medical_background"]["serious_hospitalization"], "None")
        self.assertEqual(summary["medical_background"]["long_term_medications"], "Inhaler")
        self.assertEqual(summary["medical_background"]["allergies"], "Pollen")
        self.assertEqual(summary["treatment_preferences"]["organ_donation"], "Yes")
        self.assertEqual(summary["treatment_preferences"]["body_donation"], "Yes")
        self.assertEqual(summary["treatment_preferences"]["last_rites"], "No specific wishes")

        # Verify via Doctor API dossier endpoint
        res = self.client.get(f"/api/doctor/patient/{pid}", headers=self.headers_doc)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["patient"]["chronic_conditions"], "Asthma")
        self.assertEqual(data["patient"]["allergies"], "Pollen")
        self.assertEqual(data["acp_preferences"]["organ_donation"], "YES")
        self.assertEqual(data["acp_preferences"]["body_donation"], "YES")

    # -------------------------------------------------------------------------
    # Criterion 8: Existing Patient Records Preservation
    # -------------------------------------------------------------------------
    def test_8_existing_patient_records_preserved(self):
        """Existing patient records, authentication, and completion status remain intact."""
        # Query existing patients
        pat_en = Patient.query.filter_by(patient_id=self.patient_en.patient_id).first()
        self.assertIsNotNone(pat_en)
        self.assertEqual(pat_en.user.email, "cleanup_pat_en@test.com")
        self.assertEqual(pat_en.preferred_language, "English")

        pat_kn = Patient.query.filter_by(patient_id=self.patient_kn.patient_id).first()
        self.assertIsNotNone(pat_kn)
        self.assertEqual(pat_kn.user.email, "cleanup_pat_kn@test.com")
        self.assertEqual(pat_kn.preferred_language, "Kannada")

        # Verify doctor permissions intact
        res = self.client.get("/api/doctor/patients", headers=self.headers_doc)
        self.assertEqual(res.status_code, 200)

    # -------------------------------------------------------------------------
    # Criterion 9: Representative Questions Cleanup & Validation (Q29, Q30, Q35, Q36)
    # -------------------------------------------------------------------------
    @patch("requests.request")
    def test_9_representative_questions_cleanup_and_validation(self, mock_req):
        """Primary and Alternate Representative email and address questions are simplified, Skip removed, email validated."""
        en_meta = QUESTIONNAIRE_METADATA["en"]
        kn_meta = QUESTIONNAIRE_METADATA["kn"]

        # 1. Exact question wording (no brackets, no 'Optional', no 'Skip')
        self.assertEqual(en_meta[29]["question"], "What is your primary representative's email address?")
        self.assertEqual(en_meta[30]["question"], "What is your primary representative's residential address?")
        self.assertEqual(en_meta[35]["question"], "What is your alternate representative's email address?")
        self.assertEqual(en_meta[36]["question"], "What is your alternate representative's residential address?")

        self.assertNotIn("Optional", en_meta[29]["question"])
        self.assertNotIn("Skip", en_meta[29]["question"])
        self.assertNotIn("(", en_meta[29]["question"])
        self.assertNotIn(")", en_meta[29]["question"])

        self.assertNotIn("Optional", en_meta[30]["question"])
        self.assertNotIn("Skip", en_meta[30]["question"])
        self.assertNotIn("(", en_meta[30]["question"])
        self.assertNotIn(")", en_meta[30]["question"])

        self.assertNotIn("Optional", en_meta[35]["question"])
        self.assertNotIn("Skip", en_meta[35]["question"])
        self.assertNotIn("(", en_meta[35]["question"])
        self.assertNotIn(")", en_meta[35]["question"])

        self.assertNotIn("Optional", en_meta[36]["question"])
        self.assertNotIn("Skip", en_meta[36]["question"])
        self.assertNotIn("(", en_meta[36]["question"])
        self.assertNotIn(")", en_meta[36]["question"])

        # 2. Options configuration
        self.assertIsNone(en_meta[29]["options"])
        self.assertEqual(en_meta[30]["options"], ["Same as my address"])
        self.assertIsNone(en_meta[35]["options"])
        self.assertEqual(en_meta[36]["options"], ["Same as my address"])

        self.assertIsNone(kn_meta[29]["options"])
        self.assertEqual(kn_meta[30]["options"], ["ನನ್ನ ವಿಳಾಸದಂತೆಯೇ"])
        self.assertIsNone(kn_meta[35]["options"])
        self.assertEqual(kn_meta[36]["options"], ["ನನ್ನ ವಿಳಾಸದಂತೆಯೇ"])

        # 3. Test Q29 email validation via chat API
        sess = AISession(session_id="sess_rep_validation", patient_id=self.patient_en.patient_id, language="en", current_question=29)
        db.session.add(sess)
        db.session.commit()

        # Reject "Skip"
        res_skip = self.client.post("/api/ai/chat", data=json.dumps({"session_id": "sess_rep_validation", "message": "Skip"}), headers=self.headers_en)
        self.assertEqual(res_skip.status_code, 200)
        self.assertEqual(json.loads(res_skip.data)["status"], "invalid")

        # Reject invalid email format
        res_invalid = self.client.post("/api/ai/chat", data=json.dumps({"session_id": "sess_rep_validation", "message": "notanemail"}), headers=self.headers_en)
        self.assertEqual(res_invalid.status_code, 200)
        self.assertEqual(json.loads(res_invalid.data)["status"], "invalid")

        # Accept valid email format
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "saved", "message": "Answer recorded."}
        mock_req.return_value = mock_resp

        res_valid = self.client.post("/api/ai/chat", data=json.dumps({"session_id": "sess_rep_validation", "message": "rep@family.org"}), headers=self.headers_en)
        self.assertEqual(res_valid.status_code, 200)
        self.assertEqual(json.loads(res_valid.data)["status"], "saved")

        dhr1 = DHR.query.filter_by(patient_id=self.patient_en.patient_id, preference_order=1).first()
        self.assertIsNotNone(dhr1)
        self.assertEqual(dhr1.email_primary, "rep@family.org")

        # 4. Test Q30 address validation via chat API
        db.session.refresh(sess)
        self.assertEqual(sess.current_question, 30)

        # Reject "Skip"
        res_skip_30 = self.client.post("/api/ai/chat", data=json.dumps({"session_id": "sess_rep_validation", "message": "Skip"}), headers=self.headers_en)
        self.assertEqual(res_skip_30.status_code, 200)
        self.assertEqual(json.loads(res_skip_30.data)["status"], "invalid")

        # Accept "Same as my address"
        self.patient_en.current_address = "42 Residency Road, Bengaluru"
        db.session.commit()

        res_same_30 = self.client.post("/api/ai/chat", data=json.dumps({"session_id": "sess_rep_validation", "message": "Same as my address"}), headers=self.headers_en)
        self.assertEqual(res_same_30.status_code, 200)
        self.assertEqual(json.loads(res_same_30.data)["status"], "saved")
        db.session.refresh(dhr1)
        self.assertEqual(dhr1.permanent_address, "42 Residency Road, Bengaluru")

        # 5. Test Q35 and Q36 with alternate representative
        pref = ACPPreference(patient_id=self.patient_en.patient_id, alternate_dhr_appointed=True)
        db.session.add(pref)
        sess.current_question = 35
        db.session.commit()

        # Q35 rejects "Skip"
        res_skip_35 = self.client.post("/api/ai/chat", data=json.dumps({"session_id": "sess_rep_validation", "message": "Skip"}), headers=self.headers_en)
        self.assertEqual(res_skip_35.status_code, 200)
        self.assertEqual(json.loads(res_skip_35.data)["status"], "invalid")

        # Q35 accepts valid email
        res_valid_35 = self.client.post("/api/ai/chat", data=json.dumps({"session_id": "sess_rep_validation", "message": "altrep@family.org"}), headers=self.headers_en)
        self.assertEqual(res_valid_35.status_code, 200)
        self.assertEqual(json.loads(res_valid_35.data)["status"], "saved")
        dhr2 = DHR.query.filter_by(patient_id=self.patient_en.patient_id, preference_order=2).first()
        self.assertIsNotNone(dhr2)
        self.assertEqual(dhr2.email_primary, "altrep@family.org")

        # Q36 rejects "Skip"
        db.session.refresh(sess)
        self.assertEqual(sess.current_question, 36)
        res_skip_36 = self.client.post("/api/ai/chat", data=json.dumps({"session_id": "sess_rep_validation", "message": "Skip"}), headers=self.headers_en)
        self.assertEqual(res_skip_36.status_code, 200)
        self.assertEqual(json.loads(res_skip_36.data)["status"], "invalid")

        # Q36 accepts "Same as my address"
        res_same_36 = self.client.post("/api/ai/chat", data=json.dumps({"session_id": "sess_rep_validation", "message": "Same as my address"}), headers=self.headers_en)
        self.assertEqual(res_same_36.status_code, 200)
        self.assertEqual(json.loads(res_same_36.data)["status"], "saved")
        db.session.refresh(dhr2)
        self.assertEqual(dhr2.permanent_address, "42 Residency Road, Bengaluru")

    # -------------------------------------------------------------------------
    # Criterion 10: Multilingual Choice Input Recognition (Kannada & English)
    # -------------------------------------------------------------------------
    @patch("requests.request")
    def test_10_multilingual_choice_recognition(self, mock_req):
        """Verify both English and Kannada answers are accepted and normalized to canonical DB values across languages."""
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "saved", "message": "Answer recorded."}
        mock_req.return_value = mock_resp

        # 1. Kannada session + typed English answer ("Female" for Q3 Gender)
        sess_kn = AISession(
            patient_id=self.patient_kn.patient_id,
            session_id="sess_multi_kn",
            language="kn",
            current_question=3
        )
        db.session.add(sess_kn)
        db.session.commit()

        res_kn_typed_en = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_multi_kn", "message": "Female"}),
            headers=self.headers_kn
        )
        self.assertEqual(res_kn_typed_en.status_code, 200)
        data_kn_en = json.loads(res_kn_typed_en.data)
        self.assertEqual(data_kn_en["status"], "saved")
        db.session.refresh(self.patient_kn)
        self.assertEqual(self.patient_kn.gender, "Female")

        # 2. Kannada session + typed Kannada answer ("ಮಹಿಳೆ" for Q3 Gender)
        sess_kn.current_question = 3
        db.session.commit()

        res_kn_typed_kn = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_multi_kn", "message": "ಮಹಿಳೆ"}),
            headers=self.headers_kn
        )
        self.assertEqual(res_kn_typed_kn.status_code, 200)
        data_kn_kn = json.loads(res_kn_typed_kn.data)
        self.assertEqual(data_kn_kn["status"], "saved")
        db.session.refresh(self.patient_kn)
        self.assertEqual(self.patient_kn.gender, "Female")

        # 3. English session + typed English answer ("Female" for Q3 Gender)
        sess_en = AISession(
            patient_id=self.patient_en.patient_id,
            session_id="sess_multi_en",
            language="en",
            current_question=3
        )
        db.session.add(sess_en)
        db.session.commit()

        res_en_typed_en = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_multi_en", "message": "Female"}),
            headers=self.headers_en
        )
        self.assertEqual(res_en_typed_en.status_code, 200)
        data_en_en = json.loads(res_en_typed_en.data)
        self.assertEqual(data_en_en["status"], "saved")
        db.session.refresh(self.patient_en)
        self.assertEqual(self.patient_en.gender, "Female")

        # 4. English session + supported Kannada answer ("ಪುರುಷ" -> Male)
        sess_en.current_question = 3
        db.session.commit()

        res_en_typed_kn = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_multi_en", "message": "ಪುರುಷ"}),
            headers=self.headers_en
        )
        self.assertEqual(res_en_typed_kn.status_code, 200)
        data_en_kn = json.loads(res_en_typed_kn.data)
        self.assertEqual(data_en_kn["status"], "saved")
        db.session.refresh(self.patient_en)
        self.assertEqual(self.patient_en.gender, "Male")

        # 5. Reject unrelated or ambiguous input on choice question
        sess_kn.current_question = 3
        db.session.commit()

        res_invalid_banana = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_multi_kn", "message": "banana"}),
            headers=self.headers_kn
        )
        self.assertEqual(res_invalid_banana.status_code, 200)
        self.assertEqual(json.loads(res_invalid_banana.data)["status"], "invalid")

        res_invalid_yes_on_gender = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_multi_kn", "message": "Yes"}),
            headers=self.headers_kn
        )
        self.assertEqual(res_invalid_yes_on_gender.status_code, 200)
        self.assertEqual(json.loads(res_invalid_yes_on_gender.data)["status"], "invalid")

        # 6. Treatments Q11 (CPR) & Q12 (Ventilator) in Kannada interface
        pref_kn = ACPPreference(patient_id=self.patient_kn.patient_id)
        db.session.add(pref_kn)
        sess_kn.current_question = 11
        db.session.commit()

        # Typed English "Yes" on CPR in Kannada session
        res_cpr_en = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_multi_kn", "message": "Yes"}),
            headers=self.headers_kn
        )
        self.assertEqual(res_cpr_en.status_code, 200)
        self.assertEqual(json.loads(res_cpr_en.data)["status"], "saved")
        db.session.refresh(pref_kn)
        self.assertEqual(pref_kn.cpr_preference, "WANT")

        # Typed Kannada "ಇಲ್ಲ" (No) on Ventilator (Q12) in Kannada session
        sess_kn.current_question = 12
        db.session.commit()

        res_vent_kn = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_multi_kn", "message": "ಇಲ್ಲ"}),
            headers=self.headers_kn
        )
        self.assertEqual(res_vent_kn.status_code, 200)
        self.assertEqual(json.loads(res_vent_kn.data)["status"], "saved")
        db.session.refresh(pref_kn)
        self.assertEqual(pref_kn.ventilator_preference, "DO NOT WANT")

        # 7. Preferred place of care Q20 in Kannada interface
        sess_kn.current_question = 20
        db.session.commit()

        # Typed English "Home" in Kannada session
        res_place_home = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_multi_kn", "message": "Home"}),
            headers=self.headers_kn
        )
        self.assertEqual(res_place_home.status_code, 200)
        self.assertEqual(json.loads(res_place_home.data)["status"], "saved")
        db.session.refresh(pref_kn)
        self.assertEqual(pref_kn.preferred_place_of_care, "Home")

        # Typed Kannada "ಆಸ್ಪತ್ರೆ" in Kannada session
        sess_kn.current_question = 20
        db.session.commit()

        res_place_hosp = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_multi_kn", "message": "ಆಸ್ಪತ್ರೆ"}),
            headers=self.headers_kn
        )
        self.assertEqual(res_place_hosp.status_code, 200)
        self.assertEqual(json.loads(res_place_hosp.data)["status"], "saved")
        db.session.refresh(pref_kn)
        self.assertEqual(pref_kn.preferred_place_of_care, "Hospital")

        # 8. Organ Donation Q37 (Yes/No only)
        sess_kn.current_question = 37
        db.session.commit()

        # Typed English "Yes"
        res_organ_yes = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_multi_kn", "message": "Yes"}),
            headers=self.headers_kn
        )
        self.assertEqual(res_organ_yes.status_code, 200)
        self.assertEqual(json.loads(res_organ_yes.data)["status"], "saved")
        db.session.refresh(pref_kn)
        self.assertEqual(pref_kn.organ_donation, "YES")

        # Typed Kannada "ಇಲ್ಲ" (No)
        sess_kn.current_question = 37
        db.session.commit()

        res_organ_no = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_multi_kn", "message": "ಇಲ್ಲ"}),
            headers=self.headers_kn
        )
        self.assertEqual(res_organ_no.status_code, 200)
        self.assertEqual(json.loads(res_organ_no.data)["status"], "saved")
        db.session.refresh(pref_kn)
        self.assertEqual(pref_kn.organ_donation, "NO")

        # Reject "Unsure" on Q37
        res_organ_unsure = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_multi_kn", "message": "Unsure"}),
            headers=self.headers_kn
        )
        self.assertEqual(res_organ_unsure.status_code, 200)
        self.assertEqual(json.loads(res_organ_unsure.data)["status"], "invalid")

        # 9. Verify canonical English values are preserved and render in review summary
        summary_kn = AIService._generate_review_summary(self.patient_kn.patient_id, language="kn")
        self.assertIn("ಲಿಂಗ: Female", summary_kn)
        self.assertIn("CPR (ಹೃದಯ ಬಡಿತ ಪುನರಾರಂಭ): ಹೌದು / ಬಯಸುತ್ತೇನೆ (WANT)", summary_kn)
        self.assertIn("ಮೆಕ್ಯಾನಿಕಲ್ ವೆಂಟಿಲೇಟರ್: ಇಲ್ಲ / ಬೇಡ (DO NOT WANT)", summary_kn)

        summary_en = AIService._generate_review_summary(self.patient_kn.patient_id, language="en")
        self.assertIn("Gender: Female", summary_en)
        self.assertIn("CPR (Cardiopulmonary Resuscitation): Yes (WANT)", summary_en)
        self.assertIn("Mechanical Ventilation: No (DO NOT WANT)", summary_en)
        self.assertIn("Preferred Place of Care: Hospital", summary_en)
        self.assertIn("Organ Donation: No", summary_en)


if __name__ == "__main__":
    unittest.main()
