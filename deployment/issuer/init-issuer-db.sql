-- ============================================================
-- ISSUER SERVICE DATABASE INITIALIZATION
-- ============================================================
-- This script initializes the PostgreSQL database for the Issuer Service
-- It creates the necessary users, databases, tables, and seed data
--
-- Execution: Automatically run by PostgreSQL on first container startup
-- Location: Mounted to /docker-entrypoint-initdb.d/init.sql in the container
-- ============================================================

-- ============================================================
-- USER AND DATABASE SETUP
-- ============================================================

-- Create issuer user with superuser privileges for schema management
CREATE USER issuer WITH ENCRYPTED PASSWORD 'issuer' SUPERUSER;

-- Create issuer database
CREATE DATABASE issuer;

-- Connect to issuer database as issuer user
\c issuer issuer

-- ============================================================
-- ATTESTATION TABLE: membership_attestations
-- ============================================================
-- This table stores membership attestation data for dataspace participants
-- It is queried by database attestations when issuing MembershipCredentials
--
-- Schema:
--   - id: Unique identifier for the attestation record
--   - membership_type: Type/level of membership (e.g., 0=guest, 1=consumer, 2=provider)
--   - holder_id: DID of the participant (MUST match participant DID exactly!)
--   - membership_start_date: Timestamp when membership began
--
-- Usage:
--   Database attestations query this table with:
--   SELECT * FROM membership_attestations WHERE holder_id = '<participant-did>';

CREATE TABLE IF NOT EXISTS membership_attestations (
    id VARCHAR DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    membership_type INTEGER DEFAULT 0,
    holder_id VARCHAR NOT NULL,
    membership_start_date TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Create index on holder_id for faster attestation queries
CREATE INDEX IF NOT EXISTS idx_membership_attestations_holder_id ON membership_attestations(holder_id);

-- ============================================================
-- ATTESTATION TABLE: data_processor_attestations
-- ============================================================
-- This table stores data processing capability attestations
-- It is queried by database attestations when issuing DataProcessorCredentials
--
-- Schema:
--   - id: Unique identifier for the attestation record
--   - holder_id: DID of the participant
--   - contract_version: Version of the data processing contract
--   - processing_level: Security level (e.g., "processing", "sensitive")
--   - attestation_date: Timestamp when attestation was created

CREATE TABLE IF NOT EXISTS data_processor_attestations (
    id VARCHAR DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    holder_id VARCHAR NOT NULL,
    contract_version VARCHAR DEFAULT '1.0.0' NOT NULL,
    processing_level VARCHAR DEFAULT 'processing' NOT NULL,
    attestation_date TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Create index on holder_id for faster attestation queries
CREATE INDEX IF NOT EXISTS idx_data_processor_attestations_holder_id ON data_processor_attestations(holder_id);

-- ============================================================
-- SEED DATA: Initial Participants
-- ============================================================
-- These records represent initial dataspace participants
--
-- IMPORTANT NOTES:
-- 1. holder_id MUST match the participant DID exactly (including URL encoding)
-- 2. Use host.docker.internal for Docker Compose deployments
-- 3. URL encoding: ':' becomes '%3A'
-- 4. Format: did:web:host.docker.internal%3A<port>:<participant-name>
--
-- Participant Types:
--   - Consumer: membership_type=1, can consume data
--   - Provider: membership_type=2, can provide data
--
-- DID Format Examples:
--   Docker Compose: did:web:host.docker.internal%3A7083:consumer
--   Kubernetes:     did:web:consumer-identityhub%3A7083:consumer
--   Production:     did:web:consumer.yourdomain.com:consumer

-- ============================================================
-- CONSUMER PARTICIPANT
-- ============================================================
-- DID: did:web:host.docker.internal%3A7083:consumer
-- Port: 7083 (IdentityHub DID endpoint)
-- Membership Type: 1 (Consumer)

INSERT INTO membership_attestations (membership_type, holder_id, membership_start_date)
VALUES (
    1,
    'did:web:host.docker.internal%3A7083:consumer',
    '2023-01-01T00:00:00Z'
)
ON CONFLICT DO NOTHING;

INSERT INTO data_processor_attestations (holder_id, contract_version, processing_level, attestation_date)
VALUES (
    'did:web:host.docker.internal%3A7083:consumer',
    '1.0.0',
    'processing',
    '2023-01-01T00:00:00Z'
)
ON CONFLICT DO NOTHING;

-- ============================================================
-- PROVIDER PARTICIPANT
-- ============================================================
-- DID: did:web:host.docker.internal%3A7093:provider
-- Port: 7093 (IdentityHub DID endpoint)
-- Membership Type: 2 (Provider)

INSERT INTO membership_attestations (membership_type, holder_id, membership_start_date)
VALUES (
    2,
    'did:web:host.docker.internal%3A7093:provider',
    '2023-01-01T00:00:00Z'
)
ON CONFLICT DO NOTHING;

INSERT INTO data_processor_attestations (holder_id, contract_version, processing_level, attestation_date)
VALUES (
    'did:web:host.docker.internal%3A7093:provider',
    '1.0.0',
    'processing',
    '2023-01-01T00:00:00Z'
)
ON CONFLICT DO NOTHING;

-- ============================================================
-- VERIFICATION QUERIES
-- ============================================================
-- Uncomment these to verify the seed data after initialization:
--
-- SELECT * FROM membership_attestations;
-- SELECT * FROM data_processor_attestations;
-- SELECT COUNT(*) FROM membership_attestations;
-- SELECT COUNT(*) FROM data_processor_attestations;

-- ============================================================
-- NOTES FOR PRODUCTION
-- ============================================================
-- 1. Change default password 'issuer' to a secure password
-- 2. Update holder_id DIDs to match actual participant DIDs
-- 3. Remove SUPERUSER privilege from issuer user if not needed
-- 4. Add additional participants as needed
-- 5. Consider adding foreign key constraints for referential integrity
-- 6. Implement proper backup and recovery procedures
-- 7. Set up database monitoring and alerting
-- 8. Review and adjust membership_type values to match your dataspace requirements
