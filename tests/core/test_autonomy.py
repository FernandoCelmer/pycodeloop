"""Tests for the graduated autonomy gate (pycodeloop.core.autonomy)."""

import unittest

from pycodeloop.core.autonomy import (
    AutonomyLevel,
    GateDecision,
    gate,
)


class TestAutonomyLevel(unittest.TestCase):
    def test_from_str_accepts_enum_and_string(self):
        self.assertIs(AutonomyLevel.from_str("manual"), AutonomyLevel.MANUAL)
        self.assertIs(
            AutonomyLevel.from_str(AutonomyLevel.SAFE_EXECUTE),
            AutonomyLevel.SAFE_EXECUTE,
        )

    def test_from_str_rejects_unknown(self):
        with self.assertRaises(ValueError):
            AutonomyLevel.from_str("do_everything")


class TestGate(unittest.TestCase):
    def test_manual_allows_reads_and_low_risk_with_approval_denies_high(self):
        self.assertEqual(gate("manual", "read"), GateDecision.ALLOW)
        self.assertEqual(
            gate("manual", "execute_low_risk"), GateDecision.REQUIRE_APPROVAL
        )
        self.assertEqual(
            gate("manual", "execute_high_risk"), GateDecision.DENY
        )

    def test_safe_execute_allows_low_risk_approves_high(self):
        self.assertEqual(gate("safe_execute", "read"), GateDecision.ALLOW)
        self.assertEqual(
            gate("safe_execute", "execute_low_risk"), GateDecision.ALLOW
        )
        self.assertEqual(
            gate("safe_execute", "execute_high_risk"),
            GateDecision.REQUIRE_APPROVAL,
        )

    def test_full_project_loop_allows_everything(self):
        for operation in ("read", "execute_low_risk", "execute_high_risk"):
            self.assertEqual(
                gate("full_project_loop", operation), GateDecision.ALLOW
            )

    def test_unknown_operation_raises(self):
        with self.assertRaises(ValueError):
            gate("manual", "nuke_the_site_from_orbit")


if __name__ == "__main__":
    unittest.main()
