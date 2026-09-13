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

class UserRegisterSchema(Schema):
    """Validation schema for user registration payload."""
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=6))
    full_name = fields.Str(required=True, validate=validate.Length(min=1))
    role = fields.Str(required=True, validate=validate.OneOf(['patient', 'doctor', 'admin']))

class UserLoginSchema(Schema):
    """Validation schema for user login payload."""
    email = fields.Email(required=True)
    password = fields.Str(required=True)
