# ACP chatbot question-to-data audit

This map covers the conversational questions and final review action as implemented by `backend/services/ai_service.py`. Q1–Q20 are also defined in the standalone AI service. Q21–Q35 are conditional backend follow-ups. The standard patient ACP workflow remains six sections.

| Q | Question (English) | Canonical database field | Persistence and retrieval | Doctor detail dashboard | AMD PDF | Disposition |
|---|---|---|---|---|---|---|
| 1 | What is your full name? | `users.full_name` | Persisted and retrieved | Yes | Yes | Retain |
| 2 | What is your date of birth? | `patients.date_of_birth` (age derived) | Persisted when parseable and retrieved | Yes | Yes | Retain |
| 3 | What is your gender? | `patients.gender` | Persisted and retrieved | Yes | Yes | Retain |
| 4 | Who should make healthcare decisions for you if you cannot? | `dhrs.full_name` (rank 1) | Persisted and retrieved | Yes | Yes | Retain |
| 5 | What is your relationship with this person? | `dhrs.relationship` (rank 1) | Persisted and retrieved | Yes | Yes | Retain |
| 6 | Do you have chronic medical conditions? | `patients.chronic_conditions` | Persisted and retrieved; legacy tagged answers backfilled by migration | Labelled medical history | Relevant background field | Retain |
| 7 | Have you had a serious hospitalization or major illness? | `patients.serious_hospitalization` | Persisted and retrieved; legacy tagged answers backfilled | Labelled medical history | Relevant background field | Retain |
| 8 | Are you taking long-term medications? | `patients.long_term_medications` | Persisted and retrieved; legacy tagged answers backfilled | Labelled medical history | Relevant background field | Retain |
| 9 | Do you have known allergies? | `patients.allergies` | Persisted and retrieved; legacy tagged answers backfilled | Labelled medical history | Relevant background field | Retain |
| 10 | If your heart stops, would you want CPR? | `acp_preferences.cpr_preference` | Yes; WANT / DO NOT WANT / UNSURE retained | Yes | Yes | Retain |
| 11 | If you cannot breathe, would you want a ventilator? | `acp_preferences.ventilator_preference` | Yes; UNSURE retained | Yes | Yes | Retain |
| 12 | If your kidneys stop working, would you want dialysis? | `acp_preferences.dialysis_preference` | Yes; UNSURE retained | Yes | Yes | Retain |
| 13 | Would you want artificial nutrition / feeding tube? | `acp_preferences.nutrition_hydration_preference` | Yes; UNSURE retained | Yes, separate label | Yes, separate row | Retain; distinct from hydration |
| 14 | Would you want artificial hydration by tube or vein? | `acp_preferences.iv_fluids_preference` | Yes; UNSURE retained | Yes, separate label | Yes, separate row | Retain; distinct from nutrition |
| 15 | Would you donate your organs after death? | `acp_preferences.organ_donation` | Yes; Yes / No / Unsure retained | Yes | Yes | Retain |
| 16 | What are your main goals of care? | `acp_preferences.goals_of_care` | Persisted and retrieved separately | Yes | Yes, care-preferences section | Retain; separate from pain relief |
| 17 | Where would you prefer care for serious illness? | `acp_preferences.preferred_place_of_care` | Persisted and retrieved; No preference / Unsure preserved | Yes | Yes | Retain |
| 18 | What level of medical intervention would you prefer? | `acp_preferences.special_focus_priority` | Persisted and retrieved; Unsure preserved | Yes | Yes | Retain; distinct from Q16 |
| 19 | What personal goal or value should your team understand? | `patients.personal_values` | Persisted and retrieved separately | Yes | Yes, personal-values section | Retain; distinct from clinical history |
| 20 | Any additional wishes or instructions? | `acp_preferences.additional_wishes` | Persisted and retrieved | Yes | Yes | Retain |
| 21 | Primary representative's mobile phone | `dhrs.mobile_primary` (rank 1) | Persisted and retrieved | Yes | Yes | Retain for representative contact |
| 22 | Primary representative's email | `dhrs.email_primary` (rank 1) | Persisted when supplied; Skip accepted | Yes when supplied | Yes when supplied | Optional |
| 23 | Appoint an alternate representative? | `acp_preferences.alternate_dhr_appointed` | Explicit Yes / No persisted and retrieved | Yes | Reflected through alternate DHR designation / absence | Retain; makes alternate details conditional |
| 24 | Alternate representative's full name | `dhrs.full_name` (rank 2) | Persisted and retrieved when appointed | Yes | Yes | Conditional on Q23=Yes |
| 25 | Relationship with alternate representative | `dhrs.relationship` (rank 2) | Persisted and retrieved | Yes | Yes | Conditional on Q23=Yes |
| 26 | Alternate representative's mobile phone | `dhrs.mobile_primary` (rank 2) | Persisted and retrieved | Yes | Yes | Conditional on Q23=Yes |
| 27 | Alternate representative's email | `dhrs.email_primary` (rank 2) | Optional; Skip accepted | Yes when supplied | Yes when supplied | Optional, conditional on Q23=Yes |
| 28 | What is your contact phone number? | `patients.phone` | Persisted and retrieved; only asked when profile lacks phone | Yes | Yes | Retain; avoid duplicate prompt |
| 29 | What is your residential address? | `patients.address` (also permanent address if empty) | Persisted and retrieved; only asked when profile lacks address | Yes | Yes | Retain for patient/contact and execution details |
| 30 | Would you donate your body for education/research? | `acp_preferences.body_donation` | Yes; Yes / No / Unsure retained | Yes | Yes | Retain |
| 31 | Preferred hospital/facility? | `acp_preferences.preferred_hospital` | Persisted and retrieved; No preference preserved | Yes | Yes | Optional, retain |
| 32 | Any specific spiritual/cultural/funeral wishes? | `acp_preferences.last_rites` | Persisted and retrieved; explicit No specific wishes preserved | Yes | Yes | Optional, retain |
| 33 | Preference regarding chemotherapy? | `acp_preferences.chemotherapy_preference` | Yes; WANT / DO NOT WANT / UNSURE retained | Yes | Yes | Retain |
| 34 | Preference regarding radiotherapy? | `acp_preferences.radiotherapy_preference` | Yes; WANT / DO NOT WANT / UNSURE retained | Yes | Yes | Retain |
| 35 | Preference regarding major surgery? | `acp_preferences.surgery_preference` | Yes; WANT / DO NOT WANT / UNSURE retained | Yes | Yes | Retain |
| 36 | Review, confirm, or choose a section to edit | `acp_preferences.is_completed`, `completed_at`, `review_status`; session question state | Explicit confirmation retained; no auto-completion | Yes | Gates generation; preserves existing witness/generation workflow | Retain |

## Notes

- The eight life-sustaining treatment choices are Q10–Q14 and Q33–Q35. Their database fields, doctor cards, and AMD rows remain separate. `UNSURE` is no longer collapsed into `NOT SPECIFIED` for Q10–Q14.
- Q13 artificial nutrition and Q14 artificial hydration are clinically distinct; both remain.
- The old `patients.beliefs_values` field remains for compatibility with existing profile notes. The SQL migration only extracts legacy answers with explicit chatbot labels and does not infer missing values.
- Q22 and Q27 email answers can be skipped. Q28–Q29 are only prompted when existing patient profile data is absent. Preferred hospital and funeral wishes remain optional and are never filled with assumed preferences.
- Apply `backend/database/migrations/20261023_questionnaire_data_mapping.sql` to the existing PostgreSQL database before deploying the code. Fresh databases receive the fields through the model metadata.
