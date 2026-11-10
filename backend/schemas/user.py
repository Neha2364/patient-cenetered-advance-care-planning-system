from backend.extensions import ma
from backend.models.user import User
from marshmallow import Schema, fields, validate

class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
        include_fk = True
        exclude = ('password_hash',)

    id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    email = fields.Email(required=True)
    full_name = fields.Str(required=True)
    role = fields.Str(required=True)
    must_change_password = fields.Bool(dump_only=True)

class UserRegisterSchema(Schema):
    """Validation schema for user registration payload.
    
    NOTE: 'role' is intentionally excluded. The backend always assigns
    role='patient' for public registration. The client must never control role.
    """
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=6))
    full_name = fields.Str(required=True, validate=validate.Length(min=1))

class UserLoginSchema(Schema):
    """Validation schema for user login payload."""
    email = fields.Email(required=True)
    password = fields.Str(required=True)

class ChangePasswordSchema(Schema):
    """Validation schema for authenticated password change payload."""
    current_password = fields.Str(required=True)
    new_password = fields.Str(required=True, validate=validate.Length(min=6))
    confirm_password = fields.Str(required=True, validate=validate.Length(min=6))
