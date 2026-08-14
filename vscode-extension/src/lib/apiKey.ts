export const API_KEY_SECRET = "pycodeloop.apiKey";
export const API_KEY_ENV = "PYCODELOOP_API_KEY";

export interface ProviderAuth {
  apiKeyEnv?: string;
  authHeader?: string;
}

export function providerAuthFromJson(jsonText: string): ProviderAuth {
  try {
    const data = JSON.parse(jsonText);
    return {
      apiKeyEnv:
        typeof data.api_key_env === "string" && data.api_key_env
          ? data.api_key_env
          : undefined,
      authHeader:
        typeof data.auth_header === "string" && data.auth_header
          ? data.auth_header
          : undefined,
    };
  } catch {
    return {};
  }
}

export function apiKeyEnvFromProviderJson(jsonText: string): string | undefined {
  return providerAuthFromJson(jsonText).apiKeyEnv;
}

export function spawnEnvForApiKey(
  apiKey: string | undefined,
  extraEnvNames: string[] = []
): Record<string, string> | undefined {
  const value = apiKey?.trim();
  if (!value) {
    return undefined;
  }
  const env: Record<string, string> = { [API_KEY_ENV]: value };
  for (const name of extraEnvNames) {
    if (name) {
      env[name] = value;
    }
  }
  return env;
}
