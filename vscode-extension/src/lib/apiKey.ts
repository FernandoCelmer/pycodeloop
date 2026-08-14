export const API_KEY_SECRET = "pycodeloop.apiKey";
export const API_KEY_ENV = "PYCODELOOP_API_KEY";

export function spawnEnvForApiKey(
  apiKey: string | undefined
): Record<string, string> | undefined {
  const value = apiKey?.trim();
  if (!value) {
    return undefined;
  }
  return { [API_KEY_ENV]: value };
}
