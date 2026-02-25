-- TradingAgents PostgreSQL initialization script
-- This script runs automatically when the container is first created

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Grant permissions (for Alembic migrations)
-- The POSTGRES_USER already has superuser privileges by default

-- Create schema for LangGraph store (if using separate schema)
-- CREATE SCHEMA IF NOT EXISTS langgraph;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'TradingAgents database initialized with pgvector extension';
END $$;
