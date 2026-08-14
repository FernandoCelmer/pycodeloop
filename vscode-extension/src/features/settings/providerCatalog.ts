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
    description: "Claude models",
    file: "anthropic.json",
    models: ["claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5", "claude-opus-4-8", "claude-fable-5"],
    defaultModel: "claude-sonnet-5",
    local: false,
  },
  {
    id: "openai",
    label: "OpenAI",
    description: "GPT models",
    file: "openai.json",
    models: ["gpt-5.6", "gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.3-codex"],
    defaultModel: "gpt-5.6",
    local: false,
  },
  {
    id: "gemini",
    label: "Gemini",
    description: "Google Gemini models",
    file: "gemini.json",
    models: ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-2.5-pro"],
    defaultModel: "gemini-3.6-flash",
    local: false,
  },
  {
    id: "grok",
    label: "Grok (xAI)",
    description: "xAI Grok models",
    file: "grok.json",
    models: ["grok-4.5", "grok-4.3", "grok-build-0.1"],
    defaultModel: "grok-4.5",
    local: false,
  },
  {
    id: "groq",
    label: "Groq",
    description: "Fast open-weight inference",
    file: "groq.json",
    models: ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "llama-3.3-70b-versatile"],
    defaultModel: "openai/gpt-oss-120b",
    local: false,
  },
  {
    id: "aws",
    label: "AWS (Bedrock)",
    description: "Amazon Bedrock, OpenAI-compatible",
    file: "aws.json",
    models: ["openai.gpt-oss-120b", "openai.gpt-oss-20b", "us.anthropic.claude-sonnet-4-6"],
    defaultModel: "openai.gpt-oss-120b",
    local: false,
  },
  {
    id: "kimi",
    label: "Kimi (Moonshot AI)",
    description: "Kimi models",
    file: "kimi.json",
    models: ["kimi-k3", "kimi-k2.7-code", "kimi-k2.6"],
    defaultModel: "kimi-k3",
    local: false,
  },
  {
    id: "deepseek",
    label: "DeepSeek",
    description: "DeepSeek models",
    file: "deepseek.json",
    models: ["deepseek-v4-pro", "deepseek-v4-flash"],
    defaultModel: "deepseek-v4-pro",
    local: false,
  },
  {
    id: "llama",
    label: "Llama (Together AI)",
    description: "Meta Llama, hosted",
    file: "llama.json",
    models: ["meta-llama/Llama-3.3-70B-Instruct-Turbo"],
    defaultModel: "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    local: false,
  },
  {
    id: "qwen",
    label: "Qwen (Alibaba)",
    description: "Qwen models via DashScope",
    file: "qwen.json",
    models: ["qwen-max", "qwen-plus", "qwen-turbo"],
    defaultModel: "qwen-max",
    local: false,
  },
  {
    id: "nvidia",
    label: "NVIDIA NIM",
    description: "Hosted open models on NVIDIA",
    file: "nvidia.json",
    models: ["meta/llama-3.3-70b-instruct", "qwen/qwen3-next-80b-a3b-instruct", "deepseek-ai/deepseek-v4-pro"],
    defaultModel: "meta/llama-3.3-70b-instruct",
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
