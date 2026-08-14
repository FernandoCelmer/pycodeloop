export interface ProviderDef {
  id: string;
  label: string;
  description: string;
  file: string;
  models: string[];
  defaultModel: string;
  local: boolean;
}

export const PROVIDER_CATALOG: ProviderDef[] = [
  {
    id: "anthropic",
    label: "Anthropic",
    description: "Claude models — needs ANTHROPIC_API_KEY",
    file: "anthropic.json",
    models: ["claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5", "claude-opus-4-8", "claude-fable-5"],
    defaultModel: "claude-sonnet-5",
    local: false,
  },
  {
    id: "openai",
    label: "OpenAI",
    description: "GPT models — needs OPENAI_API_KEY",
    file: "openai.json",
    models: ["gpt-5.6", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.3-codex"],
    defaultModel: "gpt-5.6",
    local: false,
  },
  {
    id: "gemini",
    label: "Gemini",
    description: "Google Gemini models — needs GEMINI_API_KEY",
    file: "gemini.json",
    models: ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite", "gemini-2.0-flash"],
    defaultModel: "gemini-2.5-flash",
    local: false,
  },
  {
    id: "grok",
    label: "Grok (xAI)",
    description: "xAI Grok models — needs XAI_API_KEY",
    file: "grok.json",
    models: ["grok-4.5", "grok-4.3", "grok-build-0.1"],
    defaultModel: "grok-4.5",
    local: false,
  },
  {
    id: "groq",
    label: "Groq",
    description: "Fast open-weight inference — needs GROQ_API_KEY",
    file: "groq.json",
    models: ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile"],
    defaultModel: "openai/gpt-oss-120b",
    local: false,
  },
  {
    id: "ollama",
    label: "Ollama",
    description: "Local models via Ollama — no API key",
    file: "ollama.json",
    models: ["llama3.1", "qwen2.5-coder", "mistral", "deepseek-r1", "gpt-oss:20b"],
    defaultModel: "llama3.1",
    local: true,
  },
  {
    id: "lmstudio",
    label: "LM Studio",
    description: "Local models via LM Studio — no API key",
    file: "lmstudio.json",
    models: ["local-model"],
    defaultModel: "local-model",
    local: true,
  },
];

export function findProviderDef(id: string): ProviderDef | undefined {
  return PROVIDER_CATALOG.find((def) => def.id === id);
}
