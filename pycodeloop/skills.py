"""Skills module"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pycodeloop.abc.tool import Tool, ToolResult
from pycodeloop.store.json_store import default_store

_MAX_DESCRIPTION = 100
_CACHE_SECTION = "skills"


@dataclass
class Skill:
    name: str
    description: str
    source: str
    path: Path
    content: str


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    meta: dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip('"').strip("'")

    return meta, parts[2].strip()


def _load_skill_md(path: Path, source: str) -> Skill | None:
    try:
        text = path.read_text()
    except OSError:
        return None

    meta, body = _parse_frontmatter(text)
    name = meta.get("name") or path.stem
    description = meta.get("description") or (
        body.splitlines()[0] if body else ""
    )
    description = " ".join(description.split())
    if len(description) > _MAX_DESCRIPTION:
        description = description[:_MAX_DESCRIPTION] + "…"

    return Skill(
        name=name,
        description=description,
        source=source,
        path=path,
        content=body or text,
    )


def _load_plain_doc(path: Path, source: str, name: str) -> Skill | None:
    try:
        text = path.read_text()
    except OSError:
        return None
    if not text.strip():
        return None

    first_line = next(
        (
            line.strip("# ").strip()
            for line in text.splitlines()
            if line.strip()
        ),
        name,
    )
    description = (
        first_line
        if len(first_line) <= _MAX_DESCRIPTION
        else first_line[:_MAX_DESCRIPTION] + "…"
    )

    return Skill(
        name=name,
        description=description,
        source=source,
        path=path,
        content=text,
    )


def _jobs(
    cwd: Path, home: Path, sources: set[str] | None
) -> list[tuple[Path, str, str, str | None]]:
    """Every (path, source, loader, fallback_name) discover_skills would
    touch — cheap to `stat()` for cache invalidation without reading."""

    def wanted(source: str) -> bool:
        return sources is None or source in sources

    jobs: list[tuple[Path, str, str, str | None]] = []

    if wanted("claude-skill"):
        for root in (home / ".claude" / "skills", cwd / ".claude" / "skills"):
            jobs.extend(
                (p, "claude-skill", "skill_md", None)
                for p in sorted(root.glob("*/SKILL.md"))
            )

    if wanted("claude-memory"):
        jobs.extend(
            (p, "claude-memory", "plain_doc", "CLAUDE.md")
            for p in (home / ".claude" / "CLAUDE.md", cwd / "CLAUDE.md")
        )

    if wanted("cursor-rule"):
        jobs.extend(
            (p, "cursor-rule", "skill_md", None)
            for p in sorted((cwd / ".cursor" / "rules").glob("*.mdc"))
        )
        jobs.append(
            (cwd / ".cursorrules", "cursor-rule", "plain_doc", ".cursorrules")
        )

    if wanted("agents-md"):
        jobs.append((cwd / "AGENTS.md", "agents-md", "plain_doc", "AGENTS.md"))

    return jobs


def _load_jobs(jobs: list[tuple[Path, str, str, str | None]]) -> list[Skill]:
    skills: list[Skill] = []
    for path, source, loader, fallback_name in jobs:
        skill = (
            _load_skill_md(path, source)
            if loader == "skill_md"
            else _load_plain_doc(path, source, fallback_name)
        )
        if skill:
            skills.append(skill)
    return skills


def _fingerprint(
    jobs: list[tuple[Path, str, str, str | None]],
) -> dict[str, float]:
    return {
        str(path): path.stat().st_mtime for path, *_ in jobs if path.exists()
    }


def _cache_key(cwd: Path, home: Path, sources: set[str] | None) -> str:
    return f"{cwd}|{home}|{','.join(sorted(sources)) if sources else '*'}"


def _skill_to_dict(skill: Skill) -> dict:
    return {
        "name": skill.name,
        "description": skill.description,
        "source": skill.source,
        "path": str(skill.path),
        "content": skill.content,
    }


def _skill_from_dict(data: dict) -> Skill:
    return Skill(
        name=data["name"],
        description=data["description"],
        source=data["source"],
        path=Path(data["path"]),
        content=data["content"],
    )


def discover_skills(
    cwd: Path | None = None,
    home: Path | None = None,
    sources: set[str] | None = None,
    use_cache: bool = True,
) -> list[Skill]:
    """Scan well-known locations Claude Code, Cursor, and the AGENTS.md
    convention (Codex and others) use for skills/instructions.

    Results are cached in `~/.pycodeloop/config.json` under "skills_cache",
    keyed by cwd and invalidated automatically when any matched file's
    mtime changes — unchanged skills are served from cache, unread.

    Args:
        cwd: Project directory to scan. Defaults to the current directory.
        home: User home directory to scan. Defaults to `Path.home()`.
        sources: Limit to these sources ("claude-skill", "claude-memory",
            "cursor-rule", "agents-md"). Defaults to all of them.
        use_cache: Set False to force a full rescan and refresh the cache.
    """
    cwd = cwd or Path.cwd()
    home = home or Path.home()
    jobs = _jobs(cwd, home, sources)
    fingerprint = _fingerprint(jobs)
    key = _cache_key(cwd, home, sources)

    cache = default_store.get_section(_CACHE_SECTION)
    cached_entry = cache.get(key)

    if (
        use_cache
        and cached_entry
        and cached_entry.get("fingerprint") == fingerprint
    ):
        return [_skill_from_dict(item) for item in cached_entry["skills"]]

    skills = _load_jobs(jobs)

    if use_cache:
        cache[key] = {
            "fingerprint": fingerprint,
            "skills": [_skill_to_dict(s) for s in skills],
        }
        default_store.set_section(_CACHE_SECTION, cache)

    return skills


def render_skills_index(skills: list[Skill]) -> str:
    if not skills:
        return ""

    lines = [
        "You have access to the following skills/instructions discovered on "
        "this machine (from Claude Code, Cursor, and the AGENTS.md "
        "convention). Each is a short index entry — call `read_skill` with "
        "its name to load the full content when it's relevant to the task.",
        "",
    ]
    lines.extend(
        f"- **{skill.name}** ({skill.source}): {skill.description}"
        for skill in skills
    )
    return "\n".join(lines)


class ReadSkillTool(Tool):
    name = "read_skill"
    description = (
        "Read the full content of a discovered skill/instruction file by name."
    )
    operation = "read"
    parameters = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }

    def __init__(self, skills: list[Skill]) -> None:
        self._skills = {skill.name: skill for skill in skills}

    def run(self, name: str) -> ToolResult:
        skill = self._skills.get(name)

        if skill is None:
            available = ", ".join(sorted(self._skills)) or "(none)"
            return ToolResult(
                output=f"Unknown skill '{name}'. Available: {available}",
                is_error=True,
            )

        return ToolResult(output=skill.content)
