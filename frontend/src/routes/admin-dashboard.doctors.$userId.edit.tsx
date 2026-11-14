import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, AlertTriangle, AlertCircle, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { adminService } from "@/lib/api";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/admin-dashboard/doctors/$userId/edit")({
  head: () => ({ meta: [{ title: "Edit Doctor — ACP Care Admin" }] }),
  component: EditDoctorPage,
});

function EditDoctorPage() {
  const { userId } = Route.useParams();
  const uid = Number(userId);
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [mobile, setMobile] = useState("");
  const [specialization, setSpecialization] = useState("");
  const [hospital, setHospital] = useState("");
  const [regNumber, setRegNumber] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [formError, setFormError] = useState("");

  const { data: doc, isLoading, isError } = useQuery({
    queryKey: ["adminDoctor", uid],
    queryFn: () => adminService.getDoctor(uid),
  });

  useEffect(() => {
    if (doc) {
      setFullName(doc.full_name ?? "");
      setEmail(doc.email ?? "");
      setMobile(doc.mobile_number ?? "");
      setSpecialization(doc.specialization ?? "");
      setHospital(doc.hospital ?? "");
      setRegNumber(doc.medical_registration_number ?? "");
      setIsActive(doc.is_active ?? true);
      setFormError("");
    }
  }, [doc]);

  const mutation = useMutation({
    mutationFn: () => {
      const cleanName = fullName.trim();
      const cleanEmail = email.trim().toLowerCase();
      const cleanMobile = mobile.trim();

      return adminService.updateDoctor(uid, {
        full_name: cleanName,
        email: cleanEmail,
        mobile_number: cleanMobile || undefined,
        specialization: specialization.trim() || undefined,
        hospital: hospital.trim() || undefined,
        medical_registration_number: regNumber.trim() || undefined,
        is_active: isActive,
      });
    },
    onSuccess: (data) => {
      toast.success("Doctor profile updated successfully.");
      setFormError("");
      qc.invalidateQueries({ queryKey: ["adminDoctors"] });
      qc.invalidateQueries({ queryKey: ["adminDoctor", uid] });
      qc.invalidateQueries({ queryKey: ["adminDashboard"] });
      navigate({ to: "/admin-dashboard/doctors/$userId", params: { userId: String(uid) } });
    },
    onError: (err: any) => {
      const msg = err?.message ?? "Failed to update doctor profile.";
      setFormError(msg);
      toast.error(msg);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError("");

    const cleanName = fullName.trim();
    if (!cleanName) {
      const msg = "Doctor's full name is required.";
      setFormError(msg);
      toast.error(msg);
      return;
    }
    if (cleanName.length < 2) {
      const msg = "Full name must be at least 2 characters long.";
      setFormError(msg);
      toast.error(msg);
      return;
    }

    const cleanEmail = email.trim().toLowerCase();
    if (!cleanEmail) {
      const msg = "Email address is required.";
      setFormError(msg);
      toast.error(msg);
      return;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(cleanEmail)) {
      const msg = "Please enter a valid email address (e.g., doctor@hospital.com).";
      setFormError(msg);
      toast.error(msg);
      return;
    }

    const cleanMobile = mobile.trim();
    if (cleanMobile && !/^[0-9+\s\-()]{7,20}$/.test(cleanMobile)) {
      const msg = "Please enter a valid mobile number (7–20 digits).";
      setFormError(msg);
      toast.error(msg);
      return;
    }

    mutation.mutate();
  };

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <div className="flex items-center gap-3">
        <Link to="/admin-dashboard/doctors/$userId" params={{ userId: String(uid) }}>
          <button
            type="button"
            className="rounded-xl p-2 text-muted-foreground hover:bg-surface hover:text-foreground"
            aria-label="Back to Doctor Details"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-foreground">Edit Doctor Profile</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">User ID: {uid}</p>
        </div>
      </div>

      {isLoading && <div className="h-64 animate-pulse rounded-2xl bg-surface" />}

      {isError && (
        <div className="flex items-center gap-3 rounded-2xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          Failed to load doctor details.
        </div>
      )}

      {doc && (
        <form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-border bg-white p-6 shadow-sm space-y-4"
        >
          {formError && (
            <div className="flex items-center gap-2.5 rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-xs text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="full_name" className="text-xs font-medium">
              Full Name <span className="text-destructive">*</span>
            </Label>
            <Input
              id="full_name"
              className="h-11 rounded-xl"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g. Dr. Jane Smith"
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="email" className="text-xs font-medium">
              Email Address <span className="text-destructive">*</span>
            </Label>
            <Input
              id="email"
              type="email"
              className="h-11 rounded-xl"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. doctor@hospital.com"
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="mobile" className="text-xs font-medium">
              Mobile Number
            </Label>
            <Input
              id="mobile"
              className="h-11 rounded-xl"
              value={mobile}
              onChange={(e) => setMobile(e.target.value)}
              placeholder="e.g. +91 9876543210"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="specialization" className="text-xs font-medium">
              Specialization
            </Label>
            <Input
              id="specialization"
              className="h-11 rounded-xl"
              value={specialization}
              onChange={(e) => setSpecialization(e.target.value)}
              placeholder="e.g. Palliative Care, Oncology, Cardiology"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="hospital" className="text-xs font-medium">
              Hospital / Institution
            </Label>
            <Input
              id="hospital"
              className="h-11 rounded-xl"
              value={hospital}
              onChange={(e) => setHospital(e.target.value)}
              placeholder="e.g. City General Hospital"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="reg_number" className="text-xs font-medium">
              Medical Registration Number
            </Label>
            <Input
              id="reg_number"
              className="h-11 rounded-xl"
              value={regNumber}
              onChange={(e) => setRegNumber(e.target.value)}
              placeholder="e.g. MCI-123456"
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-medium">Account Status</Label>
            <div className="grid grid-cols-2 gap-3 pt-0.5">
              <button
                type="button"
                onClick={() => setIsActive(true)}
                className={cn(
                  "flex h-11 items-center justify-center gap-2 rounded-xl border text-sm transition",
                  isActive
                    ? "border-green-600 bg-green-50 text-green-700 font-semibold ring-1 ring-green-600 shadow-2xs"
                    : "border-border bg-white text-muted-foreground hover:bg-surface"
                )}
              >
                <span className="h-2 w-2 rounded-full bg-green-600" />
                Active
              </button>
              <button
                type="button"
                onClick={() => setIsActive(false)}
                className={cn(
                  "flex h-11 items-center justify-center gap-2 rounded-xl border text-sm transition",
                  !isActive
                    ? "border-red-600 bg-red-50 text-red-700 font-semibold ring-1 ring-red-600 shadow-2xs"
                    : "border-border bg-white text-muted-foreground hover:bg-surface"
                )}
              >
                <span className="h-2 w-2 rounded-full bg-red-600" />
                Inactive
              </button>
            </div>
          </div>

          <div className="flex items-center gap-3 pt-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate({ to: "/admin-dashboard/doctors/$userId", params: { userId: String(uid) } })}
              disabled={mutation.isPending}
              className="h-11 flex-1 rounded-xl"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={mutation.isPending}
              className="h-11 flex-1 rounded-xl"
            >
              {mutation.isPending ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}

