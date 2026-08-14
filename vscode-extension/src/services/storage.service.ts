export interface SessionSummary {
  key: string;
  updated_at?: number;
  message_count?: number;
  cwd?: string;
}

export function sortByRecency(sessions: SessionSummary[]): SessionSummary[] {
  return [...sessions].sort((a, b) => (b.updated_at ?? 0) - (a.updated_at ?? 0));
}
