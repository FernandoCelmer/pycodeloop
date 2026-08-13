# Development Guide

## Getting Help

We use GitHub issues for tracking bugs and feature requests.

- 🐛 [Bug Report](https://github.com/dotflow-io/pycodeloop/issues/new/choose)
- 📕 [Documentation](https://github.com/dotflow-io/pycodeloop/issues/new/choose)
- 🚀 [Feature Request](https://github.com/dotflow-io/pycodeloop/issues/new/choose)
- 💬 [General Question](https://github.com/dotflow-io/pycodeloop/issues/new/choose)

## Git Workflow

This project follows a **Git Flow** branching model. Feature work happens on branches created from `develop` — never commit directly to `master`.

### Branch Naming

| Type | Pattern | Example | When to use |
|------|---------|---------|-------------|
| Feature | `feature/<ISSUE-NUMBER>` | `feature/12` | New functionality |
| Bug Fix | `bug/<ISSUE-NUMBER>` | `bug/7` | Fixing a reported bug |
| Documentation | `docs/<ISSUE-NUMBER>` | `docs/4` | Documentation-only changes |
| Release | `release/<VERSION>` | `release/0.2.0` | Preparing a new release |

### Creating a Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/12
```

## Commit Style

Every commit follows the format:

```
<emoji> <TYPE>[-#<ISSUE-NUMBER>]: <Description>
```

The issue number is omitted when a commit isn't tied to one.

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
⚙️ FEATURE-#12: Add MCP client bridging remote tools into Tool ABC
🪲 BUG-#7: Fix edit_file crash on empty old_string
📘 DOCS: Document permission prompts, streaming and token usage
📝 PEP8: Apply ruff format to providers
❤️ TEST: Add confirm gate tests for dangerous tools
📦 PyPI: Update version to 0.2.0
```

Commit messages are short by default — a subject line only. A body is added only for a one-sentence *why* that isn't obvious from the diff.

Each commit stays scoped to one file or one concern — implementation, tests, and docs land as separate commits rather than one bundled change.

## Pull Requests

- Feature/bug/docs branches → open PR against **`develop`**
- Release branches → open PR against **`master`**

### Before Opening a PR

- [ ] Code follows the project style guidelines
- [ ] Tests added/updated and passing locally (`pytest`)
- [ ] `ruff check` and `ruff format` clean
- [ ] Documentation updated (if applicable)

## Code Quality

This project uses **ruff** (lint + format), **flake8**, **mypy**, **isort**, and **black** configs, all under [`.code_quality/`](https://github.com/dotflow-io/pycodeloop/tree/master/.code_quality) and wired into `.pre-commit-config.yaml`.

```bash
# Lint + format
ruff check --config .code_quality/ruff.toml --fix .
ruff format --config .code_quality/ruff.toml .

# Tests
pytest
```

## Project Structure

```
pycodeloop/
├── pycodeloop/
│   ├── abc/          # Abstract base classes (Provider, Tool)
│   ├── cli/           # Typer CLI (run, chat)
│   ├── core/          # Agent loop, Config, Session, tools, MCP client
│   ├── providers/     # GenericProvider (any HTTP chat-completions API)
│   └── settings.py    # Env-based defaults
├── tests/              # Test suite
├── docs/               # MkDocs documentation source
└── mkdocs.yml
```

## Development Setup

```bash
git clone https://github.com/dotflow-io/pycodeloop.git
cd pycodeloop

poetry install --extras all --with dev,code-quality,docs
```

## Building the docs

```bash
poetry run mkdocs serve   # local preview at http://127.0.0.1:8000
poetry run mkdocs build   # static site into site/
```

## Summary

1. **Branch from `develop`** using the naming convention
2. **Commit** with emoji + type (+ issue number when there is one)
3. **Open a PR** against `develop` (or `master` for releases)
4. **Pass all checks** — linting, tests, and self-review
