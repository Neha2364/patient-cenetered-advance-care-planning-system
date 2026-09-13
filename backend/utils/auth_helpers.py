import jwt
from datetime import datetime, timedelta
from flask import request, jsonify, g
from functools import wraps
from backend.config import Config
from backend.models.user import User

def generate_token(user_id, email, role):
    """Utility to generate a JWT token for testing/integration purposes."""
    try:
        payload = {
            'user_id': user_id,
            'email': email,
            'role': role,
            'exp': datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRATION_HOURS),
            'iat': datetime.utcnow()
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
        # Check Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token_type, token_val = auth_header.split(" ")
                if token_type.lower() == 'bearer':
                    token = token_val
            except ValueError:
                return jsonify({'error': 'Unauthorized', 'message': 'Authorization header must be Bearer <token>'}), 401
        
        if not token:
            return jsonify({'error': 'Unauthorized', 'message': 'Authentication token is missing.'}), 401

        payload = decode_token(token)
        if 'error' in payload:
            return jsonify({'error': 'Unauthorized', 'message': payload['error']}), 401

        # Check if user exists in the database
        user = User.query.get(payload['user_id'])
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
                
            return f(*args, **kwargs)
        return decorated
    return decorator
