-- Provenance for catalog rows: where a model came from and when it was fetched.
-- Live refreshes write these fields; the seed and CSV import leave them as a
-- marker of their own source, so the UI can always say how fresh the data is.

ALTER TABLE device_models ADD COLUMN IF NOT EXISTS source text;
ALTER TABLE device_models ADD COLUMN IF NOT EXISTS fetched_at timestamptz;

CREATE INDEX IF NOT EXISTS device_models_source_idx ON device_models (source);
