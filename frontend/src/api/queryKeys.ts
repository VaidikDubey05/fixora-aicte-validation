export const queryKeys = {
  auth: {
    me: ['auth', 'me'] as const,
  },
  applications: {
    all: ['applications'] as const,
    list: (params?: Record<string, any>) => ['applications', 'list', params] as const,
    detail: (id: string) => ['applications', 'detail', id] as const,
    status: (id: string) => ['applications', 'status', id] as const,
    checklist: (id: string) => ['applications', 'checklist', id] as const,
    findings: (id: string) => ['applications', 'findings', id] as const,
  },
  findings: {
    all: ['findings'] as const,
    detail: (id: string) => ['findings', 'detail', id] as const,
  },
  documents: {
    detail: (id: string) => ['documents', 'detail', id] as const,
    fields: (id: string) => ['documents', 'fields', id] as const,
    ocr: (id: string) => ['documents', 'ocr', id] as const,
  },
  verification: {
    queue: ['verification', 'queue'] as const,
  },
  inspection: {
    queue: ['inspection', 'queue'] as const,
  },
  rulePacks: {
    all: ['rule-packs'] as const,
    detail: (id: string) => ['rule-packs', 'detail', id] as const,
  },
  alerts: {
    all: ['alerts'] as const,
  },
  analytics: {
    overview: ['analytics', 'overview'] as const,
  },
  audit: {
    all: ['audit'] as const,
    list: (params?: Record<string, any>) => ['audit', 'list', params] as const,
    verifyChain: ['audit', 'verify-chain'] as const,
  },
};
