# Z-Brand Core Architecture Audit v6.0

## Purpose

Based on the current repository architecture, this document is used as the implementation baseline before further upgrades.

## Current Architecture Understanding

Z-Brand Core is the common platform base.

```
DCC
 |
 | R&D audit / planning / controlled upgrade
 |
Z-Brand-Core
 |
 +-- CTH-POMS
 |      Production delivery system
 |
 +-- ZBMP
        Controlled enhancement capability layer
```

## Core Principles

1. Production stability has priority.
2. New capabilities must be added through extension points, not replace production chains.
3. Data enters through adapters and flows through unified content/event processing.
4. AI is an enhancement layer, not the source of business truth.

## Data Flow Baseline

```
Data Source
 ↓
Platform Adapter
 ↓
Discovery / Detail / Comment
 ↓
Normalization
 ↓
Quality Check
 ↓
Subject Filtering
 ↓
Storage
 ↓
Rules + AI Enhancement
 ↓
Events / Trends / Reports
```

## XHS App Topic Integration Position

```
collector layer
 |
 +-- xhs_web adapter
 +-- xhs_app_topic adapter (new)
 |
Content Center
 |
Event Engine
 |
Brand Intelligence
```

Do not create an independent App data system.

## Authentication Recovery Direction

```
Session abnormal
 ↓
Auth Recovery Center
 ↓
User notification / QR verification when applicable
 ↓
Health check
 ↓
Controlled recovery
```

## Upgrade Rule

Before modifying production code:

- inspect current implementation
- identify smallest change point
- add tests
- verify no production regression

## Next Review Items

- collector implementation mapping
- database schema mapping
- topic campaign integration
- event relation integration
- frontend recovery UI mapping
