export const ACP_SECTIONS = [
  { key: "personal", title: "Personal Information", questions: 5 },
  { key: "medical", title: "Medical Treatment Preferences", questions: 6 },
  { key: "end-of-life", title: "End-of-Life Preferences", questions: 4 },
  { key: "proxy", title: "Designated Healthcare Representative", questions: 4 },
  { key: "donation", title: "Organ Donation", questions: 4 },
  { key: "review", title: "Confirmation & Review", questions: 4 },
] as const;

export type AcpSectionKey = (typeof ACP_SECTIONS)[number]["key"];
export type SectionStatus = "completed" | "in_progress" | "pending";

export function getSectionStatus(
  key: AcpSectionKey,
  profile: any,
  acp: any,
  dhrs: any[] = []
): SectionStatus {
  switch (key) {
    case "personal": {
      const isComplete = Boolean(
        profile?.phone &&
          profile?.preferred_language &&
          (profile?.address || profile?.permanent_address || profile?.current_address)
      );
      if (isComplete) return "completed";
      const hasSome = Boolean(
        profile?.phone || profile?.address || profile?.beliefs_values || profile?.age
      );
      return hasSome ? "in_progress" : "pending";
    }

    case "medical": {
      const medicalFields = [
        "cpr_preference",
        "ventilator_preference",
        "dialysis_preference",
        "chemotherapy_preference",
        "radiotherapy_preference",
        "surgery_preference",
      ];
      const specifiedCount = medicalFields.filter(
        (field) => acp?.[field] && acp[field] !== "NOT SPECIFIED"
      ).length;
      if (specifiedCount === medicalFields.length) return "completed";
      if (specifiedCount > 0) return "in_progress";
      return "pending";
    }

    case "end-of-life": {
      const hasPain = Boolean(acp?.pain_management);
      const hasPlace = Boolean(acp?.preferred_place_of_care);
      if (hasPain && hasPlace) return "completed";
      if (hasPain || hasPlace || Boolean(acp?.preferred_hospital) || Boolean(acp?.additional_wishes)) {
        return "in_progress";
      }
      return "pending";
    }

    case "proxy": {
      return dhrs && dhrs.length > 0 ? "completed" : "pending";
    }

    case "donation": {
      const organ = acp?.organ_donation && acp.organ_donation !== "NOT SPECIFIED";
      const body = acp?.body_donation && acp.body_donation !== "NOT SPECIFIED";
      if (organ && body) return "completed";
      if (organ || body || Boolean(acp?.last_rites)) return "in_progress";
      return "pending";
    }

    case "review": {
      if (acp?.is_completed) return "completed";
      const priorCompleted = ["personal", "medical", "end-of-life", "proxy", "donation"].every(
        (sKey) => getSectionStatus(sKey as AcpSectionKey, profile, acp, dhrs) === "completed"
      );
      return priorCompleted ? "in_progress" : "pending";
    }

    default:
      return "pending";
  }
}

export function completedSectionKeys(profile: any, acp: any, dhrs: any[] = []): AcpSectionKey[] {
  return ACP_SECTIONS.map((s) => s.key).filter(
    (key) => getSectionStatus(key, profile, acp, dhrs) === "completed"
  );
}

export function nextAcpSection(profile: any, acp: any, dhrs: any[] = []): AcpSectionKey {
  const completed = new Set(completedSectionKeys(profile, acp, dhrs));
  return ACP_SECTIONS.find((section) => !completed.has(section.key))?.key ?? "review";
}