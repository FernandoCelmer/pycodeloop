# Welcome to CodeLoop

<div align="center">
  <a aria-label="Repository" href="https://github.com/FernandoCelmer/codeloop">Repository</a>
  &nbsp;•&nbsp;
  <a aria-label="CodeLoop Documentation" href="https://fernandocelmer.github.io/codeloop/">Documentation</a>
</div>

![PyPI](https://img.shields.io/pypi/v/codeloop?style=flat-square)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/codeloop?style=flat-square)
![GitHub last commit](https://img.shields.io/github/last-commit/FernandoCelmer/codeloop?style=flat-square)

CodeLoop is a lightweight Python library for building agentic coding assistants — in the shape of Claude Code, Codex, or Gemini CLI. Give it a provider and a prompt, it drives a tool-use loop (read, write, edit, grep, bash, web fetch, MCP) until the task is done.

Every piece is injected, not hardcoded: swap the LLM backend, the tool set, or the system prompt without touching the agent loop. Bare `codeloop` starts a full-screen Textual TUI; `run` covers one-shot and scripted use. Skills already on disk (Claude Code, Cursor, `AGENTS.md`) are discovered automatically.

Start with the basics [here](nav/how-to/install.md).

## Getting Help

We use GitHub issues for tracking bugs and feature requests.

- 🐛 [Bug Report](https://github.com/FernandoCelmer/codeloop/issues/new/choose)
- 🚀 [Feature Request](https://github.com/FernandoCelmer/codeloop/issues/new/choose)
- ⚠️ [Security Issue](https://github.com/FernandoCelmer/codeloop/issues/new/choose)

## Commit Style

| Icon | Type      | Description                                |
|------|-----------|--------------------------------------------|
| ⚙️   | FEATURE   | New feature                                |
| 📝   | PEP8      | Formatting fixes following PEP8            |
| 📌   | ISSUE     | Reference to issue                         |
| 🪲   | BUG       | Bug fix                                    |
| 📘   | DOCS      | Documentation changes                      |
| 📦   | PyPI      | PyPI releases                              |
| ❤️️   | TEST      | Automated tests                            |
| ⬆️   | CI/CD     | Changes in continuous integration/delivery |
| ⚠️   | SECURITY  | Security improvements                      |

## License

![GitHub License](https://img.shields.io/github/license/FernandoCelmer/codeloop)

This project is licensed under the terms of the MIT License.
