from backend.extensions import db
from backend.models.audit_log import AuditLog

class AuditService:
    """Service layer to log actions for clinical audit purposes."""
    
    @staticmethod
    def log_action(patient_id, action, performed_by_id, remarks=None):
        """Log a patient data modification action."""
        try:
            log = AuditLog(
                patient_id=patient_id,
                action=action,
                performed_by=performed_by_id,
                remarks=remarks
            )
            db.session.add(log)
            db.session.commit()
            return log
        except Exception as e:
            # We don't want audit logging failure to block the main operations, 
            # but in production, we should log the system warning.
            db.session.rollback()
            print(f"CRITICAL SYSTEM WARNING: Failed to write audit log: {str(e)}")
            return None

    @staticmethod
    def get_logs_by_patient(patient_id):
        """Fetch audit trail records for a specific patient."""
        return AuditLog.query.filter_by(patient_id=patient_id).order_by(AuditLog.timestamp.desc()).all()

    @staticmethod
    def get_all_logs(limit=100):
        """Fetch global audit logs for admin review."""
        return AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
