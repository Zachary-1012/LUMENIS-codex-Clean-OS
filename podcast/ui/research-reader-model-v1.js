/** Focused research reading surface; detail is deliberately secondary. */
export const RESEARCH_READER = {
  primarySections: ['conclusion', 'key-findings'],
  secondarySections: ['evidence', 'patterns', 'hypotheses', 'validation', 'transfer', 'dont-copy'],
  navigation: ['overview', 'research', 'evidence', 'validation', 'learning'],
  interaction: {
    evidenceOpensDrawer: true,
    hypothesisShowsValidationState: true,
    unverifiedClaimsStayVisibleButMarked: true,
    returnPreservesScrollPosition: true,
  },
};

export function readerState(report) {
  return {
    title: report.title ?? 'Research',
    status: report.status ?? 'unverified',
    conclusion: report.conclusion ?? null,
    findings: report.findings ?? [],
    evidenceCount: report.evidence?.length ?? 0,
    validationState: report.validationState ?? 'pending',
    transferability: report.transferability ?? 'pending',
  };
}
