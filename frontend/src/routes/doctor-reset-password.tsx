import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Stethoscope,
  KeyRound,
  Eye,
  EyeOff,
  CheckCircle2,
  AlertCircle,
  Lock,
  ArrowLeft,
  ShieldCheck,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { doctorService, ApiError } from "@/lib/api";
import { toast } from "sonner";

export const Route = createFileRoute("/doctor-reset-password")({
  validateSearch: (search: Record<string, unknown>) => ({
    token: typeof search.token === "string" ? search.token : "",
  }),
  head: () => ({
    meta: [
      { title: "Set New Password — Doctor Portal" },
      {
        name: "description",
        content: "Choose a new secure password for your ACP Care Doctor Portal account.",
      },
    ],
  }),
  component: DoctorResetPasswordPage,
});

function FieldIcon({ children }: { children: React.ReactNode }) {
  return (
    <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
      {children}
    </span>
  );
}

function DoctorResetPasswordPage() {
  const { token } = Route.useSearch();
  const navigate = useNavigate();

  const [validating, setValidating] = useState(true);
  const [tokenValid, setTokenValid] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [doctorInfo, setDoctorInfo] = useState<{ email?: string; full_name?: string } | null>(null);

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function checkToken() {
      if (!token) {
        if (isMounted) {
          setValidating(false);
          setTokenValid(false);
          setValidationError("No password reset token was provided in the link.");
        }
        return;
      }

      try {
        const res = await doctorService.validateResetToken(token);
        if (isMounted) {
          if (res.valid) {
            setTokenValid(true);
            setDoctorInfo({ email: res.email, full_name: res.full_name });
          } else {
            setTokenValid(false);
            setValidationError(res.message || "This password reset link is invalid or has expired.");
          }
        }
      } catch (err: unknown) {
        if (isMounted) {
          setTokenValid(false);
          const msg = err instanceof Error ? err.message : "Invalid or expired reset link.";
          setValidationError(msg);
        }
      } finally {
        if (isMounted) {
          setValidating(false);
        }
      }
    }

    checkToken();
    return () => {
      isMounted = false;
    };
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!newPassword || newPassword.length < 6) {
      toast.error("Password must be at least 6 characters long.");
      return;
    }

    if (newPassword !== confirmPassword) {
      toast.error("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      const res = await doctorService.resetPassword({
        token,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });

      setIsSuccess(true);
      toast.success(res.message || "Password reset successfully!");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to reset password.";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-background px-4 py-12 sm:px-6">
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="w-full max-w-md"
      >
        {/* Brand Header */}
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-brand-gradient text-white shadow-lg">
            <Stethoscope className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Doctor Portal</h1>
          <p className="mt-1 text-sm text-muted-foreground">Secure password recovery</p>
        </div>

        <div className="rounded-3xl border border-border bg-card p-6 shadow-xl sm:p-8">
          {/* 1. Loading State */}
          {validating && (
            <div className="py-10 text-center">
              <Loader2 className="mx-auto h-8 w-8 animate-spin text-primary" />
              <p className="mt-3 text-sm text-muted-foreground">
                Verifying secure reset link...
              </p>
            </div>
          )}

          {/* 2. Success State */}
          {!validating && isSuccess && (
            <div className="space-y-5 text-center">
              <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-emerald-100 text-emerald-600">
                <CheckCircle2 className="h-6 w-6" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-foreground">Password Reset Complete</h2>
                <p className="mt-2 text-sm text-muted-foreground">
                  Your doctor account password has been updated. You can now sign in with your new password.
                </p>
              </div>

              <div className="pt-2">
                <Button
                  onClick={() => navigate({ to: "/doctor-login" })}
                  className="w-full rounded-xl bg-primary font-semibold text-primary-foreground shadow hover:bg-primary/90"
                >
                  Sign In to Doctor Portal
                </Button>
              </div>
            </div>
          )}

          {/* 3. Invalid / Expired Token State */}
          {!validating && !isSuccess && !tokenValid && (
            <div className="space-y-5 text-center">
              <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-destructive/10 text-destructive">
                <AlertCircle className="h-6 w-6" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-foreground">Link Invalid or Expired</h2>
                <p className="mt-2 text-sm text-muted-foreground">
                  {validationError ||
                    "This password reset link is invalid, expired, or has already been used."}
                </p>
              </div>

              <div className="flex flex-col gap-2 pt-2">
                <Button asChild className="w-full rounded-xl bg-primary">
                  <Link to="/doctor-forgot-password">Request a New Reset Link</Link>
                </Button>

                <Button asChild variant="ghost" className="w-full rounded-xl">
                  <Link to="/doctor-login">
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back to Doctor Sign In
                  </Link>
                </Button>
              </div>
            </div>
          )}

          {/* 4. Valid Token: Reset Form */}
          {!validating && !isSuccess && tokenValid && (
            <div>
              <div className="mb-5">
                <h2 className="text-xl font-bold tracking-tight text-foreground">
                  Choose New Password
                </h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  Resetting credentials for{" "}
                  <span className="font-semibold text-foreground">
                    {doctorInfo?.full_name ? `Dr. ${doctorInfo.full_name}` : "Doctor"}
                  </span>
                  {doctorInfo?.email && (
                    <span className="block text-muted-foreground">({doctorInfo.email})</span>
                  )}
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                {/* New Password */}
                <div className="space-y-1.5">
                  <Label htmlFor="doc-new-pass" className="text-xs font-medium">
                    New Password
                  </Label>
                  <div className="relative">
                    <FieldIcon>
                      <KeyRound className="h-4 w-4" />
                    </FieldIcon>
                    <Input
                      id="doc-new-pass"
                      type={showNew ? "text" : "password"}
                      placeholder="Minimum 6 characters"
                      className="h-11 rounded-xl px-9"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      required
                      autoFocus
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
                  <Label htmlFor="doc-confirm-pass" className="text-xs font-medium">
                    Confirm New Password
                  </Label>
                  <div className="relative">
                    <FieldIcon>
                      <Lock className="h-4 w-4" />
                    </FieldIcon>
                    <Input
                      id="doc-confirm-pass"
                      type={showConfirm ? "text" : "password"}
                      placeholder="Re-enter new password"
                      className="h-11 rounded-xl px-9"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
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

                {/* Requirements indicator */}
                <div className="rounded-xl border border-border bg-muted/40 p-3 text-[11px] text-muted-foreground space-y-1">
                  <div className="flex items-center gap-1.5">
                    <ShieldCheck
                      className={`h-3.5 w-3.5 ${newPassword.length >= 6 ? "text-emerald-600" : "text-muted-foreground"}`}
                    />
                    <span>At least 6 characters</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <ShieldCheck
                      className={`h-3.5 w-3.5 ${newPassword && newPassword === confirmPassword ? "text-emerald-600" : "text-muted-foreground"}`}
                    />
                    <span>Passwords match</span>
                  </div>
                </div>

                <Button
                  type="submit"
                  disabled={submitting || !newPassword || !confirmPassword}
                  className="h-11 w-full rounded-xl bg-primary font-semibold text-primary-foreground shadow transition hover:bg-primary/90 disabled:opacity-50"
                >
                  {submitting ? "Updating Password..." : "Set New Password"}
                </Button>
              </form>

              <div className="mt-5 text-center">
                <Link
                  to="/doctor-login"
                  className="inline-flex items-center text-xs font-medium text-muted-foreground hover:text-foreground transition"
                >
                  <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
                  Cancel and Return to Sign In
                </Link>
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}

