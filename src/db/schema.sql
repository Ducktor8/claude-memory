-- Claude Memory System - Database Schema
-- SQLite + FTS5 Full-Text Search

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- Memory contexts
CREATE TABLE IF NOT EXISTS contexts (
    name TEXT PRIMARY KEY,
    description TEXT,
    parent TEXT REFERENCES contexts(name) ON DELETE SET NULL,
    directory_patterns TEXT DEFAULT '[]',  -- JSON array of glob patterns
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Memories
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    context TEXT NOT NULL REFERENCES contexts(name) ON DELETE CASCADE,
    type TEXT CHECK(type IN ('decision', 'error_fix', 'pattern', 'preference', 'note')),
    content TEXT NOT NULL,
    summary TEXT,                            -- 1-2 lines for search
    keywords TEXT,                           -- CSV: "docker,container,deploy"
    source_session TEXT,                     -- Claude session ID
    source_file TEXT,                        -- Related file (optional)
    importance REAL DEFAULT 0.5 CHECK(importance >= 0.0 AND importance <= 1.0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP,
    access_count INTEGER DEFAULT 0
);

-- Full-Text Search Index (FTS5)
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    summary,
    keywords,
    content,
    content='memories',
    content_rowid='id',
    tokenize='porter unicode61'  -- Stemming for Italian/English
);

-- Trigger to sync FTS on INSERT
CREATE TRIGGER IF NOT EXISTS memories_fts_insert AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, summary, keywords, content)
    VALUES (new.id, new.summary, new.keywords, new.content);
END;

-- Trigger to sync FTS on DELETE
CREATE TRIGGER IF NOT EXISTS memories_fts_delete AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, summary, keywords, content)
    VALUES ('delete', old.id, old.summary, old.keywords, old.content);
END;

-- Trigger to sync FTS on UPDATE
CREATE TRIGGER IF NOT EXISTS memories_fts_update AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, summary, keywords, content)
    VALUES ('delete', old.id, old.summary, old.keywords, old.content);
    INSERT INTO memories_fts(rowid, summary, keywords, content)
    VALUES (new.id, new.summary, new.keywords, new.content);
END;

-- Directory -> context mapping
CREATE TABLE IF NOT EXISTS directory_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT NOT NULL UNIQUE,            -- Glob: ~/work/*
    context TEXT NOT NULL REFERENCES contexts(name) ON DELETE CASCADE,
    priority INTEGER DEFAULT 0               -- Higher = greater priority
);

-- Sessions (for tracking)
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    context TEXT REFERENCES contexts(name),
    working_directory TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    memories_created INTEGER DEFAULT 0
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_memories_context ON memories(context);
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance DESC);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_directory_mappings_priority ON directory_mappings(priority DESC);

-- Insert default contexts
INSERT OR IGNORE INTO contexts (name, description, directory_patterns) VALUES
    ('global', 'Shared memory always active', '[]'),
    ('work', 'Work projects', '["~/work/*", "~/WebstormProjects/*", "~/IdeaProjects/*"]'),
    ('trading', 'Trading and finance', '["~/trading/*", "~/finance/*"]'),
    ('local', 'System and local configurations', '["~/.*", "~/.config/*"]'),
    ('personal', 'Personal projects', '["~/personal/*", "~/Projects/*"]');

-- Insert default directory mappings
INSERT OR IGNORE INTO directory_mappings (pattern, context, priority) VALUES
    ('~/work/*', 'work', 100),
    ('~/WebstormProjects/*', 'work', 100),
    ('~/IdeaProjects/*', 'work', 100),
    ('~/trading/*', 'trading', 100),
    ('~/finance/*', 'trading', 90),
    ('~/personal/*', 'personal', 100),
    ('~/Projects/*', 'personal', 90),
    ('~/.config/*', 'local', 80),
    ('~/.*', 'local', 50),
    ('~/', 'local', 1);  -- Lowest fallback
