from flask import request, jsonify
from backend.extensions import db
from backend.models.user import User
from backend.schemas.user import UserRegisterSchema, UserLoginSchema, UserSchema
from backend.utils.auth_helpers import generate_token
from backend.services.admin_service import AdminService
from marshmallow import ValidationError

# Instantiate schemas
register_schema = UserRegisterSchema()
login_schema = UserLoginSchema()
user_schema = UserSchema()

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
        token = generate_token(user.id, user.email, user.role)
        if isinstance(token, bytes):
            token = token.decode('utf-8')

        return jsonify({
            'token': token,
            'user_id': user.id,
            'full_name': user.full_name,
            'role': user.role
        }), 200

    except ValidationError as err:
        return jsonify({'error': 'Validation Error', 'message': format_validation_error(err.messages)}), 400
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500

