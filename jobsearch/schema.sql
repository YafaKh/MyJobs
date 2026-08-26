-- Companies/feeds we pull jobs from, plus health tracking.
CREATE TABLE IF NOT EXISTS sources (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    name                  TEXT NOT NULL,
    careers_url           TEXT NOT NULL,
    source_kind           TEXT NOT NULL DEFAULT 'saved',   -- saved | openweb
    ats_type              TEXT,                            -- greenhouse | lever | ashby | workable | recruitee | smartrecruiters | personio | generic_html
    ats_identifier        TEXT,                            -- board token / company slug used to hit the ATS API
    is_active             INTEGER NOT NULL DEFAULT 1,
    last_checked_at       TEXT,
    last_success_at       TEXT,
    last_error            TEXT,
    consecutive_failures  INTEGER NOT NULL DEFAULT 0,
    created_at            TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Permanent record of every job we've ever seen, so a deleted job doesn't
-- reappear as "new" on a later run. Deliberately separate from `jobs`.
CREATE TABLE IF NOT EXISTS seen_ledger (
    job_hash      TEXT PRIMARY KEY,
    first_seen_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Full job records. Rows for unstarred jobs are deleted 7 days after
-- first_seen_at (see storage.job_retention_days in config.yaml).
CREATE TABLE IF NOT EXISTS jobs (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    job_hash              TEXT NOT NULL UNIQUE REFERENCES seen_ledger(job_hash),
    source_id             INTEGER REFERENCES sources(id),
    source_kind           TEXT NOT NULL DEFAULT 'saved',   -- saved | openweb
    title                 TEXT NOT NULL,
    company               TEXT NOT NULL,
    url                   TEXT NOT NULL,
    description_raw       TEXT,
    posted_at             TEXT,

    -- LLM-extracted fields
    location_requirement  TEXT,
    work_authorization    TEXT,
    arrangement           TEXT,                            -- remote | hybrid | onsite
    sponsorship           TEXT,                             -- true | false | unknown
    timezone_overlap      TEXT,
    eligible_for_me       INTEGER,                          -- 0 | 1, NULL until extracted
    eligibility_reason    TEXT,
    extracted_at          TEXT,

    -- scoring / prefilter
    score                 REAL,
    title_matched         INTEGER NOT NULL DEFAULT 0,
    keyword_matched       INTEGER NOT NULL DEFAULT 0,

    -- dashboard state
    starred               INTEGER NOT NULL DEFAULT 0,
    hidden                INTEGER NOT NULL DEFAULT 0,

    first_seen_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_jobs_eligible ON jobs (eligible_for_me);
CREATE INDEX IF NOT EXISTS idx_jobs_hidden_starred ON jobs (hidden, starred);
CREATE INDEX IF NOT EXISTS idx_jobs_first_seen ON jobs (first_seen_at);

-- Manual corrections made from the dashboard, replayed as few-shot examples
-- in the next extraction run's prompt.
CREATE TABLE IF NOT EXISTS corrections (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    job_hash      TEXT REFERENCES seen_ledger(job_hash),
    text_snippet  TEXT NOT NULL,
    field_name    TEXT NOT NULL,
    wrong_value   TEXT,
    right_value   TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- One row per calendar day, counting LLM extraction calls made that day so a
-- run can stop before blowing the free-tier daily cap.
CREATE TABLE IF NOT EXISTS llm_usage (
    usage_date  TEXT PRIMARY KEY,
    calls_made  INTEGER NOT NULL DEFAULT 0
);
