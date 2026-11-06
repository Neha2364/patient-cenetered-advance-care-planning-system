from datetime import datetime
from backend.extensions import db

class AISession(db.Model):
    """Binds AHCP AI service questionnaire sessions to authenticated patients."""
    __tablename__ = 'ai_sessions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False, index=True)
    language = db.Column(db.String(10), nullable=False, default='en')
    current_question = db.Column(db.Integer, nullable=True, default=1)
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    patient = db.relationship('Patient', back_populates='ai_sessions')

    def __repr__(self):
        return f"<AISession {self.session_id} (Patient {self.patient_id})>"
