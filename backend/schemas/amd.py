from backend.extensions import ma
from backend.models.generated_amd import GeneratedAMD
from marshmallow import Schema, fields, validates, ValidationError

class WitnessInputSchema(Schema):
    """Schema to validate individual witness details passed during AMD generation."""
    name = fields.Str(required=True)
    email = fields.Email(required=True)
    mobile = fields.Str(required=True)

    @validates('mobile')
    def validate_mobile(self, value):
        cleaned = ''.join(c for c in value if c.isdigit() or c == '+')
        if len(cleaned) < 10 or len(cleaned) > 15:
            raise ValidationError("Witness mobile number must be between 10 and 15 digits.")

class AMDGenerateRequestSchema(Schema):
    """Schema to validate the request payload for AMD PDF generation."""
    patient_id = fields.Int(required=True)
    executor_place = fields.Str(load_default='Not Specified')
    notary_name = fields.Str(load_default='Not Specified')
    notary_place = fields.Str(load_default='Not Specified')
    witnesses = fields.List(fields.Nested(WitnessInputSchema), required=True)
    create_new_version = fields.Bool(load_default=False)

    @validates('witnesses')
    def validate_witnesses_count(self, value):
        if len(value) != 2:
            raise ValidationError("Exactly two witnesses are required to sign the Advance Medical Directive.")

class GeneratedAMDSchema(ma.SQLAlchemyAutoSchema):
    """Schema to serialize/deserialize stored AMD document records."""
    class Meta:
        model = GeneratedAMD
        load_instance = True
        include_fk = True

    id = fields.Int(dump_only=True)
    generated_at = fields.DateTime(dump_only=True)
    pdf_name = fields.Str(dump_only=True)
    pdf_url = fields.Str(dump_only=True)
    storage_bucket = fields.Str(dump_only=True)
    storage_path = fields.Str(dump_only=True)
    version = fields.Int(dump_only=True)
    status = fields.Str(dump_only=True)
