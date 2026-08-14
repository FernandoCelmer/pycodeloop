import assert from "node:assert/strict";
import { test } from "node:test";
import { buildInstallCommand } from "../src/services/terminal.service";

test("uses python3 on non-Windows platforms", () => {
  assert.equal(buildInstallCommand("darwin"), "python3 -m pip install --user pycodeloop");
  assert.equal(buildInstallCommand("linux"), "python3 -m pip install --user pycodeloop");
});

test("uses python (no '3') on win32", () => {
  assert.equal(buildInstallCommand("win32"), "python -m pip install --user pycodeloop");
});

test("never installs vendor extras — GenericProvider has no SDK dependency", () => {
  assert.ok(!buildInstallCommand("darwin").includes("["));
});
