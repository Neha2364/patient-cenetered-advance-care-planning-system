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

        # Re-create database tables
        db.create_all()
        
        # Clean up existing data for test isolation
        try:
            db.session.execute(db.text("TRUNCATE TABLE audit_logs, generated_amds, dhrs, acp_preferences, patients, users CASCADE;"))
            db.session.commit()
        except Exception:
            db.session.rollback()

        # Add seed users
        self.seed_users()

    def tearDown(self):
        """Clean up databases and pop testing context."""
        db.session.remove()
        db.drop_all()
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

if __name__ == '__main__':
    unittest.main()
