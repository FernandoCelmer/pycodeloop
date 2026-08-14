export function buildInstallCommand(platform: NodeJS.Platform): string {
  const pythonCmd = platform === "win32" ? "python" : "python3";
  return `${pythonCmd} -m pip install --user pycodeloop`;
}
