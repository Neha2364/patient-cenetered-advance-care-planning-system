# Doctor Account Provisioning Guide

> [!IMPORTANT]
> Doctor accounts can **only** be created by an authorized administrator using the CLI script below.
> There is **no public API endpoint** for doctor self-registration — by design.

---

## How to Create a Doctor Account

Run the following command directly on the server (with access to the project directory and database):

```powershell
cd C:\ACP_System
python -m backend.database.create_doctor `
  --email dr.name@hospital.com `
  --name "Dr. Full Name" `
  --password "SecurePassword123!"
```

### Requirements

| Requirement | Detail |
|---|---|
| **Access** | Must be run on the server — not via any API call |
| **Email** | Must be unique in the system |
| **Password** | Must be at least 6 characters |
| **Role** | Always set to `doctor` — not configurable at runtime |

### Example Output

```
✓ Doctor account created successfully.
  Email : dr.name@hospital.com
  Name  : Dr. Full Name
  Role  : doctor
  ID    : 42

The doctor can now sign in at the Doctor Portal (/doctor-login).
```

---

## Doctor Portal Sign-In

Once the account is created, the doctor signs in at:

```
/doctor-login
```

This is a **separate page** from the patient portal (`/`).

- Attempting to sign in with a patient account on this page shows an error and logs out automatically.
- The main patient login page (`/`) shows a **"Are you a doctor? Access Doctor Portal →"** link.

---

## Security Architecture

```
Public Registration (/api/auth/register)
  └── Always assigns role = 'patient'
  └── Any 'role' value sent by the client is silently stripped
  └── Patients cannot self-escalate to doctor or admin

Doctor Account Creation (CLI only)
  └── backend/database/create_doctor.py
  └── No REST endpoint — server access required
  └── Role hardcoded to 'doctor' in the script

Backend RBAC (all protected routes)
  └── @token_required  → verifies JWT, loads current user
  └── @role_required(['doctor','admin'])  → enforced on /api/doctor/* routes
  └── Patient endpoints check user_id ownership to prevent cross-patient reads
```

---

## Existing Accounts Are Preserved

- All existing patient accounts continue to work without re-registration.
- All existing doctor accounts continue to work without any change.
- No database migration is needed — `User.role` already defaults to `'patient'`.

---

## What Was Changed

| File | Change |
|---|---|
| `backend/schemas/user.py` | Removed `role` from `UserRegisterSchema` — clients can no longer supply a role |
| `backend/controllers/auth_controller.py` | Strips any client-supplied `role` before validation; hardcodes `role='patient'` |
| `backend/database/create_doctor.py` | **New** — secure CLI script for authorized doctor account creation |
| `frontend/src/routes/index.tsx` | Removed Role dropdown from Sign Up form; added "Access Doctor Portal →" link |
| `frontend/src/lib/api.ts` | `authService.register()` no longer sends `role` in payload |
| `frontend/src/routes/doctor-login.tsx` | **New** — separate Doctor Portal login page at `/doctor-login` |
| `frontend/src/components/require-authentication.tsx` | Extended with `allowedRoles` prop for role-based route guarding |
| `frontend/src/components/patient-shell.tsx` | Wraps layout in `<RequireAuthentication allowedRoles={["patient"]}>` |
| `frontend/src/routes/doctor-dashboard.tsx` | Added role guard — patients who land here are redirected |
| `backend/tests/test_rbac_security.py` | **New** — 15-test RBAC security test suite |

