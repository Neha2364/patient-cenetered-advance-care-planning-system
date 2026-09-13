import { createFileRoute } from "@tanstack/react-router";
import { PatientShell } from "@/components/patient-shell";
import { AcpWorkflow } from "@/components/acp-workflow";

export const Route = createFileRoute("/patient-dashboard/acp/$section")({ component: AcpSectionRoute });
function AcpSectionRoute() { const { section } = Route.useParams(); return <PatientShell><AcpWorkflow section={section} /></PatientShell>; }