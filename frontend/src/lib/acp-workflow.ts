export const ACP_SECTIONS = [
  { key: "personal", title: "Personal Information", questions: 5 },
  { key: "medical", title: "Medical Treatment Preferences", questions: 8 },
  { key: "end-of-life", title: "End-of-Life Preferences", questions: 4 },
  { key: "proxy", title: "Designated Healthcare Representative", questions: 4 },
  { key: "donation", title: "Organ Donation", questions: 4 },
  { key: "review", title: "Confirmation & Review", questions: 4 },
] as const;

export type AcpSectionKey = (typeof ACP_SECTIONS)[number]["key"];
export type SectionStatus = "completed" | "in_progress" | "pending";

const isDefined = (val: any): boolean =>
  val !== undefined && val !== null && val !== "" && val !== "NOT SPECIFIED" && val !== "Pending" && val !== "Not Specified";

export function getSectionStatus(
  key: AcpSectionKey,
  profile: any,
  acp: any,
  dhrs: any[] = []
): SectionStatus {
  switch (key) {
    case "personal": {
      const hasPhone = isDefined(profile?.phone);
      const hasAddr = isDefined(profile?.address || profile?.permanent_address || profile?.current_address);
      const hasName = isDefined(profile?.full_name || profile?.user?.full_name);
      const hasDobOrAge = isDefined(profile?.date_of_birth) || isDefined(profile?.age);
      const hasGender = isDefined(profile?.gender);

      const isComplete = Boolean(hasPhone && hasAddr && hasName && hasDobOrAge && hasGender);
      if (isComplete) return "completed";

      // If ONLY the registration account name is present and no clinical/contact fields are set, it's pending (0%)
      const hasClinicalOrContact = Boolean(
        hasPhone ||
          hasAddr ||
          profile?.beliefs_values ||
          hasDobOrAge ||
          hasGender
      );
      return hasClinicalOrContact ? "in_progress" : "pending";
    }

    case "medical": {
      const treatmentFields = [
        "cpr_preference",
        "ventilator_preference",
        "dialysis_preference",
        "chemotherapy_preference",
        "radiotherapy_preference",
        "surgery_preference",
        "iv_fluids_preference",
        "nutrition_hydration_preference",
      ];

      const specifiedCount = treatmentFields.filter((field) => isDefined(acp?.[field])).length;

      // Completed if all 8 medical treatment directives are answered
      if (specifiedCount === treatmentFields.length) return "completed";
      if (specifiedCount > 0) return "in_progress";
      return "pending";
    }

    case "end-of-life": {
      const fields = [acp?.goals_of_care, acp?.preferred_place_of_care, acp?.special_focus_priority, profile?.personal_values];
      const completedCount = fields.filter(isDefined).length;
      if (completedCount === fields.length) return "completed";
      if (completedCount > 0 || isDefined(acp?.preferred_hospital) || isDefined(acp?.additional_wishes)) return "in_progress";
      return "pending";
    }

    case "proxy": {
      if (!dhrs || dhrs.length === 0) return "pending";
      const primary = dhrs.find((d: any) => d.preference_order === 1) || dhrs[0];
      const alternate = dhrs.find((d: any) => d.preference_order === 2);
      const hasName = Boolean(primary?.full_name && primary.full_name !== "Representative");
      const hasRelationship = isDefined(primary?.relationship) && primary.relationship !== "Representative";
      const hasValidPhone = isDefined(primary?.mobile_primary) && primary.mobile_primary.replace(/[^0-9+]/g, "").length >= 10;
      const alternateChoice = typeof acp?.alternate_dhr_appointed === "boolean" ? acp.alternate_dhr_appointed : Boolean(alternate);
      const alternateReady = !alternateChoice || Boolean(alternate?.full_name && alternate.full_name !== "Alternate Representative" && isDefined(alternate.relationship) && alternate.relationship !== "Alternate Representative" && isDefined(alternate.mobile_primary) && alternate.mobile_primary.replace(/[^0-9+]/g, "").length >= 10);
      if (hasName && hasRelationship && hasValidPhone && alternateReady) return "completed";
      if (hasName || hasRelationship || hasValidPhone || alternateChoice) return "in_progress";
      return "pending";
    }

    case "donation": {
      const organ = isDefined(acp?.organ_donation);
      const body = isDefined(acp?.body_donation);
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

export function getSectionProgress(
  key: AcpSectionKey,
  profile: any,
  acp: any,
  dhrs: any[] = []
): number {
  const status = getSectionStatus(key, profile, acp, dhrs);
  if (status === "completed") return 100;
  if (status === "pending") return 0;

  switch (key) {
    case "personal": {
      let count = 0;
      if (isDefined(profile?.full_name || profile?.user?.full_name)) count++;
      if (isDefined(profile?.phone)) count++;
      if (isDefined(profile?.address || profile?.permanent_address || profile?.current_address)) count++;
      if (isDefined(profile?.date_of_birth) || isDefined(profile?.age)) count++;
      if (isDefined(profile?.gender)) count++;

      // If no clinical or contact ACP fields have been saved yet, genuine progress is 0%
      if (count === 0) return 0;
      return Math.min(100, Math.round((count / 5) * 100));
    }

    case "medical": {
      const treatmentFields = [
        "cpr_preference",
        "ventilator_preference",
        "dialysis_preference",
        "chemotherapy_preference",
        "radiotherapy_preference",
        "surgery_preference",
        "iv_fluids_preference",
        "nutrition_hydration_preference",
      ];
      const specifiedCount = treatmentFields.filter((field) => isDefined(acp?.[field])).length;
      if (specifiedCount === 0) return 0;
      return Math.min(100, Math.round((specifiedCount / treatmentFields.length) * 100));
    }

    case "end-of-life": {
      const required = [acp?.goals_of_care, acp?.preferred_place_of_care, acp?.special_focus_priority, profile?.personal_values];
      const completedCount = required.filter(isDefined).length;
      return Math.round((completedCount / required.length) * 100);
    }

    case "proxy": {
      if (!dhrs || dhrs.length === 0) return 0;
      const primary = dhrs.find((d: any) => d.preference_order === 1) || dhrs[0];
      const alternate = dhrs.find((d: any) => d.preference_order === 2);
      const hasName = Boolean(primary?.full_name && primary.full_name !== "Representative");
      const hasRel = isDefined(primary?.relationship) && primary.relationship !== "Representative";
      const hasValidPhone = isDefined(primary?.mobile_primary) && primary.mobile_primary.replace(/[^0-9+]/g, "").length >= 10;
      const alternateChoice = typeof acp?.alternate_dhr_appointed === "boolean" ? acp.alternate_dhr_appointed : Boolean(alternate);
      if (!alternateChoice) {
        const count = [hasName, hasRel, hasValidPhone].filter(Boolean).length;
        return Math.round((count / 3) * 100);
      }
      const hasAltName = Boolean(alternate?.full_name && alternate.full_name !== "Alternate Representative");
      const hasAltRel = isDefined(alternate?.relationship) && alternate.relationship !== "Alternate Representative";
      const hasAltPhone = isDefined(alternate?.mobile_primary) && alternate.mobile_primary.replace(/[^0-9+]/g, "").length >= 10;
      const count = [hasName, hasRel, hasValidPhone, hasAltName, hasAltRel, hasAltPhone].filter(Boolean).length;
      return Math.round((count / 6) * 100);
    }

    case "donation": {
      let count = 0;
      if (isDefined(acp?.organ_donation)) count++;
      if (isDefined(acp?.body_donation)) count++;
      return Math.round((count / 2) * 100);
    }

    case "review": {
      if (acp?.is_completed) return 100;
      const priorCompleted = ["personal", "medical", "end-of-life", "proxy", "donation"].every(
        (sKey) => getSectionStatus(sKey as AcpSectionKey, profile, acp, dhrs) === "completed"
      );
      return priorCompleted ? 50 : 0;
    }

    default:
      return 0;
  }
}

export function getOverallProgress(profile: any, acp: any, dhrs: any[] = []): number {
  if (acp?.is_completed) return 100;

  const total = ACP_SECTIONS.reduce((sum, section) => {
    return sum + getSectionProgress(section.key, profile, acp, dhrs);
  }, 0);

  const avg = Math.round(total / ACP_SECTIONS.length);
  return Math.min(100, avg);
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
