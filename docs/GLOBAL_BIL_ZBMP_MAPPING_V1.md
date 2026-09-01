# ZBMP × Global BIL｜Capability Mapping v1

> 2026-09-01
> Scope: global brand intelligence integration
> Status: mapping / shadow design only

## 1. Core decision

ZBMP does **not** create a second brand database. Existing brand entities remain the source of identity; Global BIL adds analytical dimensions and evidence-backed observations around those entities.

```text
Existing ZBMP Brand Entity
        ↓
Entity Resolution
        ↓
Global BIL Capability Layer
        ↓
Evidence / Observation / Insight
        ↓
ZBMP Intelligence
```

## 2. Existing repository assets identified

Current repository already contains brand-oriented capabilities including:

- `brand_directory.json`
- `brand_knowledge_base.py`
- `brand_report_generator.py`
- `brand_stats_recompute.py`
- `brand_websites.json`
- `case_deep_analysis.py`
- `case_library.json`
- `topic_campaign.py`
- `intelligence.py`
- `ai_learning_engine.py`
- `data_feedback_loop.py`
- `database.py`
- `database_migrations.py`

The current `brand_directory.json` is a Guangzhou Taikoo Hui directory snapshot containing 198 entities. It is therefore treated as an existing local/channel dataset, not as the global brand master.

## 3. Reuse map

| BIL capability | Existing ZBMP asset | Decision |
|---|---|---|
| Brand Entity | brand_directory / brand knowledge | REUSE + globalize aliases |
| Brand Knowledge | brand_knowledge_base.py | REUSE |
| Case Library | case_library.json / case_deep_analysis.py | REUSE + add global mechanism taxonomy |
| Intelligence | intelligence.py | REUSE / extend via adapter |
| Campaign | topic_campaign.py | REUSE / normalize campaign entity |
| Stats | brand_stats_recompute.py | REUSE calculations where compatible |
| Reporting | brand_report_generator.py | REUSE presentation layer, add BIL sections |
| Data feedback | data_feedback_loop.py | REUSE |
| AI learning | ai_learning_engine.py | REUSE with BIL labels/evidence contract |
| Runtime DB | database.py / migrations | REUSE DB infrastructure; BIL tables additive only |
| Local store directory | brand_directory.json | REUSE as one Geography/Channel source |

## 4. Initial capability matrix from verified repository evidence

### Strong / already present

- Brand identity and directory data
- Brand knowledge storage and retrieval
- Case analysis
- Brand reporting
- Brand statistics
- Campaign/topic analysis
- Intelligence layer
- AI learning / feedback infrastructure
- SQLite + migration infrastructure

### Partial / requires normalization

- Global market model
- Brand account / follower time series
- Social voice taxonomy
- UGC classification
- Consumer intent
- Creator intelligence
- Product signals
- Campaign performance evidence
- Geography hierarchy
- Store/channel lifecycle
- Competitive benchmark
- Brand lifecycle
- Evidence provenance

### Missing as explicit BIL domain contracts

- `Brand × Market × Platform` observation model
- UGC vs KOL/KOC vs Official vs Commercial normalized classification
- Consumer-intent taxonomy
- Evidence-first brand insight object
- Cross-market benchmark snapshot
- Lifecycle snapshot with time-window requirements
- Confidence / data-quality state attached to every derived metric

## 5. Initial priority brands from the visible local directory

These are not yet declared global benchmark winners. They are **priority candidates** because the current directory visibly contains strong luxury / designer / lifestyle anchors:

- LOUIS VUITTON
- DIOR
- PRADA
- Gucci
- CHANEL
- HERMÈS
- THOM BROWNE
- FERRAGAMO
- Acne Studios
- MARNI
- JIL SANDER
- Maison Margiela
- SAINT LAURENT
- Loro Piana
- FENDI
- BURBERRY
- MIU MIU
- Alexander McQueen
- ZEGNA
- RIMOWA
- Roger Vivier
- VERSACE

These entities should be resolved against the global brand master before any global metrics are attached. Store names containing city/venue suffixes must never become separate global brands.

