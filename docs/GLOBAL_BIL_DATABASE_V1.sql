-- ZBMP / Global Brand Intelligence Layer
-- Database contract v1.0
-- ADDITIVE / STAGING FIRST
-- This schema is intentionally isolated from CTH-POMS production tables.
-- Do not execute against production data/monitor.db until migration review + tests pass.

CREATE TABLE IF NOT EXISTS bi_brand_entity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE,
    name_local TEXT DEFAULT '',
    category TEXT DEFAULT '',
    sub_category TEXT DEFAULT '',
    price_segment TEXT DEFAULT '',
    origin_country TEXT DEFAULT '',
    status TEXT DEFAULT 'active',
    entity_confidence REAL DEFAULT 0,
    source TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bi_brand_alias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id INTEGER NOT NULL,
    alias TEXT NOT NULL,
    alias_normalized TEXT NOT NULL,
    language TEXT DEFAULT '',
    source TEXT DEFAULT '',
    UNIQUE(brand_id, alias_normalized),
    FOREIGN KEY(brand_id) REFERENCES bi_brand_entity(id)
);

CREATE TABLE IF NOT EXISTS bi_brand_account (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id INTEGER NOT NULL,
    platform TEXT NOT NULL,
    account_name TEXT DEFAULT '',
    account_handle TEXT DEFAULT '',
    profile_url TEXT DEFAULT '',
    account_type TEXT DEFAULT 'unknown',
    follower_count INTEGER DEFAULT 0,
    follower_captured_at TEXT DEFAULT '',
    verification_status TEXT DEFAULT 'unknown',
    source TEXT DEFAULT '',
    FOREIGN KEY(brand_id) REFERENCES bi_brand_entity(id)
);

CREATE TABLE IF NOT EXISTS bi_market_presence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id INTEGER NOT NULL,
    country_code TEXT DEFAULT '',
    region TEXT DEFAULT '',
    city TEXT DEFAULT '',
    district TEXT DEFAULT '',
    commercial_area TEXT DEFAULT '',
    venue TEXT DEFAULT '',
    presence_type TEXT DEFAULT 'unknown',
    store_name TEXT DEFAULT '',
    status TEXT DEFAULT 'unknown',
    verified_at TEXT DEFAULT '',
    source TEXT DEFAULT '',
    FOREIGN KEY(brand_id) REFERENCES bi_brand_entity(id)
);

CREATE TABLE IF NOT EXISTS bi_mention (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id INTEGER NOT NULL,
    platform TEXT DEFAULT '',
    source_id TEXT DEFAULT '',
    source_url TEXT DEFAULT '',
    title TEXT DEFAULT '',
    content_excerpt TEXT DEFAULT '',
    published_at TEXT DEFAULT '',
    captured_at TEXT DEFAULT CURRENT_TIMESTAMP,
    author_type TEXT DEFAULT 'unknown',
    content_type TEXT DEFAULT 'unknown',
    sentiment TEXT DEFAULT 'neutral',
    quality_status TEXT DEFAULT 'review',
    source TEXT DEFAULT '',
    UNIQUE(platform, source_id),
    FOREIGN KEY(brand_id) REFERENCES bi_brand_entity(id)
);

CREATE TABLE IF NOT EXISTS bi_ugc_observation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mention_id INTEGER NOT NULL UNIQUE,
    ugc_type TEXT DEFAULT 'unknown',
    consumer_intent TEXT DEFAULT 'none',
    content_scene TEXT DEFAULT 'other',
    advocacy_signal TEXT DEFAULT 'none',
    co_development_signal TEXT DEFAULT 'none',
    confidence REAL DEFAULT 0,
    model_version TEXT DEFAULT '',
    rule_version TEXT DEFAULT '',
    human_adopted INTEGER DEFAULT 0,
    FOREIGN KEY(mention_id) REFERENCES bi_mention(id)
);

CREATE TABLE IF NOT EXISTS bi_product_signal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id INTEGER NOT NULL,
    product_name TEXT DEFAULT '',
    product_aliases TEXT DEFAULT '[]',
    mention_count INTEGER DEFAULT 0,
    ugc_count INTEGER DEFAULT 0,
    purchase_intent_count INTEGER DEFAULT 0,
    sentiment_score REAL DEFAULT 0,
    period_start TEXT DEFAULT '',
    period_end TEXT DEFAULT '',
    source_count INTEGER DEFAULT 0,
    FOREIGN KEY(brand_id) REFERENCES bi_brand_entity(id)
);

CREATE TABLE IF NOT EXISTS bi_creator_signal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id INTEGER NOT NULL,
    platform TEXT DEFAULT '',
    creator_id TEXT DEFAULT '',
    creator_name TEXT DEFAULT '',
    creator_type TEXT DEFAULT 'unknown',
    follower_count INTEGER DEFAULT 0,
    brand_mentions INTEGER DEFAULT 0,
    engagement_total INTEGER DEFAULT 0,
    ugc_generated INTEGER DEFAULT 0,
    advocacy_score REAL DEFAULT 0,
    period_start TEXT DEFAULT '',
    period_end TEXT DEFAULT '',
    FOREIGN KEY(brand_id) REFERENCES bi_brand_entity(id)
);

