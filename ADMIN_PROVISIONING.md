# ACP Care — Admin Portal Provisioning Guide

## Overview

The ACP Care application has three completely separate portals:

| Portal | Route | Registration |
|---|---|---|
| Patient Portal | `/` (login), `/register` | Public self-registration (role always `patient`) |
| Doctor Portal | `/doctor-login` | No public registration — Admin creates accounts |
| Admin Portal | `/admin-login` | No public registration — CLI provisioning only |

---

## 1. Creating the First Admin Account

Admin accounts are created using a secure server-side CLI script. There is **no public registration endpoint** for admins.

### Prerequisites

- Python installed with access to the project
- The database must be initialized (run the app at least once)

### Command

```powershell
cd C:\ACP_System
python -m backend.database.create_admin `
  --email admin@acpcare.com `
  --name "Admin Name" `
  --password "SecureAdmin123!"
```

### Password Requirements

- Minimum **8 characters**
- Choose a strong, unique password — it is hashed with bcrypt before storage

### What the script does

1. Checks the database is reachable
2. Rejects if an account with that email already exists
3. Hashes the password using bcrypt (same mechanism as patient/doctor accounts)
4. Creates a `User` record with `role = 'admin'`
5. Prints confirmation

> **Security note:** The script never stores or echoes the password in plaintext.  
> The `role = 'admin'` value is set server-side — it cannot be submitted or overridden by any client request.

---

## 2. Logging In as Admin

1. Navigate to `/admin-login`
2. Enter the email and password provisioned in Step 1
3. On success, you are redirected to `/admin-dashboard`

---

## 3. Admin Dashboard

`/admin-dashboard` displays:

- **Total registered patients**
- **Total registered doctors**
- **Active doctors**
- **Inactive doctors**

Navigation sidebar:

| Item | Route |
|---|---|
| Dashboard | `/admin-dashboard` |
| Manage Doctors | `/admin-dashboard/doctors` |
| Add Doctor | `/admin-dashboard/doctors/add` |
| Manage Patients | `/admin-dashboard/patients` |
| Account Settings | `/admin-dashboard/settings` |
| Logout | Clears session |

---

## 4. Creating a Doctor Account (Admin Workflow)

Only an authenticated admin can create doctor accounts.

### Steps

1. Log in to the Admin Portal at `/admin-login`
2. Navigate to **Add Doctor** (`/admin-dashboard/doctors/add`)
3. Fill in the form:
   - Doctor Full Name *(required)*
   - Email Address *(required, must be unique)*
   - Mobile Number *(optional)*
   - Medical Specialization *(optional)*
   - Hospital / Institution *(optional)*
   - Medical Registration Number *(optional)*
4. Click **Create Doctor Account**

### What happens on the backend

1. Input is validated (name and email required, email uniqueness checked)
2. A **secure 16-character temporary password** is auto-generated (uppercase + lowercase + digits + symbols)
3. The password is **hashed with bcrypt** before storage — plaintext is never persisted
4. A `User` record is created with `role = 'doctor'`
5. A `DoctorProfile` record is created (linked to the user, `is_active = True`)
6. The plaintext temporary password is returned **once** in the success response

### Sharing the temporary password

After creation, the Admin Portal reveals the temporary password **once** in the UI (with a copy button).

> **The admin must copy and share this password with the doctor out-of-band** (e.g., a secure internal message, encrypted email, or direct verbal communication).

The doctor then:
1. Logs in at `/doctor-login` with the temporary password
2. Changes their password via Account Settings

> **The temporary password is not emailed automatically.** If email delivery is not configured, the admin is responsible for securely sharing it.

---

## 5. Managing Doctor Accounts

### View all doctors

Go to `/admin-dashboard/doctors` — search by name or email, see status (Active / Inactive).

### View doctor details

Click the **eye icon** next to a doctor → `/admin-dashboard/doctors/$userId`

### Edit doctor profile

Click the **pencil icon** → `/admin-dashboard/doctors/$userId/edit`

Fields editable: Full Name, Mobile Number, Specialization, Hospital, Medical Registration Number.  
Email is **read-only** (identity field, cannot be changed by admin).

### Activate / Deactivate a doctor

Click the **green ✓** (activate) or **red ✗** (deactivate) icon in the doctors table.

- **Deactivated doctors cannot log in** — the backend returns HTTP 401 with "account has been deactivated" at login time
- Their existing data and patient ACP records are preserved

---

## 6. Security Architecture

### Role assignment

| Portal | How role is assigned |
|---|---|
| Patient registration | Backend always assigns `role = 'patient'`; client cannot send or override role |
| Doctor creation | Admin Portal API assigns `role = 'doctor'`; endpoint requires `@role_required(['admin'])` |
| Admin creation | CLI script assigns `role = 'admin'`; no HTTP endpoint exists |

### API protection

All `/api/admin/*` routes require two decorators:

```python
@token_required          # valid JWT must be present
@role_required(['admin']) # token must belong to an admin account
```

Patients and doctors receive **HTTP 403 Forbidden** if they attempt to call admin endpoints.

### Deactivated doctor enforcement

`auth_controller.py` calls `AdminService.is_doctor_active(user.id)` before issuing a JWT.  
If the doctor's `DoctorProfile.is_active` is `False`, the login is rejected with HTTP 401.

### No privilege escalation

- `POST /api/auth/register` strips any `role` field before processing — always assigns `'patient'`
- `PUT /api/auth/profile` does not accept a `role` field — users cannot change their own role
- Admin, doctor, and patient data are siloed: each role can only access their own endpoints

---

## 7. Routes Summary

### Public routes (no auth required)

| Route | Purpose |
|---|---|
| `/` | Patient login |
| `/register` | Patient self-registration |
| `/doctor-login` | Doctor login (no public registration) |
| `/admin-login` | Admin login (no public registration) |

### Patient routes (role: `patient`)

| Route | Purpose |
|---|---|
| `/patient-dashboard` | Patient home |
| `/patient-dashboard/acp/*` | ACP chatbot sections |
| `/patient-dashboard/documents` | AMD document download |
| `/patient-dashboard/settings` | Patient profile settings |

### Doctor routes (role: `doctor`)

| Route | Purpose |
|---|---|
| `/doctor-dashboard` | Doctor home |
| `/doctor-dashboard/patients` | Patient list |
| `/doctor-dashboard/patients/$patientId` | Patient ACP review |
| `/doctor-dashboard/settings` | Doctor profile settings |

### Admin routes (role: `admin`)

| Route | Purpose |
|---|---|
| `/admin-dashboard` | Stats dashboard |
| `/admin-dashboard/doctors` | Manage doctors |
| `/admin-dashboard/doctors/add` | Add new doctor |
| `/admin-dashboard/doctors/$userId` | Doctor detail view |
| `/admin-dashboard/doctors/$userId/edit` | Edit doctor profile |
| `/admin-dashboard/patients` | Read-only patient list |
| `/admin-dashboard/settings` | Admin account settings |

---

## 8. Files Added or Modified

### New files

| File | Purpose |
|---|---|
| `backend/models/doctor_profile.py` | `DoctorProfile` ORM model |
| `backend/services/admin_service.py` | Admin business logic |
| `backend/controllers/admin_controller.py` | Admin HTTP handlers |
| `backend/database/create_admin.py` | CLI for first-admin provisioning |
| `backend/database/create_doctor.py` | CLI for doctor provisioning (delegates to AdminService) |
| `backend/tests/test_admin_portal.py` | 20 admin portal tests |
| `frontend/src/components/admin-shell.tsx` | Admin layout with sidebar |
| `frontend/src/routes/admin-login.tsx` | Admin login page |
| `frontend/src/routes/admin-dashboard.tsx` | Admin dashboard layout route |
| `frontend/src/routes/admin-dashboard.index.tsx` | Stats dashboard page |
| `frontend/src/routes/admin-dashboard.doctors.tsx` | Manage doctors page |
| `frontend/src/routes/admin-dashboard.doctors.add.tsx` | Add doctor form |
| `frontend/src/routes/admin-dashboard.doctors.$userId.tsx` | Doctor detail view |
| `frontend/src/routes/admin-dashboard.doctors.$userId.edit.tsx` | Edit doctor form |
| `frontend/src/routes/admin-dashboard.patients.tsx` | Read-only patient list |
| `frontend/src/routes/admin-dashboard.settings.tsx` | Admin account settings |
| `DOCTOR_PROVISIONING.md` | Doctor provisioning guide |
| `ADMIN_PROVISIONING.md` | This file |

### Modified files

| File | Change |
|---|---|
| `backend/models/__init__.py` | Imports `DoctorProfile` |
| `backend/models/user.py` | Added `doctor_profile` relationship |
| `backend/controllers/auth_controller.py` | Blocks deactivated doctor login |
| `backend/routes/api.py` | Registers `/api/admin/*` routes |
| `frontend/src/lib/api.ts` | Added `adminService` |
| `frontend/src/components/app-sidebar.tsx` | Added admin nav, extended role union type |
| `frontend/src/components/require-authentication.tsx` | Smart cross-role redirect |
| `frontend/src/routes/index.tsx` | Added "System administrator? Admin Portal →" link |

---

## 9. Test Coverage

```
backend/tests/test_admin_portal.py      20/20 PASS
backend/tests/test_rbac_security.py     15/15 PASS
backend/tests/test_ai_integration.py    23/23 PASS
backend/tests/test_amd_pdf.py           13/13 PASS
backend/tests/test_restart_and_edit...   4/4  PASS
backend/tests/test_questionnaire_val...  4/4  PASS
backend/tests/test_questionnaire_reg... 15/15 PASS
─────────────────────────────────────────────
TOTAL                                   94/94 PASS
```

