import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileText, FolderOpen } from "lucide-react";
import { PatientShell } from "@/components/patient-shell";
import { MotionCard } from "@/components/motion-card";
import { Button } from "@/components/ui/button";
import { patientService } from "@/lib/api";
import { toast } from "sonner";

export const Route = createFileRoute("/patient-dashboard/documents")({ component: DocumentsPage });

type Witness = { name: string; email: string; mobile: string };
const emptyWitness = (): Witness => ({ name: "", email: "", mobile: "" });

function WitnessFields({ number, value, onChange }: { number: number; value: Witness; onChange: (value: Witness) => void }) {
  const update = (field: keyof Witness, next: string) => onChange({ ...value, [field]: next });
  return <fieldset className="rounded-xl border border-border p-4"><legend className="px-1 text-sm font-semibold">Witness {number}</legend><div className="mt-2 grid gap-3 sm:grid-cols-2">{([['name', 'Full name', 'text'], ['email', 'Email', 'email'], ['mobile', 'Mobile number', 'tel']] as const).map(([field, label, type]) => <label key={field}><span className="mb-1 block text-xs text-muted-foreground">{label}</span><input required type={type} value={value[field]} onChange={(event) => update(field, event.target.value)} className="h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm outline-none focus:ring-2 focus:ring-primary/30" /></label>)}</div></fieldset>;
}

function DocumentsPage() {
  const queryClient = useQueryClient();
  const [showGenerator, setShowGenerator] = useState(false);
  const [witnesses, setWitnesses] = useState([emptyWitness(), emptyWitness()]);
  const { data: profile } = useQuery({ queryKey: ["patientProfile"], queryFn: patientService.getProfile });
  const patientId = profile?.patient_id;
  const { data: acp } = useQuery({ queryKey: ["patientAcp", patientId], queryFn: () => patientService.getACP(patientId), enabled: !!patientId });
  const { data: documents = [], isLoading } = useQuery({ queryKey: ["amdHistory", patientId], queryFn: () => patientService.getAMDHistory(patientId), enabled: !!patientId });
  const canGenerate = Boolean(acp?.is_completed);
  const generate = useMutation({
    mutationFn: () => {
      if (!patientId || !canGenerate) throw new Error("Complete Confirmation & Review before generating an AMD.");
      return patientService.generateAMD({ patient_id: patientId, witnesses });
    },
    onSuccess: () => {
      toast.success("AMD generated successfully.");
      setShowGenerator(false);
      queryClient.invalidateQueries({ queryKey: ["amdHistory", patientId] });
      queryClient.invalidateQueries({ queryKey: ["patientAcp", patientId] });
    },
    onError: (error: Error) => toast.error(error.message),
  });
  const download = async (amdId: number) => {
    if (!patientId) return;
    try { await patientService.downloadAMD(patientId, amdId); } catch (error: any) { toast.error(error.message); }
  };

  return <PatientShell><header className="flex flex-wrap items-start justify-between gap-4"><div><h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">My Documents</h1><p className="mt-1 text-sm text-muted-foreground">Your generated Advance Medical Directives are kept here.</p></div><Button disabled={!canGenerate} onClick={() => setShowGenerator((visible) => !visible)} className="rounded-xl"><FileText className="mr-2 h-4 w-4" />Generate AMD</Button></header>
    {!canGenerate && patientId && <p className="mt-4 text-sm text-muted-foreground">Complete Confirmation &amp; Review before generating your Advance Medical Directive.</p>}
    {showGenerator && <MotionCard className="mt-6 max-w-4xl"><h2 className="text-lg font-bold">Witness details</h2><p className="mt-1 text-sm text-muted-foreground">Two witnesses are required by the document generation process. Review these details carefully before continuing.</p><form className="mt-5 space-y-4" onSubmit={(event) => { event.preventDefault(); generate.mutate(); }}><WitnessFields number={1} value={witnesses[0]} onChange={(value) => setWitnesses([value, witnesses[1]])} /><WitnessFields number={2} value={witnesses[1]} onChange={(value) => setWitnesses([witnesses[0], value])} /><div className="flex justify-end gap-2"><Button type="button" variant="outline" onClick={() => setShowGenerator(false)}>Cancel</Button><Button type="submit" disabled={!canGenerate || generate.isPending}>{generate.isPending ? "Generating�" : "Generate AMD"}</Button></div></form></MotionCard>}
    <MotionCard className="mt-6 max-w-4xl">{isLoading ? <p className="text-sm text-muted-foreground">Loading documents�</p> : documents.length === 0 ? <div className="flex min-h-64 flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-surface text-center"><div className="grid h-14 w-14 place-items-center rounded-2xl bg-primary/10 text-primary"><FolderOpen className="h-6 w-6" /></div><h2 className="mt-4 font-semibold">No documents yet</h2><p className="mt-1 max-w-sm text-sm text-muted-foreground">Complete your ACP and generate an Advance Medical Directive to view or download it here.</p></div> : <div className="space-y-3">{documents.map((document: any) => <div key={document.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-surface p-4"><div className="flex items-center gap-3"><FileText className="h-5 w-5 text-primary" /><div><p className="font-semibold">{document.pdf_name || "Advance Medical Directive"}</p><p className="text-xs text-muted-foreground">Generated {new Date(document.generated_at).toLocaleDateString()} � Version {document.version} � Status: {document.status}</p></div></div><Button variant="outline" onClick={() => download(document.id)} className="rounded-xl"><Download className="mr-2 h-4 w-4" />Download PDF</Button></div>)}</div>}</MotionCard>
  </PatientShell>;
}