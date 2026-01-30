-- CortexGraph PostgreSQL + pgvector Schema
-- Maps cortexgraph.storage.models to PostgreSQL with vector support
-- Last updated: 2026-01-26

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pgvector;
CREATE EXTENSION IF NOT EXISTS uuid-ossp;

-- ============================================================================
-- MEMORIES TABLE (Short-term + Long-term memory storage)
-- ============================================================================

CREATE TABLE memories (
    -- Identity
    id TEXT PRIMARY KEY,

    -- Content
    content TEXT NOT NULL,

    -- Metadata (stored as JSONB for flexibility)
    -- Structure: { tags: [str], source: str|null, context: str|null, extra: {} }
    meta JSONB NOT NULL DEFAULT '{"tags": [], "source": null, "context": null, "extra": {}}',

    -- Entities (extracted named entities)
    entities TEXT[] DEFAULT ARRAY[]::TEXT[],

    -- Temporal fields (Unix timestamps in seconds)
    created_at BIGINT NOT NULL,
    last_used BIGINT NOT NULL,

    -- Decay scoring fields
    use_count INTEGER NOT NULL DEFAULT 0,
    strength FLOAT NOT NULL DEFAULT 1.0,  -- 0.0 to 2.0

    -- Status and promotion
    status TEXT NOT NULL DEFAULT 'active',  -- 'active', 'promoted', 'archived'
    promoted_at BIGINT,
    promoted_to TEXT,  -- Path in vault (e.g., "vault/STM/...")

    -- Embeddings (384-dimensional from all-MiniLM-L6-v2)
    -- NULL if embeddings not enabled
    embed vector(384),

    -- Natural spaced repetition fields
    review_priority FLOAT DEFAULT 0.0,  -- 0.0 to 1.0 urgency in danger zone
    last_review_at BIGINT,
    review_count INTEGER DEFAULT 0,
    cross_domain_count INTEGER DEFAULT 0,

    -- Audit
    indexed_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT
);

-- Indexes for common queries
CREATE INDEX idx_memories_status ON memories(status);
CREATE INDEX idx_memories_last_used ON memories(last_used DESC);
CREATE INDEX idx_memories_created_at ON memories(created_at DESC);
CREATE INDEX idx_memories_use_count ON memories(use_count DESC);
CREATE INDEX idx_memories_strength ON memories(strength DESC);

