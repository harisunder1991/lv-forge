"""LV Forge review tools for saved VIs and the running LabVIEW IDE."""

import base64
from datetime import datetime, timezone
import hashlib
from html import escape
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, NamedTuple

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

server = MCPServer("LV Forge")
EXEC_STATES = {0: "broken", 1: "idle", 2: "running_top_level", 3: "running_as_subvi"}


class LVKitResult(NamedTuple):
    stdout: str
    warnings: list[str]
    notices: list[str]

    def diagnostics(self) -> dict[str, Any]:
        return {
            "partial_analysis": bool(self.warnings),
            "warnings": self.warnings,
            "notices": self.notices,
        }


def vi_file(vi_path: str) -> Path:
    path = Path(vi_path).expanduser().resolve()
    if not path.is_file() or path.suffix.lower() != ".vi":
        raise ToolError(f"Expected a saved .vi file: {path}")
    return path


def lvkit(*args: str) -> LVKitResult:
    try:
        # Cached extractions can omit warnings emitted by the original parse.
        with tempfile.TemporaryDirectory(prefix="lvk-") as cache:
            result = subprocess.run(
                [sys.executable, "-X", "utf8", "-m", "lvkit", *args],
                env={**os.environ, "LVKIT_CACHE_DIR": cache},
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )
    except subprocess.TimeoutExpired as exc:
        raise ToolError(f"LVKit {args[0]} timed out after 60 seconds.") from exc
    if result.returncode not in (0, 3):
        detail = result.stderr.strip() or result.stdout.strip()
        raise ToolError(f"lvkit failed (exit {result.returncode}): {detail[-2000:]}")
    warnings, notices = [], []
    lines = result.stderr.replace(cache, "[LVKit cache]").splitlines()
    for line in dict.fromkeys(line.strip() for line in lines if line.strip()):
        if line.startswith("lvkit: auto-detected "):
            notices.append(line)
        else:
            warnings.append(line)
    if result.returncode == 3:
        warnings.insert(0, f"LVKit {args[0]} reported partial output (exit 3).")
    return LVKitResult(result.stdout, warnings, notices)


def file_sha256(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


@server.tool()
def lv_inspect(vi_path: str) -> dict[str, Any]:
    """Describe the saved VI's nodes, terminals, and wiring. Uses the file on disk."""
    path = vi_file(vi_path)
    disk_sha256 = file_sha256(path)
    result = lvkit("describe", "--format", "json", str(path))
    try:
        diagram = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        detail = " ".join(result.warnings)
        raise ToolError(f"LVKit returned invalid diagram JSON. {detail}".rstrip()) from exc
    if file_sha256(path) != disk_sha256:
        raise ToolError("The saved VI changed during inspection. Retry with a stable revision.")
    return {
        "vi_path": str(path),
        "disk_sha256": disk_sha256,
        "diagram": diagram,
        **result.diagnostics(),
    }


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
            "warnings": [],
        }
    except pythoncom.com_error as exc:
        raise ToolError(f"LabVIEW ActiveX check failed: {exc}") from exc
    finally:
        vi = app = None
        pythoncom.CoUninitialize()


@server.tool()
def lv_diff(before_vi: str, after_vi: str) -> dict[str, Any]:
    """Compare two saved VI files and report structural diagram changes."""
    before = vi_file(before_vi)
    after = vi_file(after_vi)
    result = lvkit("diff", str(before), str(after))
    return {"diff": result.stdout, **result.diagnostics()}


def render_svg(path: Path, target: Path) -> LVKitResult:
    result = lvkit("render", str(path), "-o", str(target))
    if not target.is_file() or target.stat().st_size == 0:
        detail = " ".join(result.warnings)
        raise ToolError(f"LVKit did not produce an SVG. {detail}".rstrip())
    return result


@server.tool()
def lv_render(vi_path: str) -> dict[str, Any]:
    """Render a saved VI as an SVG in a new temporary folder."""
    path = vi_file(vi_path)
    with tempfile.TemporaryDirectory(prefix="lv-forge-") as staging:
        staged_svg = Path(staging) / "diagram.svg"
        result = render_svg(path, staged_svg)
        with tempfile.NamedTemporaryFile(prefix="lv-forge-", suffix=".svg", delete=False) as output:
            output.write(staged_svg.read_bytes())
    return {"vi_path": str(path), "svg_path": output.name, **result.diagnostics()}


def html_list(items: list[str], empty: str) -> str:
    if not items:
        return f"<p>{escape(empty)}</p>"
    return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"


