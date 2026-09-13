from backend.extensions import ma
from backend.models.acp_preference import ACPPreference
from marshmallow import fields, validates, ValidationError

class ACPPreferenceSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ACPPreference
        load_instance = False
        include_fk = True

    patient_id = fields.Int(required=True)
    reviewed_by_doctor = fields.Int(allow_none=True)
    completed_at = fields.DateTime(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)

    cpr_preference = fields.Str(default='NOT SPECIFIED')
    ventilator_preference = fields.Str(default='NOT SPECIFIED')
    dialysis_preference = fields.Str(default='NOT SPECIFIED')
    chemotherapy_preference = fields.Str(default='NOT SPECIFIED')
    radiotherapy_preference = fields.Str(default='NOT SPECIFIED')
    surgery_preference = fields.Str(default='NOT SPECIFIED')
    iv_fluids_preference = fields.Str(default='NOT SPECIFIED')
    nutrition_hydration_preference = fields.Str(default='NOT SPECIFIED')

    organ_donation = fields.Str(default='NOT SPECIFIED')
    body_donation = fields.Str(default='NOT SPECIFIED')
    review_status = fields.Str(default='Pending Review')

    @validates('cpr_preference')
    @validates('ventilator_preference')
    @validates('dialysis_preference')
    @validates('chemotherapy_preference')
    @validates('radiotherapy_preference')
    @validates('surgery_preference')
    @validates('iv_fluids_preference')
    @validates('nutrition_hydration_preference')
    def validate_preference(self, value):
        if value not in ('WANT', 'DO NOT WANT', 'NOT SPECIFIED'):
            raise ValidationError("Preferences must be 'WANT', 'DO NOT WANT', or 'NOT SPECIFIED'.")

    @validates('organ_donation')
    @validates('body_donation')
    def validate_donation(self, value):
        # Allow yes/no/not specified, but also support some custom description for body/organ donation
        if value not in ('YES', 'NO', 'NOT SPECIFIED') and len(value) > 200:
            raise ValidationError("Donation preference must be 'YES', 'NO', 'NOT SPECIFIED', or a description under 200 characters.")

    @validates('review_status')
    def validate_review_status(self, value):
        if value not in ('Pending Review', 'Reviewed', 'Rejected'):
            raise ValidationError("Review status must be 'Pending Review', 'Reviewed', or 'Rejected'.")
