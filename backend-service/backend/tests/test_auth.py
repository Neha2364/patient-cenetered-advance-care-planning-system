import unittest
import json
from backend.config import Config
from backend.app import create_app
from backend.extensions import db
from backend.models.user import User
from backend.utils.auth_helpers import decode_token

class TestConfig(Config):
    TESTING = True
    ENV = 'testing'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    AHCP_AI_SERVICE_API_KEY = 'test-secret'
    JWT_SECRET_KEY = 'test-jwt-secret'

class AuthTestCase(unittest.TestCase):
    """Test suite for User Authentication endpoints (register & login)."""

    def setUp(self):
        """Set up testing context and initialize clean database tables."""
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Re-create database tables
        db.create_all()

    def tearDown(self):
        """Clean up databases and pop testing context."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_user_registration_success(self):
        """Verify successful user registration."""
        payload = {
            "email": "newuser@test.com",
            "password": "securepassword123",
            "full_name": "Test User",
            "role": "patient"
        }
        response = self.client.post(
            '/api/auth/register',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        
        # Verify response keys
        self.assertIn('id', data)
        self.assertEqual(data['email'], "newuser@test.com")
        self.assertEqual(data['full_name'], "Test User")
        self.assertEqual(data['role'], "patient")
        self.assertNotIn('password_hash', data)
        self.assertNotIn('password', data)

        # Verify entry in database and hashing
        user = User.query.filter_by(email="newuser@test.com").first()
        self.assertIsNotNone(user)
        self.assertTrue(user.check_password("securepassword123"))
        self.assertFalse(user.check_password("wrongpassword"))

    def test_user_registration_duplicate_email(self):
        """Verify duplicate email registration is rejected."""
        # Create a user first
        user = User(email="duplicate@test.com", full_name="Original User", role="patient")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        # Try to register duplicate email
        payload = {
            "email": "duplicate@test.com",
            "password": "securepassword123",
            "full_name": "Another User",
            "role": "doctor"
        }
        response = self.client.post(
            '/api/auth/register',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('message', data)
        self.assertTrue("already exists" in data['message'])

    def test_user_registration_validation_errors(self):
        """Verify registration payload constraints."""
        # Test short password (< 6 chars)
        payload = {
            "email": "shortpwd@test.com",
            "password": "123",
            "full_name": "Short Pwd",
            "role": "patient"
        }
        response = self.client.post(
            '/api/auth/register',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('password', json.loads(response.data)['message'])

        # Test invalid email
        payload = {
            "email": "not-an-email",
            "password": "password123",
            "full_name": "Bad Email",
        }
        response = self.client.post(
            '/api/auth/register',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('email', json.loads(response.data)['message'])

    def test_user_login_success(self):
        """Verify credentials validation and JWT token generation."""
        # Seed a user
        user = User(email="loginuser@test.com", full_name="Login User", role="doctor")
        user.set_password("mypassword123")
        db.session.add(user)
        db.session.commit()

        payload = {
            "email": "loginuser@test.com",
            "password": "mypassword123"
        }
        response = self.client.post(
            '/api/auth/login',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        # Check login keys
        self.assertIn('token', data)
        self.assertEqual(data['user_id'], user.id)
        self.assertEqual(data['full_name'], "Login User")
        self.assertEqual(data['role'], "doctor")

        # Verify JWT compatibility with our decorators
        claims = decode_token(data['token'])
        self.assertEqual(claims['user_id'], user.id)
        self.assertEqual(claims['email'], user.email)
        self.assertEqual(claims['role'], user.role)

    def test_user_login_failure(self):
        """Verify login fails with invalid credentials."""
        # Seed a user
        user = User(email="loginuser@test.com", full_name="Login User", role="admin")
        user.set_password("mypassword123")
        db.session.add(user)
        db.session.commit()

        # Wrong password
        payload = {
            "email": "loginuser@test.com",
            "password": "wrongpassword"
        }
        response = self.client.post(
            '/api/auth/login',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)

        # Non-existent user
        payload = {
            "email": "nonexistent@test.com",
            "password": "password123"
        }
        response = self.client.post(
            '/api/auth/login',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)

if __name__ == '__main__':
    unittest.main()
