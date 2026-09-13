from datetime import datetime
from backend.extensions import db

class GeneratedAMD(db.Model):
    """Metadata for generated Advance Care Directives stored in Supabase Storage."""
    __tablename__ = 'generated_amds'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False)
    pdf_name = db.Column(db.String(255), nullable=False)
    pdf_url = db.Column(db.Text, nullable=False)
    storage_bucket = db.Column(db.String(100), nullable=False)
    storage_path = db.Column(db.String(255), nullable=False)
    version = db.Column(db.Integer, default=1, nullable=False)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(50), default='Active', nullable=False)  # Active, Superseded, Revoked

    # Relationships
    patient = db.relationship('Patient', back_populates='generated_amds')

    def __repr__(self):
        return f"<GeneratedAMD {self.pdf_name} (Patient {self.patient_id}, Version {self.version})>"
