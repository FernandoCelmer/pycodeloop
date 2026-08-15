"""Graduated autonomy levels replacing the binary `dangerous` flag.

Instead of a tool being either "needs confirmation" or "runs freely", each
tool declares the *kind* of effect it has (`read`, `execute_low_risk`,
`execute_high_risk`) and the agent consults the configured autonomy level to
decide, per call, whether to allow it, ask for approval, or deny it. This lets
a run permit low-risk writes autonomously while still gating high-risk ones.
"""

from __future__ import annotations

from enum import Enum


class AutonomyLevel(str, Enum):
    MANUAL = "manual"
    SAFE_EXECUTE = "safe_execute"
    FULL_PROJECT_LOOP = "full_project_loop"

    @classmethod
    def from_str(cls, value: str | AutonomyLevel) -> AutonomyLevel:
        if isinstance(value, AutonomyLevel):
            return value
        try:
            return cls(value)
        except ValueError as err:
            raise ValueError(
                f"unknown autonomy level {value!r}; "
                f"expected one of {[level.value for level in cls]}"
            ) from err


class GateDecision(str, Enum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


_POLICY: dict[AutonomyLevel, dict[str, GateDecision]] = {
    AutonomyLevel.MANUAL: {
        "read": GateDecision.ALLOW,
        "execute_low_risk": GateDecision.REQUIRE_APPROVAL,
        "execute_high_risk": GateDecision.DENY,
    },
    AutonomyLevel.SAFE_EXECUTE: {
        "read": GateDecision.ALLOW,
        "execute_low_risk": GateDecision.ALLOW,
        "execute_high_risk": GateDecision.REQUIRE_APPROVAL,
    },
    AutonomyLevel.FULL_PROJECT_LOOP: {
        "read": GateDecision.ALLOW,
        "execute_low_risk": GateDecision.ALLOW,
        "execute_high_risk": GateDecision.ALLOW,
    },
}


def gate(level: AutonomyLevel | str, operation: str) -> GateDecision:
    """Decide how a tool with `operation` may run at `level`."""
    resolved = AutonomyLevel.from_str(level)
    try:
        return _POLICY[resolved][operation]
    except KeyError as err:
        raise ValueError(
            f"unknown tool operation {operation!r}; "
            "expected 'read', 'execute_low_risk', or 'execute_high_risk'"
        ) from err
