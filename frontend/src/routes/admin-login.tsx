import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { motion } from "framer-motion";
import {
  ShieldCheck,
  Mail,
  KeyRound,
  Eye,
  EyeOff,
  Lock,
  BarChart3,
  Users,
  ClipboardList,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authService } from "@/lib/api";
import { toast } from "sonner";

export const Route = createFileRoute("/admin-login")({
  head: () => ({
    meta: [
      { title: "Admin Portal — ACP Care" },
      {
        name: "description",
        content: "Secure administrator sign-in portal for ACP Care system management.",
      },
    ],
  }),
  component: AdminLoginPage,
});

const adminFeatures = [
  {
    icon: Users,
    title: "Doctor Management",
    body: "Create, activate, and deactivate authorized doctor accounts.",
  },
  {
    icon: ClipboardList,
    title: "Patient Overview",
    body: "Monitor patient registrations and account status at a glance.",
  },
  {
    icon: BarChart3,
    title: "System Analytics",
    body: "Track platform statistics and recent administrative activity.",
  },
];

function FieldIcon({ children }: { children: React.ReactNode }) {
  return (
    <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
      {children}
    </span>
  );
}

// ─── Admin Portal ──────────────────────────────────────────────────────────────
// Accepts ONLY accounts with role = "admin".
// Admin accounts are provisioned via the server-side CLI only.
// No public registration; no links to other portals.
function AdminLoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const user = await authService.login({ email, password });

      // Admin portal only: reject any non-admin account
      if (user.role !== "admin") {
        authService.logout();
        toast.error(
          "This portal is for administrators only. Please use your designated portal to sign in.",
        );
        setLoading(false);
        return;
      }

      toast.success("Welcome, Administrator!");
      setLoading(false);
      navigate({ to: "/admin-dashboard" });
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
            <ShieldCheck className="h-6 w-6" />
          </div>
          <div>
            <div className="text-lg font-bold leading-tight">ACP Care</div>
            <div className="text-xs text-white/80">Administrator Portal</div>
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
            System control,
            <br />
            secured by design.
          </motion.h1>
          <p className="mt-4 text-[15px] leading-relaxed text-white/85">
            Manage doctor accounts, monitor patient registrations, and oversee the ACP Care platform
            from one secure dashboard.
          </p>
        </div>

        {/* Feature cards */}
        <div className="relative mt-10 grid grid-cols-1 gap-3">
          {adminFeatures.map((f, i) => (
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
              Admin accounts are provisioned by server-side CLI only. No public registration is
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
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <div className="text-base font-bold">ACP Care</div>
                <div className="text-[11px] text-muted-foreground">Administrator Portal</div>
              </div>
            </div>
          </div>

          <div className="rounded-3xl border border-border bg-card p-8 shadow-[0_10px_40px_-20px_rgba(15,23,42,0.15)]">
            <div className="mb-6">
              <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs font-medium text-primary">
                <ShieldCheck className="h-3.5 w-3.5" />
                Administrator Portal
              </div>
              <h2 className="text-2xl font-bold tracking-tight text-foreground">Admin Sign In</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Sign in with your authorized administrator account.
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
                <Label htmlFor="admin-email" className="text-xs font-medium">
                  Email
                </Label>
                <div className="relative">
                  <FieldIcon>
                    <Mail className="h-4 w-4" />
                  </FieldIcon>
                  <Input
                    id="admin-email"
                    type="email"
                    placeholder="admin@acpcare.com"
                    className="h-11 rounded-xl pl-9"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
              </div>

              {/* Password */}
              <div className="space-y-1.5">
                <Label htmlFor="admin-password" className="text-xs font-medium">
                  Password
                </Label>
                <div className="relative">
                  <FieldIcon>
                    <KeyRound className="h-4 w-4" />
                  </FieldIcon>
                  <Input
                    id="admin-password"
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
                {loading ? "Signing in..." : "Sign in to Admin Portal"}
              </Button>
            </motion.form>
          </div>

          {/* No cross-portal navigation — this is a standalone admin portal */}
        </motion.div>
      </main>
    </div>
  );
}
