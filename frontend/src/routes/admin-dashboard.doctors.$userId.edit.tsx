import { createFileRoute, useNavigate, Link } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, AlertTriangle } from "lucide-react";
import { AdminShell } from "@/components/admin-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { adminService } from "@/lib/api";
import { toast } from "sonner";

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
  const [mobile, setMobile] = useState("");
  const [specialization, setSpecialization] = useState("");
  const [hospital, setHospital] = useState("");
  const [regNumber, setRegNumber] = useState("");

  const { data: doc, isLoading, isError } = useQuery({
    queryKey: ["adminDoctor", uid],
    queryFn: () => adminService.getDoctor(uid),
  });

  useEffect(() => {
    if (doc) {
      setFullName(doc.full_name ?? "");
      setMobile(doc.mobile_number ?? "");
      setSpecialization(doc.specialization ?? "");
      setHospital(doc.hospital ?? "");
      setRegNumber(doc.medical_registration_number ?? "");
    }
  }, [doc]);

  const mutation = useMutation({
    mutationFn: () =>
      adminService.updateDoctor(uid, {
        full_name: fullName.trim(),
        mobile_number: mobile.trim() || undefined,
        specialization: specialization.trim() || undefined,
        hospital: hospital.trim() || undefined,
        medical_registration_number: regNumber.trim() || undefined,
      }),
    onSuccess: () => {
      toast.success("Doctor profile updated.");
      qc.invalidateQueries({ queryKey: ["adminDoctors"] });
      qc.invalidateQueries({ queryKey: ["adminDoctor", uid] });
      navigate({ to: "/admin-dashboard/doctors/$userId", params: { userId: String(uid) } });
    },
    onError: (err: any) => toast.error(err?.message ?? "Failed to update profile."),
  });

  return (
    <AdminShell>
      <div className="mx-auto max-w-lg space-y-6">
        <div className="flex items-center gap-3">
          <Link to="/admin-dashboard/doctors/$userId" params={{ userId: String(uid) }}>
            <button className="rounded-xl p-2 text-muted-foreground hover:bg-surface hover:text-foreground">
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
            Failed to load doctor.
          </div>
        )}

        {doc && (
          <form
            onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}
            className="rounded-2xl border border-border bg-white p-6 shadow-sm space-y-4"
          >
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Full Name</Label>
              <Input className="h-11 rounded-xl" value={fullName} onChange={(e) => setFullName(e.target.value)} required />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Email (read-only)</Label>
              <Input className="h-11 rounded-xl bg-surface" value={doc.email} readOnly disabled />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Mobile Number</Label>
              <Input className="h-11 rounded-xl" value={mobile} onChange={(e) => setMobile(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Specialization</Label>
              <Input className="h-11 rounded-xl" value={specialization} onChange={(e) => setSpecialization(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Hospital / Institution</Label>
              <Input className="h-11 rounded-xl" value={hospital} onChange={(e) => setHospital(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">Medical Registration Number</Label>
              <Input className="h-11 rounded-xl" value={regNumber} onChange={(e) => setRegNumber(e.target.value)} />
            </div>
            <Button type="submit" disabled={mutation.isPending} className="h-11 w-full rounded-xl">
              {mutation.isPending ? "Saving..." : "Save Changes"}
            </Button>
          </form>
        )}
      </div>
    </AdminShell>
  );
}

