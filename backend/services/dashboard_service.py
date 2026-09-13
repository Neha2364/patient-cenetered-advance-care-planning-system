from sqlalchemy import func
from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.acp_preference import ACPPreference
from backend.models.dhr import DHR
from backend.models.generated_amd import GeneratedAMD
from backend.models.audit_log import AuditLog

class DashboardService:
    """Service layer dealing with doctor and admin dashboard analytics, queries, and search logic."""

    @staticmethod
    def search_and_filter_patients(search_query=None, language=None, is_completed=None, review_status=None, amd_generated=None):
        """Perform clinical queries to search and filter patient records."""
        # Join Patient and User models to search
        query = db.session.query(Patient).join(User)

        # 1. Text Search
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.filter(
                (User.full_name.ilike(search_pattern)) |
                (User.email.ilike(search_pattern)) |
                (Patient.phone.ilike(search_pattern))
            )

        # 2. Preferred Language Filter
        if language:
            query = query.filter(Patient.preferred_language == language)

        # Join ACPPreference if filters depend on it
        if is_completed is not None or review_status is not None or amd_generated is not None:
            query = query.join(ACPPreference)
            
            if is_completed is not None:
                query = query.filter(ACPPreference.is_completed == is_completed)
            if review_status:
                query = query.filter(ACPPreference.review_status == review_status)
            if amd_generated is not None:
                query = query.filter(ACPPreference.amd_generated == amd_generated)

        return query.all()

    @staticmethod
    def get_admin_dashboard_metrics():
        """Retrieve aggregated analytical indicators for administrators."""
        total_patients = Patient.query.count()
        total_acp = ACPPreference.query.count()
        total_dhr = DHR.query.count()
        total_amd = GeneratedAMD.query.count()

        # Preferred language distribution
        lang_stats = db.session.query(
            Patient.preferred_language, func.count(Patient.patient_id)
        ).group_by(Patient.preferred_language).all()
        languages_count = {lang: count for lang, count in lang_stats}

        # ACP completion details
        completed_acp = ACPPreference.query.filter_by(is_completed=True).count()
        completion_rate = (completed_acp / total_patients * 100.0) if total_patients > 0 else 0.0

        # Generated AMD stats (Active vs Superseded/Revoked)
        amd_status_stats = db.session.query(
            GeneratedAMD.status, func.count(GeneratedAMD.id)
        ).group_by(GeneratedAMD.status).all()
        amd_statistics = {status: count for status, count in amd_status_stats}

        # Recent activities (Latest 10 audit logs)
        recent_logs = db.session.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(10).all()
        recent_activities = []
        for log in recent_logs:
            performer = User.query.get(log.performed_by)
            recent_activities.append({
                'id': log.id,
                'patient_id': log.patient_id,
                'action': log.action,
                'performed_by': performer.full_name if performer else 'System',
                'timestamp': log.timestamp.isoformat(),
                'remarks': log.remarks
            })

        return {
            'total_patients': total_patients,
            'total_acp_preferences': total_acp,
            'total_dhrs': total_dhr,
            'total_amd_documents': total_amd,
            'preferred_languages': languages_count,
            'acp_completed_count': completed_acp,
            'acp_completion_rate_percentage': round(completion_rate, 2),
            'generated_amd_statistics': amd_statistics,
            'recent_activities': recent_activities
        }
