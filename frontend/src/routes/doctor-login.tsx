import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Stethoscope,
  Mail,
  KeyRound,
  Eye,
  EyeOff,
  Lock,
  ShieldCheck,
  ClipboardCheck,
  Users,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authService } from "@/lib/api";
import { toast } from "sonner";

export const Route = createFileRoute("/doctor-login")({
  head: () => ({
    meta: [
      { title: "Doctor Portal — ACP Care" },
      {
        name: "description",
        content:
          "Secure sign-in portal for authorized ACP Care clinicians. Monitor patient ACP progress and review submissions.",
      },
    ],
  }),
  component: DoctorLoginPage,
});

const doctorFeatures = [
  {
    icon: Users,
    title: "Patient Management",
    body: "View all registered patients and their ACP completion status.",
  },
  {
    icon: ClipboardCheck,
    title: "ACP Review",
    body: "Review and co-sign patient Advance Care Plans.",
  },
  {
    icon: ShieldCheck,
    title: "Secure Access",
    body: "Role-protected portal — only authorized clinicians can sign in.",
  },
];

function FieldIcon({ children }: { children: React.ReactNode }) {
  return (
    <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
      {children}
    </span>
  );
}

// ─── Doctor Portal ─────────────────────────────────────────────────────────────
// Accepts ONLY accounts with role = "doctor".
// Patients must use / (patient portal). Admins must use /admin-login.
function DoctorLoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const user = authService.getCurrentUser();
    if (user && user.role === "doctor") {
      if (user.must_change_password) {
        navigate({ to: "/doctor-dashboard/change-password", replace: true });
      } else {
        navigate({ to: "/doctor-dashboard", replace: true });
      }
    }
  }, [navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const user = await authService.login({ email, password });

      // Doctor portal only: reject any non-doctor account
      if (user.role !== "doctor") {
        authService.logout();
        toast.error(
          "This portal is for authorized doctors only. Please use your designated portal to sign in.",
        );
        setLoading(false);
        return;
      }

      if (user.must_change_password) {
        toast.info("Temporary password detected. Please set a new password to continue.");
        setLoading(false);
        navigate({ to: "/doctor-dashboard/change-password" });
        return;
      }

      toast.success("Welcome, Doctor!");
      setLoading(false);
      navigate({ to: "/doctor-dashboard" });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Invalid credentials.";
      toast.error(msg);
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen w-full bg-background">
      {/* LEFT PANEL */}
      <aside className="relative hidden w-[38%] shrink-0 overflow-hidden bg-brand-gradient p-10 text-white lg:flex lg:flex-col xl:w-[34%]">
        <div className="pointer-events-none absolute -left-24 -top-24 h-72 w-72 rounded-full bg-white/10 blur-3xl" />
        <div className="pointer-events-none absolute -right-16 bottom-24 h-80 w-80 rounded-full bg-white/10 blur-3xl" />

        {/* Logo */}
        <div className="relative flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-xl bg-white/15 backdrop-blur">
            <Stethoscope className="h-6 w-6" />
          </div>
          <div>
            <div className="text-lg font-bold leading-tight">ACP Care</div>
            <div className="text-xs text-white/80">Doctor Portal</div>
          </div>
        </div>

        {/* Headline */}
        <div className="relative mt-14 max-w-md">
          <motion.h1
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="text-4xl font-bold leading-[1.1] tracking-tight xl:text-[42px]"
          >
            Clinician access,
            <br />
            secure by design.
          </motion.h1>
          <p className="mt-4 text-[15px] leading-relaxed text-white/85">
            Review patient Advance Care Plans, monitor progress, and support patients through their
            end-of-life planning journey.
          </p>
        </div>

        {/* Feature cards */}
        <div className="relative mt-10 grid grid-cols-1 gap-3">
          {doctorFeatures.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.06, duration: 0.4 }}
              className="glass-card flex items-start gap-3 rounded-2xl p-4 text-white"
            >
              <div className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-white/15">
                <f.icon className="h-4 w-4" />
              </div>
              <div>
                <div className="text-sm font-semibold">{f.title}</div>
                <div className="mt-0.5 text-[12px] leading-snug text-white/80">{f.body}</div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Security note */}
        <div className="relative mt-auto pt-8">
          <div className="glass-card flex items-center gap-3 rounded-2xl px-4 py-3">
            <Lock className="h-4 w-4 shrink-0" />
            <div className="text-xs text-white/90">
              Doctor accounts are created by administrators only. Public self-registration is not
              available.
            </div>
          </div>
        </div>
      </aside>

      {/* RIGHT PANEL */}
      <main className="flex flex-1 items-center justify-center px-6 py-12 sm:px-10">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="w-full max-w-[460px]"
        >
          {/* Mobile logo */}
          <div className="mb-8 lg:hidden">
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-brand-gradient text-white">
                <Stethoscope className="h-5 w-5" />
              </div>
              <div>
                <div className="text-base font-bold">ACP Care</div>
                <div className="text-[11px] text-muted-foreground">Doctor Portal</div>
              </div>
            </div>
          </div>

          <div className="rounded-3xl border border-border bg-card p-8 shadow-[0_10px_40px_-20px_rgba(15,23,42,0.15)]">
            <div className="mb-6">
              <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-medium text-primary">
                <Stethoscope className="h-3.5 w-3.5" />
                Doctor Portal
              </div>
              <h2 className="text-2xl font-bold tracking-tight text-foreground">
                Clinician Sign In
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Sign in with your authorized doctor account.
              </p>
            </div>

            <motion.form
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              onSubmit={handleSubmit}
              className="space-y-4"
            >
              {/* Email */}
              <div className="space-y-1.5">
                <Label htmlFor="doc-email" className="text-xs font-medium">
                  Email
                </Label>
                <div className="relative">
                  <FieldIcon>
                    <Mail className="h-4 w-4" />
                  </FieldIcon>
                  <Input
                    id="doc-email"
                    type="email"
                    placeholder="doctor@hospital.com"
                    className="h-11 rounded-xl pl-9"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
              </div>

              {/* Password */}
              <div className="space-y-1.5">
                <Label htmlFor="doc-password" className="text-xs font-medium">
                  Password
                </Label>
                <div className="relative">
                  <FieldIcon>
                    <KeyRound className="h-4 w-4" />
                  </FieldIcon>
                  <Input
                    id="doc-password"
                    type={show ? "text" : "password"}
                    placeholder="Enter your password"
                    className="h-11 rounded-xl px-9"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShow((s) => !s)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    aria-label={show ? "Hide password" : "Show password"}
                  >
                    {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <Button
                type="submit"
                disabled={loading}
                className="h-12 w-full rounded-xl bg-primary text-base font-semibold text-primary-foreground shadow-md transition hover:bg-primary/90 hover:shadow-lg disabled:opacity-50"
              >
                {loading ? "Signing in..." : "Sign in to Doctor Portal"}
              </Button>
            </motion.form>
          </div>

          {/* No cross-portal navigation — this is a standalone doctor portal */}
        </motion.div>
      </main>
    </div>
  );
}
