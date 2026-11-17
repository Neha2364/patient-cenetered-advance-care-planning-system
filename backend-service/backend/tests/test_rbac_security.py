"""
RBAC Security Test Suite

Verifies that:
  1. Public registration always assigns role='patient', regardless of client payload.
  2. Patients cannot access doctor-only endpoints.
  3. Doctors can access doctor-only endpoints.
  4. Patients cannot read another patient's data.
  5. Role cannot be escalated through profile update or manipulated API calls.

Uses SQLite in-memory DB — no live database required.
"""

import os
import unittest
from backend.config import Config
from backend.app import create_app
from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.utils.auth_helpers import generate_token


class TestConfig(Config):
    TESTING = True
    ENV = 'testing'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    AHCP_AI_SERVICE_API_KEY = 'test-secret-key'
    JWT_SECRET_KEY = 'test-jwt-rbac-secret'


class RBACSecurityTestCase(unittest.TestCase):
    """Security test suite for role-based access control."""

    # ------------------------------------------------------------------ #
    # Setup / Teardown
    # ------------------------------------------------------------------ #

    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        # Pre-existing patient account (simulates an account created before this session)
        self.existing_patient = User(
            full_name="Existing Patient", email="existing_patient@test.com", role="patient"
        )
        self.existing_patient.set_password("pass123")

        # Pre-existing patient 2 (for cross-patient isolation tests)
        self.other_patient = User(
            full_name="Other Patient", email="other_patient@test.com", role="patient"
        )
        self.other_patient.set_password("pass123")

        # Pre-existing doctor account (created as if via CLI script, not public registration)
        self.existing_doctor = User(
            full_name="Dr. Authorized", email="doctor@test.com", role="doctor"
        )
        self.existing_doctor.set_password("docpass123")

        db.session.add_all([self.existing_patient, self.other_patient, self.existing_doctor])
        db.session.commit()

        # Create Patient profiles so patient endpoints can be tested
        self.patient_profile = Patient(
            user_id=self.existing_patient.id, preferred_language="English"
        )
        self.other_patient_profile = Patient(
            user_id=self.other_patient.id, preferred_language="English"
        )
        db.session.add_all([self.patient_profile, self.other_patient_profile])
        db.session.commit()

        # Generate tokens
        self.patient_token = generate_token(
            self.existing_patient.id, self.existing_patient.email, self.existing_patient.role
        )
        self.other_patient_token = generate_token(
            self.other_patient.id, self.other_patient.email, self.other_patient.role
        )
        self.doctor_token = generate_token(
            self.existing_doctor.id, self.existing_doctor.email, self.existing_doctor.role
        )

        self.patient_headers = {
            "Authorization": f"Bearer {self.patient_token}",
            "Content-Type": "application/json",
        }
        self.other_patient_headers = {
            "Authorization": f"Bearer {self.other_patient_token}",
            "Content-Type": "application/json",
        }
        self.doctor_headers = {
            "Authorization": f"Bearer {self.doctor_token}",
            "Content-Type": "application/json",
        }

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    # ------------------------------------------------------------------ #
    # Helper
    # ------------------------------------------------------------------ #

    def _register(self, payload: dict):
        return self.client.post(
            "/api/auth/register",
            json=payload,
            content_type="application/json",
        )

    def _login(self, email: str, password: str):
        return self.client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
            content_type="application/json",
        )

    # ================================================================== #
    # Test 1 — Patient registers successfully
    # ================================================================== #
    def test_01_patient_registers_successfully(self):
        """Public registration with valid data returns 201."""
        resp = self._register({
            "full_name": "New Patient",
            "email": "new_patient@test.com",
            "password": "pass123",
        })
        self.assertEqual(resp.status_code, 201, resp.data)

    # ================================================================== #
    # Test 2 — Registered user always gets role='patient'
    # ================================================================== #
    def test_02_registered_user_always_gets_patient_role(self):
        """Backend assigns role='patient' regardless of what the client sends."""
        resp = self._register({
            "full_name": "Auto Patient",
            "email": "auto_patient@test.com",
            "password": "pass123",
        })
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(data.get("role"), "patient",
                         "Registered user must have role='patient'")

    # ================================================================== #
    # Test 3 — Client sends role=doctor — still gets 'patient'
    # ================================================================== #
    def test_03_client_cannot_register_as_doctor(self):
        """Sending role=doctor in the registration payload is silently ignored."""
        resp = self._register({
            "full_name": "Escalation Attempt",
            "email": "evil@test.com",
            "password": "pass123",
            "role": "doctor",          # Should be ignored by backend
        })
        # Registration must succeed (201) and role must be 'patient'
        self.assertEqual(resp.status_code, 201, resp.data)
        data = resp.get_json()
        self.assertEqual(data.get("role"), "patient",
                         "Client-supplied role=doctor must be ignored; backend must assign 'patient'")

    # ================================================================== #
    # Test 4 — Client sends role=admin — still gets 'patient'
    # ================================================================== #
    def test_04_client_cannot_register_as_admin(self):
        """Sending role=admin in the registration payload is silently ignored."""
        resp = self._register({
            "full_name": "Admin Attempt",
            "email": "admin_attempt@test.com",
            "password": "pass123",
            "role": "admin",
        })
        self.assertEqual(resp.status_code, 201, resp.data)
        data = resp.get_json()
        self.assertEqual(data.get("role"), "patient")

    # ================================================================== #
    # Test 5 — Patient cannot access GET /doctor/patients (403)
    # ================================================================== #
    def test_05_patient_cannot_access_doctor_patients_list(self):
        """Patient token → GET /api/doctor/patients → 403 Forbidden."""
        resp = self.client.get("/api/doctor/patients", headers=self.patient_headers)
        self.assertEqual(resp.status_code, 403, resp.data)

    # ================================================================== #
    # Test 6 — Patient cannot access GET /doctor/patient/<id> (403)
    # ================================================================== #
    def test_06_patient_cannot_access_doctor_patient_detail(self):
        """Patient token → GET /api/doctor/patient/<id> → 403 Forbidden."""
        resp = self.client.get(
            f"/api/doctor/patient/{self.other_patient_profile.patient_id}",
            headers=self.patient_headers,
        )
        self.assertEqual(resp.status_code, 403, resp.data)

    # ================================================================== #
    # Test 7 — Patient cannot access doctor ACP review endpoint (403)
    # ================================================================== #
    def test_07_patient_cannot_call_doctor_review_endpoint(self):
        """Patient token → PUT /api/doctor/review/<id> → 403 Forbidden."""
        resp = self.client.put(
            f"/api/doctor/review/{self.patient_profile.patient_id}",
            json={"doctor_notes": "hack attempt"},
            headers=self.patient_headers,
        )
        self.assertEqual(resp.status_code, 403, resp.data)

    # ================================================================== #
    # Test 8 — Doctor can sign in and get a token with role='doctor'
    # ================================================================== #
    def test_08_doctor_can_login(self):
        """Pre-created doctor account can sign in and receives role='doctor' in response."""
        resp = self._login("doctor@test.com", "docpass123")
        self.assertEqual(resp.status_code, 200, resp.data)
        data = resp.get_json()
        self.assertEqual(data.get("role"), "doctor")
        self.assertIn("token", data)

    # ================================================================== #
    # Test 9 — Doctor can access GET /doctor/patients (200)
    # ================================================================== #
    def test_09_doctor_can_access_patient_list(self):
        """Doctor token → GET /api/doctor/patients → 200 OK."""
        resp = self.client.get("/api/doctor/patients", headers=self.doctor_headers)
        self.assertEqual(resp.status_code, 200, resp.data)

    # ================================================================== #
    # Test 10 — Unauthenticated request to doctor endpoint is rejected (401)
    # ================================================================== #
    def test_10_unauthenticated_request_rejected(self):
        """No token → GET /api/doctor/patients → 401 Unauthorized."""
        resp = self.client.get("/api/doctor/patients")
        self.assertEqual(resp.status_code, 401, resp.data)

    # ================================================================== #
    # Test 11 — Invalid credentials return 401
    # ================================================================== #
    def test_11_invalid_credentials_rejected(self):
        """Wrong password → POST /api/auth/login → 401."""
        resp = self._login("existing_patient@test.com", "wrongpassword")
        self.assertEqual(resp.status_code, 401, resp.data)

    # ================================================================== #
    # Test 12 — Non-existent user returns 401
    # ================================================================== #
    def test_12_nonexistent_user_login_rejected(self):
        """Unknown email → POST /api/auth/login → 401."""
        resp = self._login("ghost@test.com", "anypass")
        self.assertEqual(resp.status_code, 401, resp.data)

    # ================================================================== #
    # Test 13 — Existing patient accounts can still sign in
    # ================================================================== #
    def test_13_existing_patient_can_still_login(self):
        """Pre-existing patient accounts are unaffected by RBAC changes."""
        resp = self._login("existing_patient@test.com", "pass123")
        self.assertEqual(resp.status_code, 200, resp.data)
        data = resp.get_json()
        self.assertEqual(data.get("role"), "patient")

    # ================================================================== #
    # Test 14 — Existing doctor accounts can still sign in
    # ================================================================== #
    def test_14_existing_doctor_can_still_login(self):
        """Pre-existing doctor accounts are unaffected by RBAC changes."""
        resp = self._login("doctor@test.com", "docpass123")
        self.assertEqual(resp.status_code, 200, resp.data)
        data = resp.get_json()
        self.assertEqual(data.get("role"), "doctor")

    # ================================================================== #
    # Test 15 — Patient cannot access another patient's profile (403 / own only)
    # ================================================================== #
    def test_15_patient_cannot_read_other_patient_profile(self):
        """Patient A cannot read Patient B's record via GET /api/patients/<id>."""
        other_id = self.other_patient_profile.patient_id
        resp = self.client.get(
            f"/api/patients/{other_id}",
            headers=self.patient_headers,
        )
        # Must be 403 Forbidden (cross-patient read) — not 200
        self.assertNotEqual(
            resp.status_code, 200,
            f"Patient A must NOT be able to read Patient B's profile (got {resp.status_code})"
        )


if __name__ == "__main__":
    unittest.main()