CREATE TABLE IF NOT EXISTS bi_campaign (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id INTEGER NOT NULL,
    campaign_name TEXT DEFAULT '',
    campaign_type TEXT DEFAULT '',
    market TEXT DEFAULT '',
    start_at TEXT DEFAULT '',
    end_at TEXT DEFAULT '',
    mention_count INTEGER DEFAULT 0,
    ugc_count INTEGER DEFAULT 0,
    creator_count INTEGER DEFAULT 0,
    consumer_intent_count INTEGER DEFAULT 0,
    sentiment_score REAL DEFAULT 0,
    evidence_status TEXT DEFAULT 'review',
    source TEXT DEFAULT '',
    FOREIGN KEY(brand_id) REFERENCES bi_brand_entity(id)
);

CREATE TABLE IF NOT EXISTS bi_benchmark_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    benchmark_group TEXT NOT NULL,
    brand_id INTEGER NOT NULL,
    metric TEXT NOT NULL,
    value REAL DEFAULT 0,
    period_start TEXT DEFAULT '',
    period_end TEXT DEFAULT '',
    data_quality TEXT DEFAULT 'review',
    source_count INTEGER DEFAULT 0,
    FOREIGN KEY(brand_id) REFERENCES bi_brand_entity(id)
);

CREATE TABLE IF NOT EXISTS bi_lifecycle_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id INTEGER NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    social_voice_index REAL DEFAULT 0,
    organic_ugc_index REAL DEFAULT 0,
    consumer_intent_index REAL DEFAULT 0,
    offline_presence_index REAL DEFAULT 0,
    momentum_index REAL DEFAULT 0,
    lifecycle_stage TEXT DEFAULT 'unknown',
    confidence REAL DEFAULT 0,
    calculation_version TEXT DEFAULT '',
    FOREIGN KEY(brand_id) REFERENCES bi_brand_entity(id)
);

CREATE TABLE IF NOT EXISTS bi_case_study (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id INTEGER,
    title TEXT NOT NULL,
    market TEXT DEFAULT '',
    category TEXT DEFAULT '',
    problem TEXT DEFAULT '',
    action TEXT DEFAULT '',
    result TEXT DEFAULT '',
    lesson TEXT DEFAULT '',
    evidence_status TEXT DEFAULT 'review',
    source TEXT DEFAULT '',
    url TEXT DEFAULT '',
    published_at TEXT DEFAULT '',
    FOREIGN KEY(brand_id) REFERENCES bi_brand_entity(id)
);

CREATE TABLE IF NOT EXISTS bi_case_mechanism (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL,
    stage_order INTEGER DEFAULT 0,
    signal TEXT DEFAULT '',
    consumer_response TEXT DEFAULT '',
    brand_action TEXT DEFAULT '',
    business_effect TEXT DEFAULT '',
    mechanism_type TEXT DEFAULT '',
    FOREIGN KEY(case_id) REFERENCES bi_case_study(id)
);

CREATE TABLE IF NOT EXISTS bi_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    claim TEXT NOT NULL,
    evidence_type TEXT DEFAULT 'web',
    source_name TEXT DEFAULT '',
    source_url TEXT DEFAULT '',
    source_published_at TEXT DEFAULT '',
    observed_at TEXT DEFAULT '',
    market TEXT DEFAULT '',
    platform TEXT DEFAULT '',
    quality_status TEXT DEFAULT 'review',
    confidence REAL DEFAULT 0,
    notes TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS bi_insight (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id INTEGER NOT NULL,
    insight_type TEXT DEFAULT '',
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    period_start TEXT DEFAULT '',
    period_end TEXT DEFAULT '',
    evidence_ids TEXT DEFAULT '[]',
    methodology_version TEXT DEFAULT '',
    confidence REAL DEFAULT 0,
    status TEXT DEFAULT 'draft',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(brand_id) REFERENCES bi_brand_entity(id)
);

CREATE INDEX IF NOT EXISTS idx_bi_brand_alias ON bi_brand_alias(alias_normalized);
CREATE INDEX IF NOT EXISTS idx_bi_account_brand ON bi_brand_account(brand_id);
CREATE INDEX IF NOT EXISTS idx_bi_market_brand ON bi_market_presence(brand_id);
CREATE INDEX IF NOT EXISTS idx_bi_market_geo ON bi_market_presence(country_code, city, commercial_area);
CREATE INDEX IF NOT EXISTS idx_bi_mention_brand ON bi_mention(brand_id);
CREATE INDEX IF NOT EXISTS idx_bi_mention_platform ON bi_mention(platform, published_at);
CREATE INDEX IF NOT EXISTS idx_bi_product_brand ON bi_product_signal(brand_id);
CREATE INDEX IF NOT EXISTS idx_bi_creator_brand ON bi_creator_signal(brand_id);
CREATE INDEX IF NOT EXISTS idx_bi_campaign_brand ON bi_campaign(brand_id);
CREATE INDEX IF NOT EXISTS idx_bi_benchmark_group ON bi_benchmark_snapshot(benchmark_group, metric);
CREATE INDEX IF NOT EXISTS idx_bi_lifecycle_brand ON bi_lifecycle_snapshot(brand_id, period_end);
CREATE INDEX IF NOT EXISTS idx_bi_evidence_entity ON bi_evidence(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_bi_insight_brand ON bi_insight(brand_id, created_at);
