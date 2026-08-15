"""Rule-based classification of tool failures into typed feedback signals.

The agent injects a `[<error_kind>]` prefix ahead of an error's text so the
model can replan differently for a `syntax_error` vs a `test_failure` vs a
`permission_denied`, instead of re-parsing the raw error string each time.
Classification is pure pattern matching over the captured output and the
process exit code — no LLM call.
"""

from __future__ import annotations

UNKNOWN = "unknown"


def classify_error(output: str, exit_code: int = 0) -> str:
    """Return a stable `error_kind` for a failed tool's captured output.

    Order matters: timeout and permission failures short-circuit before the
    generic traceback/regex fallbacks.
    """
    text = output or ""
    lowered = text.lower()

    if "timed out" in lowered or "timeouterror" in lowered:
        return "timeout"
    if (
        "permissionerror" in lowered
        or "eacces" in lowered
        or "permission denied" in lowered
    ):
        return "permission_denied"
    if "syntaxerror" in lowered:
        return "syntax_error"
    if (
        "failed" in lowered
        or "assertionerror" in lowered
        or ("pytest" in lowered and exit_code != 0)
        or ("jest" in lowered and exit_code != 0)
    ):
        return "test_failure"
    if "command not found" in lowered or (
        "no such file" in lowered and "traceback" not in lowered
    ):
        return "command_not_found"
    if "traceback (most recent call last)" in lowered:
        return "runtime_exception"
    return UNKNOWN
