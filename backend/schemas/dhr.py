from backend.extensions import ma
from backend.models.dhr import DHR
from marshmallow import fields, validates, ValidationError

class DHRSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = DHR
        load_instance = False
        include_fk = True

    id = fields.Int(dump_only=True)
    patient_id = fields.Int(required=True)
    full_name = fields.Str(required=True)
    relationship = fields.Str(required=True)
    email_primary = fields.Email(required=True)
    email_secondary = fields.Email(allow_none=True)
    mobile_primary = fields.Str(required=True)
    mobile_secondary = fields.Str(allow_none=True)
    government_id_type = fields.Str(allow_none=True)
    government_id_number = fields.Str(allow_none=True)
    preference_order = fields.Int(default=1)

    @validates('government_id_type')
    def validate_gov_id_type(self, value):
        if value and value not in ('Aadhaar', 'Passport', 'Driving License', 'Voter ID'):
            raise ValidationError("Government ID type must be Aadhaar, Passport, Driving License, or Voter ID.")

    @validates('mobile_primary')
    def validate_mobile_primary(self, value):
        if not value:
            raise ValidationError("Primary mobile number is required.")
        cleaned = ''.join(c for c in value if c.isdigit() or c == '+')
        if len(cleaned) < 10 or len(cleaned) > 15:
            raise ValidationError("Primary mobile number must be between 10 and 15 digits.")
            
    @validates('mobile_secondary')
    def validate_mobile_secondary(self, value):
        if value:
            cleaned = ''.join(c for c in value if c.isdigit() or c == '+')
            if len(cleaned) < 10 or len(cleaned) > 15:
                raise ValidationError("Secondary mobile number must be between 10 and 15 digits.")
