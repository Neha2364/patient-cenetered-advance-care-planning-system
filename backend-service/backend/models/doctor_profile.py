from datetime import datetime
from backend.extensions import db


class DoctorProfile(db.Model):
    """Doctor profile details, linked to the Users table."""
    __tablename__ = 'doctor_profiles'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        unique=True,
        nullable=False,
    )
    mobile_number = db.Column(db.String(20), nullable=True)
    specialization = db.Column(db.String(100), nullable=True)
    hospital = db.Column(db.String(150), nullable=True)
    medical_registration_number = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    user = db.relationship('User', back_populates='doctor_profile')

    def __repr__(self):
        return f'<DoctorProfile user_id={self.user_id} specialization={self.specialization}>'

