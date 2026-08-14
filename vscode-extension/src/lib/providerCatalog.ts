export interface ProviderDef {
  id: string;
  label: string;
  description: string;
  /** Filename under the extension's bundled providers/ dir. */
  file: string;
  models: string[];
  defaultModel: string;
  local: boolean;
}

/** Ready-to-use provider configs bundled with the extension — pick one
 * and go, no hand-written JSON needed. Mirrors pycodeloop/providers/
 * templates/ but shipped inside the extension so it works regardless of
 * how the pycodeloop CLI was installed. */
export const PROVIDER_CATALOG: ProviderDef[] = [
  {
    id: "anthropic",
    label: "Anthropic",
    description: "Claude models — needs ANTHROPIC_API_KEY",
    file: "anthropic.json",
    models: ["claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5"],
    defaultModel: "claude-sonnet-5",
    local: false,
  },
  {
    id: "openai",
    label: "OpenAI",
    description: "GPT models — needs OPENAI_API_KEY",
    file: "openai.json",
    models: ["gpt-5", "gpt-5-mini", "gpt-5-nano"],
    defaultModel: "gpt-5",
    local: false,
  },
  {
    id: "gemini",
    label: "Gemini",
    description: "Google Gemini models — needs GEMINI_API_KEY",
    file: "gemini.json",
    // Deliberately pinned to 2.5, not the "-latest" aliases: those now
    // resolve to Gemini 3.x, whose "thinking" models attach a
    // thought_signature to function calls that the OpenAI-compatible
    // endpoint doesn't round-trip — the 2nd tool call in a turn 400s.
    // https://github.com/openai/codex/issues/7519
    models: ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite"],
    defaultModel: "gemini-2.5-flash",
    local: false,
  },
  {
    id: "grok",
    label: "Grok (xAI)",
    description: "xAI Grok models — needs XAI_API_KEY",
    file: "grok.json",
    models: ["grok-4", "grok-4-fast", "grok-code-fast-1"],
    defaultModel: "grok-4",
    local: false,
  },
  {
    id: "groq",
    label: "Groq",
    description: "Fast open-weight inference — needs GROQ_API_KEY",
    file: "groq.json",
    // llama-3.3-70b-versatile is deprecated on Groq; gpt-oss is the
    // recommended general-purpose replacement.
    models: ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "moonshotai/kimi-k2-instruct"],
    defaultModel: "openai/gpt-oss-120b",
    local: false,
  },
  {
    id: "ollama",
    label: "Ollama",
    description: "Local models via Ollama — no API key",
    file: "ollama.json",
    models: ["llama3.1", "qwen2.5-coder", "mistral"],
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
