import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain,
  FileCheck2,
  ShieldCheck,
  Languages,
  Lock,
  HeartPulse,
  Mail,
  KeyRound,
  User,
  Eye,
  EyeOff,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { authService } from "@/lib/api";
import { toast } from "sonner";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Sign in — ACP Care" },
      {
        name: "description",
        content:
          "Sign in or create an ACP Care account to begin your Advance Care Planning journey with AI-guided, private, multilingual support.",
      },
    ],
  }),
  component: AuthPage,
});

const features = [
  {
    icon: Brain,
    title: "AI Guided Planning",
    body: "Conversational prompts help you articulate your wishes at your own pace.",
  },
  {
    icon: FileCheck2,
    title: "Legal Document Generation",
    body: "Turn answers into a formatted Living Will and Advance Directive.",
  },
  {
    icon: ShieldCheck,
    title: "Secure & Private",
    body: "Your responses stay private with end-to-end encryption.",
  },
  {
    icon: Languages,
    title: "Multilingual Support",
    body: "Plan in the language that feels most natural to you.",
  },
];

function AuthPage() {
  const [tab, setTab] = useState<"signin" | "signup">("signin");
  const navigate = useNavigate();



  return (
    <div className="flex min-h-screen w-full bg-background">
      {/* LEFT PANEL */}
      <aside className="relative hidden w-[38%] shrink-0 overflow-hidden bg-brand-gradient p-10 text-white lg:flex lg:flex-col xl:w-[34%]">
        <div className="pointer-events-none absolute -left-24 -top-24 h-72 w-72 rounded-full bg-white/10 blur-3xl" />
        <div className="pointer-events-none absolute -right-16 bottom-24 h-80 w-80 rounded-full bg-white/10 blur-3xl" />

        <div className="relative flex items-center gap-3">
          <div className="grid h-11 w-11 place-items-center rounded-xl bg-white/15 backdrop-blur">
            <HeartPulse className="h-6 w-6" />
          </div>
          <div>
            <div className="text-lg font-bold leading-tight">ACP Care</div>
            <div className="text-xs text-white/80">Advance Care Planning</div>
          </div>
        </div>

        <div className="relative mt-14 max-w-md">
          <motion.h1
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="text-4xl font-bold leading-[1.1] tracking-tight xl:text-[42px]"
          >
            Your voice,
            <br />
            when it matters most.
          </motion.h1>
          <p className="mt-4 text-[15px] leading-relaxed text-white/85">
            ACP Care helps you plan the care you want with clarity, dignity, and confidence — guided
            by AI, protected by design.
          </p>
        </div>

        <div className="relative mt-10 grid grid-cols-2 gap-3">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.06, duration: 0.4 }}
              className="glass-card rounded-2xl p-4 text-white"
            >
              <div className="grid h-9 w-9 place-items-center rounded-lg bg-white/15">
                <f.icon className="h-4 w-4" />
              </div>
              <div className="mt-3 text-sm font-semibold">{f.title}</div>
              <div className="mt-1 text-[12px] leading-snug text-white/80">{f.body}</div>
            </motion.div>
          ))}
        </div>

        <div className="relative mt-auto pt-8">
          <div className="glass-card flex items-center gap-3 rounded-2xl px-4 py-3">
            <Lock className="h-4 w-4 shrink-0" />
            <div className="text-xs text-white/90">
              Protected with AES-256 encryption. HIPAA-aligned by design.
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
          <div className="mb-8 lg:hidden">
            <div className="flex items-center gap-3">
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-brand-gradient text-white">
                <HeartPulse className="h-5 w-5" />
              </div>
              <div>
                <div className="text-base font-bold">ACP Care</div>
                <div className="text-[11px] text-muted-foreground">Advance Care Planning</div>
              </div>
            </div>
          </div>

          <div className="rounded-3xl border border-border bg-card p-8 shadow-[0_10px_40px_-20px_rgba(15,23,42,0.15)]">
            <div className="mb-6">
              <h2 className="text-2xl font-bold tracking-tight text-foreground">
                {tab === "signin" ? "Welcome back" : "Create your account"}
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {tab === "signin"
                  ? "Sign in to continue your ACP journey."
                  : "Just a few details to get you started."}
              </p>
            </div>

            {/* Segmented control */}
            <div className="mb-6 grid grid-cols-2 gap-1 rounded-xl bg-surface p-1">
              {(["signin", "signup"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={cn(
                    "relative rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                    tab === t ? "text-foreground" : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {tab === t && (
                    <motion.div
                      layoutId="authTab"
                      className="absolute inset-0 rounded-lg bg-white shadow-sm"
                      transition={{ type: "spring", stiffness: 400, damping: 32 }}
                    />
                  )}
                  <span className="relative">{t === "signin" ? "Sign In" : "Create Account"}</span>
                </button>
              ))}
            </div>

            <AnimatePresence mode="wait">
              {tab === "signin" ? (
                <SignInForm key="signin" onAuthSuccess={(role) => navigate({ to: role === "doctor" ? "/doctor-dashboard" : "/patient-dashboard" })} />
              ) : (
                <SignUpForm key="signup" onAuthSuccess={(role) => navigate({ to: role === "doctor" ? "/doctor-dashboard" : "/patient-dashboard" })} />
              )}
            </AnimatePresence>


          </div>

          <p className="mt-6 text-center text-xs text-muted-foreground">
            By continuing you agree to our{" "}
            <Link to="/" className="underline underline-offset-2">
              Terms
            </Link>{" "}
            and{" "}
            <Link to="/" className="underline underline-offset-2">
              Privacy Policy
            </Link>
            .
          </p>
        </motion.div>
      </main>
    </div>
  );
}

