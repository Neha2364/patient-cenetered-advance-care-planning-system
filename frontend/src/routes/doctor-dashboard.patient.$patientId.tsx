import { createFileRoute, Navigate } from "@tanstack/react-router";

export const Route = createFileRoute("/doctor-dashboard/patient/$patientId")({
  component: RedirectToPatients,
});

function RedirectToPatients() {
  const { patientId } = Route.useParams();
  return <Navigate to="/doctor-dashboard/patients/$patientId" params={{ patientId }} replace />;
}
