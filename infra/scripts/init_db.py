import psycopg2
from config.settings import settings

SCHEMA = """
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Pipeline runs table
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  TEXT NOT NULL,
    mode        TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    metadata    JSONB DEFAULT '{}'
);

-- Agent artifacts table  
CREATE TABLE IF NOT EXISTS artifacts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id      UUID REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    agent_phase INTEGER NOT NULL,
    agent_name  TEXT NOT NULL,
    artifact    JSONB NOT NULL,
    confidence  FLOAT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Audit log — immutable record of all agent actions
CREATE TABLE IF NOT EXISTS audit_log (
    id          BIGSERIAL PRIMARY KEY,
    run_id      UUID,
    agent_name  TEXT,
    action      TEXT NOT NULL,
    payload     JSONB,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Human gate decisions
CREATE TABLE IF NOT EXISTS gate_decisions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id      UUID REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    gate_name   TEXT NOT NULL,
    decision    TEXT NOT NULL,
    decided_by  TEXT,
    feedback    TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_runs_project ON pipeline_runs(project_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON pipeline_runs(status);
CREATE INDEX IF NOT EXISTS idx_artifacts_run ON artifacts(run_id);
CREATE INDEX IF NOT EXISTS idx_audit_run ON audit_log(run_id);
"""


def init_database():
    print("Initialising PostgreSQL schema...")
    conn = psycopg2.connect(settings.database_url)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(SCHEMA)
    conn.close()
    print("✅ Database schema ready")


if __name__ == "__main__":
    init_database()