@server.tool()
def lv_report(
    vi_path: str, include_live_check: bool = False, allow_com_activation: bool = False
) -> dict[str, Any]:
    """Create a self-contained local HTML inspection report for a saved VI.

    The optional live check records IDE runnability separately from saved-file analysis.
    """
    if allow_com_activation and not include_live_check:
        raise ToolError("COM activation requires include_live_check=true.")
    path = vi_file(vi_path)
    inspection = lv_inspect(str(path))
    with tempfile.TemporaryDirectory(prefix="lv-forge-") as staging:
        svg_path = Path(staging) / "diagram.svg"
        rendering = render_svg(path, svg_path)
        svg = base64.b64encode(svg_path.read_bytes()).decode("ascii")
    if file_sha256(path) != inspection["disk_sha256"]:
        raise ToolError("The saved VI changed while generating the report. Retry with a stable revision.")

    warnings = list(dict.fromkeys(inspection["warnings"] + rendering.warnings))
    notices = list(dict.fromkeys(inspection["notices"] + rendering.notices))
    partial = bool(warnings)
    live_summary = "Live check was not requested."
    live = None
    if include_live_check:
        try:
            live = lv_check(str(path), allow_com_activation=allow_com_activation)
            live_summary = (
                f"LabVIEW {live['labview_version']}, state {live['execution_state']}, "
                f"runnable: {live['is_runnable']}. Unsaved changes and exact broken-wire count are unknown."
            )
        except ToolError as exc:
            live_summary = f"Live check unavailable. {exc}"
            warnings.append(live_summary)

    diagram = inspection["diagram"]
    saved_version = diagram.get("properties", {}).get("lv_version")
    subvis = sorted({
        item["name"] for item in diagram.get("components", [])
        if item["name"].lower().endswith((".vi", ".vim"))
    }, key=str.casefold)
    terminal_lists = []
    for direction in ("inputs", "outputs"):
        terminals = [
            f"{item['name']} ({item.get('type') or 'type unavailable'})"
            for item in diagram.get(direction, [])
        ]
        terminal_lists.append(html_list(terminals, f"No {direction} detected."))

    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    coverage = "Partial analysis" if partial else "No LVKit warnings reported"
    report = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LV Forge report — {escape(path.name)}</title>
<style>
body {{ font: 16px/1.5 system-ui, sans-serif; margin: 2rem auto; max-width: 72rem; padding: 0 1rem; }}
dt {{ font-weight: bold; }} dd {{ margin: 0 0 .7rem; overflow-wrap: anywhere; }}
.partial {{ background: #fff2cf; padding: .75rem; }} li {{ overflow-wrap: anywhere; }}
img {{ max-width: 100%; height: auto; }}
</style>
<h1>{escape(path.name)}</h1>
<p class="{'partial' if partial else 'coverage'}"><strong>{coverage}</strong></p>
<dl>
<dt>Saved VI</dt><dd>{escape(str(path))}</dd>
<dt>SHA-256</dt><dd>{inspection['disk_sha256']}</dd>
<dt>Saved LabVIEW version</dt><dd>{escape(saved_version or 'Unavailable')}</dd>
<dt>Generated (UTC)</dt><dd>{created_at}</dd>
<dt>Tool versions</dt><dd>LVKit {escape(version('lvkit'))} · MCP SDK {escape(version('mcp'))}</dd>
</dl>
<h2>Diagnostics</h2>
{html_list(warnings, 'No warnings reported.')}
{html_list(notices, 'No additional notices.')}
<h2>Inputs</h2>{terminal_lists[0]}
<h2>Outputs</h2>{terminal_lists[1]}
<h2>Detected SubVIs</h2>{html_list(subvis, 'No named SubVI calls detected.')}
<h2>Saved block diagram</h2>
<img src="data:image/svg+xml;base64,{svg}" alt="Block diagram of {escape(path.name)}">
<h2>Live IDE status</h2><p>{escape(live_summary)}</p>
<p>This report records inspection evidence. Record functional test results separately.</p>
</html>
"""
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix="lv-forge-report-", suffix=".html", delete=False
    ) as output:
        output.write(report)
    return {
        "vi_path": str(path),
        "report_path": output.name,
        "disk_sha256": inspection["disk_sha256"],
        "generated_at_utc": created_at,
        "saved_labview_version": saved_version,
        "partial_analysis": partial,
        "warnings": warnings,
        "notices": notices,
        "live_check": live,
    }


if __name__ == "__main__":
    server.run()
