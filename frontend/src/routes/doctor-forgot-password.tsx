import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { motion } from "framer-motion";
import {
  Stethoscope,
  Mail,
  ArrowLeft,
  AlertCircle,
  CheckCircle2,
  Lock,
  Send,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { doctorService, ApiError } from "@/lib/api";
import { toast } from "sonner";

export const Route = createFileRoute("/doctor-forgot-password")({
  head: () => ({
    meta: [
      { title: "Forgot Password — Doctor Portal" },
      {
        name: "description",
        content: "Request a secure, single-use password reset link for your ACP Care Doctor Portal account.",
      },
    ],
  }),
  component: DoctorForgotPasswordPage,
});

function FieldIcon({ children }: { children: React.ReactNode }) {
  return (
    <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
      {children}
    </span>
  );
}

function DoctorForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorType, setErrorType] = useState<"smtp_missing" | "temporary_password" | "generic" | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setErrorType(null);
    setLoading(true);

    try {
      const res = await doctorService.forgotPassword(email.trim());
      setSubmittedEmail(email.trim());
      toast.success(res.message || "Password reset link sent to your email.");
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
        if (err.status === 503 || err.message.toLowerCase().includes("not configured")) {
          setErrorType("smtp_missing");
        } else if (
          err.message.toLowerCase().includes("temporary password") ||
          err.message.toLowerCase().includes("first-time setup")
        ) {
          setErrorType("temporary_password");
        } else {
          setErrorType("generic");
        }
      } else {
        const msg = err instanceof Error ? err.message : "Failed to send reset link.";
        setErrorMessage(msg);
        setErrorType("generic");
      }
    } finally {
      setLoading(false);
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
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Doctor Portal
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Reset clinician account credentials
          </p>
        </div>

        <div className="rounded-3xl border border-border bg-card p-6 shadow-xl sm:p-8">
          {/* Success state */}
          {submittedEmail ? (
            <div className="space-y-5 text-center">
              <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-emerald-100 text-emerald-600">
                <CheckCircle2 className="h-6 w-6" />
              </div>

              <div>
                <h2 className="text-xl font-bold text-foreground">Reset Link Sent</h2>
                <p className="mt-2 text-sm text-muted-foreground">
                  If an active doctor account exists for{" "}
                  <span className="font-semibold text-foreground">{submittedEmail}</span>,
                  you will receive an email shortly with a secure link to reset your password.
                </p>
              </div>

              <div className="rounded-2xl border border-border bg-muted/40 p-3.5 text-xs text-muted-foreground">
                <p>The link is valid for <strong>60 minutes</strong> and can only be used once.</p>
              </div>

              <div className="flex flex-col gap-2 pt-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    setSubmittedEmail(null);
                    setErrorMessage(null);
                    setErrorType(null);
                  }}
                  className="w-full rounded-xl"
                >
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Try a different email
                </Button>

                <Button asChild variant="ghost" className="w-full rounded-xl">
                  <Link to="/doctor-login">
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back to Doctor Sign In
                  </Link>
                </Button>
              </div>
            </div>
          ) : (
            <div>
              <div className="mb-5">
                <h2 className="text-xl font-bold tracking-tight text-foreground">
                  Forgot Password?
                </h2>
                <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                  Enter your registered doctor email address. We will verify your account and email you a secure, time-limited reset link.
                </p>
              </div>

              {/* Explicit alert when email configuration is unavailable */}
              {errorType === "smtp_missing" && (
                <div className="mb-5 rounded-2xl border border-amber-300 bg-amber-50 p-4 text-amber-900">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
                    <div className="space-y-1">
                      <div className="text-xs font-semibold uppercase tracking-wider text-amber-800">
                        Email Service Not Configured
                      </div>
                      <div className="text-xs leading-relaxed">
                        {errorMessage ||
                          "Email delivery service is currently not configured on this server. Please contact your administrator to reset your password or configure SMTP settings."}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Informative alert when account still has temporary password */}
              {errorType === "temporary_password" && (
                <div className="mb-5 rounded-2xl border border-blue-200 bg-blue-50 p-4 text-blue-900">
                  <div className="flex items-start gap-3">
                    <Lock className="mt-0.5 h-5 w-5 shrink-0 text-blue-600" />
                    <div className="space-y-1">
                      <div className="text-xs font-semibold uppercase tracking-wider text-blue-800">
                        Temporary Password Issued
                      </div>
                      <div className="text-xs leading-relaxed">
                        {errorMessage}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Generic error message */}
              {errorType === "generic" && errorMessage && (
                <div className="mb-5 rounded-2xl border border-destructive/20 bg-destructive/10 p-4 text-destructive">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
                    <div className="text-xs leading-relaxed">{errorMessage}</div>
                  </div>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="doc-reset-email" className="text-xs font-medium">
                    Registered Doctor Email
                  </Label>
                  <div className="relative">
                    <FieldIcon>
                      <Mail className="h-4 w-4" />
                    </FieldIcon>
                    <Input
                      id="doc-reset-email"
                      type="email"
                      placeholder="doctor@hospital.com"
                      className="h-11 rounded-xl pl-9"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      autoFocus
                    />
                  </div>
                </div>

                <Button
                  type="submit"
                  disabled={loading || !email.trim()}
                  className="h-11 w-full rounded-xl bg-primary font-semibold text-primary-foreground shadow transition hover:bg-primary/90 disabled:opacity-50"
                >
                  {loading ? (
                    "Sending reset link..."
                  ) : (
                    <>
                      <Send className="mr-2 h-4 w-4" />
                      Send Reset Link
                    </>
                  )}
                </Button>
              </form>

              <div className="mt-6 text-center">
                <Link
                  to="/doctor-login"
                  className="inline-flex items-center text-xs font-medium text-muted-foreground hover:text-foreground transition"
                >
                  <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
                  Back to Doctor Sign In
                </Link>
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}

