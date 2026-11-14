import hashlib
import secrets
from datetime import datetime, timedelta
from flask import request, jsonify, g
from backend.config import Config
from backend.extensions import db
from backend.models.user import User
from backend.models.password_reset_token import PasswordResetToken
from backend.schemas.user import UserRegisterSchema, UserLoginSchema, UserSchema, ChangePasswordSchema
from backend.utils.auth_helpers import generate_token, token_required
from backend.utils.email_service import is_email_configured, send_password_reset_email
from backend.services.admin_service import AdminService
from backend.services.audit_service import AuditService
from marshmallow import ValidationError

# Instantiate schemas
register_schema = UserRegisterSchema()
login_schema = UserLoginSchema()
user_schema = UserSchema()
change_password_schema = ChangePasswordSchema()

def format_validation_error(messages):
    """Format Marshmallow validation error dictionary into a clean string."""
    if isinstance(messages, dict):
        formatted = []
        for field, msgs in messages.items():
            msg_str = ", ".join(msgs) if isinstance(msgs, list) else str(msgs)
            formatted.append(f"{field}: {msg_str}")
        return "; ".join(formatted)
    return str(messages)

def register():
    """Register a new user (POST /api/auth/register).

    Security: The role is ALWAYS set to 'patient' server-side.
    Any 'role' value sent by the client is silently ignored.
    Doctor accounts must be created via the secure CLI script only.
    """
    try:
        json_data = request.get_json()
        if not json_data:
            return jsonify({'error': 'Bad Request', 'message': 'No input data provided'}), 400

        # SECURITY: Strip any client-supplied role before validation.
        # Public registration always produces a 'patient' account.
        json_data.pop('role', None)

        # Validate request payload
        validated_data = register_schema.load(json_data)

        # Check if user already exists
        email = validated_data['email']
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'error': 'Bad Request', 'message': f'A user with email {email} already exists.'}), 400

        # Create new user — role is always 'patient' for public registration
        new_user = User(
            full_name=validated_data['full_name'],
            email=email,
            role='patient'
        )
        new_user.set_password(validated_data['password'])

        db.session.add(new_user)
        db.session.commit()

        return jsonify(user_schema.dump(new_user)), 201

    except ValidationError as err:
        return jsonify({'error': 'Validation Error', 'message': format_validation_error(err.messages)}), 400
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500

def login():
    """Authenticate credentials and generate token (POST /api/auth/login)."""
    try:
        json_data = request.get_json()
        if not json_data:
            return jsonify({'error': 'Bad Request', 'message': 'No credentials provided'}), 400

        # Validate request payload
        validated_data = login_schema.load(json_data)

        # Retrieve user and verify credentials
        email = validated_data['email']
        password = validated_data['password']
        user = User.query.filter_by(email=email).first()

        if not user:
            return jsonify({'error': 'Unauthorized', 'message': 'Please create an account before signing in.'}), 401

        if not user.check_password(password):
            return jsonify({'error': 'Unauthorized', 'message': 'Invalid credentials.'}), 401

        # Block deactivated doctor accounts
        if user.role == 'doctor' and not AdminService.is_doctor_active(user.id):
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Your doctor account has been deactivated. Please contact the administrator.'
            }), 401

        # Generate JWT token compatible with token_required decorator
        must_change = bool(getattr(user, 'must_change_password', False))
        token = generate_token(user.id, user.email, user.role, must_change_password=must_change)
        if isinstance(token, bytes):
            token = token.decode('utf-8')

        return jsonify({
            'token': token,
            'user_id': user.id,
            'full_name': user.full_name,
            'role': user.role,
            'must_change_password': must_change,
        }), 200

    except ValidationError as err:
        return jsonify({'error': 'Validation Error', 'message': format_validation_error(err.messages)}), 400
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500


