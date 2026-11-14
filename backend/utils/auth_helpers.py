import jwt
from datetime import datetime, timedelta, timezone
from flask import request, jsonify, g
from functools import wraps
from backend.config import Config
from backend.extensions import db
from backend.models.user import User

def generate_token(user_id, email, role, must_change_password=False):
    """Utility to generate a JWT token for testing/integration purposes."""
    try:
        now = datetime.now(timezone.utc)
        payload = {
            'user_id': int(user_id),
            'email': email,
            'role': role,
            'must_change_password': bool(must_change_password),
            'exp': now + timedelta(hours=Config.JWT_EXPIRATION_HOURS),
            'iat': now
        }
        return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm='HS256')
    except Exception as e:
        return str(e)

def decode_token(token):
    """Decode a JWT token using the configured secret key."""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return {'error': 'Token has expired.'}
    except jwt.InvalidTokenError:
        return {'error': 'Invalid token.'}

def token_required(f):
    """Decorator to require a valid JWT token on endpoints."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Check Authorization header (case-insensitive in Flask)
        auth_header = request.headers.get('Authorization')
        if auth_header:
            parts = auth_header.strip().split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
            elif len(parts) == 1:
                # Tolerant fallback: raw token passed without Bearer prefix
                token = parts[0]
            else:
                return jsonify({'error': 'Unauthorized', 'message': 'Authorization header must be Bearer <token>'}), 401
        
        if not token:
            return jsonify({'error': 'Unauthorized', 'message': 'Authentication token is missing.'}), 401

        payload = decode_token(token)
        if 'error' in payload:
            return jsonify({'error': 'Unauthorized', 'message': payload['error']}), 401

        user_id = payload.get('user_id')
        if user_id is None:
            return jsonify({'error': 'Unauthorized', 'message': 'Invalid token payload.'}), 401

        # Check if user exists in the database (SQLAlchemy 2.0 compatible)
        try:
            uid = int(user_id)
            user = db.session.get(User, uid) if hasattr(db.session, 'get') else User.query.get(uid)
        except (ValueError, TypeError):
            user = None

        if not user:
            return jsonify({'error': 'Unauthorized', 'message': 'Authenticated user no longer exists.'}), 401

        # Store authenticated user details in Flask's g context
        g.current_user = user
        return f(*args, **kwargs)
    
    return decorated

def role_required(allowed_roles):
    """Decorator to require specific roles for an endpoint."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Ensure g.current_user is populated (run token_required first)
            if not hasattr(g, 'current_user') or g.current_user is None:
                return jsonify({'error': 'Unauthorized', 'message': 'Authentication required.'}), 401
            
            if g.current_user.role not in allowed_roles:
                return jsonify({
                    'error': 'Forbidden', 
                    'message': f"Access denied. Required roles: {', '.join(allowed_roles)}. Your role: {g.current_user.role}"
                }), 403

            # Enforce mandatory password change for doctor accounts
            if getattr(g.current_user, 'must_change_password', False) and g.current_user.role == 'doctor':
                if request.path not in ('/api/auth/change-password', '/api/doctor/change-password'):
                    return jsonify({
                        'error': 'Forbidden',
                        'message': 'Password change required before accessing this resource.',
                        'must_change_password': True
                    }), 403
                
            return f(*args, **kwargs)
        return decorated
    return decorator
