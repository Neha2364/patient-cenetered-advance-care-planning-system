import os
import unittest
import json
from datetime import date
from unittest.mock import patch
from backend.app import create_app
from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.acp_preference import ACPPreference
from backend.models.dhr import DHR
from backend.models.ai_session import AISession
from backend.models.chat_history import ChatHistory
from backend.utils.auth_helpers import generate_token

class ACPTestCase(unittest.TestCase):
    """Test suite for Patient-Centered Advance Care Planning REST APIs."""

    def setUp(self):
        """Set up testing context and initialize schema tables."""
        # Use database configured in environment (typically a separate test PostgreSQL instance)
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['ENV'] = 'testing'
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Clean up existing test data for test isolation
        try:
            for test_email in ["patient@test.com", "doctor@test.com", "admin@test.com"]:
                u = User.query.filter_by(email=test_email).first()
                if u:
                    db.session.delete(u)
            db.session.commit()
        except Exception:
            db.session.rollback()

        # Add seed users
        self.seed_users()

    def tearDown(self):
        """Clean up databases and pop testing context."""
        try:
            for test_email in ["patient@test.com", "doctor@test.com", "admin@test.com"]:
                u = User.query.filter_by(email=test_email).first()
                if u:
                    db.session.delete(u)
            db.session.commit()
        except Exception:
            db.session.rollback()
        db.session.remove()
        self.app_context.pop()

    def seed_users(self):
        """Populate base roles for JWT token generation."""
        self.p_user = User(full_name="Rajesh Kumar", email="patient@test.com", role="patient")
        self.d_user = User(full_name="Dr. Aradhana Gowda", email="doctor@test.com", role="doctor")
        self.a_user = User(full_name="System Administrator", email="admin@test.com", role="admin")
        db.session.add_all([self.p_user, self.d_user, self.a_user])
        db.session.commit()

        # Generate tokens
        self.patient_token = generate_token(self.p_user.id, self.p_user.email, self.p_user.role)
        self.doctor_token = generate_token(self.d_user.id, self.d_user.email, self.d_user.role)
        self.admin_token = generate_token(self.a_user.id, self.a_user.email, self.a_user.role)

        self.patient_headers = {'Authorization': f'Bearer {self.patient_token}'}
        self.doctor_headers = {'Authorization': f'Bearer {self.doctor_token}'}
        self.admin_headers = {'Authorization': f'Bearer {self.admin_token}'}

    def test_patient_registration_flow(self):
        """Verify patient CRUD APIs."""
        payload = {
            "user_id": self.p_user.id,
            "age": 68,
            "gender": "Male",
            "date_of_birth": "1958-04-15",
            "phone": "+919876543210",
            "address": "Bangalore, Karnataka",
            "preferred_language": "English",
            "government_id_type": "Aadhaar",
            "government_id_number": "1234-5678-9012"
        }

        # 1. POST /patients (Create)
        response = self.client.post(
            '/api/patients',
            data=json.dumps(payload),
            content_type='application/json',
            headers=self.patient_headers
        )
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['phone'], "+919876543210")
        patient_id = data['patient_id']

        # 2. GET /patients/{id} (Read)
        response = self.client.get(
            f'/api/patients/{patient_id}',
            headers=self.patient_headers
        )
        self.assertEqual(response.status_code, 200)

        # 3. PUT /patients/{id} (Update)
        update_payload = {"phone": "+919876543222"}
        response = self.client.put(
            f'/api/patients/{patient_id}',
            data=json.dumps(update_payload),
            content_type='application/json',
            headers=self.patient_headers
        )
        self.assertEqual(response.status_code, 200)
        updated_data = json.loads(response.data)
        self.assertEqual(updated_data['phone'], "+919876543222")

    def test_dhr_appointment_and_acp_preferences(self):
        """Verify DHR registration and ACP preference webhook integrations."""
        # Setup patient first
        pat = Patient(
            user_id=self.p_user.id,
            phone="+919876543210",
            preferred_language="English"
        )
        db.session.add(pat)
        db.session.commit()
        pid = pat.patient_id

        # 1. POST /dhr (Appoint DHR)
        dhr_payload = {
            "patient_id": pid,
            "full_name": "Sunita Kumar",
            "relationship": "Spouse",
            "date_of_birth": "1962-08-20",
            "government_id_type": "Aadhaar",
            "government_id_number": "9876-5432-1098",
            "mobile_primary": "+919876543211",
            "email_primary": "sunita@test.com"
        }
        res = self.client.post(
            '/api/dhr',
            data=json.dumps(dhr_payload),
            content_type='application/json',
            headers=self.patient_headers
        )
        self.assertEqual(res.status_code, 201)

        # 2. POST /chat/process (AI integration)
        chat_payload = {
            "patient_id": pid,
            "cpr": "No",
            "ventilator": "Yes",
            "dialysis": "No",
            "pain_management": "Comfort Care",
            "preferred_place": "Home"
        }
        res = self.client.post(
            '/api/chat/process',
            data=json.dumps(chat_payload),
            content_type='application/json',
            headers=self.patient_headers
        )
        self.assertEqual(res.status_code, 200)

        # Retrieve preferences to verify mappings
        res = self.client.get(f'/api/acp/{pid}', headers=self.patient_headers)
        self.assertEqual(res.status_code, 200)
        acp_data = json.loads(res.data)
        self.assertEqual(acp_data['cpr_preference'], 'DO NOT WANT')
        self.assertEqual(acp_data['ventilator_preference'], 'WANT')

    @patch('backend.services.storage_service.StorageService.upload_pdf')
    def test_amd_pdf_generation_flow(self, mock_upload):
        """Verify AMD PDF rendering and Supabase upload pipelines."""
        # Arrange mock response
        mock_upload.return_value = {
            'success': True,
            'pdf_name': 'test.pdf',
            'pdf_url': 'https://mock.supabase.co/test.pdf',
            'storage_bucket': 'amd-documents',
            'storage_path': 'patient_1/v1/test.pdf'
        }

        # Setup Patient, Preferences, and DHR
        pat = Patient(user_id=self.p_user.id, phone="+919876543210", preferred_language="English")
        db.session.add(pat)
        db.session.commit()
        pid = pat.patient_id

        acp = ACPPreference(
            patient_id=pid,
            cpr_preference="DO NOT WANT",
            ventilator_preference="DO NOT WANT",
            dialysis_preference="DO NOT WANT",
            is_completed=True
        )
        dhr = DHR(
            patient_id=pid,
            full_name="Sunita Kumar",
            relationship="Spouse",
            mobile_primary="+919876543211",
            email_primary="sunita@test.com"
        )
        db.session.add_all([acp, dhr])
        db.session.commit()

        # POST /amd/generate
        gen_payload = {
            "patient_id": pid,
            "executor_place": "Bangalore",
            "notary_name": "Mr. Notary",
            "notary_place": "Bangalore",
            "witnesses": [
                {
                    "name": "Jane Witness",
                    "email": "jane@test.com",
                    "mobile": "+919876543299"
                },
                {
                    "name": "Bob Witness",
                    "email": "bob@test.com",
                    "mobile": "+919876543298"
                }
            ]
        }

        res = self.client.post(
            '/api/amd/generate',
            data=json.dumps(gen_payload),
            content_type='application/json',
            headers=self.patient_headers
        )
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertEqual(data['status'], 'Active')
        self.assertEqual(data['pdf_url'], 'https://mock.supabase.co/test.pdf')

    def test_ai_session_language_toggle(self):
        """Verify seamless language toggle without loss of active session or state."""
        pat = Patient(user_id=self.p_user.id, phone="+919876543210", preferred_language="English")
        db.session.add(pat)
        db.session.commit()

        session = AISession(
            session_id="test-session-toggle-1",
            patient_id=pat.patient_id,
            language="en",
            current_question=21
        )
        db.session.add(session)
        db.session.commit()

        # Switch to Kannada
        res = self.client.post(
            '/api/ai/session/language',
            data=json.dumps({"session_id": session.session_id, "language": "kn"}),
            content_type='application/json',
            headers=self.patient_headers
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['language'], 'kn')
        self.assertEqual(data['current_question'], 21)
        self.assertIsNotNone(data['question'])

        # Verify patient record updated
        db.session.refresh(pat)
        self.assertEqual(pat.preferred_language, 'Kannada')

        # Switch back to English
        res = self.client.post(
            '/api/ai/session/language',
            data=json.dumps({"session_id": session.session_id, "language": "en"}),
            content_type='application/json',
            headers=self.patient_headers
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['language'], 'en')
        db.session.refresh(pat)
        self.assertEqual(pat.preferred_language, 'English')

    def test_ai_follow_up_chat_and_educational_unsure(self):
        """Verify follow-up conversational answers, validations, and Unsure educational explanation."""
        pat = Patient(user_id=self.p_user.id, preferred_language="English")
        db.session.add(pat)
        db.session.commit()

        dhr = DHR(
            patient_id=pat.patient_id,
            full_name="Ananya Kumar",
            relationship="Daughter",
            mobile_primary="Pending",
            email_primary="pending@example.com",
            preference_order=1
        )
        db.session.add(dhr)
        db.session.commit()

        session = AISession(
            session_id="test-session-followup-1",
            patient_id=pat.patient_id,
            language="en",
            current_question=21
        )
        db.session.add(session)
        db.session.commit()

        # 1. Answer Q21 (Primary DHR phone)
        res = self.client.post(
            '/api/ai/chat',
            data=json.dumps({"session_id": session.session_id, "message": "+919876543299"}),
            content_type='application/json',
            headers=self.patient_headers
        )
        self.assertEqual(res.status_code, 200)
        db.session.refresh(dhr)
        self.assertEqual(dhr.mobile_primary, "+919876543299")

        # 2. Answer Q22 with invalid email
        session.current_question = 22
        db.session.commit()
        res = self.client.post(
            '/api/ai/chat',
            data=json.dumps({"session_id": session.session_id, "message": "invalidemail"}),
            content_type='application/json',
            headers=self.patient_headers
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['status'], 'invalid')

        # 3. Answer Q22 with valid email
        res = self.client.post(
            '/api/ai/chat',
            data=json.dumps({"session_id": session.session_id, "message": "ananya@example.com"}),
            content_type='application/json',
            headers=self.patient_headers
        )
        self.assertEqual(res.status_code, 200)
        db.session.refresh(dhr)
        self.assertEqual(dhr.email_primary, "ananya@example.com")

        # 4. Answer Q30 (Body donation) with Unsure
        session.current_question = 30
        db.session.commit()
        res = self.client.post(
            '/api/ai/chat',
            data=json.dumps({"session_id": session.session_id, "message": "Unsure"}),
            content_type='application/json',
            headers=self.patient_headers
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['status'], 'explanation')
        self.assertIn("Body donation", data['message'])

        # Verify body donation was NOT silently committed to Yes or No
        pref = ACPPreference.query.filter_by(patient_id=pat.patient_id).first()
        if pref:
            self.assertNotEqual(pref.body_donation, 'YES')
            self.assertNotEqual(pref.body_donation, 'NO')

    def test_ai_confirm_review_workflow(self):
        """Verify explicit Confirmation & Review, required fields validation, and dashboard completion status."""
        pat = Patient(user_id=self.p_user.id, preferred_language="English")
        db.session.add(pat)
        db.session.commit()

        session = AISession(
            session_id="test-session-review-1",
            patient_id=pat.patient_id,
            language="en",
            current_question=33
        )
        db.session.add(session)
        db.session.commit()

        # 1. Attempt review confirmation with missing contact fields -> Should fail with 400
        res = self.client.post(
            '/api/ai/confirm-review',
            data=json.dumps({"session_id": session.session_id}),
            content_type='application/json',
            headers=self.patient_headers
        )
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.data)
        self.assertIn("missing", data['message'].lower())

        # 2. Populate required patient & DHR contact fields
        pat.phone = "+919876543210"
        pat.address = "123 MG Road, Bangalore"
        dhr = DHR(
            patient_id=pat.patient_id,
            full_name="Meera Kumar",
            relationship="Spouse",
            mobile_primary="+919876543222",
            email_primary="meera@example.com",
            preference_order=1
        )
        db.session.add(dhr)
        db.session.commit()

        # 3. Confirm review -> Should succeed
        res = self.client.post(
            '/api/ai/confirm-review',
            data=json.dumps({"session_id": session.session_id}),
            content_type='application/json',
            headers=self.patient_headers
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data['is_completed'])

        # Verify DB records
        pref = ACPPreference.query.filter_by(patient_id=pat.patient_id).first()
        self.assertIsNotNone(pref)
        self.assertTrue(pref.is_completed)
        self.assertIsNotNone(pref.completed_at)
        self.assertEqual(pref.review_status, "Pending Review")

        # Verify Doctor patients list reflects completed status
        doc_res = self.client.get('/api/doctor/patients', headers=self.doctor_headers)
        self.assertEqual(doc_res.status_code, 200)
        patients_list = json.loads(doc_res.data)
        matched = next((p for p in patients_list if p['patient_id'] == pat.patient_id), None)
        self.assertIsNotNone(matched)
        self.assertTrue(matched['is_completed'])

if __name__ == '__main__':
    unittest.main()
