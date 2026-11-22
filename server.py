"""LV Forge review tools for saved VIs and the running LabVIEW IDE."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

server = MCPServer("LV Forge")
EXEC_STATES = {0: "broken", 1: "idle", 2: "running_top_level", 3: "running_as_subvi"}


def vi_file(vi_path: str) -> Path:
    path = Path(vi_path).expanduser().resolve()
    if not path.is_file() or path.suffix.lower() != ".vi":
        raise ToolError(f"Expected a saved .vi file: {path}")
    return path


def lvkit(*args: str) -> str:
    try:
        result = subprocess.run(
            [sys.executable, "-X", "utf8", "-m", "lvkit", *args],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"LVKit {args[0]} timed out after 30 seconds.") from exc
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise ToolError(f"lvkit failed (exit {result.returncode}): {detail[-2000:]}")
    return result.stdout


@server.tool()
def lv_inspect(vi_path: str) -> dict[str, Any]:
    """Describe the saved VI's nodes, terminals, and wiring. Uses the file on disk."""
    path = vi_file(vi_path)
    with path.open("rb") as source:
        disk_sha256 = hashlib.file_digest(source, "sha256").hexdigest()
    try:
        diagram = json.loads(lvkit("describe", "--format", "json", str(path)))
    except json.JSONDecodeError as exc:
        raise ToolError("LVKit returned invalid diagram JSON.") from exc
    return {"vi_path": str(path), "disk_sha256": disk_sha256, "diagram": diagram}


@server.tool()
def lv_check(vi_path: str, allow_com_activation: bool = False) -> dict[str, Any]:
    """Check runnability in the running Windows LabVIEW IDE without running the VI.

    Acquiring the reference can load a saved VI into the IDE. Set
    allow_com_activation only if COM may start LabVIEW when attachment fails.
    Broken-wire count and unsaved edits are reported as unknown.
    """
    if sys.platform != "win32":
        raise ToolError("The live LabVIEW check requires Windows and LabVIEW.")

    import pythoncom
    from win32com.client import Dispatch, GetActiveObject

    path = vi_file(vi_path)
    app = vi = None
    pythoncom.CoInitialize()
    try:
        try:
            app = GetActiveObject("LabVIEW.Application")
        except pythoncom.com_error as exc:
            if not allow_com_activation:
                raise ToolError(
                    "Could not attach to LabVIEW via ActiveX. Set "
                    "allow_com_activation only if COM may start LabVIEW."
                ) from exc
            app = Dispatch("LabVIEW.Application")
        vi = app.GetVIReference(str(path))
        state = int(vi.ExecState)
        return {
            "vi_path": str(path),
            "labview_version": str(app.Version),
            "execution_state": EXEC_STATES.get(state, f"unknown ({state})"),
            "is_runnable": state != 0 if state in EXEC_STATES else None,
            "broken_wire_count": None,
            "has_unsaved_changes": None,
        }
    except pythoncom.com_error as exc:
        raise ToolError(f"LabVIEW ActiveX check failed: {exc}") from exc
    finally:
        vi = app = None
        pythoncom.CoUninitialize()


@server.tool()
def lv_diff(before_vi: str, after_vi: str) -> str:
    """Compare two saved VI files and report structural diagram changes."""
    before = vi_file(before_vi)
    after = vi_file(after_vi)
    return lvkit("diff", str(before), str(after))


@server.tool()
def lv_render(vi_path: str) -> dict[str, str]:
    """Render a saved VI as an SVG in a new temporary folder."""
    path = vi_file(vi_path)
    with tempfile.TemporaryDirectory(prefix="lv-forge-") as staging:
        staged_svg = Path(staging) / "diagram.svg"
        lvkit("render", str(path), "-o", str(staged_svg))
        with tempfile.NamedTemporaryFile(prefix="lv-forge-", suffix=".svg", delete=False) as output:
            output.write(staged_svg.read_bytes())
    return {"vi_path": str(path), "svg_path": output.name}


if __name__ == "__main__":
    server.run()