## 6. Global benchmark candidate pool

The benchmark pool should be broader than the local directory and deliberately cover different mechanisms:

### Luxury / designer

Jacquemus, Miu Miu, Loewe, Prada, Gucci, Bottega Veneta, The Row, Simone Rocha, SHUSHU/TONG, Molly Goddard, Acne Studios, Coperni.

### Outdoor / sport

Patagonia, Arc'teryx, Salomon, On, HOKA, Nike, Adidas, Lululemon, Gymshark.

### Beauty

Glossier, The Ordinary, CeraVe, Aesop, Rare Beauty, Rhode.

### Lifestyle / culture

Gentle Monster, Crocs, Dr. Martens, Uniqlo.

### Portfolio / global operating models

PVH portfolio, L'Oréal portfolio, Shiseido portfolio, Authentic Brands Group portfolio.

The portfolio cases are used to learn multi-brand governance rather than treated as ordinary single-brand entities.

## 7. BIL capability coverage target

Every benchmark brand should eventually support:

```text
01 Brand DNA
02 Market Presence
03 Audience
04 Social Voice
05 UGC
06 Creator
07 Product
08 Campaign
09 Store / Channel
10 Community
11 Competitor
12 Lifecycle
13 Consumer Intent
14 Evidence / Confidence
```

## 8. Global geography model

The Guangzhou directory is one local market/channel observation. It must map into:

```text
Global
 └─ Country
     └─ Region
         └─ City
             └─ District
                 └─ Commercial Area
                     └─ Venue
                         └─ Store / Channel
```

Do not encode Guangzhou assumptions into the BIL schema.

## 9. Research-derived mechanisms to encode

### Social → Consumer Insight

PVH demonstrates the value of using social intelligence as consumer insight and linking it with marketing/product teams. This supports a first-class `consumer_signal` layer.

### Conversation → Purchase Intent

Brandwatch's purchase-intent methodology shows why mention volume must be separated from purchase-intent language. BIL therefore stores `consumer_intent` separately from `voice`.

### Global → Local

Samsung's multi-market model shows that centrally defined concepts need native-market localization. BIL therefore separates global taxonomy from local language/query packs.

### Brand → Campaign → Brand Health

YouGov and Comscore examples support measuring brand health and purchase intent across campaign periods rather than treating campaign performance as engagement only.

### Brand → Competitor → Market

The Body Shop and Samsung cases support continuous competitor and market-context monitoring.

### Creator → Community → Advocacy

Current creator-market evidence supports evaluating resonance, credibility and community fit alongside reach; follower count must not be the sole creator metric.

## 10. Data quality rules

Every BIL observation must carry:

```text
source
source_type
observed_at
captured_at
market
platform
entity_resolution_status
verification_status
confidence
quality_status
model_version
```

Dynamic values such as followers, engagement and store status require timestamps.

A missing source is `UNKNOWN`, not zero.

A failed collection is `FAILED`, not zero.

An unverified current claim is `NOT_VERIFIED`, not current fact.

## 11. Migration rule

Do not directly migrate BIL tables into the production `data/monitor.db` until:

1. schema validation passes;
2. migration is executed against an isolated `ZBC_DB_PATH` staging database;
3. existing CTH-POMS tests pass;
4. BIL smoke tests pass;
5. rollback is verified;
6. production impact is explicitly approved.

## 12. Next execution stage

```text
Current
 ↓
Global case research + mechanism extraction          DONE/ONGOING
 ↓
ZBMP asset inventory                                  IN PROGRESS
 ↓
Brand × BIL capability matrix                        NEXT
 ↓
Global entity resolution                              NEXT
 ↓
Staging DB migration                                  NEXT
 ↓
Populate research/evidence seed                       NEXT
 ↓
Shadow adapter                                       NEXT
 ↓
BIL validation                                        NEXT
 ↓
Production integration                                LATER
```

No production collector, subject rule, risk engine, event aggregation or report SQL is authorized to change under this mapping document.