@token_required
def change_password():
    """Change the authenticated user's password (POST /api/auth/change-password).

    Security:
    - Only the authenticated user (via g.current_user) can change their own password.
    - Requires verification of the current/temporary password.
    - New password must be at least 6 characters and match confirmation.
    - New password must be distinct from current password.
    - Resets must_change_password to False upon successful change.
    """
    try:
        user = g.current_user
        json_data = request.get_json()
        if not json_data:
            return jsonify({'error': 'Bad Request', 'message': 'No input data provided'}), 400

        validated_data = change_password_schema.load(json_data)
        current_password = validated_data['current_password']
        new_password = validated_data['new_password']
        confirm_password = validated_data['confirm_password']

        # Verify current password
        if not user.check_password(current_password):
            return jsonify({'error': 'Bad Request', 'message': 'Current password is incorrect.'}), 400

        # Validate confirmation
        if new_password != confirm_password:
            return jsonify({'error': 'Validation Error', 'message': 'New password and confirmation do not match.'}), 400

        # Ensure new password differs from current
        if current_password == new_password:
            return jsonify({'error': 'Validation Error', 'message': 'New password must be different from current password.'}), 400

        # Update password and clear must_change_password flag
        user.set_password(new_password)
        user.must_change_password = False
        db.session.commit()

        # Audit log the action
        AuditService.log_action(
            patient_id=None,
            action=f'{user.role.capitalize()}: Password changed',
            performed_by_id=user.id,
            remarks=f'Password changed for {user.email}',
        )

        # Generate refreshed token with must_change_password = False
        new_token = generate_token(user.id, user.email, user.role, must_change_password=False)
        if isinstance(new_token, bytes):
            new_token = new_token.decode('utf-8')

        return jsonify({
            'message': 'Password changed successfully.',
            'token': new_token,
            'user_id': user.id,
            'full_name': user.full_name,
            'role': user.role,
            'must_change_password': False,
        }), 200

    except ValidationError as err:
        return jsonify({'error': 'Validation Error', 'message': format_validation_error(err.messages)}), 400
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500


