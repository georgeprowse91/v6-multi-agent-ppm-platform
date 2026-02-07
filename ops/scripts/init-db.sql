-- Multi-Agent PPM Platform - Database Initialization Script
-- This script is run automatically when PostgreSQL container starts

-- Create database if it doesn't exist (already created by POSTGRES_DB env var)

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create initial schema (to be managed by Alembic migrations)

GRANT ALL PRIVILEGES ON DATABASE ppm TO ppm;

-- Log initialization
DO $$
BEGIN
  RAISE NOTICE 'Database initialization complete';
END $$;
