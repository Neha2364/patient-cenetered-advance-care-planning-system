"""
ACP Progress and Workflow Status Calculator.
Provides uniform, reliable calculation across backend services, controllers, and APIs.
Enforces the 5 distinct clinical ACP workflow statuses:
- Not Started
- In Progress
- Completed – Not Submitted
- Pending Review
- Reviewed
"""
from datetime import datetime

def is_field_defined(val) -> bool:
    """Check if a field has a genuine, non-empty, non-placeholder value."""
    if val is None:
        return False
    s = str(val).strip()
    return s not in (
        '',
        'NOT SPECIFIED',
        'Pending',
        'Not Specified',
        'None',
        'Representative',
        'Alternate Representative'
    )

def resolve_acp_status(pref, completion_percentage: int) -> str:
    """
    Determine the clinical ACP workflow status based on actual database fields.

    Statuses:
      - 'Reviewed': Clinically reviewed and acknowledged by a doctor.
      - 'Pending Review': Patient has genuinely submitted ACP (is_completed=True or completed_at set) and awaits doctor review.
      - 'Completed – Not Submitted': Required sections complete (100%), but not yet submitted for clinical review.
      - 'In Progress': Partially completed ACP draft (1–99%).
      - 'Not Started': No ACP preferences saved (0%).
    """
    if pref and (pref.review_status == 'Reviewed' or getattr(pref, 'reviewed_by_doctor', None) is not None):
        return 'Reviewed'

    is_submitted = bool(pref and (pref.is_completed or getattr(pref, 'completed_at', None) is not None))

    if is_submitted and pref and pref.review_status == 'Pending Review':
        return 'Pending Review'

    if completion_percentage >= 100 and not is_submitted:
        return 'Completed – Not Submitted'

    if completion_percentage > 0 or (pref and any(
        is_field_defined(getattr(pref, col, None))
        for col in [
            'cpr_preference', 'ventilator_preference', 'dialysis_preference',
            'chemotherapy_preference', 'radiotherapy_preference', 'surgery_preference',
            'iv_fluids_preference', 'nutrition_hydration_preference',
            'goals_of_care', 'preferred_place_of_care', 'organ_donation', 'body_donation'
        ]
    )):
        return 'In Progress'

    return 'Not Started'

