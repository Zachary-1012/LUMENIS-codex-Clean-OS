/**
 * ZBC Podcast Intelligence Table Model v1
 *
 * Shared presentation metadata for Case / Episode / Topic / Person /
 * Platform / Runtime / Research views. Business data remains separate.
 */
export const PODCAST_TABLES = {
  cases: {
    title: 'Case Library',
    columns: ['case','type','pattern','scale','breakout','research_status','transferability','confidence'],
    primary: 'case',
    density: 'high',
    drilldown: 'research-reader',
  },
  episodes: {
    title: 'Episode Benchmark',
    columns: ['episode','published_at','runtime','hook','story','emotion','insight','yield','breakout'],
    primary: 'episode',
    density: 'high',
    drilldown: 'episode-workspace',
  },
  topics: {
    title: 'Topic Intelligence',
    columns: ['topic','demand','timeliness','novelty','guest_fit','evidence','yield','risk','score','stage'],
    primary: 'topic',
    density: 'high',
    drilldown: 'topic-dossier',
  },
  people: {
    title: 'Person Dossier',
    columns: ['person','identity','signals','questions','events','risk','evidence','guest_fit'],
    primary: 'person',
    density: 'high',
    drilldown: 'person-dossier',
  },
  platforms: {
    title: 'Platform Matrix',
    columns: ['episode','xiaoyuzhou','youtube','bilibili','douyin','xiaohongshu','spotify','apple'],
    primary: 'episode',
    density: 'compact',
    drilldown: 'platform-runtime',
  },
  runtime: {
    title: 'Runtime / Story Timeline',
    columns: ['time','segment','speaker','type','emotion','story','insight','evidence'],
    primary: 'time',
    density: 'high',
    drilldown: 'timeline-segment',
  },
  research: {
    title: 'Research Reader Index',
    columns: ['research','status','evidence','hypothesis','validation','transfer'],
    primary: 'research',
    density: 'comfortable',
    drilldown: 'research-reader',
  },
};

export const TABLE_INTERACTION = {
  row: ['hover', 'keyboard-focus', 'open-drilldown'],
  sort: 'server-or-local-stable-sort',
  filter: 'facet-and-free-text',
  empty: 'explain-and-next-action',
  loading: 'skeleton-preserve-layout',
  error: 'inline-retry',
  evidence: 'drawer',
  secondary: 'progressive-disclosure',
};
