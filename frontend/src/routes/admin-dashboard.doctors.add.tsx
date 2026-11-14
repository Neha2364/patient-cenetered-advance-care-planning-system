import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Eye, EyeOff, Copy, CheckCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { adminService } from "@/lib/api";
import { toast } from "sonner";

export const Route = createFileRoute("/admin-dashboard/doctors/add")({
  head: () => ({ meta: [{ title: "Add Doctor — ACP Care Admin" }] }),
  component: AddDoctorPage,
});

function AddDoctorPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [mobile, setMobile] = useState("");
  const [specialization, setSpecialization] = useState("");
  const [hospital, setHospital] = useState("");
  const [regNumber, setRegNumber] = useState("");
  const [formError, setFormError] = useState("");

  // Result state after creation
  const [createdDoctor, setCreatedDoctor] = useState<{
    full_name: string;
    email: string;
    temporary_password: string;
    user_id: number;
  } | null>(null);
  const [showPass, setShowPass] = useState(false);
  const [copied, setCopied] = useState(false);

  const mutation = useMutation({
    mutationFn: () =>
      adminService.createDoctor({
        full_name: fullName.trim(),
        email: email.trim().toLowerCase(),
        mobile_number: mobile.trim() || undefined,
        specialization: specialization.trim() || undefined,
        hospital: hospital.trim() || undefined,
        medical_registration_number: regNumber.trim() || undefined,
      }),
    onSuccess: (data) => {
      toast.success(`Doctor account created for ${data.email}.`);
      setFormError("");
      setCreatedDoctor(data);
      qc.invalidateQueries({ queryKey: ["adminDoctors"] });
      qc.invalidateQueries({ queryKey: ["adminDashboard"] });
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Failed to create doctor account.";
      setFormError(msg);
      toast.error(msg);
    },
  });

  const handleCopy = async () => {
    if (createdDoctor?.temporary_password) {
      await navigator.clipboard.writeText(createdDoctor.temporary_password);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (createdDoctor) {
    return (
      <div className="mx-auto max-w-lg space-y-6">
          <div className="rounded-2xl border border-green-200 bg-green-50 p-6 shadow-sm">
            <div className="mb-4 text-lg font-bold text-green-800">✓ Doctor Account Created</div>
            <div className="space-y-2 text-sm text-green-900">
              <div>
                <span className="font-medium">Name:</span> {createdDoctor.full_name}
              </div>
              <div>
                <span className="font-medium">Email:</span> {createdDoctor.email}
              </div>
            </div>

            <div className="mt-4 rounded-xl border border-green-300 bg-white p-4">
              <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-green-700">
                Temporary Password — Share Securely
              </div>
              <div className="flex items-center gap-2">
                <code className="flex-1 rounded-lg bg-surface px-3 py-2 font-mono text-sm text-foreground">
                  {showPass ? createdDoctor.temporary_password : "••••••••••••••••"}
                </code>
                <button
                  type="button"
                  onClick={() => setShowPass((s) => !s)}
                  className="rounded-lg p-2 text-muted-foreground hover:bg-surface hover:text-foreground"
                  title={showPass ? "Hide" : "Show"}
                >
                  {showPass ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
                <button
                  type="button"
                  onClick={handleCopy}
                  className="rounded-lg p-2 text-muted-foreground hover:bg-surface hover:text-foreground"
                  title="Copy to clipboard"
                >
                  {copied ? (
                    <CheckCheck className="h-4 w-4 text-green-600" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </button>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                This password is shown only once and was not stored in plain text. Share it with the
                doctor securely (e.g., via encrypted email or a secure channel). The doctor should
                change it after first login.
              </p>
            </div>
          </div>

          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={() => {
                setCreatedDoctor(null);
                setFullName("");
                setEmail("");
                setMobile("");
                setSpecialization("");
                setHospital("");
                setRegNumber("");
              }}
              className="flex-1"
            >
              Add Another Doctor
            </Button>
            <Button onClick={() => navigate({ to: "/admin-dashboard/doctors" })} className="flex-1">
              View All Doctors
            </Button>
          </div>
        </div>
    );
  }

  return (
    <div className="mx-auto max-w-lg space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <Link
            to="/admin-dashboard/doctors"
            className="inline-flex items-center justify-center rounded-xl p-2 text-muted-foreground transition hover:bg-surface hover:text-foreground"
            title="Back to Doctors"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-foreground">Add New Doctor</h1>
            <p className="mt-0.5 text-sm text-muted-foreground">
              Create an authorized doctor account. A secure temporary password will be generated.
            </p>
          </div>
        </div>

        {/* Form */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setFormError("");
            if (!fullName.trim()) {
              setFormError("Doctor full name is required.");
              return;
            }
            if (!email.trim()) {
              setFormError("Email address is required.");
              return;
            }
            if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
              setFormError("Enter a valid email address.");
              return;
            }
            mutation.mutate();
          }}
          className="rounded-2xl border border-border bg-white p-6 shadow-sm space-y-4"
        >
          {formError && (
            <div
              role="alert"
              className="rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive"
            >
              {formError}
            </div>
          )}
          <div className="space-y-1.5">
            <Label className="text-xs font-medium">
              Doctor Full Name <span className="text-destructive">*</span>
            </Label>
            <Input
              placeholder="Dr. Full Name"
              className="h-11 rounded-xl"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-medium">
              Email Address <span className="text-destructive">*</span>
            </Label>
            <Input
              type="email"
              placeholder="doctor@hospital.com"
              className="h-11 rounded-xl"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-medium">Mobile Number</Label>
            <Input
              type="tel"
              placeholder="+91 98765 43210"
              className="h-11 rounded-xl"
              value={mobile}
              onChange={(e) => setMobile(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-medium">Medical Specialization</Label>
            <Input
              placeholder="e.g. Palliative Care, General Medicine"
              className="h-11 rounded-xl"
              value={specialization}
              onChange={(e) => setSpecialization(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-medium">Hospital / Institution</Label>
            <Input
              placeholder="e.g. City General Hospital"
              className="h-11 rounded-xl"
              value={hospital}
              onChange={(e) => setHospital(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-medium">Medical Registration Number (Optional)</Label>
            <Input
              placeholder="e.g. MCI-12345"
              className="h-11 rounded-xl"
              value={regNumber}
              onChange={(e) => setRegNumber(e.target.value)}
            />
          </div>

          <div className="rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-xs text-blue-800">
            A secure 16-character temporary password will be generated automatically. You will see
            it once after creation — share it with the doctor via a secure channel.
          </div>

          <Button type="submit" disabled={mutation.isPending} className="h-11 w-full rounded-xl">
            {mutation.isPending ? "Creating..." : "Create Doctor Account"}
          </Button>
        </form>
      </div>
  );
}
