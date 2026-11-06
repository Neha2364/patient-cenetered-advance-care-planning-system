-- Preserve the stable questionnaire question ID associated with each saved turn.
ALTER TABLE chat_histories
    ADD COLUMN IF NOT EXISTS question_number INTEGER;
