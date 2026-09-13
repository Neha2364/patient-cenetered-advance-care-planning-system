from datetime import datetime
from backend.extensions import db

class AuditLog(db.Model):
    """Audit logs for patient-related data alterations."""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    # E.g. ACP Created, ACP Updated, DHR Updated, AMD Generated, AMD Downloaded, Doctor Reviewed, Patient Updated
    performed_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    remarks = db.Column(db.Text, nullable=True)

    # Relationships
    patient = db.relationship('Patient', back_populates='audit_logs')
    performer = db.relationship('User', back_populates='performed_logs')

    def __repr__(self):
        return f"<AuditLog {self.action} performed by User {self.performed_by} at {self.timestamp}>"
