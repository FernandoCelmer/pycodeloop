export interface SessionSummary {
  key: string;
  updated_at?: number;
  message_count?: number;
  cwd?: string;
}

export interface SessionPickItem {
  label: string;
  description: string;
  detail: string | undefined;
  key: string;
}

/** Newest-first, without mutating the input array. */
export function sortByRecency(sessions: SessionSummary[]): SessionSummary[] {
  return [...sessions].sort((a, b) => (b.updated_at ?? 0) - (a.updated_at ?? 0));
}

/** Builds QuickPick items for the session switcher, marking the active one.
 * Pure — extracted from ChatViewProvider.selectSession() for unit testing. */
export function toSessionPickItems(
  sessions: SessionSummary[],
  activeKey: string
): SessionPickItem[] {
  return sortByRecency(sessions).map((session) => ({
    label: (session.key === activeKey ? "$(check) " : "") + session.key,
    description:
      (session.message_count ?? 0) + " messages" + (session.cwd ? " · " + session.cwd : ""),
    detail: session.updated_at ? new Date(session.updated_at * 1000).toLocaleString() : undefined,
    key: session.key,
  }));
}