-- Vector similarity search index (HNSW for fast similarity)
CREATE INDEX idx_memories_embed ON memories USING hnsw (embed vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
    WHERE embed IS NOT NULL;

-- Full-text search on content
CREATE INDEX idx_memories_content_fts ON memories USING gin(to_tsvector('english', content));

-- Composite index for decay scoring queries
CREATE INDEX idx_memories_decay ON memories(status, last_used, use_count, strength)
    WHERE status IN ('active', 'promoted');

-- JSONB index for metadata queries
CREATE INDEX idx_memories_meta_tags ON memories USING gin(meta -> 'tags');
CREATE INDEX idx_memories_meta_source ON memories USING hash(meta ->> 'source');

-- ============================================================================
-- RELATIONSHIPS TABLE (Memory graph edges)
-- ============================================================================

CREATE TABLE relationships (
    -- Identity
    id TEXT PRIMARY KEY,

    -- Graph edges (references to memories)
    from_memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    to_memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,

    -- Relationship semantics
    relation_type TEXT NOT NULL,
        -- Allowed values: 'related', 'causes', 'supports', 'contradicts',
        --                'has_decision', 'consolidated_from'

    -- Strength of relationship
    strength FLOAT NOT NULL DEFAULT 1.0,  -- 0.0 to 1.0

    -- Temporal tracking
    created_at BIGINT NOT NULL,

    -- Custom metadata for relationships
    metadata JSONB NOT NULL DEFAULT '{}',

    -- Audit
    indexed_at BIGINT DEFAULT EXTRACT(EPOCH FROM NOW())::BIGINT
);

-- Indexes for relationship queries
CREATE INDEX idx_relationships_from ON relationships(from_memory_id);
CREATE INDEX idx_relationships_to ON relationships(to_memory_id);
CREATE INDEX idx_relationships_type ON relationships(relation_type);
CREATE INDEX idx_relationships_strength ON relationships(strength DESC);

-- Composite index for graph traversal
CREATE INDEX idx_relationships_from_type ON relationships(from_memory_id, relation_type);
CREATE INDEX idx_relationships_to_type ON relationships(to_memory_id, relation_type);

-- Check constraint on relation types
ALTER TABLE relationships
ADD CONSTRAINT ck_relation_type CHECK (
    relation_type IN ('related', 'causes', 'supports', 'contradicts', 'has_decision', 'consolidated_from')
);

-- Check constraint on strength
ALTER TABLE relationships
ADD CONSTRAINT ck_relationship_strength CHECK (strength >= 0.0 AND strength <= 1.0);

-- ============================================================================
-- VIEWS FOR COMMON DECAY CALCULATIONS
-- ============================================================================

-- Current decay score for each memory (exponential model with 3-day half-life)
CREATE VIEW memories_with_scores AS
SELECT
    id,
    content,
    status,
    created_at,
    last_used,
    use_count,
    strength,

    -- Exponential decay: score = (use_count+1)^0.6 * e^(-λ·Δt) * strength
    -- λ = ln(2) / (3 days in seconds) = 2.673e-6
    -- Δt = current_time - last_used
    (use_count + 1)^0.6 *
    EXP(-2.673e-6 * (EXTRACT(EPOCH FROM NOW())::BIGINT - last_used)) *
    strength AS current_score,

    CASE
        WHEN (use_count + 1)^0.6 *
             EXP(-2.673e-6 * (EXTRACT(EPOCH FROM NOW())::BIGINT - last_used)) *
             strength >= 0.65 THEN 'promote'
        WHEN (use_count + 1)^0.6 *
             EXP(-2.673e-6 * (EXTRACT(EPOCH FROM NOW())::BIGINT - last_used)) *
             strength < 0.05 THEN 'forget'
        ELSE 'keep'
    END AS action,

    -- Danger zone for review (0.15 to 0.35)
    CASE
        WHEN (use_count + 1)^0.6 *
             EXP(-2.673e-6 * (EXTRACT(EPOCH FROM NOW())::BIGINT - last_used)) *
             strength BETWEEN 0.15 AND 0.35 THEN true
        ELSE false
    END AS in_danger_zone

FROM memories
WHERE status IN ('active', 'promoted');

-- Recent memories (last 7 days) ordered by decay score
CREATE VIEW recent_memories AS
SELECT
    m.*,
    (m.use_count + 1)^0.6 *
    EXP(-2.673e-6 * (EXTRACT(EPOCH FROM NOW())::BIGINT - m.last_used)) *
    m.strength AS current_score

FROM memories m
WHERE m.status IN ('active', 'promoted')
  AND m.last_used > EXTRACT(EPOCH FROM NOW())::BIGINT - (7 * 86400)
ORDER BY current_score DESC;

-- Memories in danger zone needing reinforcement
CREATE VIEW memories_for_review AS
SELECT
    m.*,
    review_priority,
    review_count,
    (m.use_count + 1)^0.6 *
    EXP(-2.673e-6 * (EXTRACT(EPOCH FROM NOW())::BIGINT - m.last_used)) *
    m.strength AS current_score

FROM memories m
WHERE m.status IN ('active', 'promoted')
  AND m.review_priority > 0.0
  AND (m.use_count + 1)^0.6 *
      EXP(-2.673e-6 * (EXTRACT(EPOCH FROM NOW())::BIGINT - m.last_used)) *
      m.strength BETWEEN 0.15 AND 0.35
ORDER BY m.review_priority DESC;

-- ============================================================================
-- STORED PROCEDURES FOR DECAY OPERATIONS
-- ============================================================================

-- Calculate current decay score for a single memory
CREATE OR REPLACE FUNCTION calculate_decay_score(
    p_use_count INTEGER,
    p_last_used BIGINT,
    p_strength FLOAT
) RETURNS FLOAT AS $$
BEGIN
    -- Exponential decay with 3-day half-life
    -- λ = ln(2) / (3 * 86400) = 2.673e-6
    RETURN (p_use_count + 1)^0.6 *
           EXP(-2.673e-6 * (EXTRACT(EPOCH FROM NOW())::BIGINT - p_last_used)) *
           p_strength;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Find memories ready for promotion
CREATE OR REPLACE FUNCTION find_memories_to_promote()
RETURNS TABLE(memory_id TEXT, current_score FLOAT, reason TEXT) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        (m.use_count + 1)^0.6 *
        EXP(-2.673e-6 * (EXTRACT(EPOCH FROM NOW())::BIGINT - m.last_used)) *
        m.strength,
        'score_threshold'::TEXT
    FROM memories m
    WHERE m.status = 'active'
      AND (m.use_count + 1)^0.6 *
          EXP(-2.673e-6 * (EXTRACT(EPOCH FROM NOW())::BIGINT - m.last_used)) *
          m.strength >= 0.65

    UNION ALL

    SELECT
        m.id,
        (m.use_count + 1)^0.6 *
        EXP(-2.673e-6 * (EXTRACT(EPOCH FROM NOW())::BIGINT - m.last_used)) *
        m.strength,
        'usage_count'::TEXT
    FROM memories m
    WHERE m.status = 'active'
      AND m.use_count >= 5
      AND m.last_used > EXTRACT(EPOCH FROM NOW())::BIGINT - (14 * 86400);
END;
$$ LANGUAGE plpgsql;

-- Find memories to forget (below threshold)
CREATE OR REPLACE FUNCTION find_memories_to_forget()
RETURNS TABLE(memory_id TEXT, current_score FLOAT) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        (m.use_count + 1)^0.6 *
        EXP(-2.673e-6 * (EXTRACT(EPOCH FROM NOW())::BIGINT - m.last_used)) *
        m.strength
    FROM memories m
    WHERE m.status = 'active'
      AND (m.use_count + 1)^0.6 *
          EXP(-2.673e-6 * (EXTRACT(EPOCH FROM NOW())::BIGINT - m.last_used)) *
          m.strength < 0.05;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- UTILITY FUNCTIONS
-- ============================================================================

-- Search by content (full-text) OR vector similarity
CREATE OR REPLACE FUNCTION search_memories(
    p_query TEXT,
    p_query_vector vector DEFAULT NULL,
    p_limit INTEGER DEFAULT 10,
    p_status TEXT DEFAULT 'active'
)
RETURNS TABLE(
    memory_id TEXT,
    content TEXT,
    score FLOAT,
    search_method TEXT
) AS $$
BEGIN
    -- If vector query provided, use vector similarity
    IF p_query_vector IS NOT NULL THEN
        RETURN QUERY
        SELECT
            m.id,
            m.content,
            (1 - (m.embed <=> p_query_vector))::FLOAT AS score,
            'vector'::TEXT
        FROM memories m
        WHERE m.status = p_status AND m.embed IS NOT NULL
        ORDER BY m.embed <=> p_query_vector
        LIMIT p_limit;
    ELSE
        -- Use full-text search on content
        RETURN QUERY
        SELECT
            m.id,
            m.content,
            ts_rank(to_tsvector('english', m.content),
                   plainto_tsquery('english', p_query))::FLOAT AS score,
            'fulltext'::TEXT
        FROM memories m
        WHERE m.status = p_status
          AND to_tsvector('english', m.content) @@ plainto_tsquery('english', p_query)
        ORDER BY ts_rank(to_tsvector('english', m.content),
                        plainto_tsquery('english', p_query)) DESC
        LIMIT p_limit;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Graph traversal: find related memories via relationships
CREATE OR REPLACE FUNCTION traverse_relationships(
    p_memory_id TEXT,
    p_depth INTEGER DEFAULT 1,
    p_relation_type TEXT DEFAULT NULL
)
RETURNS TABLE(
    memory_id TEXT,
    content TEXT,
    relation_type TEXT,
    strength FLOAT,
    depth INTEGER
) AS $$
WITH RECURSIVE related AS (
    -- Base case: direct relationships
    SELECT
        r.to_memory_id,
        m.content,
        r.relation_type,
        r.strength,
        1 AS depth
    FROM relationships r
    JOIN memories m ON r.to_memory_id = m.id
    WHERE r.from_memory_id = p_memory_id
      AND (p_relation_type IS NULL OR r.relation_type = p_relation_type)

    UNION ALL

    -- Recursive case: follow relationships up to depth
    SELECT
        r.to_memory_id,
        m.content,
        r.relation_type,
        r.strength,
        rel.depth + 1
    FROM related rel
    JOIN relationships r ON r.from_memory_id = rel.memory_id
    JOIN memories m ON r.to_memory_id = m.id
    WHERE rel.depth < p_depth
      AND (p_relation_type IS NULL OR r.relation_type = p_relation_type)
)
SELECT * FROM related;
$$ LANGUAGE sql;

-- ============================================================================
-- AUDIT & MAINTENANCE
-- ============================================================================

-- Track when memories were last indexed (for reindex scheduling)
CREATE TABLE memory_audit (
    memory_id TEXT REFERENCES memories(id) ON DELETE CASCADE,
    operation TEXT NOT NULL,  -- 'created', 'updated', 'promoted', 'forgotten'
    score_at_time FLOAT,
    triggered_at BIGINT NOT NULL,
    PRIMARY KEY (memory_id, triggered_at)
);

CREATE INDEX idx_memory_audit_triggered ON memory_audit(triggered_at DESC);

-- ============================================================================
-- CONSTRAINTS & DATA VALIDATION
-- ============================================================================

-- Strength must be between 0 and 2
ALTER TABLE memories
ADD CONSTRAINT ck_memory_strength CHECK (strength >= 0.0 AND strength <= 2.0);

-- Status must be valid
ALTER TABLE memories
ADD CONSTRAINT ck_memory_status CHECK (status IN ('active', 'promoted', 'archived'));

-- Review priority must be 0-1
ALTER TABLE memories
ADD CONSTRAINT ck_review_priority CHECK (review_priority >= 0.0 AND review_priority <= 1.0);

-- Temporal constraints
ALTER TABLE memories
ADD CONSTRAINT ck_memory_timestamps CHECK (created_at > 0 AND last_used >= created_at);

-- No self-referential relationships
ALTER TABLE relationships
ADD CONSTRAINT ck_no_self_ref CHECK (from_memory_id != to_memory_id);
