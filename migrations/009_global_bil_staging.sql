-- Z-Brand-Core Global BIL v1 staging migration
-- SAFETY: staging-only definition. Do NOT apply directly to production monitor.db.
-- Execute only against an isolated DB selected via ZBC_DB_PATH after schema validation.

BEGIN;

CREATE TABLE IF NOT EXISTS bi_brand_entity (
  brand_id TEXT PRIMARY KEY,
  canonical_name TEXT NOT NULL,
  brand_type TEXT DEFAULT 'single_brand',
  category TEXT DEFAULT '',
  sub_category TEXT DEFAULT '',
  price_segment TEXT DEFAULT '',
  origin_country TEXT DEFAULT '',
  status TEXT DEFAULT 'active',
  entity_resolution_status TEXT DEFAULT 'verified',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bi_brand_alias (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  brand_id TEXT NOT NULL,
  alias TEXT NOT NULL,
  language TEXT DEFAULT '',
  alias_type TEXT DEFAULT 'name',
  source TEXT DEFAULT '',
  UNIQUE(brand_id, alias),
  FOREIGN KEY(brand_id) REFERENCES bi_brand_entity(brand_id)
);

CREATE TABLE IF NOT EXISTS bi_brand_market (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  brand_id TEXT NOT NULL,
  country_code TEXT DEFAULT '',
  region_code TEXT DEFAULT '',
  city_code TEXT DEFAULT '',
  district TEXT DEFAULT '',
  commercial_area TEXT DEFAULT '',
  presence_type TEXT DEFAULT 'unknown',
  status TEXT DEFAULT 'unknown',
  observed_at TEXT DEFAULT '',
  source TEXT DEFAULT '',
  confidence REAL DEFAULT 0,
  FOREIGN KEY(brand_id) REFERENCES bi_brand_entity(brand_id)
);

CREATE TABLE IF NOT EXISTS bi_brand_account (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  brand_id TEXT NOT NULL,
  platform TEXT NOT NULL,
  account_type TEXT DEFAULT 'unknown',
  account_name TEXT DEFAULT '',
  handle TEXT DEFAULT '',
  profile_url TEXT DEFAULT '',
  follower_count INTEGER DEFAULT NULL,
  follower_captured_at TEXT DEFAULT '',
  source TEXT DEFAULT '',
  verification_status TEXT DEFAULT 'unknown',
  FOREIGN KEY(brand_id) REFERENCES bi_brand_entity(brand_id)
);

CREATE TABLE IF NOT EXISTS bi_mention (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  brand_id TEXT NOT NULL,
  platform TEXT DEFAULT '',
  source_content_id TEXT DEFAULT '',
  source_url TEXT DEFAULT '',
  published_at TEXT DEFAULT '',
  captured_at TEXT DEFAULT '',
  author_type TEXT DEFAULT 'unknown',
  content_type TEXT DEFAULT 'unknown',
  engagement_snapshot TEXT DEFAULT '{}',
  market_code TEXT DEFAULT '',
  quality_status TEXT DEFAULT 'unknown',
  confidence REAL DEFAULT 0,
  UNIQUE(platform, source_content_id),
  FOREIGN KEY(brand_id) REFERENCES bi_brand_entity(brand_id)
);

CREATE TABLE IF NOT EXISTS bi_ugc_observation (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  mention_id INTEGER,
  brand_id TEXT NOT NULL,
  ugc_type TEXT DEFAULT 'unknown',
  consumer_intent TEXT DEFAULT 'none',
  content_scene TEXT DEFAULT 'other',
  sentiment TEXT DEFAULT 'neutral',
  topic TEXT DEFAULT '',
  product_signal TEXT DEFAULT '',
  creator_signal TEXT DEFAULT '',
  confidence REAL DEFAULT 0,
  model_version TEXT DEFAULT '',
  rule_version TEXT DEFAULT '',
  observed_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(mention_id) REFERENCES bi_mention(id),
  FOREIGN KEY(brand_id) REFERENCES bi_brand_entity(brand_id)
);

CREATE TABLE IF NOT EXISTS bi_product_signal (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  brand_id TEXT NOT NULL,
  product_key TEXT DEFAULT '',
  product_name TEXT DEFAULT '',
  signal_type TEXT DEFAULT '',
  signal_value REAL DEFAULT 0,
  period_start TEXT DEFAULT '',
  period_end TEXT DEFAULT '',
  source_count INTEGER DEFAULT 0,
  confidence REAL DEFAULT 0,
  FOREIGN KEY(brand_id) REFERENCES bi_brand_entity(brand_id)
);

CREATE TABLE IF NOT EXISTS bi_creator_signal (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  brand_id TEXT NOT NULL,
  platform TEXT DEFAULT '',
  creator_key TEXT DEFAULT '',
  creator_type TEXT DEFAULT 'unknown',
  reach_snapshot INTEGER DEFAULT NULL,
  engagement_rate REAL DEFAULT NULL,
  resonance_score REAL DEFAULT NULL,
  content_count INTEGER DEFAULT 0,
  consumer_intent_rate REAL DEFAULT NULL,
  period_start TEXT DEFAULT '',
  period_end TEXT DEFAULT '',
  source TEXT DEFAULT '',
  FOREIGN KEY(brand_id) REFERENCES bi_brand_entity(brand_id)
);

CREATE TABLE IF NOT EXISTS bi_campaign (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  brand_id TEXT NOT NULL,
  campaign_key TEXT NOT NULL,
  campaign_name TEXT DEFAULT '',
  market_code TEXT DEFAULT '',
  start_at TEXT DEFAULT '',
  end_at TEXT DEFAULT '',
  objective TEXT DEFAULT '',
  voice_delta REAL DEFAULT NULL,
  ugc_delta REAL DEFAULT NULL,
  intent_delta REAL DEFAULT NULL,
  source TEXT DEFAULT '',
  confidence REAL DEFAULT 0,
  UNIQUE(brand_id, campaign_key, market_code),
  FOREIGN KEY(brand_id) REFERENCES bi_brand_entity(brand_id)
);

CREATE TABLE IF NOT EXISTS bi_benchmark_snapshot (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  benchmark_group TEXT NOT NULL,
  brand_id TEXT NOT NULL,
  metric TEXT NOT NULL,
  value REAL DEFAULT NULL,
  unit TEXT DEFAULT '',
  period_start TEXT DEFAULT '',
  period_end TEXT DEFAULT '',
  data_quality TEXT DEFAULT 'unknown',
  source_count INTEGER DEFAULT 0,
  FOREIGN KEY(brand_id) REFERENCES bi_brand_entity(brand_id)
);

CREATE TABLE IF NOT EXISTS bi_lifecycle_snapshot (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  brand_id TEXT NOT NULL,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  social_voice_index REAL DEFAULT NULL,
  ugc_index REAL DEFAULT NULL,
  consumer_intent_index REAL DEFAULT NULL,
  offline_presence_index REAL DEFAULT NULL,
  momentum_index REAL DEFAULT NULL,
  lifecycle_stage TEXT DEFAULT 'unknown',
  confidence REAL DEFAULT 0,
  model_version TEXT DEFAULT '',
  FOREIGN KEY(brand_id) REFERENCES bi_brand_entity(brand_id)
);

CREATE TABLE IF NOT EXISTS bi_case_study (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  brand_id TEXT DEFAULT '',
  case_key TEXT UNIQUE NOT NULL,
  brand_name TEXT NOT NULL,
  market_scope TEXT DEFAULT 'global',
  category TEXT DEFAULT '',
  outcome_type TEXT DEFAULT '',
  source_url TEXT DEFAULT '',
  source_published_at TEXT DEFAULT '',
  evidence_status TEXT DEFAULT 'unverified',
  summary TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS bi_case_mechanism (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id INTEGER NOT NULL,
  mechanism_stage TEXT NOT NULL,
  mechanism TEXT NOT NULL,
  evidence TEXT DEFAULT '',
  transferability TEXT DEFAULT 'unknown',
  FOREIGN KEY(case_id) REFERENCES bi_case_study(id)
);

CREATE TABLE IF NOT EXISTS bi_evidence (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity_type TEXT NOT NULL,
  entity_key TEXT NOT NULL,
  claim TEXT NOT NULL,
  source_type TEXT DEFAULT '',
  source_url TEXT DEFAULT '',
  observed_at TEXT DEFAULT '',
  captured_at TEXT DEFAULT CURRENT_TIMESTAMP,
  market_code TEXT DEFAULT '',
  platform TEXT DEFAULT '',
  verification_status TEXT DEFAULT 'unverified',
  quality_status TEXT DEFAULT 'unknown',
  confidence REAL DEFAULT 0,
  model_version TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS bi_insight (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  brand_id TEXT NOT NULL,
  insight_type TEXT DEFAULT '',
  title TEXT NOT NULL,
  finding TEXT NOT NULL,
  evidence_ids TEXT DEFAULT '[]',
  recommended_action TEXT DEFAULT '',
  confidence REAL DEFAULT 0,
  generated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  model_version TEXT DEFAULT '',
  FOREIGN KEY(brand_id) REFERENCES bi_brand_entity(brand_id)
);

CREATE INDEX IF NOT EXISTS idx_bi_market_brand ON bi_brand_market(brand_id);
CREATE INDEX IF NOT EXISTS idx_bi_account_brand ON bi_brand_account(brand_id);
CREATE INDEX IF NOT EXISTS idx_bi_mention_brand_time ON bi_mention(brand_id, published_at);
CREATE INDEX IF NOT EXISTS idx_bi_ugc_brand_time ON bi_ugc_observation(brand_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_bi_product_brand ON bi_product_signal(brand_id);
CREATE INDEX IF NOT EXISTS idx_bi_creator_brand ON bi_creator_signal(brand_id);
CREATE INDEX IF NOT EXISTS idx_bi_campaign_brand ON bi_campaign(brand_id);
CREATE INDEX IF NOT EXISTS idx_bi_benchmark_group ON bi_benchmark_snapshot(benchmark_group, metric);
CREATE INDEX IF NOT EXISTS idx_bi_lifecycle_brand ON bi_lifecycle_snapshot(brand_id, period_end);
CREATE INDEX IF NOT EXISTS idx_bi_evidence_entity ON bi_evidence(entity_type, entity_key);
CREATE INDEX IF NOT EXISTS idx_bi_insight_brand ON bi_insight(brand_id, generated_at);

COMMIT;
