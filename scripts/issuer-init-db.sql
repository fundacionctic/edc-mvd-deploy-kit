--
-- Issuer Service Database Initialization
--
-- This script creates the necessary tables for the issuer service
-- to manage credential attestations and membership information.
--

-- Create attestations table
CREATE TABLE IF NOT EXISTS membership_attestations (
    membership_type       INTEGER   DEFAULT 0,
    holder_id             VARCHAR                             NOT NULL,
    membership_start_date TIMESTAMP DEFAULT NOW()             NOT NULL,
    id                    VARCHAR   DEFAULT gen_random_uuid() NOT NULL
        CONSTRAINT attestations_pk PRIMARY KEY
);

-- Create unique index on holder_id
CREATE UNIQUE INDEX IF NOT EXISTS membership_attestation_holder_id_uindex
    ON membership_attestations (holder_id);

-- Note: Participant attestations will be added by the seed script
-- This keeps the database initialization separate from participant configuration
