-- ============================================================
-- PROVIDER PARTICIPANT DATABASE INITIALIZATION
-- ============================================================
-- This script initializes the PostgreSQL database for the Provider Participant
-- It creates separate databases and users for each component:
-- - Control Plane: Manages catalogs, contracts, and negotiations
-- - Data Plane: Handles data transfer operations
-- - Identity Hub: Manages credentials and identity
--
-- Execution: Automatically run by PostgreSQL on first container startup
-- Location: Mounted to /docker-entrypoint-initdb.d/init.sql in the container
-- ============================================================

-- ============================================================
-- CONTROL PLANE DATABASE SETUP
-- ============================================================
-- The Control Plane manages assets, policies, contract definitions,
-- contract negotiations, and transfer processes

-- Create control plane user with superuser privileges for schema management
CREATE USER provider_cp WITH ENCRYPTED PASSWORD 'provider_cp' SUPERUSER;

-- Create control plane database
CREATE DATABASE provider_controlplane;

-- Grant all privileges to the control plane user
GRANT ALL PRIVILEGES ON DATABASE provider_controlplane TO provider_cp;

-- ============================================================
-- DATA PLANE DATABASE SETUP
-- ============================================================
-- The Data Plane manages data transfer state and proxy operations

-- Create data plane user with superuser privileges for schema management
CREATE USER provider_dp WITH ENCRYPTED PASSWORD 'provider_dp' SUPERUSER;

-- Create data plane database
CREATE DATABASE provider_dataplane;

-- Grant all privileges to the data plane user
GRANT ALL PRIVILEGES ON DATABASE provider_dataplane TO provider_dp;

-- ============================================================
-- IDENTITY HUB DATABASE SETUP
-- ============================================================
-- The Identity Hub manages participant credentials, DID documents,
-- and STS token operations

-- Create identity hub user with superuser privileges for schema management
CREATE USER provider_ih WITH ENCRYPTED PASSWORD 'provider_ih' SUPERUSER;

-- Create identity hub database
CREATE DATABASE provider_identity;

-- Grant all privileges to the identity hub user
GRANT ALL PRIVILEGES ON DATABASE provider_identity TO provider_ih;

-- ============================================================
-- VERIFICATION QUERIES
-- ============================================================
-- Uncomment these to verify the database setup after initialization:
--
-- \l                                    -- List all databases
-- \du                                   -- List all users
-- SELECT datname FROM pg_database WHERE datname LIKE 'provider_%';
-- SELECT usename FROM pg_user WHERE usename LIKE 'provider_%';

-- ============================================================
-- NOTES FOR PRODUCTION
-- ============================================================
-- 1. Change default passwords to secure passwords:
--    - provider_cp: 'provider_cp' -> secure password
--    - provider_dp: 'provider_dp' -> secure password  
--    - provider_ih: 'provider_ih' -> secure password
-- 2. Remove SUPERUSER privilege if not needed for schema auto-creation
-- 3. Consider using separate PostgreSQL instances for each component
-- 4. Implement proper backup and recovery procedures for each database
-- 5. Set up database monitoring and alerting
-- 6. Configure connection pooling for high-load scenarios
-- 7. Review and adjust database names to match your naming conventions
-- 8. Consider implementing database-level encryption for sensitive data

-- ============================================================
-- EDC SCHEMA AUTO-CREATION
-- ============================================================
-- Each EDC component will automatically create its required tables
-- when EDC_SQL_SCHEMA_AUTOCREATE=true is set in the environment.
-- 
-- Control Plane creates tables for:
--   - Assets, Policies, Contract Definitions
--   - Contract Negotiations, Transfer Processes
--   - Participant Context, Catalog Cache
--
-- Data Plane creates tables for:
--   - Data Plane Instances, Transfer State
--   - Access Token Management
--
-- Identity Hub creates tables for:
--   - Credentials, Participant Context
--   - Key Pairs, DID Documents
--   - STS Client Management