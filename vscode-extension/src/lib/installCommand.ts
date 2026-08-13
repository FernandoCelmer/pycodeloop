/** The pycodeloop CLI always installs globally (--user), regardless of
 * which project/venv is open — matches pycodeloop.command defaulting to a
 * bare "pycodeloop" resolved off PATH rather than a venv-pinned path. */
export function buildInstallCommand(platform: NodeJS.Platform): string {
  const pythonCmd = platform === "win32" ? "python" : "python3";
  return `${pythonCmd} -m pip install --user pycodeloop`;
}
