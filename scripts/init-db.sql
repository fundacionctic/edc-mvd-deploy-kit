-- Initialize PostgreSQL database for MVD
-- Create user and database for the MVD components

CREATE USER mvd_user WITH ENCRYPTED PASSWORD 'mvd_password' SUPERUSER;
CREATE DATABASE mvd;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE mvd TO mvd_user;
