from datetime import datetime, timedelta
from sqlalchemy import func
from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.acp_preference import ACPPreference
from backend.models.dhr import DHR
from backend.models.generated_amd import GeneratedAMD
from backend.models.audit_log import AuditLog
from backend.utils.acp_calculator import calculate_patient_acp_progress

class DashboardService:
    """Service layer dealing with doctor and admin dashboard analytics, queries, and search logic."""

    @staticmethod
    def search_and_filter_patients(search_query=None, language=None, is_completed=None, review_status=None, amd_generated=None):
        """Perform clinical queries to search and filter patient records."""
        # Explicitly join Patient and User models
        query = db.session.query(Patient).join(User, Patient.user_id == User.id)

        # 1. Text Search across name, email, and phone
        if search_query:
            search_pattern = f"%{search_query.strip()}%"
            query = query.filter(
                (User.full_name.ilike(search_pattern)) |
                (User.email.ilike(search_pattern)) |
                (Patient.phone.ilike(search_pattern))
            )

        # 2. Preferred Language Filter
        if language and language != 'all':
            query = query.filter(Patient.preferred_language == language)

        # 3. Completion flag filter
        if is_completed is not None:
            if is_completed:
                query = query.join(ACPPreference, Patient.patient_id == ACPPreference.patient_id).filter(
                    ACPPreference.is_completed == True
                )
            else:
                query = query.outerjoin(ACPPreference, Patient.patient_id == ACPPreference.patient_id).filter(
                    (ACPPreference.is_completed == False) | (ACPPreference.patient_id.is_(None))
                )

        if amd_generated is not None:
            query = query.join(ACPPreference, Patient.patient_id == ACPPreference.patient_id).filter(
                ACPPreference.amd_generated == amd_generated
            )

        patients = query.order_by(Patient.patient_id.asc()).all()

        # 4. Status Filter across the 5 distinct statuses:
        # 'Not Started', 'In Progress', 'Completed – Not Submitted', 'Pending Review', 'Reviewed'
        if review_status and review_status != 'all':
            target_status = review_status.strip()
            filtered = []
            for pat in patients:
                progress = calculate_patient_acp_progress(pat)
                pat_status = progress['status']
                if pat_status.lower() == target_status.lower() or (
                    target_status.lower() == 'incomplete' and pat_status in ('In Progress', 'Completed – Not Submitted', 'Not Started')
                ):
                    filtered.append(pat)
            return filtered

        return patients

    @staticmethod
    def get_doctor_dashboard_analytics(doctor_id=None):
        """Retrieve aggregated clinical analytics and distributions for the doctor portal."""
        patients = Patient.query.order_by(Patient.patient_id.asc()).all()

        total_patients = len(patients)
        status_counts = {
            'Not Started': 0,
            'In Progress': 0,
            'Completed – Not Submitted': 0,
            'Pending Review': 0,
            'Reviewed': 0
        }

        # Completion distribution buckets
        completion_dist = {
            '0–25%': 0,
            '26–50%': 0,
            '51–75%': 0,
            '76–99%': 0,
            '100%': 0
        }

        section_totals = {
            'personal': 0,
            'medical': 0,
            'end_of_life': 0,
            'proxy': 0,
            'donation': 0,
            'review': 0
        }

        stale_records_count = 0
        now = datetime.utcnow()
        fourteen_days_ago = now - timedelta(days=14)

        for pat in patients:
            metrics = calculate_patient_acp_progress(pat)
            comp_pct = metrics['completion_percentage']
            status = metrics['status']

            status_counts[status] = status_counts.get(status, 0) + 1

            # Completion distribution
            if comp_pct <= 25:
                completion_dist['0–25%'] += 1
            elif comp_pct <= 50:
                completion_dist['26–50%'] += 1
            elif comp_pct <= 75:
                completion_dist['51–75%'] += 1
            elif comp_pct < 100:
                completion_dist['76–99%'] += 1
            else:
                completion_dist['100%'] += 1

            # Section averages
            for sec_key, sec_val in metrics['section_progress'].items():
                section_totals[sec_key] = section_totals.get(sec_key, 0) + sec_val

            # Check for stale record (> 14 days without update)
            try:
                updated_dt = datetime.fromisoformat(metrics['last_updated'])
                if updated_dt < fourteen_days_ago:
                    stale_records_count += 1
            except Exception:
                pass

        section_averages = {}
        for sec_key, total_score in section_totals.items():
            section_averages[sec_key] = round(total_score / total_patients, 1) if total_patients > 0 else 0

        # Summary KPIs
        completed_acps = status_counts['Reviewed'] + status_counts['Pending Review'] + status_counts['Completed – Not Submitted']

        # Recent activities (Patient-linked Audit Logs)
        logs = (
            db.session.query(AuditLog)
            .filter(AuditLog.patient_id.isnot(None))
            .order_by(AuditLog.timestamp.desc())
            .limit(12)
            .all()
        )
        recent_activities = []
        for log in logs:
            pat = Patient.query.filter_by(patient_id=log.patient_id).first()
            patient_name = pat.user.full_name if (pat and pat.user) else f"Patient #{log.patient_id}"
            progress = calculate_patient_acp_progress(pat) if pat else None
            recent_activities.append({
                'id': log.id,
                'patient_id': log.patient_id,
                'patient_name': patient_name,
                'action': log.action,
                'timestamp': log.timestamp.isoformat(),
                'status': progress['status'] if progress else 'Not Started',
                'remarks': log.remarks
            })

        return {
            'summary': {
                'total_patients': total_patients,
                'pending_reviews': status_counts['Pending Review'],
                'reviewed_acps': status_counts['Reviewed'],
                'in_progress_acps': status_counts['In Progress'],
                'completed_not_submitted_acps': status_counts['Completed – Not Submitted'],
                'not_started_acps': status_counts['Not Started'],
                'completed_acps': completed_acps,
                'stale_records_count': stale_records_count
            },
            'completion_distribution': [
                {'range': '0–25%', 'count': completion_dist['0–25%']},
                {'range': '26–50%', 'count': completion_dist['26–50%']},
                {'range': '51–75%', 'count': completion_dist['51–75%']},
                {'range': '76–99%', 'count': completion_dist['76–99%']},
                {'range': '100%', 'count': completion_dist['100%']}
            ],
            'review_status_distribution': [
                {'status': 'Pending Review', 'count': status_counts['Pending Review']},
                {'status': 'Reviewed', 'count': status_counts['Reviewed']},
                {'status': 'In Progress', 'count': status_counts['In Progress']},
                {'status': 'Completed – Not Submitted', 'count': status_counts['Completed – Not Submitted']},
                {'status': 'Not Started', 'count': status_counts['Not Started']}
            ],
            'section_completion': [
                {'section': 'Personal Info', 'completion': section_averages.get('personal', 0), 'key': 'personal'},
                {'section': 'Medical Treatments', 'completion': section_averages.get('medical', 0), 'key': 'medical'},
                {'section': 'End-of-Life', 'completion': section_averages.get('end_of_life', 0), 'key': 'end_of_life'},
                {'section': 'Proxy (DHR)', 'completion': section_averages.get('proxy', 0), 'key': 'proxy'},
                {'section': 'Donation', 'completion': section_averages.get('donation', 0), 'key': 'donation'},
                {'section': 'Confirmation', 'completion': section_averages.get('review', 0), 'key': 'review'}
            ],
            'recent_activities': recent_activities,
            'status_counts': status_counts,
            'insights': {
                'awaiting_review': status_counts['Pending Review'],
                'in_progress': status_counts['In Progress'],
                'reviewed': status_counts['Reviewed'],
                'not_started': status_counts['Not Started'],
                'stale_records': stale_records_count
            }
        }

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
