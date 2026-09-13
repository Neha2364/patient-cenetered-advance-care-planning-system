from datetime import datetime
from backend.extensions import db

class Patient(db.Model):
    """Patient clinical profile details."""
    __tablename__ = 'patients'

    patient_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    preferred_language = db.Column(db.String(20), nullable=False, default='English') # English or Kannada
    government_id_type = db.Column(db.String(50), nullable=True)  # Aadhaar, Passport, Driving License, Voter ID
    government_id_number = db.Column(db.String(50), nullable=True)
    permanent_address = db.Column(db.Text, nullable=True)
    current_address = db.Column(db.Text, nullable=True)
    municipality_panchayat = db.Column(db.String(100), nullable=True)
    beliefs_values = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = db.relationship('User', back_populates='patient_profile')
    acp_preferences = db.relationship('ACPPreference', back_populates='patient', uselist=False, cascade="all, delete-orphan")
    dhrs = db.relationship('DHR', back_populates='patient', cascade="all, delete-orphan")
    chat_histories = db.relationship('ChatHistory', back_populates='patient', cascade="all, delete-orphan")
    generated_amds = db.relationship('GeneratedAMD', back_populates='patient', cascade="all, delete-orphan")
    audit_logs = db.relationship('AuditLog', back_populates='patient', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Patient ID {self.patient_id} (User ID {self.user_id})>"
