-- DHR name and relationship may be captured conversationally before the patient
-- completes the contact form. Empty contact fields remain NULL; no contact data is fabricated.
ALTER TABLE dhrs ALTER COLUMN mobile_primary DROP NOT NULL;
ALTER TABLE dhrs ALTER COLUMN email_primary DROP NOT NULL;
