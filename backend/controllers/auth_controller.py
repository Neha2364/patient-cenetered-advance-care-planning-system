from flask import request, jsonify, g
from backend.extensions import db
from backend.models.user import User
from backend.schemas.user import UserRegisterSchema, UserLoginSchema, UserSchema, ChangePasswordSchema
from backend.utils.auth_helpers import generate_token, token_required
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

