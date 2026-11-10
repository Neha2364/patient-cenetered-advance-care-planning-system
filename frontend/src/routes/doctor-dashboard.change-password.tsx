import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState } from "react";
import { motion } from "framer-motion";
import {
  KeyRound,
  Eye,
  EyeOff,
  ShieldCheck,
  AlertCircle,
  CheckCircle2,
  Lock,
  ArrowLeft,
  LogOut,
  Stethoscope,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authService } from "@/lib/api";
import { toast } from "sonner";
import { DoctorPageShell } from "@/components/doctor-page-shell";

export const Route = createFileRoute("/doctor-dashboard/change-password")({
  head: () => ({
    meta: [
      { title: "Change Password — Doctor Portal" },
      {
        name: "description",
        content: "Update your ACP Care clinician account password securely.",
      },
    ],
  }),
  component: DoctorChangePasswordPage,
});

function FieldIcon({ children }: { children: React.ReactNode }) {
  return (
    <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
      {children}
    </span>
  );
}

function DoctorChangePasswordPage() {
  const user = authService.getCurrentUser();
  const isMandatory = Boolean(user?.must_change_password);

  if (isMandatory) {
    // Dedicated mandatory first-login screen without distracting sidebar links
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 px-4 py-12">
        <div className="w-full max-w-lg">
          <div className="mb-6 text-center">
            <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-brand-gradient text-white shadow-lg">
              <Stethoscope className="h-6 w-6" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              First-Login Password Change
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Welcome to ACP Care, {user?.full_name || "Doctor"}. Please replace your temporary
              password to secure your clinical portal.
            </p>
          </div>

          <div className="rounded-3xl border border-border bg-card p-6 shadow-xl sm:p-8">
            <div className="mb-6 rounded-2xl border border-amber-200 bg-amber-50/80 p-4 text-amber-900">
              <div className="flex items-start gap-3">
                <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
                <div className="text-xs leading-relaxed">
                  <span className="font-semibold">Security Requirement:</span> You were assigned a
                  temporary password by an administrator. You must set a personal password before
                  accessing patient records and advance care planning reviews.
                </div>
              </div>
            </div>

            <PasswordChangeForm isMandatory={true} />
          </div>

          <div className="mt-6 text-center">
            <button
              type="button"
              onClick={() => {
                authService.logout();
                window.location.href = "/doctor-login";
              }}
              className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-destructive transition-colors"
            >
              <LogOut className="h-3.5 w-3.5" />
              Sign out and return to login
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Voluntary change password within standard doctor dashboard shell
  return (
    <DoctorPageShell>
      <div className="mb-6">
        <Link
          to="/doctor-dashboard/settings"
          className="mb-3 inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Account Settings
        </Link>
        <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          Change Password
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Update your doctor account credentials to ensure patient data protection.
        </p>
      </div>

      <div className="max-w-xl rounded-3xl border border-border bg-card p-6 shadow-sm sm:p-8">
        <PasswordChangeForm isMandatory={false} />
      </div>
    </DoctorPageShell>
  );
}

function PasswordChangeForm({ isMandatory }: { isMandatory: boolean }) {
  const navigate = useNavigate();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const isMinLength = newPassword.length >= 6;
  const isMatching = newPassword.length > 0 && newPassword === confirmPassword;
  const isDistinct = newPassword.length > 0 && newPassword !== currentPassword;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!currentPassword) {
      setErrorMessage("Please enter your current/temporary password.");
      return;
    }

    if (newPassword.length < 6) {
      setErrorMessage("New password must be at least 6 characters long.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setErrorMessage("New password and confirmation do not match.");
      return;
    }

    if (newPassword === currentPassword) {
      setErrorMessage("New password must be different from your current temporary password.");
      return;
    }

    setLoading(true);
    try {
      await authService.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });

      toast.success(
        isMandatory
          ? "Password set successfully! Welcome to ACP Care Doctor Portal."
          : "Your password has been changed successfully.",
      );

      navigate({ to: "/doctor-dashboard" });
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : "Failed to update password. Please check your current password.";
      setErrorMessage(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {errorMessage && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-start gap-2.5 rounded-xl border border-destructive/20 bg-destructive/10 p-3 text-xs text-destructive"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{errorMessage}</span>
        </motion.div>
      )}

      {/* Current / Temporary Password */}
      <div className="space-y-1.5">
        <Label htmlFor="current-password" className="text-xs font-medium">
          {isMandatory ? "Current Temporary Password" : "Current Password"}
        </Label>
        <div className="relative">
          <FieldIcon>
            <KeyRound className="h-4 w-4" />
          </FieldIcon>
          <Input
            id="current-password"
            type={showCurrent ? "text" : "password"}
            placeholder="Enter your current password"
            className="h-11 rounded-xl px-9"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
          <button
            type="button"
            onClick={() => setShowCurrent((s) => !s)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            aria-label={showCurrent ? "Hide password" : "Show password"}
          >
            {showCurrent ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* New Password */}
      <div className="space-y-1.5">
        <Label htmlFor="new-password" className="text-xs font-medium">
          New Password
        </Label>
        <div className="relative">
          <FieldIcon>
            <Lock className="h-4 w-4" />
          </FieldIcon>
          <Input
            id="new-password"
            type={showNew ? "text" : "password"}
            placeholder="At least 6 characters"
            className="h-11 rounded-xl px-9"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            minLength={6}
            required
            autoComplete="new-password"
          />
          <button
            type="button"
            onClick={() => setShowNew((s) => !s)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            aria-label={showNew ? "Hide password" : "Show password"}
          >
            {showNew ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Confirm Password */}
      <div className="space-y-1.5">
        <Label htmlFor="confirm-password" className="text-xs font-medium">
          Confirm New Password
        </Label>
        <div className="relative">
          <FieldIcon>
            <ShieldCheck className="h-4 w-4" />
          </FieldIcon>
          <Input
            id="confirm-password"
            type={showConfirm ? "text" : "password"}
            placeholder="Re-enter your new password"
            className="h-11 rounded-xl px-9"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            minLength={6}
            required
            autoComplete="new-password"
          />
          <button
            type="button"
            onClick={() => setShowConfirm((s) => !s)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            aria-label={showConfirm ? "Hide password" : "Show password"}
          >
            {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Live validation checklist */}
      <div className="rounded-2xl border border-border bg-surface p-3 text-xs space-y-1.5">
        <div className="font-semibold text-foreground text-[11px] uppercase tracking-wider mb-1">
          Password Guidelines:
        </div>
        <div
          className={`flex items-center gap-2 ${isMinLength ? "text-emerald-600" : "text-muted-foreground"}`}
        >
          <CheckCircle2
            className={`h-3.5 w-3.5 ${isMinLength ? "text-emerald-600" : "text-muted-foreground/40"}`}
          />
          <span>At least 6 characters long</span>
        </div>
        <div
          className={`flex items-center gap-2 ${isMatching ? "text-emerald-600" : "text-muted-foreground"}`}
        >
          <CheckCircle2
            className={`h-3.5 w-3.5 ${isMatching ? "text-emerald-600" : "text-muted-foreground/40"}`}
          />
          <span>New password and confirmation match</span>
        </div>
        <div
          className={`flex items-center gap-2 ${isDistinct ? "text-emerald-600" : "text-muted-foreground"}`}
        >
          <CheckCircle2
            className={`h-3.5 w-3.5 ${isDistinct ? "text-emerald-600" : "text-muted-foreground/40"}`}
          />
          <span>Different from current temporary password</span>
        </div>
      </div>

      <Button
        type="submit"
        disabled={loading || !currentPassword || !isMinLength || !isMatching}
        className="h-12 w-full rounded-xl bg-primary text-base font-semibold text-primary-foreground shadow-md transition hover:bg-primary/90 disabled:opacity-50"
      >
        {loading
          ? "Updating Password..."
          : isMandatory
            ? "Save Password & Enter Dashboard"
            : "Update Password"}
      </Button>
    </form>
  );
}

