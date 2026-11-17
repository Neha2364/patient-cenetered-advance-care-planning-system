-- Add normalized questionnaire fields. Only explicitly tagged legacy answers are backfilled.
ALTER TABLE patients ADD COLUMN IF NOT EXISTS chronic_conditions TEXT;
ALTER TABLE patients ADD COLUMN IF NOT EXISTS serious_hospitalization TEXT;
ALTER TABLE patients ADD COLUMN IF NOT EXISTS long_term_medications TEXT;
ALTER TABLE patients ADD COLUMN IF NOT EXISTS allergies TEXT;
ALTER TABLE patients ADD COLUMN IF NOT EXISTS personal_values TEXT;

ALTER TABLE acp_preferences ADD COLUMN IF NOT EXISTS goals_of_care VARCHAR(120);
ALTER TABLE acp_preferences ADD COLUMN IF NOT EXISTS alternate_dhr_appointed BOOLEAN;


UPDATE patients SET chronic_conditions = substring(beliefs_values from '\[Chronic Conditions: ([^\]]*)\]')
WHERE chronic_conditions IS NULL AND beliefs_values ~ '\[Chronic Conditions: [^\]]*\]';
UPDATE patients SET serious_hospitalization = substring(beliefs_values from '\[Major Illness/Hospitalization: ([^\]]*)\]')
WHERE serious_hospitalization IS NULL AND beliefs_values ~ '\[Major Illness/Hospitalization: [^\]]*\]';
UPDATE patients SET long_term_medications = substring(beliefs_values from '\[Medications: ([^\]]*)\]')
WHERE long_term_medications IS NULL AND beliefs_values ~ '\[Medications: [^\]]*\]';
UPDATE patients SET allergies = substring(beliefs_values from '\[Allergies: ([^\]]*)\]')
WHERE allergies IS NULL AND beliefs_values ~ '\[Allergies: [^\]]*\]';
UPDATE patients SET personal_values = substring(beliefs_values from 'Personal Goal: ([^;]*)')
WHERE personal_values IS NULL AND beliefs_values ~ 'Personal Goal: [^;]+';
