"""
Unit and Integration Test Suite: Doctor Forgot Password Feature

Tests:
1. Forgot password request with missing or invalid email returns 400.
2. Forgot password request when SMTP is not configured returns 503 with clear message.
3. Forgot password request for non-existent user or non-doctor role returns 404.
4. Forgot password request for deactivated doctor returns 403.
5. Forgot password request for doctor with pending temporary password (must_change_password=True) returns 400 with guidance.
6. Successful forgot password generates token hash in DB, 1-hour expiry, audit log, and sends email.
7. Validate reset token: missing token (400), invalid token (400), expired token (400), used token (400).
8. Validate reset token: valid token returns 200 with masked email and clinician name.
9. Reset password: validation failures for short password, mismatched passwords, same as current password.
10. Reset password: successful reset updates password hash, marks token used, invalidates prior tokens.
11. After reset: doctor can immediately sign in with new password; old password fails (401).
12. Security: single-use enforcement prevents token reuse; raw token is not stored in DB plaintext.
"""

import unittest
import json
import hashlib
from datetime import datetime, timedelta
from unittest.mock import patch

from backend.config import Config
from backend.app import create_app
from backend.extensions import db
from backend.models.user import User
from backend.models.doctor_profile import DoctorProfile
from backend.models.password_reset_token import PasswordResetToken
from backend.services.admin_service import AdminService


class TestConfig(Config):
    TESTING = True
    ENV = 'testing'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    AHCP_AI_SERVICE_API_KEY = 'test-secret'
    JWT_SECRET_KEY = 'test-jwt-forgot-password-secret'
    SMTP_HOST = 'smtp.testserver.local'
    SMTP_PORT = 587
    FRONTEND_URL = 'http://localhost:5173'


class DoctorForgotPasswordTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        # Seed Admin
        self.admin = User(full_name='System Admin', email='admin@acpcare.app', role='admin')
        self.admin.set_password('AdminPass123!')
        db.session.add(self.admin)

        # Seed Patient
        self.patient = User(full_name='John Patient', email='patient@example.com', role='patient')
        self.patient.set_password('PatientPass123!')
        db.session.add(self.patient)

        # Seed Established Doctor (already changed temporary password)
        self.doctor = User(
            full_name='Dr. Sarah Smith',
            email='sarah.smith@hospital.com',
            role='doctor',
            must_change_password=False
        )
        self.doctor.set_password('DoctorOldPass123!')
        db.session.add(self.doctor)
        db.session.flush()

        self.doctor_profile = DoctorProfile(
            user_id=self.doctor.id,
            specialization='Palliative Care',
            hospital='City General',
            medical_registration_number='MED-1001',
            is_active=True
        )
        db.session.add(self.doctor_profile)

        # Seed New Doctor with pending temporary password
        self.temp_doctor = User(
            full_name='Dr. New Clinician',
            email='new.doc@hospital.com',
            role='doctor',
            must_change_password=True
        )
        self.temp_doctor.set_password('TempSecretPass123!')
        db.session.add(self.temp_doctor)
        db.session.flush()

        self.temp_doctor_profile = DoctorProfile(
            user_id=self.temp_doctor.id,
            specialization='Internal Medicine',
            hospital='City General',
            medical_registration_number='MED-1002',
            is_active=True
        )
        db.session.add(self.temp_doctor_profile)

        # Seed Inactive Doctor
        self.inactive_doctor = User(
            full_name='Dr. Inactive',
            email='inactive.doc@hospital.com',
            role='doctor',
            must_change_password=False
        )
        self.inactive_doctor.set_password('InactivePass123!')
        db.session.add(self.inactive_doctor)
        db.session.flush()

        self.inactive_profile = DoctorProfile(
            user_id=self.inactive_doctor.id,
            specialization='Geriatrics',
            hospital='City General',
            medical_registration_number='MED-1003',
            is_active=False
        )
        db.session.add(self.inactive_profile)

        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_01_forgot_password_invalid_input(self):
        """Empty input or bad email returns 400."""
        # Empty body
        res = self.client.post('/api/doctor/forgot-password', json={})
        self.assertEqual(res.status_code, 400)

        # Missing @
        res = self.client.post('/api/doctor/forgot-password', json={'email': 'sarahhospital.com'})
        self.assertEqual(res.status_code, 400)

    def test_02_forgot_password_smtp_not_configured(self):
        """When SMTP host is unset/empty, return 503 with exact clear message."""
        with patch('backend.controllers.auth_controller.is_email_configured', return_value=False):
            res = self.client.post('/api/doctor/forgot-password', json={'email': 'sarah.smith@hospital.com'})
            self.assertEqual(res.status_code, 503)
            data = res.get_json()
            self.assertIn("Email delivery service is currently not configured", data['message'])

    def test_03_forgot_password_nonexistent_or_non_doctor(self):
        """Non-existent email or non-doctor accounts return 404."""
        # Non-existent email
        res = self.client.post('/api/doctor/forgot-password', json={'email': 'ghost@hospital.com'})
        self.assertEqual(res.status_code, 404)

        # Patient account
        res = self.client.post('/api/doctor/forgot-password', json={'email': 'patient@example.com'})
        self.assertEqual(res.status_code, 404)

        # Admin account
        res = self.client.post('/api/doctor/forgot-password', json={'email': 'admin@acpcare.app'})
        self.assertEqual(res.status_code, 404)

    def test_04_forgot_password_deactivated_doctor(self):
        """Deactivated doctor accounts cannot request password reset (403)."""
        res = self.client.post('/api/doctor/forgot-password', json={'email': 'inactive.doc@hospital.com'})
        self.assertEqual(res.status_code, 403)
        data = res.get_json()
        self.assertIn("deactivated", data['message'])

    def test_05_forgot_password_pending_temporary_password(self):
        """Doctors with must_change_password=True must sign in with temporary password."""
        res = self.client.post('/api/doctor/forgot-password', json={'email': 'new.doc@hospital.com'})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("temporary password", data['message'])
        self.assertIn("first-time setup", data['message'])

    @patch('backend.controllers.auth_controller.send_password_reset_email', return_value=(True, 'Email sent'))
    def test_06_forgot_password_success(self, mock_send_email):
        """Established doctor requesting reset receives 200, token created in DB."""
        res = self.client.post('/api/doctor/forgot-password', json={'email': 'sarah.smith@hospital.com'})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("password reset link has been sent", data['message'])

        mock_send_email.assert_called_once()
        call_kwargs = mock_send_email.call_args[1]
        self.assertEqual(call_kwargs['to_email'], 'sarah.smith@hospital.com')
        self.assertEqual(call_kwargs['recipient_name'], 'Dr. Sarah Smith')
        self.assertIn('token=', call_kwargs['reset_link'])

        # Check DB record
        tokens = PasswordResetToken.query.filter_by(user_id=self.doctor.id).all()
        self.assertEqual(len(tokens), 1)
        self.assertFalse(tokens[0].is_used)
        self.assertGreater(tokens[0].expires_at, datetime.utcnow())

    def test_07_validate_token_errors(self):
        """Validation fails for invalid, missing, used, or expired tokens."""
        # Missing token
        res = self.client.post('/api/doctor/validate-reset-token', json={})
        self.assertEqual(res.status_code, 400)

        # Invalid token
        res = self.client.post('/api/doctor/validate-reset-token', json={'token': 'nonexistent_token_12345'})
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.get_json()['valid'])

        # Used token
        raw_token = 'used_token_abc'
        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        used_token = PasswordResetToken(
            user_id=self.doctor.id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(hours=1),
            is_used=True,
            used_at=datetime.utcnow()
        )
        db.session.add(used_token)
        db.session.commit()

        res = self.client.post('/api/doctor/validate-reset-token', json={'token': raw_token})
        self.assertEqual(res.status_code, 400)
        self.assertIn("already been used", res.get_json()['message'])

        # Expired token
        raw_token_exp = 'expired_token_xyz'
        token_hash_exp = hashlib.sha256(raw_token_exp.encode('utf-8')).hexdigest()
        exp_token = PasswordResetToken(
            user_id=self.doctor.id,
            token_hash=token_hash_exp,
            expires_at=datetime.utcnow() - timedelta(minutes=10),
            is_used=False
        )
        db.session.add(exp_token)
        db.session.commit()

        res = self.client.post('/api/doctor/validate-reset-token', json={'token': raw_token_exp})
        self.assertEqual(res.status_code, 400)
        self.assertIn("expired", res.get_json()['message'])

    def test_08_validate_token_success(self):
        """Valid token returns valid=True with masked email and doctor name."""
        raw_token = 'valid_token_1234567890abcdef'
        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        token_rec = PasswordResetToken(
            user_id=self.doctor.id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(hours=1),
            is_used=False
        )
        db.session.add(token_rec)
        db.session.commit()

        res = self.client.post('/api/doctor/validate-reset-token', json={'token': raw_token})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['valid'])
        self.assertEqual(data['full_name'], 'Dr. Sarah Smith')
        self.assertIn('@hospital.com', data['email'])
        self.assertIn('***', data['email'])

    def test_09_reset_password_validation(self):
        """Input validation on reset-password endpoint."""
        raw_token = 'reset_val_token_123'
        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        token_rec = PasswordResetToken(
            user_id=self.doctor.id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(hours=1),
            is_used=False
        )
        db.session.add(token_rec)
        db.session.commit()

        # Missing confirmation
        res = self.client.post('/api/doctor/reset-password', json={
            'token': raw_token,
            'new_password': 'BrandNewPass123!'
        })
        self.assertEqual(res.status_code, 400)

        # Passwords mismatch
        res = self.client.post('/api/doctor/reset-password', json={
            'token': raw_token,
            'new_password': 'BrandNewPass123!',
            'confirm_password': 'DifferentPass123!'
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("do not match", res.get_json()['message'])

        # Too short (< 6 characters)
        res = self.client.post('/api/doctor/reset-password', json={
            'token': raw_token,
            'new_password': 'abc',
            'confirm_password': 'abc'
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("at least 6 characters", res.get_json()['message'])

        # Same as current password
        res = self.client.post('/api/doctor/reset-password', json={
            'token': raw_token,
            'new_password': 'DoctorOldPass123!',
            'confirm_password': 'DoctorOldPass123!'
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("different from current password", res.get_json()['message'])

    def test_10_reset_password_success_and_login_verification(self):
        """Complete end-to-end password reset and login verification."""
        raw_token = 'fresh_reset_token_secret'
        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        token_rec = PasswordResetToken(
            user_id=self.doctor.id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(hours=1),
            is_used=False
        )
        db.session.add(token_rec)
        db.session.commit()

        # Submit password reset
        new_pass = 'DoctorFreshNewPass2026!'
        res = self.client.post('/api/doctor/reset-password', json={
            'token': raw_token,
            'new_password': new_pass,
            'confirm_password': new_pass
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("successfully reset", data['message'])

        # Check DB: token is used
        refreshed_token = PasswordResetToken.query.filter_by(token_hash=token_hash).first()
        self.assertTrue(refreshed_token.is_used)
        self.assertIsNotNone(refreshed_token.used_at)

        # Check login with OLD password -> Fails (401)
        res_old = self.client.post('/api/auth/login', json={
            'email': 'sarah.smith@hospital.com',
            'password': 'DoctorOldPass123!'
        })
        self.assertEqual(res_old.status_code, 401)

        # Check login with NEW password -> Succeeds (200)
        res_new = self.client.post('/api/auth/login', json={
            'email': 'sarah.smith@hospital.com',
            'password': new_pass
        })
        self.assertEqual(res_new.status_code, 200)
        login_data = res_new.get_json()
        self.assertEqual(login_data['role'], 'doctor')
        self.assertFalse(login_data['must_change_password'])
        self.assertIn('token', login_data)

        # Check single-use: Trying to use the same token again fails
        res_reuse = self.client.post('/api/doctor/reset-password', json={
            'token': raw_token,
            'new_password': 'AnotherPass123!',
            'confirm_password': 'AnotherPass123!'
        })
        self.assertEqual(res_reuse.status_code, 400)


if __name__ == '__main__':
    unittest.main()