def doctor_forgot_password():
    """Request a password reset link for a doctor (POST /api/doctor/forgot-password)."""
    try:
        json_data = request.get_json() or {}
        email = (json_data.get('email') or '').strip().lower()

        if not email:
            return jsonify({'error': 'Bad Request', 'message': 'Email address is required.'}), 400

        # Basic email syntax check
        if '@' not in email or '.' not in email.split('@')[-1]:
            return jsonify({'error': 'Bad Request', 'message': 'Please provide a valid email address.'}), 400

        # Check SMTP / email configuration first
        if not is_email_configured():
            return jsonify({
                'error': 'Email Service Unavailable',
                'message': (
                    'Email delivery service is currently not configured on this server. '
                    'Please contact your administrator to reset your password or configure SMTP settings.'
                )
            }), 503

        # Locate doctor user
        user = User.query.filter_by(email=email).first()
        if not user or user.role != 'doctor':
            return jsonify({
                'error': 'Not Found',
                'message': 'No doctor account was found with this email address.'
            }), 404

        # Check if doctor account is deactivated
        if not AdminService.is_doctor_active(user.id):
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Your doctor account has been deactivated. Please contact the administrator.'
            }), 403

        # Check if doctor is still on mandatory first-login temporary password
        if getattr(user, 'must_change_password', False):
            return jsonify({
                'error': 'Temporary Password Active',
                'message': (
                    'This account is configured with an initial temporary password from your administrator and has not completed first-time setup. '
                    'Please sign in with your temporary password or contact your administrator.'
                )
            }), 400

        # Invalidate any prior unused reset tokens for this user
        PasswordResetToken.query.filter_by(user_id=user.id, is_used=False).update({
            'is_used': True,
            'used_at': datetime.utcnow()
        })

        # Generate secure single-use time-limited token
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        expires_at = datetime.utcnow() + timedelta(hours=1)

        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_used=False
        )
        db.session.add(reset_token)
        db.session.commit()

        # Build reset link
        try:
            from flask import current_app
            frontend_url = current_app.config.get('FRONTEND_URL') or getattr(Config, 'FRONTEND_URL', 'http://localhost:5173')
        except Exception:
            frontend_url = getattr(Config, 'FRONTEND_URL', 'http://localhost:5173')
        reset_link = f"{frontend_url}/doctor-reset-password?token={raw_token}"

        # Send reset email
        success, err_msg = send_password_reset_email(
            to_email=user.email,
            recipient_name=user.full_name,
            reset_link=reset_link,
            expires_in_minutes=60
        )

        if not success:
            return jsonify({
                'error': 'Email Delivery Failed',
                'message': f'Failed to send password reset email: {err_msg}'
            }), 502

        # Log audit entry
        AuditService.log_action(
            patient_id=None,
            action='Doctor: Password reset requested',
            performed_by_id=user.id,
            remarks=f'Password reset link sent to {user.email}'
        )

        return jsonify({
            'message': 'A password reset link has been sent to your email address. Please check your inbox and follow the instructions within 60 minutes.'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500


def doctor_validate_reset_token():
    """Validate a password reset token (POST /api/doctor/validate-reset-token)."""
    try:
        json_data = request.get_json() or {}
        raw_token = (json_data.get('token') or '').strip()

        if not raw_token:
            return jsonify({'valid': False, 'message': 'Reset token is required.'}), 400

        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        record = PasswordResetToken.query.filter_by(token_hash=token_hash).first()

        if not record:
            return jsonify({'valid': False, 'message': 'This password reset link is invalid or has expired.'}), 400

        if record.is_used:
            return jsonify({'valid': False, 'message': 'This password reset link has already been used. Please request a new one.'}), 400

        if record.is_expired:
            return jsonify({'valid': False, 'message': 'This password reset link has expired. Please request a new one.'}), 400

        user = record.user
        if not user or user.role != 'doctor':
            return jsonify({'valid': False, 'message': 'Invalid token for doctor portal.'}), 400

        if not AdminService.is_doctor_active(user.id):
            return jsonify({'valid': False, 'message': 'Doctor account has been deactivated.'}), 403

        # Mask email for privacy
        email = user.email
        parts = email.split('@')
        name_part = parts[0]
        domain_part = parts[1] if len(parts) > 1 else ''
        masked_local = (name_part[0] + '***' + name_part[-1]) if len(name_part) > 2 else (name_part[:1] + '***')
        masked_email = f"{masked_local}@{domain_part}" if domain_part else masked_local

        return jsonify({
            'valid': True,
            'email': masked_email,
            'full_name': user.full_name
        }), 200

    except Exception as e:
        return jsonify({'valid': False, 'message': str(e)}), 500


def doctor_reset_password():
    """Reset a doctor's password using a valid token (POST /api/doctor/reset-password)."""
    try:
        json_data = request.get_json() or {}
        raw_token = (json_data.get('token') or '').strip()
        new_password = json_data.get('new_password') or ''
        confirm_password = json_data.get('confirm_password') or ''

        if not raw_token:
            return jsonify({'error': 'Bad Request', 'message': 'Reset token is required.'}), 400

        if not new_password or not confirm_password:
            return jsonify({'error': 'Bad Request', 'message': 'New password and confirmation are required.'}), 400

        if len(new_password) < 6:
            return jsonify({'error': 'Validation Error', 'message': 'Password must be at least 6 characters long.'}), 400

        if new_password != confirm_password:
            return jsonify({'error': 'Validation Error', 'message': 'New password and confirmation do not match.'}), 400

        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()
        record = PasswordResetToken.query.filter_by(token_hash=token_hash).first()

        if not record or record.is_used or record.is_expired:
            return jsonify({'error': 'Bad Request', 'message': 'This password reset link is invalid, expired, or already used.'}), 400

        user = record.user
        if not user or user.role != 'doctor':
            return jsonify({'error': 'Bad Request', 'message': 'Invalid token for doctor portal.'}), 400

        if not AdminService.is_doctor_active(user.id):
            return jsonify({'error': 'Unauthorized', 'message': 'Doctor account has been deactivated.'}), 403

        if user.check_password(new_password):
            return jsonify({'error': 'Validation Error', 'message': 'New password must be different from current password.'}), 400

        # Update password
        user.set_password(new_password)
        user.must_change_password = False
        record.is_used = True
        record.used_at = datetime.utcnow()

        # Invalidate any other active reset tokens for this user
        PasswordResetToken.query.filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.id != record.id
        ).update({'is_used': True, 'used_at': datetime.utcnow()})

        db.session.commit()

        # Audit log
        AuditService.log_action(
            patient_id=None,
            action='Doctor: Password reset completed',
            performed_by_id=user.id,
            remarks=f'Password reset successfully via reset token for {user.email}'
        )

        return jsonify({
            'message': 'Your password has been successfully reset. You may now sign in with your new password.'
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500
