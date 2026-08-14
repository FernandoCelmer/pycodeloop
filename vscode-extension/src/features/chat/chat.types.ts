export const FORWARDED_NOTIFICATIONS = [
  "ready",
  "chat/textDelta",
  "chat/toolCall",
  "chat/toolResult",
  "chat/usage",
  "chat/context",
  "chat/retry",
  "chat/compactStart",
  "chat/compactEnd",
  "chat/confirmRequest",
  "chat/autoApproved",
];

export type PostMessage = (message: { type: string } & Record<string, unknown>) => void;
export type ResolveSetting = (value: string) => string;
