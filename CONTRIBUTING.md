# Contributing to CodeLoop

## Getting Help

We use GitHub issues for tracking bugs and feature requests and have limited bandwidth to address them. If you need anything, I ask you to please follow our templates for opening issues or discussions.

- 🐛 [Bug Report](https://github.com/FernandoCelmer/codeloop/issues/new/choose)
- 📕 [Documentation](https://github.com/FernandoCelmer/codeloop/issues/new/choose)
- 🚀 [Feature Request](https://github.com/FernandoCelmer/codeloop/issues/new/choose)
- 💬 [General Question](https://github.com/FernandoCelmer/codeloop/issues/new/choose)

## Git Workflow

This project follows a **Git Flow** branching model. All development happens on the `develop` branch — never commit directly to `master`.

```mermaid
---
config:
  gitGraph:
    mainBranchName: master
---
gitGraph
    commit id: "v0.1.0"
    branch develop
    checkout develop
    commit id: "start dev"
    branch feature/42
    checkout feature/42
    commit id: "FEATURE-#42"
    commit id: "PEP8-#42"
    checkout develop
    merge feature/42 id: "PR #43"
    branch bug/38
    checkout bug/38
    commit id: "BUG-#38"
    checkout develop
    merge bug/38 id: "PR #39"
    branch docs/30
    checkout docs/30
    commit id: "DOCS-#30"
    checkout develop
    merge docs/30 id: "PR develop"
    checkout master
    merge develop id: "Release v0.2.0" tag: "v0.2.0"
```

### Branch Naming

All branches must be created **from `develop`** and follow the pattern:

| Type | Pattern | Example | When to use |
|------|---------|---------|-------------|
| Feature | `feature/<ISSUE-NUMBER>` | `feature/42` | New functionality |
| Bug Fix | `bug/<ISSUE-NUMBER>` | `bug/38` | Fixing a reported bug |
| Documentation | `docs/<ISSUE-NUMBER>` | `docs/30` | Documentation-only changes |
| Release | `release/<VERSION>` | `release/1.0.0` | Preparing a new release |

### Creating a Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/123
```

## Commit Style

Every commit must follow the format:

```
<emoji> <TYPE>-#<ISSUE-NUMBER>: <Description>
```

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

### Examples

```
⚙️ FEATURE-#42: Add JSON-configured provider support
🪲 BUG-#38: Fix system prompt dropped for message_shape=anthropic
📘 DOCS-#30: Document the generic provider's request/response config
📝 PEP8-#42: Apply ruff format to CLI commands
❤️ TEST-#42: Add tests for GenericProvider streaming
📌 ISSUE-#42: Resolve merge conflict with develop
📦 PyPI: Update version to 0.2.0.dev1
```

## Pull Requests

### Target Branch

- Feature/bug/docs branches → open PR against **`develop`**
- Release branches → open PR against **`master`**

### PR Guidelines

When opening a PR, fill out the provided template:

1. **Description** — Summarize the changes and link the related issue
2. **Type of change** — Check the appropriate box (bug fix, feature, breaking change, docs)
3. **Checklist** — Confirm code quality, tests, and documentation

### Before Opening a PR

- [ ] Code follows the project style guidelines
- [ ] Self-review completed
- [ ] Tests added/updated and passing locally
- [ ] No new warnings introduced
- [ ] Documentation updated (if applicable)

## Code Quality

### Linting & Formatting

This project uses **ruff** for formatting, linting, and import sorting, and **mypy** for type checking — configured in `.code_quality/`.

```bash
# Format code
ruff format .

# Check linting
ruff check .

# Type check
mypy codeloop/
```

### Tests

Run the test suite with:

```bash
pytest
```

## Project Structure

```
codeloop/
├── codeloop/           # Main library
│   ├── abc/          # Abstract base classes (Provider, Tool)
│   ├── cli/          # CLI commands and the Textual TUI
│   ├── core/         # Agent loop, session, config, tools
│   └── providers/    # LLM backends (Anthropic, OpenAI, Ollama, generic)
├── tests/            # Test suite
├── docs/             # MkDocs documentation source
└── templates/        # Example JSON provider configs
```

## Development Setup

```bash
# Clone the repository
git clone https://github.com/FernandoCelmer/codeloop.git
cd codeloop

# Install dependencies with Poetry
poetry install --all-extras

# Activate the virtual environment
poetry shell
```

## Summary

1. **Branch from `develop`** using the naming convention
2. **Commit** with emoji + type + issue number
3. **Open a PR** against `develop` (or `master` for releases)
4. **Pass all checks** — linting, tests, and self-review
5. Wait for code review and approval before merging
