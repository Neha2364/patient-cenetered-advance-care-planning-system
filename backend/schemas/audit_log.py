from backend.extensions import ma
from backend.models.audit_log import AuditLog
from marshmallow import fields

class AuditLogSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = AuditLog
        load_instance = True
        include_fk = True

    id = fields.Int(dump_only=True)
    timestamp = fields.DateTime(dump_only=True)
    patient_id = fields.Int(allow_none=True)
    action = fields.Str(required=True)
    performed_by = fields.Int(allow_none=True)
    remarks = fields.Str(allow_none=True)
