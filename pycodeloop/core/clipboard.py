"""Read an image straight off the system clipboard — a terminal's own
paste (Cmd+V) only ever delivers text over stdin, so a pasted
screenshot never reaches a TUI that way. This reads the OS pasteboard
directly instead, bypassing the terminal entirely."""

from __future__ import annotations

import base64
import subprocess
import sys
import tempfile
from pathlib import Path

_APPLESCRIPT = """
try
    set imgData to (the clipboard as «class PNGf»)
on error
    return "NO_IMAGE"
end try
set fileRef to open for access POSIX file "{path}" with write permission
write imgData to fileRef
close access fileRef
return "OK"
"""


def read_clipboard_image_base64() -> str | None:
    """Return the clipboard's image as base64-encoded PNG, or `None` if
    the clipboard holds no image (or this isn't macOS)."""
    if sys.platform != "darwin":
        return None

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = Path(f.name)

    try:
        result = subprocess.run(
            ["osascript", "-e", _APPLESCRIPT.format(path=path)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0 or "NO_IMAGE" in result.stdout:
            return None

        data = path.read_bytes()
        return base64.b64encode(data).decode() if data else None
    except (subprocess.SubprocessError, OSError):
        return None
    finally:
        path.unlink(missing_ok=True)
