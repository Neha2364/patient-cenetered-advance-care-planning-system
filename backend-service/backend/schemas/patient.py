from backend.extensions import ma
from backend.models.patient import Patient
from marshmallow import fields, validates, ValidationError

class PatientSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Patient
        load_instance = False
        include_fk = True

    patient_id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    user_id = fields.Int(required=True)
    full_name = fields.Method("get_full_name", dump_only=True)
    email = fields.Method("get_email", dump_only=True)

    def get_full_name(self, obj):
        return obj.user.full_name if obj.user else None

    def get_email(self, obj):
        return obj.user.email if obj.user else None

    phone = fields.Str(required=False, allow_none=True)
    preferred_language = fields.Str(default='English')
    government_id_type = fields.Str(allow_none=True)
    government_id_number = fields.Str(allow_none=True)

    @validates('phone')
    def validate_phone(self, value):
        if not value:
            return
        # Basic validation: digits and optional leading plus, between 10 and 15 chars
        cleaned = ''.join(c for c in value if c.isdigit() or c == '+')
        if len(cleaned) < 10 or len(cleaned) > 15:
            raise ValidationError("Phone number must be between 10 and 15 digits.")

    @validates('preferred_language')
    def validate_language(self, value):
        if not value:
            raise ValidationError("Preferred language must be specified.")

    @validates('government_id_type')
    def validate_gov_id_type(self, value):
        if value and value not in ('Aadhaar', 'Passport', 'Driving License', 'Voter ID'):
            raise ValidationError("Government ID type must be Aadhaar, Passport, Driving License, or Voter ID.")
