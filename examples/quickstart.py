"""Demonstrate LV Forge's inspection tools using the bundled sample VIs."""

import argparse
from pathlib import Path
import sys

from mcp.server.mcpserver.exceptions import ToolError

EXAMPLES_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXAMPLES_DIR.parent))
import server


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="also check runnability in LabVIEW")
    parser.add_argument(
        "--allow-com-activation",
        action="store_true",
        help="allow COM to start LabVIEW if attachment fails (requires --live)",
    )
    args = parser.parse_args()
    if args.allow_com_activation and not args.live:
        parser.error("--allow-com-activation requires --live")

    add_vi = str(EXAMPLES_DIR / "Sample_Add.vi")
    multiply_vi = str(EXAMPLES_DIR / "Sample_Multiply.vi")

    try:
        print("Inspecting Sample_Add.vi")
        inspection = server.lv_inspect(add_vi)
        print(f"  SHA-256: {inspection['disk_sha256']}")
        terminals = inspection["diagram"].get("connector_pane", {}).get("terminals", [])
        print(f"  Connector pane terminals: {[terminal['name'] for terminal in terminals]}")

        print("\nComparing Sample_Add.vi with Sample_Multiply.vi")
        comparison = server.lv_diff(add_vi, multiply_vi)
        print(comparison["diff"].rstrip())

        print("\nRendering Sample_Add.vi")
        rendering = server.lv_render(add_vi)
        print(f"  SVG: {rendering['svg_path']}")

        offline_results = (inspection, comparison, rendering)
        for warning in dict.fromkeys(warning for result in offline_results for warning in result["warnings"]):
            print(f"  {warning}", file=sys.stderr)
        partial = any(result["partial_analysis"] for result in offline_results)

        if partial:
            print("\nOffline analysis is partial. See the warnings above.", file=sys.stderr)

        if not args.live:
            if not partial:
                print("\nOffline demo passed. Use --live to request the IDE check.")
            return 3 if partial else 0

        print("\nChecking Sample_Add.vi in LabVIEW")
        result = server.lv_check(add_vi, allow_com_activation=args.allow_com_activation)
        print(f"  LabVIEW version: {result['labview_version']}")
        print(f"  Execution state: {result['execution_state']}")
        print(f"  Runnable: {result['is_runnable']}")
        if result["is_runnable"] is not True:
            print("Live check did not confirm runnability.", file=sys.stderr)
            return 1
    except (ToolError, OSError) as exc:
        print(f"Quickstart failed: {exc}", file=sys.stderr)
        return 1

    print("\nLive check passed." if partial else "\nOffline demo and live check passed.")
    return 3 if partial else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="backslashreplace")
    raise SystemExit(main())
