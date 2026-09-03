/** Decision-first Episode Workspace. */
export const EPISODE_WORKSPACE = {
  primary: ['overview', 'runtime', 'story'],
  secondary: ['evidence', 'assets', 'performance'],
  contextual: ['person', 'topic', 'research', 'platforms'],
  maxPrimaryActions: 3,
  interaction: {
    transcriptClickSeeksPlayer: true,
    timelineClickSeeksPlayer: true,
    evidenceOpensDrawer: true,
    secondaryUsesProgressiveDisclosure: true,
    preserveNavigationContext: true,
  },
};

export function buildEpisodeWorkspace(episode) {
  return {
    id: episode.id,
    title: episode.title ?? 'Untitled episode',
    status: episode.status ?? 'unknown',
    primary: {
      overview: episode.overview ?? null,
      runtime: episode.runtime ?? null,
      story: episode.story ?? null,
    },
    secondary: {
      evidenceCount: episode.evidence?.length ?? 0,
      assetCount: episode.assets?.length ?? 0,
      performance: episode.performance ?? null,
    },
    contextual: {
      personIds: episode.personIds ?? [],
      topicIds: episode.topicIds ?? [],
      researchIds: episode.researchIds ?? [],
      platformIds: episode.platformIds ?? [],
    },
  };
}