def calculate_patient_acp_progress(patient) -> dict:
    """
    Calculate ACP section completion, overall progress percentage, and workflow status
    for a given Patient model instance.

    Returns:
        {
            'completion_percentage': int (0 to 100),
            'section_progress': {
                'personal': int,
                'medical': int,
                'end_of_life': int,
                'proxy': int,
                'donation': int,
                'review': int
            },
            'is_completed': bool,
            'status': 'Not Started' | 'In Progress' | 'Completed – Not Submitted' | 'Pending Review' | 'Reviewed',
            'review_status': str,
            'last_updated': str (ISO format)
        }
    """
    pref = getattr(patient, 'acp_preferences', None)
    dhrs = getattr(patient, 'dhrs', None) or []
    user = getattr(patient, 'user', None)

    # Determine last updated timestamp from patient, preferences, or creation
    dates = []
    if getattr(patient, 'updated_at', None):
        dates.append(patient.updated_at)
    if getattr(patient, 'created_at', None):
        dates.append(patient.created_at)
    if pref:
        if getattr(pref, 'updated_at', None):
            dates.append(pref.updated_at)
        if getattr(pref, 'completed_at', None):
            dates.append(pref.completed_at)
    last_updated_dt = max(dates) if dates else datetime.utcnow()
    last_updated_iso = last_updated_dt.isoformat()

    # Check contact and clinical fields
    has_contact = (
        is_field_defined(getattr(patient, 'phone', None)) or
        is_field_defined(getattr(patient, 'address', None)) or
        is_field_defined(getattr(patient, 'permanent_address', None)) or
        is_field_defined(getattr(patient, 'current_address', None)) or
        is_field_defined(getattr(patient, 'beliefs_values', None)) or
        is_field_defined(getattr(patient, 'chronic_conditions', None))
    )

    if not pref and not has_contact:
        return {
            'completion_percentage': 0,
            'section_progress': {
                'personal': 0,
                'medical': 0,
                'end_of_life': 0,
                'proxy': 0,
                'donation': 0,
                'review': 0
            },
            'is_completed': False,
            'status': 'Not Started',
            'review_status': 'Not Started',
            'last_updated': last_updated_iso
        }

    # 1. Personal Information (5 key items)
    p_count = 0
    if is_field_defined(getattr(user, 'full_name', None)):
        p_count += 1
    if is_field_defined(getattr(patient, 'phone', None)):
        p_count += 1
    if (
        is_field_defined(getattr(patient, 'address', None)) or
        is_field_defined(getattr(patient, 'permanent_address', None)) or
        is_field_defined(getattr(patient, 'current_address', None))
    ):
        p_count += 1
    if (
        is_field_defined(getattr(patient, 'date_of_birth', None)) or
        (getattr(patient, 'age', None) is not None and patient.age > 0)
    ):
        p_count += 1
    if is_field_defined(getattr(patient, 'gender', None)):
        p_count += 1

    # If only account registration name is present and no clinical/contact fields, score is 0
    if p_count <= 1 and not has_contact:
        personal_score = 0
    else:
        personal_score = min(100, round((p_count / 5.0) * 100))

    # 2. Medical Preferences (8 life-sustaining treatment fields)
    treatment_fields = [
        'cpr_preference',
        'ventilator_preference',
        'dialysis_preference',
        'chemotherapy_preference',
        'radiotherapy_preference',
        'surgery_preference',
        'iv_fluids_preference',
        'nutrition_hydration_preference'
    ]
    med_count = sum(
        1 for f in treatment_fields
        if pref and is_field_defined(getattr(pref, f, None))
    )
    medical_score = min(100, round((med_count / 8.0) * 100))

    # 3. End-of-Life Preferences (4 directives)
    eol_fields = [
        getattr(pref, 'goals_of_care', None) if pref else None,
        getattr(pref, 'preferred_place_of_care', None) if pref else None,
        getattr(pref, 'special_focus_priority', None) if pref else None,
        getattr(patient, 'personal_values', None) or (getattr(pref, 'pain_management', None) if pref else None)
    ]
    eol_count = sum(1 for val in eol_fields if is_field_defined(val))
    eol_score = min(100, round((eol_count / 4.0) * 100))

    # 4. Proxy / DHR Representative
    proxy_score = 0
    if dhrs:
        primary = next((d for d in dhrs if getattr(d, 'preference_order', None) == 1), dhrs[0])
        has_primary_name = is_field_defined(getattr(primary, 'full_name', None))
        has_primary_rel = is_field_defined(getattr(primary, 'relationship', None))
        clean_phone = ''.join(filter(str.isdigit, str(getattr(primary, 'mobile_primary', '') or '')))
        has_primary_phone = is_field_defined(getattr(primary, 'mobile_primary', None)) and len(clean_phone) >= 10

        alt_appointed = getattr(pref, 'alternate_dhr_appointed', False) if pref else False
        alt = next((d for d in dhrs if getattr(d, 'preference_order', None) == 2), None)

        if not alt_appointed and not alt:
            proxy_score = round(([has_primary_name, has_primary_rel, has_primary_phone].count(True) / 3.0) * 100)
        else:
            has_alt_name = alt and is_field_defined(getattr(alt, 'full_name', None))
            has_alt_rel = alt and is_field_defined(getattr(alt, 'relationship', None))
            clean_alt_phone = ''.join(filter(str.isdigit, str(getattr(alt, 'mobile_primary', '') or '')))
            has_alt_phone = alt and is_field_defined(getattr(alt, 'mobile_primary', None)) and len(clean_alt_phone) >= 10
            count = [has_primary_name, has_primary_rel, has_primary_phone, has_alt_name, has_alt_rel, has_alt_phone].count(True)
            proxy_score = round((count / 6.0) * 100)

    # 5. Donation (Organ and Body donation directives)
    don_count = 0
    if pref and is_field_defined(getattr(pref, 'organ_donation', None)):
        don_count += 1
    if pref and is_field_defined(getattr(pref, 'body_donation', None)):
        don_count += 1
    donation_score = round((don_count / 2.0) * 100)

    # 6. Review & Overall Completion
    is_completed = bool(pref and pref.is_completed)

    if is_completed:
        review_score = 100
        overall = 100
    else:
        # Check if all required prior sections are complete
        all_prior_complete = (
            personal_score >= 100 and
            medical_score >= 100 and
            eol_score >= 100 and
            proxy_score >= 100 and
            donation_score >= 100
        )
        review_score = 50 if all_prior_complete else 0
        raw_avg = (personal_score + medical_score + eol_score + proxy_score + donation_score + review_score) / 6.0
        # If all sections are 100%, overall is 100% (Completed - Not Submitted)
        if all_prior_complete:
            overall = 100
        else:
            overall = min(99, max(0, round(raw_avg)))

    # Resolve the exact workflow status
    status = resolve_acp_status(pref, overall)

    return {
        'completion_percentage': overall,
        'section_progress': {
            'personal': personal_score,
            'medical': medical_score,
            'end_of_life': eol_score,
            'proxy': proxy_score,
            'donation': donation_score,
            'review': review_score
        },
        'is_completed': is_completed,
        'status': status,
        'review_status': status,
        'last_updated': last_updated_iso
    }