function FieldIcon({ children }: { children: React.ReactNode }) {
  return (
    <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
      {children}
    </span>
  );
}

function SignInForm({ onAuthSuccess }: { onAuthSuccess: (role: string) => void }) {
  const [show, setShow] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const user = await authService.login({ email, password });
      toast.success("Welcome back!");
      onAuthSuccess(user.role);
    } catch (err: any) {
      const msg = typeof err?.message === "string" ? err.message : "Invalid credentials.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.form
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2 }}
      onSubmit={handleSubmit}
      className="space-y-4"
    >
      <div className="space-y-1.5">
        <Label htmlFor="email" className="text-xs font-medium">
          Email
        </Label>
        <div className="relative">
          <FieldIcon>
            <Mail className="h-4 w-4" />
          </FieldIcon>
          <Input
            id="email"
            type="email"
            placeholder="you@example.com"
            className="h-11 rounded-xl pl-9"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="password" className="text-xs font-medium">
          Password
        </Label>
        <div className="relative">
          <FieldIcon>
            <KeyRound className="h-4 w-4" />
          </FieldIcon>
          <Input
            id="password"
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
      <div className="flex items-center justify-between">
        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          <Checkbox id="remember" /> Remember me
        </label>
        <button type="button" className="text-xs font-medium text-primary hover:underline">
          Forgot password?
        </button>
      </div>
      <Button
        type="submit"
        disabled={loading}
        className="h-12 w-full rounded-xl bg-primary text-base font-semibold text-primary-foreground shadow-md transition hover:bg-primary/90 hover:shadow-lg disabled:opacity-50"
      >
        {loading ? "Signing in..." : "Sign in"}
      </Button>
    </motion.form>
  );
}

function SignUpForm({ onAuthSuccess }: { onAuthSuccess: (role: string) => void }) {
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("patient");
  const [language, setLanguage] = useState("en");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 6) {
      toast.error("Password must be at least 6 characters long.");
      return;
    }
    if (password !== confirmPassword) {
      toast.error("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      await authService.register({ fullName, email, role, password });
      // Automatically log in after registration
      const user = await authService.login({ email, password });
      toast.success("Account created successfully!");
      onAuthSuccess(user.role);
    } catch (err: any) {
      const msg = typeof err?.message === "string" ? err.message : "Failed to create account.";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.form
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2 }}
      onSubmit={handleSubmit}
      className="space-y-4"
    >
      <div className="space-y-1.5">
        <Label className="text-xs font-medium">Full name</Label>
        <div className="relative">
          <FieldIcon>
            <User className="h-4 w-4" />
          </FieldIcon>
          <Input
            placeholder="Your Name"
            className="h-11 rounded-xl pl-9"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label className="text-xs font-medium">Role</Label>
          <Select value={role} onValueChange={(val) => setRole(val)}>
            <SelectTrigger className="h-11 rounded-xl">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="patient">Patient</SelectItem>
              <SelectItem value="doctor">Doctor</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs font-medium">Language</Label>
          <Select value={language} onValueChange={(val) => setLanguage(val)}>
            <SelectTrigger className="h-11 rounded-xl">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="en">English</SelectItem>
              <SelectItem value="hi">हिन्दी</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
      <div className="space-y-1.5">
        <Label className="text-xs font-medium">Email</Label>
        <div className="relative">
          <FieldIcon>
            <Mail className="h-4 w-4" />
          </FieldIcon>
          <Input
            type="email"
            placeholder="you@example.com"
            className="h-11 rounded-xl pl-9"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label className="text-xs font-medium">Password (min 6 chars)</Label>
          <Input
            type="password"
            placeholder="••••••••"
            className="h-11 rounded-xl"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={6}
            required
          />
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs font-medium">Confirm</Label>
          <Input
            type="password"
            placeholder="••••••••"
            className="h-11 rounded-xl"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            minLength={6}
            required
          />
        </div>
      </div>
      <label className="flex items-start gap-2 text-xs text-muted-foreground">
        <Checkbox id="terms" className="mt-0.5" required />
        <span>
          I agree to the Terms of Service and acknowledge the Privacy Policy.
        </span>
      </label>
      <Button
        type="submit"
        disabled={loading}
        className="h-12 w-full rounded-xl bg-primary text-base font-semibold text-primary-foreground shadow-md transition hover:bg-primary/90 hover:shadow-lg disabled:opacity-50"
      >
        {loading ? "Creating..." : "Create account"}
      </Button>
    </motion.form>
  );
}
